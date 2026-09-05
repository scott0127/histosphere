from app.core.experiment_conditions import condition_code_for_key
from app.models.domain import EventTask
from app.models.domain import ChatMessage, Participant, utc_now
from datetime import timedelta
import pytest


@pytest.mark.parametrize("condition_key", ["no_ebl_no_roleplay", "ebl_no_roleplay", "no_ebl_roleplay", "ebl_roleplay"])
def test_timed_closure_is_scoped_durable_and_separate_from_chat(client, condition_key):
    from tests.test_api import submit_task
    initialized = initialize_event(client, condition_key=condition_key)
    submitted = submit_task(client, initialized)
    repo = client.app.state.repository
    sid, cid = initialized["session_id"], submitted["conversation_id"]
    url = f"/api/sessions/{sid}/state"
    assert client.get(url).json()["closure"] is None
    assert client.post(f"/api/sessions/{sid}/closure", json={"closure_id": "early", "reflection": "不應提前領答案"}).status_code == 409
    session = repo.get_session(sid)
    session.timer_ends_at = utc_now() - timedelta(seconds=1)
    repo.save_session(session)
    response = client.get(url)
    assert response.status_code == 200, response.text
    closure = response.json()["closure"]
    if not condition_key.startswith("ebl_"):
        assert closure is None
        return
    assert closure["question_id"] == "q01"
    assert closure["answer"] and closure["explanation"]
    assert "reasoning_criteria" not in closure and "answer_review" not in closure
    assert client.get(url).json()["closure"] == closure
    repo.save_participant(Participant(code="OTHER", auth_user_id="other", condition_list=["04"]))
    assert client.get(url, headers={"Authorization": "Bearer other"}).status_code == 403
    payload = {"closure_id": closure["closure_id"], "reflection": "我原先的判斷需要改變。"}
    assert client.post(f"/api/sessions/{sid}/closure", json=payload, headers={"Authorization": "Bearer other"}).status_code == 403
    assert client.post(f"/api/sessions/{sid}/closure", json={**payload, "reflection": "   "}).status_code == 422
    before = repo.list_messages(cid)
    closed = client.post(f"/api/sessions/{sid}/closure", json=payload)
    assert closed.status_code == 200, closed.text
    assert closed.json()["completed_at"]
    assert client.post(f"/api/sessions/{sid}/closure", json=payload).json() == closed.json()
    assert client.get(url).json()["closure"] == closed.json()
    assert repo.list_messages(cid) == before
    logs = [log for log in repo.list_research_logs_for_session(sid) if log.action_type == "session_closure_restatement"]
    assert len(logs) == 1 and logs[0].payload["independent_mastery"] is False
    assert client.post("/api/chat", json={"conversation_id": cid, "user_message": "重開聊天", "client_request_id": "late"}).status_code == 409
    client.app.state.session_service.reset_timer(sid)
    assert client.get(url).json()["closure"] is None
    assert client.post(f"/api/sessions/{sid}/closure", json=payload).status_code == 409


