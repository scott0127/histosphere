import pytest

from app.core.experiment_conditions import EXPERIMENT_CONDITION_DEFINITIONS
from app.core.interaction_contract import (
    INTERACTION_POLICY_VERSION,
    build_interaction_runtime,
    enforce_interaction_response,
    initial_greeting_metadata,
    resolve_interaction_metadata,
)
from app.core.historical_ebl_policy import HISTORICAL_EBL_POLICY_VERSION
from app.models.domain import ChatMessage, ExperimentCondition, TaskAttempt


def _condition(code: str) -> ExperimentCondition:
    definition = next(item for item in EXPERIMENT_CONDITION_DEFINITIONS if item.code == code)
    return ExperimentCondition(
        condition_key=definition.condition_key,
        label=definition.default_label,
        ebl_enabled=definition.ebl_enabled,
        roleplay_enabled=definition.roleplay_enabled,
        agent_mode=definition.agent_mode,
        response_policy=definition.response_policy,
    )


def _attempt() -> TaskAttempt:
    return TaskAttempt(
        session_id="session-1",
        task_id="task-1",
        event_id="event-1",
        status="submitted",
        judgement_payload={
            "result": "partial",
            "question_results": [
                {
                    "question_id": "q01",
                    "prompt": "第三等級要求如何表決？",
                    "source_text": "第三等級反對每一等級各一票。",
                    "learner_answer": "按等級",
                    "expected_answer": "按人數",
                    "correctness": "incorrect",
                    "error_code": "unclassified",
                    "historical_concept": "cause_and_consequence",
                    "reasoning_process": "argumentation",
                    "evidence_ids": ["E03"],
                }
            ],
        },
    )


def _multi_error_attempt() -> TaskAttempt:
    attempt = _attempt()
    attempt.judgement_payload["question_results"].extend(
        [
            {
                "question_id": "q02",
                "prompt": "財政危機如何影響革命爆發？",
                "source_text": "王室債務與稅制不平等削弱政府財政。",
                "learner_answer": "完全沒有影響",
                "expected_answer": "加劇政治與社會危機",
                "correctness": "partial",
                "error_code": "causal_oversimplification",
                "historical_concept": "cause_and_consequence",
                "reasoning_process": "argumentation",
                "evidence_ids": ["E05"],
            },
            {
                "question_id": "q03",
                "prompt": "巴士底監獄位於巴黎。",
                "learner_answer": True,
                "expected_answer": True,
                "correctness": "correct",
            },
        ]
    )
    return attempt


def test_standard_chat_cells_do_not_force_task_correction():
    for code in ("01", "03"):
        condition = _condition(code)
        runtime = build_interaction_runtime(condition, _attempt(), [])
        metadata = resolve_interaction_metadata(
            runtime,
            {"dialogue_state": "NOTICE_ERROR", "dialogue_move": "error_awareness_prompt"},
            "正確答案是按人數，因為代表權按個別代表計算。",
        )

        assert runtime.interaction_mode == "standard_chat"
        assert metadata["interaction_policy_version"] == INTERACTION_POLICY_VERSION
        assert metadata["condition_code"] == code
        assert metadata["dialogue_state"] == "STANDARD_CHAT"
        assert metadata["dialogue_move"] == "natural_response"
        assert metadata["disclosure_level"] is None
        assert metadata["target_question_id"] is None
        assert metadata["historical_ebl_policy_version"] == HISTORICAL_EBL_POLICY_VERSION


def test_standard_chat_records_off_topic_redirect_without_changing_mode():
    for code in ("01", "03"):
        runtime = build_interaction_runtime(_condition(code), _attempt(), [])
        metadata = resolve_interaction_metadata(
            runtime,
            {
                "dialogue_state": "STANDARD_CHAT",
                "dialogue_move": "natural_response",
                "off_topic_redirect": True,
            },
            "這不屬於目前事件的討論範圍，讓我們回到法國大革命。",
        )

        assert metadata["condition_code"] == code
        assert metadata["interaction_mode"] == "standard_chat"
        assert metadata["dialogue_state"] == "STANDARD_CHAT"
        assert metadata["off_topic_redirect"] is True


