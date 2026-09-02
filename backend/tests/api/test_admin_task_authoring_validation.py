from app.core.error_elicitation_contract import ERROR_ELICITATION_CONTRACT_VERSION
import pytest


def initialize_event(client, event_name="法國大革命") -> dict:
    response = client.post(
        "/api/event/initialize",
        json={"event_name": event_name, "condition_key": "ebl_roleplay", "rebuild": False},
        headers={"x-admin-key": "test-admin"},
    )
    assert response.status_code == 200
    initialized = response.json()
    snapshot = client.get("/api/admin/snapshot", headers={"x-admin-key": "test-admin"})
    assert snapshot.status_code == 200
    initialized["task"] = next(
        event["latest_task"] for event in snapshot.json()["events"]
        if event["id"] == initialized["event_id"]
    )
    return initialized


def test_admin_task_update_accepts_valid_structured_payload_and_logs(client):
    initialized = initialize_event(client)
    task = initialized["task"]

    updated = client.patch(
        f"/api/admin/tasks/{task['id']}",
        headers={"x-admin-key": "test-admin"},
        json={
            "title": "更新後 task",
            "story_text": task["story_text"],
            "error_elicitation_task_full_text": task["error_elicitation_task_full_text"],
            "evaluation_payload": task["evaluation_payload"],
            "revision_state": "teacher_modified",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["title"] == "更新後 task"

    logs = client.get("/api/admin/research-logs", headers={"x-admin-key": "test-admin"})
    assert logs.status_code == 200
    assert any(item["action_type"] == "task_updated" for item in logs.json())


def test_admin_task_update_rejects_corrupt_story_tokens_and_questions(client):
    initialized = initialize_event(client)
    task = initialized["task"]
    original_error_elicitation_task_full_text = task["error_elicitation_task_full_text"]

    invalid = client.patch(
        f"/api/admin/tasks/{task['id']}",
        headers={"x-admin-key": "test-admin"},
        json={
            "error_elicitation_task_full_text": "故事 {{blank:q01}} {{blank:q01}} {{blank:q99}}",
            "evaluation_payload": {
                "questions": [
                    {
                        "id": "q01",
                        "blank_id": "q01",
                        "type": "multiple_choice",
                        "prompt": "請選出答案。",
                        "options": [{"id": "a", "label": "A", "value": "A"}],
                        "correct_answer": "B",
                    },
                    {
                        "id": "q02",
                        "blank_id": "q02",
                        "type": "true_false",
                        "prompt": "請判斷是非。",
                        "correct_answer": "true",
                    },
                    {
                        "id": "q03",
                        "blank_id": "q01",
                        "type": "cloze",
                        "prompt": "請填空。",
                        "correct_answer": "",
                    },
                ]
            },
        },
    )

    assert invalid.status_code == 422
    detail = invalid.json()["detail"]
    assert detail["message"] == "Task authoring payload failed validation."
    codes = {issue["code"] for issue in detail["issues"]}
    assert {
        "duplicate_blank_token",
        "duplicate_question_blank_id",
        "orphan_blank_token",
        "question_missing_token",
        "missing_options",
        "invalid_true_false_answer",
        "missing_correct_answer",
    }.issubset(codes)

    snapshot = client.get("/api/admin/snapshot", headers={"x-admin-key": "test-admin"})
    latest_task = snapshot.json()["events"][0]["latest_task"]
    assert latest_task["id"] == task["id"]
    assert latest_task["error_elicitation_task_full_text"] == original_error_elicitation_task_full_text


def test_admin_task_update_rejects_required_null_fields(client):
    initialized = initialize_event(client, "霧社事件")
    task = initialized["task"]

    response = client.patch(
        f"/api/admin/tasks/{task['id']}",
        headers={"x-admin-key": "test-admin"},
        json={"error_elicitation_task_full_text": None},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["issues"][0]["field"] == "error_elicitation_task_full_text"
    assert detail["issues"][0]["code"] == "required_field_null"


@pytest.mark.parametrize("obsolete_field", ["prompt", "display_text"])
def test_admin_task_update_rejects_obsolete_full_text_names(client, obsolete_field):
    task = initialize_event(client)["task"]
    response = client.patch(
        f"/api/admin/tasks/{task['id']}",
        headers={"x-admin-key": "test-admin"},
        json={obsolete_field: "不得被默默忽略的完整題目內容"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"


def test_admin_can_save_new_task_contract_without_rewriting_existing_snapshot(client):
    initialized = initialize_event(client)
    repository = client.app.state.repository
    snapshot = next(log for log in repository.list_research_logs() if log.action_type == "session_material_snapshot")
    previous_snapshot = snapshot.model_dump_json()
    evaluation = initialized["task"]["evaluation_payload"]
    evaluation["contract_version"] = ERROR_ELICITATION_CONTRACT_VERSION
    evaluation["questions"][0]["reasoning_criteria"] = "說明題目素材如何支持答案。"
    evaluation["questions"][0].pop("prompt", None)
    response = client.patch(
        f"/api/admin/tasks/{initialized['task']['id']}",
        headers={"x-admin-key": "test-admin"},
        json={"error_elicitation_task_full_text": "逐題作答並說明理由。{{blank:q01}}", "evaluation_payload": evaluation},
    )
    assert response.status_code == 200
    assert response.json()["evaluation_payload"] == evaluation
    assert snapshot.model_dump_json() == previous_snapshot
