from app.models.domain import ExperimentSession


ADMIN_HEADERS = {"x-admin-key": "test-admin"}


def _create_materials(client, event_name: str) -> dict:
    response = client.post(
        "/api/event/initialize",
        headers=ADMIN_HEADERS,
        json={"event_name": event_name, "condition_key": "ebl_roleplay", "rebuild": False},
    )
    assert response.status_code == 200
    return response.json()


def _set_lock(client, event_id: str, locked: bool):
    return client.post(
        f"/api/admin/events/{event_id}/material-lock",
        headers=ADMIN_HEADERS,
        json={"locked": locked},
    )


def test_material_lock_controls_learner_visibility_and_blocks_all_material_edits(client):
    material = _create_materials(client, "素材鎖定測試")
    event_id = material["event_id"]
    task_id = material["task"]["id"]
    persona_id = material["personas"][0]["id"]

    assert not any(event["id"] == event_id for event in client.get("/api/events").json())
    unavailable = client.post(
        "/api/event/initialize",
        json={"event_name": "素材鎖定測試", "condition_key": "ebl_roleplay", "rebuild": False},
    )
    assert unavailable.status_code == 409

    locked = _set_lock(client, event_id, True)
    assert locked.status_code == 200
    assert locked.json()["materials_locked_at"]
    assert any(event["id"] == event_id for event in client.get("/api/events").json())

    learner = client.post(
        "/api/event/initialize",
        json={"event_name": "素材鎖定測試", "condition_key": "ebl_roleplay", "rebuild": False},
    )
    assert learner.status_code == 200

    assert client.patch(
        f"/api/admin/events/{event_id}",
        headers=ADMIN_HEADERS,
        json={"description": "不應寫入"},
    ).status_code == 409
    assert client.patch(
        f"/api/admin/tasks/{task_id}",
        headers=ADMIN_HEADERS,
        json={"title": "不應寫入"},
    ).status_code == 409
    assert client.patch(
        f"/api/admin/personas/{persona_id}",
        headers=ADMIN_HEADERS,
        json={"biography": "不應寫入"},
    ).status_code == 409
    assert client.post(
        "/api/personas",
        headers=ADMIN_HEADERS,
        json={"event_id": event_id, "name": "不應建立", "active": False},
    ).status_code == 409

    lock_log = next(
        log
        for log in client.app.state.repository.list_research_logs()
        if log.event_id == event_id and log.action_type == "event_materials_locked"
    )
    assert lock_log.payload["changes"]["materials_locked_at"]


def test_material_unlock_rejects_active_participant_session_but_allows_admin_test_session(client):
    material = _create_materials(client, "素材解除鎖定測試")
    event_id = material["event_id"]
    assert _set_lock(client, event_id, True).status_code == 200

    # 純 Admin 測試 Session 不會阻塞素材維護。
    assert _set_lock(client, event_id, False).status_code == 200
    assert _set_lock(client, event_id, True).status_code == 200

    learner = client.post(
        "/api/event/initialize",
        json={"event_name": "素材解除鎖定測試", "condition_key": "ebl_roleplay", "rebuild": False},
    )
    assert learner.status_code == 200
    learner_session = learner.json()["session_id"]

    blocked = _set_lock(client, event_id, False)
    assert blocked.status_code == 409
    assert "Active experiment sessions" in blocked.json()["detail"]

    repository = client.app.state.repository
    session = repository.get_session(learner_session)
    assert isinstance(session, ExperimentSession)
    session.status = "archived"
    repository.save_session(session)

    unlocked = _set_lock(client, event_id, False)
    assert unlocked.status_code == 200
    assert unlocked.json()["materials_locked_at"] is None
