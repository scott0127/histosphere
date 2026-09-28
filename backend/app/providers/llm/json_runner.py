"""LLM JSON execution helper.

本模組集中處理 LiteLLM 呼叫、JSON 擷取、重試、研究 metadata 與 Pydantic 驗證。
Provider 方法只需要描述任務與 schema，避免每個生成函式各自實作解析邏輯。

執行流程:
    1. 鎖定設定中的單一模型與 provider。
    2. 呼叫 LiteLLM ``acompletion``；暫時性錯誤最多以同一模型重試一次。
    3. 從回覆中擷取 JSON 並以 Pydantic schema 驗證。
    4. 若 JSON 解析或驗證失敗，發送 repair prompt 重試一次。
    5. 回傳 payload 與該次呼叫專屬的研究 metadata。
"""

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from time import perf_counter
from typing import Generic, TypeVar
from uuid import uuid4

from litellm import acompletion, completion_cost
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.services.llm_generation_audit import record_rejected_generation, record_llm_usage


PayloadT = TypeVar("PayloadT", bound=BaseModel)
MAX_TRANSIENT_RETRIES = 1


@dataclass(frozen=True)
class LLMCallCandidate:
    """單一 LLM completion endpoint 嘗試的描述。

    封裝一個具體 model endpoint 的連線資訊，供
    ``LLMJsonRunner`` 依序嘗試。

    Attributes:
        provider: Provider 名稱（如 ``"litellm"``、``"nvidia"``）。
        model: LiteLLM 使用的 model 字串（可含 prefix）。
        display_model: 用於日誌與 metadata 的模型顯示名稱。
        api_base: 自訂 API base URL（可選）。
        api_key: 自訂 API key（可選）。
        extra_body: 傳給 LiteLLM 的額外 body 參數（可選）。
    """

    provider: str
    model: str
    display_model: str
    api_base: str | None = None
    api_key: str | None = None
    extra_body: dict | None = None
    reasoning_effort: str | None = None


@dataclass(frozen=True)
class LLMCompletion:
    """一次 LiteLLM HTTP completion 的文字與可取得的 token usage。"""

    content: str
    prompt_tokens: int | None = None
    cached_prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    finish_reason: str | None = None
    request_messages: list[dict[str, str]] = field(default_factory=list, repr=False)


@dataclass(frozen=True)
class LLMCallMetadata:
    """一個 structured LLM 任務的獨立研究紀錄。"""

    correlation_id: str
    task_name: str
    provider: str
    model: str
    status: str
    latency_ms: int
    attempt_count: int
    transient_retry_count: int
    schema_repair_count: int
    provider_switching_enabled: bool = False
    fallback_reason: str | None = None
    retry_reason: str | None = None
    failure_category: str | None = None
    prompt_tokens: int | None = None
    cached_prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    finish_reason: str | None = None

    audit_write_failures: list[str] = field(default_factory=list)
    usage_reported_attempts: int = 0
    cost_reported_attempts: int = 0
    estimated_known_cost_usd: float | None = None

    def as_dict(self) -> dict:
        """轉成可直接寫入 Supabase JSON 欄位的資料。"""

        return asdict(self)


@dataclass(frozen=True)
class LLMRunResult(Generic[PayloadT]):
    """通過 schema 的 payload，以及只屬於該次呼叫的 metadata。"""

    payload: PayloadT
    metadata: LLMCallMetadata
    request_messages: list[dict[str, str]] = field(default_factory=list, repr=False)


class LLMRunError(RuntimeError):
    """LLM 任務失敗，並保留不含密鑰的研究 metadata。"""

    def __init__(self, message: str, metadata: LLMCallMetadata) -> None:
        super().__init__(message)
        self.metadata = metadata


