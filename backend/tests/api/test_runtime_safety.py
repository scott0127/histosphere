from datetime import datetime, timedelta

from app.models.domain import ChatMessage, utc_now
from app.schemas.requests import TaskSubmitRequest


ADMIN_HEADERS = {"x-admin-key": "test-admin"}


def admin_initialize(client, event_name="法國大革命", condition_key="ebl_roleplay"):
    response = client.post(
        "/api/event/initialize",
        headers=ADMIN_HEADERS,
        json={"event_name": event_name, "condition_key": condition_key, "rebuild": False},
    )
    assert response.status_code == 200
    return response.json()


def learner_initialize(client, event_name, condition_key="ebl_roleplay"):
    response = client.post(
        "/api/event/initialize",
        json={
            "event_name": event_name,
            "condition_key": condition_key,
            "rebuild": False,
        },
    )
    return response


def submit_and_poll(client, initialized):
    accepted = client.post(
        f"/api/tasks/{initialized['task']['id']}/submit",
        json={
            "session_id": initialized["session_id"],
            "response_payload": {"answer_text": "測試回答"},
        },
    )
    assert accepted.status_code == 202
    status_response = client.get(accepted.json()["poll_url"])
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["attempt"]["status"] == "submitted"
    assert payload["result"]
    return payload["result"]


def test_learner_may_only_reuse_assigned_existing_material(client):
    initialized = admin_initialize(client)
    assert client.post(
        f"/api/admin/events/{initialized['event_id']}/material-lock",
        headers=ADMIN_HEADERS,
        json={"locked": True},
    ).status_code == 200

    allowed = client.post(
        "/api/event/initialize",
        json={
            "event_name": initialized["event"]["canonical_name"],
            "condition_key": "ebl_roleplay",
            "user_id": "participant-001",
            "rebuild": False,
        },
    )
    assert allowed.status_code == 200

    participant = client.app.state.repository.get_participant_by_auth_user("participant-001")
    participant.condition_list = ["01"]
    client.app.state.repository.save_participant(participant)

    denied_assignment = client.post(
        "/api/event/initialize",
        json={
            "event_name": initialized["event"]["canonical_name"],
            "condition_key": "ebl_roleplay",
            "user_id": "participant-001",
            "rebuild": False,
        },
    )
    assert denied_assignment.status_code == 403
    assert "Condition 04" in denied_assignment.json()["detail"]

    denied_creation = client.post(
        "/api/event/initialize",
        json={
            "event_name": "Learner 不可建立的新事件",
            "condition_key": "no_ebl_no_roleplay",
            "user_id": "participant-001",
            "rebuild": False,
        },
    )
    assert denied_creation.status_code == 403
    assert "Only an admin" in denied_creation.json()["detail"]


def test_event_archive_hides_without_deleting_and_can_restore(client):
    initialized = admin_initialize(client, "封存測試事件")
    repository = client.app.state.repository
    event_id = initialized["event_id"]
    task_id = initialized["task"]["id"]
    persona_id = initialized["personas"][0]["id"]
    assert client.post(
        f"/api/admin/events/{event_id}/material-lock",
        headers=ADMIN_HEADERS,
        json={"locked": True},
    ).status_code == 200

    archived = client.post(f"/api/admin/events/{event_id}/archive", headers=ADMIN_HEADERS)
    assert archived.status_code == 200
    assert archived.json()["archived_at"]
    assert not any(event["id"] == event_id for event in client.get("/api/events").json())
    assert repository.get_event_task(task_id)
    assert repository.get_persona(persona_id)
    assert repository.get_session(initialized["session_id"])

    snapshot = client.get("/api/admin/snapshot", headers=ADMIN_HEADERS).json()
    assert any(event["id"] == event_id and event["archived_at"] for event in snapshot["events"])

    restored = client.post(f"/api/admin/events/{event_id}/restore", headers=ADMIN_HEADERS)
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    assert any(event["id"] == event_id for event in client.get("/api/events").json())


