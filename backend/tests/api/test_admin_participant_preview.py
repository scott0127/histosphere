from datetime import timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.models.domain import Participant, utc_now
from tests.api.test_posttest import finish_posttest
from tests.test_api import initialize_event


ADMIN_HEADERS = {"x-admin-key": "test-admin"}


def assigned_participant(client):
    repository = client.app.state.repository
    participant = repository.get_participant_by_auth_user("participant-001")
    participant.condition_list = ["02", "04"]
    return repository.save_participant(participant)


def preview_url(participant):
    return f"/api/admin/participants/{participant.id}/preview"


def preview_initialize(client, participant, event_name, condition_key="ebl_no_roleplay", **overrides):
    return client.post(
        "/api/event/initialize",
        headers=ADMIN_HEADERS,
        json={
            "event_name": event_name,
            "condition_key": condition_key,
            "preview_participant_id": participant.id,
            # The server must not let this contaminate the actual participant's progress.
            "user_id": participant.auth_user_id,
            **overrides,
        },
    )


def test_preview_requires_admin_and_active_source_participant(client):
    participant = assigned_participant(client)
    material = initialize_event(client, "預覽權限", "ebl_no_roleplay")
    assert client.get(preview_url(participant)).status_code == 401
    denied = client.post("/api/event/initialize", json={
        "event_name": material["event"]["canonical_name"],
        "condition_key": "ebl_no_roleplay",
        "preview_participant_id": participant.id,
    })
    assert denied.status_code == 403
    assert "Only an admin" in denied.json()["detail"]
    assert client.get("/api/admin/participants/missing/preview", headers=ADMIN_HEADERS).status_code == 404
    assert preview_initialize(client, participant, "預覽權限", preview_participant_id="missing").status_code == 404
    assert len(client.app.state.repository.list_sessions()) == 1


@pytest.mark.parametrize("participant_status", ["archived", "excluded", "completed"])
def test_preview_rejects_inactive_participant_on_load_and_start(client, participant_status):
    participant = assigned_participant(client)
    initialize_event(client, "非啟用受測者預覽", "ebl_no_roleplay")
    participant.status = participant_status
    client.app.state.repository.save_participant(participant)
    assert client.get(preview_url(participant), headers=ADMIN_HEADERS).status_code == 403
    assert preview_initialize(client, participant, "非啟用受測者預覽").status_code == 403
    assert len(client.app.state.repository.list_sessions()) == 1


def test_preview_uses_stable_isolated_identity_resumes_and_audits_assignment(client):
    participant = assigned_participant(client)
    repository = client.app.state.repository
    source_before = participant.model_dump()
    material = initialize_event(client, "草稿指派預覽", "ebl_no_roleplay")
    assert material["event"]["materials_locked_at"] is None
    first_load = client.get(preview_url(participant), headers=ADMIN_HEADERS).json()
    assert first_load["participant"]["condition_list"] == ["02", "04"]
    assert first_load["progress"] == []
    test_user_id = first_load["test_user_id"]
    assert UUID(test_user_id).version == 5
    assert test_user_id != participant.auth_user_id

    started = preview_initialize(client, participant, "草稿指派預覽")
    assert started.status_code == 200, started.text
    session_id = started.json()["session_id"]
    session = repository.get_session(session_id)
    assert (session.user_id, session.participant_id, session.is_admin_test) == (test_user_id, None, True)
    resumed = preview_initialize(client, participant, "草稿指派預覽", user_id="spoofed-other-user")
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["session_id"] == session_id
    assert repository.get_session(session_id).participant_id is None
    assert len(repository.list_sessions_for_user(test_user_id)) == 1
    assert repository.list_sessions_for_user(participant.auth_user_id) == []
    assert repository.get_participant(participant.id).model_dump() == source_before

    loaded = client.get(preview_url(participant), headers=ADMIN_HEADERS).json()
    assert loaded["test_user_id"] == test_user_id
    assert [item["session_id"] for item in loaded["progress"]] == [session_id]
    assert client.get("/api/sessions/progress").json()["progress"] == []
    logs = [log for log in repository.list_research_logs() if log.session_id == session_id
            and log.action_type in {"event_initialized", "event_session_resumed"}]
    assert {log.action_type for log in logs} == {"event_initialized", "event_session_resumed"}
    assert all(log.payload["preview_participant_id"] == participant.id for log in logs)
    assert all(log.payload["preview_condition_list"] == ["02", "04"] for log in logs)

    other = repository.save_participant(Participant(code="OTHER", condition_list=["02", "04"]))
    other_preview = client.get(preview_url(other), headers=ADMIN_HEADERS).json()
    assert other_preview["test_user_id"] != test_user_id
    assert other_preview["progress"] == []


