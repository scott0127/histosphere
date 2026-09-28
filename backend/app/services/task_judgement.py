"""把作答與 Judge 結果整理成後續對話可使用的逐題錯誤資料。

現行題組：選擇／是非的答案用規則判，填空答案與所有理由由 LLM 判。
舊格式活動仍走相容分支，不把新判準偷偷套回既有研究紀錄。
"""

from __future__ import annotations

from typing import Any
import re
import unicodedata

from app.core.error_elicitation_contract import (
    ERROR_ELICITATION_CONTRACT_VERSION,
    ERROR_ELICITATION_JUDGE_CONTRACT_VERSION,
    ErrorElicitationJudgementPayload,
    ErrorElicitationQuestionResult,
    validate_task_answers,
)


OBJECTIVE_QUESTION_TYPES = frozenset({"cloze", "multiple_choice", "true_false"})
QUESTION_CORRECTNESS_VALUES = frozenset({"correct", "partial", "incorrect", "unanswered"})


def _normalized_text(value: Any) -> str:
    return " ".join(
        unicodedata.normalize("NFKC", str(value if value is not None else ""))
        .strip().casefold().split()
    )


def _normalized_cloze_text(value: Any) -> str:
    # 舊格式填空比對才使用：忽略句尾句號，不刪掉答案內部的標點或文字。
    return _normalized_text(value).rstrip(" .。")


def _answers_match(answer: Any, expected: Any, *, question_type: str | None = None) -> bool:
    if isinstance(expected, bool):
        if isinstance(answer, bool):
            return answer is expected
        normalized = _normalized_text(answer)
        return normalized in ({"true", "是"} if expected else {"false", "否"})
    normalize = _normalized_cloze_text if question_type == "cloze" else _normalized_text
    if question_type == "cloze" and not normalize(answer):
        return False
    if isinstance(expected, list):
        if isinstance(answer, list):
            actual_values = sorted(normalize(item) for item in answer)
            expected_values = sorted(normalize(item) for item in expected)
            return actual_values == expected_values
        return any(normalize(answer) == normalize(item) for item in expected)
    return normalize(answer) == normalize(expected)


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


def _all_correct_fallback_snapshot(evaluation_payload: dict[str, Any]) -> dict[str, Any] | None:
    """凍結研究者預先核定的第三方錯誤，避免後續修改 Task 影響既有 session。"""

    raw = evaluation_payload.get("all_correct_fallback")
    if not isinstance(raw, dict):
        return None
    incorrect_claim = str(raw.get("incorrect_claim") or "").strip()
    correct_interpretation = str(raw.get("correct_interpretation") or "").strip()
    if not incorrect_claim or not correct_interpretation:
        return None
    evidence_ids = raw.get("evidence_ids")
    return {
        "id": str(raw.get("id") or "all-correct-fallback"),
        "incorrect_claim": incorrect_claim,
        "correct_interpretation": correct_interpretation,
        "source_text": raw.get("source_text"),
        "historical_concept": raw.get("historical_concept"),
        "reasoning_process": raw.get("reasoning_process"),
        "evidence_ids": (
            [str(item) for item in evidence_ids if item]
            if isinstance(evidence_ids, list)
            else []
        ),
    }


def enrich_task_judgement(
    task: Any,
    response_payload: dict[str, Any],
    judgement: dict[str, Any],
) -> dict[str, Any]:
    """依題組版本選擇整理方式；現行格式中，填空答案也使用 LLM 的判定。"""
    evaluation_payload = getattr(task, "evaluation_payload", {})
    if evaluation_payload.get("contract_version") == ERROR_ELICITATION_CONTRACT_VERSION:
        return _enrich_error_elicitation(task, response_payload, judgement)
    # 以下保留舊活動的 partial／unanswered 等語意，不是現行二分判定流程。
    raw_questions = evaluation_payload.get("questions") if isinstance(evaluation_payload, dict) else []
    questions = [item for item in raw_questions or [] if isinstance(item, dict)]
    all_correct_fallback = (
        _all_correct_fallback_snapshot(evaluation_payload)
        if isinstance(evaluation_payload, dict)
        else None
    )
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
            correctness = (
                "correct"
                if _answers_match(learner_answer, expected_answer, question_type=question_type)
                else "incorrect"
            )
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

    enriched = {
        **{key: value for key, value in judgement.items() if key != "score"},
        "result": overall_result,
        "question_results": question_results,
    }
    if all_correct_fallback:
        enriched["all_correct_fallback"] = all_correct_fallback
    return enriched