def test_task_submission_is_persisted_and_polled(client):
    initialized = admin_initialize(client, "非同步提交測試")
    submitted = submit_and_poll(client, initialized)
    assert submitted["conversation_id"]
    assert submitted["attempt"]["status"] == "submitted"
    assert submitted["judgement"]["llm_call"]["task_name"] == "judge_task_attempt"
    assert submitted["history"][0]["metadata"]["llm_call"]["task_name"] == "generate_greeting"

    processed_log = next(
        log
        for log in client.app.state.repository.list_research_logs()
        if log.action_type == "task_submission_processed"
        and log.attempt_id == submitted["attempt_id"]
    )
    assert processed_log.payload["judgement_llm_call"]["provider_switching_enabled"] is False
    assert processed_log.payload["opening_llm_call"]["provider_switching_enabled"] is False

    duplicate = client.post(
        f"/api/tasks/{initialized['task']['id']}/submit",
        json={"session_id": initialized["session_id"], "response_payload": {"answer_text": "重送"}},
    )
    assert duplicate.status_code == 202
    assert duplicate.json()["attempt_id"] == submitted["attempt_id"]


def test_processing_attempt_is_recovered_by_polling_after_worker_loss(client):
    initialized = admin_initialize(client, "處理中斷恢復測試")
    service = client.app.state.task_service
    accepted, should_process = service.queue_submission(
        initialized["task"]["id"],
        TaskSubmitRequest(
            session_id=initialized["session_id"],
            response_payload={"answer_text": "等待恢復"},
            user_id="participant-001",
        ),
    )
    assert should_process is True
    assert service.submission_status(accepted.attempt_id).attempt.status == "processing"

    client.app.state.active_task_attempts = set()
    first_poll = client.get(accepted.poll_url)
    assert first_poll.status_code == 200
    assert first_poll.json()["attempt"]["status"] == "processing"

    recovered = client.get(accepted.poll_url)
    assert recovered.status_code == 200
    assert recovered.json()["attempt"]["status"] == "submitted"
    assert recovered.json()["result"]


def test_chat_uses_database_backed_multi_turn_history(client):
    initialized = admin_initialize(client, "多輪記憶測試", "no_ebl_no_roleplay")
    submitted = submit_and_poll(client, initialized)

    first = client.post(
        "/api/chat",
        json={
            "conversation_id": submitted["conversation_id"],
            "user_message": "第一輪：請記住代表權爭議。",
            "history": [],
        },
    )
    assert first.status_code == 200
    second = client.post(
        "/api/chat",
        json={
            "conversation_id": submitted["conversation_id"],
            "user_message": "第二輪：我上一輪要你記住什麼？",
            "history": [],
        },
    )
    assert second.status_code == 200

    prompts = client.app.state.llm_provider.chat_prompts
    assert "第一輪：請記住代表權爭議。" in prompts[-1]
    assert "Authoritative prior messages from the database" in prompts[-1]
    metadata = second.json()["message"]["metadata"]
    assert metadata["prompt_hash"]
    assert metadata["history_message_count"] >= 3


def test_chat_persists_learner_message_when_llm_generation_fails(client):
    initialized = admin_initialize(client, "聊天失敗持久化測試", "no_ebl_no_roleplay")
    submitted = submit_and_poll(client, initialized)

    async def fail_generation(**kwargs):
        raise TimeoutError("simulated provider timeout")

    client.app.state.llm_provider.generate_chat_response = fail_generation
    failed = client.post(
        "/api/chat",
        json={
            "conversation_id": submitted["conversation_id"],
            "user_message": "即使模型失敗也要保存這則訊息。",
        },
    )
    assert failed.status_code == 502
    assert "訊息已保存" in failed.json()["detail"]

    loaded = client.get(f"/api/conversations/{submitted['conversation_id']}").json()
    learner_messages = [
        message
        for message in loaded["messages"]
        if message["content"] == "即使模型失敗也要保存這則訊息。"
    ]
    assert len(learner_messages) == 1
    assert learner_messages[0]["metadata"]["response_status"] == "failed"
    assert learner_messages[0]["metadata"]["failure_type"] == "TimeoutError"


