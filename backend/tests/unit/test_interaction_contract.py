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
            {"dialogue_state": "ELICIT_REASONING", "dialogue_move": "reasoning_probe"},
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
                "dialogue_state": "INSPECT_EVIDENCE",
                "dialogue_move": "evidence_probe",
                "disclosure_level": "D1",
                "learner_revision_status": "not_yet",
            },
            "請對照 E03，這項證據支持哪一種表決方式？",
        )

    assert metadata_by_code["02"]["dialogue_state"] == "INSPECT_EVIDENCE"
    assert metadata_by_code["04"]["dialogue_state"] == "INSPECT_EVIDENCE"
    assert metadata_by_code["02"]["dialogue_move"] == metadata_by_code["04"]["dialogue_move"]
    assert metadata_by_code["02"]["target_question_id"] == metadata_by_code["04"]["target_question_id"]
    assert metadata_by_code["02"]["disclosure_level"] == metadata_by_code["04"]["disclosure_level"]
    assert (
        metadata_by_code["02"]["primary_historical_thinking_move"]
        == metadata_by_code["04"]["primary_historical_thinking_move"]
        == "inspect_source_or_task_evidence"
    )


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
            "dialogue_state": "RESOLVED",
            "dialogue_move": "resolution",
            "disclosure_level": "D4",
        },
        "請先說明你的理由？",
    )

    assert metadata["dialogue_state"] == "ELICIT_REASONING"
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
    assert second_runtime.previous_state == "ELICIT_REASONING"
    assert second_runtime.allowed_states == ("ELICIT_REASONING", "INSPECT_EVIDENCE")
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
        ("ELICIT_REASONING", "reasoning_probe", "你是根據哪一項史實得出原先的判斷？"),
        ("INSPECT_EVIDENCE", "evidence_probe", "題目中的哪一項證據支持或削弱你的判斷？"),
        (
            "CONTEXTUALIZE_OR_COMPARE",
            "context_or_comparison_probe",
            "比較三個等級的代表人口後，這種安排會造成什麼權力差異？",
        ),
        ("REVISE_CLAIM", "revision_prompt", "根據前面的證據，你會如何改寫原先的判斷？"),
        ("REFLECT", "reflection_prompt", "哪一項證據最改變你原先的判斷？"),
        ("RESOLVED", "resolution", "你已完成修正，正確答案是「按人數」。"),
    ]

    for index, (state, move, response) in enumerate(steps):
        runtime = build_interaction_runtime(condition, _attempt(), messages)
        enforced = enforce_interaction_response(
            runtime,
            {
                "dialogue_state": state,
                "dialogue_move": move,
                "disclosure_level": f"L{min(index, 4)}",
            },
            response,
        )

        assert enforced.fallback_applied is False
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


def test_same_ebl_state_escalates_one_disclosure_level_at_a_time():
    condition = _condition("02")
    messages: list[ChatMessage] = []

    for expected_level in ("D0", "D1", "D2"):
        runtime = build_interaction_runtime(condition, _attempt(), messages)
        enforced = enforce_interaction_response(
            runtime,
            {
                "dialogue_state": "ELICIT_REASONING",
                "dialogue_move": "reasoning_probe",
                "disclosure_level": "D0",
            },
            "你是根據哪一項史實得出原先的判斷？",
        )

        assert enforced.metadata["disclosure_level"] == expected_level
        messages.append(
            ChatMessage(
                conversation_id="conversation-1",
                speaker_type="assistant",
                speaker_name="AI Tutor",
                content=enforced.response,
                sequence_index=len(messages),
                metadata=enforced.metadata,
            )
        )


def test_ebl_answer_leak_requires_regeneration_before_delivery():
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [])
    raw_response = "正確答案是「按人數」。你現在理解了嗎？"

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "ELICIT_REASONING",
            "dialogue_move": "reasoning_probe",
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


def test_ebl_accepts_an_implicit_scaffold_without_a_question():
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "ELICIT_REASONING",
            "dialogue_move": "reasoning_probe",
            "disclosure_level": "D0",
        },
        "先把你原先的判斷與作答理由說成一句完整的話。",
    )

    assert enforced.fallback_applied is False
    assert enforced.response.count("？") == 0
    assert enforced.metadata["primary_historical_thinking_move"] == "make_initial_claim_and_reasoning_visible"


def test_ebl_accepts_two_tightly_related_questions_for_one_reasoning_move():
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "ELICIT_REASONING",
            "dialogue_move": "reasoning_probe",
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
            "dialogue_state": "ELICIT_REASONING",
            "dialogue_move": "reasoning_probe",
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
