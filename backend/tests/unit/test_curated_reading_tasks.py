import json
import hashlib
import re
from pathlib import Path

from app.core.learner_task_view import learner_evaluation
from app.core.task_payload_validator import validate_task_authoring_payload


CONTENT_FILE = (
    Path(__file__).resolve().parents[3]
    / "supabase"
    / "content"
    / "error-elicitation-reading-tasks.json"
)
MIGRATION_FILE = CONTENT_FILE.parents[1] / "migrations" / "202609040002_curated_error_elicitation_tasks.sql"


def test_curated_task_migration_matches_the_canonical_json():
    """避免正式 DB／fresh seed 與研究者核定的 JSON 靜默分歧。"""
    content = json.loads(CONTENT_FILE.read_text(encoding="utf-8"))
    sql = MIGRATION_FILE.read_text(encoding="utf-8")
    embedded_match = re.search(r"\$json\$(.*?)\$json\$::jsonb", sql, re.DOTALL)
    hash_match = re.search(r"source_sha256: ([0-9a-f]{64})", sql)

    assert embedded_match is not None
    assert hash_match is not None
    embedded = embedded_match.group(1)
    assert json.loads(embedded) == content
    assert hashlib.sha256(embedded.encode("utf-8")).hexdigest() == hash_match.group(1)


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
        assert "authoring" not in learner_payload
        # 編製註記留在 Admin；受測者仍能看到判讀所需的年代與材料名稱。
        learner_copy = task["error_elicitation_task_full_text"] + "".join(
            material.get("caption", "") for material in learner_payload["materials"]
        )
        assert not any(notice in learner_copy for notice in ("改寫", "原創", "逐字"))
        assert all(material.get("caption") for material in learner_payload["materials"])
        assert all("correct_answer" not in question for question in learner_payload["questions"])
        assert all("reasoning_criteria" not in question for question in learner_payload["questions"])
        assert all("source_url" not in material for material in learner_payload["materials"])
        assert all("attribution" not in material for material in learner_payload["materials"])