def test_ebl_cells_share_the_same_state_contract():
    metadata_by_code = {}
    for code in ("02", "04"):
        condition = _condition(code)
        greeting_metadata = initial_greeting_metadata(
            condition,
            _attempt(),
            "你原本是根據什麼理由作答？",
        )
        greeting = ChatMessage(
            conversation_id="conversation-1",
            speaker_type="persona" if condition.roleplay_enabled else "assistant",
            speaker_name="Persona" if condition.roleplay_enabled else "AI Tutor",
            content="你原本是根據什麼理由作答？",
            metadata=greeting_metadata,
        )
        runtime = build_interaction_runtime(condition, _attempt(), [greeting])
        metadata_by_code[code] = resolve_interaction_metadata(
            runtime,
            {
                "dialogue_state": "REFLECT",
                "dialogue_move": "reflection_prompt",
                "disclosure_level": "D1",
                "learner_revision_status": "not_yet",
            },
            "請對照 E03，這項證據支持哪一種表決方式？",
        )

    assert metadata_by_code["02"]["dialogue_state"] == "REFLECT"
    assert metadata_by_code["04"]["dialogue_state"] == "REFLECT"
    assert metadata_by_code["02"]["dialogue_move"] == metadata_by_code["04"]["dialogue_move"]
    assert metadata_by_code["02"]["target_question_id"] == metadata_by_code["04"]["target_question_id"]
    assert metadata_by_code["02"]["disclosure_level"] == metadata_by_code["04"]["disclosure_level"]
    assert (
        metadata_by_code["02"]["primary_ebl_move"]
        == metadata_by_code["04"]["primary_ebl_move"]
        == "analyze_and_reflect_on_the_error"
    )


def test_ebl_off_topic_redirect_preserves_state_disclosure_and_attempt_count():
    for code in ("02", "04"):
        condition = _condition(code)
        previous = ChatMessage(
            conversation_id="conversation-1",
            speaker_type="persona" if condition.roleplay_enabled else "assistant",
            speaker_name="歷史人物" if condition.roleplay_enabled else "AI Tutor",
            content="先說明你原先判斷的理由。",
            metadata={
                "interaction_policy_version": INTERACTION_POLICY_VERSION,
                "target_question_id": "q01",
                "dialogue_state": "NOTICE_ERROR",
                "dialogue_move": "error_awareness_prompt",
                "disclosure_level": "D1",
                "attempts_in_state": 2,
                "completion_status": "continue",
            },
        )
        runtime = build_interaction_runtime(condition, _attempt(), [previous])
        enforced = enforce_interaction_response(
            runtime,
            {
                "dialogue_state": "REFLECT",
                "dialogue_move": "reflection_prompt",
                "disclosure_level": "D2",
                "learner_progress": "clear_progress",
                "learner_revision_status": "revised",
                "off_topic_redirect": True,
            },
            "這個疑問與眼前事件無關；讓我們回到第三等級的代表權爭議。",
        )

        assert enforced.retry_required is False
        assert enforced.metadata["condition_code"] == code
        assert enforced.metadata["off_topic_redirect"] is True
        assert enforced.metadata["dialogue_state"] == "NOTICE_ERROR"
        assert enforced.metadata["dialogue_move"] == "error_awareness_prompt"
        assert enforced.metadata["disclosure_level"] == "D1"
        assert enforced.metadata["learner_progress"] == "no_progress"
        assert enforced.metadata["learner_revision_status"] == "not_yet"
        assert enforced.metadata["attempts_in_state"] == 2
        assert enforced.metadata["completion_status"] == "continue"
        assert enforced.metadata["next_target_started"] is False
        assert enforced.metadata["fidelity_flags"] == []


def test_invalid_ebl_transition_is_blocked_and_flagged():
    condition = _condition("02")
    greeting_metadata = initial_greeting_metadata(
        condition,
        _attempt(),
        "你原本是根據什麼理由作答？",
    )
    greeting = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="你原本是根據什麼理由作答？",
        metadata=greeting_metadata,
    )
    runtime = build_interaction_runtime(condition, _attempt(), [greeting])
    metadata = resolve_interaction_metadata(
        runtime,
        {
            "dialogue_state": "UNKNOWN_STATE",
            "dialogue_move": "resolution",
            "disclosure_level": "D4",
        },
        "請先說明你的理由？",
    )

    assert metadata["dialogue_state"] == "NOTICE_ERROR"
    assert "invalid_state_transition" in metadata["fidelity_flags"]


