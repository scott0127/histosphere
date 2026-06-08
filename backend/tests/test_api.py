CONDITIONS = [
    "no_ebl_no_roleplay",
    "ebl_no_roleplay",
    "no_ebl_roleplay",
    "ebl_roleplay",
]


def initialize_event(client, event_name: str = "諾曼第登陸", condition_key: str = "ebl_roleplay") -> dict:
    response = client.post(
        "/api/event/initialize",
        json={"event_name": event_name, "condition_key": condition_key, "rebuild": False},
    )
    assert response.status_code == 200
    return response.json()


def submit_task(client, initialized: dict, answer_text: str = "1944 年盟軍在法國諾曼第登陸，影響西線戰局。") -> dict:
    response = client.post(
        f"/api/tasks/{initialized['task']['id']}/submit",
        json={
            "session_id": initialized["session_id"],
            "response_payload": {"answer_text": answer_text},
        },
    )
    assert response.status_code == 200
    return response.json()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_conditions_are_seeded(client):
    response = client.get("/api/conditions")
    assert response.status_code == 200
    keys = {condition["condition_key"] for condition in response.json()}
    assert set(CONDITIONS).issubset(keys)


def test_event_initialize_creates_workspace_without_conversation(client):
    data = initialize_event(client)

    assert data["event_id"]
    assert data["session_id"]
    assert "conversation_id" not in data
    assert data["event"]["canonical_name"] == "諾曼第登陸"
    assert data["task"]["display_text"]
    assert len(data["personas"]) >= 1
    assert len(data["personas"]) <= 3
    assert data["condition"]["condition_key"] == "ebl_roleplay"


def test_event_check_and_list_events(client):
    initialized = initialize_event(client, "法國大革命")

    check = client.post("/api/event/check", json={"event_name": "法國大革命"})
    assert check.status_code == 200
    assert check.json()["exists"] is True

    events = client.get("/api/events")
    assert events.status_code == 200
    payload = events.json()
    assert len(payload) == 1
    assert payload[0]["id"] == initialized["event_id"]
    assert payload[0]["personas"]
    assert payload[0]["latest_task"]


def test_task_submit_creates_attempt_conversation_messages_and_logs(client):
    initialized = initialize_event(client)
    submitted = submit_task(client, initialized, "短答")

    assert submitted["attempt_id"]
    assert submitted["conversation_id"]
    assert submitted["judgement"]["result"] in {"incorrect", "partial", "correct"}
    assert submitted["history"][0]["speaker_type"] == "persona"
    assert submitted["history"][0]["sequence_index"] == 0

    loaded = client.get(f"/api/conversations/{submitted['conversation_id']}")
    assert loaded.status_code == 200
    payload = loaded.json()
    assert payload["messages"][0]["speaker_name"]
    assert payload["task_attempt"]["id"] == submitted["attempt_id"]

    logs = client.get("/api/admin/research-logs", headers={"x-admin-key": "test-admin"})
    assert logs.status_code == 200
    action_types = {item["action_type"] for item in logs.json()}
    assert {"event_initialized", "task_answer_changed", "task_submitted", "conversation_started"}.issubset(action_types)


def test_chat_policy_matrix(client):
    for condition_key in CONDITIONS:
        initialized = initialize_event(client, f"測試事件 {condition_key}", condition_key)
        submitted = submit_task(client, initialized)
        target_persona_id = initialized["personas"][0]["id"] if "roleplay" in condition_key and not condition_key.startswith("no_ebl_no") else None

        chat = client.post(
            "/api/chat",
            json={
                "conversation_id": submitted["conversation_id"],
                "user_message": "這場事件的重要性是什麼？",
                "history": [],
                "target_persona_id": target_persona_id,
            },
        )
        assert chat.status_code == 200
        payload = chat.json()
        assert payload["response"]
        if initialized["condition"]["roleplay_enabled"]:
            assert payload["selected_persona"]
            assert payload["message"]["speaker_type"] == "persona"
        else:
            assert payload["selected_persona"] is None
            assert payload["message"]["speaker_type"] == "assistant"
        if initialized["condition"]["response_policy"] == "scaffold":
            assert "我先不直接給結論" in payload["response"]
        else:
            assert "直接回答" in payload["response"]

        loaded = client.get(f"/api/conversations/{submitted['conversation_id']}")
        messages = loaded.json()["messages"]
        assert [message["sequence_index"] for message in messages] == list(range(len(messages)))


def test_persona_crud(client):
    initialized = initialize_event(client, "明治維新")
    event_id = initialized["event_id"]

    created = client.post(
        "/api/personas",
        json={
            "event_id": event_id,
            "name": "測試人物",
            "role": "觀察者",
            "biography": "用於測試人物管理的角色。",
            "expertise_areas": ["history"],
            "prompt_profile": {"speaking_style": "calm"},
            "active": True,
        },
    )
    assert created.status_code == 200
    persona = created.json()

    updated = client.patch(
        f"/api/personas/{persona['id']}",
        json={"role": "更新後角色", "active": True},
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "更新後角色"

    listed = client.get(f"/api/personas?event_id={event_id}")
    assert listed.status_code == 200
    assert any(item["id"] == persona["id"] for item in listed.json())

    deleted = client.delete(f"/api/personas/{persona['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["success"] is True


def test_admin_key_protects_mutations(client):
    initialized = initialize_event(client)
    task_id = initialized["task"]["id"]

    denied = client.patch(
        f"/api/admin/tasks/{task_id}",
        json={"title": "新標題"},
        headers={"x-admin-key": "wrong"},
    )
    assert denied.status_code == 401

    allowed = client.patch(
        f"/api/admin/tasks/{task_id}",
        json={"title": "新標題", "revision_state": "teacher_modified"},
        headers={"x-admin-key": "test-admin"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["title"] == "新標題"

    snapshot = client.get("/api/admin/snapshot", headers={"x-admin-key": "test-admin"})
    assert snapshot.status_code == 200
    assert snapshot.json()["conditions"]


def test_compatibility_endpoints(client):
    initialized = initialize_event(client)
    event_id = initialized["event_id"]
    persona_id = initialized["personas"][0]["id"]

    stats = client.post("/api/stats/view-count/increment")
    assert stats.status_code == 200
    assert stats.json()["success"] is True

    background = client.post(f"/api/event/{event_id}/regenerate-background")
    assert background.status_code == 200
    assert "background_url" in background.json()

    avatar = client.post(f"/api/personas/{persona_id}/regenerate_avatar")
    assert avatar.status_code == 200
    assert avatar.json()["success"] is True

    deleted = client.delete(f"/api/event/{event_id}")
    assert deleted.status_code == 200
    assert deleted.json()["success"] is True
