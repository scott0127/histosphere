import json

import pytest

from app.core.experiment_conditions import EXPERIMENT_CONDITION_DEFINITIONS
from app.core.interaction_contract import build_interaction_runtime, resolve_interaction_metadata
from app.core.learner_task_view import learner_view
from app.models.domain import ChatMessage, Event, ExperimentCondition, TaskAttempt
from app.services.prompt_service import PromptService


RAW_RATIONALE = "  I guessed.\nI have not linked it to the evidence.  "
FULL_TEXT = "Shared authored context. Which rule applied? {{blank:q01}}"


def _condition(code="02"):
    definition = next(item for item in EXPERIMENT_CONDITION_DEFINITIONS if item.code == code)
    return ExperimentCondition(
        condition_key=definition.condition_key,
        label=definition.default_label,
        ebl_enabled=definition.ebl_enabled,
        roleplay_enabled=definition.roleplay_enabled,
        agent_mode=definition.agent_mode,
        response_policy=definition.response_policy,
    )


def _attempt(answer_correct=True, reasoning_correct=False, issue="insufficient_reasoning"):
    return TaskAttempt(
        task_id="task-1",
        event_id="event-1",
        status="submitted",
        judgement_payload={
            "contract_version": "error_elicitation_v1",
            "result": "incorrect",
            "error_elicitation_task_full_text": FULL_TEXT,
            "question_results": [{
                "question_id": "q01",
                "blank_id": "q01",
                "question_type": "multiple_choice",
                "question_text": "Which rule applied? {{blank:q01}}",
                "source_text": "PRIVATE source",
                "learner_answer": "B",
                "learner_rationale": RAW_RATIONALE,
                "answer_correct": answer_correct,
                "reasoning_correct": reasoning_correct,
                "reasoning_issue": issue,
                "reasoning_feedback": "PRIVATE feedback",
                "reasoning_criteria": "PRIVATE criteria",
                "correctness": "correct" if answer_correct and reasoning_correct else "incorrect",
                "expected_answer": "B",
                "error_code": issue,
                "evidence_ids": ["m01"],
            }],
        },
    )


@pytest.mark.parametrize("answer_correct,reasoning_correct", [(True, False), (False, True), (False, False), (True, True)])
def test_targets_require_both_answer_and_reasoning_to_be_correct(answer_correct, reasoning_correct):
    attempt = _attempt(answer_correct, reasoning_correct)
    before = attempt.model_dump()
    runtime = build_interaction_runtime(_condition(), attempt, [])

    assert (runtime.target is None) == (answer_correct and reasoning_correct)
    if runtime.target:
        assert runtime.target.correctness == "incorrect"
        assert runtime.target.prompt == "Which rule applied? {{blank:q01}}"
        assert runtime.target.learner_rationale == RAW_RATIONALE
        assert runtime.target.answer_correct == answer_correct
        assert runtime.target.reasoning_correct == reasoning_correct
        assert runtime.allowed_states == ("ELICIT_REASONING",)
        assert runtime.allowed_disclosure_levels == ("D0",)
    assert attempt.model_dump() == before


def test_two_dimensions_override_stale_correctness_for_queue_selection():
    attempt = _attempt()
    attempt.judgement_payload["question_results"][0]["correctness"] = "correct"
    runtime = build_interaction_runtime(_condition(), attempt, [])
    assert runtime.target is not None
    assert runtime.target.probe_kind == "reasoning_gap"
    assert runtime.target.correctness == "incorrect"


