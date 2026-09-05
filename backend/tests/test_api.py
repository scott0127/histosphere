import pytest

from app.core.interaction_contract import INTERACTION_POLICY_VERSION, build_interaction_runtime
from app.models.domain import ChatMessage, Event
from app.providers.llm.base import ChatGenerationResult


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
        headers={"x-admin-key": "test-admin"},
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
    assert response.status_code == 202
    accepted = response.json()
    polled = client.get(accepted["poll_url"])
    assert polled.status_code == 200
    assert polled.json()["attempt"]["status"] == "submitted"
    assert polled.json()["result"]
    return polled.json()["result"]


def test_task_attempt_stays_processing_until_opening_is_durable(client):
    initialized = initialize_event(client, "提交狀態語意測試", "no_ebl_roleplay")
    repository = client.app.state.repository
    provider = client.app.state.opening_service.llm_provider
    original_generate_greeting = provider.generate_greeting
    observed: dict[str, object] = {}

    async def capture_state_before_opening(**kwargs):
        attempt = repository.get_task_attempt(kwargs["attempt"].id)
        observed["attempt_status"] = attempt.status
        observed["conversation_exists"] = bool(
            repository.get_conversation_by_session(initialized["session_id"])
        )
        return await original_generate_greeting(**kwargs)

    provider.generate_greeting = capture_state_before_opening
    accepted = client.post(
        f"/api/tasks/{initialized['task']['id']}/submit",
        json={
            "session_id": initialized["session_id"],
            "response_payload": {"answer_text": "測試答案"},
        },
    )

    assert accepted.status_code == 202
    assert observed == {"attempt_status": "processing", "conversation_exists": False}
    polled = client.get(accepted.json()["poll_url"])
    assert polled.status_code == 200
    assert polled.json()["attempt"]["status"] == "submitted"
    assert polled.json()["result"]["conversation_id"]


def test_compatibility_conversation_creation_is_idempotent_and_workflow_bound(client):
    initialized = initialize_event(client, "相容對話建立測試", "no_ebl_roleplay")
    submitted = submit_task(client, initialized, "測試答案")
    provider = client.app.state.opening_service.llm_provider
    greeting_count = len(provider.greeting_prompts)

    repeated = client.post(
        "/api/conversations",
        json={
            "event_id": initialized["event_id"],
            "task_attempt_id": submitted["attempt_id"],
            "session_id": initialized["session_id"],
        },
    )

    assert repeated.status_code == 200
    assert repeated.json()["conversation_id"] == submitted["conversation_id"]
    assert len(repeated.json()["history"]) == 1
    assert len(provider.greeting_prompts) == greeting_count

    other = initialize_event(client, "另一條相容對話流程", "no_ebl_roleplay")
    mismatched = client.post(
        "/api/conversations",
        json={
            "event_id": other["event_id"],
            "task_attempt_id": submitted["attempt_id"],
            "session_id": initialized["session_id"],
        },
    )
    assert mismatched.status_code == 400


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
    assert data["task"]["error_elicitation_task_full_text"]
    assert len(data["personas"]) == 1
    assert data["condition"]["condition_key"] == "ebl_roleplay"


def test_event_initialize_persists_primary_persona_when_teacher_does_not_specify(client):
    data = initialize_event(client, "文藝復興")

    assert len(data["personas"]) == 1
    persona = data["personas"][0]
    assert persona["name"]
    assert persona["event_id"] == data["event_id"]
    assert persona["prompt_profile"].get("selection_policy")

    listed = client.get(f"/api/personas?event_id={data['event_id']}")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == persona["id"]


def test_event_initialize_normalizes_event_name_before_reuse(client):
    simplified = initialize_event(client, "法国大革命")
    traditional = initialize_event(client, "法國大革命", "no_ebl_no_roleplay")

    assert simplified["event_id"] == traditional["event_id"]
    assert simplified["task"]["id"] == traditional["task"]["id"]
    assert simplified["personas"][0]["id"] == traditional["personas"][0]["id"]
    assert traditional["event"]["canonical_name"] == "法國大革命"
    assert simplified["session_id"] != traditional["session_id"]


def test_public_initialize_does_not_rebuild_existing_event_materials(client):
    first = initialize_event(client, "法國大革命")
    rebuilt = client.post(
        "/api/event/initialize",
        json={"event_name": "法國大革命", "condition_key": "ebl_roleplay", "rebuild": True},
        headers={"x-admin-key": "test-admin"},
    )

    assert rebuilt.status_code == 200
    payload = rebuilt.json()
    assert payload["event_id"] == first["event_id"]
    assert payload["task"]["id"] == first["task"]["id"]
    assert payload["personas"][0]["id"] == first["personas"][0]["id"]
    assert payload["session_id"] != first["session_id"]


