"""Admin 研究資料重播與匯出的整合測試。"""

import json


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
    completed = client.get(accepted.json()["poll_url"])
    assert completed.status_code == 200
    result = completed.json()["result"]
    assert result

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
        "prompt_tokens": 22,
        "completion_tokens": 14,
        "total_tokens": 36,
        "llm_messages_total": 2,
        "llm_messages_with_usage": 2,
        "token_usage_coverage": 1.0,
        "token_usage_complete": True,
    }
    assert payload["material_snapshot"]["status"] == "captured"
    assert payload["material_snapshot"]["hash_verified"] is True
    assert len(payload["prompt_records"]) == 2
    assert all(record["hash_verified"] for record in payload["prompt_records"])
    assert {record["stage"] for record in payload["prompt_records"]} == {
        "conversation_opening",
        "chat_response",
    }


def test_admin_research_export_is_anonymized_and_supports_json_and_csv(client):
    initialized, _result = _prepare_conversation(client)

    exported_json = client.get("/api/admin/research-export?format=json", headers=ADMIN_HEADERS)
    assert exported_json.status_code == 200
    raw_json = exported_json.text
    assert "participant-001" not in raw_json
    records = json.loads(raw_json)
    target = next(record for record in records if record["session"]["id"] == initialized["session_id"])
    assert target["participant_code"] == "PTEST"
    assert target["stats"]["total_tokens"] == 36
    assert target["messages"][1]["content"] == "請說明這個事件的背景。"

    exported_csv = client.get("/api/admin/research-export?format=csv", headers=ADMIN_HEADERS)
    assert exported_csv.status_code == 200
    assert "text/csv" in exported_csv.headers["content-type"]
    assert "PTEST" in exported_csv.text
    assert "請說明這個事件的背景。" in exported_csv.text
    assert "participant-001" not in exported_csv.text


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
    assert replay.json()["material_snapshot"]["status"] == "captured"
    assert replay.json()["material_snapshot"]["hash_verified"] is True
