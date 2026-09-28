"""An incomplete draft must be caught before it is locked for an experiment."""

import pytest

from tests.api.test_runtime_safety import admin_initialize, ADMIN_HEADERS


@pytest.mark.parametrize("missing", ["question", "fallback"])
def test_lock_requires_student_facing_correction_explanations(client, missing):
    initialized = admin_initialize(client)
    repo = client.app.state.repository
    task = repo.get_event_task(initialized["task"]["id"])
    if missing == "question":
        task.evaluation_payload["questions"][0]["source_text"] = "  "
    else:
        task.evaluation_payload["all_correct_fallback"] = {
            "id": "fallback", "incorrect_claim": "錯誤主張", "correct_interpretation": "修正後的判斷",
        }
    repo.save_event_task(task)
    response = client.post(
        f"/api/admin/events/{initialized['event_id']}/material-lock",
        headers=ADMIN_HEADERS, json={"locked": True},
    )
    assert response.status_code == 422
    issues = response.json()["detail"]["issues"]
    assert any(issue["code"] == "missing_closure_explanation" for issue in issues)
    assert repo.get_event(initialized["event_id"]).materials_locked_at is None
    if missing == "question":
        task.evaluation_payload["questions"][0]["source_text"] = "經核對、提供學生閱讀的解說。"
    else:
        task.evaluation_payload["all_correct_fallback"]["source_text"] = "經核對、提供學生閱讀的解說。"
    repo.save_event_task(task)
    assert client.post(
        f"/api/admin/events/{initialized['event_id']}/material-lock",
        headers=ADMIN_HEADERS, json={"locked": True},
    ).status_code == 200