def test_resolved_error_does_not_open_correct_items_as_new_targets():
    condition = _condition("02")
    attempt = _attempt()
    attempt.judgement_payload["question_results"].append(
        {
            "question_id": "q02",
            "prompt": "巴士底監獄位於巴黎。",
            "learner_answer": True,
            "expected_answer": True,
            "correctness": "correct",
        }
    )
    resolved = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="你已修正這項判斷。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "target_question_id": "q01",
            "dialogue_state": "RESOLVED",
            "completion_status": "resolved",
        },
    )

    runtime = build_interaction_runtime(condition, attempt, [resolved])

    assert runtime.target is None
    assert runtime.allowed_states == ("RESOLVED",)


def test_ebl_advances_to_the_next_error_and_resets_the_scaffold():
    condition = _condition("02")
    attempt = _multi_error_attempt()
    first_runtime = build_interaction_runtime(condition, attempt, [])

    assert first_runtime.target.question_id == "q01"
    assert first_runtime.next_target.question_id == "q02"
    assert first_runtime.target_sequence_number == 1
    assert first_runtime.target_count == 2

    resolved_first = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="你已完成第一項修正。接著看下一項，先說明你原先的因果判斷。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "target_question_id": "q01",
            "next_target_question_id": "q02",
            "next_target_started": True,
            "dialogue_state": "RESOLVED",
            "disclosure_level": "D4",
            "attempts_in_state": 3,
            "completion_status": "resolved",
        },
    )
    second_runtime = build_interaction_runtime(condition, attempt, [resolved_first])

    assert second_runtime.target.question_id == "q02"
    assert second_runtime.next_target is None
    assert second_runtime.target_sequence_number == 2
    assert second_runtime.target_count == 2
    assert second_runtime.previous_state == "NOTICE_ERROR"
    assert second_runtime.allowed_states == ("NOTICE_ERROR", "REFLECT", "SELF_CORRECT", "RESOLVED")
    assert second_runtime.previous_disclosure_level == "D0"
    assert second_runtime.previous_attempts_in_state == 0

    resolved_second = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="第二項也已完成修正。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "target_question_id": "q02",
            "dialogue_state": "RESOLVED",
            "completion_status": "resolved",
        },
    )
    completed_runtime = build_interaction_runtime(
        condition,
        attempt,
        [resolved_first, resolved_second],
    )

    assert completed_runtime.target is None
    assert completed_runtime.allowed_states == ("RESOLVED",)


def test_resolved_turn_bridges_to_the_next_error_without_exposing_its_answer():
    condition = _condition("02")
    attempt = _multi_error_attempt()
    reflected = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="比較修正前後的理由，指出哪項證據改變了你的判斷。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "target_question_id": "q01",
            "dialogue_state": "REFLECT",
            "dialogue_move": "reflection_prompt",
            "disclosure_level": "D3",
            "attempts_in_state": 0,
            "completion_status": "continue",
        },
    )
    runtime = build_interaction_runtime(condition, attempt, [reflected])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "RESOLVED",
            "dialogue_move": "resolution",
            "disclosure_level": "D4",
            "learner_revision_status": "revised",
            "resolution_error_recognized": True,
            "resolution_error_reflected": True,
            "resolution_self_corrected": True,
        },
        "你已完成這一項修正，正確答案是「按人數」。",
    )

    assert enforced.fallback_applied is False
    assert enforced.retry_required is True
    assert "next_target_transition_missing" in enforced.metadata["fidelity_flags"]
    assert enforced.metadata["next_target_question_id"] == "q02"
    assert enforced.metadata["next_target_started"] is True
    assert enforced.response == "你已完成這一項修正，正確答案是「按人數」。"
    assert "加劇政治與社會危機" not in enforced.response


@pytest.mark.parametrize("missing", ["resolution_error_recognized", "resolution_error_reflected", "resolution_self_corrected"])
def test_resolved_requires_error_recognition_reflection_and_self_correction(missing):
    condition = _condition("02")
    reflected = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="請說明是哪項證據改變了你的判斷。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "target_question_id": "q01",
            "dialogue_state": "REFLECT",
            "dialogue_move": "reflection_prompt",
            "disclosure_level": "D3",
            "completion_status": "continue",
        },
    )
    runtime = build_interaction_runtime(condition, _attempt(), [reflected])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "RESOLVED",
            "dialogue_move": "resolution",
            "disclosure_level": "D4",
            "resolution_error_recognized": True,
            "resolution_error_reflected": True,
            "resolution_self_corrected": True,
            missing: False,
        },
        "你的主張與證據已經接近完整。",
    )

    assert enforced.retry_required is True
    assert enforced.metadata["resolution_criteria_met"] is False
    assert "incomplete_resolution_criteria" in enforced.metadata["fidelity_flags"]


