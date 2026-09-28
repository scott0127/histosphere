"""HTTP permissions, private review recovery and resumable SSE notifications."""

import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import state_events
from tests.api.test_error_elicitation_workflow import answers, initialize, judged
from tests.task_review_helpers import ADMIN_HEADERS, review_and_approve


@pytest.fixture
def pending_review(client):
    initialized = initialize(client, "ebl_no_roleplay")

    async def judge(*args):
        return judged()

    client.app.state.llm_provider.judge_task_attempt = judge
    submitted = client.post(f"/api/tasks/{initialized['task']['id']}/submit", json={
        "session_id": initialized["session_id"], "response_payload": answers(),
    })
    assert submitted.status_code == 202, submitted.text
    accepted = submitted.json()
    assert client.get(accepted["poll_url"]).json()["attempt"]["status"] == "awaiting_review"
    return initialized, accepted


def _short_stream(monkeypatch):
    """Keep the production generator but end after its first polling interval."""
    clock = SimpleNamespace(value=0)

    async def advance(_seconds):
        clock.value += 46

    monkeypatch.setattr(state_events, "time", SimpleNamespace(monotonic=lambda: clock.value))
    monkeypatch.setattr(state_events, "asyncio", SimpleNamespace(to_thread=asyncio.to_thread, sleep=advance))


def _events(response):
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    return [json.loads(line.removeprefix("data: ")) for line in response.text.splitlines()
            if line.startswith("data: ")]


@pytest.mark.parametrize("endpoint", ["snapshot", "events", "save", "approve", "retry"])
def test_monitor_routes_require_admin_even_for_the_session_owner(client, pending_review, endpoint):
    initialized, accepted = pending_review
    sid, aid = initialized["session_id"], accepted["attempt_id"]
    method, path, body = {
        "snapshot": ("GET", f"/api/admin/monitor/sessions/{sid}", None),
        "events": ("GET", f"/api/admin/monitor/sessions/{sid}/events", None),
        "save": ("PATCH", f"/api/admin/monitor/attempts/{aid}/review", {"expected_version": 0, "question_results": []}),
        "approve": ("POST", f"/api/admin/monitor/attempts/{aid}/approve", {"expected_version": 0}),
        "retry": ("POST", f"/api/admin/monitor/attempts/{aid}/retry", None),
    }[endpoint]
    for headers in ({}, {"x-admin-key": "invalid-admin-key"}):
        response = client.request(method, path, headers=headers, json=body)
        assert response.status_code == 401, response.text
    assert client.app.state.repository.get_task_attempt(aid).review_version == 0


def test_learner_status_and_sse_enforce_ownership_over_http(client, pending_review, monkeypatch):
    _, accepted = pending_review
    _short_stream(monkeypatch)
    for path in (accepted["poll_url"], f"{accepted['poll_url']}/events"):
        unauthenticated = TestClient(client.app).get(path)
        assert unauthenticated.status_code == 401
        other = client.get(path, headers={"Authorization": "Bearer participant-002"})
        assert other.status_code == 403, other.text
        owner = client.get(path)
        assert owner.status_code == 200, owner.text
    event = _events(client.get(f"{accepted['poll_url']}/events"))[0]
    assert event["stage"] == "awaiting_review"
    assert set(event) == {"attempt_id", "stage", "version"}