def test_conditions_reuse_same_event_materials_but_create_isolated_conversations(client):
    initialized_by_condition = {
        condition_key: initialize_event(client, "法國大革命", condition_key)
        for condition_key in CONDITIONS
    }

    event_ids = {payload["event_id"] for payload in initialized_by_condition.values()}
    task_ids = {payload["task"]["id"] for payload in initialized_by_condition.values()}
    persona_ids = {payload["personas"][0]["id"] for payload in initialized_by_condition.values()}
    session_ids = {payload["session_id"] for payload in initialized_by_condition.values()}

    assert len(event_ids) == 1
    assert len(task_ids) == 1
    assert len(persona_ids) == 1
    assert len(session_ids) == len(CONDITIONS)

    submitted_by_condition = {
        condition_key: submit_task(client, payload, "1789 年法國大革命與啟蒙思想、國民議會和巴士底監獄有關。")
        for condition_key, payload in initialized_by_condition.items()
    }
    conversation_ids = {payload["conversation_id"] for payload in submitted_by_condition.values()}

    assert len(conversation_ids) == len(CONDITIONS)
    assert all(payload["event"]["id"] == next(iter(event_ids)) for payload in submitted_by_condition.values())

    for condition_key, submitted in submitted_by_condition.items():
        loaded = client.get(f"/api/conversations/{submitted['conversation_id']}")
        assert loaded.status_code == 200
        payload = loaded.json()
        assert payload["condition"]["condition_key"] == condition_key
        assert len(payload["messages"]) == 1
        if payload["condition"]["roleplay_enabled"]:
            assert payload["messages"][0]["speaker_type"] == "persona"
            assert payload["messages"][0]["speaker_name"] == payload["personas"][0]["name"]
        else:
            assert payload["messages"][0]["speaker_type"] == "assistant"
            assert payload["messages"][0]["speaker_name"] in {"AI Tutor", "AI Assistant"}


def test_event_check_and_list_events(client):
    initialized = initialize_event(client, "法國大革命")
    locked = client.post(
        f"/api/admin/events/{initialized['event_id']}/material-lock",
        headers={"x-admin-key": "test-admin"},
        json={"locked": True},
    )
    assert locked.status_code == 200

    check = client.post("/api/event/check", json={"event_name": "法國大革命"})
    assert check.status_code == 200
    assert check.json()["exists"] is True

    events = client.get("/api/events")
    assert events.status_code == 200
    payload = events.json()
    assert len(payload) == 1
    assert payload[0]["id"] == initialized["event_id"]
    assert payload[0]["personas"]
    public_task = payload[0]["latest_task"]
    assert public_task
    assert public_task["story_text"] == ""
    assert public_task["error_elicitation_task_full_text"] == ""
    assert public_task["evaluation_payload"] == {"question_count": 1}

    snapshot = client.get("/api/admin/snapshot", headers={"x-admin-key": "test-admin"})
    assert snapshot.status_code == 200
    admin_task = snapshot.json()["events"][0]["latest_task"]
    assert admin_task["story_text"] == client.app.state.repository.get_event_task(admin_task["id"]).story_text
    assert initialized["task"]["story_text"] == ""
    assert admin_task["evaluation_payload"]["questions"][0]["correct_answer"] == "原因"


def test_existing_event_without_task_requires_admin_prepared_material(client):
    repository = client.app.state.repository
    event = repository.save_event(
        Event(
            canonical_name="缺少任務的事件",
            context="缺少任務的事件用來測試系統建立可編輯的保守題目。",
        )
    )

    # 不能在缺少題目時偷偷建立只需抄事件名稱、又沒有理由標準的題目。
    response = client.post(
        "/api/event/initialize",
        headers={"x-admin-key": "test-admin"},
        json={"event_name": "缺少任務的事件", "condition_key": "no_ebl_no_roleplay", "rebuild": False},
    )
    assert response.status_code == 409
    assert "Task" in response.json()["detail"]
    assert not repository.list_event_tasks(event.id)


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


