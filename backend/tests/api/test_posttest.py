from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.models.domain import Participant, utc_now
from tests.api.test_session_task_contracts import initialize_event
from tests.test_api import submit_task


ENGAGEMENT = {"engagement_1": 4, "engagement_2": 3, "engagement_3": 5}
HAT = {"hat_1": "這是第一題的示範答案與理由。", "hat_2": "這是第二題的示範答案與理由。"}


def completed_chat(client, condition="no_ebl_roleplay"):
    initialized = initialize_event(client, condition_key=condition)
    submitted = submit_task(client, initialized)
    sid = initialized["session_id"]
    session = client.app.state.repository.get_session(sid)
    session.timer_ends_at = utc_now() - timedelta(seconds=1)
    client.app.state.repository.save_session(session)
    return initialized, submitted, f"/api/sessions/{sid}/posttest"


def enter_hat(client, url):
    started = client.post(f"{url}/start")
    assert started.status_code == 200, started.text
    saved = client.patch(url, json={"revision": 0, "engagement_answers": ENGAGEMENT})
    assert saved.status_code == 200, saved.text
    advanced = client.post(f"{url}/advance", json={"revision": 1})
    assert advanced.status_code == 200, advanced.text
    return advanced.json()["response"]


def finish_posttest(client, url):
    enter_hat(client, url)
    saved = client.patch(url, json={"revision": 2, "hat_answers": HAT})
    assert saved.status_code == 200, saved.text
    submitted = client.post(f"{url}/submit", json={"revision": 3})
    assert submitted.status_code == 200, submitted.text
    return submitted.json()


def test_posttest_durable_ordered_and_idempotent(client):
    initialized, submitted, url = completed_chat(client)
    sid = initialized["session_id"]
    state = client.get(url)
    assert state.status_code == 200, state.text
    assert state.json()["eligible"] and state.json()["response"] is None
    assert state.json()["event_name"] == initialized["event"]["canonical_name"]
    assert client.get(f"/api/sessions/{sid}/state").json()["posttest_stage"] == "not_started"
    started = client.post(f"{url}/start").json()
    assert started["response"]["is_placeholder"] is True
    assert started["response"]["instrument_version"] == "posttest_placeholder_v1"
    assert client.post(f"{url}/start").json() == started
    assert client.post(f"{url}/advance", json={"revision": 0}).status_code == 422
    assert client.post(f"{url}/submit", json={"revision": 0}).status_code == 409
    assert client.patch(url, json={"revision": 0, "hat_answers": HAT}).status_code == 409
    client.patch(url, json={"revision": 0, "engagement_answers": {"engagement_1": 4}})
    assert client.get(url).json()["response"]["engagement_answers"] == {"engagement_1": 4}
    assert client.patch(url, json={"revision": 0, "engagement_answers": ENGAGEMENT}).status_code == 409
    client.patch(url, json={"revision": 1, "engagement_answers": ENGAGEMENT})
    assert client.post(f"{url}/advance", json={"revision": 2}).json()["response"]["stage"] == "hat"
    assert client.patch(url, json={"revision": 3, "engagement_answers": ENGAGEMENT}).status_code == 409
    assert client.post(f"{url}/submit", json={"revision": 3}).status_code == 422
    client.patch(url, json={"revision": 3, "hat_answers": {"hat_1": "   ", "hat_2": "reason"}})
    assert client.post(f"{url}/submit", json={"revision": 4}).status_code == 422
    client.patch(url, json={"revision": 4, "hat_answers": HAT})
    result = client.post(f"{url}/submit", json={"revision": 5}).json()
    assert result["response"]["stage"] == "completed"
    assert result["response"]["submitted_at"]
    assert result["response"]["hat_answers"] == HAT
    assert client.post(f"{url}/submit", json={"revision": 5}).json() == result
    assert client.patch(url, json={"revision": 6, "hat_answers": {"hat_1": "changed"}}).status_code == 409
    assert client.get(url).json() == result
    progress = client.get("/api/sessions/progress").json()["progress"]
    assert next(item for item in progress if item["session_id"] == sid)["posttest_stage"] == "completed"
    assert client.get(f"/api/sessions/{sid}/state").json()["posttest_stage"] == "completed"
    assert client.post("/api/chat", json={"conversation_id": submitted["conversation_id"], "user_message": "幫我做後測", "client_request_id": "late"}).status_code == 409
    assert client.app.state.repository.get_session(sid).completion_reason == "timer_elapsed"


