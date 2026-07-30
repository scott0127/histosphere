"""Admin research log coverage for field-level changes."""


ADMIN_HEADERS = {"x-admin-key": "test-admin"}


def initialize_event(client, event_name: str = "法國大革命") -> dict:
    response = client.post(
        "/api/event/initialize",
        headers=ADMIN_HEADERS,
        json={
            "event_name": event_name,
            "condition_key": "ebl_roleplay",
            "rebuild": False,
        },
    )
    assert response.status_code == 200
    return response.json()


def latest_log(client, action_type: str) -> dict:
    response = client.get("/api/admin/research-logs", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    return next(log for log in response.json() if log["action_type"] == action_type)


def test_admin_material_updates_record_field_level_before_and_after(client):
    initialized = initialize_event(client)
    event = initialized["event"]
    task = initialized["task"]

    event_response = client.patch(
        f"/api/admin/events/{event['id']}",
        headers=ADMIN_HEADERS,
        json={
            "description": "更新後事件介紹",
            # 同值不應被列為實際變更。
            "canonical_name": event["canonical_name"],
        },
    )
    assert event_response.status_code == 200

    event_log = latest_log(client, "event_updated")
    assert event_log["payload"]["updated_fields"] == ["description"]
    assert event_log["payload"]["changes"]["description"] == {
        "before": event["description"],
        "after": "更新後事件介紹",
    }

    task_response = client.patch(
        f"/api/admin/tasks/{task['id']}",
        headers=ADMIN_HEADERS,
        json={"title": "更新後 Task"},
    )
    assert task_response.status_code == 200

    task_log = latest_log(client, "task_updated")
    assert task_log["payload"]["updated_fields"] == ["title"]
    assert task_log["payload"]["changes"]["title"] == {
        "before": task["title"],
        "after": "更新後 Task",
    }


def test_admin_condition_persona_and_participant_updates_are_auditable(client):
    initialized = initialize_event(client, "霧社事件")
    condition = initialized["condition"]
    persona = initialized["personas"][0]
    repository = client.app.state.repository
    participant = repository.get_participant_by_auth_user("participant-001")
    original_participant_notes = participant.notes

    condition_response = client.patch(
        f"/api/admin/conditions/{condition['id']}",
        headers=ADMIN_HEADERS,
        json={"label": "更新後條件名稱"},
    )
    assert condition_response.status_code == 200
    condition_log = latest_log(client, "condition_updated")
    assert condition_log["payload"]["changes"]["label"] == {
        "before": condition["label"],
        "after": "更新後條件名稱",
    }

    persona_response = client.patch(
        f"/api/admin/personas/{persona['id']}",
        headers=ADMIN_HEADERS,
        json={"biography": "更新後人物生平"},
    )
    assert persona_response.status_code == 200
    persona_log = latest_log(client, "persona_updated")
    assert persona_log["payload"]["persona_name"] == persona["name"]
    assert persona_log["payload"]["changes"]["biography"] == {
        "before": persona["biography"],
        "after": "更新後人物生平",
    }

    participant_response = client.patch(
        f"/api/admin/participants/{participant.id}",
        headers=ADMIN_HEADERS,
        json={"notes": "更新後研究備註"},
    )
    assert participant_response.status_code == 200
    participant_log = latest_log(client, "participant_updated")
    assert participant_log["payload"]["participant_code"] == participant.code
    assert participant_log["payload"]["changes"]["notes"] == {
        "before": original_participant_notes,
        "after": "更新後研究備註",
    }


def test_admin_archive_and_restore_records_state_changes(client):
    initialized = initialize_event(client, "事件封存稽核")
    event_id = initialized["event_id"]

    archived = client.post(
        f"/api/admin/events/{event_id}/archive",
        headers=ADMIN_HEADERS,
    )
    assert archived.status_code == 200
    archive_log = latest_log(client, "event_archived")
    assert archive_log["payload"]["changes"]["archived_at"]["before"] is None
    assert archive_log["payload"]["changes"]["archived_at"]["after"]

    restored = client.post(
        f"/api/admin/events/{event_id}/restore",
        headers=ADMIN_HEADERS,
    )
    assert restored.status_code == 200
    restore_log = latest_log(client, "event_restored")
    assert restore_log["payload"]["changes"]["archived_at"]["before"]
    assert restore_log["payload"]["changes"]["archived_at"]["after"] is None


def test_admin_persona_archive_and_restore_records_state_changes(client):
    initialized = initialize_event(client, "人物封存稽核")
    persona_id = initialized["personas"][0]["id"]

    archived = client.delete(
        f"/api/personas/{persona_id}",
        headers=ADMIN_HEADERS,
    )
    assert archived.status_code == 200
    archive_log = latest_log(client, "persona_archived")
    assert archive_log["payload"]["changes"]["active"] == {
        "before": True,
        "after": False,
    }
    assert archive_log["payload"]["changes"]["archived_at"]["before"] is None
    assert archive_log["payload"]["changes"]["archived_at"]["after"]

    restored = client.post(
        f"/api/personas/{persona_id}/restore",
        headers=ADMIN_HEADERS,
    )
    assert restored.status_code == 200
    restore_log = latest_log(client, "persona_restored")
    assert restore_log["payload"]["changes"]["archived_at"]["before"]
    assert restore_log["payload"]["changes"]["archived_at"]["after"] is None
