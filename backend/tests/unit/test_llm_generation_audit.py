from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.models.domain import Event
from app.providers.llm.json_runner import LLMJsonRunner
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

    async def fake_complete(_candidate, **_kwargs) -> str:
        return next(responses)

    monkeypatch.setattr(runner, "_complete", fake_complete)

    with pytest.raises(RuntimeError, match="All LLM candidates failed"):
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


def test_provider_candidates_carry_provider_specific_configuration() -> None:
    settings = Settings(
        gemini_api_key="gemini-key",
        gemini_reasoning_effort="low",
        cohere_api_key="cohere-key",
    )
    runner = LLMJsonRunner(settings)

    gemini = runner._candidate_from_model("gemini/gemini-3.6-flash")
    cohere = runner._candidate_from_model("cohere/command-a-plus-05-2026")

    assert (gemini.provider, gemini.reasoning_effort, gemini.api_key) == (
        "gemini",
        "low",
        "gemini-key",
    )
    assert (cohere.provider, cohere.api_key) == ("cohere", "cohere-key")


def test_latest_gemini_models_omit_deprecated_sampling_temperature() -> None:
    assert LLMJsonRunner._supports_sampling_temperature("gemini/gemini-2.5-flash") is True
    assert LLMJsonRunner._supports_sampling_temperature("gemini/gemini-3.5-flash-lite") is False
    assert LLMJsonRunner._supports_sampling_temperature("gemini/gemini-3.6-flash") is False
    assert LLMJsonRunner._supports_sampling_temperature("cohere/command-a-plus-05-2026") is True


@pytest.mark.parametrize(
    ("model", "provider"),
    [
        ("gemini/gemini-3.5-flash-lite", "gemini"),
        ("cohere/command-a-plus-05-2026", "cohere"),
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
        )
    )
    candidate = runner._candidate_from_model(model)

    result = asyncio.run(
        runner._complete(candidate, system_prompt="system", user_prompt="user")
    )

    assert result == '{"value":1}'
    assert candidate.provider == provider
    assert captured["response_format"] == {"type": "json_object"}