@pytest.mark.parametrize("issue", ["insufficient_reasoning", "factual_error", "unsupported_inference"])
def test_reasoning_issue_reaches_private_prompt_and_research_metadata(issue):
    runtime = build_interaction_runtime(_condition(), _attempt(issue=issue), [])
    prompt = runtime.prompt_block()
    payload = json.loads(prompt.split("Current target: ", 1)[1].split("\n", 1)[0])
    assert payload["learner_rationale"] == RAW_RATIONALE
    assert payload["reasoning_issue"] == issue
    assert payload["reasoning_feedback"] == "PRIVATE feedback"
    assert payload["reasoning_criteria"] == "PRIVATE criteria"
    assert "not evidence of a factual misconception" in prompt
    metadata = resolve_interaction_metadata(runtime, {
        "dialogue_state": "ELICIT_REASONING",
        "dialogue_move": "reasoning_probe",
        "disclosure_level": "D0",
    }, "What supported your answer?")
    assert metadata["answer_correct"] is True
    assert metadata["reasoning_correct"] is False
    assert metadata["reasoning_issue"] == issue
    assert metadata["completion_status"] == "continue"
    assert "reasoning_feedback" not in metadata
    assert "reasoning_criteria" not in metadata


@pytest.mark.parametrize("code", ["01", "02", "03", "04"])
@pytest.mark.parametrize("opening", [True, False])
def test_hidden_prompt_preserves_fulltext_and_original_rationale(code, opening):
    attempt = _attempt()
    attempt.judgement_payload["question_results"].append({
        **attempt.judgement_payload["question_results"][0],
        "question_id": "q02",
        "blank_id": "q02",
        "reasoning_feedback": "OTHER TARGET feedback",
    })
    service = PromptService()
    args = dict(event=Event(canonical_name="Test event"), persona=None, condition=_condition(code), task_attempt=attempt)
    modules = (
        service.assemble_opening_modules(**args) if opening else
        service.assemble_chat_modules(**args, user_message="Discuss the event.", rag_sources=[])
    )
    rendered = service.render_modules(modules)
    learner_task = next(module.content for module in modules if module.name == "learner_task")
    context = json.loads(learner_task.split("Task context: ", 1)[1])
    assert rendered.count(FULL_TEXT) == 1
    assert context["question_results"][0]["learner_rationale"] == RAW_RATIONALE
    assert "prompt" not in context["question_results"][0]
    assert "not evidence of a factual misconception" in learner_task
    if code in {"02", "04"}:
        assert len(context["question_results"]) == 1
        assert "OTHER TARGET feedback" not in rendered
    else:
        assert len(context["question_results"]) == 2
        assert "Standard chat has no mandated error target" in learner_task


def test_resumed_target_retains_rationale_and_advances_only_after_existing_resolution():
    attempt = _attempt()
    message = ChatMessage(
        speaker_type="assistant", speaker_name="Tutor", content="Explain your reasoning.",
        metadata={
            "interaction_policy_version": "2x2-interaction-v7",
            "target_question_id": "q01",
            "dialogue_state": "INSPECT_EVIDENCE",
            "disclosure_level": "D1",
            "completion_status": "continue",
        },
    )
    runtime = build_interaction_runtime(_condition(), attempt, [message])
    assert runtime.target.learner_rationale == RAW_RATIONALE
    assert runtime.previous_state == "INSPECT_EVIDENCE"
    assert runtime.allowed_disclosure_levels == ("D0", "D1", "D2")
    message.metadata["completion_status"] = "resolved"
    assert build_interaction_runtime(_condition(), attempt, [message]).target is None


def test_legacy_message_redaction_preserves_runtime_metadata_and_returns_a_copy():
    message = ChatMessage(
        speaker_type="assistant", speaker_name="Tutor", content="Visible response",
        metadata={
            "judgement": {"feedback": "PRIVATE"},
            "dialogue_state": "INSPECT_EVIDENCE",
            "completion_status": "continue",
            "nested": [{"judgement_payload": {"expected_answer": "PRIVATE"}, "keep": True}],
            "llm_call": {"total_tokens": 123},
        },
    )
    before = message.model_dump()
    public = learner_view(message)
    assert isinstance(public, ChatMessage)
    assert public.metadata == {
        "dialogue_state": "INSPECT_EVIDENCE",
        "completion_status": "continue",
        "nested": [{"keep": True}],
        "llm_call": {"total_tokens": 123},
    }
    public.metadata["llm_call"]["total_tokens"] = 0
    assert message.model_dump() == before
