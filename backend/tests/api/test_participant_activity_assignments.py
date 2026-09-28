import pytest

from app.models.domain import SessionPosttest, utc_now
from tests.api.test_admin_participant_preview import ADMIN_HEADERS, preview_initialize
from tests.test_api import initialize_event


def materials(client):
    return [initialize_event(client, f"配對事件 {name}", "ebl_roleplay") for name in ("A", "B", "C")]


def pairs(events):
    return [{"event_id": events[0]["event_id"], "condition_code": "02"},
            {"event_id": events[1]["event_id"], "condition_code": "04"}]


def update(client, participant, payload, *, admin=True):
    return client.patch(f"/api/admin/participants/{participant.id}",
                        headers=ADMIN_HEADERS if admin else {}, json=payload)


def assign(client, events):
    participant = client.app.state.repository.get_participant_by_auth_user("participant-001")
    response = update(client, participant, {"activity_assignments": pairs(events), "metadata": {"cohort_note": "keep"}})
    assert response.status_code == 200, response.text
    return client.app.state.repository.get_participant(participant.id)


def start(client, participant, event, code="02", *, preview=False):
    condition = "ebl_no_roleplay" if code == "02" else "ebl_roleplay"
    if preview:
        return preview_initialize(client, participant, event["event"]["canonical_name"], condition)
    return client.post("/api/event/initialize", json={
        "event_name": event["event"]["canonical_name"], "condition_key": condition,
    })


def lock_materials(client, events):
    for event in events:
        assert client.post(f"/api/admin/events/{event['event_id']}/material-lock",
                           headers=ADMIN_HEADERS, json={"locked": True}).status_code == 200


def test_admin_creates_paired_participant_and_merges_metadata_with_audit(client):
    events = materials(client)
    assignments = pairs(events)
    created = client.post("/api/admin/participants", headers=ADMIN_HEADERS, json={
        "code": "PAIRED", "activity_assignments": assignments, "metadata": {"other": "preserved"},
    })
    assert created.status_code == 201, created.text
    data = created.json()
    assert data["condition_list"] == ["02", "04"]
    assert data["metadata"] == {"other": "preserved", "activity_assignments": assignments}
    assert "activity_assignments" not in data
    participant = client.app.state.repository.get_participant(data["id"])
    assert update(client, participant, {"notes": "unauthorized"}, admin=False).status_code == 401
    assert client.post("/api/admin/participants", json={"code": "DENIED", "activity_assignments": assignments}).status_code == 401
    updated = update(client, participant, {"metadata": {"new": "value"}, "display_name": "Learner"})
    assert updated.status_code == 200
    assert updated.json()["metadata"] == {"other": "preserved", "new": "value", "activity_assignments": assignments}
    assert update(client, participant, {"metadata": None}).json()["metadata"] == updated.json()["metadata"]
    logs = [log for log in client.app.state.repository.list_research_logs()
            if log.action_type == "participant_created" and log.payload["participant_id"] == participant.id]
    assert logs[0].payload["changes"]["metadata"]["after"]["activity_assignments"] == assignments


@pytest.mark.parametrize("bad_kind", ["duplicate_condition", "duplicate_event", "missing_event", "archived_event",
                                     "inactive_condition", "unknown_condition", "mismatching_conditions", "null", "metadata"])
def test_rejects_invalid_pair_configuration_without_changing_participant(client, bad_kind):
    events = materials(client)
    participant = client.app.state.repository.get_participant_by_auth_user("participant-001")
    before = participant.model_dump()
    assignments = pairs(events)
    payload = {"activity_assignments": assignments}
    if bad_kind == "duplicate_condition":
        assignments[1]["condition_code"] = "02"
    elif bad_kind == "duplicate_event":
        assignments[1]["event_id"] = assignments[0]["event_id"]
    elif bad_kind == "missing_event":
        assignments[0]["event_id"] = "missing"
    elif bad_kind == "archived_event":
        event = client.app.state.repository.get_event(assignments[0]["event_id"])
        event.archived_at = utc_now()
        client.app.state.repository.save_event(event)
    elif bad_kind == "inactive_condition":
        condition = client.app.state.repository.get_condition_by_key("ebl_no_roleplay")
        condition.active = False
        client.app.state.repository.save_condition(condition)
    elif bad_kind == "unknown_condition":
        assignments[0]["condition_code"] = "05"
    elif bad_kind == "mismatching_conditions":
        payload["condition_list"] = ["04", "02"]
    elif bad_kind == "null":
        payload["activity_assignments"] = None
    else:
        payload = {"metadata": {"activity_assignments": assignments}}
    response = update(client, participant, payload)
    assert response.status_code == 422, response.text
    assert client.app.state.repository.get_participant(participant.id).model_dump() == before


