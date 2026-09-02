from types import SimpleNamespace

import pytest

from app.models.domain import EventTask
from app.providers.llm.structured import QuestionJudgementPayload
from app.services.task_judgement import enrich_task_judgement


def test_enrich_task_judgement_builds_stable_question_results():
    task = EventTask(
        event_id="event-1",
        title="Task",
        story_text="Story",
        display_text="{{blank:q01}} / {{blank:q02}}",
        evaluation_payload={
            "questions": [
                {
                    "id": "q01",
                    "type": "cloze",
                    "prompt": "核心原因是什麼？",
                    "correct_answer": "財政危機",
                    "historical_concept": "cause_and_consequence",
                    "reasoning_processes": ["argumentation"],
                    "accepted_evidence_ids": ["E01"],
                },
                {
                    "id": "q02",
                    "type": "true_false",
                    "prompt": "革命後衝突立刻消失。",
                    "correct_answer": False,
                },
            ]
        },
    )
    result = enrich_task_judgement(
        task,
        {
            "answers": [
                {"question_id": "q01", "value": "糧食危機"},
                {"question_id": "q02", "value": False},
            ]
        },
        {
            "result": "partial",
            "misconception_summary": "一題錯誤",
            "feedback": "請修正",
        },
    )

    q01, q02 = result["question_results"]
    assert q01["learner_answer"] == "糧食危機"
    assert q01["correctness"] == "incorrect"
    assert q01["error_code"] == "unclassified"
    assert "historical_concept" not in q01
    assert "reasoning_process" not in q01
    assert q01["evidence_ids"] == ["E01"]
    assert q02["correctness"] == "correct"
    assert q02["error_code"] is None


def test_enrich_task_judgement_supports_single_question_legacy_answer_text():
    task = EventTask(
        event_id="event-1",
        title="Task",
        story_text="Story",
        display_text="{{blank:q01}}",
        evaluation_payload={
            "questions": [
                {
                    "id": "q01",
                    "type": "cloze",
                    "prompt": "核心原因是什麼？",
                    "correct_answer": "原因",
                }
            ]
        },
    )
    result = enrich_task_judgement(
        task,
        {"answer_text": "錯誤答案"},
        {"result": "incorrect", "misconception_summary": "錯誤", "feedback": "修正"},
    )

    assert result["question_results"][0]["learner_answer"] == "錯誤答案"
    assert result["question_results"][0]["correctness"] == "incorrect"


def test_open_question_uses_llm_judgement_even_with_reference_answer():
    task = EventTask(
        event_id="event-1",
        title="Task",
        story_text="Story",
        display_text="Story",
        evaluation_payload={
            "questions": [
                {
                    "id": "q01",
                    "type": "short_answer",
                    "prompt": "請解釋革命的兩項原因。",
                    "correct_answer": "財政危機與代表權衝突",
                }
            ]
        },
    )

    result = enrich_task_judgement(
        task,
        {"answers": [{"question_id": "q01", "value": "財政危機"}]},
        {
            "result": "partial",
            "misconception_summary": "只提出一項原因",
            "feedback": "已保存回答",
            "score": 0.5,
            "question_results": [
                {
                    "question_id": "q01",
                    "correctness": "partial",
                    "error_code": "incomplete_reasoning",
                    "historical_concept": "cause_and_consequence",
                }
            ],
        },
    )

    question = result["question_results"][0]
    assert question["correctness"] == "partial"
    assert question["error_code"] == "incomplete_reasoning"
    assert "historical_concept" not in question
    assert "score" not in result


def test_answered_open_question_requires_a_valid_llm_judgement():
    task = EventTask(
        event_id="event-1",
        title="Task",
        story_text="Story",
        display_text="Story",
        evaluation_payload={
            "questions": [
                {
                    "id": "q01",
                    "type": "short_answer",
                    "prompt": "請解釋事件原因。",
                }
            ]
        },
    )

    with pytest.raises(ValueError, match="Open question q01 has no valid LLM judgement"):
        enrich_task_judgement(
            task,
            {"answers": [{"question_id": "q01", "value": "一段回答"}]},
            {"result": "incorrect", "misconception_summary": "", "feedback": ""},
        )


def test_unanswered_open_question_does_not_require_llm_classification():
    task = EventTask(
        event_id="event-1",
        title="Task",
        story_text="Story",
        display_text="Story",
        evaluation_payload={
            "questions": [{"id": "q01", "type": "short_answer", "prompt": "請說明。"}]
        },
    )

    result = enrich_task_judgement(
        task,
        {"answers": [{"question_id": "q01", "value": "  "}]},
        {"result": "unanswered", "misconception_summary": "未作答", "feedback": ""},
    )

    assert result["question_results"][0]["correctness"] == "unanswered"
    assert result["result"] == "unanswered"


def test_structured_question_judgement_has_only_four_correctness_values():
    with pytest.raises(ValueError):
        QuestionJudgementPayload(question_id="q01", correctness="ungraded")


def test_legacy_task_without_questions_preserves_provider_diagnosis():
    task = SimpleNamespace(evaluation_payload={})

    result = enrich_task_judgement(
        task,
        {"answer_text": "舊格式作答"},
        {
            "result": "partial",
            "misconception_summary": "仍有部分理解",
            "feedback": "後續對話再處理",
            "score": 50,
        },
    )

    assert result["result"] == "partial"
    assert result["question_results"] == []
    assert "score" not in result


def test_all_correct_fallback_is_frozen_into_the_task_judgement():
    task = EventTask(
        event_id="event-1",
        title="Task",
        story_text="Story",
        display_text="{{blank:q01}}",
        evaluation_payload={
            "questions": [
                {
                    "id": "q01",
                    "type": "cloze",
                    "prompt": "表決方式是什麼？",
                    "correct_answer": "按人數",
                }
            ],
            "all_correct_fallback": {
                "id": "fallback-01",
                "incorrect_claim": "三級會議原先採按人數表決。",
                "correct_interpretation": "三級會議原先採按等級表決。",
                "evidence_ids": ["E03"],
            },
        },
    )

    result = enrich_task_judgement(
        task,
        {"answers": [{"question_id": "q01", "value": "按人數"}]},
        {"result": "correct", "misconception_summary": "", "feedback": ""},
    )

    assert result["result"] == "correct"
    assert result["all_correct_fallback"] == {
        "id": "fallback-01",
        "incorrect_claim": "三級會議原先採按人數表決。",
        "correct_interpretation": "三級會議原先採按等級表決。",
        "source_text": None,
        "historical_concept": None,
        "reasoning_process": None,
        "evidence_ids": ["E03"],
    }
