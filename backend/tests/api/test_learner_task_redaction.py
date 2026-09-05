import json

import pytest

from app.core.learner_task_view import learner_view
from app.core.research_reproducibility import record_session_material_snapshot
from app.models.domain import ChatMessage, Conversation, Event, EventTask, ExperimentSession, Persona, TaskAttempt, utc_now
from app.schemas.responses import ChatOperationStatusResponse, ChatResponse, TaskDraftResponse


FULL_TEXT = "Read the materials. Which rule applied? {{blank:q01}}"
RATIONALE = "  I guessed.\nI need to explain the link.  "
PRIVATE_VALUES = (
    "PRIVATE_ORIGINAL", "PRIVATE_SOURCE", "PRIVATE_CRITERIA", "PRIVATE_EXPLANATION",
    "PRIVATE_FEEDBACK", "PRIVATE_EXPECTED", "PRIVATE_RUBRIC", "PRIVATE_FALLBACK",
    "PRIVATE_ANSWER_REVIEW",
)


def _seed(client, admin_test=False):
    repository = client.app.state.repository
    condition = repository.get_condition_by_key("ebl_roleplay")
    event = repository.save_event(Event(canonical_name="Redaction test", materials_locked_at=utc_now()))
    task = repository.save_event_task(EventTask(
        event_id=event.id,
        story_text="PRIVATE_ORIGINAL",
        error_elicitation_task_full_text=FULL_TEXT,
        evaluation_payload={
            "contract_version": "error_elicitation_v1",
            "rubric": "PRIVATE_RUBRIC",
            "all_correct_fallback": {"correct_interpretation": "PRIVATE_FALLBACK"},
            "materials": [{
                "id": "m01", "title": "Public material", "text": "Public evidence",
                "image_url": "/images/material.png", "source_url": "https://example.org/source",
                "attribution": "Public archive credit",
                "caption": "Artist, 1850; depicting events in 1600.",
                "reasoning_criteria": "PRIVATE_CRITERIA",
            }],
            "questions": [{
                "id": "q01", "blank_id": "q01", "type": "multiple_choice", "required": True,
                "options": [
                    {"id": "opt-a", "value": "A", "label": "Public A", "explanation": "PRIVATE_EXPLANATION"},
                    {"id": "opt-b", "value": "B", "label": "Public B"},
                ],
                "correct_answer": "PRIVATE_EXPECTED", "source_text": "PRIVATE_SOURCE",
                "reasoning_criteria": "PRIVATE_CRITERIA", "explanation": "PRIVATE_EXPLANATION",
            }],
        },
    ))
    repository.save_persona(Persona(event_id=event.id, name="Historical person"))
    session = repository.save_session(ExperimentSession(
        event_id=event.id, condition_id=condition.id, condition_key_snapshot=condition.condition_key,
        user_id="participant-001", is_admin_test=admin_test, status="conversation_started",
    ))
    attempt = repository.save_task_attempt(TaskAttempt(
        task_id=task.id, event_id=event.id, session_id=session.id, user_id=session.user_id, status="submitted",
        response_payload={
            "contract_version": "error_elicitation_v1",
            "answers": [{"question_id": "q01", "value": "B", "rationale": RATIONALE}],
        },
        judgement_payload={
            "contract_version": "error_elicitation_v1", "result": "incorrect", "score": 0,
            "error_elicitation_task_full_text": FULL_TEXT, "feedback": "PRIVATE_FEEDBACK",
            "question_results": [{
                "question_id": "q01", "blank_id": "q01", "question_type": "multiple_choice",
                "question_text": "Which rule applied? {{blank:q01}}", "source_text": "PRIVATE_SOURCE",
                "learner_answer": "B", "learner_rationale": RATIONALE,
                "answer_correct": True, "reasoning_correct": False,
                "reasoning_feedback": "PRIVATE_FEEDBACK",
                "historical_thinking_tags": ["evidence"],
                "reasoning_criteria": "PRIVATE_CRITERIA", "correctness": "incorrect",
                "expected_answer": "PRIVATE_EXPECTED",
                "evidence_ids": ["m01"],
            }],
        },
    ))
    conversation = repository.save_conversation(Conversation(
        event_id=event.id, session_id=session.id, task_attempt_id=attempt.id, user_id=session.user_id,
    ))
    message = repository.add_message(ChatMessage(
        conversation_id=conversation.id, speaker_type="assistant", speaker_name="Tutor", content="Explain your reasoning.",
        metadata={
            "judgement": attempt.judgement_payload,
            "interaction_policy_version": "2x2-interaction-v7", "target_question_id": "q01",
            "dialogue_state": "ELICIT_REASONING", "disclosure_level": "D0", "completion_status": "continue",
            "target_count": 1, "target_sequence_number": 1,
            "historical_thinking_tags": ["evidence"],
            "llm_call": {"total_tokens": 18},
            "answer_review": {"status": "completed", "findings": ["PRIVATE_ANSWER_REVIEW"]},
            "nested": {"judgement": attempt.judgement_payload, "keep": "runtime"},
        },
    ))
    record_session_material_snapshot(repository, session)
    return event, task, session, attempt, conversation, message


