import json
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.providers.llm.base import ChatGenerationResult
from app.providers.llm.litellm_provider import LiteLLMProvider


ADMIN_HEADERS = {"x-admin-key": "test-admin"}


def initialize(client):
    response = client.post(
        "/api/event/initialize", headers=ADMIN_HEADERS,
        json={"event_name": "提示詞追蹤測試", "condition_key": "no_ebl_no_roleplay", "rebuild": False},
    )
    assert response.status_code == 200
    return response.json()["event_id"]


def test_dry_run_exposes_exact_accepted_messages_including_json_repair(client, monkeypatch, tmp_path):
    event_id = initialize(client)
    monkeypatch.setenv("LLM_REJECTION_LOG_PATH", str(tmp_path / "rejected.jsonl"))
    usage_path = tmp_path / "usage.jsonl"
    monkeypatch.setenv("LLM_USAGE_LOG_PATH", str(usage_path))
    sent = []

    async def completion(**kwargs):
        sent.append([dict(message) for message in kwargs["messages"]])
        content = "INVALID_JSON_MARKER" if len(sent) == 1 else json.dumps({
            "response": "這是測試回覆。", "dialogue_state": "STANDARD_CHAT",
        })
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=content), finish_reason="stop",
        )])

    monkeypatch.setattr("app.providers.llm.json_runner.acompletion", completion)
    monkeypatch.setattr("app.providers.llm.json_runner.completion_cost", lambda **_: 0)
    client.app.state.chat_service.llm_provider = LiteLLMProvider(Settings(llm_model="gpt-test", openai_api_key="not-a-key"))
    before_logs = len(client.app.state.repository.list_research_logs())
    response = client.post("/api/admin/prompt-dry-run", headers=ADMIN_HEADERS, json={
        "event_id": event_id, "condition_key": "no_ebl_no_roleplay",
        "sample_user_message": "TRACE_LEARNER_INPUT",
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(sent) == 2
    assert payload["final_messages"] == sent[-1]
    assert payload["final_messages"][0]["role"] == "system"
    assert "Return only valid JSON" in payload["final_messages"][0]["content"]
    assert "Previous response:\nINVALID_JSON_MARKER" in payload["final_messages"][1]["content"]
    assert "TRACE_LEARNER_INPUT" in payload["final_messages"][1]["content"]
    assert payload["schema_repair_count"] == 1
    assert payload["final_prompt_kind"] == "base"
    assert payload["final_prompt"] == payload["prompt"]
    assert "INVALID_JSON_MARKER" not in payload["prompt"]
    assert len(client.app.state.repository.list_research_logs()) == before_logs
    # The admin-only trace must not be copied into the usage ledger or research metadata.
    assert "TRACE_LEARNER_INPUT" not in usage_path.read_text(encoding="utf-8")
    assert "request_messages" not in usage_path.read_text(encoding="utf-8")
    assert "request_messages" not in json.dumps(payload["interaction_metadata"])


@pytest.mark.parametrize("kind", ["repair", "constrained", "system_fallback"])
def test_dry_run_keeps_final_generation_path_distinct_from_base_modules(client, monkeypatch, kind):
    event_id = initialize(client)
    final = "" if kind == "system_fallback" else f"ACTUAL_{kind.upper()}_PROMPT"
    messages = [] if not final else [{"role": "system", "content": "actual system"}, {"role": "user", "content": final}]

    async def generate(**kwargs):
        metadata = {"answer_delivery": {"outcome": "accepted" if kind == "repair" else kind}}
        return ChatGenerationResult(response="測試回覆", request_messages=messages), metadata, final

    monkeypatch.setattr(client.app.state.chat_service, "generate_validated_response", generate)
    response = client.post("/api/admin/prompt-dry-run", headers=ADMIN_HEADERS, json={
        "event_id": event_id, "condition_key": "no_ebl_no_roleplay", "sample_user_message": "測試",
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["final_prompt_kind"] == kind
    assert payload["final_prompt"] == final
    assert payload["final_messages"] == messages
    assert payload["modules"]
    assert payload["prompt"] != final
