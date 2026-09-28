import pytest

from app.core.interaction_contract import INTERACTION_POLICY_VERSION
from app.models.domain import ChatMessage
from app.services.learning_focus import build_learning_focus
from tests.unit.test_interaction_contract import _condition, _multi_error_attempt


def _message(question_id="q01", **metadata):
    return ChatMessage(
        conversation_id="conversation-1", speaker_type="assistant", speaker_name="Tutor", content="Public reply",
        metadata={"interaction_policy_version": INTERACTION_POLICY_VERSION,
                  "target_question_id": question_id, "dialogue_state": "SELF_CORRECT",
                  "disclosure_level": "D4", "completion_status": "continue", **metadata},
    )


@pytest.mark.parametrize("code", ["01", "02", "03", "04"])
def test_focus_uses_canonical_condition_and_safe_fields_only(code):
    focus = build_learning_focus(_condition(code), _multi_error_attempt(), [])
    assert focus.model_dump() == {
        "question_id": "q01", "status": "active", "origin": "learner", "claim": None,
    }


@pytest.mark.parametrize("completion", ["continue", "final_answer_pending", "corrective_resolution_pending"])
def test_pending_feedback_and_restatement_keep_the_old_question(completion):
    focus = build_learning_focus(_condition("02"), _multi_error_attempt(), [_message(completion_status=completion)])
    assert focus.question_id == "q01" and focus.status == "active"


@pytest.mark.parametrize("completion", ["resolved", "feedback_completed"])
@pytest.mark.parametrize("held", [False, True])
def test_only_committed_resolution_advances_and_completes(completion, held):
    attempt = _multi_error_attempt()
    first = _message(completion_status=completion, next_target_started=True, next_target_question_id="q02",
                     answer_delivery={"state_held": held})
    focus = build_learning_focus(_condition("04"), attempt, [first])
    assert focus.question_id == ("q01" if held else "q02")
    second = _message("q02", completion_status=completion)
    final = build_learning_focus(_condition("04"), attempt, [first, second])
    assert final.model_dump() == ({"question_id": "q01", "status": "active", "origin": "learner", "claim": None}
                                 if held else {"question_id": None, "status": "completed", "origin": None, "claim": None})


@pytest.mark.parametrize("code", ["01", "02", "03", "04"])
def test_all_correct_fallback_is_third_party_and_exposes_only_claim(code):
    attempt = _multi_error_attempt()
    for result in attempt.judgement_payload["question_results"]:
        result["correctness"] = "correct"
    assert build_learning_focus(_condition(code), attempt, []).status == "none"
    attempt.judgement_payload["all_correct_fallback"] = {
        "id": "third-party-1", "incorrect_claim": "  Public claim  ",
        "correct_interpretation": "PRIVATE_ANSWER", "source_text": "PRIVATE_SOURCE",
        "reasoning_criteria": "PRIVATE_CRITERIA",
    }
    focus = build_learning_focus(_condition(code), attempt, [])
    assert focus.model_dump() == {
        "question_id": "third-party-1", "status": "active", "origin": "third_party", "claim": "Public claim",
    }
    completed = build_learning_focus(_condition(code), attempt, [_message("third-party-1", completion_status="resolved")])
    assert completed.model_dump() == {"question_id": None, "status": "completed", "origin": None, "claim": None}


def test_missing_attempt_condition_and_legacy_target_are_explicit():
    assert build_learning_focus(None, None, []) is None
    assert build_learning_focus(_condition("02"), None, []).model_dump() == {
        "question_id": None, "status": "none", "origin": None, "claim": None,
    }
    attempt = _multi_error_attempt()
    attempt.judgement_payload = {"misconception_summary": "PRIVATE_DIAGNOSIS"}
    assert build_learning_focus(_condition("02"), attempt, []).model_dump() == {
        "question_id": None, "status": "active", "origin": "learner", "claim": None,
    }
    assert build_learning_focus(_condition("02"), attempt, [_message(None, completion_status="resolved")]).status == "completed"
