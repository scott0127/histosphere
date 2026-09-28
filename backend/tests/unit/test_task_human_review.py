import asyncio
from copy import deepcopy

import pytest
from fastapi import HTTPException

from app.core.interaction_contract import build_interaction_runtime
from app.core.learner_task_view import learner_view
from app.schemas.requests import ChatRequest
from app.schemas.task_review import TaskReviewDraftRequest
from app.services.task_review_service import TaskReviewService
from app.services.research_export_service import ResearchExportService
from tests.api.test_error_elicitation_workflow import HEADERS, answers, initialize, judged


@pytest.fixture
def pending(client):
    initialized = initialize(client, "ebl_no_roleplay")

    async def judge(*args):
        return judged()

    client.app.state.llm_provider.judge_task_attempt = judge
    accepted = client.post(f"/api/tasks/{initialized['task']['id']}/submit", headers=HEADERS, json={
        "session_id": initialized["session_id"], "response_payload": answers(), "user_id": "participant-001",
    })
    assert accepted.status_code == 202, accepted.text
    attempt = client.app.state.repository.get_task_attempt(accepted.json()["attempt_id"])
    assert attempt.status == "awaiting_review"
    return initialized, attempt


def reviewed(service, attempt, *, rows=None):
    rows = deepcopy(rows if rows is not None else attempt.review_payload["question_results"])
    for row in rows:
        row["reviewed"] = True
    return service.save_draft(attempt.id, TaskReviewDraftRequest(
        expected_version=attempt.review_version, question_results=rows,
    ))


def test_judge_waits_for_every_human_review_and_hides_private_checkpoints(client, pending):
    initialized, attempt = pending
    repository = client.app.state.repository
    assert repository.get_conversation_by_session(attempt.session_id) is None
    assert repository.get_session(attempt.session_id).timer_started_at is None
    assert attempt.ai_judgement_payload["question_results"][1]["reasoning_correct"] is False
    assert attempt.judgement_payload == {}
    response = client.get(f"/api/tasks/attempts/{attempt.id}", headers=HEADERS).json()
    public = response["attempt"]
    assert public["ai_judgement_payload"] == public["review_payload"] == public["judgement_payload"] == {}
    assert response["result"] is None
    service = TaskReviewService(repository)
    with pytest.raises(HTTPException, match="every question"):
        service.approve(attempt.id, 0)
    assert repository.get_task_attempt(attempt.id).status == "awaiting_review"


def test_review_draft_survives_recreation_and_rejects_stale_window(client, pending):
    _, attempt = pending
    repository = client.app.state.repository
    service = TaskReviewService(repository)
    rows = deepcopy(attempt.review_payload["question_results"])
    rows[0]["reviewed"] = True
    rows[0]["override_reason"] = "人工核對備註，不提供受測者。"
    saved = service.save_draft(attempt.id, TaskReviewDraftRequest(expected_version=0, question_results=rows))
    recovered = TaskReviewService(repository).load(attempt.id)
    assert recovered.review_payload == saved.review_payload
    assert recovered.review_version == 1
    with pytest.raises(HTTPException) as stale:
        service.save_draft(attempt.id, TaskReviewDraftRequest(expected_version=0, question_results=rows))
    assert stale.value.status_code == 409
    assert "人工核對備註" not in learner_view(recovered).model_dump_json()


@pytest.mark.parametrize("invalid", ["missing", "duplicate"])
def test_review_cannot_omit_or_duplicate_questions(client, pending, invalid):
    _, attempt = pending
    rows = deepcopy(attempt.review_payload["question_results"])
    if invalid == "missing":
        rows.pop()
    else:
        rows[-1] = deepcopy(rows[0])
    with pytest.raises(HTTPException) as error:
        TaskReviewService(client.app.state.repository).save_draft(attempt.id, TaskReviewDraftRequest(
            expected_version=0, question_results=rows,
        ))
    assert error.value.status_code == 422


def test_revised_boolean_requires_reason_and_matching_diagnostic(client, pending):
    _, attempt = pending
    service = TaskReviewService(client.app.state.repository)
    rows = deepcopy(attempt.review_payload["question_results"])
    rows[1]["reasoning_correct"] = True
    saved = reviewed(service, attempt, rows=rows)
    with pytest.raises(HTTPException, match="reason for changing"):
        service.approve(saved.id, saved.review_version)
    rows[1]["override_reason"] = "這份理由已符合本題判準。"
    saved = reviewed(service, saved, rows=rows)
    with pytest.raises(HTTPException, match="update the explanation"):
        service.approve(saved.id, saved.review_version)