def test_timed_closure_handles_only_the_current_error_with_frozen_answers(client):
    from tests.test_api import submit_task
    from app.core.interaction_contract import INTERACTION_POLICY_VERSION
    initialized = initialize_event(client)
    submitted = submit_task(client, initialized)
    repo = client.app.state.repository
    sid, cid = initialized["session_id"], submitted["conversation_id"]
    attempt = repo.get_task_attempt(submitted["attempt_id"])
    first = attempt.judgement_payload["question_results"][0]
    attempt.judgement_payload["question_results"] = [first, {**first, "question_id": "q02",
        "expected_answer": False, "source_text": "原始文件時間不同於出版時間。"}]
    repo.save_task_attempt(attempt)
    session = repo.get_session(sid)
    session.timer_ends_at = utc_now() - timedelta(seconds=1)
    repo.save_session(session)
    url = f"/api/sessions/{sid}/state"
    assert client.get(url).json()["closure"]["question_id"] == "q01"
    repo.add_message(ChatMessage(conversation_id=cid, sequence_index=1, speaker_type="persona", speaker_name="人物",
        content="第一個判斷已修正，接著看第二個問題。", metadata={
            "interaction_policy_version": INTERACTION_POLICY_VERSION, "target_question_id": "q01",
            "dialogue_state": "RESOLVED", "completion_status": "feedback_completed",
            "next_target_question_id": "q02", "next_target_started": True}))
    closure = client.get(url).json()["closure"]
    assert closure["question_id"] == "q02" and closure["answer"] == "否"
    # 後來修改題目不能改變本次已凍結的正解與說明。
    task = repo.get_event_task(attempt.task_id)
    task.evaluation_payload["questions"][0]["source_text"] = "CHANGED"
    repo.save_event_task(task)
    assert client.get(url).json()["closure"] == closure
    repo.add_message(ChatMessage(conversation_id=cid, sequence_index=2, speaker_type="persona", speaker_name="人物",
        content="第二題已完成。", metadata={"interaction_policy_version": INTERACTION_POLICY_VERSION,
            "target_question_id": "q02", "dialogue_state": "RESOLVED", "completion_status": "feedback_completed"}))
    assert client.get(url).json()["closure"] is None