def test_legacy_d4_skip_record_can_still_resume_without_rewriting_history():
    condition = _condition("02")
    previous = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="目前已整理出最強證據，但仍由你完成判斷。",
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
    action_metadata = {
        "interaction_policy_version": "2x2-interaction-v7",
        "target_question_id": "q01",
        "next_target_question_id": "q02",
        "next_target_started": True,
        "dialogue_state": "INSPECT_EVIDENCE",
        "disclosure_level": "D4",
        "completion_status": "unresolved_after_max_support",
    }
    action = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="learner",
        speaker_name="learner",
        content="處理下一個錯誤",
        metadata=action_metadata,
    )

    next_runtime = build_interaction_runtime(condition, _multi_error_attempt(), [previous, action])

    assert action_metadata["completion_status"] == "unresolved_after_max_support"
    assert next_runtime.target.question_id == "q02"
    assert next_runtime.previous_state == "NOTICE_ERROR"
    assert next_runtime.previous_disclosure_level == "D0"


@pytest.mark.parametrize("code", ["02", "04"])
def test_d4_failure_requests_final_answer_without_revealing_or_switching(code):
    previous = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="目前已整理出最強證據，請你完成判斷。",
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
    runtime = build_interaction_runtime(_condition(code), _multi_error_attempt(), [previous])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "SELF_CORRECT",
            "dialogue_move": "final_answer_prompt",
            "disclosure_level": "D4",
            "completion_status": "final_answer_pending",
            "learner_progress": "no_progress",
            "resolution_error_recognized": False,
            "resolution_error_reflected": False,
            "resolution_self_corrected": False,
        },
        "請先用自己的話整理這一題最後的答案與理由。",
    )

    assert runtime.final_answer_required is True
    assert runtime.corrective_feedback_required is False
    assert enforced.retry_required is False
    assert enforced.metadata["completion_status"] == "final_answer_pending"
    assert enforced.metadata["resolution_outcome"] == "awaiting_final_answer"
    assert enforced.metadata["dialogue_move"] == "final_answer_prompt"
    assert enforced.metadata["corrective_feedback_revealed_answer"] is False
    assert enforced.metadata["next_target_started"] is False
    assert "early_answer_exposure" not in enforced.metadata["fidelity_flags"]
    leaked = enforce_interaction_response(
        runtime,
        {"dialogue_state": "SELF_CORRECT", "dialogue_move": "corrective_feedback",
         "disclosure_level": "D4", "completion_status": "feedback_completed"},
        "正確答案是「按人數」。請用自己的話整理答案。",
    )
    assert leaked.retry_required is True
    assert {"early_answer_exposure", "invalid_dialogue_move", "invalid_completion_status"} <= set(leaked.metadata["fidelity_flags"])


def test_d4_success_remains_a_learner_resolution_instead_of_corrective_feedback():
    previous = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="請用最強證據完成你的修正。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "target_question_id": "q01",
            "dialogue_state": "NOTICE_ERROR",
            "dialogue_move": "error_awareness_prompt",
            "disclosure_level": "D4",
            "completion_status": "continue",
        },
    )
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [previous])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "RESOLVED",
            "dialogue_move": "resolution",
            "disclosure_level": "D4",
            "learner_progress": "resolved",
            "resolution_error_recognized": True,
            "resolution_error_reflected": True,
            "resolution_self_corrected": True,
        },
        "你已用證據完成修正，正確答案是「按人數」。",
    )

    assert enforced.retry_required is False
    assert enforced.metadata["dialogue_state"] == "RESOLVED"
    assert enforced.metadata["completion_status"] == "resolved"
    assert enforced.metadata["resolution_outcome"] == "learner_resolved"
    assert enforced.metadata["corrective_feedback_revealed_answer"] is False


