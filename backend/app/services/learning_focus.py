"""告訴前端現在正在處理哪一題；沿用已存對話，不另外維護一份題目進度。"""

from collections.abc import Sequence

from app.core.interaction_contract import build_interaction_runtime
from app.models.domain import ChatMessage, ExperimentCondition, TaskAttempt
from app.schemas.responses import LearningFocus


def build_learning_focus(
    condition: ExperimentCondition | None,
    attempt: TaskAttempt | None,
    messages: Sequence[ChatMessage],
) -> LearningFocus | None:
    """僅接受後端持久化資料；保留待修正、待重述與未送達回覆的原題目。"""
    if not condition:
        return None

    runtime = build_interaction_runtime(condition, attempt, messages)
    target = runtime.target
    if target is None:
        # 現在沒有目標可能是「全部處理完」或「一開始就沒有錯誤」，畫面要能區分。
        had_target = (
            runtime.target_count > 0
            or build_interaction_runtime(condition, attempt, []).target is not None
        )
        return LearningFocus(status="completed" if had_target else "none")

    third_party = target.error_source == "researcher_authored_fallback"
    # 第三方練習只公開原始待判斷說法，不把它當成受測者答錯的題目。
    return LearningFocus(
        question_id=target.question_id,
        status="active",
        origin="third_party" if third_party else "learner",
        claim=target.learner_answer if third_party and isinstance(target.learner_answer, str) else None,
    )
