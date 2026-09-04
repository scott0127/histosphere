from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.models.domain import Event
from app.providers.llm.json_runner import (
    LLMCallMetadata,
    LLMCompletion,
    LLMJsonRunner,
    LLMRunResult,
)
from app.providers.llm.litellm_provider import LiteLLMProvider
from app.providers.llm.structured import ChatOutputPayload
from app.services.llm_generation_audit import record_rejected_generation


class _Payload(BaseModel):
    value: int


def test_rejected_generation_audit_retains_raw_output(monkeypatch, tmp_path) -> None:
    audit_path = tmp_path / "rejections.jsonl"
    monkeypatch.setenv("LLM_REJECTION_LOG_PATH", str(audit_path))

    record_id = record_rejected_generation(
        stage="contract_validation",
        provider="gemini",
        model="gemini/gemini-3.6-flash",
        task_name="test",
        raw_output="未通過的原始回覆",
        reasons=["early_answer_exposure"],
        context={"condition_key": "ebl_roleplay"},
    )

    record = json.loads(audit_path.read_text(encoding="utf-8"))
    assert record["record_id"] == record_id
    assert record["raw_output"] == "未通過的原始回覆"
    assert record["reasons"] == ["early_answer_exposure"]
    assert record["context"]["condition_key"] == "ebl_roleplay"


def test_chat_structured_output_preserves_off_topic_redirect_metadata() -> None:
    result = LiteLLMProvider._chat_generation_result(
        ChatOutputPayload(
            response="讓我們回到目前的歷史事件。",
            off_topic_redirect=True,
        ),
        Event(canonical_name="法國大革命"),
    )

    assert result.interaction_metadata["off_topic_redirect"] is True


def test_chat_structured_output_preserves_resolution_criteria() -> None:
    result = LiteLLMProvider._chat_generation_result(
        ChatOutputPayload(
            response="你已用證據修正原先的判斷。",
            resolution_error_recognized=True,
            resolution_error_reflected=True,
            resolution_self_corrected=True,
        ),
        Event(canonical_name="法國大革命"),
    )

    assert result.interaction_metadata["resolution_error_recognized"] is True
    assert result.interaction_metadata["resolution_error_reflected"] is True
    assert result.interaction_metadata["resolution_self_corrected"] is True


def test_json_runner_audits_initial_and_repair_schema_failures(monkeypatch, tmp_path) -> None:
    audit_path = tmp_path / "schema-rejections.jsonl"
    monkeypatch.setenv("LLM_REJECTION_LOG_PATH", str(audit_path))
    runner = LLMJsonRunner(
        Settings(
            llm_model="gemini/gemini-3.6-flash",
            llm_fallback_models=[],
            gemini_api_key="test-key",
        )
    )
    responses = iter(["not json", '{"value":"still invalid"}'])

    async def fake_complete(_candidate, **_kwargs) -> LLMCompletion:
        return LLMCompletion(content=next(responses))

    monkeypatch.setattr(runner, "_complete", fake_complete)

    with pytest.raises(RuntimeError, match="locked provider"):
        asyncio.run(
            runner.run_json(
                schema=_Payload,
                system_prompt="system",
                user_prompt="user",
                task_name="schema_test",
            )
        )

    records = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert records[0]["stage"] == "schema_validation_initial"
    assert records[0]["raw_output"] == "not json"
    assert records[1]["stage"] == "schema_validation_repair"
    assert records[1]["raw_output"] == '{"value":"still invalid"}'


def test_json_runner_counts_initial_and_schema_repair_usage(monkeypatch) -> None:
    runner = LLMJsonRunner(
        Settings(llm_model="gpt-5.6-luna", openai_api_key="openai-key")
    )
    responses = iter(
        [
            LLMCompletion(
                content="not json",
                prompt_tokens=100,
                cached_prompt_tokens=40,
                completion_tokens=20,
                reasoning_tokens=8,
                total_tokens=120,
                estimated_cost_usd=0.001,
            ),
            LLMCompletion(
                content='{"value":1}',
                prompt_tokens=60,
                cached_prompt_tokens=20,
                completion_tokens=10,
                reasoning_tokens=3,
                total_tokens=70,
                estimated_cost_usd=0.0005,
            ),
        ]
    )

    async def fake_complete(_candidate, **_kwargs) -> LLMCompletion:
        return next(responses)

    monkeypatch.setattr(runner, "_complete", fake_complete)
    result = asyncio.run(
        runner.run_json(
            schema=_Payload,
            system_prompt="system",
            user_prompt="user",
            task_name="usage_repair_test",
        )
    )

    assert result.metadata.schema_repair_count == 1
    assert result.metadata.prompt_tokens == 160
    assert result.metadata.cached_prompt_tokens == 60
    assert result.metadata.completion_tokens == 30
    assert result.metadata.reasoning_tokens == 11
    assert result.metadata.total_tokens == 190
    assert result.metadata.estimated_cost_usd == pytest.approx(0.0015)


