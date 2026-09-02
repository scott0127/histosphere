import json
from pathlib import Path

from app.core.learner_task_view import learner_evaluation
from app.core.task_payload_validator import validate_task_authoring_payload


CONTENT_FILE = (
    Path(__file__).resolve().parents[3]
    / "supabase"
    / "content"
    / "error-elicitation-reading-tasks.json"
)


def test_four_curated_reading_tasks_follow_the_runtime_contract():
    content = json.loads(CONTENT_FILE.read_text(encoding="utf-8"))
    tasks = content["tasks"]

    assert len(tasks) == 4
    assert len({task["event_name"] for task in tasks}) == 4

    for task in tasks:
        evaluation = task["evaluation_payload"]
        assert validate_task_authoring_payload(
            task["error_elicitation_task_full_text"], evaluation
        ) == []
        assert len(evaluation["materials"]) == 2
        assert len(evaluation["questions"]) == 3
        assert {question["type"] for question in evaluation["questions"]} == {
            "multiple_choice",
            "true_false",
            "cloze",
        }

        material_ids = {material["id"] for material in evaluation["materials"]}
        for question in evaluation["questions"]:
            assert set(question["accepted_evidence_ids"]) <= material_ids

        # 正解、判定標準與來源網址只留在後端及 Admin 資料。
        learner_payload = learner_evaluation(evaluation)
        assert all("correct_answer" not in question for question in learner_payload["questions"])
        assert all("reasoning_criteria" not in question for question in learner_payload["questions"])
        assert all("source_url" not in material for material in learner_payload["materials"])
        assert all("attribution" not in material for material in learner_payload["materials"])