def test_posttest_requires_chat_end_and_ebl_closure(client):
    initialized = initialize_event(client)
    url = f"/api/sessions/{initialized['session_id']}/posttest"
    assert client.get(url).json()["eligible"] is False
    assert client.post(f"{url}/start").status_code == 409
    submit_task(client, initialized)
    assert client.post(f"{url}/start").status_code == 409
    repo = client.app.state.repository
    session = repo.get_session(initialized["session_id"])
    session.timer_ends_at = utc_now() - timedelta(seconds=1)
    repo.save_session(session)
    closure = client.get(f"/api/sessions/{session.id}/state").json()["closure"]
    assert closure is not None
    assert client.post(f"{url}/start").status_code == 409
    response = client.post(f"/api/sessions/{session.id}/closure", json={"closure_id": closure["closure_id"], "reflection": "我的修正理由。"})
    assert response.status_code == 200
    assert client.post(f"{url}/start").status_code == 200
    with pytest.raises(HTTPException) as error:
        client.app.state.session_service.reset_timer(session.id)
    assert error.value.status_code == 409


@pytest.mark.parametrize("value", [0, 6, True, "4", 1.5])
def test_posttest_rejects_invalid_likert_values(client, value):
    _, _, url = completed_chat(client)
    client.post(f"{url}/start")
    assert client.patch(url, json={"revision": 0, "engagement_answers": {"engagement_1": value}}).status_code == 422


def test_posttest_ownership_unknown_keys_and_archived_session(client):
    initialized, _, url = completed_chat(client)
    repo = client.app.state.repository
    repo.save_participant(Participant(code="OTHER", auth_user_id="other", condition_list=["03"]))
    for method, suffix, body in [("get", "", None), ("post", "/start", None), ("patch", "", {"revision": 0}), ("post", "/advance", {"revision": 0}), ("post", "/submit", {"revision": 0})]:
        kwargs = {"headers": {"Authorization": "Bearer other"}}
        if body is not None:
            kwargs["json"] = body
        assert getattr(client, method)(url + suffix, **kwargs).status_code == 403
    client.post(f"{url}/start")
    assert client.patch(url, json={"revision": 0, "engagement_answers": {"unexpected": 3}}).status_code == 422
    assert client.patch(url, json={"revision": 0, "is_placeholder": False}).status_code == 422
    session = repo.get_session(initialized["session_id"])
    session.status = "archived"
    repo.save_session(session)
    assert client.get(url).json()["eligible"] is False
    assert client.patch(url, json={"revision": 0, "engagement_answers": ENGAGEMENT}).status_code == 409


def test_posttest_export_is_explicitly_placeholder(client):
    initialized, _, url = completed_chat(client)
    completed = finish_posttest(client, url)
    response = client.get(f"/api/admin/sessions/{initialized['session_id']}/research", headers={"x-admin-key": "test-admin"})
    assert response.status_code == 200, response.text
    assert response.json()["posttest"] == completed["response"]
    csv = client.get("/api/admin/research-export?format=csv", headers={"x-admin-key": "test-admin"})
    assert "posttest_is_placeholder" in csv.text and "posttest_placeholder_v1" in csv.text


def test_next_condition_is_blocked_until_posttest_submitted(client):
    initialized, _, url = completed_chat(client)
    repo = client.app.state.repository
    participant = repo.get_participant_by_auth_user("participant-001")
    participant.condition_list = ["03", "01"]
    repo.save_participant(participant)
    service = client.app.state.event_initialization_service
    with pytest.raises(HTTPException) as error:
        service._validate_participant_execution_order(participant, "no_ebl_no_roleplay", None)
    assert error.value.status_code == 409
    finish_posttest(client, url)
    service._validate_participant_execution_order(participant, "no_ebl_no_roleplay", None)