def test_chat_stream_reports_persistence_status_deltas_and_completion(client):
    initialized = admin_initialize(client, "聊天串流測試", "no_ebl_no_roleplay")
    submitted = submit_and_poll(client, initialized)

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={
            "conversation_id": submitted["conversation_id"],
            "user_message": "請以串流方式回覆。",
        },
    ) as streamed:
        assert streamed.status_code == 200
        body = "".join(streamed.iter_text())

    assert "event: user_message" in body
    assert "event: status" in body
    assert "event: delta" in body
    assert "event: complete" in body

    loaded = client.get(f"/api/conversations/{submitted['conversation_id']}").json()
    learner_message = next(
        message for message in loaded["messages"] if message["content"] == "請以串流方式回覆。"
    )
    assert learner_message["metadata"]["response_status"] == "completed"
    response_message = next(
        message
        for message in loaded["messages"]
        if message["id"] == learner_message["metadata"]["response_message_id"]
    )
    assert response_message["metadata"]["generation_status"] == "completed"
    assert response_message["metadata"]["delivery_mode"] == "validated_stream"
    assert response_message["metadata"]["llm_call"]["task_name"] == "generate_chat_response"
    response_log = next(
        log
        for log in client.app.state.repository.list_research_logs()
        if log.message_id == response_message["id"]
    )
    assert response_log.payload["llm_call"]["provider_switching_enabled"] is False


def test_chat_stream_reports_failure_after_learner_message_is_saved(client):
    initialized = admin_initialize(client, "聊天串流失敗測試", "no_ebl_no_roleplay")
    submitted = submit_and_poll(client, initialized)

    async def fail_generation(**kwargs):
        raise TimeoutError("simulated stream timeout")

    client.app.state.llm_provider.generate_chat_response = fail_generation
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={
            "conversation_id": submitted["conversation_id"],
            "user_message": "請保留這則失敗串流訊息。",
        },
    ) as streamed:
        body = "".join(streamed.iter_text())

    assert "event: user_message" in body
    assert "event: error" in body
    assert "訊息已保存" in body
    loaded = client.get(f"/api/conversations/{submitted['conversation_id']}").json()
    learner_message = next(
        message
        for message in loaded["messages"]
        if message["content"] == "請保留這則失敗串流訊息。"
    )
    assert learner_message["metadata"]["response_status"] == "failed"


def test_chat_request_id_is_idempotent_and_status_can_be_reloaded(client):
    initialized = admin_initialize(client, "聊天冪等測試", "no_ebl_no_roleplay")
    submitted = submit_and_poll(client, initialized)
    request_payload = {
        "conversation_id": submitted["conversation_id"],
        "user_message": "同一個回合只能生成一次。",
        "client_request_id": "request-idempotent-001",
    }
    prompt_count = len(client.app.state.llm_provider.chat_prompts)

    first = client.post("/api/chat", json=request_payload)
    second = client.post("/api/chat", json=request_payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["message"]["id"] == first.json()["message"]["id"]
    assert len(client.app.state.llm_provider.chat_prompts) == prompt_count + 1

    operation = client.get(
        "/api/chat/operations/request-idempotent-001",
        params={"conversation_id": submitted["conversation_id"]},
    )
    assert operation.status_code == 200
    assert operation.json()["status"] == "completed"
    assert operation.json()["learner_message"]["operation_status"] == "completed"
    assert operation.json()["response"]["message"]["id"] == first.json()["message"]["id"]

    messages = client.app.state.repository.list_messages(submitted["conversation_id"])
    learner_operations = [
        message
        for message in messages
        if message.client_request_id == "request-idempotent-001"
        and message.speaker_type == "learner"
    ]
    assert len(learner_operations) == 1


def test_chat_blocks_a_second_operation_while_one_is_processing(client):
    initialized = admin_initialize(client, "聊天並行防護測試", "no_ebl_no_roleplay")
    submitted = submit_and_poll(client, initialized)
    repository = client.app.state.repository
    conversation_id = submitted["conversation_id"]
    repository.add_message(
        ChatMessage(
            conversation_id=conversation_id,
            speaker_type="learner",
            speaker_name="learner",
            sequence_index=repository.next_message_sequence(conversation_id),
            content="仍在處理中的訊息",
            client_request_id="request-active-001",
            operation_status="processing",
            metadata={"response_status": "pending"},
        )
    )
    prompt_count = len(client.app.state.llm_provider.chat_prompts)

    blocked = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation_id,
            "user_message": "不應同時送入模型。",
            "client_request_id": "request-active-002",
        },
    )

    assert blocked.status_code == 409
    assert "already processing" in blocked.json()["detail"]
    assert len(client.app.state.llm_provider.chat_prompts) == prompt_count