@pytest.mark.parametrize("preview", [False, True])
def test_paired_rounds_enforce_event_order_resume_and_posttest_before_next(client, preview):
    events = materials(client)
    participant = assign(client, events)
    if not preview:
        lock_materials(client, events)
    repository = client.app.state.repository
    count_before = len(repository.list_sessions())
    assert start(client, participant, events[1], preview=preview).status_code == 403
    assert start(client, participant, events[0], "04", preview=preview).status_code == 403
    assert start(client, participant, events[2], preview=preview).status_code == 403
    assert start(client, participant, events[1], "04", preview=preview).status_code == 409
    assert len(repository.list_sessions()) == count_before
    started = start(client, participant, events[0], preview=preview)
    assert started.status_code == 200, started.text
    first_id = started.json()["session_id"]
    resumed = start(client, participant, events[0], preview=preview)
    assert resumed.status_code == 200 and resumed.json()["session_id"] == first_id
    assert start(client, participant, events[1], "04", preview=preview).status_code == 409
    first = repository.get_session(first_id)
    first.status, first.completed_at, first.completion_reason = "completed", utc_now(), "learner"
    repository.save_session(first)
    assert start(client, participant, events[1], "04", preview=preview).status_code == 409
    posttest = repository.create_posttest(SessionPosttest(session_id=first.id, stage="engagement"))
    assert start(client, participant, events[1], "04", preview=preview).status_code == 409
    posttest.stage, posttest.submitted_at = "completed", utc_now()
    assert repository.update_posttest(posttest, expected_revision=posttest.revision)
    second = start(client, participant, events[1], "04", preview=preview)
    assert second.status_code == 200, second.text
    assert repository.get_session(second.json()["session_id"]).is_admin_test is preview
    logs = [log for log in repository.list_research_logs() if log.session_id == first_id
            and log.action_type in {"event_initialized", "event_session_resumed"}]
    assert all(log.payload["activity_assignments"] == pairs(events) for log in logs)


@pytest.mark.parametrize("preview", [False, True])
def test_reassignment_preserves_started_rounds_and_allows_compatible_future_changes(client, preview):
    events = materials(client)
    participant = assign(client, events)
    if not preview:
        lock_materials(client, events)
    repository = client.app.state.repository
    started = start(client, participant, events[0], preview=preview)
    assert started.status_code == 200
    session = repository.get_session(started.json()["session_id"])
    original = session.model_dump()
    for changed in (pairs([events[2], events[1]]), list(reversed(pairs(events))), []):
        response = update(client, participant, {"activity_assignments": changed})
        assert response.status_code == 409, response.text
    assert update(client, participant, {"condition_list": ["04"]}).status_code == 422
    assert update(client, participant, {"metadata": {"activity_assignments": []}}).status_code == 422
    compatible = pairs([events[0], events[2]])
    response = update(client, participant, {"activity_assignments": compatible})
    assert response.status_code == 200, response.text
    assert response.json()["metadata"] == {"cohort_note": "keep", "activity_assignments": compatible}
    assert repository.get_session(session.id).model_dump() == original
    session.status = "archived"
    repository.save_session(session)
    reassigned = update(client, participant, {"activity_assignments": pairs([events[2], events[1]])})
    assert reassigned.status_code == 200, reassigned.text
    assert repository.get_session(session.id).status == "archived"


@pytest.mark.parametrize("preview", [False, True])
def test_old_completion_for_another_event_never_satisfies_a_new_pair(client, preview):
    events = materials(client)
    participant = assign(client, events)
    if not preview:
        lock_materials(client, events)
    repository = client.app.state.repository
    first = start(client, participant, events[0], preview=preview)
    session = repository.get_session(first.json()["session_id"])
    session.status, session.completed_at = "completed", utc_now()
    repository.save_session(session)
    repository.create_posttest(SessionPosttest(session_id=session.id, stage="completed", submitted_at=utc_now()))
    # Simulate imported/legacy inconsistent data, bypassing the admin API's conflict guard.
    participant.metadata["activity_assignments"] = pairs([events[2], events[1]])
    repository.save_participant(participant)
    skipped = start(client, participant, events[1], "04", preview=preview)
    assert skipped.status_code == 409
    assert "既有活動進度與目前分派的事件、模式不一致" in skipped.json()["detail"]


def test_legacy_condition_only_assignment_remains_supported_and_can_gain_compatible_pairs(client):
    events = materials(client)
    repository = client.app.state.repository
    participant = repository.get_participant_by_auth_user("participant-001")
    assert update(client, participant, {"condition_list": ["02", "04"]}).status_code == 200
    lock_materials(client, events)
    started = start(client, participant, events[0])
    assert started.status_code == 200
    assert "activity_assignments" not in repository.get_participant(participant.id).metadata
    paired = update(client, participant, {"activity_assignments": pairs(events), "condition_list": ["02", "04"]})
    assert paired.status_code == 200, paired.text
    resumed = start(client, participant, events[0])
    assert resumed.status_code == 200 and resumed.json()["session_id"] == started.json()["session_id"]
