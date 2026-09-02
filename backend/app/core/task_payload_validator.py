"""Validation for task story tokens and questions.

Admin 編輯與 LLM 自動生成共用同一份驗證規則，避免兩條資料流產生
不同的 task 格式後才在 Supabase 或 learner 頁面出錯。
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

from app.core.error_elicitation_contract import ERROR_ELICITATION_CONTRACT_VERSION


INLINE_QUESTION_TYPES = {"cloze", "multiple_choice", "true_false"}
SUPPORTED_QUESTION_TYPES = INLINE_QUESTION_TYPES | {"short_answer"}
BLANK_PATTERN = re.compile(r"\{\{\s*blank:([a-zA-Z0-9_-]+)\s*\}\}")


def validate_task_authoring_payload(
    error_elicitation_task_full_text: str,
    evaluation_payload: dict[str, Any] | Any,
) -> list[dict[str, str]]:
    """回傳 Task 的欄位級驗證問題。

    新版每題要求答案與理由通過標準；分批切換完成前不改變現行題目規則。
    """

    if not isinstance(evaluation_payload, dict):
        return [
            _issue(
                "evaluation_payload",
                "evaluation_payload must be an object.",
                "invalid_evaluation_payload",
            )
        ]

    issues: list[dict[str, str]] = []
    contract_version = evaluation_payload.get("contract_version")
    if "contract_version" in evaluation_payload and contract_version != ERROR_ELICITATION_CONTRACT_VERSION:
        return [_issue(
            "evaluation_payload.contract_version",
            "Unsupported task contract_version.",
            "unsupported_task_contract",
        )]
    error_elicitation = contract_version == ERROR_ELICITATION_CONTRACT_VERSION
    if error_elicitation:
        if not str(error_elicitation_task_full_text or "").strip():
            issues.append(_issue("error_elicitation_task_full_text", "Full task text is required.", "missing_full_text"))
        _validate_materials(evaluation_payload.get("materials", []), issues)
    raw_questions = evaluation_payload.get("questions")
    all_correct_fallback = evaluation_payload.get("all_correct_fallback")
    token_ids = _blank_ids(error_elicitation_task_full_text)
    structured_mode = (
        "questions" in evaluation_payload
        or bool(token_ids)
        or all_correct_fallback is not None
        or error_elicitation
    )

    if raw_questions is None and not structured_mode:
        return issues
    if raw_questions is None:
        raw_questions = []
    if not isinstance(raw_questions, list):
        return [
            _issue(
                "evaluation_payload.questions",
                "questions must be an array.",
                "invalid_questions",
            )
        ]

    questions = [question for question in raw_questions if isinstance(question, dict)]
    if len(questions) != len(raw_questions):
        issues.append(
            _issue(
                "evaluation_payload.questions",
                "Every question must be an object.",
                "invalid_question",
            )
        )
    if structured_mode and not questions:
        issues.append(
            _issue(
                "evaluation_payload.questions",
                "Structured task authoring requires at least one question.",
                "missing_questions",
            )
        )

    _validate_story_tokens(token_ids, questions, issues)
    if error_elicitation:
        # 每題理由靠 question_id 關聯，不能讓重複 id 覆蓋另一題的作答。
        ids = [str(question.get("id") or "").strip() for question in questions]
        if len(ids) != len(set(ids)):
            issues.append(_issue("evaluation_payload.questions", "Question ids must be unique.", "duplicate_question_id"))
    for index, question in enumerate(questions):
        _validate_question(index, question, token_ids, issues, error_elicitation=error_elicitation)
    _validate_all_correct_fallback(all_correct_fallback, issues)

    return issues


def _validate_all_correct_fallback(
    fallback: Any,
    issues: list[dict[str, str]],
) -> None:
    """可選素材只在全數答對時使用，且必須由研究者提供完整錯誤與正解。"""

    if fallback is None:
        return
    field = "evaluation_payload.all_correct_fallback"
    if not isinstance(fallback, dict):
        issues.append(_issue(field, "all_correct_fallback must be an object.", "invalid_all_correct_fallback"))
        return
    if not str(fallback.get("id") or "").strip():
        issues.append(_issue(f"{field}.id", "Fallback id is required.", "missing_fallback_id"))
    if not str(fallback.get("incorrect_claim") or "").strip():
        issues.append(
            _issue(
                f"{field}.incorrect_claim",
                "A researcher-authored incorrect claim is required.",
                "missing_fallback_incorrect_claim",
            )
        )
    if not str(fallback.get("correct_interpretation") or "").strip():
        issues.append(
            _issue(
                f"{field}.correct_interpretation",
                "A verified correct interpretation is required.",
                "missing_fallback_correct_interpretation",
            )
        )
    evidence_ids = fallback.get("evidence_ids")
    if evidence_ids is not None and not isinstance(evidence_ids, list):
        issues.append(
            _issue(
                f"{field}.evidence_ids",
                "evidence_ids must be an array.",
                "invalid_fallback_evidence_ids",
            )
        )


def _blank_ids(error_elicitation_task_full_text: str) -> list[str]:
    return [match.group(1) for match in BLANK_PATTERN.finditer(error_elicitation_task_full_text or "")]


def _validate_story_tokens(
    token_ids: list[str],
    questions: list[dict[str, Any]],
    issues: list[dict[str, str]],
) -> None:
    token_counts = Counter(token_ids)
    for blank_id, count in token_counts.items():
        if count > 1:
            issues.append(
                _issue(
                    "error_elicitation_task_full_text",
                    f"Story text contains duplicate blank token '{blank_id}'.",
                    "duplicate_blank_token",
                )
            )

    question_blank_ids = [_question_blank_id(question) for question in questions]
    question_blank_set = set(question_blank_ids)
    question_blank_counts = Counter(question_blank_ids)
    for blank_id, count in question_blank_counts.items():
        if blank_id and count > 1:
            issues.append(
                _issue(
                    "evaluation_payload.questions",
                    f"Question blank id '{blank_id}' is used by multiple questions.",
                    "duplicate_question_blank_id",
                )
            )

    for blank_id in token_ids:
        if blank_id not in question_blank_set:
            issues.append(
                _issue(
                    "error_elicitation_task_full_text",
                    f"Story token '{blank_id}' does not map to any question.",
                    "orphan_blank_token",
                )
            )


def _validate_question(
    index: int,
    question: dict[str, Any],
    token_ids: list[str],
    issues: list[dict[str, str]],
    *,
    error_elicitation: bool = False,
) -> None:
    field = f"evaluation_payload.questions[{index}]"
    question_id = str(question.get("id") or "").strip()
    question_type = str(question.get("type") or "").strip()
    prompt = str(question.get("prompt") or "").strip()
    blank_id = _question_blank_id(question)

    if not question_id:
        issues.append(_issue(f"{field}.id", "Question id is required.", "missing_question_id"))
    if not error_elicitation and not prompt:
        issues.append(_issue(f"{field}.prompt", "Question prompt is required.", "missing_prompt"))
    supported_types = INLINE_QUESTION_TYPES if error_elicitation else SUPPORTED_QUESTION_TYPES
    if question_type not in supported_types:
        issues.append(
            _issue(
                f"{field}.type",
                f"Question type '{question_type or '<empty>'}' is not supported.",
                "unsupported_question_type",
            )
        )
        return

    if error_elicitation:
        # 題目敘述只存在整份 full text；題號標記將作答區與判定標準連起來。
        if "prompt" in question:
            issues.append(_issue(f"{field}.prompt", "Write question statements in error_elicitation_task_full_text, not per-question prompt.", "duplicate_question_text"))
        if blank_id != question_id or question_id not in token_ids:
            issues.append(_issue(f"{field}.id", "Every question must have one matching {{blank:question_id}} in the full text.", "question_missing_token"))
        if not isinstance(question.get("id"), str) or question["id"] != question_id:
            issues.append(_issue(f"{field}.id", "Question id must be a string without surrounding whitespace.", "invalid_question_id"))
        criteria = question.get("reasoning_criteria")
        if not isinstance(criteria, str) or not criteria.strip():
            issues.append(_issue(
                f"{field}.reasoning_criteria",
                "Each question requires nonblank researcher-defined reasoning criteria.",
                "missing_reasoning_criteria",
            ))
        if question.get("required", True) is not True:
            issues.append(_issue(f"{field}.required", "Every question requires an answer and rationale.", "question_must_be_required"))

    # 新版每題有獨立答案與理由區，不再要求三種題型都插入故事 token。
    if not error_elicitation and question_type in INLINE_QUESTION_TYPES and blank_id not in token_ids:
        issues.append(
            _issue(
                f"{field}.blank_id",
                f"Inline question '{question_id or blank_id}' is not inserted in error_elicitation_task_full_text.",
                "question_missing_token",
            )
        )

    if question_type == "cloze":
        raw_answer = question.get("correct_answer")
        if error_elicitation:
            accepted_answers = raw_answer if isinstance(raw_answer, list) else [raw_answer]
            valid_answer = bool(accepted_answers) and all(
                isinstance(answer, str) and bool(answer.strip()) for answer in accepted_answers
            )
        else:
            valid_answer = bool(str(raw_answer or "").strip())
        if not valid_answer:
            issues.append(
                _issue(
                    f"{field}.correct_answer",
                    f"Cloze question '{question_id or blank_id}' requires a correct_answer.",
                    "missing_correct_answer",
                )
            )
    elif question_type == "multiple_choice":
        _validate_multiple_choice(field, question, question_id, blank_id, issues, strict_values=error_elicitation)
    elif question_type == "true_false" and not isinstance(question.get("correct_answer"), bool):
        issues.append(
            _issue(
                f"{field}.correct_answer",
                f"True/false question '{question_id or blank_id}' requires a boolean correct_answer.",
                "invalid_true_false_answer",
            )
        )


def _validate_multiple_choice(
    field: str,
    question: dict[str, Any],
    question_id: str,
    blank_id: str,
    issues: list[dict[str, str]],
    *,
    strict_values: bool = False,
) -> None:
    options = question.get("options")
    if not isinstance(options, list) or len(options) < 2:
        issues.append(
            _issue(
                f"{field}.options",
                f"Multiple-choice question '{question_id or blank_id}' requires at least two options.",
                "missing_options",
            )
        )
        return

    option_values: list[str] = []
    for option_index, option in enumerate(options):
        value = option.get("value") if isinstance(option, dict) else None
        value_text = str(value or "").strip()
        if not value_text or (strict_values and not isinstance(value, str)):
            issues.append(
                _issue(
                    f"{field}.options[{option_index}].value",
                    "Option value is required.",
                    "missing_option_value",
                )
            )
        option_values.append(value_text)

    if strict_values and len(option_values) != len(set(value.casefold() for value in option_values)):
        issues.append(_issue(f"{field}.options", "Option values must be distinct under answer normalization.", "duplicate_option_value"))
    correct_answer = str(question.get("correct_answer") or "").strip()
    if correct_answer not in option_values or (strict_values and not isinstance(question.get("correct_answer"), str)):
        issues.append(
            _issue(
                f"{field}.correct_answer",
                f"Multiple-choice question '{question_id or blank_id}' correct_answer must match an option value.",
                "answer_not_in_options",
            )
        )


def _question_blank_id(question: dict[str, Any]) -> str:
    return str(question.get("blank_id") or question.get("id") or "").strip()


def _issue(field: str, message: str, code: str) -> dict[str, str]:
    return {"field": field, "message": message, "code": code}


def _validate_materials(materials: Any, issues: list[dict[str, str]]) -> None:
    if not isinstance(materials, list):
        issues.append(_issue("evaluation_payload.materials", "Materials must be an array.", "invalid_materials"))
        return
    ids = set()
    for index, material in enumerate(materials):
        field = f"evaluation_payload.materials[{index}]"
        if not isinstance(material, dict):
            issues.append(_issue(field, "Material must be an object.", "invalid_material"))
            continue
        for key in ("id", "title"):
            if not isinstance(material.get(key), str) or not material[key].strip():
                issues.append(_issue(f"{field}.{key}", "Material id and title are required.", "invalid_material"))
        material_id = str(material.get("id") or "")
        if material_id in ids:
            issues.append(_issue(f"{field}.id", "Material ids must be unique.", "duplicate_material_id"))
        ids.add(material_id)
        if not isinstance(material.get("text", ""), str):
            issues.append(_issue(f"{field}.text", "Material text must be a string.", "invalid_material"))
        if material.get("caption") is not None and not isinstance(material["caption"], str):
            issues.append(_issue(f"{field}.caption", "Material caption must be a string.", "invalid_material"))
        if not str(material.get("text") or "").strip() and not material.get("image_url"):
            issues.append(_issue(field, "Material requires text or an image.", "empty_material"))
        for key in ("image_url", "source_url"):
            value = material.get(key)
            if not value:
                continue
            local_image = key == "image_url" and isinstance(value, str) and value.startswith("/images/") and ".." not in value
            parsed = urlparse(str(value))
            if not local_image and (parsed.scheme not in {"http", "https"} or not parsed.netloc):
                issues.append(_issue(f"{field}.{key}", "Use an http(s) URL or a local /images/ image path.", "invalid_material_url"))
