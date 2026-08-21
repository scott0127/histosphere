def admin_headers() -> dict[str, str]:
    return {"x-admin-key": "test-admin"}


def test_admin_creates_participant_with_unique_code_and_auth_binding(client):
    response = client.post(
        "/api/admin/participants",
        headers=admin_headers(),
        json={
            "code": " p006 ",
            "auth_user_id": "participant-006",
            "condition_list": ["04", "01"],
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["code"] == "P006"
    assert created["auth_user_id"] == "participant-006"
    assert created["condition_list"] == ["04", "01"]
    assert created["status"] == "active"

    duplicate_code = client.post(
        "/api/admin/participants",
        headers=admin_headers(),
        json={"code": "p006"},
    )
    assert duplicate_code.status_code == 409

    duplicate_auth = client.post(
        "/api/admin/participants",
        headers=admin_headers(),
        json={"code": "P007", "auth_user_id": "participant-006"},
    )
    assert duplicate_auth.status_code == 409

    no_admin_key = client.post("/api/admin/participants", json={"code": "P008"})
    assert no_admin_key.status_code == 401


def test_archive_blocks_learner_but_preserves_binding_and_admin_access(client):
    initialized = client.post(
        "/api/event/initialize",
        headers=admin_headers(),
        json={
            "event_name": "受測者封存測試事件",
            "condition_key": "no_ebl_no_roleplay",
            "rebuild": False,
            "user_id": "participant-001",
        },
    )
    assert initialized.status_code == 200
    session_id = initialized.json()["session_id"]
    assert client.get(f"/api/sessions/{session_id}/state").status_code == 200

    repository = client.app.state.repository
    participant = repository.get_participant_by_auth_user("participant-001")
    archived = client.post(
        f"/api/admin/participants/{participant.id}/archive",
        headers=admin_headers(),
    )

    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert archived.json()["auth_user_id"] == "participant-001"
    assert repository.get_session(session_id) is not None

    assert client.get("/api/participants/me").status_code == 403
    assert client.get(f"/api/sessions/{session_id}/state").status_code == 403
    assert client.post(
        "/api/event/initialize",
        json={
            "event_name": "受測者封存測試事件",
            "condition_key": "no_ebl_no_roleplay",
            "rebuild": False,
            "user_id": "participant-001",
        },
    ).status_code == 403

    admin_view = client.get(
        "/api/participants/me",
        headers=admin_headers(),
        params={"auth_user_id": "participant-001"},
    )
    assert admin_view.status_code == 200
    assert admin_view.json()["participant"]["status"] == "archived"

    restored = client.post(
        f"/api/admin/participants/{participant.id}/restore",
        headers=admin_headers(),
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"
    assert restored.json()["auth_user_id"] == "participant-001"
    assert client.get(f"/api/sessions/{session_id}/state").status_code == 200

    action_types = [log.action_type for log in repository.list_research_logs()]
    assert "participant_archived" in action_types
    assert "participant_restored" in action_types