def test_json_runner_repairs_payload_that_fails_dynamic_validation(monkeypatch) -> None:
    runner = LLMJsonRunner(
        Settings(llm_model="gpt-5.6-luna", openai_api_key="openai-key")
    )
    responses = iter(
        [
            LLMCompletion(content='{"value":1}'),
            LLMCompletion(content='{"value":2}'),
        ]
    )

    async def fake_complete(_candidate, **_kwargs) -> LLMCompletion:
        return next(responses)

    def require_even(payload: _Payload) -> None:
        if payload.value % 2:
            raise ValueError("value must be even")

    monkeypatch.setattr(runner, "_complete", fake_complete)
    result = asyncio.run(
        runner.run_json(
            schema=_Payload,
            system_prompt="system",
            user_prompt="user",
            task_name="dynamic_validation_test",
            payload_validator=require_even,
        )
    )

    assert result.payload.value == 2
    assert result.metadata.schema_repair_count == 1
    assert result.metadata.attempt_count == 2


def test_provider_candidates_carry_provider_specific_configuration() -> None:
    settings = Settings(
        gemini_api_key="gemini-key",
        gemini_reasoning_effort="low",
        openai_api_key="openai-key",
        openai_reasoning_effort="low",
        cohere_api_key="cohere-key",
    )
    runner = LLMJsonRunner(settings)

    gemini = runner._candidate_from_model("gemini/gemini-3.6-flash")
    cohere = runner._candidate_from_model("cohere/command-a-plus-05-2026")
    openai = runner._candidate_from_model("gpt-5.6-luna")

    assert (gemini.provider, gemini.reasoning_effort, gemini.api_key) == (
        "gemini",
        "low",
        "gemini-key",
    )
    assert (cohere.provider, cohere.api_key) == ("cohere", "cohere-key")
    assert (openai.provider, openai.reasoning_effort, openai.api_key) == (
        "openai",
        "low",
        "openai-key",
    )
    assert openai.model == "gpt-5.6-luna"


def test_runtime_locks_the_configured_model_without_provider_fallback() -> None:
    runner = LLMJsonRunner(
        Settings(
            llm_model="gemini/gemini-3.6-flash",
            llm_fallback_models=["nvidia/backup-model", "cohere/backup-model"],
            gemini_api_key="gemini-key",
            nvidia_api_key="nvidia-key",
            cohere_api_key="cohere-key",
        )
    )

    candidates = runner._candidates()

    assert len(candidates) == 1
    assert candidates[0].provider == "gemini"
    assert candidates[0].display_model == "gemini/gemini-3.6-flash"


def test_json_runner_retries_transient_failure_on_same_model_and_records_metadata(monkeypatch) -> None:
    runner = LLMJsonRunner(
        Settings(
            llm_model="gemini/gemini-3.6-flash",
            llm_fallback_models=["nvidia/backup-model"],
            gemini_api_key="gemini-key",
            nvidia_api_key="nvidia-key",
        )
    )
    called_models: list[str] = []

    async def fake_complete(candidate, **_kwargs) -> LLMCompletion:
        called_models.append(candidate.display_model)
        if len(called_models) == 1:
            raise TimeoutError("temporary timeout")
        return LLMCompletion(
            content='{"value":1}',
            prompt_tokens=12,
            completion_tokens=4,
            total_tokens=16,
            finish_reason="stop",
        )

    monkeypatch.setattr(runner, "_complete", fake_complete)

    result = asyncio.run(
        runner.run_json(
            schema=_Payload,
            system_prompt="system",
            user_prompt="user",
            task_name="metadata_test",
        )
    )

    assert result.payload.value == 1
    assert called_models == [
        "gemini/gemini-3.6-flash",
        "gemini/gemini-3.6-flash",
    ]
    assert result.metadata.provider == "gemini"
    assert result.metadata.model == "gemini/gemini-3.6-flash"
    assert result.metadata.attempt_count == 2
    assert result.metadata.transient_retry_count == 1
    assert result.metadata.provider_switching_enabled is False
    assert result.metadata.fallback_reason is None
    assert result.metadata.retry_reason == "timeout"
    assert result.metadata.total_tokens == 16
    assert result.metadata.finish_reason == "stop"
    assert result.metadata.correlation_id


