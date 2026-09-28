import json
import hashlib
import re
from pathlib import Path

from app.core.learner_task_view import learner_evaluation
from app.core.task_payload_validator import validate_task_authoring_payload, validate_task_closure_payload


CONTENT_FILE = (
    Path(__file__).resolve().parents[3]
    / "supabase"
    / "content"
    / "error-elicitation-reading-tasks.json"
)
MIGRATION_FILE = CONTENT_FILE.parents[1] / "migrations" / "202609040002_curated_error_elicitation_tasks.sql"
WUSHE_MIGRATION = MIGRATION_FILE.with_name("202609050001_wushe_reading_materials.sql")
MATERIAL_MIGRATION = MIGRATION_FILE.with_name("202609050002_descriptive_reading_materials.sql")
COPY_MIGRATION = MIGRATION_FILE.with_name("202609160001_wushe_learner_copy.sql")
FACT_CHECK_MIGRATION = MIGRATION_FILE.with_name("202609170001_source_checked_history_content.sql")
EVENT_CONTENT_FILE = CONTENT_FILE.with_name("historical-events.json")
PERSONA_REVIEW_MIGRATION = MIGRATION_FILE.with_name("202609200001_verified_persona_profiles.sql")


def _migration_payload(path):
    sql = path.read_text(encoding="utf-8")
    embedded_match = re.search(r"\$json\$(.*?)\$json\$::jsonb", sql, re.DOTALL)
    hash_match = re.search(r"source_sha256: ([0-9a-f]{64})", sql)

    assert embedded_match is not None
    assert hash_match is not None
    embedded = embedded_match.group(1)
    assert hashlib.sha256(embedded.encode("utf-8")).hexdigest() == hash_match.group(1)
    return json.loads(embedded)


def test_curated_task_migration_matches_the_canonical_json():
    """依序套用新增版本，不回寫已發布 migration，也不改既有作答快照。"""
    content = json.loads(CONTENT_FILE.read_text(encoding="utf-8"))
    baseline = _migration_payload(MIGRATION_FILE)
    updates = _migration_payload(WUSHE_MIGRATION)["tasks"]
    assert len(updates) == 1
    assert updates[0]["event_name"] == "霧社事件"
    old_task = next(task for task in baseline["tasks"] if task["event_name"] == "霧社事件")
    assert old_task["evaluation_payload"]["questions"] == updates[0]["evaluation_payload"]["questions"]
    baseline["tasks"] = [updates[0] if task["event_name"] == "霧社事件" else task for task in baseline["tasks"]]
    sql = MATERIAL_MIGRATION.read_text(encoding="utf-8")
    material_updates = json.loads(re.search(r"\$json\$(.*?)\$json\$::JSONB", sql, re.DOTALL).group(1))
    version = re.search(r"to_jsonb\('([^']+)'::TEXT\)", sql).group(1)
    baseline["version"] = version
    for task in baseline["tasks"]:
        evaluation = task["evaluation_payload"]
        for material in evaluation["materials"]:
            material.update(material_updates[material["id"]])
        evaluation["authoring"]["version"] = version
        if task["event_name"] == "法國大革命":
            evaluation["authoring"]["sources"].append("https://commons.wikimedia.org/wiki/File:Le_Serment_du_Jeu_de_paume.jpg")
    copy_update = _migration_payload(COPY_MIGRATION)
    baseline["version"] = copy_update["version"]
    task = next(task for task in baseline["tasks"] if task["event_name"] == copy_update["event_name"])
    assert task["error_elicitation_task_full_text"].count(copy_update["instruction_before"]) == 1
    task["error_elicitation_task_full_text"] = task["error_elicitation_task_full_text"].replace(
        copy_update["instruction_before"], copy_update["instruction_after"]
    )
    task["evaluation_payload"]["authoring"]["version"] = copy_update["version"]
    revision = _migration_payload(FACT_CHECK_MIGRATION)
    assert revision["previous_tasks"] == baseline["tasks"]
    baseline["tasks"] = revision["tasks"]
    baseline["version"] = revision["version"]
    assert baseline == content
    events = json.loads(EVENT_CONTENT_FILE.read_text(encoding="utf-8"))
    persona_revision = _migration_payload(PERSONA_REVIEW_MIGRATION)
    for event in revision["events"]:
        for persona in event["personas"]:
            patch = next(p for p in persona_revision["personas"]
                         if event["canonical_name"] in p["event_names"] and p["name"] == persona["name"])
            persona["prompt_profile"] = patch["prompt_profile"]
            persona["sources"] = patch["canonical_sources"]
    assert revision["events"] == events["events"]
    assert events["version"] == content["version"]

    # Fresh seed 直接建立現行題組；不重播同一交易內可能具有相同時間戳的歷次修訂。
    seed_config = (CONTENT_FILE.parents[1] / "config.toml").read_text(encoding="utf-8")
    seed_paths = re.search(r"sql_paths\s*=\s*\[(.*?)\]", seed_config, re.DOTALL).group(1)
    assert re.findall(r'"([^"]+)"', seed_paths) == [
        "./seed.sql", f"./migrations/{FACT_CHECK_MIGRATION.name}",
        f"./migrations/{PERSONA_REVIEW_MIGRATION.name}",
    ]
    seed_sql = (CONTENT_FILE.parents[1] / "seed.sql").read_text(encoding="utf-8")
    assert "INSERT INTO event_tasks" not in seed_sql
    evaluation = updates[0]["evaluation_payload"]
    provenance = evaluation["authoring"]["image_provenance"]
    assert evaluation["materials"][1]["image_url"] == provenance["path"]
    image = CONTENT_FILE.parents[2] / "public" / provenance["path"].lstrip("/")
    assert image.read_bytes().startswith(b"\xff\xd8")
    assert hashlib.sha256(image.read_bytes()).hexdigest() == provenance["sha256"]


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
        assert validate_task_closure_payload(evaluation) == []
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
        for material in evaluation["materials"]:
            image_url = material.get("image_url", "")
            if image_url.startswith("/images/"):
                image = CONTENT_FILE.parents[2] / "public" / image_url.lstrip("/")
                assert image.read_bytes().startswith(b"\xff\xd8")


