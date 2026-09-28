"""Backend-owned interaction contract for the fixed 2x2 experiment."""

from __future__ import annotations

import hashlib
import json
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

INTERACTION_POLICY_VERSION = "2x2-interaction-v17-shared-question-progress"
COMPATIBLE_INTERACTION_POLICY_VERSIONS = {
    INTERACTION_POLICY_VERSION,
    "2x2-interaction-v16-reviewed-transition",
    "2x2-interaction-v15-feedback-restatement",
    "2x2-interaction-v14-answer-observation",
    "2x2-interaction-v13-semantic-observation",
    "2x2-interaction-v12-disclosure-audit",
    "2x2-interaction-v11-answer-boundary",
    "2x2-interaction-v10-persona-led",
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
# 史實、比較與理由線索可以充分提供；界線是不要替受測者宣告作答結論。
DISCLOSURE_POLICY = {
    "D0": {
        "allowed": (
            "Engage the learner's claim and invite independent reconsideration. Acknowledge any rationale already "
            "submitted instead of asking the learner to repeat it. Develop the historical situation and your reaction; "
            "begin with an open invitation rather than a worked correction."
        ),
        "hard_ceiling": (
            "Do not announce the correct option, fill-in, truth value, or corrected task conclusion for the learner."
        ),
    },
    "D1": {
        "allowed": (
            "Point out a doubt, direction, or distinction worth reconsidering in the current claim. "
            "Ground that doubt in relevant historical facts, the person's concerns, or a concrete contrast."
        ),
        "hard_ceiling": (
            "Do not announce the correct option, fill-in, truth value, or corrected task conclusion for the learner."
        ),
    },
    "D2": {
        "allowed": (
            "Offer useful facts and explain their relationships or implications. Comparisons may include both sides. "
            "Make the historical issue understandable, then invite the learner's own revised judgment."
        ),
        "hard_ceiling": (
            "Do not announce the correct option, fill-in, truth value, or corrected task conclusion for the learner."
        ),
    },
    "D3": {
        "allowed": (
            "Connect information already offered, highlight a tension, or break the difficulty into manageable parts. "
            "Explain the reasoning route explicitly if helpful, while leaving the final task judgment to the learner."
        ),
        "hard_ceiling": (
            "Do not announce the correct option, fill-in, truth value, or corrected task conclusion for the learner."
        ),
    },
    "D4": {
        "allowed": (
            "Offer the strongest support: organize what is known, clarify what remains unresolved, and make a final "
            "independent answer and rationale attempt possible. Follow the runtime's feedback-then-restatement sequence."
        ),
        "hard_ceiling": (
            "Do not provide the complete correction before runtime-authorized feedback or demonstrated self-correction. "
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
        "incomplete_resolution_criteria",
        "invalid_completion_status",
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
    answer_feedback: str | None = None
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
    def restatement_required(self) -> bool:
        """已提供修正回饋，等待 learner 用自己的話重述一次。"""
        return bool(self.interaction_mode == "scaffold" and self.target is not None
                    and self.previous_completion_status == "corrective_resolution_pending")

    @property
    def corrective_feedback_required(self) -> bool:
        """D4 支持後給正解及理由，再要求一次重述；舊 final_answer_pending 也走此順序。"""

        return bool(
            self.interaction_mode == "scaffold"
            and self.target is not None
            and (self.previous_completion_status == "final_answer_pending"
                 or (self.previous_disclosure_level == "D4" and self.previous_completion_status == "continue"))
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
            "answer_feedback": target.answer_feedback if target else None,
            "reasoning_criteria": target.reasoning_criteria if target else None,
        }
        shared = (
            f"Policy version: {INTERACTION_POLICY_VERSION}\n"
            f"EBL policy version: {HISTORICAL_EBL_POLICY_VERSION}\n"
            f"Interaction mode: {self.interaction_mode}\n"
            f"Current target position: {self.target_sequence_number or 0}/{self.target_count}\n"
            f"Current target: {json.dumps(target_payload, ensure_ascii=False)}\n"
            "Private evaluation context: task_source_text, expected_answer, reasoning_criteria, reasoning_feedback, answer_feedback, "
            "and evidence_ids are private references for assessing progress and selecting appropriate help. "
            "Knowing these references alone does not authorize an unsolicited task-answer summary; follow the "
            "interaction mode. Standard Chat may answer the learner's actual question directly. During EBL "
            "scaffolding, follow the selected Disclosure level and authorized terminal feedback. "
            "If error_source=researcher_authored_fallback, this is another person's claim, not a learner mistake."
        )
        if target and target.reasoning_correct is not None:
            shared += (
                "\nThe submitted learner_rationale is the learner's original wording, not an inferred belief. "
                "An item is correct only when answer_correct and reasoning_correct are both true. "
                "When the answer is right but the reasoning is not, focus on the reasoning gap; do not describe "
                "the answer itself as wrong. Use answer_feedback for a cloze answer mismatch and reasoning_feedback for "
                "a reasoning gap to locate the concrete factual or inferential "
                "deficiency, but do not quote it to the learner or disclose more than the current Disclosure level. "
                "An inadequate rationale is not automatically proof of a factual misconception. Historical Thinking "
                "tags describe what the rationale engages and are not a score or an instruction to teach that label. "
                "Do not invent a misconception or attribute an unstated belief to the learner. These distinctions do not change the dialogue "
                "states, Disclosure progression, or formal RESOLVED criteria."
            )
        if self.interaction_mode == "standard_chat":
            next_target = (
                {"question_id": self.next_target.question_id, "prompt": self.next_target.prompt,
                 "learner_answer": self.next_target.learner_answer,
                 "learner_rationale": self.next_target.learner_rationale}
                if self.next_target else None
            )
            return (
                f"{shared}\n"
                "Required behavior: conduct a natural historical conversation. Answer the learner's actual request and "
                "ask a clarification or follow-up when useful. Do not force a correction, Socratic sequence, evidence "
                "exercise, revision, or reflection. The current question and completion tracking are shared workflow, "
                "not EBL scaffolding. Discuss this item's historical claim and the learner's original reason naturally; "
                "do not withhold an answer or use graduated hints. Related historical questions may be answered without "
                "forcing the conversation back on every turn.\n"
                "Privately assess the learner's own statements using the same completion criteria in all conditions: "
                "(1) resolution_error_recognized: recognizes what in the original answer or rationale needs changing; "
                "(2) resolution_error_reflected: explains why; (3) resolution_self_corrected: supplies a revised answer "
                "AND rationale satisfying the current question's existing criteria. Evidence can accumulate across "
                "learner turns on this question. A sound revised explanation may demonstrate recognition and reflection "
                "without literally saying 'I was wrong'. Do not add a citation, named skill or extra task requirement. "
                "A bare option, 'I understand', agreement, a request to move on, or an AI-authored correction alone does "
                "not establish learner correction. Do not use a reply about another question to resolve this one. "
                "This records correction demonstrated in dialogue, not proof of independent mastery.\n"
                "Keep dialogue_state=STANDARD_CHAT, dialogue_move=natural_response and disclosure_level=null. "
                "Set completion_status=resolved and learner_progress=resolved only when a current target exists and "
                "all three criteria are demonstrated. Otherwise keep completion_status=continue and report the "
                "actual learner progress; use not_assessed before any learner reply or when no target exists. "
                "Opening turns and off-topic redirects must set all three resolution_* fields=false. "
                "When resolved, briefly acknowledge the corrected idea and introduce the next target's historical "
                "issue naturally in the same reply. Do not reopen completed errors or dump the next answer unasked. "
                "If no target remains, continue event discussion until the timer ends; do not invent errors or "
                "claim that the timed activity has ended. Do not announce internal completion criteria to the learner.\n"
                f"Next target (only after closing this one): {json.dumps(next_target, ensure_ascii=False)}"
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
                "D4 support has been used. If the learner has already met all three self-correction criteria, resolve "
                "normally and confirm the answer without another restatement. Otherwise, now state the verified "
                "expected_answer clearly and briefly explain the corrected "
                "interpretation using the current question's criteria and materials. If the answer was already "
                "right but its rationale was wrong, confirm the answer and correct the rationale. Do not just "
                "acknowledge an incorrect answer. AFTER this feedback, invite the learner to explain once in their own "
                "words how the original answer or reason should change. Stay on this target; do not bridge yet. "
                "Use dialogue_state=SELF_CORRECT, dialogue_move=corrective_feedback, disclosure_level=D4, "
                "completion_status=corrective_resolution_pending. This is assisted correction, not independent mastery."
            )
        elif self.restatement_required:
            terminal_instruction = (
                "The verified correction has already been given and a restatement requested. The learner has now had "
                "one opportunity to restate it. Acknowledge a sound restatement; if it remains wrong, incomplete or "
                "off-topic, briefly reiterate the verified correction without endorsing the error. Then bridge to the "
                "next target, without giving its answer. Do not demand repeated perfection or another restatement. "
                "Use RESOLVED/corrective_feedback/feedback_completed. Record assisted completion, not independent mastery."
            )
        else:
            terminal_instruction = (
                "Before authorized corrective feedback, withhold the correct answer unless the learner has already "
                "self-corrected and met the EBL resolution criteria. Do not request assisted closure early."
            )
        transition_instruction = (
            "\nWhen an authorized closure has a next target, introduce that specific target's historical issue "
            "or original learner claim so the learner knows what is now being discussed. Use natural wording; "
            "no fixed connector or question-number formula is required. A vague promise "
            "to continue later or an invitation to reconsider the same question is not a transition.\n"
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
            "solution-assistance ceiling still applies. Opening, restatement and corrective-feedback turns "
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
                "Facts, comparisons and reasoning cues are allowed even when they make the answer easier to infer. "
                "Levels guide how explicit the support is, not a fact quota or a ban on useful historical explanation. "
                "Before authorized feedback, do not announce the correct option, fill-in, truth value or final task "
                "conclusion, including a paraphrase or a rhetorical question that already asserts that conclusion. "
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
                f"{terminal_instruction}{transition_instruction}{persona_turn_policy}"
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
            "at every level. Facts, comparisons and reasoning cues may make the answer easy to infer; that alone is not "
            "answer disclosure. Levels guide assistance, not a fact quota; do not mechanically count facts. "
            "Materials are not an exhaustive historical-knowledge whitelist. "
            "Use only reliable historical knowledge consistent with the active identity's time and access. A quotation or a "
            "claimed source still needs support. Before authorized feedback, do not announce the correct option, fill-in, "
            "truth value or corrected task conclusion, including its paraphrase or a rhetorical question that asserts it. "
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
            "another failed scaffold attempt. Exception: during authorized closure, continue the verified "
            "feedback even if that reply is off topic, without answering the unrelated request. "
            "When evidence_ids is empty, do not invent a source ID, quotation, or retrieval claim. Reliable contextual "
            "knowledge remains available under the same solution-assistance and identity boundaries.\n"
            f"{terminal_instruction}{transition_instruction}{persona_turn_policy}"
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
        if metadata.get("answer_delivery", {}).get("state_held"):
            continue
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
        if metadata.get("answer_delivery", {}).get("state_held"):
            continue
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
        answer_feedback=result.get("answer_feedback"),
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
    target = select_interaction_target(task_attempt, messages)
    next_target, target_sequence_number, target_count = _target_queue_context(task_attempt, messages, target)
    previous_metadata = _last_interaction_metadata(messages)
    if interaction_mode == "standard_chat":
        return InteractionRuntime(
            condition_code=condition_code_for_key(condition.condition_key),
            condition_key=condition.condition_key,
            interaction_mode=interaction_mode,
            roleplay_enabled=condition.roleplay_enabled,
            target=target,
            next_target=next_target,
            target_sequence_number=target_sequence_number,
            target_count=target_count,
            previous_state="STANDARD_CHAT" if previous_metadata else None,
            allowed_states=("STANDARD_CHAT",),
            previous_disclosure_level=None,
            previous_attempts_in_state=0,
            previous_completion_status=None,
        )

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
    elif previous_completion_status == "corrective_resolution_pending":
        allowed_states = ("RESOLVED",)
    elif previous_completion_status == "final_answer_pending" or previous_disclosure_level == "D4":
        allowed_states = ("SELF_CORRECT", "RESOLVED")
    elif previous_state:
        allowed_states = EBL_STATE_TRANSITIONS[previous_state]
    elif messages:
        # 已換到新題且 learner 已回覆時，可直接展現完整修正，不強迫多聊開場一輪。
        allowed_states = EBL_STATE_TRANSITIONS[EBL_INITIAL_STATE]
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


def resolve_interaction_metadata(
    runtime: InteractionRuntime,
    provider_metadata: dict[str, Any] | None,
    response_text: str,
    *,
    is_opening: bool = False,
) -> dict[str, Any]:
    """Validate model-proposed metadata against the backend-owned condition contract."""
    raw = dict(provider_metadata) if isinstance(provider_metadata, dict) else {}
    if is_opening:
        # AI 開場尚無 learner 修正證據；即使模型自報成功也不能產生完成紀錄。
        raw.update(resolution_error_recognized=False, resolution_error_reflected=False,
                   resolution_self_corrected=False, learner_progress="not_assessed",
                   completion_status="continue")
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
        # 四組共用完成判準；一般對話只追蹤題目，不啟用 EBL 狀態或提示階梯。
        may_assess = runtime.target is not None and not is_opening and not off_topic_redirect
        criteria = {
            key: may_assess and raw.get(key) is True
            for key in ("resolution_error_recognized", "resolution_error_reflected", "resolution_self_corrected")
        }
        resolved = all(criteria.values())
        if may_assess and raw.get("completion_status") in {"resolved", "complete"} and not resolved:
            flags.add("incomplete_resolution_criteria")
        progress = raw.get("learner_progress")
        if not may_assess:
            progress = "not_assessed"
        elif resolved:
            progress = "resolved"
        elif progress not in {"not_assessed", "no_progress", "partial_progress", "clear_progress"}:
            progress = "partial_progress" if any(criteria.values()) else "no_progress"
        return {
            "interaction_policy_version": INTERACTION_POLICY_VERSION,
            "condition_code": runtime.condition_code,
            "interaction_mode": "standard_chat",
            "dialogue_state": "STANDARD_CHAT",
            "dialogue_move": "natural_response",
            "primary_ebl_move": "none",
            "disclosure_level": None,
            "allowed_disclosure_levels": [],
            "attempts_in_state": 0,
            "learner_revision_status": (
                "revised" if resolved else "not_applicable" if runtime.target is None
                else "partial" if any(criteria.values()) else "not_yet"
            ),
            "completion_status": "resolved" if resolved else "continue",
            "learner_progress": progress,
            "disclosure_reason": None,
            "off_topic_redirect": off_topic_redirect,
            **criteria,
            "resolution_criteria_met": resolved,
            "resolution_outcome": "learner_resolved" if resolved else "in_progress" if runtime.target else "no_target",
            "next_target_transition_required": bool(resolved and runtime.next_target),
            "next_target_started": False,
            "fidelity_flags": sorted(flags),
            "provider_fidelity_flags": provider_flags,
            **target_metadata,
        }

    independently_corrected = bool(
        raw.get("dialogue_state") == "RESOLVED" and not off_topic_redirect
        and all(raw.get(key) is True for key in (
            "resolution_error_recognized", "resolution_error_reflected", "resolution_self_corrected"))
    )
    corrective_feedback_delivered = runtime.corrective_feedback_required and not independently_corrected
    restatement_completed = runtime.restatement_required
    # 人物可回答相關歷史問題；此回合不是 EBL 失敗，也不是離題。
    conversational_turn = bool(
        runtime.roleplay_enabled and runtime.target is not None
        and runtime.previous_state is not None
        and not restatement_completed and not corrective_feedback_delivered
        and not off_topic_redirect and raw.get("dialogue_move") == "natural_response"
    )
    proposed_state = raw.get("dialogue_state")
    if corrective_feedback_delivered or restatement_completed:
        # 先給正解並等待一次重述；重述後才轉題，不以提示後回答宣稱獨立學會。
        off_topic_redirect = False
        proposed_state = "RESOLVED" if restatement_completed else "SELF_CORRECT"
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
    if off_topic_redirect or conversational_turn or corrective_feedback_delivered or restatement_completed:
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
    if (
        runtime.target is not None and proposed_state == "RESOLVED"
        and not resolution_criteria_met and not restatement_completed
    ):
        flags.add("incomplete_resolution_criteria")
        # 只修正無效狀態，不改寫文字；不能用完成宣告跳過尚未修正的錯誤。
        proposed_state = (
            runtime.previous_state
            if runtime.previous_state in runtime.allowed_states and runtime.previous_state != "RESOLVED"
            else EBL_INITIAL_STATE
        )
    expected_move = (
        "corrective_feedback" if corrective_feedback_delivered or restatement_completed
        else "natural_response" if conversational_turn
        else DIALOGUE_MOVE_BY_STATE[proposed_state]
    )
    allowed_provider_moves = {expected_move} if (
        corrective_feedback_delivered or restatement_completed
    ) else {None, expected_move}
    if not off_topic_redirect and raw.get("dialogue_move") not in allowed_provider_moves:
        flags.add("invalid_dialogue_move")
    question_count = response_text.count("？") + response_text.count("?")
    if question_count > MAX_FOCUSED_QUESTIONS_PER_TURN:
        flags.add("excessive_scaffold_questions")
    # 04 人物表達驗收暫不設字數門檻；之後另行檢討正式 2x2 篇幅控制。
    if not runtime.roleplay_enabled and len(response_text) > 700:
        flags.add("overlong_scaffold_response")
    if restatement_completed or corrective_feedback_delivered:
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
    same_state = proposed_state == runtime.previous_state
    attempts_in_state = (
        runtime.previous_attempts_in_state
        if off_topic_redirect or conversational_turn
        else runtime.previous_attempts_in_state + 1 if same_state else 0
    )
    if restatement_completed:
        # 表示已給回饋，不代表 learner 看完之後已學會或自行修正成功。
        completion_status = "feedback_completed"
        resolution_outcome = "assisted_restatement_completed"
    elif corrective_feedback_delivered:
        completion_status = "corrective_resolution_pending"
        resolution_outcome = "awaiting_restatement"
    elif proposed_state == "RESOLVED":
        completion_status = "resolved"
        resolution_outcome = "learner_resolved" if runtime.target else "no_target"
    else:
        completion_status = "continue"
        resolution_outcome = "in_progress"
    if not off_topic_redirect and raw.get("completion_status") not in {None, completion_status}:
        flags.add("invalid_completion_status")
    next_target_transition_required = bool(
        runtime.next_target
        and (restatement_completed or completion_status == "resolved")
    )
    revision_status = raw.get("learner_revision_status")
    if corrective_feedback_delivered or restatement_completed:
        revision_status = "unresolved"
    elif revision_status not in {"not_yet", "partial", "revised", "unresolved"}:
        revision_status = "revised" if proposed_state == "RESOLVED" else "not_yet"
    if "incomplete_resolution_criteria" in flags:
        revision_status = "partial" if resolution_self_corrected else "not_yet"
    learner_progress = raw.get("learner_progress")
    if learner_progress not in {
        "not_assessed",
        "no_progress",
        "partial_progress",
        "clear_progress",
        "resolved",
    }:
        learner_progress = "resolved" if proposed_state == "RESOLVED" else "not_assessed"
    if corrective_feedback_delivered or restatement_completed:
        learner_progress = "not_assessed"
    elif off_topic_redirect or conversational_turn:
        learner_progress = "no_progress"
        revision_status = "not_yet"
        if conversational_turn:
            learner_progress = "not_assessed"
    disclosure_reason = raw.get("disclosure_reason")
    if "incomplete_resolution_criteria" in flags and learner_progress == "resolved":
        learner_progress = "partial_progress"
    if not isinstance(disclosure_reason, str) or not disclosure_reason.strip():
        disclosure_reason = None

    primary_ebl_move = (
        "provide_corrective_resolution"
        if corrective_feedback_delivered
        else "acknowledge_assisted_restatement" if restatement_completed
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
        # 舊欄位保留相容；未有獨立語意判定時不可宣稱已確認答案有無揭露。
        "corrective_feedback_revealed_answer": None if corrective_feedback_delivered else False,
        "next_target_transition_required": next_target_transition_required,
        # 前題完成不等於已把下一題說清楚；送出前的獨立語意審查才可確認後者。
        # 未啟用審查時，下輪仍選取下一題，但以新題開場，不假設學習者已收到銜接。
        "next_target_started": False,
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
    *,
    is_opening: bool = False,
) -> EnforcedInteractionResponse:
    """Validate a candidate and require regeneration instead of writing visible fallback prose."""
    metadata = resolve_interaction_metadata(runtime, provider_metadata, response_text, is_opening=is_opening)
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
