from app.core.experiment_conditions import EXPERIMENT_CONDITION_DEFINITIONS
from app.models.domain import Event, ExperimentCondition, Persona, TaskAttempt
from app.services.prompt_service import PromptService


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
            "result": "incorrect",
            "question_results": [
                {
                    "question_id": "q01",
                    "prompt": "第三等級要求如何表決？",
                    "source_text": "第三等級反對每一等級各一票。",
                    "learner_answer": "按等級",
                    "expected_answer": "按人數",
                    "correctness": "incorrect",
                    "error_code": "unclassified",
                }
            ],
        },
    )


def _modules(code: str) -> dict[str, str]:
    condition = _condition(code)
    persona = (
        Persona(
            event_id="event-1",
            name="歷史人物",
            prompt_profile={"contract_version": "persona_prompt_v1"},
        )
        if condition.roleplay_enabled
        else None
    )
    modules = PromptService().assemble_chat_modules(
        event=Event(canonical_name="法國大革命"),
        persona=persona,
        condition=condition,
        task_attempt=_attempt(),
        user_message="固定訊息",
        rag_sources=[],
        conversation_history=[],
    )
    return {module.name: module.content for module in modules}


def test_prompt_modules_change_only_on_their_assigned_factor():
    matrix = {code: _modules(code) for code in ("01", "02", "03", "04")}

    assert len({matrix[code]["general_prompt"] for code in matrix}) == 1

    assert matrix["01"]["independent_1_prompt"] == matrix["02"]["independent_1_prompt"]
    assert matrix["03"]["independent_1_prompt"] == matrix["04"]["independent_1_prompt"]
    assert matrix["01"]["independent_1_prompt"] != matrix["03"]["independent_1_prompt"]

    assert matrix["01"]["independent_2_prompt"] == matrix["03"]["independent_2_prompt"]
    assert matrix["02"]["independent_2_prompt"] == matrix["04"]["independent_2_prompt"]
    assert matrix["01"]["independent_2_prompt"] != matrix["02"]["independent_2_prompt"]

    assert matrix["01"]["interaction_runtime"] == matrix["03"]["interaction_runtime"]
    assert matrix["02"]["interaction_runtime"] == matrix["04"]["interaction_runtime"]
