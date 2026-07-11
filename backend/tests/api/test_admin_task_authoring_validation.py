def initialize_event(client, event_name="法國大革命") -> dict:
    response = client.post(
        "/api/event/initialize",
        json={"event_name": event_name, "condition_key": "ebl_roleplay", "rebuild": False},
        headers={"x-admin-key": "test-admin"},
    )
    assert response.status_code == 200
    return response.json()


def test_admin_task_update_accepts_valid_structured_payload_and_logs(client):
    initialized = initialize_event(client)
    task = initialized["task"]

    updated = client.patch(
        f"/api/admin/tasks/{task['id']}",
        headers={"x-admin-key": "test-admin"},
        json={
            "title": "更新後 task",
            "story_text": task["story_text"],
            "display_text": task["display_text"],
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
    original_display_text = task["display_text"]

    invalid = client.patch(
        f"/api/admin/tasks/{task['id']}",
        headers={"x-admin-key": "test-admin"},
        json={
            "display_text": "故事 {{blank:q01}} {{blank:q01}} {{blank:q99}}",
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
    assert latest_task["display_text"] == original_display_text


def test_admin_task_update_rejects_required_null_fields(client):
    initialized = initialize_event(client, "霧社事件")
    task = initialized["task"]

    response = client.patch(
        f"/api/admin/tasks/{task['id']}",
        headers={"x-admin-key": "test-admin"},
        json={"display_text": None},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["issues"][0]["field"] == "display_text"
    assert detail["issues"][0]["code"] == "required_field_null"