def test_final_judgement_drives_target_and_initial_judgement_remains_immutable(client, pending):
    _, attempt = pending
    repository = client.app.state.repository
    service = TaskReviewService(repository)
    original = deepcopy(attempt.ai_judgement_payload)
    rows = deepcopy(attempt.review_payload["question_results"])
    rows[1].update({"reasoning_correct": True, "reasoning_feedback": "人工已依題目判準確認理由成立。",
                    "override_reason": "初判未接受學生的等義表述。"})
    saved = reviewed(service, attempt, rows=rows)
    approved = service.approve(saved.id, saved.review_version, "researcher")
    assert approved.status == "preparing_chat"
    assert approved.ai_judgement_payload == original
    assert approved.judgement_payload["question_results"][1]["correctness"] == "correct"
    assert approved.judgement_payload["question_results"][1]["reasoning_feedback"] == rows[1]["reasoning_feedback"]
    condition = repository.get_condition_by_key("ebl_no_roleplay")
    runtime = build_interaction_runtime(condition, approved, [])
    assert runtime.target.question_id == "q03"
    assert runtime.target_count == 1
    assert service.approve(saved.id, saved.review_version).review_version == approved.review_version
    with pytest.raises(HTTPException) as frozen:
        service.save_draft(saved.id, TaskReviewDraftRequest(expected_version=approved.review_version, question_results=rows))
    assert frozen.value.status_code == 409
    tampered = repository.get_task_attempt(saved.id)
    tampered.ai_judgement_payload["result"] = "tampered"
    with pytest.raises(ValueError, match="initial task judgements"):
        repository.save_task_attempt(tampered)


def test_ready_does_not_start_timer_or_allow_chat_until_entered(client, pending):
    _, attempt = pending
    state = client.app.state
    review = TaskReviewService(state.repository)
    saved = reviewed(review, attempt)
    review.approve(saved.id, saved.review_version)
    asyncio.run(state.task_service.process_submission(saved.id))
    ready = state.repository.get_task_attempt(saved.id)
    assert ready.status == "ready"
    assert state.repository.get_session(ready.session_id).timer_ends_at is None
    conversation = state.repository.get_conversation_by_session(ready.session_id)
    waiting_state = state.session_service.load_state(ready.session_id)
    assert waiting_state.conversation_id is None
    assert waiting_state.learning_focus is None
    assert state.task_service.submission_status(ready.id).result is None
    assert state.session_service._public_status("initialized", "ready", True) == "task_submitted"
    progress = state.session_service.user_progress(ready.user_id, admin_test=True)
    assert next(row for row in progress.progress if row.session_id == ready.session_id).conversation_id is None
    with pytest.raises(HTTPException) as blocked:
        asyncio.run(state.chat_service.chat(ChatRequest(conversation_id=conversation.id, user_message="test")))
    assert blocked.value.status_code == 409
    with pytest.raises(HTTPException):
        state.conversation_service.load_conversation(conversation.id)
    result = state.task_service.enter_interaction(ready.id)
    assert result.attempt.status == "submitted"
    timer = state.repository.get_session(ready.session_id).timer_ends_at
    state.task_service.enter_interaction(ready.id)
    assert state.repository.get_session(ready.session_id).timer_ends_at == timer
    assert len(state.repository.list_messages(conversation.id)) == 1
    public = learner_view(result).model_dump_json()
    assert '"ai_judgement_payload":{}' in public
    assert '"review_payload":{}' in public
    assert "approved_at" not in public


def test_saved_initial_judgement_resumes_without_another_llm_call(client, pending):
    _, attempt = pending
    state = client.app.state
    initial = deepcopy(attempt.ai_judgement_payload)
    # Simulate a persisted judge checkpoint before the stage transition was acknowledged.
    attempt.status = "processing"
    state.repository.save_task_attempt(attempt)

    async def forbidden(*args):
        raise AssertionError("A saved initial judgement must never be rerun")

    state.task_service.llm_provider.judge_task_attempt = forbidden
    asyncio.run(state.task_service.process_submission(attempt.id))
    recovered = state.repository.get_task_attempt(attempt.id)
    assert recovered.status == "awaiting_review"
    assert recovered.ai_judgement_payload == initial


def test_initial_judge_usage_is_available_while_human_review_is_pending(client, pending):
    _, attempt = pending
    attempt.ai_judgement_payload["llm_call"] = {"total_tokens": 42}
    assert ResearchExportService._judgement_llm_call(attempt) == {"total_tokens": 42}
    assert attempt.judgement_payload == {}