def test_terminal_feedback_cannot_close_target_without_showing_the_correct_answer():
    previous = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="目前已提供 D4 支援。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "target_question_id": "q01",
            "dialogue_state": "REFLECT",
            "dialogue_move": "reflection_prompt",
            "disclosure_level": "D4",
            "completion_status": "final_answer_pending",
        },
    )
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [previous])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "RESOLVED",
            "dialogue_move": "corrective_feedback",
            "disclosure_level": "D4",
        },
        "你的判斷仍需要修正。",
    )

    assert enforced.retry_required is True
    assert "corrective_answer_missing" in enforced.metadata["fidelity_flags"]


@pytest.mark.parametrize(
    ("expected_answer", "response_text"),
    [
        (True, "依據題文，這一題的正確判斷是「真」。"),
        (True, "你的最後答案應改為「是」。"),
        (False, "依據題文，這一題的正確判斷是「假」。"),
        (False, "你的最後答案應改為「否」。"),
        (False, "這一句應選「否」。"),
    ],
)
def test_terminal_feedback_accepts_natural_true_false_labels(expected_answer, response_text):
    attempt = _attempt()
    attempt.judgement_payload["question_results"][0]["expected_answer"] = expected_answer
    previous = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="請整理這一題最後的答案與理由。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "target_question_id": "q01",
            "dialogue_state": "SELF_CORRECT",
            "dialogue_move": "final_answer_prompt",
            "disclosure_level": "D4",
            "completion_status": "final_answer_pending",
        },
    )
    runtime = build_interaction_runtime(_condition("02"), attempt, [previous])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "RESOLVED",
            "dialogue_move": "corrective_feedback",
            "disclosure_level": "D4",
        },
        response_text,
    )

    assert enforced.retry_required is False
    assert enforced.metadata["completion_status"] == "feedback_completed"
    assert "corrective_answer_missing" not in enforced.metadata["fidelity_flags"]


def test_terminal_feedback_accepts_standalone_multiple_choice_code():
    attempt = _attempt()
    attempt.judgement_payload["question_results"][0]["expected_answer"] = "A"
    previous = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="請整理這一題最後的答案與理由。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "target_question_id": "q01",
            "dialogue_state": "SELF_CORRECT",
            "dialogue_move": "final_answer_prompt",
            "disclosure_level": "D4",
            "completion_status": "final_answer_pending",
        },
    )
    runtime = build_interaction_runtime(_condition("02"), attempt, [previous])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "RESOLVED",
            "dialogue_move": "corrective_feedback",
            "disclosure_level": "D4",
        },
        "A 才符合材料；兩個方案都有議事機構，但權力歸屬並不相同。",
    )

    assert enforced.retry_required is False
    assert "corrective_answer_missing" not in enforced.metadata["fidelity_flags"]


def test_nonterminal_choice_code_does_not_confuse_source_label_with_answer_leak():
    attempt = _attempt()
    attempt.judgement_payload["question_results"][0]["expected_answer"] = "A"
    runtime = build_interaction_runtime(_condition("02"), attempt, [])
    metadata = {
        "dialogue_state": "NOTICE_ERROR",
        "dialogue_move": "error_awareness_prompt",
        "disclosure_level": "D0",
    }

    source_reference = enforce_interaction_response(
        runtime,
        metadata,
        "資料 A 提供了事件背景，但先說說你原本的推論如何成立。",
    )
    explicit_answer = enforce_interaction_response(
        runtime,
        metadata,
        "這題應選 A。",
    )

    assert "early_answer_exposure" not in source_reference.metadata["fidelity_flags"]
    assert "early_answer_exposure" in explicit_answer.metadata["fidelity_flags"]


@pytest.mark.parametrize("code", ["02", "04"])
@pytest.mark.parametrize("pending_status", ["final_answer_pending", "corrective_resolution_pending"])
def test_final_answer_gets_corrective_feedback_before_next_error_even_if_still_wrong(code, pending_status):
    corrective = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="請整理這一題最後的答案與理由。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "target_question_id": "q01",
            "next_target_question_id": "q02",
            "dialogue_state": "SELF_CORRECT",
            "dialogue_move": "final_answer_prompt",
            "disclosure_level": "D4",
            "completion_status": pending_status,
        },
    )
    runtime = build_interaction_runtime(_condition(code), _multi_error_attempt(), [corrective])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "RESOLVED",
            "dialogue_move": "corrective_feedback",
            "disclosure_level": "D4",
            "completion_status": "feedback_completed",
            "off_topic_redirect": True,
        },
        "正確答案是「按人數」，你原先把等級的一票和每個代表的一票混淆了。接著看你對財政危機的判斷。",
    )

    assert runtime.corrective_feedback_required is True
    assert enforced.retry_required is False
    assert enforced.metadata["completion_status"] == "feedback_completed"
    assert enforced.metadata["resolution_outcome"] == "feedback_delivered"
    assert enforced.metadata["resolution_criteria_met"] is False
    assert enforced.metadata["learner_revision_status"] == "unresolved"
    assert enforced.metadata["corrective_feedback_revealed_answer"] is True
    assert enforced.metadata["next_target_started"] is True

    completed = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content=enforced.response,
        metadata=enforced.metadata,
    )
    next_runtime = build_interaction_runtime(
        _condition(code),
        _multi_error_attempt(),
        [corrective, completed],
    )
    assert next_runtime.target.question_id == "q02"
    assert next_runtime.previous_disclosure_level == "D0"


