from app.core.experiment_conditions import condition_code_for_key


def initialize_event(client, event_name="法國大革命", condition_key="ebl_roleplay", user_id="participant-001"):
    created = client.post(
        "/api/event/initialize",
        json={
            "event_name": event_name,
            "condition_key": condition_key,
            "rebuild": False,
        },
        headers={"x-admin-key": "test-admin"},
    )
    assert created.status_code == 200
    created_payload = created.json()

    locked = client.post(
        f"/api/admin/events/{created_payload['event_id']}/material-lock",
        headers={"x-admin-key": "test-admin"},
        json={"locked": True},
    )
    assert locked.status_code == 200

    repository = client.app.state.repository
    participant = repository.get_participant_by_auth_user(user_id)
    assigned = client.patch(
        f"/api/admin/participants/{participant.id}",
        headers={"x-admin-key": "test-admin"},
        json={"condition_list": [condition_code_for_key(condition_key)]},
    )
    assert assigned.status_code == 200

    response = client.post(
        "/api/event/initialize",
        json={
            "event_name": created_payload["event"]["canonical_name"],
            "condition_key": condition_key,
            "rebuild": False,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_route_uuid_contracts_return_validation_errors(client):
    valid_session_id = "11111111-1111-4111-8111-111111111111"

    assert client.get("/api/sessions/not-a-uuid/state").status_code == 422
    assert client.get("/api/conversations/not-a-uuid").status_code == 422
    assert client.patch(
        "/api/tasks/not-a-uuid/draft",
        json={
            "session_id": valid_session_id,
            "response_payload": {},
        },
    ).status_code == 422
    assert client.post(
        "/api/tasks/not-a-uuid/submit",
        json={
            "session_id": valid_session_id,
            "response_payload": {},
        },
    ).status_code == 422


def test_session_state_progress_and_task_draft_follow_frontend_recovery_contract(client):
    initialized = initialize_event(client)

    empty_state = client.get(f"/api/sessions/{initialized['session_id']}/state")
    assert empty_state.status_code == 200
    empty_payload = empty_state.json()
    assert empty_payload["session"]["id"] == initialized["session_id"]
    assert empty_payload["event"]["id"] == initialized["event_id"]
    assert empty_payload["task"]["id"] == initialized["task"]["id"]
    assert empty_payload["attempt"] is None
    assert empty_payload["conversation_id"] is None

    draft = client.patch(
        f"/api/tasks/{initialized['task']['id']}/draft",
        json={
            "session_id": initialized["session_id"],
            "user_id": "participant-001",
            "response_payload": {
                "answers": [
                    {
                        "question_id": "q01",
                        "blank_id": "q01",
                        "type": "cloze",
                        "prompt": "請填入一個核心問題。",
                        "value": "制度危機",
                    }
                ]
            },
        },
    )
    assert draft.status_code == 200
    assert draft.json()["attempt"]["status"] == "in_progress"

    draft_state = client.get(f"/api/sessions/{initialized['session_id']}/state")
    draft_payload = draft_state.json()
    assert draft_payload["attempt"]["status"] == "in_progress"
    assert draft_payload["attempt"]["response_payload"]["answers"][0]["value"] == "制度危機"
    assert draft_payload["conversation_id"] is None

    progress = client.get("/api/sessions/progress", params={"user_id": "participant-001"})
    assert progress.status_code == 200
    progress_item = progress.json()["progress"][0]
    assert progress_item["event_id"] == initialized["event_id"]
    assert progress_item["condition_key"] == "ebl_roleplay"
    assert progress_item["session_id"] == initialized["session_id"]
    assert progress_item["task_id"] == initialized["task"]["id"]
    assert progress_item["status"] == "task_draft"


def test_submit_transitions_session_to_conversation_started(client):
    initialized = initialize_event(client, event_name="霧社事件", condition_key="no_ebl_no_roleplay")

    submitted = client.post(
        f"/api/tasks/{initialized['task']['id']}/submit",
        json={
            "session_id": initialized["session_id"],
            "user_id": "participant-001",
            "response_payload": {
                "answer_text": "霧社事件需要放在殖民治理、警察制度、族群關係與抵抗行動中理解。",
            },
        },
    )
    assert submitted.status_code == 202
    accepted_payload = submitted.json()
    polled = client.get(accepted_payload["poll_url"])
    assert polled.status_code == 200
    submitted_payload = polled.json()["result"]
    assert submitted_payload["conversation_id"]
    assert submitted_payload["attempt"]["status"] == "submitted"
    assert submitted_payload["history"][0]["speaker_type"] == "assistant"

    state = client.get(f"/api/sessions/{initialized['session_id']}/state")
    assert state.status_code == 200
    state_payload = state.json()
    assert state_payload["session"]["status"] == "conversation_started"
    assert state_payload["conversation_id"] == submitted_payload["conversation_id"]
    assert state_payload["attempt"]["id"] == submitted_payload["attempt_id"]

    progress = client.get("/api/sessions/progress", params={"user_id": "participant-001"})
    assert progress.status_code == 200
    progress_item = progress.json()["progress"][0]
    assert progress_item["conversation_id"] == submitted_payload["conversation_id"]
    assert progress_item["status"] == "chat_started"
