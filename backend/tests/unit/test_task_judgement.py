from app.models.domain import EventTask
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
    assert q01["historical_concept"] == "cause_and_consequence"
    assert q01["reasoning_process"] == "argumentation"
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