@pytest.mark.parametrize("answer,feedback", [
    ("西周", "這套構想由西周提出。"),
    (["西周", "西先生"], "這套構想由西周提出。"),
    ("B", "應選擇「B」。"),
    (True, "這個判斷正確。"),
    (False, "這個判斷不正確。"),
])
def test_terminal_feedback_accepts_answer_formats_and_does_not_mistake_shared_keys_for_next_answer(answer, feedback):
    attempt = _multi_error_attempt()
    for result in attempt.judgement_payload["question_results"][:2]:
        result["expected_answer"] = answer
    pending = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="Tutor",
        content="請先整理最後判斷。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "target_question_id": "q01", "dialogue_state": "SELF_CORRECT",
            "disclosure_level": "D4", "completion_status": "final_answer_pending",
        },
    )
    runtime = build_interaction_runtime(_condition("02"), attempt, [pending])
    result = enforce_interaction_response(runtime, {
        "dialogue_state": "RESOLVED", "dialogue_move": "corrective_feedback",
        "disclosure_level": "D4", "completion_status": "feedback_completed",
    }, feedback + "接著看下一個判斷。")
    assert result.retry_required is False
    assert result.metadata["corrective_feedback_revealed_answer"] is True
    assert result.metadata["next_target_started"] is True


def test_all_correct_attempt_uses_only_researcher_authored_fallback():
    attempt = TaskAttempt(
        session_id="session-1",
        task_id="task-1",
        event_id="event-1",
        status="submitted",
        judgement_payload={
            "result": "correct",
            "question_results": [
                {
                    "question_id": "q01",
                    "prompt": "第三等級要求如何表決？",
                    "learner_answer": "按人數",
                    "expected_answer": "按人數",
                    "correctness": "correct",
                }
            ],
            "all_correct_fallback": {
                "id": "fallback-01",
                "incorrect_claim": "三級會議一直採按人數表決。",
                "correct_interpretation": "三級會議原先採按等級表決。",
                "evidence_ids": ["E03"],
            },
        },
    )

    runtime = build_interaction_runtime(_condition("02"), attempt, [])

    assert runtime.target.question_id == "fallback-01"
    assert runtime.target.probe_kind == "controlled_fallback"
    assert runtime.target.error_source == "researcher_authored_fallback"
    assert runtime.target.learner_answer == "三級會議一直採按人數表決。"


def test_all_correct_attempt_without_researcher_fallback_does_not_invent_an_error():
    attempt = TaskAttempt(
        session_id="session-1",
        task_id="task-1",
        event_id="event-1",
        status="submitted",
        judgement_payload={
            "result": "correct",
            "question_results": [
                {
                    "question_id": "q01",
                    "learner_answer": "按人數",
                    "expected_answer": "按人數",
                    "correctness": "correct",
                }
            ],
        },
    )

    runtime = build_interaction_runtime(_condition("02"), attempt, [])

    assert runtime.target is None
    assert runtime.target_count == 0


def test_standard_chat_has_no_mandated_task_target():
    condition = _condition("01")
    greeting = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Assistant",
        content="正確答案是按人數。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "interaction_mode": "standard_chat",
            "target_question_id": "q01",
            "dialogue_state": "STANDARD_CHAT",
            "completion_status": "complete",
        },
    )

    runtime = build_interaction_runtime(condition, _attempt(), [greeting])

    assert runtime.target is None