def test_review_draft_reloads_privately_and_only_owner_entry_starts_timer(client, pending_review):
    initialized, accepted = pending_review
    sid, aid = initialized["session_id"], accepted["attempt_id"]
    monitor_url = f"/api/admin/monitor/sessions/{sid}"
    initial = client.get(monitor_url, headers=ADMIN_HEADERS).json()["attempt"]
    rows = deepcopy(initial["review_payload"]["question_results"])
    rows[0]["reviewed"] = True
    rows[1].update(reviewed=True, reasoning_correct=True,
                   reasoning_feedback="PRIVATE_REVISED_REASONING: 人工核對後理由符合要求。",
                   override_reason="PRIVATE_REVIEW_NOTE: 受測者已表達相同概念。")
    saved = client.patch(f"/api/admin/monitor/attempts/{aid}/review", headers=ADMIN_HEADERS, json={
        "expected_version": initial["review_version"], "question_results": rows,
    })
    assert saved.status_code == 200, saved.text

    # A separate administrator browser has no client-side review state to reuse.
    reconnected_admin = TestClient(client.app, headers=ADMIN_HEADERS)
    recovered = reconnected_admin.get(monitor_url)
    assert recovered.status_code == 200, recovered.text
    restored = recovered.json()["attempt"]
    assert restored["review_payload"] == saved.json()["review_payload"]
    assert restored["review_version"] == saved.json()["review_version"]
    student = client.get(accepted["poll_url"])
    assert "PRIVATE_" not in student.text
    assert student.json()["attempt"]["review_payload"] == {}
    assert student.json()["attempt"]["ai_judgement_payload"] == {}
    assert student.json()["result"] is None
    incomplete = reconnected_admin.post(f"/api/admin/monitor/attempts/{aid}/approve", json={
        "expected_version": restored["review_version"],
    })
    assert incomplete.status_code == 422, incomplete.text

    for row in rows:
        row["reviewed"] = True
    saved = reconnected_admin.patch(f"/api/admin/monitor/attempts/{aid}/review", json={
        "expected_version": restored["review_version"], "question_results": rows,
    })
    assert saved.status_code == 200, saved.text
    approved = reconnected_admin.post(f"/api/admin/monitor/attempts/{aid}/approve", json={
        "expected_version": saved.json()["review_version"],
    })
    assert approved.status_code == 200, approved.text
    ready = client.get(accepted["poll_url"])
    assert ready.json()["attempt"]["status"] == "ready"
    assert "PRIVATE_" not in ready.text
    repo = client.app.state.repository
    assert repo.get_session(sid).timer_started_at is None
    assert repo.get_task_attempt(aid).judgement_payload["question_results"][1]["reasoning_correct"] is True

    rejected = client.post(f"{accepted['poll_url']}/enter", headers={"Authorization": "Bearer participant-002"})
    assert rejected.status_code == 403, rejected.text
    assert repo.get_session(sid).timer_started_at is None
    entered = client.post(f"{accepted['poll_url']}/enter")
    assert entered.status_code == 200, entered.text
    assert "PRIVATE_" not in entered.text
    timer = repo.get_session(sid).timer_started_at
    assert timer is not None
    replay = client.post(f"{accepted['poll_url']}/enter")
    assert replay.status_code == 200
    assert replay.json()["conversation_id"] == entered.json()["conversation_id"]
    assert repo.get_session(sid).timer_started_at == timer


def test_sse_reconnect_emits_current_stage_without_private_verdicts(client, pending_review, monkeypatch):
    initialized, accepted = pending_review
    _short_stream(monkeypatch)
    learner_url = f"{accepted['poll_url']}/events"
    admin_url = f"/api/admin/monitor/sessions/{initialized['session_id']}/events"
    before = _events(client.get(learner_url))[0]
    before_admin = _events(client.get(admin_url, headers=ADMIN_HEADERS))[0]
    assert before["stage"] == before_admin["stage"] == "awaiting_review"
    review_and_approve(client, accepted)
    # The original connection missed approval; a new connection reads persisted state.
    after = _events(client.get(learner_url))[0]
    after_admin = _events(client.get(admin_url, headers=ADMIN_HEADERS))[0]
    assert after["stage"] == after_admin["stage"] == "ready"
    assert after["version"] != before["version"]
    assert after_admin["version"] != before_admin["version"]
    assert set(after) == {"attempt_id", "stage", "version"}
    assert set(after_admin) == {"session_id", "stage", "version"}
    assert client.app.state.repository.get_session(initialized["session_id"]).timer_started_at is None


def test_sse_stream_emits_changes_without_repeating_unchanged_state(monkeypatch):
    ticks = []
    current = {"stage": "awaiting_review", "version": "saved-1"}

    async def tick(_seconds):
        ticks.append(1)
        if len(ticks) == 2:
            current.update(stage="ready", version="saved-2")

    async def connected():
        return False

    monkeypatch.setattr(state_events, "asyncio", SimpleNamespace(to_thread=asyncio.to_thread, sleep=tick))

    async def consume():
        response = state_events.state_event_response(SimpleNamespace(is_disconnected=connected), lambda: dict(current))
        stream = response.body_iterator
        try:
            first = await anext(stream)
            second = await anext(stream)
            return first, second
        finally:
            await stream.aclose()

    first, second = asyncio.run(consume())
    assert '"stage": "awaiting_review"' in first
    assert '"stage": "ready"' in second
    assert len(ticks) == 2
