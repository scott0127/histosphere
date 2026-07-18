"""Backend-owned interaction contract for the fixed 2x2 experiment."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, Sequence

from app.core.experiment_conditions import condition_code_for_key


InteractionMode = Literal["direct", "scaffold"]
DialogueState = Literal[
    "DIRECT_RESPONSE",
    "ELICIT_REASONING",
    "INSPECT_EVIDENCE",
    "CONTEXTUALIZE_OR_COMPARE",
    "REVISE_CLAIM",
    "REFLECT",
    "RESOLVED",
]

INTERACTION_POLICY_VERSION = "2x2-interaction-v1"
EBL_INITIAL_STATE: DialogueState = "ELICIT_REASONING"
EBL_STATE_TRANSITIONS: dict[str, tuple[DialogueState, ...]] = {
    "ELICIT_REASONING": ("ELICIT_REASONING", "INSPECT_EVIDENCE"),
    "INSPECT_EVIDENCE": ("INSPECT_EVIDENCE", "CONTEXTUALIZE_OR_COMPARE"),
    "CONTEXTUALIZE_OR_COMPARE": ("CONTEXTUALIZE_OR_COMPARE", "REVISE_CLAIM"),
    "REVISE_CLAIM": ("REVISE_CLAIM", "REFLECT"),
    "REFLECT": ("REFLECT", "RESOLVED"),
    "RESOLVED": ("RESOLVED",),
}
DIALOGUE_MOVE_BY_STATE: dict[str, str] = {
    "DIRECT_RESPONSE": "direct_correction",
    "ELICIT_REASONING": "reasoning_probe",
    "INSPECT_EVIDENCE": "evidence_probe",
    "CONTEXTUALIZE_OR_COMPARE": "context_or_comparison_probe",
    "REVISE_CLAIM": "revision_prompt",
    "REFLECT": "reflection_prompt",
    "RESOLVED": "resolution",
}
SCAFFOLD_LEVELS = ("L0", "L1", "L2", "L3", "L4")
QUESTION_RESULT_PRIORITY = {
    "incorrect": 0,
    "partial": 1,
    "unanswered": 2,
    "ungraded": 3,
    "correct": 4,
}


@dataclass(frozen=True)
class InteractionTarget:
    """One task item selected as the current conversation target."""

    question_id: str | None
    prompt: str
    source_text: Any
    learner_answer: Any
    expected_answer: Any
    correctness: str
    error_code: str | None
    historical_concept: str | None
    reasoning_process: str | None
    evidence_ids: tuple[str, ...]
    probe_kind: str

    def as_metadata(self) -> dict[str, Any]:
        return {
            "target_question_id": self.question_id,
            "target_correctness": self.correctness,
            "error_code": self.error_code,
            "historical_concept": self.historical_concept,
            "reasoning_process": self.reasoning_process,
            "evidence_ids": list(self.evidence_ids),
            "probe_kind": self.probe_kind,
        }


@dataclass(frozen=True)
class InteractionRuntime:
    """Validated input contract supplied to one chat completion."""

    condition_code: str
    condition_key: str
    interaction_mode: InteractionMode
    roleplay_enabled: bool
    target: InteractionTarget | None
    previous_state: DialogueState | None
    allowed_states: tuple[DialogueState, ...]
    previous_scaffold_level: str | None
    previous_attempts_in_state: int

    def prompt_block(self) -> str:
        target = self.target
        target_payload = {
            "question_id": target.question_id if target else None,
            "prompt": target.prompt if target else "No task item is attached.",
            "task_source_text": target.source_text if target else None,
            "learner_answer": target.learner_answer if target else None,
            "expected_answer": target.expected_answer if target else None,
            "correctness": target.correctness if target else "ungraded",
            "error_code": target.error_code if target else None,
            "historical_concept": target.historical_concept if target else None,
            "reasoning_process": target.reasoning_process if target else None,
            "evidence_ids": list(target.evidence_ids) if target else [],
            "probe_kind": target.probe_kind if target else "general_question",
        }
        shared = (
            f"Policy version: {INTERACTION_POLICY_VERSION}\n"
            f"Interaction mode: {self.interaction_mode}\n"
            f"Current target: {json.dumps(target_payload, ensure_ascii=False)}"
        )
        if self.interaction_mode == "direct":
            return (
                f"{shared}\n"
                "Required behavior: answer or correct the target immediately in the first substantive sentence. "
                "Then give a concise historically grounded explanation. Do not delay the correction with a "
                "Socratic question or require a reflection sequence.\n"
                "Structured interaction fields must be dialogue_state=DIRECT_RESPONSE, "
                "dialogue_move=direct_correction, completion_status=complete, and scaffold_level=null."
            )

        state_moves = ", ".join(
            f"{state}={DIALOGUE_MOVE_BY_STATE[state]}"
            for state in self.allowed_states
        )
        return (
            f"{shared}\n"
            f"Previous dialogue state: {self.previous_state or 'NONE'}\n"
            f"Allowed response states: {', '.join(self.allowed_states)}\n"
            f"Allowed state-to-move mapping: {state_moves}\n"
            f"Previous scaffold level: {self.previous_scaffold_level or 'NONE'}\n"
            f"Previous attempts in state: {self.previous_attempts_in_state}\n"
            "Required behavior: choose exactly one allowed response state after assessing the learner's latest "
            "message. Perform only that state's move and ask at most one explicit question. Do not discuss a "
            "second task error. Before RESOLVED, do not reveal the complete expected answer unless L4 support is "
            "needed after repeated failure. If the learner has not progressed, remain in the previous state and "
            "increase support by at most one level. If the learner has progressed, advance by at most one state. "
            "When evidence_ids is empty, use only event_context or task_source_text as contextual evidence and do "
            "not invent a source ID or quotation."
        )


def _message_metadata(message: Any) -> dict[str, Any]:
    metadata = getattr(message, "metadata", None)
    return metadata if isinstance(metadata, dict) else {}


def _question_results(task_attempt: Any | None) -> list[dict[str, Any]]:
    if not task_attempt:
        return []
    judgement = getattr(task_attempt, "judgement_payload", None)
    if not isinstance(judgement, dict):
        return []
    results = judgement.get("question_results")
    return [item for item in results if isinstance(item, dict)] if isinstance(results, list) else []


def _resolved_question_ids(messages: Sequence[Any]) -> set[str]:
    resolved: set[str] = set()
    for message in messages:
        metadata = _message_metadata(message)
        if metadata.get("completion_status") not in {"resolved", "complete"}:
            continue
        question_id = metadata.get("target_question_id")
        if isinstance(question_id, str) and question_id:
            resolved.add(question_id)
    return resolved


def _last_interaction_metadata(messages: Sequence[Any]) -> dict[str, Any]:
    for message in reversed(messages):
        metadata = _message_metadata(message)
        if metadata.get("interaction_policy_version") == INTERACTION_POLICY_VERSION:
            return metadata
    return {}


def _target_from_result(result: dict[str, Any]) -> InteractionTarget:
    correctness = str(result.get("correctness") or "ungraded")
    probe_kind = "error_correction" if correctness != "correct" else "justification_probe"
    evidence_ids = result.get("evidence_ids")
    return InteractionTarget(
        question_id=str(result.get("question_id")) if result.get("question_id") else None,
        prompt=str(result.get("prompt") or "請說明你的判斷。"),
        source_text=result.get("source_text"),
        learner_answer=result.get("learner_answer"),
        expected_answer=result.get("expected_answer"),
        correctness=correctness,
        error_code=str(result.get("error_code")) if result.get("error_code") else None,
        historical_concept=(
            str(result.get("historical_concept"))
            if result.get("historical_concept")
            else None
        ),
        reasoning_process=(
            str(result.get("reasoning_process"))
            if result.get("reasoning_process")
            else None
        ),
        evidence_ids=tuple(str(item) for item in evidence_ids or [] if item),
        probe_kind=probe_kind,
    )


def select_interaction_target(task_attempt: Any | None, messages: Sequence[Any]) -> InteractionTarget | None:
    """Keep one unresolved task item stable across the conversation."""
    results = _question_results(task_attempt)
    if not results:
        judgement = getattr(task_attempt, "judgement_payload", {}) if task_attempt else {}
        last_metadata = _last_interaction_metadata(messages)
        if (
            last_metadata.get("completion_status") in {"resolved", "complete"}
            and not last_metadata.get("target_question_id")
        ):
            return None
        summary = judgement.get("misconception_summary") if isinstance(judgement, dict) else None
        if not summary:
            return None
        return InteractionTarget(
            question_id=None,
            prompt=str(summary),
            source_text=None,
            learner_answer=None,
            expected_answer=None,
            correctness=str(judgement.get("result") or "ungraded"),
            error_code="unclassified",
            historical_concept=None,
            reasoning_process=None,
            evidence_ids=(),
            probe_kind="error_correction",
        )

    resolved_ids = _resolved_question_ids(messages)
    last_metadata = _last_interaction_metadata(messages)
    last_target_id = last_metadata.get("target_question_id")
    if isinstance(last_target_id, str) and last_target_id not in resolved_ids:
        for result in results:
            if result.get("question_id") == last_target_id:
                return _target_from_result(result)

    unresolved_results = [
        result
        for result in results
        if result.get("question_id") not in resolved_ids
        and str(result.get("correctness")) != "correct"
    ]
    if unresolved_results:
        unresolved_results.sort(
            key=lambda item: QUESTION_RESULT_PRIORITY.get(str(item.get("correctness")), 99)
        )
        return _target_from_result(unresolved_results[0])

    had_error = any(str(result.get("correctness")) != "correct" for result in results)
    if had_error:
        return None

    correct_candidates = [
        result
        for result in results
        if result.get("question_id") not in resolved_ids
    ]
    return _target_from_result(correct_candidates[0]) if correct_candidates else None


def build_interaction_runtime(
    condition: Any,
    task_attempt: Any | None,
    messages: Sequence[Any],
) -> InteractionRuntime:
    """Build the backend-owned policy input for one completion."""
    interaction_mode: InteractionMode = "scaffold" if condition.ebl_enabled else "direct"
    target = select_interaction_target(task_attempt, messages)
    if interaction_mode == "direct":
        previous_metadata = _last_interaction_metadata(messages)
        if previous_metadata.get("completion_status") == "complete":
            target = None
        return InteractionRuntime(
            condition_code=condition_code_for_key(condition.condition_key),
            condition_key=condition.condition_key,
            interaction_mode=interaction_mode,
            roleplay_enabled=condition.roleplay_enabled,
            target=target,
            previous_state=None,
            allowed_states=("DIRECT_RESPONSE",),
            previous_scaffold_level=None,
            previous_attempts_in_state=0,
        )

    previous_metadata = _last_interaction_metadata(messages)
    raw_previous_state = previous_metadata.get("dialogue_state")
    previous_state = (
        raw_previous_state
        if raw_previous_state in EBL_STATE_TRANSITIONS
        else None
    )
    if target is None:
        allowed_states: tuple[DialogueState, ...] = ("RESOLVED",)
    elif previous_state:
        allowed_states = EBL_STATE_TRANSITIONS[previous_state]
    else:
        allowed_states = (EBL_INITIAL_STATE,)
    return InteractionRuntime(
        condition_code=condition_code_for_key(condition.condition_key),
        condition_key=condition.condition_key,
        interaction_mode=interaction_mode,
        roleplay_enabled=condition.roleplay_enabled,
        target=target,
        previous_state=previous_state,
        allowed_states=allowed_states,
        previous_scaffold_level=(
            str(previous_metadata.get("scaffold_level"))
            if previous_metadata.get("scaffold_level") in SCAFFOLD_LEVELS
            else None
        ),
        previous_attempts_in_state=int(previous_metadata.get("attempts_in_state") or 0),
    )


def _scaffold_level(runtime: InteractionRuntime, state: str, raw_level: Any) -> str:
    if raw_level in SCAFFOLD_LEVELS:
        suggested_index = SCAFFOLD_LEVELS.index(raw_level)
    else:
        suggested_index = 0
    previous_index = (
        SCAFFOLD_LEVELS.index(runtime.previous_scaffold_level)
        if runtime.previous_scaffold_level in SCAFFOLD_LEVELS
        else 0
    )
    if state == runtime.previous_state:
        return SCAFFOLD_LEVELS[min(4, max(suggested_index, previous_index + 1))]
    return SCAFFOLD_LEVELS[min(4, max(suggested_index, previous_index - 1, 0))]


def resolve_interaction_metadata(
    runtime: InteractionRuntime,
    provider_metadata: dict[str, Any] | None,
    response_text: str,
) -> dict[str, Any]:
    """Validate model-proposed metadata against the backend-owned condition contract."""
    raw = provider_metadata if isinstance(provider_metadata, dict) else {}
    flags = {
        str(item)
        for item in raw.get("fidelity_flags", [])
        if isinstance(item, str) and item
    }
    target_metadata = runtime.target.as_metadata() if runtime.target else {
        "target_question_id": None,
        "target_correctness": None,
        "error_code": None,
        "historical_concept": None,
        "reasoning_process": None,
        "evidence_ids": [],
        "probe_kind": "general_question",
    }

    if runtime.interaction_mode == "direct":
        if "？" in response_text or "?" in response_text:
            flags.add("direct_question_present")
        expected_text = (
            str(runtime.target.expected_answer).strip()
            if runtime.target and runtime.target.expected_answer is not None
            else ""
        )
        if expected_text and expected_text not in response_text:
            flags.add("direct_correction_missing")
        return {
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "condition_code": runtime.condition_code,
            "interaction_mode": "direct",
            "dialogue_state": "DIRECT_RESPONSE",
            "dialogue_move": "direct_correction",
            "scaffold_level": None,
            "attempts_in_state": 0,
            "learner_revision_status": raw.get("learner_revision_status") or "not_applicable",
            "completion_status": "complete",
            "fidelity_flags": sorted(flags),
            **target_metadata,
        }

    proposed_state = raw.get("dialogue_state")
    if proposed_state not in runtime.allowed_states:
        flags.add("invalid_state_transition")
        proposed_state = runtime.previous_state if runtime.previous_state in runtime.allowed_states else runtime.allowed_states[0]
    expected_move = DIALOGUE_MOVE_BY_STATE[proposed_state]
    if raw.get("dialogue_move") not in {None, expected_move}:
        flags.add("invalid_dialogue_move")

    question_count = response_text.count("？") + response_text.count("?")
    if proposed_state != "RESOLVED" and question_count == 0:
        flags.add("missing_scaffold_question")
    if question_count > 1:
        flags.add("multiple_scaffold_questions")
    if len(response_text) > 700:
        flags.add("overlong_scaffold_response")
    expected_text = (
        str(runtime.target.expected_answer).strip()
        if runtime.target and runtime.target.expected_answer is not None
        else ""
    )
    if proposed_state != "RESOLVED" and expected_text and expected_text in response_text:
        flags.add("early_answer_exposure")

    same_state = proposed_state == runtime.previous_state
    attempts_in_state = runtime.previous_attempts_in_state + 1 if same_state else 0
    completion_status = "resolved" if proposed_state == "RESOLVED" else "continue"
    revision_status = raw.get("learner_revision_status")
    if revision_status not in {"not_yet", "partial", "revised", "unresolved"}:
        revision_status = "revised" if proposed_state == "RESOLVED" else "not_yet"

    return {
        "interaction_policy_version": INTERACTION_POLICY_VERSION,
        "condition_code": runtime.condition_code,
        "interaction_mode": "scaffold",
        "dialogue_state": proposed_state,
        "dialogue_move": expected_move,
        "scaffold_level": _scaffold_level(runtime, proposed_state, raw.get("scaffold_level")),
        "attempts_in_state": attempts_in_state,
        "learner_revision_status": revision_status,
        "completion_status": completion_status,
        "fidelity_flags": sorted(flags),
        **target_metadata,
    }


def initial_greeting_metadata(condition: Any, task_attempt: Any, greeting: str) -> dict[str, Any]:
    """Mark the greeting as the first direct correction or EBL reasoning probe."""
    runtime = build_interaction_runtime(condition, task_attempt, [])
    raw: dict[str, Any]
    if runtime.interaction_mode == "direct":
        raw = {"learner_revision_status": "not_applicable"}
    else:
        raw = {
            "dialogue_state": EBL_INITIAL_STATE if runtime.target else "RESOLVED",
            "dialogue_move": "reasoning_probe" if runtime.target else "resolution",
            "scaffold_level": "L0",
            "learner_revision_status": "not_yet" if runtime.target else "revised",
        }
    return resolve_interaction_metadata(runtime, raw, greeting)