class LLMJsonRunner:
    """執行 structured JSON LLM call 並驗證回傳結構。

    集中處理 LLM 呼叫、JSON 擷取、有限重試、研究 metadata 與 Pydantic 驗證，
    讓 provider 方法只需描述 schema 與 prompt。

    Attributes:
        settings: 全域設定實例。
    """

    def __init__(self, settings: Settings) -> None:
        """初始化 runner。

        Args:
            settings: 全域 Settings 實例，提供 LLM 相關設定。
        """
        self.settings = settings

    async def run_json(
        self,
        *,
        schema: type[PayloadT],
        system_prompt: str,
        user_prompt: str,
        task_name: str,
        payload_validator: Callable[[PayloadT], None] | None = None,
        audit_best_effort: bool = False,
    ) -> LLMRunResult[PayloadT]:
        """以單一模型呼叫 LLM、驗證 JSON，並回傳 per-call metadata。

        Args:
            schema: 預期回傳 JSON 的 Pydantic model 類別。
            system_prompt: LLM system prompt。
            user_prompt: LLM user prompt。
            task_name: 任務名稱，用於錯誤訊息與日誌。
            payload_validator: 來源白名單等執行期條件的額外驗證器。

        Returns:
            LLMRunResult[PayloadT]: 結構化 payload 與本次呼叫的研究 metadata。

        Raises:
            LLMRunError: 單一設定模型經有限重試後仍失敗。
        """
        candidate = self._candidates()[0]
        correlation_id = str(uuid4())
        started_at = perf_counter()
        attempt_count = 0
        transient_retry_count = 0
        schema_repair_count = 0
        retry_reason: str | None = None
        finish_reason: str | None = None
        token_totals = {
            "prompt_tokens": 0,
            "cached_prompt_tokens": 0,
            "completion_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
        }
        token_usage_seen = False
        estimated_cost_usd = 0.0
        cost_seen = False
        usage_reported_attempts = 0
        cost_reported_attempts = 0
        audit_write_failures: list[str] = []
        request_messages: list[dict[str, str]] = []

        def audit(writer, **record) -> None:
            try:
                writer(**record)
            except Exception as exc:
                if not audit_best_effort:
                    raise
                # 背景觀察不能因額外檔案故障丟掉已生成的結果與用量。
                audit_write_failures.append(type(exc).__name__)

        def build_metadata(
            *,
            status: str,
            failure_category: str | None = None,
        ) -> LLMCallMetadata:
            return LLMCallMetadata(
                correlation_id=correlation_id,
                task_name=task_name,
                provider=candidate.provider,
                model=candidate.display_model,
                status=status,
                latency_ms=round((perf_counter() - started_at) * 1000),
                attempt_count=attempt_count,
                transient_retry_count=transient_retry_count,
                schema_repair_count=schema_repair_count,
                provider_switching_enabled=False,
                fallback_reason=None,
                retry_reason=retry_reason,
                failure_category=failure_category,
                prompt_tokens=token_totals["prompt_tokens"] if token_usage_seen else None,
                cached_prompt_tokens=(
                    token_totals["cached_prompt_tokens"] if token_usage_seen else None
                ),
                completion_tokens=token_totals["completion_tokens"] if token_usage_seen else None,
                reasoning_tokens=token_totals["reasoning_tokens"] if token_usage_seen else None,
                total_tokens=token_totals["total_tokens"] if token_usage_seen else None,
                estimated_cost_usd=estimated_cost_usd if cost_seen and cost_reported_attempts == attempt_count else None,
                finish_reason=finish_reason,
                audit_write_failures=list(audit_write_failures),
                usage_reported_attempts=usage_reported_attempts,
                cost_reported_attempts=cost_reported_attempts,
                estimated_known_cost_usd=estimated_cost_usd if cost_seen else None,
            )

        async def complete(current_user_prompt: str) -> str:
            nonlocal attempt_count, finish_reason, retry_reason
            nonlocal token_usage_seen, transient_retry_count
            nonlocal estimated_cost_usd, cost_seen
            nonlocal usage_reported_attempts, cost_reported_attempts
            nonlocal request_messages

            for retry_index in range(MAX_TRANSIENT_RETRIES + 1):
                attempt_count += 1
                # 一次網路請求一個 ID，避免重試、JSON 修復與報表副本重複計費。
                usage_record = dict(
                    api_key=candidate.api_key, attempt_id=str(uuid4()),
                    correlation_id=correlation_id, attempt_number=attempt_count,
                    task_name=task_name, provider=candidate.provider, model=candidate.display_model,
                )
                audit(record_llm_usage, **usage_record, status="started")
                try:
                    completion = await self._complete(
                        candidate,
                        system_prompt=system_prompt,
                        user_prompt=current_user_prompt,
                    )
                except Exception as exc:
                    audit(record_llm_usage, **usage_record, status="failed", failure_category=self._failure_category(exc),
                                     estimated_cost_usd=None, usage_known=False)
                    if retry_index >= MAX_TRANSIENT_RETRIES or not self._is_transient_error(exc):
                        raise
                    transient_retry_count += 1
                    retry_reason = self._failure_category(exc)
                    continue
                request_messages = completion.request_messages
                # 先保留已付費用量；額外帳本寫入失敗時，錯誤 metadata 仍可帶回它。
                if completion.total_tokens is not None:
                    usage_reported_attempts += 1
                if completion.estimated_cost_usd is not None:
                    cost_reported_attempts += 1
                for field_name in token_totals:
                    value = getattr(completion, field_name)
                    if value is not None:
                        token_totals[field_name] += value
                        token_usage_seen = True
                if completion.estimated_cost_usd is not None:
                    estimated_cost_usd += completion.estimated_cost_usd
                    cost_seen = True
                finish_reason = completion.finish_reason
                # 寫入失敗不應觸發模型重試；空回覆仍可能有付費推理 tokens。
                audit(record_llm_usage, **usage_record, status="completed" if completion.content else "empty_response",
                                 usage_known=completion.total_tokens is not None,
                                 **{k: v for k, v in asdict(completion).items() if k not in {"content", "request_messages"}})
                try:
                    if not completion.content:
                        raise RuntimeError(f"LLM returned empty content (finish_reason={finish_reason or 'unknown'})")
                    return completion.content
                except Exception as exc:
                    if retry_index >= MAX_TRANSIENT_RETRIES or not self._is_transient_error(exc):
                        raise
                    # 正式實驗只允許同一模型做一次有限重試，不切換 provider 或 model。
                    transient_retry_count += 1
                    retry_reason = self._failure_category(exc)
            raise RuntimeError("LLM retry loop exited unexpectedly")

        try:
            first_text = await complete(user_prompt)
            try:
                payload = self._parse(schema, first_text)
                if payload_validator is not None:
                    payload_validator(payload)
                return LLMRunResult(payload=payload, metadata=build_metadata(status="completed"), request_messages=request_messages)
            except (json.JSONDecodeError, ValidationError, ValueError) as first_error:
                audit(record_rejected_generation,
                    stage="schema_validation_initial",
                    provider=candidate.provider,
                    model=candidate.display_model,
                    task_name=task_name,
                    raw_output=first_text,
                    reasons=[self._safe_error_message(first_error)],
                    context={"llm_call": build_metadata(status="repairing").as_dict()},
                )
                repair_prompt = (
                    "The previous response failed JSON validation. "
                    f"Task: {task_name}\n"
                    f"Validation error: {first_error}\n"
                    "Return only one valid JSON object matching the requested schema. "
                    "Do not include markdown fences."
                )
                schema_repair_count += 1
                second_text = await complete(
                    f"{user_prompt}\n\n{repair_prompt}\n\nPrevious response:\n{first_text}"
                )
                try:
                    payload = self._parse(schema, second_text)
                    if payload_validator is not None:
                        payload_validator(payload)
                except (json.JSONDecodeError, ValidationError, ValueError) as second_error:
                    audit(record_rejected_generation,
                        stage="schema_validation_repair",
                        provider=candidate.provider,
                        model=candidate.display_model,
                        task_name=task_name,
                        raw_output=second_text,
                        reasons=[self._safe_error_message(second_error)],
                        context={
                            "llm_call": build_metadata(
                                status="failed",
                                failure_category="schema_validation",
                            ).as_dict()
                        },
                    )
                    raise
                return LLMRunResult(payload=payload, metadata=build_metadata(status="completed"), request_messages=request_messages)
        except Exception as exc:
            failure_category = self._failure_category(exc)
            metadata = build_metadata(status="failed", failure_category=failure_category)
            audit(record_rejected_generation,
                stage="provider_or_generation_failure",
                provider=candidate.provider,
                model=candidate.display_model,
                task_name=task_name,
                raw_output=None,
                reasons=[self._safe_error_message(exc)],
                context={"llm_call": metadata.as_dict()},
            )
            raise LLMRunError(
                f"LLM call failed for {task_name} with locked provider "
                f"{candidate.provider}:{candidate.display_model}",
                metadata,
            ) from exc

    async def _complete(
        self,
        candidate: LLMCallCandidate,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMCompletion:
        """執行 LiteLLM completion。

        每個 candidate 可指定自己的 api_base、api_key 與 extra_body。

        Args:
            candidate: 目標 LLM endpoint 描述。
            system_prompt: System message 內容。
            user_prompt: User message 內容。

        Returns:
            LLMCompletion: LLM 文字內容與 provider 可提供的 token usage。

        Raises:
            RuntimeError: LLM 回傳空內容時。
        """
        kwargs = {
            "model": candidate.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self.settings.llm_max_output_tokens,
            "timeout": self.settings.llm_timeout_seconds,
        }
        if self._supports_sampling_temperature(candidate.model):
            kwargs["temperature"] = self.settings.llm_temperature
        if candidate.api_base:
            kwargs["api_base"] = candidate.api_base
        if candidate.api_key:
            kwargs["api_key"] = candidate.api_key
        if candidate.extra_body:
            kwargs["extra_body"] = candidate.extra_body
        if candidate.reasoning_effort:
            kwargs["reasoning_effort"] = candidate.reasoning_effort
        if candidate.provider in {"gemini", "cohere", "openai"}:
            kwargs["response_format"] = {"type": "json_object"}

        # Preserve precisely the messages submitted by this attempt, including schema repair.
        # Keep this snapshot out of the usage ledger and persisted research metadata.
        request_messages = [dict(message) for message in kwargs["messages"]]
        response = await acompletion(**kwargs)
        content = response.choices[0].message.content
        usage = getattr(response, "usage", None)
        return LLMCompletion(
            content=str(content) if content else "",
            prompt_tokens=self._usage_value(usage, "prompt_tokens"),
            cached_prompt_tokens=self._usage_detail_value(
                usage,
                "prompt_tokens_details",
                "cached_tokens",
            ),
            completion_tokens=self._usage_value(usage, "completion_tokens"),
            reasoning_tokens=self._usage_detail_value(
                usage,
                "completion_tokens_details",
                "reasoning_tokens",
            ),
            total_tokens=self._usage_value(usage, "total_tokens"),
            estimated_cost_usd=self._estimated_response_cost(response),
            finish_reason=self._finish_reason(response),
            request_messages=request_messages,
        )

    @staticmethod
    def _supports_sampling_temperature(model: str) -> bool:
        """判斷模型是否接受 temperature；reasoning 模型不傳衝突參數。"""

        normalized = model.lower()
        return not (
            "gemini-3.5-" in normalized
            or "gemini-3.6-" in normalized
            or "gpt-5.6-" in normalized
        )

    def _candidates(self) -> list[LLMCallCandidate]:
        """只建立設定中的單一 LLM endpoint。

        正式受測期間不能因 provider 狀態改變而讓不同受測者使用不同模型，
        因此其他已設定的 API key 不會被用來建立備援模型。

        Returns:
            list[LLMCallCandidate]: 僅包含鎖定模型的單元素清單。
        """
        return [self._candidate_from_model(self.settings.llm_model)]

    def _candidate_from_model(self, model: str) -> LLMCallCandidate:
        """依 model 名稱建立對應的 candidate。

        若 model 以 ``nvidia/`` 開頭，自動導向 NVIDIA endpoint。

        Args:
            model: LiteLLM 格式的模型名稱。

        Returns:
            LLMCallCandidate: 對應的 candidate。
        """
        normalized = model.removeprefix("openai/")
        if normalized.startswith("nvidia/"):
            return self._nvidia_candidate(normalized)
        if normalized.startswith("gemini/"):
            return LLMCallCandidate(
                provider="gemini",
                model=model,
                display_model=model,
                api_base=self.settings.llm_api_base,
                api_key=self.settings.gemini_api_key or self.settings.llm_api_key,
                reasoning_effort=self.settings.gemini_reasoning_effort,
            )
        if normalized.startswith("cohere/"):
            return LLMCallCandidate(
                provider="cohere",
                model=model,
                display_model=model,
                api_base=self.settings.llm_api_base,
                api_key=self.settings.cohere_api_key or self.settings.llm_api_key,
            )
        if normalized.startswith("gpt-"):
            return LLMCallCandidate(
                provider="openai",
                # 新模型名稱可能尚未在 LiteLLM 清單內，明確指定 provider，不能依賴名稱推測。
                model=f"openai/{normalized}",
                display_model=model,
                api_base=self.settings.llm_api_base,
                api_key=self.settings.openai_api_key or self.settings.llm_api_key,
                reasoning_effort=self.settings.openai_reasoning_effort,
            )
        return LLMCallCandidate(
            provider="litellm",
            model=model,
            display_model=model,
            api_base=self.settings.llm_api_base,
            api_key=self.settings.llm_api_key,
        )

    def _nvidia_candidate(self, model: str) -> LLMCallCandidate:
        """建立 NVIDIA NIM API candidate。

        若啟用 thinking 模式，會在 extra_body 中加入
        ``chat_template_kwargs`` 與 ``reasoning_budget``。

        Args:
            model: NVIDIA 模型名稱。

        Returns:
            LLMCallCandidate: NVIDIA endpoint candidate。
        """
        extra_body = None
        if self.settings.nvidia_enable_thinking:
            extra_body = {
                "chat_template_kwargs": {"enable_thinking": True},
                "reasoning_budget": self.settings.nvidia_reasoning_budget,
            }
        return LLMCallCandidate(
            provider="nvidia",
            model=f"openai/{model.removeprefix('openai/')}",
            display_model=model.removeprefix("openai/"),
            api_base=self.settings.nvidia_api_base,
            api_key=self.settings.nvidia_api_key,
            extra_body=extra_body,
        )

    def _safe_error_message(self, exc: Exception) -> str:
        """遮蔽 API key 後回傳安全的錯誤訊息。

        Args:
            exc: 原始例外。

        Returns:
            str: 已遮蔽敏感資訊的錯誤訊息。
        """
        text = str(exc)
        for secret in (
            self.settings.llm_api_key,
            self.settings.gemini_api_key,
            self.settings.openai_api_key,
            self.settings.nvidia_api_key,
            self.settings.cohere_api_key,
        ):
            if secret:
                text = text.replace(secret, "***")
        return text

    @staticmethod
    def _usage_value(usage, field_name: str) -> int | None:
        """從 LiteLLM dict 或物件 usage 中安全擷取整數。"""

        if usage is None:
            return None
        value = usage.get(field_name) if isinstance(usage, dict) else getattr(usage, field_name, None)
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @classmethod
    def _usage_detail_value(cls, usage, details_field: str, field_name: str) -> int | None:
        """讀取 Provider 回報的快取輸入或隱藏推理 token。"""

        if usage is None:
            return None
        details = (
            usage.get(details_field)
            if isinstance(usage, dict)
            else getattr(usage, details_field, None)
        )
        return cls._usage_value(details, field_name)

    @staticmethod
    def _estimated_response_cost(response) -> float | None:
        """依 LiteLLM 當前價格表估算本次回覆費用；無法核算時明確留空。"""

        try:
            return float(completion_cost(completion_response=response))
        except Exception:
            return None

    @staticmethod
    def _finish_reason(response) -> str | None:
        """讀取 provider 結束原因，以辨識輸出是否被 token 上限截斷。"""

        choices = getattr(response, "choices", None)
        if not choices:
            return None
        value = getattr(choices[0], "finish_reason", None)
        return str(value) if value is not None else None

    @staticmethod
    def _failure_category(exc: Exception) -> str:
        """將 provider 例外縮成可分析且不含敏感資訊的穩定分類。"""

        status_code = getattr(exc, "status_code", None)
        if status_code == 429:
            return "rate_limited"
        if status_code in {408, 500, 502, 503, 504}:
            return "provider_transient"
        if status_code in {401, 403}:
            return "authentication"
        if status_code == 400:
            return "invalid_request"
        if isinstance(exc, TimeoutError):
            return "timeout"
        if isinstance(exc, ConnectionError):
            return "connection"
        if isinstance(exc, (json.JSONDecodeError, ValidationError)):
            return "schema_validation"
        if str(exc).startswith("LLM returned empty content"):
            return "empty_response"

        name = type(exc).__name__.lower()
        if "timeout" in name:
            return "timeout"
        if "ratelimit" in name or "rate_limit" in name:
            return "rate_limited"
        if "connection" in name:
            return "connection"
        return "provider_error"

    @classmethod
    def _is_transient_error(cls, exc: Exception) -> bool:
        """只有暫時性錯誤與空回應才能以原 provider 重試。"""

        return cls._failure_category(exc) in {
            "timeout",
            "rate_limited",
            "connection",
            "provider_transient",
            "empty_response",
        }

    @staticmethod
    def _parse(schema: type[PayloadT], text: str) -> PayloadT:
        """擷取 JSON object 並套用 Pydantic schema。

        自動處理 markdown fences 包裹與非 JSON 前後綴。
        從回覆文字中找到第一個 ``{`` 到最後一個 ``}`` 的區間，
        解析為 JSON 並以 schema 驗證。

        Args:
            schema: 目標 Pydantic model 類別。
            text: LLM 回覆的原始文字。

        Returns:
            PayloadT: 驗證後的結構化物件。

        Raises:
            json.JSONDecodeError: JSON 解析失敗。
            ValidationError: Pydantic 驗證失敗。
        """
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.strip("`").strip()
            if clean.lower().startswith("json"):
                clean = clean[4:].strip()
        start = clean.find("{")
        end = clean.rfind("}")
        if start >= 0 and end >= start:
            clean = clean[start : end + 1]
        return schema.model_validate(json.loads(clean))
