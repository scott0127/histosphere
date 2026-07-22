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
    assert "zero to two tightly related questions" in matrix["02"]["independent_2_prompt"]
    assert "Keep one error in focus until it is resolved" in matrix["04"]["independent_2_prompt"]
    assert "zero to two tightly related questions" not in matrix["01"]["independent_2_prompt"]


def test_prompt_exposes_only_the_runtime_selected_task_error():
    condition = _condition("02")
    attempt = _attempt()
    attempt.judgement_payload["question_results"].append(
        {
            "question_id": "q02",
            "prompt": "第二個不應提前出現的錯誤",
            "learner_answer": "錯誤答案二",
            "expected_answer": "正確答案二",
            "correctness": "incorrect",
        }
    )
    modules = PromptService().assemble_chat_modules(
        event=Event(canonical_name="法國大革命"),
        persona=None,
        condition=condition,
        task_attempt=attempt,
        user_message="固定訊息",
        rag_sources=[],
        conversation_history=[],
    )
    learner_task = next(module.content for module in modules if module.name == "learner_task")
    runtime = next(module.content for module in modules if module.name == "interaction_runtime")

    assert "第三等級要求如何表決" in learner_task
    assert "第二個不應提前出現的錯誤" not in learner_task
    assert "第二個不應提前出現的錯誤" in runtime
    assert "正確答案二" not in runtime