def test_failed_chat_operation_retries_without_duplicating_learner_message(client):
    initialized = admin_initialize(client, "聊天安全重試測試", "no_ebl_no_roleplay")
    submitted = submit_and_poll(client, initialized)
    provider = client.app.state.llm_provider
    repository = client.app.state.repository
    original_generation = provider.generate_chat_response

    async def fail_generation(**kwargs):
        raise TimeoutError("simulated retryable timeout")

    provider.generate_chat_response = fail_generation
    request_payload = {
        "conversation_id": submitted["conversation_id"],
        "user_message": "這一回合失敗後要安全重試。",
        "client_request_id": "request-retry-001",
    }
    failed = client.post("/api/chat", json=request_payload)
    assert failed.status_code == 502

    failed_status = client.get(
        "/api/chat/operations/request-retry-001",
        params={"conversation_id": submitted["conversation_id"]},
    )
    assert failed_status.status_code == 200
    assert failed_status.json()["status"] == "failed"
    assert failed_status.json()["retryable"] is True

    provider.generate_chat_response = original_generation
    retried = client.post(
        "/api/chat",
        json={**request_payload, "retry_failed": True},
    )
    assert retried.status_code == 200

    messages = repository.list_messages(submitted["conversation_id"])
    learner_operations = [
        message
        for message in messages
        if message.client_request_id == "request-retry-001"
        and message.speaker_type == "learner"
    ]
    assert len(learner_operations) == 1
    assert learner_operations[0].operation_status == "completed"
    assert learner_operations[0].metadata["retry_count"] == 1
    assert any(
        log.action_type == "response_generation_retried"
        and log.message_id == learner_operations[0].id
        for log in repository.list_research_logs()
    )


def test_backend_restart_marks_interrupted_chat_operation_retryable(client):
    initialized = admin_initialize(client, "聊天重啟恢復測試", "no_ebl_no_roleplay")
    submitted = submit_and_poll(client, initialized)
    repository = client.app.state.repository
    conversation_id = submitted["conversation_id"]
    request_payload = {
        "conversation_id": conversation_id,
        "user_message": "後端重啟後應沿用同一則 learner 訊息重試。",
        "client_request_id": "request-restart-001",
    }
    repository.add_message(
        ChatMessage(
            conversation_id=conversation_id,
            speaker_type="learner",
            speaker_name="learner",
            sequence_index=repository.next_message_sequence(conversation_id),
            content=request_payload["user_message"],
            client_request_id=request_payload["client_request_id"],
            operation_status="processing",
            metadata={
                "client_request_id": request_payload["client_request_id"],
                "response_status": "pending",
            },
        )
    )

    recovered = client.app.state.chat_service.recover_interrupted_operations()

    assert recovered == 1
    assert client.app.state.chat_service.recover_interrupted_operations() == 0
    operation = client.get(
        f"/api/chat/operations/{request_payload['client_request_id']}",
        params={"conversation_id": conversation_id},
    )
    assert operation.status_code == 200
    assert operation.json()["status"] == "failed"
    assert operation.json()["retryable"] is True
    assert operation.json()["learner_message"]["metadata"]["failure_type"] == "backend_restart"

    retried = client.post(
        "/api/chat",
        json={**request_payload, "retry_failed": True},
    )
    assert retried.status_code == 200
    learner_operations = [
        message
        for message in repository.list_messages(conversation_id)
        if message.client_request_id == request_payload["client_request_id"]
        and message.speaker_type == "learner"
    ]
    assert len(learner_operations) == 1
    assert learner_operations[0].operation_status == "completed"
    assert learner_operations[0].metadata["retry_count"] == 1
    assert any(
        log.action_type == "response_generation_failed"
        and log.message_id == learner_operations[0].id
        and log.payload["failure_type"] == "backend_restart"
        for log in repository.list_research_logs()
    )


