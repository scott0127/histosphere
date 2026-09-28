"""建立受測者可見副本，不改動後端保存的題目、判定與研究紀錄。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, TypeVar

from pydantic import BaseModel

from app.models.domain import ChatMessage, EventTask, TaskAttempt


T = TypeVar("T")
PUBLIC_QUESTION_FIELDS = {
    "id", "blank_id", "type", "prompt", "placeholder", "required",
}
PUBLIC_MATERIAL_FIELDS = {
    "id", "title", "text", "image_url", "image_alt", "caption",
}
PUBLIC_RESULT_FIELDS = {
    "question_id", "blank_id", "question_type", "question_text", "prompt",
    "learner_answer", "learner_rationale", "correctness", "answer_correct", "reasoning_correct",
}
PRIVATE_MESSAGE_FIELDS = {
    "prompt_preview", "disclosure_reason", "learning_focus",
    "expected_answer", "correct_answer", "source_text", "reasoning_criteria", "correct_interpretation",
    "answer_feedback",
    "answer_delivery",
    "judgement", "judgement_payload", "answer_review", "provider_fidelity_flags",
    "fidelity_flags", "persona_fidelity_flags", "content_validation_mode",
    "content_validation_would_retry", "content_validation_flags",
    "corrective_feedback_revealed_answer",
    "raw_interaction_metadata", "fidelity_retry_required", "fidelity_fallback_applied",
    "rejected_response_sha256", "rejected_response_length",
}


def _pick(payload: dict[str, Any], fields: set[str]) -> dict[str, Any]:
    return {key: deepcopy(value) for key, value in payload.items() if key in fields}


def learner_evaluation(payload: dict[str, Any]) -> dict[str, Any]:
    """僅提供受測者題文與素材，不傳送通過標準或正解。"""
    public = _pick(payload, {"contract_version", "question_count"})
    if isinstance(payload.get("questions"), list):
        questions = []
        for question in payload["questions"]:
            if not isinstance(question, dict):
                continue
            item = _pick(question, PUBLIC_QUESTION_FIELDS)
            if isinstance(question.get("options"), list):
                item["options"] = [
                    _pick(option, {"id", "value", "label"}) if isinstance(option, dict) else deepcopy(option)
                    for option in question["options"]
                ]
            questions.append(item)
        public["questions"] = questions
    if isinstance(payload.get("materials"), list):
        public["materials"] = [
            _pick(material, PUBLIC_MATERIAL_FIELDS)
            for material in payload["materials"]
            if isinstance(material, dict)
        ]
    return public


def learner_judgement(payload: dict[str, Any]) -> dict[str, Any]:
    """保留逐題對錯，不傳送內部診斷說明或預期答案。"""
    public = _pick(payload, {"contract_version", "result", "score"})
    if isinstance(payload.get("question_results"), list):
        public["question_results"] = [
            _pick(result, PUBLIC_RESULT_FIELDS)
            for result in payload["question_results"]
            if isinstance(result, dict)
        ]
    return public


def _message_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _message_metadata(item)
            for key, item in value.items()
            if key not in PRIVATE_MESSAGE_FIELDS
        }
    if isinstance(value, list):
        return [_message_metadata(item) for item in value]
    return deepcopy(value)


def learner_view(value: T) -> T:
    """遞迴複製回應並保留模型型別。

    僅在受測者路由輸出時使用，包含 Admin test 受測者視角。
    服務內部與管理員研究資料路由不得使用此過濾。
    """
    if isinstance(value, EventTask):
        # 保留相容欄位但清空舊故事；新版全文仍透過正式欄位提供。
        return value.model_copy(deep=True, update={
            "story_text": "",
            "evaluation_payload": learner_evaluation(value.evaluation_payload),
        })
    if isinstance(value, TaskAttempt):
        return value.model_copy(deep=True, update={
            "judgement_payload": learner_judgement(value.judgement_payload),
        })
    if isinstance(value, ChatMessage):
        return value.model_copy(deep=True, update={
            "metadata": _message_metadata(value.metadata),
        })
    if isinstance(value, BaseModel):
        return value.model_copy(update={
            name: (
                learner_judgement(getattr(value, name))
                if name == "judgement"
                else learner_view(getattr(value, name))
            )
            for name in type(value).model_fields
        })
    if isinstance(value, list):
        return [learner_view(item) for item in value]
    return deepcopy(value)