def test_fact_check_revision_preserves_question_identity_and_answer_keys():
    revision = _migration_payload(FACT_CHECK_MIGRATION)
    old_tasks = {task["event_name"]: task for task in revision["previous_tasks"]}
    for task in revision["tasks"]:
        old = old_tasks[task["event_name"]]["evaluation_payload"]
        new = task["evaluation_payload"]
        identity = lambda evaluation: [
            (q["id"], q["type"], q["correct_answer"], q["required"])
            for q in evaluation["questions"]
        ]
        assert identity(old) == identity(new)
        assert [m["id"] for m in old["materials"]] == [m["id"] for m in new["materials"]]
        assert [m.get("image_url") for m in old["materials"]] == [m.get("image_url") for m in new["materials"]]


def test_revised_event_and_persona_sources_follow_existing_models():
    from app.models.domain import Event, Persona

    content = json.loads(EVENT_CONTENT_FILE.read_text(encoding="utf-8"))
    for item in content["events"]:
        event = Event(**{key: value for key, value in item.items() if key not in ("personas", "content_review")})
        assert event.start_year <= event.end_year
        assert item["content_review"]["sources"]
        for fields in item["personas"]:
            persona = Persona(event_id=event.id, **fields)
            assert persona.sources
            assert all(source.get("url", "").startswith("https://") for source in persona.sources)
            profile = persona.prompt_profile
            assert profile["event_timepoint_year"] == profile["knowledge_cutoff_year"]
            for field in ("event_timepoint", "event_location", "event_vantage_point", "current_stakes",
                          "social_position", "relationship_to_event", "teacher_notes", "source_policy"):
                assert profile[field], (persona.name, field)
            assert profile["firsthand_experience_allowed"] is False
            assert any(source.get("checked_at") == "2026-09-20" and source.get("supports") for source in persona.sources)