def test_chat_rejects_missing_session_or_condition_without_falling_back(client):
    initialized = admin_initialize(client, "Condition fail-closed 測試", "no_ebl_no_roleplay")
    submitted = submit_and_poll(client, initialized)
    repository = client.app.state.repository
    conversation = repository.get_conversation(submitted["conversation_id"])
    original_session_id = conversation.session_id
    prompt_count = len(client.app.state.llm_provider.chat_prompts)

    conversation.session_id = None
    repository.save_conversation(conversation)
    missing_session = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation.id,
            "user_message": "這則訊息不應送進模型。",
        },
    )
    assert missing_session.status_code == 409
    assert "not bound to an experiment session" in missing_session.json()["detail"]

    conversation.session_id = original_session_id
    repository.save_conversation(conversation)
    session = repository.get_session(original_session_id)
    session.condition_key_snapshot = "missing-condition"
    repository.save_session(session)
    missing_condition = client.post(
        "/api/chat",
        json={
            "conversation_id": conversation.id,
            "user_message": "這則訊息也不應送進模型。",
        },
    )
    assert missing_condition.status_code == 409
    assert "condition snapshot is unavailable" in missing_condition.json()["detail"]
    assert len(client.app.state.llm_provider.chat_prompts) == prompt_count


def test_chat_timer_starts_once_expires_and_only_admin_can_reset_it(client):
    initialized = admin_initialize(client, "計時器測試")
    session_id = initialized["session_id"]
    original = client.get(f"/api/sessions/{session_id}/state", headers=ADMIN_HEADERS).json()["session"]
    assert original["timer_ends_at"] is None

    submitted = submit_and_poll(client, initialized)
    assert submitted["conversation_id"]
    started = client.get(f"/api/sessions/{session_id}/state", headers=ADMIN_HEADERS).json()["session"]
    assert started["status"] == "conversation_started"
    assert started["timer_started_at"]
    assert started["timer_ends_at"]
    started_at = datetime.fromisoformat(started["timer_started_at"].replace("Z", "+00:00"))
    ends_at = datetime.fromisoformat(started["timer_ends_at"].replace("Z", "+00:00"))
    assert (ends_at - started_at).total_seconds() == 300

    # 重整只讀取同一截止時間，不能重新給受測者五分鐘。
    reloaded = client.get(f"/api/sessions/{session_id}/state", headers=ADMIN_HEADERS).json()["session"]
    assert reloaded["timer_started_at"] == started["timer_started_at"]
    assert reloaded["timer_ends_at"] == started["timer_ends_at"]

    invalid_duration = client.post(
        f"/api/admin/sessions/{session_id}/timer",
        headers=ADMIN_HEADERS,
        json={"duration_minutes": 30},
    )
    assert invalid_duration.status_code == 422

    repository = client.app.state.repository
    session = repository.get_session(session_id)
    session.timer_ends_at = utc_now() - timedelta(seconds=1)
    repository.save_session(session)
    assert client.app.state.session_service.expire_due_sessions() == 1

    completed = client.get(f"/api/sessions/{session_id}/state", headers=ADMIN_HEADERS).json()["session"]
    assert completed["status"] == "completed"
    assert completed["completion_reason"] == "timer_elapsed"

    reset = client.post(
        f"/api/admin/sessions/{session_id}/timer",
        headers=ADMIN_HEADERS,
        json={"duration_minutes": 5},
    )
    assert reset.status_code == 200
    reset_session = reset.json()
    assert reset_session["status"] == "conversation_started"
    assert reset_session["completed_at"] is None
    assert reset_session["completion_reason"] is None
    assert reset_session["timer_ends_at"] != completed["timer_ends_at"]


