import json

from app.services.llm_usage_summary import usage_breakdown


def test_admin_usage_groups_all_stages_without_exposing_raw_ledger(client, monkeypatch, tmp_path):
    path = tmp_path / "usage.jsonl"
    monkeypatch.setenv("LLM_USAGE_LOG_PATH", str(path))
    stages = ["generate_event_profile", "generate_task", "generate_personas", "judge_task_attempt",
              "generate_greeting", "generate_chat_response", "review_answer", "generate_recovery_continuation"]
    records = []
    for index, stage in enumerate(stages):
        base = dict(attempt_id=str(index), task_name=stage, provider="test", model="test-model",
                    recorded_at="2026-09-05T00:00:00+00:00", key_fingerprint="private-fingerprint")
        done = dict(base, status="completed", prompt_tokens=10, completion_tokens=5, total_tokens=15,
                    estimated_cost_usd=0 if index == 0 else 0.001)
        records.extend([dict(base, status="started"), done, done, dict(base, status="started")])
    records.append(dict(base, attempt_id="retry", status="failed"))
    path.write_text("\n".join(json.dumps(record) for record in records) + '\n[]\n{"truncated":', encoding="utf-8")
    assert client.get("/api/admin/llm-usage").status_code == 401
    response = client.get("/api/admin/llm-usage", headers={"x-admin-key": "test-admin"})
    assert response.status_code == 200
    body = response.json()
    assert body["malformed_lines"] == 2
    assert body["log_available"] is True
    assert {row["stage"] for row in body["rows"]} == set(stages)
    assert sum(row["requests"] for row in body["rows"]) == 9
    assert sum(row["token_reported_requests"] for row in body["rows"]) == 8
    assert sum(row["cost_reported_requests"] for row in body["rows"]) == 8
    assert sum(row["total_tokens"] for row in body["rows"]) == 120
    assert round(sum(row["estimated_known_cost_usd"] for row in body["rows"]), 6) == 0.007
    for private in ("attempt_id", "private-fingerprint", str(path)):
        assert private not in response.text


def test_admin_usage_distinguishes_missing_log_from_read_failure(client, monkeypatch, tmp_path):
    path = tmp_path / "missing.jsonl"
    monkeypatch.setenv("LLM_USAGE_LOG_PATH", str(path))
    result = client.get("/api/admin/llm-usage", headers={"x-admin-key": "test-admin"}).json()
    assert result["log_available"] is False and result["rows"] == []
    path.mkdir()
    response = client.get("/api/admin/llm-usage", headers={"x-admin-key": "test-admin"})
    assert response.status_code == 503
    assert str(path) not in response.text


def test_usage_breakdown_does_not_infer_complete_legacy_retries_or_invalid_costs():
    rows = usage_breakdown([
        dict(task_name="chat", attempt_count=2, total_tokens=12, estimated_cost_usd=0.01),
        dict(task_name="invalid", total_tokens=None, estimated_cost_usd=float("nan")),
    ])
    chat, invalid = rows
    assert chat.requests == 2 and chat.total_tokens == 12
    assert chat.cost_reported_requests == chat.token_reported_requests == 0
    assert chat.estimated_known_cost_usd == 0.01
    assert invalid.cost_reported_requests == 0 and invalid.estimated_known_cost_usd == 0
