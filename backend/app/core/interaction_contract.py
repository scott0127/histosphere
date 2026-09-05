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
    primary_reasoning_move,
)


InteractionMode = Literal["standard_chat", "scaffold"]
DialogueState = Literal[
    "STANDARD_CHAT",
    "NOTICE_ERROR",
    "REFLECT",
    "SELF_CORRECT",
    "RESOLVED",
]

INTERACTION_POLICY_VERSION = "2x2-interaction-v10-persona-led"
COMPATIBLE_INTERACTION_POLICY_VERSIONS = {
    INTERACTION_POLICY_VERSION,
    "2x2-interaction-v9",
    "2x2-interaction-v8",
    "2x2-interaction-v7",
    "2x2-interaction-v6",
    "2x2-interaction-v5",
    "2x2-interaction-v4",
    "2x2-interaction-v3",
}
EBL_INITIAL_STATE: DialogueState = "NOTICE_ERROR"
# 只在讀取舊活動時轉換狀態，不把舊 HT 技能名稱再送給生成模型。
LEGACY_EBL_STATES = {
    "ELICIT_REASONING": "NOTICE_ERROR",
    "INSPECT_EVIDENCE": "NOTICE_ERROR",
    "CONTEXTUALIZE_OR_COMPARE": "REFLECT",
    "REVISE_CLAIM": "SELF_CORRECT",
}
EBL_STATE_TRANSITIONS: dict[str, tuple[DialogueState, ...]] = {
    # 一次回答可同時展現反思與修正，不強迫為每個步驟多聊一輪。
    "NOTICE_ERROR": ("NOTICE_ERROR", "REFLECT", "SELF_CORRECT", "RESOLVED"),
    "REFLECT": ("REFLECT", "SELF_CORRECT", "RESOLVED"),
    "SELF_CORRECT": ("SELF_CORRECT", "REFLECT", "RESOLVED"),
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
# 等級只限制針對當前錯誤的解題協助，不限制人物語氣、篇幅或一般歷史背景。
# 背景若實際提示了答案，仍須算入協助；不能透過人物敘事繞過界線。
DISCLOSURE_POLICY = {
    "D0": {
        "allowed": (
            "Engage the learner's claim and invite independent reconsideration. Acknowledge any rationale already "
            "submitted instead of asking the learner to repeat it. Event orientation and a personal reaction are welcome."
        ),
        "hard_ceiling": (
            "Do not supply a new key solution clue, diagnose the missing distinction for the learner, or correct their "
            "answer or rationale. Background may establish the situation, but must not do this problem-solving work."
        ),
    },
    "D1": {
        "allowed": (
            "Point out a doubt, direction, or distinction worth reconsidering in the current claim. "
            "Explain what to think about without doing the comparison or correction for the learner."
        ),
        "hard_ceiling": (
            "Do not supply the decisive content or explanation that settles the item. A direction must leave the "
            "learner something substantive to work out, not merely invite agreement with a supplied answer."
        ),
    },
    "D2": {
        "allowed": (
            "Offer partial relevant information or a useful clue, explaining its meaning if needed. "
            "Use accurate task content or well-established historical knowledge within the identity's knowledge boundary."
        ),
        "hard_ceiling": (
            "Leave a task-specific part of the correction for the learner to work out. Do not supply all the decisive "
            "details and leave only an option letter, agreement, or rewording to the learner."
        ),
    },
    "D3": {
        "allowed": (
            "Connect information already offered, highlight a tension, or break the difficulty into manageable parts. "
            "Make the route to revision clearer without completing it."
        ),
        "hard_ceiling": (
            "Leave a meaningful task-specific inference or revision to the learner, not just agreement with or "
            "repetition of the correction already supplied."
        ),
    },
    "D4": {
        "allowed": (
            "Offer the strongest support: organize what is known, clarify what remains unresolved, and make a final "
            "independent answer and rationale attempt possible. Follow the runtime's final-answer sequence."
        ),
        "hard_ceiling": (
            "Do not provide the complete correction before the learner's final attempt or demonstrated self-correction. "
            "Full corrective feedback is a separate runtime-authorized step, not another Disclosure level."
        ),
    },
}
LEGACY_DISCLOSURE_LEVELS = {f"L{index}": level for index, level in enumerate(DISCLOSURE_LEVELS)}
# dialogue_move 由已驗證的 dialogue_state 唯一決定；供應商填錯時留旗標並由後端正規化，不浪費一次生成。
INTERACTION_RETRY_FLAGS = frozenset(
    {
        "invalid_state_transition",
        "invalid_disclosure_transition",
        "excessive_scaffold_questions",
        "overlong_scaffold_response",
        "early_answer_exposure",
        "incomplete_resolution_criteria",
        "next_target_transition_missing",
        "corrective_answer_missing",
        "invalid_completion_status",
        "next_answer_exposure",
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
    error_source: str
    blank_id: str | None = None
    question_type: str | None = None
    learner_rationale: str | None = None
    answer_correct: bool | None = None
    reasoning_correct: bool | None = None
    historical_thinking_tags: tuple[str, ...] = ()
    # 僅用於讀取舊 judgement_payload；新版 Judge 不再產生此欄位。
    reasoning_issue: str | None = None
    reasoning_feedback: str | None = None
    reasoning_criteria: Any = None

    def as_metadata(self) -> dict[str, Any]:
        return {
            "target_question_id": self.question_id,
            "target_correctness": self.correctness,
            "error_code": self.error_code,
            "historical_concept": self.historical_concept,
            "reasoning_process": self.reasoning_process,
            "evidence_ids": list(self.evidence_ids),
            "probe_kind": self.probe_kind,
            "error_source": self.error_source,
            "blank_id": self.blank_id,
            "question_type": self.question_type,
            "answer_correct": self.answer_correct,
            "reasoning_correct": self.reasoning_correct,
            "historical_thinking_tags": list(self.historical_thinking_tags),
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
    previous_completion_status: str | None

    @property
    def final_answer_required(self) -> bool:
        """D4 後仍未修正，先請 learner 整理最後答案，不先公布正解。"""

        return bool(
            self.interaction_mode == "scaffold"
            and self.target is not None
            and self.previous_disclosure_level == "D4"
            and self.previous_completion_status == "continue"
        )

    @property
    def corrective_feedback_required(self) -> bool:
        """最後答案已送來，本回合給修正回饋後結束，不再要求再答一次。"""

        return bool(
            self.interaction_mode == "scaffold"
            and self.target is not None
            # 舊活動若已先公布答案，也以一次回饋收尾，不重啟 D4 流程。
            and self.previous_completion_status in {"final_answer_pending", "corrective_resolution_pending"}
        )

    @property
    def allowed_disclosure_levels(self) -> tuple[str, ...]:
        """回傳本回合允許模型選擇的揭露等級，最多只能升降一級。"""
        if self.interaction_mode == "standard_chat":
            return ()
        if self.previous_disclosure_level not in DISCLOSURE_LEVELS:
            return ("D0",)
        previous_index = DISCLOSURE_LEVELS.index(self.previous_disclosure_level)
        start = max(0, previous_index - 1)
        end = min(len(DISCLOSURE_LEVELS), previous_index + 2)
        return DISCLOSURE_LEVELS[start:end]

    @property
    def prompt_disclosure_ceiling(self) -> str | None:
        """保留給既有 metadata 使用；實際決策範圍以 allowed_disclosure_levels 為準。"""

        allowed = self.allowed_disclosure_levels
        return allowed[-1] if allowed else None

    @property
    def source_content_available(self) -> bool:
        """模型可讀取內部判斷資料；Disclosure 只限制受測者實際看見的內容。"""

        return self.target is not None

    def prompt_block(self) -> str:
        target = self.target
        source_text = target.source_text if target else None
        target_payload = {
            "question_id": target.question_id if target else None,
            "prompt": target.prompt if target else "No task item is attached.",
            "task_source_text": source_text if target else None,
            "learner_answer": target.learner_answer if target else None,
            "expected_answer": target.expected_answer if target else None,
            "correctness": target.correctness if target else "ungraded",
            "error_code": target.error_code if target else None,
            "evidence_ids": list(target.evidence_ids) if target else [],
            "probe_kind": target.probe_kind if target else "general_question",
            "error_source": target.error_source if target else "none",
            "blank_id": target.blank_id if target else None,
            "question_type": target.question_type if target else None,
            "learner_rationale": target.learner_rationale if target else None,
            "answer_correct": target.answer_correct if target else None,
            "reasoning_correct": target.reasoning_correct if target else None,
            "historical_thinking_tags": list(target.historical_thinking_tags) if target else [],
            "reasoning_feedback": target.reasoning_feedback if target else None,
            "reasoning_criteria": target.reasoning_criteria if target else None,
        }
        shared = (
            f"Policy version: {INTERACTION_POLICY_VERSION}\n"
            f"EBL policy version: {HISTORICAL_EBL_POLICY_VERSION}\n"
            f"Interaction mode: {self.interaction_mode}\n"
            f"Current target position: {self.target_sequence_number or 0}/{self.target_count}\n"
            f"Current target: {json.dumps(target_payload, ensure_ascii=False)}\n"
            "Private evaluation context: task_source_text, expected_answer, reasoning_criteria, reasoning_feedback, "
            "and evidence_ids are private references for assessing progress and selecting appropriate help. "
            "Knowing these references does not authorize revealing the complete correction; every response must "
            "follow the interaction mode and, during scaffolding, the selected Disclosure level. "
            "Terminal feedback authorized below is the only pre-transition exception. "
            "If error_source=researcher_authored_fallback, this is another person's claim, not a learner mistake."
        )
        if target and target.reasoning_correct is not None:
            shared += (
                "\nThe submitted learner_rationale is the learner's original wording, not an inferred belief. "
                "An item is correct only when answer_correct and reasoning_correct are both true. "
                "When the answer is right but the reasoning is not, focus on the reasoning gap; do not describe "
                "the answer itself as wrong. Use reasoning_feedback to locate the concrete factual or inferential "
                "deficiency, but do not quote it to the learner or disclose more than the current Disclosure level. "
                "An inadequate rationale is not automatically proof of a factual misconception. Historical Thinking "
                "tags describe what the rationale engages and are not a score or an instruction to teach that label. "
                "Do not invent a misconception or attribute an unstated belief to the learner. These distinctions do not change the dialogue "
                "states, Disclosure progression, or formal RESOLVED criteria."
            )
        if self.interaction_mode == "standard_chat":
            return (
                f"{shared}\n"
                "Required behavior: conduct a natural historical conversation. Answer the learner's actual request and "
                "ask a clarification or follow-up when useful. Do not force a correction, Socratic sequence, evidence "
                "exercise, revision, or reflection.\n"
                "Structured interaction fields must be dialogue_state=STANDARD_CHAT, "
                "dialogue_move=natural_response, completion_status=continue, disclosure_level=null, and all three "
                "resolution_* fields=false."
            )

        state_moves = ", ".join(
            f"{state}={DIALOGUE_MOVE_BY_STATE[state]}"
            for state in self.allowed_states
        )
        move_rules = {
            state: {
                "primary_ebl_move": primary_reasoning_move(state),
                "learner_action": HISTORICAL_EBL_MOVES[state].learner_action,
                "allowed_support": list(HISTORICAL_EBL_MOVES[state].allowed_support),
            }
            for state in self.allowed_states
        }
        next_target_payload = (
            {
                "question_id": self.next_target.question_id,
                "prompt": self.next_target.prompt,
                "learner_answer": self.next_target.learner_answer,
                "learner_rationale": self.next_target.learner_rationale,
            }
            if self.next_target
            else None
        )
        if target is None:
            terminal_instruction = (
                "No unresolved target remains. Do not invent a learner error. Use dialogue_state=RESOLVED, "
                "dialogue_move=resolution, completion_status=resolved, and continue ordinary event discussion "
                "without asserting that the timed experiment has ended."
            )
        elif self.corrective_feedback_required:
            terminal_instruction = (
                "Terminal feedback: the learner has submitted their final answer and rationale. Regardless of its "
                "quality, now state the verified expected_answer clearly and briefly explain the corrected "
                "interpretation using the current question's criteria and materials. If the answer was already "
                "right but its rationale was wrong, confirm the answer and correct the rationale. Do not just "
                "acknowledge an incorrect final answer. Only AFTER this feedback, bridge to the next target if one "
                "exists, without its answer. Use dialogue_state=RESOLVED, dialogue_move=corrective_feedback, "
                "completion_status=feedback_completed. Do not ask for another restatement or continue grading "
                "this target. This also finishes legacy activities that already received corrective feedback."
            )
        elif self.final_answer_required:
            terminal_instruction = (
                "Max-support decision: this learner message follows D4 support. If the learner has already "
                "recognized, reflected on, and corrected the error, resolve normally and confirm the verified "
                "answer before transitioning. Otherwise, elicit one final answer and rationale from the learner "
                "without supplying either. Do NOT give the correct answer yet and do NOT change target. Use "
                "dialogue_state=SELF_CORRECT, dialogue_move=final_answer_prompt, disclosure_level=D4, "
                "completion_status=final_answer_pending. The next learner reply triggers terminal feedback, "
                "not another round of assessment or hints."
            )
        else:
            terminal_instruction = (
                "Before the final-answer step, withhold the correct answer unless the learner has already "
                "self-corrected and met the EBL resolution criteria. Do not request final-answer closure early."
            )
        persona_turn_policy = (
            "\n04 conversational priority: the historical person leads; the following EBL actions describe "
            "learning support, not the whole content of the reply. Develop a substantive historical point through "
            "the person's concerns and integrate the learning invitation where it belongs. "
            "If a later learner message discusses a related historical matter rather than the current error, "
            "you may use dialogue_move=natural_response without a forced EBL question. Keep the previous "
            "dialogue_state and disclosure_level, completion_status=continue, learner_progress=not_assessed, "
            "and all resolution_* fields=false. This is NOT off_topic_redirect. Do not advance or resolve the "
            "error, count a failed attempt, or increase support during this conversational turn. The same "
            "solution-assistance ceiling still applies. Opening, final-answer and corrective-feedback turns "
            "cannot take this interlude; their required steps remain binding.\n"
            if self.roleplay_enabled else ""
        )
        if self.roleplay_enabled:
            # 04 只交付隱藏判斷資料，不把教師的句型、填空模板當成人物應說的話。
            return (
                f"{shared}\n"
                "Hidden EBL opportunity within a character-led historical conversation. Determine whether the latest "
                "reply recognizes the current error, reflects on it, or corrects it. The historical person chooses "
                "what they have to say; these internal state names are not a script or the subject of their speech. "
                "Do not turn an option letter, worksheet instruction or sentence stem into the conversation. "
                "Engage the historical claim behind it. Historical Thinking is the AI's shared quality basis, not "
                "a separate learner skill exercise.\n"
                f"Disclosure policy: {json.dumps(DISCLOSURE_POLICY, ensure_ascii=False)}\n"
                "Disclosure controls ONLY assistance that settles the current error, not historical discussion, "
                "personality or reply length. Historical context, concerns and judgments may develop at every level. "
                "A decisive explanation hidden in that narrative still counts as solution assistance. Withholding "
                "an option letter is insufficient if the learner need only repeat your supplied correction. "
                "Reliable historical knowledge beyond supplied materials is allowed within the person's time and access; "
                "never invent a source, quotation or firsthand experience.\n"
                f"Previous state: {self.previous_state or 'NONE'}\n"
                f"Allowed states/moves: {state_moves}\n"
                f"Previous Disclosure: {self.previous_disclosure_level or 'NONE'}\n"
                f"Allowed Disclosure this turn: {', '.join(self.allowed_disclosure_levels)}\n"
                f"Next target (only after closing this one): {json.dumps(next_target_payload, ensure_ascii=False)}\n"
                "Select the permitted state and assistance level from the learner's actual contribution. Levels move "
                "at most one step. Record progress and the reason privately. With no learner reply yet, use D0 and "
                "not_assessed; invite discussion of the original claim without supplying its correction. "
                "When giving learning support, let the person's substantive response carry it; no more than two related "
                "questions are needed, and a question is not mandatory in every turn.\n"
                "Self-correction is established only when the learner (1) recognizes what in their answer or reason "
                "needs changing, (2) explains why, and (3) gives a revised answer AND reason satisfying the existing "
                "question criteria. These may appear across turns. Set the three resolution_* booleans from this "
                "evidence, not merely a correct answer or terminology; require no additional citation or named skill. "
                "If all three are met, use RESOLVED/resolution/resolved, confirm the verified answer before a natural "
                "bridge to the next error. Do not reveal the next answer or invent another error. If no target remains, "
                "continue historical conversation without claiming the timed stage ended.\n"
                "Unrelated requests use off_topic_redirect=true with no substantive answer; preserve state and "
                "Disclosure and do not count failure. A pending terminal correction still takes precedence.\n"
                f"{terminal_instruction}{persona_turn_policy}"
            )
        return (
            f"{shared}\n"
            "Decision order: select the EBL action (recognize the error, analyze/reflect, or self-correct), "
            "then select Disclosure to control assistance. Historical Thinking is the AI's shared historical "
            "response foundation in all four conditions, not an extra learner skill checklist in EBL. "
            "Do not prescribe a Historical Thinking technique, mandatory evidence citation, or source-comparison "
            "exercise. The learner may use such reasoning spontaneously.\n"
            f"Disclosure policy: {json.dumps(DISCLOSURE_POLICY, ensure_ascii=False)}\n"
            "Disclosure limits solution assistance for the current error, not response length, paragraph count, personality, "
            "or all historical information. Natural event context, personal concerns, and conversational framing may appear "
            "at every level. However, if they help settle this error, they count as solution assistance and must fit the "
            "selected level. Assess what the whole reply enables the learner to solve; do not mechanically count facts or "
            "hide extra help in a persona introduction or ending. Materials are not an exhaustive historical-knowledge whitelist. "
            "Use only reliable historical knowledge consistent with the active identity's time and access. A quotation or a "
            "claimed source still needs support. For a choice, true/false, or fill-in item, a seemingly small hint may itself "
            "give away the answer: withholding the answer label alone is insufficient. Treat the correct interpretation and "
            "its decisive rationale as part of the solution, not just expected_answer's literal text. Before sending, check "
            "what task-specific reasoning the learner still has to do: if only agreement, choosing a letter, or restating "
            "your supplied correction remains, reduce the solution assistance, not the character's voice or general context. "
            "Do not deliberately prolong the exchange "
            "when the learner has already recognized, reflected on, and corrected the error.\n"
            f"Previous dialogue state: {self.previous_state or 'NONE'}\n"
            f"Allowed response states: {', '.join(self.allowed_states)}\n"
            f"Allowed state-to-move mapping: {state_moves}\n"
            f"Allowed move rules: {json.dumps(move_rules, ensure_ascii=False)}\n"
            f"Previous disclosure level: {self.previous_disclosure_level or 'NONE'}\n"
            f"Allowed disclosure levels this turn: {', '.join(self.allowed_disclosure_levels)}\n"
            f"Maximum solution-assistance level allowed this turn: {self.prompt_disclosure_ceiling or 'NONE'}\n"
            f"Previous attempts in state: {self.previous_attempts_in_state}\n"
            f"Next unresolved target for transition only: {json.dumps(next_target_payload, ensure_ascii=False)}\n"
            "Required behavior: if no learner message exists yet, use learner_progress=not_assessed and D0. Otherwise, "
            "first assess the learner's latest message as no_progress, partial_progress, clear_progress, or resolved. "
            "Then choose exactly one disclosure level from the allowed list and briefly "
            "record the solution assistance chosen and why in disclosure_reason, not the amount of scene-setting or prose. "
            "Increase support when the learner shows little progress, keep it "
            "stable for partial progress, and reduce it when the learner demonstrates more independent reasoning. "
            "Do not change disclosure by more than one level. Choose exactly one allowed response state and perform "
            "one EBL action for the current error. An action may be expressed "
            "as a cue, reflection prompt, sentence stem, or zero to two tightly related questions; do not "
            "turn every turn into an interview. Do not discuss a second task error before RESOLVED. When RESOLVED "
            "and a next target exists, briefly confirm the current correction and bridge to that next target without "
            "revealing its answer. Confirm the current verified answer and briefly explain the correction before "
            "the bridge. During scaffolding, do not reveal the complete expected answer at any Disclosure level. "
            "The EBL action and Disclosure level are separate decisions. "
            "Self-correction criteria (may be demonstrated across turns): "
            "(1) resolution_error_recognized: the learner recognizes what in the original answer or rationale "
            "needs changing; (2) resolution_error_reflected: the learner explains what went wrong or why it needs "
            "changing; (3) resolution_self_corrected: the learner's revised answer AND rationale satisfy this "
            "question's existing reasoning_criteria. Do not require a new citation, named skill, or more criteria "
            "than the question requires. Do not infer success from just using a Historical Thinking term. "
            "A bare answer is insufficient. Use RESOLVED with completion_status=resolved only when all three "
            "are demonstrated; terminal feedback below closes the target separately without claiming independent "
            "self-correction. "
            "If off_topic_redirect=true, only redirect to the selected event: keep the current target, dialogue state, "
            "and disclosure level unchanged, use learner_progress=no_progress, and do not treat the off-topic message as "
            "another failed scaffold attempt. Exception: after a final answer was requested, close with verified "
            "feedback even if that reply is off topic, without answering the unrelated request. "
            "When evidence_ids is empty, do not invent a source ID, quotation, or retrieval claim. Reliable contextual "
            "knowledge remains available under the same solution-assistance and identity boundaries.\n"
            f"{terminal_instruction}{persona_turn_policy}"
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
        if question_result_correctness(result) != "correct"
    ]
    if error_results:
        return error_results
    if not results:
        return []

    judgement = getattr(task_attempt, "judgement_payload", None) if task_attempt else None
    fallback = judgement.get("all_correct_fallback") if isinstance(judgement, dict) else None
    if not isinstance(fallback, dict):
        return []
    incorrect_claim = str(fallback.get("incorrect_claim") or "").strip()
    correct_interpretation = str(fallback.get("correct_interpretation") or "").strip()
    if not incorrect_claim or not correct_interpretation:
        return []
    evidence_ids = fallback.get("evidence_ids")
    return [
        {
            "question_id": str(fallback.get("id") or "all-correct-fallback"),
            "prompt": (
                f"另一位學習者提出這個判斷：「{incorrect_claim}」"
                "請判斷這個說法並說明理由。"
            ),
            "source_text": fallback.get("source_text"),
            "learner_answer": incorrect_claim,
            "expected_answer": correct_interpretation,
            "correctness": "incorrect",
            "error_code": "researcher_authored_controlled_error",
            "historical_concept": fallback.get("historical_concept"),
            "reasoning_process": fallback.get("reasoning_process"),
            "evidence_ids": [str(item) for item in evidence_ids or [] if item],
            "probe_kind": "controlled_fallback",
            "error_source": "researcher_authored_fallback",
        }
    ]


def _resolved_question_ids(messages: Sequence[Any]) -> set[str]:
    resolved: set[str] = set()
    for message in messages:
        metadata = _message_metadata(message)
        # 終止性回饋會關閉 target；舊版跳題紀錄仍可讀，但新流程不再產生它。
        if metadata.get("completion_status") not in {
            "resolved",
            "complete",
            "unresolved_after_max_support",
            "corrected_after_feedback",
            "feedback_completed",
        }:
            continue
        question_id = metadata.get("target_question_id")
        if isinstance(question_id, str) and question_id:
            resolved.add(question_id)
    return resolved


def _last_interaction_metadata(messages: Sequence[Any]) -> dict[str, Any]:
    for message in reversed(messages):
        metadata = _message_metadata(message)
        if metadata.get("interaction_policy_version") in COMPATIBLE_INTERACTION_POLICY_VERSIONS:
            return metadata
    return {}


def question_result_correctness(result: dict[str, Any]) -> str:
    """Use both judgement dimensions when present; preserve legacy results."""
    if isinstance(result.get("answer_correct"), bool) and isinstance(result.get("reasoning_correct"), bool):
        return "correct" if result["answer_correct"] and result["reasoning_correct"] else "incorrect"
    return str(result.get("correctness") or "ungraded")


def _target_from_result(result: dict[str, Any]) -> InteractionTarget:
    correctness = question_result_correctness(result)
    probe_kind = str(
        result.get("probe_kind")
        or ("reasoning_gap" if result.get("answer_correct") is True and result.get("reasoning_correct") is False else None)
        or ("error_correction" if correctness != "correct" else "justification_probe")
    )
    evidence_ids = result.get("evidence_ids")
    historical_thinking_tags = result.get("historical_thinking_tags")
    if not isinstance(historical_thinking_tags, list):
        historical_thinking_tags = []
    return InteractionTarget(
        question_id=str(result.get("question_id")) if result.get("question_id") else None,
        prompt=str(result.get("question_text") or result.get("prompt") or "請說明你的判斷。"),
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
        error_source=str(result.get("error_source") or "learner_task_response"),
        blank_id=result.get("blank_id"),
        question_type=result.get("question_type"),
        learner_rationale=result.get("learner_rationale"),
        answer_correct=result.get("answer_correct"),
        reasoning_correct=result.get("reasoning_correct"),
        historical_thinking_tags=tuple(
            str(item)
            for item in historical_thinking_tags or []
            if item
        ),
        reasoning_issue=result.get("reasoning_issue"),
        reasoning_feedback=result.get("reasoning_feedback"),
        reasoning_criteria=result.get("reasoning_criteria"),
    )


def select_interaction_target(task_attempt: Any | None, messages: Sequence[Any]) -> InteractionTarget | None:
    """Keep one task error stable, then advance through the queue in task order."""
    results = _question_results(task_attempt)
    if not results:
        judgement = getattr(task_attempt, "judgement_payload", {}) if task_attempt else {}
        last_metadata = _last_interaction_metadata(messages)
        if (
            last_metadata.get("completion_status") in {"resolved", "complete", "feedback_completed", "corrected_after_feedback"}
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
            error_source="legacy_judgement_summary",
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
            previous_completion_status=None,
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
    raw_previous_state = LEGACY_EBL_STATES.get(raw_previous_state, raw_previous_state)
    raw_completion_status = previous_metadata.get("completion_status")
    if transition_started:
        previous_state: DialogueState | None = EBL_INITIAL_STATE
        previous_disclosure_level = "D0"
        previous_attempts_in_state = 0
        previous_completion_status = None
    elif target_changed:
        previous_state = None
        previous_disclosure_level = None
        previous_attempts_in_state = 0
        previous_completion_status = None
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
        previous_completion_status = (
            str(raw_completion_status) if isinstance(raw_completion_status, str) else None
        )
    if target is None:
        allowed_states: tuple[DialogueState, ...] = ("RESOLVED",)
    elif previous_completion_status in {"final_answer_pending", "corrective_resolution_pending"}:
        allowed_states = ("RESOLVED",)
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
        previous_completion_status=previous_completion_status,
    )


def _normalize_disclosure_level(raw_level: Any) -> str | None:
    if raw_level in DISCLOSURE_LEVELS:
        return str(raw_level)
    return LEGACY_DISCLOSURE_LEVELS.get(str(raw_level))


def _disclosure_level(runtime: InteractionRuntime, raw_level: Any) -> tuple[str, bool]:
    """驗證模型選擇的 D 等級；越級時回傳安全 fallback 並要求重新生成。"""

    normalized_level = _normalize_disclosure_level(raw_level)
    allowed = runtime.allowed_disclosure_levels or ("D0",)
    if normalized_level in allowed:
        return normalized_level, True
    fallback = (
        runtime.previous_disclosure_level
        if runtime.previous_disclosure_level in allowed
        else allowed[0]
    )
    return fallback, False


def _answer_text(value: Any) -> str:
    if value is True:
        return "是"
    if value is False:
        return "否"
    return str(value).strip() if value is not None else ""


def _contains_expected_answer(response_text: str, expected_answer: Any, *, terminal_feedback: bool = False) -> bool:
    # 填空可有多個可接受答案；回饋包含任一個即可，不要求輸出整個 Python list。
    if isinstance(expected_answer, (list, tuple)):
        return any(_contains_expected_answer(response_text, item, terminal_feedback=terminal_feedback) for item in expected_answer)
    answer = _answer_text(expected_answer)
    if not answer:
        return False
    compact = re.sub(r"\s+", "", response_text)
    if expected_answer is True:
        # 是非題可用「是／否」或「真／假」表達；辨認明確加引號的答案，
        # 不把判定綁死在「答案是」等單一句型上。
        if any(marker in compact for marker in ("「是」", "『是』", "「真」", "『真』")):
            return True
        return any(
            marker in compact
            for marker in (
                "答案是「是」",
                "正確答案是「是」",
                "答案是「真」",
                "正確答案是「真」",
                "正確判斷是「真」",
                "應選「真」",
                "選擇「真」",
                "判斷為真",
                "這個判斷正確",
            )
        )
    if expected_answer is False:
        if any(marker in compact for marker in ("「否」", "『否』", "「假」", "『假』")):
            return True
        return any(
            marker in compact
            for marker in (
                "答案是「否」",
                "正確答案是「否」",
                "答案是「假」",
                "正確答案是「假」",
                "正確判斷是「假」",
                "應選「假」",
                "選擇「假」",
                "判斷為假",
                "這個判斷不正確",
                "說法不成立",
            )
        )
    # 最終回饋可自然使用單一選項代號；較早階段仍要求明確作答語句，避免把「資料 A」誤判成洩漏。
    if terminal_feedback and len(answer) == 1 and answer.upper() in "ABCDEFGH":
        return re.search(
            rf"(?<![A-Za-z0-9]){re.escape(answer)}(?![A-Za-z0-9])",
            response_text,
            flags=re.IGNORECASE,
        ) is not None
    # 收尾需明示正解，但短姓名等不應被強迫加引號或套「正確答案是」固定話術。
    if len(answer) >= 4 or (terminal_feedback and len(answer) >= 2):
        return answer in response_text
    return any(
        marker in compact
        for marker in (
            f"「{answer}」",
            f"『{answer}』",
            f"答案是{answer}",
            f"正確答案是{answer}",
            f"應選{answer}",
            f"改選{answer}",
            f"選{answer}",
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
    off_topic_redirect = raw.get("off_topic_redirect") is True
    target_metadata = runtime.target.as_metadata() if runtime.target else {
        "target_question_id": None,
        "target_correctness": None,
        "error_code": None,
        "historical_concept": None,
        "reasoning_process": None,
        "evidence_ids": [],
        "probe_kind": "general_question",
        "error_source": "none",
    }
    target_metadata.update(
        {
            "historical_ebl_policy_version": HISTORICAL_EBL_POLICY_VERSION,
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
            "learner_progress": "not_assessed",
            "disclosure_reason": None,
            "off_topic_redirect": off_topic_redirect,
            "resolution_error_recognized": False,
            "resolution_error_reflected": False,
            "resolution_self_corrected": False,
            "resolution_criteria_met": False,
            "resolution_outcome": "not_applicable",
            "fidelity_flags": sorted(flags),
            "provider_fidelity_flags": provider_flags,
            **target_metadata,
        }

    corrective_feedback_delivered = runtime.corrective_feedback_required
    # 人物可回答相關歷史問題；此回合不是 EBL 失敗，也不是離題。
    conversational_turn = bool(
        runtime.roleplay_enabled and runtime.target is not None
        and runtime.previous_state is not None
        and not runtime.final_answer_required and not corrective_feedback_delivered
        and not off_topic_redirect and raw.get("dialogue_move") == "natural_response"
    )
    final_answer_required = runtime.final_answer_required and not off_topic_redirect
    proposed_state = raw.get("dialogue_state")
    if corrective_feedback_delivered:
        # learner 已有最後整理機會；即使仍錯或偏題，也給正解收尾，不再追加作答。
        off_topic_redirect = False
        proposed_state = "RESOLVED"
    elif off_topic_redirect or conversational_turn:
        # 離題只做範圍重新導向，不視為學習進展，也不推進 EBL 階段。
        proposed_state = (
            runtime.previous_state
            if runtime.previous_state in runtime.allowed_states
            else runtime.allowed_states[0]
        )
    elif proposed_state not in runtime.allowed_states:
        flags.add("invalid_state_transition")
        proposed_state = runtime.previous_state if runtime.previous_state in runtime.allowed_states else runtime.allowed_states[0]
    resolution_error_recognized = raw.get("resolution_error_recognized") is True
    resolution_error_reflected = raw.get("resolution_error_reflected") is True
    resolution_self_corrected = raw.get("resolution_self_corrected") is True
    if off_topic_redirect or conversational_turn or runtime.previous_completion_status == "corrective_resolution_pending":
        resolution_error_recognized = False
        resolution_error_reflected = False
        resolution_self_corrected = False
    resolution_criteria_met = all(
        (
            resolution_error_recognized,
            resolution_error_reflected,
            resolution_self_corrected,
        )
    )
    learner_self_resolved = bool(
        runtime.target is not None
        and resolution_criteria_met
        and not corrective_feedback_delivered
        and (proposed_state == "RESOLVED" or final_answer_required)
    )
    if learner_self_resolved and final_answer_required:
        # D4 後若已完成自我修正，不再多加一輪「最後答案」。
        flags.discard("invalid_state_transition")
        proposed_state = "RESOLVED"
    final_answer_requested = final_answer_required and not learner_self_resolved
    if final_answer_requested:
        proposed_state = "SELF_CORRECT"
    expected_move = (
        "corrective_feedback" if corrective_feedback_delivered
        else "final_answer_prompt" if final_answer_requested
        else "natural_response" if conversational_turn
        else DIALOGUE_MOVE_BY_STATE[proposed_state]
    )
    allowed_provider_moves = {expected_move} if (
        corrective_feedback_delivered or final_answer_requested
    ) else {None, expected_move}
    if not off_topic_redirect and raw.get("dialogue_move") not in allowed_provider_moves:
        flags.add("invalid_dialogue_move")
    if (
        runtime.target is not None
        and proposed_state == "RESOLVED"
        and not resolution_criteria_met
        and not corrective_feedback_delivered
    ):
        flags.add("incomplete_resolution_criteria")

    question_count = response_text.count("？") + response_text.count("?")
    if question_count > MAX_FOCUSED_QUESTIONS_PER_TURN:
        flags.add("excessive_scaffold_questions")
    # 04 人物表達驗收暫不設字數門檻；之後另行檢討正式 2x2 篇幅控制。
    if not runtime.roleplay_enabled and len(response_text) > 700:
        flags.add("overlong_scaffold_response")
    if final_answer_requested or corrective_feedback_delivered:
        resolved_disclosure_level = "D4"
    elif off_topic_redirect or conversational_turn:
        resolved_disclosure_level = (
            runtime.previous_disclosure_level
            if runtime.previous_disclosure_level in runtime.allowed_disclosure_levels
            else runtime.allowed_disclosure_levels[0]
        )
    else:
        resolved_disclosure_level, disclosure_transition_valid = _disclosure_level(
            runtime,
            raw.get("disclosure_level") or raw.get("scaffold_level"),
        )
        if not disclosure_transition_valid:
            flags.add("invalid_disclosure_transition")
    expected_answer = runtime.target.expected_answer if runtime.target else None
    terminal_feedback = corrective_feedback_delivered or learner_self_resolved
    answer_exposed = bool(
        expected_answer is not None
        and _contains_expected_answer(response_text, expected_answer, terminal_feedback=terminal_feedback)
    )
    if terminal_feedback:
        if expected_answer is not None and not answer_exposed:
            flags.add("corrective_answer_missing")
    elif (
        proposed_state != "RESOLVED" and answer_exposed
        # 答案本身已對時，重述 learner 的既有答案不是新洩漏；仍不能替他完成錯誤理由的修正。
        and not (runtime.target and runtime.target.answer_correct is True)
    ):
        flags.add("early_answer_exposure")

    same_state = proposed_state == runtime.previous_state
    attempts_in_state = (
        runtime.previous_attempts_in_state
        if off_topic_redirect or conversational_turn
        else runtime.previous_attempts_in_state + 1 if same_state else 0
    )
    if corrective_feedback_delivered:
        # 表示已給回饋，不代表 learner 看完之後已學會或自行修正成功。
        completion_status = "feedback_completed"
        resolution_outcome = "feedback_delivered"
    elif final_answer_requested:
        completion_status = "final_answer_pending"
        resolution_outcome = "awaiting_final_answer"
    elif proposed_state == "RESOLVED":
        completion_status = "resolved"
        resolution_outcome = "learner_resolved" if runtime.target else "no_target"
    else:
        completion_status = "continue"
        resolution_outcome = "in_progress"
    if not off_topic_redirect and raw.get("completion_status") not in {None, completion_status}:
        flags.add("invalid_completion_status")
    next_target_started = bool(
        runtime.next_target
        and (corrective_feedback_delivered or completion_status == "resolved")
    )
    if (
        next_target_started
        and not any(marker in response_text for marker in ("下一", "接著", "再看", "換到"))
    ):
        flags.add("next_target_transition_missing")
    if next_target_started:
        # 同一答案可出現在多題；只擋下一題獨有的答案，不誤擋上題必要回饋。
        current_answers = expected_answer if isinstance(expected_answer, (list, tuple)) else [expected_answer]
        next_answer = runtime.next_target.expected_answer
        next_answers = next_answer if isinstance(next_answer, (list, tuple)) else [next_answer]
        current_texts = {_answer_text(answer) for answer in current_answers}
        if any(
            _answer_text(answer) not in current_texts and _contains_expected_answer(response_text, answer)
            for answer in next_answers
        ):
            flags.add("next_answer_exposure")
    revision_status = raw.get("learner_revision_status")
    if corrective_feedback_delivered:
        revision_status = "revised" if resolution_self_corrected else "unresolved"
    elif final_answer_requested:
        revision_status = "unresolved"
    elif revision_status not in {"not_yet", "partial", "revised", "unresolved"}:
        revision_status = "revised" if proposed_state == "RESOLVED" else "not_yet"
    learner_progress = raw.get("learner_progress")
    if learner_progress not in {
        "not_assessed",
        "no_progress",
        "partial_progress",
        "clear_progress",
        "resolved",
    }:
        learner_progress = "resolved" if proposed_state == "RESOLVED" else "not_assessed"
    if corrective_feedback_delivered:
        learner_progress = "clear_progress" if resolution_self_corrected else "no_progress"
    elif final_answer_requested and learner_progress == "resolved":
        learner_progress = "partial_progress"
    elif off_topic_redirect or conversational_turn:
        learner_progress = "no_progress"
        revision_status = "not_yet"
        if conversational_turn:
            learner_progress = "not_assessed"
    disclosure_reason = raw.get("disclosure_reason")
    if not isinstance(disclosure_reason, str) or not disclosure_reason.strip():
        disclosure_reason = None

    primary_ebl_move = (
        "provide_corrective_resolution"
        if corrective_feedback_delivered
        else "request_final_answer" if final_answer_requested
        else "none" if conversational_turn
        else primary_reasoning_move(proposed_state)
    )

    return {
        "interaction_policy_version": INTERACTION_POLICY_VERSION,
        "condition_code": runtime.condition_code,
        "interaction_mode": "scaffold",
        "dialogue_state": proposed_state,
        "dialogue_move": expected_move,
        "primary_ebl_move": primary_ebl_move,
        "disclosure_level": resolved_disclosure_level,
        "allowed_disclosure_levels": list(runtime.allowed_disclosure_levels),
        "learner_progress": learner_progress,
        "disclosure_reason": disclosure_reason,
        "off_topic_redirect": off_topic_redirect,
        "attempts_in_state": attempts_in_state,
        "learner_revision_status": revision_status,
        "completion_status": completion_status,
        "resolution_outcome": resolution_outcome,
        "corrective_feedback_revealed_answer": corrective_feedback_delivered and answer_exposed,
        "next_target_started": next_target_started,
        "resolution_error_recognized": resolution_error_recognized,
        "resolution_error_reflected": resolution_error_reflected,
        "resolution_self_corrected": resolution_self_corrected,
        "resolution_criteria_met": resolution_criteria_met,
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
            "dialogue_move": DIALOGUE_MOVE_BY_STATE[EBL_INITIAL_STATE] if runtime.target else "resolution",
            "disclosure_level": "D0",
            "learner_revision_status": "not_yet" if runtime.target else "revised",
        }
    return enforce_interaction_response(runtime, raw, greeting)


def initial_greeting_metadata(condition: Any, task_attempt: Any, greeting: str) -> dict[str, Any]:
    """Return enforced first-turn metadata for compatibility callers."""
    return enforce_initial_greeting(condition, task_attempt, greeting).metadata