def test_learner_resumes_active_event_and_cannot_repeat_completed_event(client):
    materials = admin_initialize(client, "同事件永久防重測試")
    assert client.post(
        f"/api/admin/events/{materials['event_id']}/material-lock",
        headers=ADMIN_HEADERS,
        json={"locked": True},
    ).status_code == 200

    first = learner_initialize(client, materials["event"]["canonical_name"], "ebl_roleplay")
    assert first.status_code == 200
    first_payload = first.json()

    resumed = learner_initialize(client, materials["event"]["canonical_name"], "ebl_roleplay")
    assert resumed.status_code == 200
    assert resumed.json()["session_id"] == first_payload["session_id"]
    assert resumed.json()["condition"]["condition_key"] == "ebl_roleplay"

    repository = client.app.state.repository
    participant_sessions = repository.list_sessions_for_user("participant-001")
    assert [session.id for session in participant_sessions] == [first_payload["session_id"]]

    completed_session = repository.get_session(first_payload["session_id"])
    completed_session.status = "completed"
    completed_session.completed_at = utc_now()
    completed_session.completion_reason = "learner"
    repository.save_session(completed_session)

    blocked = learner_initialize(client, materials["event"]["canonical_name"], "ebl_roleplay")
    assert blocked.status_code == 409
    assert "already been completed" in blocked.json()["detail"]
    assert len(repository.list_sessions_for_user("participant-001")) == 1


def test_learner_must_follow_admin_assigned_condition_order(client):
    first_material = admin_initialize(client, "分派順序第一事件", "no_ebl_no_roleplay")
    second_material = admin_initialize(client, "分派順序第二事件", "no_ebl_roleplay")
    for material in (first_material, second_material):
        assert client.post(
            f"/api/admin/events/{material['event_id']}/material-lock",
            headers=ADMIN_HEADERS,
            json={"locked": True},
        ).status_code == 200

    repository = client.app.state.repository
    participant = repository.get_participant_by_auth_user("participant-001")
    participant.condition_list = ["01", "03"]
    repository.save_participant(participant)

    skipped = learner_initialize(
        client,
        second_material["event"]["canonical_name"],
        "no_ebl_roleplay",
    )
    assert skipped.status_code == 409
    assert "must complete Condition 01 before Condition 03" in skipped.json()["detail"]

    first = learner_initialize(
        client,
        first_material["event"]["canonical_name"],
        "no_ebl_no_roleplay",
    )
    assert first.status_code == 200

    blocked_while_active = learner_initialize(
        client,
        second_material["event"]["canonical_name"],
        "no_ebl_roleplay",
    )
    assert blocked_while_active.status_code == 409
    assert "must resume Condition 01" in blocked_while_active.json()["detail"]

    resumed = learner_initialize(
        client,
        first_material["event"]["canonical_name"],
        "no_ebl_no_roleplay",
    )
    assert resumed.status_code == 200
    assert resumed.json()["session_id"] == first.json()["session_id"]

    completed_session = repository.get_session(first.json()["session_id"])
    completed_session.status = "completed"
    completed_session.completed_at = utc_now()
    completed_session.completion_reason = "timer_elapsed"
    repository.save_session(completed_session)

    second = learner_initialize(
        client,
        second_material["event"]["canonical_name"],
        "no_ebl_roleplay",
    )
    assert second.status_code == 200
    assert second.json()["condition"]["condition_key"] == "no_ebl_roleplay"