def test_ebl_can_progress_through_the_complete_state_sequence():
    condition = _condition("02")
    messages: list[ChatMessage] = []
    steps = [
        ("NOTICE_ERROR", "error_awareness_prompt", "你覺得原來的答案有哪裡需要重新想一想？"),
        ("REFLECT", "reflection_prompt", "你原來的判斷為什麼需要改變？"),
        ("SELF_CORRECT", "self_correction_prompt", "那你會如何修改原本的答案與理由？"),
        ("RESOLVED", "resolution", "你已完成修正，正確答案是「按人數」。"),
    ]

    for index, (state, move, response) in enumerate(steps):
        runtime = build_interaction_runtime(condition, _attempt(), messages)
        resolution_metadata = (
            {
                "resolution_error_recognized": True,
                "resolution_error_reflected": True,
                "resolution_self_corrected": True,
            }
            if state == "RESOLVED"
            else {}
        )
        enforced = enforce_interaction_response(
            runtime,
            {
                "dialogue_state": state,
                "dialogue_move": move,
                "disclosure_level": f"D{index}",
                **resolution_metadata,
            },
            response,
        )

        assert enforced.fallback_applied is False
        assert enforced.retry_required is False
        assert enforced.metadata["dialogue_state"] == state
        assert enforced.metadata["dialogue_move"] == move
        messages.append(
            ChatMessage(
                conversation_id="conversation-1",
                speaker_type="assistant",
                speaker_name="AI Tutor",
                content=enforced.response,
                sequence_index=index,
                metadata=enforced.metadata,
            )
        )

    completed_runtime = build_interaction_runtime(condition, _attempt(), messages)
    assert completed_runtime.target is None
    assert completed_runtime.allowed_states == ("RESOLVED",)


def test_same_ebl_state_accepts_model_selected_adjacent_disclosure_level():
    condition = _condition("02")
    previous = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="先說明你原先判斷的理由。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "target_question_id": "q01",
            "dialogue_state": "NOTICE_ERROR",
            "dialogue_move": "error_awareness_prompt",
            "disclosure_level": "D2",
            "completion_status": "continue",
        },
    )

    for selected_level, learner_progress in (
        ("D1", "clear_progress"),
        ("D2", "partial_progress"),
        ("D3", "no_progress"),
    ):
        runtime = build_interaction_runtime(condition, _attempt(), [previous])
        enforced = enforce_interaction_response(
            runtime,
            {
                "dialogue_state": "NOTICE_ERROR",
                "dialogue_move": "error_awareness_prompt",
                "disclosure_level": selected_level,
                "learner_progress": learner_progress,
                "disclosure_reason": "依受測者本回合的推理完整度調整。",
            },
            "你是根據哪一項史實得出原先的判斷？",
        )

        assert enforced.retry_required is False
        assert enforced.metadata["allowed_disclosure_levels"] == ["D1", "D2", "D3"]
        assert enforced.metadata["disclosure_level"] == selected_level
        assert enforced.metadata["learner_progress"] == learner_progress
        assert enforced.metadata["disclosure_reason"] == "依受測者本回合的推理完整度調整。"


def test_first_learner_reply_may_choose_d0_or_d1_only():
    condition = _condition("02")
    greeting = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Tutor",
        content="你原本是根據什麼理由作答？",
        metadata=initial_greeting_metadata(
            condition,
            _attempt(),
            "你原本是根據什麼理由作答？",
        ),
    )
    runtime = build_interaction_runtime(condition, _attempt(), [greeting])

    assert runtime.allowed_disclosure_levels == ("D0", "D1")
    assert runtime.source_content_available is True

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "REFLECT",
            "dialogue_move": "reflection_prompt",
            "disclosure_level": "D1",
            "learner_progress": "no_progress",
            "disclosure_reason": "受測者尚未提出可檢查的史實依據。",
        },
        "先回到題目中的代表權安排，哪一個關係最值得重新檢查？",
    )

    assert enforced.retry_required is False
    assert enforced.metadata["disclosure_level"] == "D1"
    assert enforced.metadata["learner_progress"] == "no_progress"


def test_initial_ebl_prompt_uses_private_reference_without_relaxing_d0():
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [])
    prompt = runtime.prompt_block()

    assert runtime.prompt_disclosure_ceiling == "D0"
    assert runtime.source_content_available is True
    assert "第三等級反對每一等級各一票" in prompt
    assert "按人數" in prompt
    assert "Private evaluation context" in prompt
    assert "Do not add a target-relevant historical fact" in prompt
    assert "Do not introduce a new analytical distinction" in prompt
    assert "Neutral event orientation" in prompt


