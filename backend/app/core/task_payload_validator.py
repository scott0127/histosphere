"""Validation for task story tokens and questions.

Admin 編輯與 LLM 自動生成共用同一份驗證規則，避免兩條資料流產生
不同的 task 格式後才在 Supabase 或 learner 頁面出錯。
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


INLINE_QUESTION_TYPES = {"cloze", "multiple_choice", "true_false"}
SUPPORTED_QUESTION_TYPES = INLINE_QUESTION_TYPES | {"short_answer"}
BLANK_PATTERN = re.compile(r"\{\{\s*blank:([a-zA-Z0-9_-]+)\s*\}\}")


def validate_task_authoring_payload(
    display_text: str,
    evaluation_payload: dict[str, Any] | Any,
) -> list[dict[str, str]]:
    """回傳 story-first task 的欄位級驗證問題。

    只有 ``evaluation_payload.questions`` 或 story token 已存在時才進入
    strict mode，讓既有舊資料仍可由研究員打開後逐步轉換。
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
    raw_questions = evaluation_payload.get("questions")
    token_ids = _blank_ids(display_text)
    structured_mode = "questions" in evaluation_payload or bool(token_ids)

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
    for index, question in enumerate(questions):
        _validate_question(index, question, token_ids, issues)

    return issues


def _blank_ids(display_text: str) -> list[str]:
    return [match.group(1) for match in BLANK_PATTERN.finditer(display_text or "")]


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
                    "display_text",
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
                    "display_text",
                    f"Story token '{blank_id}' does not map to any question.",
                    "orphan_blank_token",
                )
            )


def _validate_question(
    index: int,
    question: dict[str, Any],
    token_ids: list[str],
    issues: list[dict[str, str]],
) -> None:
    field = f"evaluation_payload.questions[{index}]"
    question_id = str(question.get("id") or "").strip()
    question_type = str(question.get("type") or "").strip()
    prompt = str(question.get("prompt") or "").strip()
    blank_id = _question_blank_id(question)

    if not question_id:
        issues.append(_issue(f"{field}.id", "Question id is required.", "missing_question_id"))
    if not prompt:
        issues.append(_issue(f"{field}.prompt", "Question prompt is required.", "missing_prompt"))
    if question_type not in SUPPORTED_QUESTION_TYPES:
        issues.append(
            _issue(
                f"{field}.type",
                f"Question type '{question_type or '<empty>'}' is not supported.",
                "unsupported_question_type",
            )
        )
        return

    if question_type in INLINE_QUESTION_TYPES and blank_id not in token_ids:
        issues.append(
            _issue(
                f"{field}.blank_id",
                f"Inline question '{question_id or blank_id}' is not inserted in display_text.",
                "question_missing_token",
            )
        )

    if question_type == "cloze":
        correct_answer = str(question.get("correct_answer") or "").strip()
        if not correct_answer:
            issues.append(
                _issue(
                    f"{field}.correct_answer",
                    f"Cloze question '{question_id or blank_id}' requires a correct_answer.",
                    "missing_correct_answer",
                )
            )
    elif question_type == "multiple_choice":
        _validate_multiple_choice(field, question, question_id, blank_id, issues)
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
        if not value_text:
            issues.append(
                _issue(
                    f"{field}.options[{option_index}].value",
                    "Option value is required.",
                    "missing_option_value",
                )
            )
        option_values.append(value_text)

    correct_answer = str(question.get("correct_answer") or "").strip()
    if correct_answer not in option_values:
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