def _enrich_error_elicitation(task: Any, response: dict, judgement: dict) -> dict:
    """合併規則與模型判定；漏題或格式錯誤要報處理失敗，不能算成學生答錯。"""
    evaluation = task.evaluation_payload
    validate_task_answers(evaluation, response, complete=True)
    parsed = ErrorElicitationJudgementPayload.model_validate(
        {
            "judge_contract_version": judgement.get("judge_contract_version"),
            "question_results": judgement.get("question_results"),
        }
    )
    # 先核對題號完全一致，再逐題合併；不能靠位置配對，也不能默默漏掉某一題。
    reasoning = {result.question_id: result for result in parsed.question_results}
    questions = evaluation["questions"]
    if set(reasoning) != {question["id"] for question in questions}:
        raise ValueError("Judge must return exactly the questions in this task")
    answers = {answer["question_id"]: answer for answer in response["answers"]}
    # 只由完整題文抽取顯示片段，不接受前端自填的題目文字或評分標準。
    text_by_id = {}
    previous_end = 0
    for match in re.finditer(
        r"\{\{\s*blank:([a-zA-Z0-9_-]+)\s*\}\}", task.error_elicitation_task_full_text
    ):
        text_by_id[match.group(1)] = (
            task.error_elicitation_task_full_text[previous_end:match.start()].strip()
        )
        previous_end = match.end()
    results = []
    for question in questions:
        qid = question["id"]
        answer = answers[qid]
        rationale = reasoning[qid]
        if question["type"] == "cloze":
            # 填空可有合理同義說法，不能再用字串相等覆蓋 LLM 的答案判定。
            if rationale.answer_correct is None or not rationale.answer_feedback:
                raise ValueError(f"{qid}: cloze answer judgement and feedback are required")
            answer_correct = rationale.answer_correct
            answer_feedback = rationale.answer_feedback
        else:
            # 選擇與是非仍由後端核對，LLM 不能改寫這兩種題目的答案對錯。
            answer_correct = _answers_match(answer["value"], question["correct_answer"])
            answer_feedback = None
        # 答案與理由都正確才算通過；歷史思考標籤只做描述，不參與這個判斷。
        result = ErrorElicitationQuestionResult(
            **rationale.model_dump(exclude={"answer_correct", "answer_feedback"}),
            answer_correct=answer_correct,
            answer_feedback=answer_feedback,
            correctness="correct" if answer_correct and rationale.reasoning_correct else "incorrect",
        )
        # 留下判題當時的題目、標準與作答，後續 AI 才能針對原本的錯誤引導。
        results.append(
            {
                **result.model_dump(),
                "blank_id": qid,
                "question_type": question["type"],
                "question_text": text_by_id.get(qid, ""),
                "options": question.get("options", []),
                "learner_answer": answer["value"],
                "learner_rationale": answer["rationale"],
                "expected_answer": question["correct_answer"],
                "reasoning_criteria": question["reasoning_criteria"],
                "source_text": question.get("source_text"),
                "evidence_ids": question.get("accepted_evidence_ids", []),
            }
        )
    enriched = {
        **{key: value for key, value in judgement.items() if key not in {"score", "question_results"}},
        "contract_version": ERROR_ELICITATION_CONTRACT_VERSION,
        "judge_contract_version": ERROR_ELICITATION_JUDGE_CONTRACT_VERSION,
        "error_elicitation_task_full_text": task.error_elicitation_task_full_text,
        "materials": evaluation.get("materials", []),
        "result": "correct" if all(result["correctness"] == "correct" for result in results) else "incorrect",
        "question_results": results,
    }
    fallback = _all_correct_fallback_snapshot(evaluation)
    if fallback:
        enriched["all_correct_fallback"] = fallback
    return enriched
