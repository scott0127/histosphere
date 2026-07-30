import pytest
from fastapi.testclient import TestClient

from app.core import config


def _admin_initialize(client: TestClient, event_name: str = "JWT 身分邊界測試") -> dict:
    response = client.post(
        "/api/event/initialize",
        json={
            "event_name": event_name,
            "condition_key": "ebl_roleplay",
            "rebuild": False,
            "user_id": "participant-001",
        },
        headers={"x-admin-key": "test-admin"},
    )
    assert response.status_code == 200
    return response.json()


def test_admin_key_is_required_from_environment(monkeypatch):
    monkeypatch.setattr(config, "load_local_env", lambda: None)
    monkeypatch.delenv("HISTOSPHERE_ADMIN_KEY", raising=False)
    config.get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="HISTOSPHERE_ADMIN_KEY"):
        config.get_settings()

    config.get_settings.cache_clear()


def test_learner_routes_require_bearer_but_public_catalog_stays_public(client):
    unauthenticated = TestClient(client.app)

    assert unauthenticated.get("/api/events").status_code == 200
    assert unauthenticated.get("/api/conditions").status_code == 200
    assert unauthenticated.get("/api/participants/me").status_code == 401
    assert unauthenticated.get("/api/sessions/progress", params={"user_id": "participant-001"}).status_code == 401


def test_jwt_identity_overrides_stale_request_user_ids_and_blocks_cross_account_access(client):
    material = _admin_initialize(client)

    initialized = client.post(
        "/api/event/initialize",
        json={
            "event_name": material["event"]["canonical_name"],
            "condition_key": "ebl_roleplay",
            "rebuild": False,
            "user_id": "stale-browser-user",
        },
    )
    assert initialized.status_code == 200
    session_id = initialized.json()["session_id"]
    task_id = initialized.json()["task"]["id"]

    state = client.get(f"/api/sessions/{session_id}/state")
    assert state.status_code == 200
    assert state.json()["session"]["user_id"] == "participant-001"

    participant = client.get("/api/participants/me", params={"auth_user_id": "stale-browser-user"})
    assert participant.status_code == 200
    assert participant.json()["participant"]["auth_user_id"] == "participant-001"

    progress = client.get("/api/sessions/progress", params={"user_id": "stale-browser-user"})
    assert progress.status_code == 200
    assert any(item["session_id"] == session_id for item in progress.json()["progress"])

    draft = client.patch(
        f"/api/tasks/{task_id}/draft",
        json={
            "session_id": session_id,
            "user_id": "stale-browser-user",
            "response_payload": {"answers": [{"question_id": "q01", "value": "test"}]},
        },
    )
    assert draft.status_code == 200
    attempt_id = draft.json()["attempt"]["id"]
    assert draft.json()["attempt"]["user_id"] == "participant-001"

    other_user_headers = {"Authorization": "Bearer participant-002"}
    assert client.get(f"/api/sessions/{session_id}/state", headers=other_user_headers).status_code == 403
    assert client.get(f"/api/tasks/attempts/{attempt_id}", headers=other_user_headers).status_code == 403


def test_jwt_blocks_cross_account_conversation_reads_and_chat_writes(client):
    material = _admin_initialize(client, "JWT 對話 ownership 測試")
    initialized = client.post(
        "/api/event/initialize",
        json={
            "event_name": material["event"]["canonical_name"],
            "condition_key": "ebl_roleplay",
            "rebuild": False,
        },
    )
    assert initialized.status_code == 200

    submitted = client.post(
        f"/api/tasks/{initialized.json()['task']['id']}/submit",
        json={
            "session_id": initialized.json()["session_id"],
            "response_payload": {"answer_text": "測試回答"},
        },
    )
    assert submitted.status_code == 202
    completed = client.get(submitted.json()["poll_url"])
    assert completed.status_code == 200
    conversation_id = completed.json()["result"]["conversation_id"]
    owner_chat = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "user_message": "建立一筆可查詢狀態的對話回合",
            "client_request_id": "ownership-operation-001",
        },
    )
    assert owner_chat.status_code == 200

    other_user_headers = {"Authorization": "Bearer participant-002"}
    assert client.get(
        f"/api/conversations/{conversation_id}",
        headers=other_user_headers,
    ).status_code == 403
    assert client.post(
        "/api/chat",
        headers=other_user_headers,
        json={
            "conversation_id": conversation_id,
            "user_message": "嘗試寫入其他帳號的對話",
            "history": [],
        },
    ).status_code == 403
    assert client.get(
        "/api/chat/operations/ownership-operation-001",
        headers=other_user_headers,
        params={"conversation_id": conversation_id},
    ).status_code == 403


def test_admin_key_bypasses_supabase_login_for_management_and_test_mode(client):
    admin_only = TestClient(client.app)
    initialized = admin_only.post(
        "/api/event/initialize",
        json={
            "event_name": "Admin 無 Supabase 登入測試",
            "condition_key": "no_ebl_no_roleplay",
            "rebuild": False,
            "user_id": "admin-test-user",
        },
        headers={"x-admin-key": "test-admin"},
    )
    assert initialized.status_code == 200

    state = admin_only.get(
        f"/api/sessions/{initialized.json()['session_id']}/state",
        headers={"x-admin-key": "test-admin"},
    )
    assert state.status_code == 200
    assert state.json()["session"]["user_id"] == "admin-test-user"