def _assert_private_absent(payload):
    serialized = json.dumps(payload)
    assert '"answer_review"' not in serialized
    for private in PRIVATE_VALUES:
        assert private not in serialized


def _assert_public_task(task):
    assert task["story_text"] == ""
    assert task["error_elicitation_task_full_text"] == FULL_TEXT
    assert task["evaluation_payload"]["questions"] == [{
        "id": "q01", "blank_id": "q01", "type": "multiple_choice", "required": True,
        "options": [{"id": "opt-a", "value": "A", "label": "Public A"}, {"id": "opt-b", "value": "B", "label": "Public B"}],
    }]
    assert task["evaluation_payload"]["materials"][0]["text"] == "Public evidence"
    assert task["evaluation_payload"]["materials"][0]["image_url"] == "/images/material.png"
    assert task["evaluation_payload"]["materials"][0]["caption"] == "Artist, 1850; depicting events in 1600."
    assert "attribution" not in task["evaluation_payload"]["materials"][0]
    assert "source_url" not in task["evaluation_payload"]["materials"][0]
    _assert_private_absent(task)


def _assert_public_message(message):
    metadata = message["metadata"]
    assert "judgement" not in metadata
    assert metadata["nested"] == {"keep": "runtime"}
    assert metadata["target_question_id"] == "q01"
    assert metadata["completion_status"] == "continue"
    assert metadata["target_count"] == 1
    assert metadata["llm_call"] == {"total_tokens": 18}
    _assert_private_absent(message)


@pytest.mark.parametrize("admin_test", [False, True])
def test_learner_initialize_resume_submission_and_conversation_redact_but_admin_retains(client, admin_test):
    event, task, session, attempt, conversation, message = _seed(client, admin_test)
    headers = {"x-admin-key": "test-admin"} if admin_test else {}
    task_before = task.model_dump()
    attempt_before = attempt.model_dump()
    message_before = message.model_dump()

    initialized = client.post("/api/event/initialize", headers=headers, json={
        "event_name": event.canonical_name, "condition_key": session.condition_key_snapshot,
        "user_id": session.user_id,
    })
    assert initialized.status_code == 200, initialized.text
    _assert_public_task(initialized.json()["task"])
    _assert_private_absent(initialized.json())

    resumed = client.get(f"/api/sessions/{session.id}/state", headers=headers)
    assert resumed.status_code == 200, resumed.text
    _assert_public_task(resumed.json()["task"])
    _assert_private_absent(resumed.json())
    assert resumed.json()["attempt"]["response_payload"]["answers"][0]["rationale"] == RATIONALE

    submitted = client.get(f"/api/tasks/attempts/{attempt.id}", headers=headers)
    assert submitted.status_code == 200, submitted.text
    result = submitted.json()["result"]
    _assert_public_task(result["task"])
    _assert_private_absent(submitted.json())
    public_result = result["judgement"]["question_results"][0]
    assert public_result["correctness"] == "incorrect"
    assert public_result["answer_correct"] is True
    assert public_result["reasoning_correct"] is False
    assert "reasoning_feedback" not in public_result
    _assert_public_message(result["history"][0])

    loaded = client.get(f"/api/conversations/{conversation.id}", headers=headers)
    assert loaded.status_code == 200, loaded.text
    _assert_public_task(loaded.json()["task"])
    _assert_public_message(loaded.json()["messages"][0])
    _assert_private_absent(loaded.json())

    created = client.post("/api/conversations", headers=headers, json={
        "event_id": event.id, "task_attempt_id": attempt.id, "session_id": session.id, "user_id": session.user_id,
    })
    assert created.status_code == 200, created.text
    _assert_public_message(created.json()["history"][0])

    listed = client.get("/api/events", headers=headers)
    assert listed.status_code == 200
    _assert_private_absent(listed.json())

    snapshot = client.get("/api/admin/snapshot", headers={"x-admin-key": "test-admin"})
    assert snapshot.status_code == 200
    assert snapshot.json()["events"][0]["latest_task"]["evaluation_payload"] == task.evaluation_payload
    assert snapshot.json()["events"][0]["latest_task"]["story_text"] == "PRIVATE_ORIGINAL"
    research = client.get(f"/api/admin/sessions/{session.id}/research", headers={"x-admin-key": "test-admin"})
    assert research.status_code == 200, research.text
    assert research.json()["attempt"]["judgement_payload"] == attempt.judgement_payload
    assert research.json()["messages"][0]["metadata"] == message.metadata
    assert research.json()["material_snapshot"]["hash_verified"] is True
    assert "PRIVATE_CRITERIA" in json.dumps(research.json()["material_snapshot"])
    assert task.model_dump() == task_before
    assert attempt.model_dump() == attempt_before
    assert message.model_dump() == message_before


