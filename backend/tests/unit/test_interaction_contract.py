from app.core.experiment_conditions import EXPERIMENT_CONDITION_DEFINITIONS
from app.core.interaction_contract import (
    INTERACTION_POLICY_VERSION,
    build_interaction_runtime,
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