def test_json_runner_treats_empty_provider_response_as_retryable(monkeypatch) -> None:
    runner = LLMJsonRunner(
        Settings(
            llm_model="gpt-5.6-luna",
            openai_api_key="openai-key",
        )
    )
    attempts = 0

    async def fake_complete(_candidate, **_kwargs) -> LLMCompletion:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("LLM returned empty content (finish_reason=length)")
        return LLMCompletion(
            content='{"value":1}',
            prompt_tokens=12,
            completion_tokens=4,
            total_tokens=16,
            finish_reason="stop",
        )

    monkeypatch.setattr(runner, "_complete", fake_complete)

    result = asyncio.run(
        runner.run_json(
            schema=_Payload,
            system_prompt="system",
            user_prompt="user",
            task_name="empty_response_test",
        )
    )

    assert result.payload.value == 1
    assert attempts == 2
    assert result.metadata.transient_retry_count == 1
    assert result.metadata.retry_reason == "empty_response"


def test_chat_provider_passes_the_canonical_learner_message_only_once(monkeypatch) -> None:
    provider = LiteLLMProvider(
        Settings(
            llm_model="gemini/gemini-3.6-flash",
            gemini_api_key="gemini-key",
        )
    )
    captured: dict = {}
    metadata = LLMCallMetadata(
        correlation_id="call-1",
        task_name="generate_chat_response",
        provider="gemini",
        model="gemini/gemini-3.6-flash",
        status="completed",
        latency_ms=20,
        attempt_count=1,
        transient_retry_count=0,
        schema_repair_count=0,
    )

    async def fake_run_json(**kwargs):
        captured.update(kwargs)
        return LLMRunResult(
            payload=ChatOutputPayload(response="收到。"),
            metadata=metadata,
        )

    monkeypatch.setattr(provider.runner, "run_json", fake_run_json)
    learner_message = "這是唯一 learner 訊息"

    result = asyncio.run(
        provider.generate_chat_response(
            event=Event(canonical_name="法國大革命"),
            persona=None,
            condition=None,
            task_attempt=None,
            user_message=learner_message,
            prompt=f"[user_message]\n{learner_message}",
            rag_sources=[],
        )
    )

    assert captured["user_prompt"].count(learner_message) == 1
    assert result.llm_metadata["llm_call"]["correlation_id"] == "call-1"


def test_latest_gemini_models_omit_deprecated_sampling_temperature() -> None:
    assert LLMJsonRunner._supports_sampling_temperature("gemini/gemini-2.5-flash") is True
    assert LLMJsonRunner._supports_sampling_temperature("gemini/gemini-3.5-flash-lite") is False
    assert LLMJsonRunner._supports_sampling_temperature("gemini/gemini-3.6-flash") is False
    assert LLMJsonRunner._supports_sampling_temperature("gpt-5.6-luna") is False
    assert LLMJsonRunner._supports_sampling_temperature("gpt-5.6-terra") is False
    assert LLMJsonRunner._supports_sampling_temperature("cohere/command-a-plus-05-2026") is True


@pytest.mark.parametrize(
    ("model", "provider"),
    [
        ("gemini/gemini-3.5-flash-lite", "gemini"),
        ("cohere/command-a-plus-05-2026", "cohere"),
        ("gpt-5.6-luna", "openai"),
    ],
)
def test_structured_providers_request_json_mode(monkeypatch, model, provider) -> None:
    captured: dict = {}

    async def fake_completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"value":1}'))]
        )

    monkeypatch.setattr("app.providers.llm.json_runner.acompletion", fake_completion)
    runner = LLMJsonRunner(
        Settings(
            llm_model=model,
            gemini_api_key="gemini-key",
            cohere_api_key="cohere-key",
            openai_api_key="openai-key",
        )
    )
    candidate = runner._candidate_from_model(model)

    result = asyncio.run(
        runner._complete(candidate, system_prompt="system", user_prompt="user")
    )

    assert result.content == '{"value":1}'
    assert candidate.provider == provider
    assert captured["response_format"] == {"type": "json_object"}


def test_openai_usage_preserves_cache_reasoning_and_estimated_cost(monkeypatch) -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"value":1}'), finish_reason="stop")],
        usage=SimpleNamespace(
            prompt_tokens=120,
            prompt_tokens_details=SimpleNamespace(cached_tokens=80),
            completion_tokens=30,
            completion_tokens_details=SimpleNamespace(reasoning_tokens=12),
            total_tokens=150,
        ),
    )

    async def fake_completion(**_kwargs):
        return response

    monkeypatch.setattr("app.providers.llm.json_runner.acompletion", fake_completion)
    monkeypatch.setattr("app.providers.llm.json_runner.completion_cost", lambda **_kwargs: 0.000123)
    runner = LLMJsonRunner(Settings(llm_model="gpt-5.6-luna", openai_api_key="openai-key"))

    result = asyncio.run(
        runner._complete(
            runner._candidate_from_model("gpt-5.6-luna"),
            system_prompt="system",
            user_prompt="user",
        )
    )

    assert result.prompt_tokens == 120
    assert result.cached_prompt_tokens == 80
    assert result.completion_tokens == 30
    assert result.reasoning_tokens == 12
    assert result.total_tokens == 150
    assert result.estimated_cost_usd == 0.000123