def initialize_event(client, event_name="法國大革命", condition_key="ebl_roleplay", user_id="participant-001"):
    created = client.post(
        "/api/event/initialize",
        json={
            "event_name": event_name,
            "condition_key": condition_key,
            "rebuild": False,
        },
        headers={"x-admin-key": "test-admin"},
    )
    assert created.status_code == 200
    created_payload = created.json()

    locked = client.post(
        f"/api/admin/events/{created_payload['event_id']}/material-lock",
        headers={"x-admin-key": "test-admin"},
        json={"locked": True},
    )
    assert locked.status_code == 200

    repository = client.app.state.repository
    participant = repository.get_participant_by_auth_user(user_id)
    assigned = client.patch(
        f"/api/admin/participants/{participant.id}",
        headers={"x-admin-key": "test-admin"},
        json={"condition_list": [condition_code_for_key(condition_key)]},
    )
    assert assigned.status_code == 200

    response = client.post(
        "/api/event/initialize",
        json={
            "event_name": created_payload["event"]["canonical_name"],
            "condition_key": condition_key,
            "rebuild": False,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_route_uuid_contracts_return_validation_errors(client):
    valid_session_id = "11111111-1111-4111-8111-111111111111"

    assert client.get("/api/sessions/not-a-uuid/state").status_code == 422
    assert client.get("/api/conversations/not-a-uuid").status_code == 422
    assert client.patch(
        "/api/tasks/not-a-uuid/draft",
        json={
            "session_id": valid_session_id,
            "response_payload": {},
        },
    ).status_code == 422
    assert client.post(
        "/api/tasks/not-a-uuid/submit",
        json={
            "session_id": valid_session_id,
            "response_payload": {},
        },
    ).status_code == 422


def test_replacing_task_keeps_existing_session_on_its_original_version(client):
    initialized = initialize_event(client)
    repository = client.app.state.repository
    replacement = repository.save_event_task(EventTask(
        event_id=initialized["event_id"],
        title="新版閱讀題組",
        error_elicitation_task_full_text="另一份題目。",
    ))
    state_url = f"/api/sessions/{initialized['session_id']}/state"
    # 尚未作答也必須依初始化快照取回舊題，而不是誤用最新版。
    assert client.get(state_url).json()["task"]["id"] == initialized["task"]["id"]

    draft = client.patch(
        f"/api/tasks/{initialized['task']['id']}/draft",
        json={"session_id": initialized["session_id"], "response_payload": {"answer_text": "舊題的答案"}},
    )
    assert draft.status_code == 200
    state = client.get(state_url).json()
    assert state["task"]["id"] == initialized["task"]["id"]
    assert state["attempt"]["response_payload"]["answer_text"] == "舊題的答案"
    progress = client.get("/api/sessions/progress").json()["progress"]
    assert next(item for item in progress if item["session_id"] == initialized["session_id"])["task_id"] == initialized["task"]["id"]

    request = {"event_name": "法國大革命", "condition_key": "ebl_roleplay"}
    resumed = client.post("/api/event/initialize", json=request)
    assert resumed.status_code == 200
    assert resumed.json()["task"]["id"] == initialized["task"]["id"]
    new_test = client.post("/api/event/initialize", json=request, headers={"x-admin-key": "test-admin"})
    assert new_test.status_code == 200
    assert new_test.json()["task"]["id"] == replacement.id


def test_session_state_progress_and_task_draft_follow_frontend_recovery_contract(client):
    initialized = initialize_event(client)

    empty_state = client.get(f"/api/sessions/{initialized['session_id']}/state")
    assert empty_state.status_code == 200
    empty_payload = empty_state.json()
    assert empty_payload["session"]["id"] == initialized["session_id"]
    assert empty_payload["event"]["id"] == initialized["event_id"]
    assert empty_payload["task"]["id"] == initialized["task"]["id"]
    assert empty_payload["attempt"] is None
    assert empty_payload["conversation_id"] is None

    draft = client.patch(
        f"/api/tasks/{initialized['task']['id']}/draft",
        json={
            "session_id": initialized["session_id"],
            "user_id": "participant-001",
            "response_payload": {
                "answers": [
                    {
                        "question_id": "q01",
                        "blank_id": "q01",
                        "type": "cloze",
                        "prompt": "請填入一個核心問題。",
                        "value": "制度危機",
                    }
                ]
            },
        },
    )
    assert draft.status_code == 200
    assert draft.json()["attempt"]["status"] == "in_progress"

    draft_state = client.get(f"/api/sessions/{initialized['session_id']}/state")
    draft_payload = draft_state.json()
    assert draft_payload["attempt"]["status"] == "in_progress"
    assert draft_payload["attempt"]["response_payload"]["answers"][0]["value"] == "制度危機"
    assert draft_payload["conversation_id"] is None

    progress = client.get("/api/sessions/progress", params={"user_id": "participant-001"})
    assert progress.status_code == 200
    progress_item = progress.json()["progress"][0]
    assert progress_item["event_id"] == initialized["event_id"]
    assert progress_item["condition_key"] == "ebl_roleplay"
    assert progress_item["session_id"] == initialized["session_id"]
    assert progress_item["task_id"] == initialized["task"]["id"]
    assert progress_item["status"] == "task_draft"


def test_submit_transitions_session_to_conversation_started(client):
    initialized = initialize_event(client, event_name="霧社事件", condition_key="no_ebl_no_roleplay")

    submitted = client.post(
        f"/api/tasks/{initialized['task']['id']}/submit",
        json={
            "session_id": initialized["session_id"],
            "user_id": "participant-001",
            "response_payload": {
                "answer_text": "霧社事件需要放在殖民治理、警察制度、族群關係與抵抗行動中理解。",
            },
        },
    )
    assert submitted.status_code == 202
    accepted_payload = submitted.json()
    polled = client.get(accepted_payload["poll_url"])
    assert polled.status_code == 200
    submitted_payload = polled.json()["result"]
    assert submitted_payload["conversation_id"]
    assert submitted_payload["attempt"]["status"] == "submitted"
    assert submitted_payload["history"][0]["speaker_type"] == "assistant"

    state = client.get(f"/api/sessions/{initialized['session_id']}/state")
    assert state.status_code == 200
    state_payload = state.json()
    assert state_payload["session"]["status"] == "conversation_started"
    assert state_payload["conversation_id"] == submitted_payload["conversation_id"]
    assert state_payload["attempt"]["id"] == submitted_payload["attempt_id"]

    progress = client.get("/api/sessions/progress", params={"user_id": "participant-001"})
    assert progress.status_code == 200
    progress_item = progress.json()["progress"][0]
    assert progress_item["conversation_id"] == submitted_payload["conversation_id"]
    assert progress_item["status"] == "chat_started"
