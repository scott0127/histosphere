"""Backend-owned interaction contract for the fixed 2x2 experiment."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Literal, Sequence

from app.core.experiment_conditions import condition_code_for_key
from app.core.historical_ebl_policy import (
    HISTORICAL_EBL_MOVES,
    HISTORICAL_EBL_POLICY_VERSION,
    MAX_FOCUSED_QUESTIONS_PER_TURN,
    historical_thinking_focus,
    primary_reasoning_move,
)


InteractionMode = Literal["standard_chat", "scaffold"]
DialogueState = Literal[
    "STANDARD_CHAT",
    "ELICIT_REASONING",
    "INSPECT_EVIDENCE",
    "CONTEXTUALIZE_OR_COMPARE",
    "REVISE_CLAIM",
    "REFLECT",
    "RESOLVED",
]

INTERACTION_POLICY_VERSION = "2x2-interaction-v3"
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
    "STANDARD_CHAT": "natural_response",
    **{
        state: policy.dialogue_move
        for state, policy in HISTORICAL_EBL_MOVES.items()
    },
}
DISCLOSURE_LEVELS = ("D0", "D1", "D2", "D3", "D4")
LEGACY_DISCLOSURE_LEVELS = {f"L{index}": level for index, level in enumerate(DISCLOSURE_LEVELS)}
INTERACTION_RETRY_FLAGS = frozenset(
    {
        "invalid_state_transition",
        "invalid_dialogue_move",
        "excessive_scaffold_questions",
        "overlong_scaffold_response",
        "early_answer_exposure",
        "next_target_transition_missing",
    }
)


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
    next_target: InteractionTarget | None
    target_sequence_number: int | None
    target_count: int
    previous_state: DialogueState | None
    allowed_states: tuple[DialogueState, ...]
    previous_disclosure_level: str | None
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
            f"Historical EBL policy version: {HISTORICAL_EBL_POLICY_VERSION}\n"
            f"Interaction mode: {self.interaction_mode}\n"
            f"Current target position: {self.target_sequence_number or 0}/{self.target_count}\n"
            f"Current target: {json.dumps(target_payload, ensure_ascii=False)}"
        )
        if self.interaction_mode == "standard_chat":
            return (
                f"{shared}\n"
                "Required behavior: conduct a natural historical conversation. Answer the learner's actual request and "
                "ask a clarification or follow-up when useful. Do not force a correction, Socratic sequence, evidence "
                "exercise, revision, or reflection.\n"
                "Structured interaction fields must be dialogue_state=STANDARD_CHAT, "
                "dialogue_move=natural_response, completion_status=continue, and disclosure_level=null."
            )

        state_moves = ", ".join(
            f"{state}={DIALOGUE_MOVE_BY_STATE[state]}"
            for state in self.allowed_states
        )
        move_rules = {
            state: {
                "primary_reasoning_move": primary_reasoning_move(state),
                "learner_action": HISTORICAL_EBL_MOVES[state].learner_action,
                "allowed_support": list(HISTORICAL_EBL_MOVES[state].allowed_support),
            }
            for state in self.allowed_states
        }
        next_target_payload = (
            {
                "question_id": self.next_target.question_id,
                "prompt": self.next_target.prompt,
                "historical_thinking_focus": historical_thinking_focus(
                    self.next_target.historical_concept,
                    self.next_target.reasoning_process,
                ),
            }
            if self.next_target
            else None
        )
        return (
            f"{shared}\n"
            f"Target historical-thinking focus: "
            f"{historical_thinking_focus(target.historical_concept, target.reasoning_process) if target else 'none'}\n"
            f"Previous dialogue state: {self.previous_state or 'NONE'}\n"
            f"Allowed response states: {', '.join(self.allowed_states)}\n"
            f"Allowed state-to-move mapping: {state_moves}\n"
            f"Allowed move rules: {json.dumps(move_rules, ensure_ascii=False)}\n"
            f"Previous disclosure level: {self.previous_disclosure_level or 'NONE'}\n"
            f"Previous attempts in state: {self.previous_attempts_in_state}\n"
            f"Next unresolved target for transition only: {json.dumps(next_target_payload, ensure_ascii=False)}\n"
            "Required behavior: choose exactly one allowed response state after assessing the learner's latest "
            "message. Perform one primary historical-reasoning move for the current target. A move may be expressed "
            "as a cue, evidence pointer, contrast, sentence stem, or zero to two tightly related questions; do not "
            "turn every turn into an interview. Do not discuss a second task error before RESOLVED. When RESOLVED "
            "and a next target exists, briefly confirm the current correction and bridge to that next target without "
            "revealing its answer. Before RESOLVED, do not reveal the complete expected answer at any disclosure "
            "level. If the learner has not progressed, remain in the previous state and "
            "increase support by at most one level. If the learner has progressed, advance by at most one state. "
            "When evidence_ids is empty, use only event_context or task_source_text as contextual evidence and do "
            "not invent a source ID or quotation."
        )


@dataclass(frozen=True)
class EnforcedInteractionResponse:
    """Validated candidate; callers must regenerate when ``retry_required`` is true."""

    response: str
    metadata: dict[str, Any]
    fallback_applied: bool
    retry_required: bool = False


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


def _interaction_queue(task_attempt: Any | None) -> list[dict[str, Any]]:
    """Return the stable task-order queue used by this conversation."""

    results = _question_results(task_attempt)
    error_results = [
        result
        for result in results
        if str(result.get("correctness") or "ungraded") != "correct"
    ]
    if error_results:
        return error_results
    return results[:1]


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
    """Keep one task error stable, then advance through the queue in task order."""
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

    queue = _interaction_queue(task_attempt)
    resolved_ids = _resolved_question_ids(messages)
    last_metadata = _last_interaction_metadata(messages)
    last_target_id = last_metadata.get("target_question_id")
    if isinstance(last_target_id, str) and last_target_id not in resolved_ids:
        for result in queue:
            if result.get("question_id") == last_target_id:
                return _target_from_result(result)

    for result in queue:
        if result.get("question_id") not in resolved_ids:
            return _target_from_result(result)
    return None


def _target_queue_context(
    task_attempt: Any | None,
    messages: Sequence[Any],
    target: InteractionTarget | None,
) -> tuple[InteractionTarget | None, int | None, int]:
    queue = _interaction_queue(task_attempt)
    if not queue or not target:
        return None, None, len(queue)

    resolved_ids = _resolved_question_ids(messages)
    current_index = next(
        (
            index
            for index, result in enumerate(queue)
            if result.get("question_id") == target.question_id
        ),
        None,
    )
    next_target = next(
        (
            _target_from_result(result)
            for result in queue
            if result.get("question_id") != target.question_id
            and result.get("question_id") not in resolved_ids
        ),
        None,
    )
    return next_target, (current_index + 1 if current_index is not None else None), len(queue)


def build_interaction_runtime(
    condition: Any,
    task_attempt: Any | None,
    messages: Sequence[Any],
) -> InteractionRuntime:
    """Build the backend-owned policy input for one completion."""
    interaction_mode: InteractionMode = "scaffold" if condition.ebl_enabled else "standard_chat"
    if interaction_mode == "standard_chat":
        return InteractionRuntime(
            condition_code=condition_code_for_key(condition.condition_key),
            condition_key=condition.condition_key,
            interaction_mode=interaction_mode,
            roleplay_enabled=condition.roleplay_enabled,
            target=None,
            next_target=None,
            target_sequence_number=None,
            target_count=0,
            previous_state=None,
            allowed_states=("STANDARD_CHAT",),
            previous_disclosure_level=None,
            previous_attempts_in_state=0,
        )

    target = select_interaction_target(task_attempt, messages)
    next_target, target_sequence_number, target_count = _target_queue_context(
        task_attempt,
        messages,
        target,
    )
    previous_metadata = _last_interaction_metadata(messages)
    last_target_id = previous_metadata.get("target_question_id")
    target_changed = bool(
        target
        and last_target_id is not None
        and target.question_id != last_target_id
    )
    transition_started = bool(
        target_changed
        and previous_metadata.get("next_target_started")
        and previous_metadata.get("next_target_question_id") == target.question_id
    )
    raw_previous_state = previous_metadata.get("dialogue_state")
    if transition_started:
        previous_state: DialogueState | None = EBL_INITIAL_STATE
        previous_disclosure_level = "D0"
        previous_attempts_in_state = 0
    elif target_changed:
        previous_state = None
        previous_disclosure_level = None
        previous_attempts_in_state = 0
    else:
        previous_state = (
            raw_previous_state
            if raw_previous_state in EBL_STATE_TRANSITIONS
            else None
        )
        previous_disclosure_level = _normalize_disclosure_level(
            previous_metadata.get("disclosure_level") or previous_metadata.get("scaffold_level")
        )
        previous_attempts_in_state = int(previous_metadata.get("attempts_in_state") or 0)
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
        next_target=next_target,
        target_sequence_number=target_sequence_number,
        target_count=target_count,
        previous_state=previous_state,
        allowed_states=allowed_states,
        previous_disclosure_level=previous_disclosure_level,
        previous_attempts_in_state=previous_attempts_in_state,
    )


def _normalize_disclosure_level(raw_level: Any) -> str | None:
    if raw_level in DISCLOSURE_LEVELS:
        return str(raw_level)
    return LEGACY_DISCLOSURE_LEVELS.get(str(raw_level))


def _disclosure_level(runtime: InteractionRuntime, state: str, raw_level: Any) -> str:
    normalized_level = _normalize_disclosure_level(raw_level)
    if normalized_level in DISCLOSURE_LEVELS:
        suggested_index = DISCLOSURE_LEVELS.index(normalized_level)
    else:
        suggested_index = 0
    previous_index = (
        DISCLOSURE_LEVELS.index(runtime.previous_disclosure_level)
        if runtime.previous_disclosure_level in DISCLOSURE_LEVELS
        else 0
    )
    if state == runtime.previous_state:
        return DISCLOSURE_LEVELS[min(4, max(suggested_index, previous_index + 1))]
    return DISCLOSURE_LEVELS[min(4, max(suggested_index, previous_index - 1, 0))]


def _answer_text(value: Any) -> str:
    if value is True:
        return "是"
    if value is False:
        return "否"
    return str(value).strip() if value is not None else ""


def _contains_expected_answer(response_text: str, expected_answer: Any) -> bool:
    answer = _answer_text(expected_answer)
    if not answer:
        return False
    compact = re.sub(r"\s+", "", response_text)
    if expected_answer is True:
        return any(
            marker in compact
            for marker in ("答案是「是」", "正確答案是「是」", "判斷為真", "這個判斷正確")
        )
    if expected_answer is False:
        return any(
            marker in compact
            for marker in ("答案是「否」", "正確答案是「否」", "判斷為假", "這個判斷不正確", "說法不成立")
        )
    if len(answer) >= 4:
        return answer in response_text
    return any(
        marker in compact
        for marker in (
            f"「{answer}」",
            f"『{answer}』",
            f"答案是{answer}",
            f"正確答案是{answer}",
            f"應以{answer}",
            f"按{answer}",
            f"選擇{answer}",
            f"填入{answer}",
        )
    )


def resolve_interaction_metadata(
    runtime: InteractionRuntime,
    provider_metadata: dict[str, Any] | None,
    response_text: str,
) -> dict[str, Any]:
    """Validate model-proposed metadata against the backend-owned condition contract."""
    raw = provider_metadata if isinstance(provider_metadata, dict) else {}
    provider_flags = sorted(
        {
            str(item)
            for item in raw.get("fidelity_flags", [])
            if isinstance(item, str) and item
        }
    )
    flags: set[str] = set()
    target_metadata = runtime.target.as_metadata() if runtime.target else {
        "target_question_id": None,
        "target_correctness": None,
        "error_code": None,
        "historical_concept": None,
        "reasoning_process": None,
        "evidence_ids": [],
        "probe_kind": "general_question",
    }
    target_metadata.update(
        {
            "historical_ebl_policy_version": HISTORICAL_EBL_POLICY_VERSION,
            "historical_thinking_focus": (
                historical_thinking_focus(
                    runtime.target.historical_concept,
                    runtime.target.reasoning_process,
                )
                if runtime.target
                else None
            ),
            "target_sequence_number": runtime.target_sequence_number,
            "target_count": runtime.target_count,
            "next_target_question_id": runtime.next_target.question_id if runtime.next_target else None,
        }
    )

    if runtime.interaction_mode == "standard_chat":
        return {
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "condition_code": runtime.condition_code,
            "interaction_mode": "standard_chat",
            "dialogue_state": "STANDARD_CHAT",
            "dialogue_move": "natural_response",
            "disclosure_level": None,
            "attempts_in_state": 0,
            "learner_revision_status": raw.get("learner_revision_status") or "not_applicable",
            "completion_status": "continue",
            "fidelity_flags": sorted(flags),
            "provider_fidelity_flags": provider_flags,
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
    if question_count > MAX_FOCUSED_QUESTIONS_PER_TURN:
        flags.add("excessive_scaffold_questions")
    if len(response_text) > 700:
        flags.add("overlong_scaffold_response")
    resolved_disclosure_level = _disclosure_level(
        runtime,
        proposed_state,
        raw.get("disclosure_level") or raw.get("scaffold_level"),
    )
    expected_answer = runtime.target.expected_answer if runtime.target else None
    if (
        proposed_state != "RESOLVED"
        and expected_answer is not None
        and _contains_expected_answer(response_text, expected_answer)
    ):
        flags.add("early_answer_exposure")

    same_state = proposed_state == runtime.previous_state
    attempts_in_state = runtime.previous_attempts_in_state + 1 if same_state else 0
    completion_status = "resolved" if proposed_state == "RESOLVED" else "continue"
    next_target_started = bool(proposed_state == "RESOLVED" and runtime.next_target)
    if (
        next_target_started
        and not any(marker in response_text for marker in ("下一", "接著", "再看", "換到"))
    ):
        flags.add("next_target_transition_missing")
    revision_status = raw.get("learner_revision_status")
    if revision_status not in {"not_yet", "partial", "revised", "unresolved"}:
        revision_status = "revised" if proposed_state == "RESOLVED" else "not_yet"

    return {
        "interaction_policy_version": INTERACTION_POLICY_VERSION,
        "condition_code": runtime.condition_code,
        "interaction_mode": "scaffold",
        "dialogue_state": proposed_state,
        "dialogue_move": expected_move,
        "primary_historical_thinking_move": primary_reasoning_move(proposed_state),
        "disclosure_level": resolved_disclosure_level,
        "attempts_in_state": attempts_in_state,
        "learner_revision_status": revision_status,
        "completion_status": completion_status,
        "next_target_started": next_target_started,
        "fidelity_flags": sorted(flags),
        "provider_fidelity_flags": provider_flags,
        **target_metadata,
    }


def enforce_interaction_response(
    runtime: InteractionRuntime,
    provider_metadata: dict[str, Any] | None,
    response_text: str,
) -> EnforcedInteractionResponse:
    """Validate a candidate and require regeneration instead of writing visible fallback prose."""
    metadata = resolve_interaction_metadata(runtime, provider_metadata, response_text)
    flags = set(metadata["fidelity_flags"])
    metadata["fidelity_flags"] = sorted(flags)
    retry_required = bool(flags.intersection(INTERACTION_RETRY_FLAGS))
    metadata["fidelity_fallback_applied"] = False
    metadata["fidelity_retry_required"] = retry_required
    if retry_required:
        metadata["rejected_response_sha256"] = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
        metadata["rejected_response_length"] = len(response_text)
    return EnforcedInteractionResponse(
        response=response_text,
        metadata=metadata,
        fallback_applied=False,
        retry_required=retry_required,
    )


def enforce_initial_greeting(
    condition: Any,
    task_attempt: Any,
    greeting: str,
) -> EnforcedInteractionResponse:
    """Enforce the first AI turn with the same contract as later chat turns."""
    runtime = build_interaction_runtime(condition, task_attempt, [])
    raw: dict[str, Any]
    if runtime.interaction_mode == "standard_chat":
        raw = {
            "dialogue_state": "STANDARD_CHAT",
            "dialogue_move": "natural_response",
            "learner_revision_status": "not_applicable",
        }
    else:
        raw = {
            "dialogue_state": EBL_INITIAL_STATE if runtime.target else "RESOLVED",
            "dialogue_move": "reasoning_probe" if runtime.target else "resolution",
            "disclosure_level": "D0",
            "learner_revision_status": "not_yet" if runtime.target else "revised",
        }
    return enforce_interaction_response(runtime, raw, greeting)


def initial_greeting_metadata(condition: Any, task_attempt: Any, greeting: str) -> dict[str, Any]:
    """Return enforced first-turn metadata for compatibility callers."""
    return enforce_initial_greeting(condition, task_attempt, greeting).metadata