def test_task_draft_and_session_progress_are_recoverable(client):
    created = client.post(
        "/api/event/initialize",
        json={
            "event_name": "霧社事件",
            "condition_key": "ebl_roleplay",
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

    initialized_response = client.post(
        "/api/event/initialize",
        json={
            "event_name": created_payload["event"]["canonical_name"],
            "condition_key": "ebl_roleplay",
            "rebuild": False,
        },
    )
    assert initialized_response.status_code == 200
    initialized = initialized_response.json()

    draft = client.patch(
        f"/api/tasks/{initialized['task']['id']}/draft",
        json={
            "session_id": initialized["session_id"],
            "user_id": "participant-001",
            "response_payload": {"answers": [{"question_id": "q01", "value": "殖民治理"}]},
        },
    )
    assert draft.status_code == 200
    attempt = draft.json()["attempt"]
    assert attempt["status"] == "in_progress"
    assert attempt["response_payload"]["answers"][0]["value"] == "殖民治理"

    state = client.get(f"/api/sessions/{initialized['session_id']}/state")
    assert state.status_code == 200
    payload = state.json()
    assert payload["session"]["id"] == initialized["session_id"]
    assert payload["event"]["id"] == initialized["event_id"]
    assert payload["task"]["id"] == initialized["task"]["id"]
    assert payload["attempt"]["id"] == attempt["id"]
    assert payload["conversation_id"] is None

    progress = client.get("/api/sessions/progress", params={"user_id": "participant-001"})
    assert progress.status_code == 200
    item = progress.json()["progress"][0]
    assert item["event_id"] == initialized["event_id"]
    assert item["condition_key"] == "ebl_roleplay"
    assert item["session_id"] == initialized["session_id"]
    assert item["task_id"] == initialized["task"]["id"]
    assert item["attempt_id"] == attempt["id"]
    assert item["status"] == "task_draft"

    submitted = submit_task(client, initialized, "霧社事件與殖民治理、警察權力和族群處境有關。")
    progress_after_submit = client.get("/api/sessions/progress", params={"user_id": "participant-001"})
    item_after_submit = progress_after_submit.json()["progress"][0]
    assert item_after_submit["conversation_id"] == submitted["conversation_id"]
    assert item_after_submit["status"] == "chat_started"

    blocked_draft = client.patch(
        f"/api/tasks/{initialized['task']['id']}/draft",
        json={
            "session_id": initialized["session_id"],
            "user_id": "participant-001",
            "response_payload": {"answers": []},
        },
    )
    assert blocked_draft.status_code == 409


def test_chat_policy_matrix(client):
    for index, condition_key in enumerate(CONDITIONS, start=1):
        initialized = initialize_event(client, f"矩陣測試事件 {index}", condition_key)
        submitted = submit_task(client, initialized)

        chat = client.post(
            "/api/chat",
            json={
                "conversation_id": submitted["conversation_id"],
                "user_message": "這場事件的重要性是什麼？",
                "history": [],
            },
        )
        assert chat.status_code == 200
        payload = chat.json()
        assert payload["response"]
        greeting = submitted["greeting"]
        if initialized["condition"]["roleplay_enabled"]:
            assert payload["selected_persona"]
            assert payload["message"]["speaker_type"] == "persona"
            assert initialized["personas"][0]["name"] in greeting
        else:
            assert payload["selected_persona"] is None
            assert payload["message"]["speaker_type"] == "assistant"
        if initialized["condition"]["response_policy"] == "scaffold":
            assert payload["message"]["metadata"]["response_policy"] == "scaffold"
            assert "正確答案是" not in greeting
            assert greeting.count("？") <= 2
            assert "正確答案是" not in payload["response"]
            assert payload["response"].count("？") <= 2
            assert payload["message"]["metadata"]["interaction_mode"] == "scaffold"
            assert payload["message"]["metadata"]["dialogue_state"] in {
                "NOTICE_ERROR",
                "REFLECT",
            }
            assert payload["message"]["metadata"]["dialogue_move"] in {
                "error_awareness_prompt",
                "reflection_prompt",
            }
            assert payload["message"]["metadata"]["disclosure_level"] in {
                "D0",
                "D1",
                "D2",
                "D3",
                "D4",
            }
        else:
            assert payload["message"]["metadata"]["response_policy"] == "standard"
            assert "正確答案是" not in greeting
            assert "？" in greeting
            assert payload["message"]["metadata"]["interaction_mode"] == "standard_chat"
            assert payload["message"]["metadata"]["dialogue_state"] == "STANDARD_CHAT"
            assert payload["message"]["metadata"]["dialogue_move"] == "natural_response"
            assert payload["message"]["metadata"]["disclosure_level"] is None
            assert payload["message"]["metadata"]["target_question_id"] is None

        assert payload["message"]["metadata"]["interaction_policy_version"] == INTERACTION_POLICY_VERSION
        if initialized["condition"]["response_policy"] == "scaffold":
            assert payload["message"]["metadata"]["target_question_id"] == "q01"
        assert "interaction_runtime" in payload["message"]["metadata"]["prompt_modules"]
        assert "fidelity_flags" not in payload["message"]["metadata"]
        assert client.app.state.repository.get_message(payload["message"]["id"]).metadata["fidelity_flags"] == []

        loaded = client.get(f"/api/conversations/{submitted['conversation_id']}")
        messages = loaded.json()["messages"]
        assert [message["sequence_index"] for message in messages] == list(range(len(messages)))


@pytest.mark.parametrize("condition_key", ["ebl_no_roleplay", "ebl_roleplay"])
def test_d4_gives_feedback_then_waits_for_one_restatement(client, condition_key):
    initialized = initialize_event(client, "D4 切題測試事件", condition_key)
    submitted = submit_task(client, initialized)
    repository = client.app.state.repository
    attempt = repository.get_task_attempt(submitted["attempt_id"])
    judgement = dict(attempt.judgement_payload)
    question_results = list(judgement["question_results"])
    question_results[0] = {**question_results[0], "expected_answer": "按人數"}
    question_results.append(
        {
            "question_id": "q02",
            "prompt": "第二項錯誤應如何修正？",
            "source_text": "第二項可檢查的歷史脈絡。",
            "learner_answer": "錯誤判斷",
            "expected_answer": "修正判斷",
            "correctness": "incorrect",
            "error_code": "unclassified",
            "historical_concept": "cause_and_consequence",
            "reasoning_process": "argumentation",
            "evidence_ids": ["E02"],
        }
    )
    repository.save_task_attempt(
        attempt.model_copy(update={"judgement_payload": {**judgement, "question_results": question_results}})
    )
    repository.add_message(
        ChatMessage(
            conversation_id=submitted["conversation_id"],
            speaker_type="persona",
            speaker_name=initialized["personas"][0]["name"],
            sequence_index=repository.next_message_sequence(submitted["conversation_id"]),
            content="目前已整理最強證據，但判斷仍需由你完成。",
            metadata={
                "interaction_policy_version": INTERACTION_POLICY_VERSION,
                "target_question_id": "q01",
                "next_target_question_id": "q02",
                "dialogue_state": "REFLECT",
                "dialogue_move": "reflection_prompt",
                "disclosure_level": "D4",
                "completion_status": "continue",
            },
        )
    )

    messages_before = repository.list_messages(submitted["conversation_id"])
    response = client.post(
        "/api/chat",
        json={
            "conversation_id": submitted["conversation_id"],
            "user_message": "處理下一個錯誤",
            "history": [],
            "client_request_id": "next-error-request",
            "interaction_action": "next_error",
        },
    )

    assert response.status_code == 409
    assert "Direct error skipping" in response.json()["detail"]
    assert repository.list_messages(submitted["conversation_id"]) == messages_before

    calls = []
    valid_feedback = "依我所見，應以「按人數」表決，不能把每個等級的一票與每個代表的一票混淆。接著看財政危機。"

    async def scripted_response(**kwargs):
        calls.append(kwargs["prompt"])
        if len(calls) == 1:
            assert "D4 support has been used" in kwargs["prompt"]
            return ChatGenerationResult(
                response="應以按人數表決，而非按等級。請用自己的話重述原判斷應如何修正。",
                interaction_metadata={
                    "dialogue_state": "SELF_CORRECT", "dialogue_move": "corrective_feedback",
                    "disclosure_level": "D4", "completion_status": "corrective_resolution_pending",
                },
            )
        assert "one opportunity to restate" in kwargs["prompt"]
        return ChatGenerationResult(
            response=valid_feedback,
            interaction_metadata={
                "dialogue_state": "RESOLVED", "dialogue_move": "corrective_feedback",
                "disclosure_level": "D4", "completion_status": "feedback_completed",
                "resolution_self_corrected": False,
            },
        )

    client.app.state.llm_provider.generate_chat_response = scripted_response
    final_request = client.post("/api/chat", json={
        "conversation_id": submitted["conversation_id"], "user_message": "我還是不太清楚。",
        "client_request_id": "ask-final",
    })
    assert final_request.status_code == 200
    assert final_request.json()["message"]["metadata"]["completion_status"] == "corrective_resolution_pending"
    assert "按人數" in final_request.json()["response"]
    stored_attempt = repository.get_task_attempt(submitted["attempt_id"])
    condition = repository.get_condition_by_key(condition_key)
    waiting = build_interaction_runtime(condition, stored_attempt, repository.list_messages(submitted["conversation_id"]))
    assert waiting.target.question_id == "q01"
    assert waiting.restatement_required is True
    assert waiting.corrective_feedback_required is False

    final_payload = {
        "conversation_id": submitted["conversation_id"], "user_message": "我最後仍認為按等級，因為我把兩種投票方式當成同一件事。",
        "client_request_id": "final-answer",
    }
    feedback = client.post("/api/chat", json=final_payload)
    assert feedback.status_code == 200
    metadata = feedback.json()["message"]["metadata"]
    assert metadata["completion_status"] == "feedback_completed"
    assert metadata["resolution_self_corrected"] is False
    assert "corrective_feedback_revealed_answer" not in metadata
    assert metadata["next_target_started"] is True
    assert feedback.json()["response"] == valid_feedback
    messages = repository.list_messages(submitted["conversation_id"])
    assert any(message.content == valid_feedback for message in messages)
    resumed = build_interaction_runtime(condition, stored_attempt, messages)
    assert resumed.target.question_id == "q02"
    assert resumed.previous_disclosure_level == "D0"
    # 重送最後答案只回讀已儲存回饋，不多生成、不再切換一次 target。
    replay = client.post("/api/chat", json=final_payload)
    assert replay.status_code == 200
    assert replay.json()["response"] == valid_feedback
    assert len(calls) == 2


def test_invalid_persona_candidate_is_retried_and_never_persisted(client):
    initialized = initialize_event(client, "候選重試事件", "no_ebl_roleplay")
    submitted = submit_task(client, initialized)
    provider = client.app.state.llm_provider
    event_name = initialized["event"]["canonical_name"]
    persona_name = initialized["personas"][0]["name"]
    invalid_response = f"作為 AI，我將扮演{persona_name}並介紹{event_name}。"
    calls = 0

    async def scripted_chat_response(**kwargs):
        nonlocal calls
        calls += 1
        response = (
            invalid_response
            if calls == 1
            else f"我是{persona_name}。此刻{event_name}的局勢正在我眼前變化，你想先談哪一項衝突？"
        )
        return ChatGenerationResult(
            response=response,
            interaction_metadata={
                "dialogue_state": "STANDARD_CHAT",
                "dialogue_move": "natural_response",
                "learner_revision_status": "not_applicable",
                "completion_status": "continue",
                "fidelity_flags": [],
            },
        )

    provider.generate_chat_response = scripted_chat_response
    chat = client.post(
        "/api/chat",
        json={
            "conversation_id": submitted["conversation_id"],
            "user_message": "請說明你眼前的處境。",
            "history": [],
        },
    )

    assert chat.status_code == 200
    payload = chat.json()
    assert calls == 2
    assert payload["message"]["metadata"]["generation_retry_count"] == 1
    assert len(payload["message"]["metadata"]["rejected_candidates"]) == 1
    loaded = client.get(f"/api/conversations/{submitted['conversation_id']}").json()
    contents = [message["content"] for message in loaded["messages"]]
    assert invalid_response not in contents
    assert contents.count("請說明你眼前的處境。") == 1


def test_persona_crud(client):
    initialized = initialize_event(client, "明治維新")
    event_id = initialized["event_id"]
    original_persona = initialized["personas"][0]

    unauthorized = client.post(
        "/api/personas",
        json={"event_id": event_id, "name": "未授權人物"},
    )
    assert unauthorized.status_code == 401

    created = client.post(
        "/api/personas",
        headers={"x-admin-key": "test-admin"},
        json={
            "event_id": event_id,
            "name": "測試人物",
            "role": "觀察者",
            "biography": "用於測試人物管理的角色。",
            "expertise_areas": ["history"],
            "avatar_url": "/images/personas/test-persona.png",
            "prompt_profile": {"speaking_style": "calm"},
            "active": False,
        },
    )
    assert created.status_code == 200
    persona = created.json()
    assert persona["avatar_url"] == "/images/personas/test-persona.png"

    unauthorized_update = client.patch(
        f"/api/personas/{persona['id']}",
        json={"active": True},
    )
    assert unauthorized_update.status_code == 401

    conflict = client.patch(
        f"/api/personas/{persona['id']}",
        headers={"x-admin-key": "test-admin"},
        json={"active": True},
    )
    assert conflict.status_code == 409

    disabled = client.patch(
        f"/api/admin/personas/{original_persona['id']}",
        headers={"x-admin-key": "test-admin"},
        json={"active": False},
    )
    assert disabled.status_code == 200

    updated = client.patch(
        f"/api/admin/personas/{persona['id']}",
        headers={"x-admin-key": "test-admin"},
        json={"role": "更新後角色", "active": True},
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "更新後角色"
    assert updated.json()["active"] is True

    listed = client.get(f"/api/personas?event_id={event_id}")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [persona["id"]]

    unauthorized_archive = client.delete(f"/api/personas/{persona['id']}")
    assert unauthorized_archive.status_code == 401

    deleted = client.delete(
        f"/api/personas/{persona['id']}",
        headers={"x-admin-key": "test-admin"},
    )
    assert deleted.status_code == 200
    assert deleted.json()["success"] is True

    snapshot = client.get("/api/admin/snapshot", headers={"x-admin-key": "test-admin"})
    archived = next(
        item
        for event in snapshot.json()["events"]
        if event["id"] == event_id
        for item in event["personas"]
        if item["id"] == persona["id"]
    )
    assert archived["active"] is False
    assert archived["archived_at"] is not None

    unauthorized_restore = client.post(f"/api/personas/{persona['id']}/restore")
    assert unauthorized_restore.status_code == 401

    restored = client.post(
        f"/api/personas/{persona['id']}/restore",
        headers={"x-admin-key": "test-admin"},
    )
    assert restored.status_code == 200
    assert restored.json()["active"] is False
    assert restored.json()["archived_at"] is None


def test_learner_cannot_select_persona(client):
    initialized = initialize_event(client, "禁止人物切換", "no_ebl_roleplay")
    submitted = submit_task(client, initialized)

    response = client.post(
        "/api/chat",
        json={
            "conversation_id": submitted["conversation_id"],
            "user_message": "請繼續。",
            "history": [],
            "target_persona_id": initialized["personas"][0]["id"],
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Learners cannot select a historical persona"


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


def test_admin_updates_event_materials_and_logs(client):
    initialized = initialize_event(client, "法國大革命")
    event_id = initialized["event_id"]

    denied = client.patch(
        f"/api/admin/events/{event_id}",
        json={"description": "不應更新"},
        headers={"x-admin-key": "wrong"},
    )
    assert denied.status_code == 401

    updated = client.patch(
        f"/api/admin/events/{event_id}",
        json={
            "canonical_name": "法國大革命",
            "description": "更新後事件介紹",
            "context": "更新後研究脈絡",
            "start_year": 1789,
            "end_year": 1799,
            "source_summary": {"review_state": "teacher_modified"},
        },
        headers={"x-admin-key": "test-admin"},
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["description"] == "更新後事件介紹"
    assert payload["context"] == "更新後研究脈絡"
    assert payload["start_year"] == 1789
    assert payload["end_year"] == 1799
    assert payload["source_summary"]["review_state"] == "teacher_modified"

    locked = client.post(
        f"/api/admin/events/{event_id}/material-lock",
        headers={"x-admin-key": "test-admin"},
        json={"locked": True},
    )
    assert locked.status_code == 200

    events = client.get("/api/events")
    assert events.status_code == 200
    listed = events.json()[0]
    assert listed["id"] == event_id
    assert listed["description"] == "更新後事件介紹"

    logs = client.get("/api/admin/research-logs", headers={"x-admin-key": "test-admin"})
    assert logs.status_code == 200
    assert any(item["action_type"] == "event_updated" for item in logs.json())


def test_removed_noop_endpoints_return_not_found(client):
    initialized = initialize_event(client)
    event_id = initialized["event_id"]
    persona_id = initialized["personas"][0]["id"]

    assert client.post("/api/stats/view-count/increment").status_code == 404
    assert client.post(f"/api/event/{event_id}/regenerate-background").status_code == 404
    assert client.post(
        f"/api/personas/{persona_id}/regenerate_avatar",
        headers={"x-admin-key": "test-admin"},
    ).status_code == 404

    assert client.delete(f"/api/event/{event_id}").status_code == 404
    archived = client.post(
        f"/api/admin/events/{event_id}/archive",
        headers={"x-admin-key": "test-admin"},
    )
    assert archived.status_code == 200
    assert archived.json()["archived_at"]