def test_preview_enforces_assignment_order_resume_and_actual_posttest_gate(client):
    participant = assigned_participant(client)
    repository = client.app.state.repository
    initialize_event(client, "預覽第一輪", "ebl_no_roleplay")
    initialize_event(client, "預覽第二輪", "ebl_roleplay")
    assert preview_initialize(client, participant, "預覽第一輪", "no_ebl_no_roleplay").status_code == 403
    assert preview_initialize(client, participant, "預覽第一輪", "no_ebl_roleplay").status_code == 403
    skipped = preview_initialize(client, participant, "預覽第二輪", "ebl_roleplay")
    assert skipped.status_code == 409
    assert "must complete Condition 02 before Condition 04" in skipped.json()["detail"]

    started = preview_initialize(client, participant, "預覽第一輪")
    assert started.status_code == 200, started.text
    initialized = started.json()
    blocked = preview_initialize(client, participant, "預覽第二輪", "ebl_roleplay")
    assert blocked.status_code == 409
    assert "must resume Condition 02" in blocked.json()["detail"]

    admin_client = TestClient(client.app, headers=ADMIN_HEADERS)
    accepted = admin_client.post(f"/api/tasks/{initialized['task']['id']}/submit", json={
        "session_id": initialized["session_id"],
        "user_id": repository.get_session(initialized["session_id"]).user_id,
        "response_payload": {"answer_text": "我先依原先的理解提出答案。"},
    })
    assert accepted.status_code == 202, accepted.text
    polled = admin_client.get(accepted.json()["poll_url"])
    assert polled.status_code == 200, polled.text
    submitted = polled.json()["result"]
    assert submitted
    session = repository.get_session(initialized["session_id"])
    session.timer_ends_at = utc_now() - timedelta(seconds=1)
    repository.save_session(session)
    state = admin_client.get(f"/api/sessions/{session.id}/state").json()
    closure = state["closure"]
    assert closure is not None
    assert preview_initialize(client, participant, "預覽第二輪", "ebl_roleplay").status_code == 409
    closed = admin_client.post(f"/api/sessions/{session.id}/closure", json={
        "closure_id": closure["closure_id"], "reflection": "我依材料檢查原先答案，再重新說明理由。",
    })
    assert closed.status_code == 200, closed.text
    assert preview_initialize(client, participant, "預覽第二輪", "ebl_roleplay").status_code == 409
    posttest_url = f"/api/sessions/{session.id}/posttest"
    assert finish_posttest(admin_client, posttest_url)["response"]["stage"] == "completed"
    progress = client.get(preview_url(participant), headers=ADMIN_HEADERS).json()["progress"]
    assert progress[0]["posttest_stage"] == "completed"
    second = preview_initialize(client, participant, "預覽第二輪", "ebl_roleplay")
    assert second.status_code == 200, second.text
    assert repository.get_session(second.json()["session_id"]).participant_id is None
    assert repository.get_task_attempt(submitted["attempt_id"]).user_id == session.user_id
    assert repository.get_conversation(submitted["conversation_id"]).user_id == session.user_id
    assert repository.list_sessions_for_user(participant.auth_user_id) == []
    assert client.get("/api/sessions/progress").json()["progress"] == []
    assert client.get("/api/admin/research-export?format=json", headers=ADMIN_HEADERS).json() == []


def test_preview_does_not_create_materials_and_excludes_archived_progress(client):
    participant = assigned_participant(client)
    repository = client.app.state.repository
    assert preview_initialize(client, participant, "不存在的事件").status_code == 404
    assert repository.find_event_by_name("不存在的事件") is None
    assert repository.list_sessions() == []
    material = initialize_event(client, "預覽封存測試", "ebl_no_roleplay")
    started = preview_initialize(client, participant, "預覽封存測試")
    old_session = repository.get_session(started.json()["session_id"])
    old_session.status = "archived"
    repository.save_session(old_session)
    assert client.get(preview_url(participant), headers=ADMIN_HEADERS).json()["progress"] == []
    restarted = preview_initialize(client, participant, "預覽封存測試")
    assert restarted.status_code == 200
    assert restarted.json()["session_id"] != old_session.id
    progress = client.get(preview_url(participant), headers=ADMIN_HEADERS).json()["progress"]
    assert [item["session_id"] for item in progress] == [restarted.json()["session_id"]]
    assert repository.get_session(old_session.id).status == "archived"
    event = repository.get_event(material["event_id"])
    event.archived_at = utc_now()
    repository.save_event(event)
    assert preview_initialize(client, participant, "預覽封存測試").status_code == 409


def test_preview_and_formal_progress_are_mutually_isolated_and_assignment_is_fresh(client):
    participant = assigned_participant(client)
    repository = client.app.state.repository
    material = initialize_event(client, "正式與預覽隔離", "ebl_no_roleplay")
    assert client.post(f"/api/admin/events/{material['event_id']}/material-lock",
                       headers=ADMIN_HEADERS, json={"locked": True}).status_code == 200
    formal = client.post("/api/event/initialize", json={
        "event_name": "正式與預覽隔離", "condition_key": "ebl_no_roleplay",
    })
    assert formal.status_code == 200, formal.text
    formal_session = repository.get_session(formal.json()["session_id"])
    formal_before = formal_session.model_dump()
    preview = preview_initialize(client, participant, "正式與預覽隔離")
    assert preview.status_code == 200, preview.text
    assert preview.json()["session_id"] != formal_session.id
    assert repository.get_session(formal_session.id).model_dump() == formal_before
    assert [item["session_id"] for item in client.get("/api/sessions/progress").json()["progress"]] == [formal_session.id]
    progress = client.get(preview_url(participant), headers=ADMIN_HEADERS).json()["progress"]
    assert [item["session_id"] for item in progress] == [preview.json()["session_id"]]
    exported = client.get("/api/admin/research-export?format=json", headers=ADMIN_HEADERS).json()
    assert [row["session"]["id"] for row in exported] == [formal_session.id]
    assert client.get(f"/api/sessions/{preview.json()['session_id']}/state").status_code == 403

    participant.condition_list = ["04"]
    repository.save_participant(participant)
    assert client.get(preview_url(participant), headers=ADMIN_HEADERS).json()["participant"]["condition_list"] == ["04"]
    assert preview_initialize(client, participant, "正式與預覽隔離").status_code == 403
    assert repository.get_session(formal_session.id).model_dump() == formal_before
