"""Operational Historical EBL scaffold policy.

This module is an implementation synthesis, not a claim that any cited paper
prescribes this exact state machine. The policy combines:

- error detection, correction, feedback, and reflection from Error-Based
  Learning research (Tirado-Olivares et al., 2023,
  https://doi.org/10.1057/s41599-023-01537-w);
- historical questions, sources, contextualization, and argumentation from the
  historical reasoning framework (van Drie & van Boxtel, 2008,
  https://doi.org/10.1007/s10648-007-9056-1);
- the project's advisor-reviewed sequence in which a learner's task errors
  become focused historical-thinking dialogue targets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


HISTORICAL_EBL_POLICY_VERSION: Final = "historical-ebl-scaffold-v1"
MAX_FOCUSED_QUESTIONS_PER_TURN: Final = 2


@dataclass(frozen=True)
class HistoricalEblMove:
    """One primary learner reasoning action for an EBL dialogue state."""

    dialogue_move: str
    primary_reasoning_move: str
    learner_action: str
    allowed_support: tuple[str, ...]


HISTORICAL_EBL_MOVES: Final[dict[str, HistoricalEblMove]] = {
    "ELICIT_REASONING": HistoricalEblMove(
        dialogue_move="reasoning_probe",
        primary_reasoning_move="make_initial_claim_and_reasoning_visible",
        learner_action="State the original claim and the reason used to reach it.",
        allowed_support=("neutral_restatement", "focused_prompt", "sentence_stem"),
    ),
    "INSPECT_EVIDENCE": HistoricalEblMove(
        dialogue_move="evidence_probe",
        primary_reasoning_move="inspect_source_or_task_evidence",
        learner_action="Identify one relevant clue and explain whether it supports or weakens the claim.",
        allowed_support=("evidence_pointer", "source_cue", "focused_contrast"),
    ),
    "CONTEXTUALIZE_OR_COMPARE": HistoricalEblMove(
        dialogue_move="context_or_comparison_probe",
        primary_reasoning_move="apply_target_historical_thinking_focus",
        learner_action=(
            "Use the target's relevant historical-thinking focus, such as causation, "
            "context, continuity/change, significance, or perspective."
        ),
        allowed_support=("context_cue", "comparison_frame", "timeline_or_perspective_cue"),
    ),
    "REVISE_CLAIM": HistoricalEblMove(
        dialogue_move="revision_prompt",
        primary_reasoning_move="revise_with_evidence_based_argumentation",
        learner_action="Rewrite the claim with a claim-evidence-reasoning connection.",
        allowed_support=("claim_evidence_reasoning_stem", "partial_structure", "revision_cue"),
    ),
    "REFLECT": HistoricalEblMove(
        dialogue_move="reflection_prompt",
        primary_reasoning_move="reflect_on_error_and_reasoning_change",
        learner_action="Compare the original and revised reasoning and identify what changed it.",
        allowed_support=("before_after_frame", "metacognitive_cue", "confidence_check"),
    ),
    "RESOLVED": HistoricalEblMove(
        dialogue_move="resolution",
        primary_reasoning_move="confirm_correction_and_transition",
        learner_action="Consolidate the corrected claim, then move to the next unresolved error if one exists.",
        allowed_support=("concise_feedback", "correct_answer_confirmation", "next_target_bridge"),
    ),
}


HISTORICAL_THINKING_ALIASES: Final[dict[str, str]] = {
    "significance": "historical_significance",
    "historical_significance": "historical_significance",
    "evidence": "evidence_and_source_use",
    "source": "evidence_and_source_use",
    "source_analysis": "evidence_and_source_use",
    "continuity": "continuity_and_change",
    "change": "continuity_and_change",
    "continuity_and_change": "continuity_and_change",
    "cause": "cause_and_consequence",
    "causation": "cause_and_consequence",
    "cause_and_consequence": "cause_and_consequence",
    "perspective": "historical_perspective",
    "historical_perspective": "historical_perspective",
    "ethical": "ethical_dimension",
    "ethical_dimension": "ethical_dimension",
    "context": "contextualization",
    "contextualization": "contextualization",
    "argumentation": "evidence_based_argumentation",
}


def historical_thinking_focus(
    historical_concept: str | None,
    reasoning_process: str | None,
) -> str:
    """沿用可用的舊資料；沒有預設向度時交由當回合模型選擇。"""

    for candidate in (historical_concept, reasoning_process):
        normalized = (candidate or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not normalized:
            continue
        if normalized in HISTORICAL_THINKING_ALIASES:
            return HISTORICAL_THINKING_ALIASES[normalized]
        for marker, resolved in HISTORICAL_THINKING_ALIASES.items():
            if marker in normalized:
                return resolved
    return "select_one_relevant_operation_from_current_error_and_dialogue"


def primary_reasoning_move(state: str) -> str:
    """Return the backend-owned reasoning move for a dialogue state."""

    policy = HISTORICAL_EBL_MOVES.get(state)
    return policy.primary_reasoning_move if policy else "standard_historical_conversation"
