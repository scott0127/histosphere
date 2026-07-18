from app.core.experiment_conditions import EXPERIMENT_CONDITION_DEFINITIONS
from app.core.interaction_contract import (
    INTERACTION_POLICY_VERSION,
    build_interaction_runtime,
    enforce_interaction_response,
    initial_greeting_metadata,
    resolve_interaction_metadata,
)
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


def test_direct_cells_force_immediate_response_metadata():
    for code in ("01", "03"):
        condition = _condition(code)
        runtime = build_interaction_runtime(condition, _attempt(), [])
        metadata = resolve_interaction_metadata(
            runtime,
            {"dialogue_state": "ELICIT_REASONING", "dialogue_move": "reasoning_probe"},
            "正確答案是按人數，因為代表權按個別代表計算。",
        )

        assert runtime.interaction_mode == "direct"
        assert metadata["interaction_policy_version"] == INTERACTION_POLICY_VERSION
        assert metadata["condition_code"] == code
        assert metadata["dialogue_state"] == "DIRECT_RESPONSE"
        assert metadata["dialogue_move"] == "direct_correction"
        assert metadata["scaffold_level"] is None
        assert metadata["target_question_id"] == "q01"


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
                "scaffold_level": "L1",
                "learner_revision_status": "not_yet",
            },
            "請對照 E03，這項證據支持哪一種表決方式？",
        )

    assert metadata_by_code["02"]["dialogue_state"] == "INSPECT_EVIDENCE"
    assert metadata_by_code["04"]["dialogue_state"] == "INSPECT_EVIDENCE"
    assert metadata_by_code["02"]["dialogue_move"] == metadata_by_code["04"]["dialogue_move"]
    assert metadata_by_code["02"]["target_question_id"] == metadata_by_code["04"]["target_question_id"]
    assert metadata_by_code["02"]["scaffold_level"] == metadata_by_code["04"]["scaffold_level"]


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
            "scaffold_level": "L4",
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


def test_direct_follow_up_no_longer_repeats_task_correction():
    condition = _condition("01")
    greeting = ChatMessage(
        conversation_id="conversation-1",
        speaker_type="assistant",
        speaker_name="AI Assistant",
        content="正確答案是按人數。",
        metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "interaction_mode": "direct",
            "target_question_id": "q01",
            "dialogue_state": "DIRECT_RESPONSE",
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
                "scaffold_level": f"L{min(index, 4)}",
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


def test_same_ebl_state_escalates_one_scaffold_level_at_a_time():
    condition = _condition("02")
    messages: list[ChatMessage] = []

    for expected_level in ("L0", "L1", "L2"):
        runtime = build_interaction_runtime(condition, _attempt(), messages)
        enforced = enforce_interaction_response(
            runtime,
            {
                "dialogue_state": "ELICIT_REASONING",
                "dialogue_move": "reasoning_probe",
                "scaffold_level": "L0",
            },
            "你是根據哪一項史實得出原先的判斷？",
        )

        assert enforced.metadata["scaffold_level"] == expected_level
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


def test_ebl_answer_leak_is_replaced_before_reaching_the_learner():
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [])
    raw_response = "正確答案是「按人數」。你現在理解了嗎？"

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "ELICIT_REASONING",
            "dialogue_move": "reasoning_probe",
            "scaffold_level": "L0",
        },
        raw_response,
    )

    assert enforced.fallback_applied is True
    assert "按人數" not in enforced.response
    assert enforced.response.count("？") == 1
    assert "early_answer_exposure" in enforced.metadata["fidelity_flags"]
    assert enforced.metadata["raw_response_length"] == len(raw_response)
    assert len(enforced.metadata["raw_response_sha256"]) == 64


def test_ebl_multiple_questions_are_replaced_with_one_question():
    runtime = build_interaction_runtime(_condition("02"), _attempt(), [])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "ELICIT_REASONING",
            "dialogue_move": "reasoning_probe",
            "scaffold_level": "L0",
        },
        "你為什麼這樣想？你能提出證據嗎？",
    )

    assert enforced.fallback_applied is True
    assert enforced.response.count("？") == 1
    assert "multiple_scaffold_questions" in enforced.metadata["fidelity_flags"]


def test_direct_missing_correction_is_replaced_with_the_answer():
    runtime = build_interaction_runtime(_condition("01"), _attempt(), [])

    enforced = enforce_interaction_response(
        runtime,
        {
            "dialogue_state": "DIRECT_RESPONSE",
            "dialogue_move": "direct_correction",
        },
        "你要不要再想想這項表決安排？",
    )

    assert enforced.fallback_applied is True
    assert enforced.response.startswith("正確答案是「按人數」。")
    assert "？" not in enforced.response
    assert "direct_correction_missing" in enforced.metadata["fidelity_flags"]
    assert "direct_question_present" in enforced.metadata["fidelity_flags"]


def test_roleplay_requires_first_person_but_generic_mode_does_not_impersonate():
    roleplay_runtime = build_interaction_runtime(_condition("03"), _attempt(), [])
    roleplay = enforce_interaction_response(
        roleplay_runtime,
        {"dialogue_state": "DIRECT_RESPONSE", "dialogue_move": "direct_correction"},
        "正確答案是「按人數」。這反映第三等級的代表權訴求。",
    )

    assert roleplay.fallback_applied is True
    assert roleplay.response.startswith("我的判斷是：")
    assert "roleplay_first_person_missing" in roleplay.metadata["fidelity_flags"]

    generic_runtime = build_interaction_runtime(_condition("01"), _attempt(), [])
    generic = enforce_interaction_response(
        generic_runtime,
        {
            "dialogue_state": "DIRECT_RESPONSE",
            "dialogue_move": "direct_correction",
            "fidelity_flags": ["historical_accuracy"],
        },
        "正確答案是「按人數」。這反映第三等級的代表權訴求。",
    )

    assert generic.fallback_applied is False
    assert "我的判斷" not in generic.response
    assert generic.metadata["fidelity_flags"] == []
    assert generic.metadata["provider_fidelity_flags"] == ["historical_accuracy"]
