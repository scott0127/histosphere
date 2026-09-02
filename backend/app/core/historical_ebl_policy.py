"""歷史情境中的 EBL 互動政策。

依使用者確認的設計，02／04 額外引導認知錯誤、分析／反思、自我修正與回饋。
Historical Thinking 是四組 AI 共用的歷史回應品質基礎，不在此指定 learner 技能。
這是專案的操作化流程，不宣稱文獻直接提出此狀態機。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


HISTORICAL_EBL_POLICY_VERSION: Final = "ebl-error-reflection-v2"
MAX_FOCUSED_QUESTIONS_PER_TURN: Final = 2


@dataclass(frozen=True)
class HistoricalEblMove:
    """每個 EBL 狀態主要促發的學習行為，不是 Historical Thinking 技能清單。"""

    dialogue_move: str
    primary_reasoning_move: str
    learner_action: str
    allowed_support: tuple[str, ...]


HISTORICAL_EBL_MOVES: Final[dict[str, HistoricalEblMove]] = {
    "NOTICE_ERROR": HistoricalEblMove(
        dialogue_move="error_awareness_prompt",
        primary_reasoning_move="recognize_the_current_error",
        learner_action=(
            "Revisit the submitted answer and rationale and recognize which part may need correction. "
            "Use the rationale already supplied; do not demand that the learner repeat it verbatim."
        ),
        allowed_support=("neutral_restatement", "focused_prompt", "sentence_stem"),
    ),
    "REFLECT": HistoricalEblMove(
        dialogue_move="reflection_prompt",
        primary_reasoning_move="analyze_and_reflect_on_the_error",
        learner_action="Explain what went wrong in the original answer or reasoning and why it needs changing.",
        allowed_support=("focused_hint", "reflection_cue", "sentence_stem"),
    ),
    "SELF_CORRECT": HistoricalEblMove(
        dialogue_move="self_correction_prompt",
        primary_reasoning_move="reattempt_and_self_correct",
        learner_action="Try again by revising the mistaken answer or rationale in the learner's own words.",
        allowed_support=("revision_cue", "partial_structure", "focused_hint"),
    ),
    "RESOLVED": HistoricalEblMove(
        dialogue_move="resolution",
        primary_reasoning_move="confirm_correction_and_transition",
        learner_action="Consolidate the corrected claim, then move to the next unresolved error if one exists.",
        allowed_support=("concise_feedback", "correct_answer_confirmation", "next_target_bridge"),
    ),
}


def primary_reasoning_move(state: str) -> str:
    """回傳 EBL 行為；不是替學習者指定歷史思考操作。"""

    policy = HISTORICAL_EBL_MOVES.get(state)
    return policy.primary_reasoning_move if policy else "standard_historical_conversation"
