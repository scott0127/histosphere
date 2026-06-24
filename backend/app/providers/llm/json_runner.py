"""LLM JSON execution helper.

本模組集中處理 LiteLLM 呼叫、JSON 擷取、重試與 Pydantic 驗證。
Provider 方法只需要描述任務與 schema，避免每個生成函式各自實作解析邏輯。
"""

import json
from dataclasses import dataclass
from typing import TypeVar

from litellm import acompletion
from pydantic import BaseModel, ValidationError

from app.core.config import Settings


PayloadT = TypeVar("PayloadT", bound=BaseModel)


@dataclass(frozen=True)
class LLMCallCandidate:
    """One concrete completion endpoint attempt."""

    provider: str
    model: str
    display_model: str
    api_base: str | None = None
    api_key: str | None = None
    extra_body: dict | None = None


class LLMJsonRunner:
    """執行 structured JSON LLM call。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.last_provider = "litellm"
        self.last_model = settings.llm_model

    async def run_json(
        self,
        *,
        schema: type[PayloadT],
        system_prompt: str,
        user_prompt: str,
        task_name: str,
    ) -> PayloadT:
        """呼叫 LLM 並驗證 JSON；失敗時依序嘗試備援模型。"""
        errors: list[str] = []
        for candidate in self._candidates():
            try:
                first_text = await self._complete(
                    candidate,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
                try:
                    payload = self._parse(schema, first_text)
                    self._mark_success(candidate)
                    return payload
                except (json.JSONDecodeError, ValidationError) as first_error:
                    repair_prompt = (
                        "The previous response failed JSON validation. "
                        f"Task: {task_name}\n"
                        f"Validation error: {first_error}\n"
                        "Return only one valid JSON object matching the requested schema. "
                        "Do not include markdown fences."
                    )
                    second_text = await self._complete(
                        candidate,
                        system_prompt=system_prompt,
                        user_prompt=f"{user_prompt}\n\n{repair_prompt}\n\nPrevious response:\n{first_text}",
                    )
                    payload = self._parse(schema, second_text)
                    self._mark_success(candidate)
                    return payload
            except Exception as exc:
                errors.append(
                    f"{candidate.provider}:{candidate.display_model}: {self._safe_error_message(exc)}"
                )
        raise RuntimeError(f"All LLM candidates failed for {task_name}: {' | '.join(errors)}")

    async def _complete(self, candidate: LLMCallCandidate, *, system_prompt: str, user_prompt: str) -> str:
        """執行 LiteLLM completion；每個 candidate 可指定自己的 api_base/api_key。"""
        kwargs = {
            "model": candidate.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_output_tokens,
            "timeout": self.settings.llm_timeout_seconds,
        }
        if candidate.api_base:
            kwargs["api_base"] = candidate.api_base
        if candidate.api_key:
            kwargs["api_key"] = candidate.api_key
        if candidate.extra_body:
            kwargs["extra_body"] = candidate.extra_body

        response = await acompletion(**kwargs)
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("LLM returned empty content")
        return str(content)

    def _candidates(self) -> list[LLMCallCandidate]:
        candidates = [self._candidate_from_model(self.settings.llm_model)]
        for model in self.settings.llm_fallback_models:
            candidates.append(self._candidate_from_model(model))

        if self.settings.nvidia_api_key and not any(candidate.provider == "nvidia" for candidate in candidates):
            candidates.append(self._nvidia_candidate(self.settings.nvidia_llm_model))

        deduped: list[LLMCallCandidate] = []
        seen: set[tuple[str, str, str | None]] = set()
        for candidate in candidates:
            key = (candidate.provider, candidate.display_model, candidate.api_base)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)
        return deduped

    def _candidate_from_model(self, model: str) -> LLMCallCandidate:
        normalized = model.removeprefix("openai/")
        if normalized.startswith("nvidia/"):
            return self._nvidia_candidate(normalized)
        return LLMCallCandidate(
            provider="litellm",
            model=model,
            display_model=model,
            api_base=self.settings.llm_api_base,
            api_key=self.settings.llm_api_key,
        )

    def _nvidia_candidate(self, model: str) -> LLMCallCandidate:
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

    def _mark_success(self, candidate: LLMCallCandidate) -> None:
        self.last_provider = candidate.provider
        self.last_model = candidate.display_model

    def _safe_error_message(self, exc: Exception) -> str:
        text = str(exc)
        for secret in (self.settings.llm_api_key, self.settings.nvidia_api_key):
            if secret:
                text = text.replace(secret, "***")
        return text

    @staticmethod
    def _parse(schema: type[PayloadT], text: str) -> PayloadT:
        """擷取 JSON object 並套用 Pydantic schema。"""
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