def test_initial_disclosure_cannot_jump_past_prompt_ceiling():
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [])
    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "NOTICE_ERROR",
            "dialogue_move": "error_awareness_prompt",
            "disclosure_level": "D4",
        },
        "你原先的判斷理由是什麼？",
    )

    assert enforced.retry_required is True
    assert enforced.metadata["disclosure_level"] == "D0"
    assert "invalid_disclosure_transition" in enforced.metadata["fidelity_flags"]


def test_ebl_answer_leak_requires_regeneration_before_delivery():
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [])
    raw_response = "正確答案是「按人數」。你現在理解了嗎？"

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "NOTICE_ERROR",
            "dialogue_move": "error_awareness_prompt",
            "disclosure_level": "D0",
        },
        raw_response,
    )

    assert enforced.fallback_applied is False
    assert enforced.retry_required is True
    assert enforced.response == raw_response
    assert "early_answer_exposure" in enforced.metadata["fidelity_flags"]
    assert enforced.metadata["rejected_response_length"] == len(raw_response)
    assert len(enforced.metadata["rejected_response_sha256"]) == 64


def test_redundant_dialogue_move_is_recorded_but_canonicalized_without_retry():
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "NOTICE_ERROR",
            "dialogue_move": "reflection_prompt",
            "disclosure_level": "D0",
        },
        "你原先認為形式相同就是公平；這個推論有哪一部分值得再想一次？",
    )

    assert enforced.retry_required is False
    assert enforced.metadata["dialogue_move"] == "error_awareness_prompt"
    assert "invalid_dialogue_move" in enforced.metadata["fidelity_flags"]


def test_ebl_accepts_an_implicit_scaffold_without_a_question():
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "NOTICE_ERROR",
            "dialogue_move": "error_awareness_prompt",
            "disclosure_level": "D0",
        },
        "先把你原先的判斷與作答理由說成一句完整的話。",
    )

    assert enforced.fallback_applied is False
    assert enforced.response.count("？") == 0
    assert enforced.metadata["primary_ebl_move"] == "recognize_the_current_error"


def test_ebl_accepts_two_tightly_related_questions_for_one_reasoning_move():
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "NOTICE_ERROR",
            "dialogue_move": "error_awareness_prompt",
            "disclosure_level": "D0",
        },
        "你原先主張按等級表決的理由是什麼？這個理由依據題目中的哪項線索？",
    )

    assert enforced.fallback_applied is False
    assert enforced.response.count("？") == 2


def test_ebl_unfocused_question_checklist_requires_regeneration():
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "NOTICE_ERROR",
            "dialogue_move": "error_awareness_prompt",
            "disclosure_level": "D0",
        },
        "你為什麼這樣想？有什麼證據？當時背景是什麼？還有誰的觀點？",
    )

    assert enforced.fallback_applied is False
    assert enforced.retry_required is True
    assert enforced.response.count("？") == 4
    assert "excessive_scaffold_questions" in enforced.metadata["fidelity_flags"]


def test_standard_chat_allows_a_natural_follow_up_question():
    runtime = build_interaction_runtime(_condition("01"), _attempt(), [])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "STANDARD_CHAT",
            "dialogue_move": "natural_response",
        },
        "你要不要再想想這項表決安排？",
    )

    assert enforced.fallback_applied is False
    assert enforced.retry_required is False
    assert enforced.response == "你要不要再想想這項表決安排？"
    assert enforced.metadata["dialogue_state"] == "STANDARD_CHAT"
    assert enforced.metadata["fidelity_flags"] == []


def test_generic_standard_chat_preserves_provider_flags_without_impersonating():
    generic_runtime = build_interaction_runtime(_condition("01"), _attempt(), [])
    generic = enforce_interaction_response(
        generic_runtime,
        {
            "dialogue_state": "STANDARD_CHAT",
            "dialogue_move": "natural_response",
            "fidelity_flags": ["historical_accuracy"],
        },
        "正確答案是「按人數」。這反映第三等級的代表權訴求。",
    )

    assert generic.fallback_applied is False
    assert generic.metadata["fidelity_flags"] == []
    assert generic.metadata["provider_fidelity_flags"] == ["historical_accuracy"]
