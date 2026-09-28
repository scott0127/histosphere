"""Shared completion must not turn Standard Chat into an EBL intervention."""
import pytest

from app.core.interaction_contract import build_interaction_runtime, resolve_interaction_metadata
from app.models.domain import ChatMessage
from app.services.learning_focus import build_learning_focus
from app.services.prompt_service import PromptService
from tests.unit.test_interaction_contract import _condition, _multi_error_attempt, _opening_metadata


def _opening(condition, attempt):
    return ChatMessage(conversation_id="shared", speaker_type="assistant", speaker_name="AI",
                       content="Opening", metadata=_opening_metadata(condition, attempt, "Opening"))


def _completion(code):
    return {
        "dialogue_state": "STANDARD_CHAT" if code in {"01", "03"} else "RESOLVED",
        "dialogue_move": "natural_response" if code in {"01", "03"} else "resolution",
        "disclosure_level": None if code in {"01", "03"} else "D0",
        "completion_status": "resolved", "learner_progress": "resolved",
        "resolution_error_recognized": True, "resolution_error_reflected": True,
        "resolution_self_corrected": True,
    }


def _reply(metadata):
    return ChatMessage(conversation_id="shared", speaker_type="assistant", speaker_name="AI",
                       content="Reply", metadata=metadata)


@pytest.mark.parametrize("code", ["01", "02", "03", "04"])
@pytest.mark.parametrize("missing", ["resolution_error_recognized", "resolution_error_reflected", "resolution_self_corrected"])
def test_partial_revision_never_completes_a_question(code, missing):
    condition, attempt = _condition(code), _multi_error_attempt()
    opening = _opening(condition, attempt)
    runtime = build_interaction_runtime(condition, attempt, [opening])
    raw = _completion(code)
    raw[missing] = False
    metadata = resolve_interaction_metadata(runtime, raw, "下一次我們再談。")
    assert metadata["completion_status"] == "continue"
    assert not metadata["resolution_criteria_met"]
    assert "incomplete_resolution_criteria" in metadata["fidelity_flags"]
    assert build_learning_focus(condition, attempt, [opening, _reply(metadata)]).question_id == "q01"


@pytest.mark.parametrize("code", ["01", "02", "03", "04"])
def test_opening_and_off_topic_cannot_create_completion(code):
    condition, attempt = _condition(code), _multi_error_attempt()
    raw = _completion(code)
    metadata = resolve_interaction_metadata(build_interaction_runtime(condition, attempt, []), raw,
                                            "開場", is_opening=True)
    assert metadata["completion_status"] == "continue"
    assert not metadata["resolution_criteria_met"]
    assert not metadata["resolution_self_corrected"]
    assert raw["resolution_self_corrected"] is True  # no mutation of provider evidence
    opening = _opening(condition, attempt)
    metadata = resolve_interaction_metadata(build_interaction_runtime(condition, attempt, [opening]),
                                            {**raw, "off_topic_redirect": True}, "回到本事件。")
    assert metadata["completion_status"] == "continue"
    assert not metadata["resolution_criteria_met"]


@pytest.mark.parametrize("code", ["01", "03"])
def test_standard_direct_answer_or_agreement_does_not_count_as_learner_correction(code):
    condition, attempt = _condition(code), _multi_error_attempt()
    opening = _opening(condition, attempt)
    runtime = build_interaction_runtime(condition, attempt, [opening])
    metadata = resolve_interaction_metadata(runtime, {
        "dialogue_state": "STANDARD_CHAT", "dialogue_move": "natural_response",
        "completion_status": "continue", "learner_progress": "no_progress",
    }, "正確答案是按人數。接下來看別的問題。")
    assert metadata["completion_status"] == "continue"
    assert build_learning_focus(condition, attempt, [opening, _reply(metadata)]).question_id == "q01"
    assert runtime.allowed_disclosure_levels == ()
    assert not runtime.corrective_feedback_required and not runtime.restatement_required
    assert metadata["primary_ebl_move"] == "none" and metadata["disclosure_level"] is None


@pytest.mark.parametrize("code", ["01", "02", "03", "04"])
def test_current_prompt_moves_forward_and_first_reply_on_next_question_can_resolve(code):
    condition, attempt = _condition(code), _multi_error_attempt()
    opening = _opening(condition, attempt)
    runtime = build_interaction_runtime(condition, attempt, [opening])
    first = _reply(resolve_interaction_metadata(runtime, _completion(code), "本題的理由已修正。"))
    next_runtime = build_interaction_runtime(condition, attempt, [opening, first])
    assert next_runtime.target.question_id == "q02"
    # A missing spoken transition must not force a redundant EBL opening turn.
    second = _reply(resolve_interaction_metadata(next_runtime, _completion(code), "第二題也已修正。"))
    assert second.metadata["completion_status"] == "resolved"
    focus = build_learning_focus(condition, attempt, [opening, first, second])
    assert focus.status == "completed" and focus.question_id is None
    before = PromptService._error_elicitation_context(attempt.judgement_payload, runtime)
    after = PromptService._error_elicitation_context(attempt.judgement_payload, next_runtime)
    assert '"question_id": "q01"' in before and '"question_id": "q02"' not in before
    assert '"question_id": "q02"' in after and '"question_id": "q01"' not in after
    assert attempt.judgement_payload["question_results"][0]["correctness"] == "incorrect"


@pytest.mark.parametrize("code", ["01", "03"])
def test_legacy_standard_history_starts_shared_tracking_without_inventing_past_completion(code):
    condition, attempt = _condition(code), _multi_error_attempt()
    legacy = _reply({
        "interaction_policy_version": "2x2-interaction-v16-reviewed-transition",
        "dialogue_state": "STANDARD_CHAT", "completion_status": "continue",
        "learner_revision_status": "revised", "target_question_id": None,
    })
    runtime = build_interaction_runtime(condition, attempt, [legacy])
    assert runtime.target.question_id == "q01"
    assert runtime.allowed_states == ("STANDARD_CHAT",)
    done = _reply(resolve_interaction_metadata(runtime, _completion(code), "已修正。"))
    assert build_learning_focus(condition, attempt, [legacy, done]).question_id == "q02"


@pytest.mark.parametrize("code", ["01", "03"])
def test_no_target_cannot_be_marked_as_a_learner_correction(code):
    condition = _condition(code)
    runtime = build_interaction_runtime(condition, None, [])
    result = resolve_interaction_metadata(runtime, _completion(code), "一般歷史討論。")
    assert result["completion_status"] == "continue"
    assert result["resolution_outcome"] == "no_target"
    assert result["learner_progress"] == "not_assessed"
    assert not result["resolution_criteria_met"]