def test_admin_restart_archives_old_runtime_and_preserves_research_data(client):
    materials = admin_initialize(client, "管理員重建 Session 測試")
    assert client.post(
        f"/api/admin/events/{materials['event_id']}/material-lock",
        headers=ADMIN_HEADERS,
        json={"locked": True},
    ).status_code == 200
    learner = learner_initialize(client, materials["event"]["canonical_name"], "ebl_roleplay")
    assert learner.status_code == 200
    learner_payload = learner.json()
    submitted = submit_and_poll(client, learner_payload)

    repository = client.app.state.repository
    old_session = repository.get_session(learner_payload["session_id"])
    old_session.status = "completed"
    old_session.completed_at = utc_now()
    old_session.completion_reason = "learner"
    repository.save_session(old_session)
    old_conversation = repository.get_conversation(submitted["conversation_id"])
    old_attempt = repository.get_task_attempt_for_session(old_session.id, learner_payload["task"]["id"])
    old_messages = repository.list_messages(old_conversation.id)

    restarted = client.post(
        f"/api/admin/sessions/{old_session.id}/restart",
        headers=ADMIN_HEADERS,
    )
    assert restarted.status_code == 200
    payload = restarted.json()
    assert payload["new_session"]["id"] != old_session.id
    assert payload["new_session"]["status"] == "initialized"
    assert payload["new_session"]["event_id"] == old_session.event_id
    assert payload["new_session"]["condition_key_snapshot"] == old_session.condition_key_snapshot
    assert payload["new_session"]["user_id"] == old_session.user_id

    archived = repository.get_session(old_session.id)
    assert archived.status == "archived"
    assert archived.completion_reason == "admin_restart"
    assert repository.get_conversation(old_conversation.id).status == "archived"
    assert repository.get_task_attempt(old_attempt.id)
    assert repository.list_messages(old_conversation.id) == old_messages

    resumed = learner_initialize(client, materials["event"]["canonical_name"], "ebl_roleplay")
    assert resumed.status_code == 200
    assert resumed.json()["session_id"] == payload["new_session"]["id"]
    assert any(
        log.action_type == "session_restarted"
        and log.payload["new_session_id"] == payload["new_session"]["id"]
        for log in repository.list_research_logs()
    )


def test_persona_prompt_contract_and_dry_run_are_non_persistent(client):
    initialized = admin_initialize(client, "Persona contract 測試")
    profile = initialized["personas"][0]["prompt_profile"]
    assert profile["contract_version"] == "persona_prompt_v2"
    assert profile["speaking_style"]
    assert profile["knowledge_boundary"]
    assert profile["forbidden_claims"]

    before_logs = len(client.app.state.repository.list_research_logs())
    response = client.post(
        "/api/admin/prompt-dry-run",
        headers=ADMIN_HEADERS,
        json={
            "event_id": initialized["event_id"],
            "condition_key": "no_ebl_roleplay",
            "persona_id": initialized["personas"][0]["id"],
            "sample_user_message": "請以人物資訊邊界回應。",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    module_names = [module["name"] for module in payload["modules"]]
    assert module_names[0] == "general_prompt"
    assert module_names.index("independent_2_prompt") < module_names.index("interaction_runtime")
    assert module_names.index("interaction_runtime") < module_names.index("independent_1_prompt")
    assert module_names.index("independent_1_prompt") < module_names.index("persona_event_context")
    assert payload["response"]
    assert len(client.app.state.repository.list_research_logs()) == before_logs

    missing_attempt = client.post(
        "/api/admin/prompt-dry-run",
        headers=ADMIN_HEADERS,
        json={
            "event_id": initialized["event_id"],
            "condition_key": "ebl_roleplay",
            "persona_id": initialized["personas"][0]["id"],
            "sample_user_message": "請檢查我的理由。",
        },
    )
    assert missing_attempt.status_code == 400
    assert "task_attempt_id" in missing_attempt.json()["detail"]
