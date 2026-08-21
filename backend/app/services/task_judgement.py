"""Normalize task judgement into a stable per-question error profile."""

from __future__ import annotations

from typing import Any


OBJECTIVE_QUESTION_TYPES = frozenset({"cloze", "multiple_choice", "true_false"})
QUESTION_CORRECTNESS_VALUES = frozenset({"correct", "partial", "incorrect", "unanswered"})


def _normalized_text(value: Any) -> str:
    return " ".join(str(value if value is not None else "").strip().lower().split())


def _answers_match(answer: Any, expected: Any) -> bool:
    if isinstance(expected, bool):
        if isinstance(answer, bool):
            return answer is expected
        normalized = _normalized_text(answer)
        return normalized in ({"true", "是"} if expected else {"false", "否"})
    if isinstance(expected, list):
        if isinstance(answer, list):
            actual_values = sorted(_normalized_text(item) for item in answer)
            expected_values = sorted(_normalized_text(item) for item in expected)
            return actual_values == expected_values
        return any(_normalized_text(answer) == _normalized_text(item) for item in expected)
    return _normalized_text(answer) == _normalized_text(expected)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return True


def _answer_by_question(response_payload: dict[str, Any]) -> dict[str, Any]:
    answers = response_payload.get("answers")
    if not isinstance(answers, list):
        return {}
    result: dict[str, Any] = {}
    for item in answers:
        if not isinstance(item, dict):
            continue
        question_id = item.get("question_id") or item.get("blank_id")
        if question_id:
            result[str(question_id)] = item.get("value")
    return result


def enrich_task_judgement(
    task: Any,
    response_payload: dict[str, Any],
    judgement: dict[str, Any],
) -> dict[str, Any]:
    """建立逐題診斷結果；客觀題用規則，簡答題採用 LLM 判定。"""
    evaluation_payload = getattr(task, "evaluation_payload", {})
    raw_questions = evaluation_payload.get("questions") if isinstance(evaluation_payload, dict) else []
    questions = [item for item in raw_questions or [] if isinstance(item, dict)]
    if not questions:
        provider_result = judgement.get("result")
        return {
            **{key: value for key, value in judgement.items() if key != "score"},
            "result": (
                str(provider_result)
                if provider_result in QUESTION_CORRECTNESS_VALUES
                else "incorrect"
            ),
            "question_results": [],
        }

    provider_results = judgement.get("question_results")
    provider_by_id = {
        str(item.get("question_id")): item
        for item in provider_results or []
        if isinstance(item, dict) and item.get("question_id")
    }
    answer_by_id = _answer_by_question(response_payload)
    legacy_answer = response_payload.get("answer_text") if len(questions) == 1 else None
    question_results: list[dict[str, Any]] = []

    for question in questions:
        question_id = str(question.get("id") or question.get("blank_id") or "")
        if not question_id:
            continue
        provider_result = provider_by_id.get(question_id, {})
        learner_answer = answer_by_id.get(question_id, legacy_answer)
        question_type = str(question.get("type") or "short_answer")
        expected_answer = question.get("correct_answer")
        if not _has_value(learner_answer):
            correctness = "unanswered"
        elif question_type in OBJECTIVE_QUESTION_TYPES:
            if expected_answer is None:
                raise ValueError(f"Objective question {question_id} has no correct_answer")
            correctness = "correct" if _answers_match(learner_answer, expected_answer) else "incorrect"
        else:
            provider_correctness = provider_result.get("correctness")
            if provider_correctness not in QUESTION_CORRECTNESS_VALUES - {"unanswered"}:
                raise ValueError(f"Open question {question_id} has no valid LLM judgement")
            correctness = str(provider_correctness)

        error_code = provider_result.get("error_code")
        if correctness == "correct":
            error_code = None
        elif not error_code:
            anticipated = question.get("anticipated_error_codes")
            if isinstance(anticipated, list) and anticipated:
                error_code = anticipated[0]
            elif correctness == "partial":
                error_code = "incomplete_reasoning"
            elif correctness == "unanswered":
                error_code = "unanswered"
            else:
                error_code = "unclassified"

        evidence_ids = provider_result.get("evidence_ids")
        if not isinstance(evidence_ids, list):
            evidence_ids = question.get("accepted_evidence_ids")
        if not isinstance(evidence_ids, list):
            evidence_ids = []

        question_results.append(
            {
                "question_id": question_id,
                "blank_id": str(question.get("blank_id") or question_id),
                "question_type": question_type,
                "prompt": str(question.get("prompt") or ""),
                "source_text": question.get("source_text"),
                "learner_answer": learner_answer,
                "correctness": correctness,
                "expected_answer": expected_answer,
                "error_code": str(error_code) if error_code else None,
                "evidence_ids": [str(item) for item in evidence_ids if item],
                "classifier_confidence": provider_result.get("classifier_confidence"),
            }
        )

    statuses = [item["correctness"] for item in question_results]
    if not statuses:
        provider_result = judgement.get("result")
        overall_result = (
            str(provider_result)
            if provider_result in QUESTION_CORRECTNESS_VALUES
            else "incorrect"
        )
    elif all(item == "correct" for item in statuses):
        overall_result = "correct"
    elif all(item == "unanswered" for item in statuses):
        overall_result = "unanswered"
    elif any(item in {"correct", "partial"} for item in statuses):
        overall_result = "partial"
    else:
        overall_result = "incorrect"

    return {
        **{key: value for key, value in judgement.items() if key != "score"},
        "result": overall_result,
        "question_results": question_results,
    }