@pytest.mark.parametrize("admin_test", [False, True])
def test_chat_regular_stream_and_operation_recovery_redact_judgement(client, monkeypatch, admin_test):
    _, _, _, _, conversation, message = _seed(client, admin_test)
    headers = {"x-admin-key": "test-admin"} if admin_test else {}
    learner = message.model_copy(deep=True, update={
        "speaker_type": "learner", "speaker_name": "Learner", "content": "My response",
        "client_request_id": "redaction-turn", "operation_status": "completed",
    })
    response = ChatResponse(response=message.content, assistant_name=message.speaker_name, message=message)
    before = response.model_dump()

    async def fake_chat(request, on_user_persisted=None):
        if on_user_persisted:
            await on_user_persisted(learner)
        return response

    monkeypatch.setattr(client.app.state.chat_service, "chat", fake_chat)
    monkeypatch.setattr(client.app.state.chat_service, "get_operation_status", lambda *args: ChatOperationStatusResponse(
        client_request_id="redaction-turn", status="completed", learner_message=learner, response=response,
    ))
    request = {"conversation_id": conversation.id, "user_message": "Discuss the event.", "client_request_id": "redaction-turn"}
    regular = client.post("/api/chat", headers=headers, json=request)
    assert regular.status_code == 200, regular.text
    _assert_public_message(regular.json()["message"])

    operation = client.get(f"/api/chat/operations/redaction-turn?conversation_id={conversation.id}", headers=headers)
    assert operation.status_code == 200, operation.text
    _assert_public_message(operation.json()["learner_message"])
    _assert_public_message(operation.json()["response"]["message"])

    stream = client.post("/api/chat/stream", headers=headers, json=request)
    assert stream.status_code == 200
    frames = [json.loads(line.removeprefix("data: ")) for line in stream.text.splitlines() if line.startswith("data: ")]
    _assert_private_absent(frames)
    _assert_public_message(next(frame for frame in frames if frame["type"] == "user_message")["message"])
    _assert_public_message(next(frame for frame in frames if frame["type"] == "complete")["response"]["message"])
    assert response.model_dump() == before
    assert learner.metadata["judgement"]


def test_draft_endpoint_copies_even_an_existing_service_attempt(client, monkeypatch):
    _, task, session, attempt, _, _ = _seed(client)
    original = TaskDraftResponse(attempt=attempt)
    monkeypatch.setattr(client.app.state.task_service, "save_draft", lambda *args: original)
    response = client.patch(f"/api/tasks/{task.id}/draft", json={
        "session_id": session.id, "response_payload": attempt.response_payload,
    })
    assert response.status_code == 200, response.text
    _assert_private_absent(response.json())
    assert response.json()["attempt"]["response_payload"] == attempt.response_payload
    assert "PRIVATE_CRITERIA" in json.dumps(original.model_dump(mode="json"))


def test_redacted_domain_copies_remain_valid_and_do_not_share_mutable_materials(client):
    _, task, _, attempt, _, _ = _seed(client)
    public_task = learner_view(task)
    public_attempt = learner_view(attempt)
    assert isinstance(public_task, EventTask)
    assert isinstance(public_attempt, TaskAttempt)
    EventTask.model_validate(public_task.model_dump())
    TaskAttempt.model_validate(public_attempt.model_dump())
    public_task.evaluation_payload["materials"][0]["text"] = "Changed copy"
    public_attempt.response_payload["answers"][0]["rationale"] = "Changed copy"
    assert task.evaluation_payload["materials"][0]["text"] == "Public evidence"
    assert attempt.response_payload["answers"][0]["rationale"] == RATIONALE


def test_actual_chat_preserves_reasoning_target_and_raw_prompt_in_admin_research(client):
    _, _, session, _, conversation, _ = _seed(client)
    response = client.post("/api/chat", json={
        "conversation_id": conversation.id,
        "user_message": "What evidence supports this interpretation?",
        "client_request_id": "reasoning-target-research",
    })
    assert response.status_code == 200, response.text
    metadata = response.json()["message"]["metadata"]
    assert metadata["target_question_id"] == "q01"
    assert metadata["probe_kind"] == "reasoning_gap"
    assert metadata["answer_correct"] is True
    assert metadata["reasoning_correct"] is False
    assert "reasoning_issue_types" not in metadata
    assert metadata["historical_thinking_tags"] == ["evidence"]
    _assert_private_absent(response.json())

    research = client.get(f"/api/admin/sessions/{session.id}/research", headers={"x-admin-key": "test-admin"})
    assert research.status_code == 200, research.text
    record = research.json()["prompt_records"][0]
    assert record["hash_verified"] is True
    learner_task = next(module["content"] for module in record["modules"] if module["name"] == "learner_task")
    task_context = json.loads(learner_task.split("Task context: ", 1)[1])
    assert task_context["question_results"][0]["learner_rationale"] == RATIONALE
    assert task_context["question_results"][0]["reasoning_criteria"] == "PRIVATE_CRITERIA"
    assert task_context["error_elicitation_task_full_text"] == FULL_TEXT
    assert "reasoning_issue_types" not in research.json()["messages"][-1]["metadata"]
