from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.core.error_elicitation_contract import (
    ERROR_ELICITATION_CONTRACT_VERSION,
    ErrorElicitationQuestionResult,
    ErrorElicitationItemJudgement,
)
from app.models.domain import TaskAttempt
from app.schemas.requests import TaskDraftRequest, TaskSubmitRequest


@pytest.mark.parametrize("request_type", [TaskDraftRequest, TaskSubmitRequest])
def test_request_preserves_raw_rationale_and_json_roundtrip(request_type):
    raw = {
        "contract_version": ERROR_ELICITATION_CONTRACT_VERSION,
        "answers": [{"question_id": "q01", "value": False, "rationale": "  作品晚於事件。\n仍需其他證據。  ", "prompt": "原題"}],
        "answer_text": "原始作答文字",
    }
    original = deepcopy(raw)
    request = request_type(session_id="session-1", response_payload=raw)
    attempt = TaskAttempt(
        task_id="task-1",
        event_id="event-1",
        session_id="session-1",
        response_payload=request.response_payload,
    )

    assert TaskAttempt.model_validate_json(attempt.model_dump_json()).response_payload == original
    assert request.model_dump()["response_payload"] == original
    assert raw == original


def test_draft_allows_incomplete_answers_without_inventing_rationale():
    raw = {"contract_version": ERROR_ELICITATION_CONTRACT_VERSION, "answers": [{"question_id": "q01", "value": None}]}
    request = TaskDraftRequest(session_id="session-1", response_payload=raw)
    assert request.response_payload == raw
    assert "rationale" not in request.response_payload["answers"][0]


@pytest.mark.parametrize(
    "answers",
    [
        [{"question_id": "q01"}, {"question_id": "q01"}],
        [{"question_id": " "}],
        [{"question_id": "q01", "value": ["A", "B"]}],
        [{"question_id": "q01", "rationale": False}],
    ],
)
def test_request_rejects_invalid_answer_shape(answers):
    with pytest.raises(ValidationError):
        TaskSubmitRequest(session_id="session-1", response_payload={
            "contract_version": ERROR_ELICITATION_CONTRACT_VERSION,
            "answers": answers,
        })


@pytest.mark.parametrize("version", [None, "unknown-version"])
def test_request_rejects_unknown_contract(version):
    with pytest.raises(ValidationError):
        TaskDraftRequest(session_id="session-1", response_payload={"contract_version": version, "answers": []})


@pytest.mark.parametrize("answer_correct,reasoning_correct", [(True, True), (True, False), (False, True), (False, False)])
def test_question_result_requires_both_answer_and_reasoning(answer_correct, reasoning_correct):
    expected = "correct" if answer_correct and reasoning_correct else "incorrect"
    raw = {
        "question_id": "q01",
        "answer_correct": answer_correct,
        "reasoning_correct": reasoning_correct,
        "reasoning_feedback": "理由能支持答案。" if reasoning_correct else "未說明來源與結論的關係。",
        "historical_thinking_tags": ["evidence"],
        "correctness": expected,
    }
    result = ErrorElicitationQuestionResult.model_validate(raw)
    assert ErrorElicitationQuestionResult.model_validate_json(result.model_dump_json()).correctness == expected

    with pytest.raises(ValidationError):
        ErrorElicitationQuestionResult.model_validate({**raw, "correctness": "incorrect" if expected == "correct" else "correct"})


@pytest.mark.parametrize(
    "changes",
    [
        {"reasoning_feedback": " "},
        {"reasoning_correct": "false"},
        {"answer_correct": "true"},
        {"answer_feedback": " "},
        {"historical_thinking_tags": ["evidence", "evidence"]},
        {"reasoning_issue_types": ["reasoning_error"]},
    ],
)
def test_reasoning_judgement_requires_specific_consistent_result(changes):
    with pytest.raises(ValidationError):
        ErrorElicitationItemJudgement.model_validate({
            "question_id": "q01",
            "reasoning_correct": False,
            "reasoning_feedback": "沒有說明理由，不能據此推測學生的歷史觀念。",
            "historical_thinking_tags": [],
            **changes,
        })
