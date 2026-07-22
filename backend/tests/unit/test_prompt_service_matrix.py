from app.core.experiment_conditions import EXPERIMENT_CONDITION_DEFINITIONS
from app.models.domain import ChatMessage, Event, ExperimentCondition, Persona, TaskAttempt
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
    assert "Identity is a renderer only" in matrix["01"]["independent_1_prompt"]
    assert "Role-play is a renderer only" in matrix["04"]["independent_1_prompt"]
    assert "content budget must be identical to generic mode" in matrix["04"]["independent_1_prompt"]

    assert matrix["01"]["independent_2_prompt"] == matrix["03"]["independent_2_prompt"]
    assert matrix["02"]["independent_2_prompt"] == matrix["04"]["independent_2_prompt"]
    assert matrix["01"]["independent_2_prompt"] != matrix["02"]["independent_2_prompt"]

    assert matrix["01"]["interaction_runtime"] == matrix["03"]["interaction_runtime"]
    assert matrix["02"]["interaction_runtime"] == matrix["04"]["interaction_runtime"]
    assert "Disclosure levels are not Historical EBL stages" in matrix["02"]["interaction_runtime"]
    assert '"D0"' in matrix["02"]["interaction_runtime"]
    assert '"D4"' in matrix["02"]["interaction_runtime"]
    assert "leaving the key answer blank" in matrix["02"]["interaction_runtime"]
    assert "D1 may identify the sentence" in matrix["02"]["interaction_runtime"]
    assert "must not disclose the evidence content" in matrix["02"]["interaction_runtime"]
    assert "第三等級反對每一等級各一票" not in matrix["02"]["learner_task"]
    assert "按人數" not in matrix["02"]["learner_task"]
    assert "WITHHELD_UNTIL_D2" in matrix["02"]["learner_task"]
    assert "final identity renderer" in matrix["02"]["runtime_policy"]
    assert matrix["03"]["persona_event_context"] == matrix["04"]["persona_event_context"]
    assert "Frame mode: event-situated first-person historical persona" in matrix["03"]["persona_event_context"]
    assert "No persona context applies" in matrix["01"]["persona_event_context"]
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


def test_opening_uses_the_same_dynamic_modules_without_a_prewritten_greeting():
    condition = _condition("03")
    persona = Persona(
        event_id="event-1",
        name="馬克西米連·羅伯斯比爾",
        role="國民公會代表",
        prompt_profile={
            "speaking_style": "嚴肅、論辯性強",
            "event_timepoint": "1793 年國民公會期間",
            "event_timepoint_year": 1793,
            "event_location": "巴黎",
            "event_anchor_terms": ["國民公會"],
            "knowledge_cutoff_year": 1793,
        },
    )
    modules = PromptService().assemble_opening_modules(
        event=Event(
            canonical_name="法國大革命",
            description="革命政府面臨內外危機。",
            start_year=1789,
            end_year=1799,
        ),
        persona=persona,
        condition=condition,
        task_attempt=_attempt(),
    )
    by_name = {module.name: module.content for module in modules}

    assert "Turn kind: opening" in by_name["persona_event_context"]
    assert "Selected in-event timepoint: 1793 年國民公會期間" in by_name["persona_event_context"]
    assert "Selected in-event location: 巴黎" in by_name["persona_event_context"]
    assert "Generate the first substantive AI turn" in by_name["turn_intent"]
    assert "user_message" not in by_name
    assert "我是羅伯斯比爾" not in by_name["persona_event_context"]


def test_conversation_history_keeps_more_than_twelve_database_messages():
    history = [
        ChatMessage(
            conversation_id="conversation-1",
            speaker_type="learner" if index % 2 else "assistant",
            speaker_name="learner" if index % 2 else "AI Assistant",
            sequence_index=index,
            content=f"歷史訊息 {index:02d}",
        )
        for index in range(1, 21)
    ]
    modules = PromptService().assemble_chat_modules(
        event=Event(canonical_name="法國大革命"),
        persona=None,
        condition=_condition("01"),
        task_attempt=_attempt(),
        user_message="請延續前面的討論",
        rag_sources=[],
        conversation_history=history,
    )
    rendered_history = next(module.content for module in modules if module.name == "conversation_history")

    assert "歷史訊息 01" in rendered_history
    assert "歷史訊息 20" in rendered_history
    assert rendered_history.count("歷史訊息") == 20
