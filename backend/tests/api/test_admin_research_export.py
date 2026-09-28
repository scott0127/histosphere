"""Admin 研究資料重播與匯出的整合測試。"""

import csv
import io
import json

from app.core.experiment_conditions import condition_code_for_key
from app.models.domain import ChatMessage, Participant, ResearchLog
from tests.task_review_helpers import review_and_enter


ADMIN_HEADERS = {"x-admin-key": "test-admin"}


def _prepare_conversation(client):
    created = client.post(
        "/api/event/initialize",
        headers=ADMIN_HEADERS,
        json={
            "event_name": "研究匯出整合測試事件",
            "condition_key": "no_ebl_no_roleplay",
            "rebuild": False,
        },
    )
    assert created.status_code == 200
    locked = client.post(
        f"/api/admin/events/{created.json()['event_id']}/material-lock",
        headers=ADMIN_HEADERS,
        json={"locked": True},
    )
    assert locked.status_code == 200

    repository = client.app.state.repository
    participant = repository.get_participant_by_auth_user("participant-001")
    assigned = client.patch(
        f"/api/admin/participants/{participant.id}",
        headers=ADMIN_HEADERS,
        json={"condition_list": [condition_code_for_key("no_ebl_no_roleplay")]},
    )
    assert assigned.status_code == 200

    initialized = client.post(
        "/api/event/initialize",
        json={
            "event_name": created.json()["event"]["canonical_name"],
            "condition_key": "no_ebl_no_roleplay",
            "rebuild": False,
        },
    )
    assert initialized.status_code == 200
    initialized_payload = initialized.json()

    accepted = client.post(
        f"/api/tasks/{initialized_payload['task']['id']}/submit",
        json={
            "session_id": initialized_payload["session_id"],
            "response_payload": {"answers": [{"question_id": "q01", "value": "測試回答"}]},
        },
    )
    assert accepted.status_code == 202
    result = review_and_enter(client, accepted.json())

    chat = client.post(
        "/api/chat",
        json={
            "conversation_id": result["conversation_id"],
            "user_message": "請說明這個事件的背景。",
            "client_request_id": "research-export-round-001",
        },
    )
    assert chat.status_code == 200
    return initialized_payload, result


