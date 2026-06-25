def initialize_event(client, event_name="法國大革命", condition_key="ebl_roleplay") -> dict:
    response = client.post(
        "/api/event/initialize",
        json={"event_name": event_name, "condition_key": condition_key, "rebuild": False},
    )
    assert response.status_code == 200
    return response.json()


def test_admin_prompt_preview_returns_runtime_prompt_modules(client):
    initialized = initialize_event(client)

    response = client.get(
        "/api/admin/prompt-preview",
        headers={"x-admin-key": "test-admin"},
        params={
            "event_id": initialized["event_id"],
            "condition_key": "ebl_roleplay",
            "persona_id": initialized["personas"][0]["id"],
            "sample_user_message": "請說明這個事件的重要性。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    module_names = [module["name"] for module in payload["modules"]]
    assert payload["event"]["id"] == initialized["event_id"]
    assert payload["condition"]["condition_key"] == "ebl_roleplay"
    assert payload["persona"]["id"] == initialized["personas"][0]["id"]
    assert "backend_teacher_prompt" in module_names
    assert "speaker_context" in module_names
    assert "請說明這個事件的重要性。" in payload["prompt"]
    assert "[event_context]" in payload["prompt"]


def test_admin_prompt_preview_generic_condition_does_not_require_persona(client):
    initialized = initialize_event(client, condition_key="no_ebl_no_roleplay")

    response = client.get(
        "/api/admin/prompt-preview",
        headers={"x-admin-key": "test-admin"},
        params={
            "event_id": initialized["event_id"],
            "condition_key": "no_ebl_no_roleplay",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["persona"] is None
    assert "generic AI tutor" in payload["prompt"]


def test_admin_prompt_preview_requires_valid_admin_key(client):
    initialized = initialize_event(client)

    response = client.get(
        "/api/admin/prompt-preview",
        headers={"x-admin-key": "wrong"},
        params={
            "event_id": initialized["event_id"],
            "condition_key": "ebl_roleplay",
        },
    )

    assert response.status_code == 401