def test_admin_can_replay_session_with_tokens_prompts_and_material_snapshot(client):
    initialized, _result = _prepare_conversation(client)

    response = client.get(
        f"/api/admin/sessions/{initialized['session_id']}/research",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["participant_code"] == "PTEST"
    assert payload["participant_bound"] is True
    assert payload["session"]["participant_id"] is not None
    assert payload["session"]["is_admin_test"] is False
    assert payload["session"]["user_id"] is None
    assert payload["attempt"]["user_id"] is None
    assert payload["conversation"]["user_id"] is None
    assert [message["speaker_type"] for message in payload["messages"]] == [
        "assistant",
        "learner",
        "assistant",
    ]
    assert payload["stats"] == {
        **payload["stats"],
        "total_messages": 3,
        "learner_messages": 1,
        "assistant_messages": 2,
        "completed_exchanges": 1,
        "prompt_tokens": 33,
        "cached_prompt_tokens": 12,
        "completion_tokens": 21,
        "reasoning_tokens": 6,
        "total_tokens": 54,
        "llm_calls_total": 3,
        "llm_calls_with_usage": 3,
        "llm_messages_total": 2,
        "llm_messages_with_usage": 2,
        "token_usage_coverage": 1.0,
        "token_usage_complete": True,
        "estimated_cost_usd": 0.0003,
        "cost_usage_complete": True,
    }
    assert payload["material_snapshot"]["status"] == "captured"
    rows = payload["stats"]["usage_breakdown"]
    assert {row["stage"] for row in rows} == {"judge_task_attempt", "generate_greeting", "generate_chat_response"}
    assert sum(row["total_tokens"] for row in rows) == 54
    assert sum(row["requests"] for row in rows) == 3
    assert payload["material_snapshot"]["hash_verified"] is True
    assert len(payload["prompt_records"]) == 2
    assert all(record["hash_verified"] for record in payload["prompt_records"])
    assert {record["stage"] for record in payload["prompt_records"]} == {
        "conversation_opening",
        "chat_response",
    }
    stats = payload["stats"]
    assert stats["total_characters"] == sum(
        sum(not char.isspace() for char in message["content"]) for message in payload["messages"]
    )
    assert stats["assistant_total_tokens"] == 36
    assert stats["assistant_average_tokens"] == 18
    assert stats["assistant_token_usage_complete"] is True
    assert len(stats["message_metrics"]) == 3
    assert stats["round_trips"][0]["learner_message_id"] == payload["messages"][1]["id"]
    assert stats["round_trips"][0]["assistant_message_id"] == payload["messages"][2]["id"]
    assert stats["round_trips"][0]["response_seconds"] >= 0
    assert stats["learning"]["denominator"] == max(stats["learning"]["corrected_questions"], 1)


def test_session_usage_includes_failed_calls_without_counting_audit_duplicates(client):
    initialized, result = _prepare_conversation(client)
    repository = client.app.state.repository
    failed_chat_call = {
        **client.app.state.llm_provider._llm_metadata("failed_chat")["llm_call"],
        "correlation_id": "failed-chat-call",
        "attempt_count": 2,
        "usage_reported_attempts": 1,
        "cost_reported_attempts": 1,
        "estimated_cost_usd": None,
        "estimated_known_cost_usd": 0.0001,
    }
    repository.add_message(
        ChatMessage(
            conversation_id=result["conversation_id"],
            speaker_type="learner",
            speaker_name="learner",
            sequence_index=repository.next_message_sequence(result["conversation_id"]),
            content="這次模型回覆失敗。",
            operation_status="failed",
            metadata={"response_status": "failed", "llm_call": failed_chat_call},
        )
    )
    # 同一失敗呼叫也會寫入 audit log，correlation id 應避免重複計費。
    repository.log_research(
        ResearchLog(
            session_id=initialized["session_id"],
            action_type="response_generation_failed",
            payload={"llm_call": failed_chat_call},
        )
    )
    failed_opening_call = {
        **client.app.state.llm_provider._llm_metadata("failed_opening")["llm_call"],
        "correlation_id": "failed-opening-call",
    }
    repository.log_research(
        ResearchLog(
            session_id=initialized["session_id"],
            action_type="task_submission_failed",
            payload={"llm_call": failed_opening_call},
        )
    )

    response = client.get(
        f"/api/admin/sessions/{initialized['session_id']}/research",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    stats = response.json()["stats"]
    assert stats["llm_calls_total"] == 5
    assert stats["llm_calls_with_usage"] == 5
    assert stats["total_tokens"] == 90
    assert stats["estimated_cost_usd"] is None
    assert stats["cost_usage_complete"] is False
    assert stats["token_usage_complete"] is False
    assert stats["token_usage_coverage"] == 0.8333
    rows = stats["usage_breakdown"]
    assert sum(row["requests"] for row in rows) == 6
    assert sum(row["total_tokens"] for row in rows) == 90
    assert round(sum(row["estimated_known_cost_usd"] for row in rows), 6) == 0.0005
    assert sum(row["cost_reported_requests"] for row in rows) == 5


def test_session_export_keeps_the_participant_bound_when_auth_mapping_changes(client):
    initialized, _result = _prepare_conversation(client)
    repository = client.app.state.repository
    original = repository.get_participant_by_auth_user("participant-001")
    assert original is not None

    original.auth_user_id = None
    repository.save_participant(original)
    repository.save_participant(
        Participant(
            code="PNEW",
            auth_user_id="participant-001",
            condition_list=[condition_code_for_key("no_ebl_no_roleplay")],
        )
    )

    response = client.get(
        f"/api/admin/sessions/{initialized['session_id']}/research",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["participant_code"] == "PTEST"
    assert response.json()["participant_bound"] is True


def test_admin_research_export_is_anonymized_and_supports_json_and_csv(client):
    initialized, _result = _prepare_conversation(client)

    exported_json = client.get("/api/admin/research-export?format=json", headers=ADMIN_HEADERS)
    assert exported_json.status_code == 200
    raw_json = exported_json.text
    assert "participant-001" not in raw_json
    records = json.loads(raw_json)
    target = next(record for record in records if record["session"]["id"] == initialized["session_id"])
    assert target["participant_code"] == "PTEST"
    assert target["stats"]["total_tokens"] == 54
    assert target["messages"][1]["content"] == "請說明這個事件的背景。"

    exported_csv = client.get("/api/admin/research-export?format=csv", headers=ADMIN_HEADERS)
    assert exported_csv.status_code == 200
    assert "text/csv" in exported_csv.headers["content-type"]
    assert "PTEST" in exported_csv.text
    assert "請說明這個事件的背景。" in exported_csv.text
    assert "0.0003" in exported_csv.text
    assert "participant-001" not in exported_csv.text
    rows = list(csv.DictReader(io.StringIO(exported_csv.text.lstrip("\ufeff"))))
    target_rows = [row for row in rows if row["session_id"] == initialized["session_id"]]
    assert len(target_rows) == 3
    assert target_rows[1]["round_trip_index"] == "1"
    assert target_rows[2]["round_trip_status"] == "completed"
    assert target_rows[1]["round_trip_response_seconds"] != ""
    assert target_rows[2]["assistant_average_tokens"] == "18.0"
    assert int(target_rows[1]["message_characters"]) == len("請說明這個事件的背景。")
    assert json.loads(target_rows[2]["learning_questions_json"]) == target["stats"]["learning"]["questions"] or (
        # A still-running question's observed duration can advance between exports.
        [q["question_id"] for q in json.loads(target_rows[2]["learning_questions_json"])]
        == [q["question_id"] for q in target["stats"]["learning"]["questions"]]
    )


def test_admin_test_session_is_replayable_but_excluded_from_formal_export(client):
    """Admin 測試可供後台檢查，但不得進入正式 JSON/CSV 研究資料。"""
    initialized = client.post(
        "/api/event/initialize",
        headers=ADMIN_HEADERS,
        json={
            "event_name": "Admin test 匯出隔離測試",
            "condition_key": "no_ebl_no_roleplay",
            "rebuild": False,
            "user_id": "admin-test-session",
        },
    )
    assert initialized.status_code == 200
    session_id = initialized.json()["session_id"]

    replay = client.get(
        f"/api/admin/sessions/{session_id}/research",
        headers=ADMIN_HEADERS,
    )
    assert replay.status_code == 200
    assert replay.json()["participant_code"] == "ADMIN_TEST"
    assert replay.json()["participant_bound"] is False
    assert replay.json()["session"]["is_admin_test"] is True

    exported_json = client.get("/api/admin/research-export?format=json", headers=ADMIN_HEADERS)
    assert exported_json.status_code == 200
    assert session_id not in {record["session"]["id"] for record in json.loads(exported_json.text)}

    exported_csv = client.get("/api/admin/research-export?format=csv", headers=ADMIN_HEADERS)
    assert exported_csv.status_code == 200
    assert session_id not in exported_csv.text


def test_research_routes_require_admin_key_and_restart_captures_new_snapshot(client):
    initialized, _result = _prepare_conversation(client)

    denied = client.get(f"/api/admin/sessions/{initialized['session_id']}/research")
    assert denied.status_code == 401

    restarted = client.post(
        f"/api/admin/sessions/{initialized['session_id']}/restart",
        headers=ADMIN_HEADERS,
    )
    assert restarted.status_code == 200
    new_session_id = restarted.json()["new_session"]["id"]
    replay = client.get(
        f"/api/admin/sessions/{new_session_id}/research",
        headers=ADMIN_HEADERS,
    )
    assert replay.status_code == 200
    assert replay.json()["participant_code"] == "PTEST"
    assert replay.json()["participant_bound"] is True
    assert replay.json()["material_snapshot"]["status"] == "captured"
    assert replay.json()["material_snapshot"]["hash_verified"] is True
