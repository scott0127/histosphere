"""A turn accepted before expiry is delivered once and remains readable at closure."""

from datetime import timedelta
import json

import pytest

from app.models.domain import ChatMessage, utc_now
from app.providers.llm.base import ChatGenerationResult
from app.services.posttest_service import PosttestService
from tests.api.test_session_task_contracts import initialize_event
from tests.test_api import submit_task


@pytest.mark.parametrize("condition", ["no_ebl_no_roleplay", "ebl_no_roleplay", "no_ebl_roleplay", "ebl_roleplay"])
def test_inflight_reply_survives_expiry_and_gates_closure(client, monkeypatch, condition):
    initialized = initialize_event(client, condition_key=condition)
    submitted = submit_task(client, initialized)
    repo = client.app.state.repository
    sid, cid = initialized["session_id"], submitted["conversation_id"]
    service = client.app.state.chat_service
    calls = []

    async def generate(**kwargs):
        calls.append(True)
        session = repo.get_session(sid)
        session.timer_ends_at = utc_now() - timedelta(seconds=1)
        repo.save_session(session)
        waiting = client.app.state.session_service.load_state(sid)
        assert waiting.pending_final_response is True
        assert waiting.closure is None
        assert waiting.final_exchange.learner_message == "照片沒有居民的說法，還需要其他材料嗎？"
        assert waiting.final_exchange.assistant_message is None
        assert PosttestService(repo).load(sid).eligible is False
        return ChatGenerationResult(response="你已注意到材料的限制，能用自己的話說明嗎？"), {
            "target_question_id": "q01", "completion_status": "continue",
        }, kwargs["base_prompt"]

    monkeypatch.setattr(service, "generate_validated_response", generate)
    request = {"conversation_id": cid, "user_message": "照片沒有居民的說法，還需要其他材料嗎？", "client_request_id": "last-turn"}
    result = client.post("/api/chat", json=request)
    assert result.status_code == 200, result.text
    message = result.json()["message"]
    assert message["metadata"]["delivered_after_deadline"] is True
    assert message["metadata"]["delivery_phase"] == "post_timer_closure"
    state = client.get(f"/api/sessions/{sid}/state").json()
    assert not state["pending_final_response"]
    assert state["final_exchange"]["assistant_message"] == message["content"]
    assert state["final_exchange"]["delivered_after_deadline"]
    if condition.startswith("ebl_"):
        assert state["closure"]["question_id"] == "q01"
    assert client.post("/api/chat", json=request).json()["message"]["id"] == message["id"]
    stream = client.post("/api/chat/stream", json=request)
    assert stream.status_code == 200
    frames = [json.loads(line[6:]) for line in stream.text.splitlines() if line.startswith("data: ")]
    assert frames[0]["type"] == "user_message"
    assert frames[-1]["type"] == "complete"
    assert frames[-1]["response"]["message"]["id"] == message["id"]
    assert len(calls) == 1
    assert client.post("/api/chat", json={**request, "client_request_id": "new-turn"}).status_code == 409
    operation = client.get(f"/api/chat/operations/last-turn?conversation_id={cid}").json()
    assert operation["status"] == "completed"
    logs = repo.list_research_logs_for_session(sid)
    generated = next(log for log in logs if log.message_id == message["id"] and log.action_type.endswith("response_generated"))
    assert generated.payload["delivery_phase"] == "post_timer_closure"


def test_archiving_during_generation_still_blocks_delivery(client, monkeypatch):
    initialized = initialize_event(client)
    submitted = submit_task(client, initialized)
    repo = client.app.state.repository
    sid, cid = initialized["session_id"], submitted["conversation_id"]
    before = len(repo.list_messages(cid))

    async def generate(**kwargs):
        session = repo.get_session(sid)
        session.status = "archived"
        session.completion_reason = "admin_restart"
        repo.save_session(session)
        return ChatGenerationResult(response="不應寫入"), {}, kwargs["base_prompt"]

    monkeypatch.setattr(client.app.state.chat_service, "generate_validated_response", generate)
    response = client.post("/api/chat", json={"conversation_id": cid, "user_message": "test", "client_request_id": "archive-turn"})
    assert response.status_code == 409
    assert len(repo.list_messages(cid)) == before + 1
    assert all(message.content != "不應寫入" for message in repo.list_messages(cid))


def test_failed_last_turn_unblocks_closure_without_inventing_reply(client, monkeypatch):
    initialized = initialize_event(client)
    submitted = submit_task(client, initialized)
    repo = client.app.state.repository
    sid, cid = initialized["session_id"], submitted["conversation_id"]

    async def generate(**kwargs):
        session = repo.get_session(sid)
        session.timer_ends_at = utc_now() - timedelta(seconds=1)
        repo.save_session(session)
        raise TimeoutError("simulated")

    monkeypatch.setattr(client.app.state.chat_service, "generate_validated_response", generate)
    response = client.post("/api/chat", json={"conversation_id": cid, "user_message": "最後的疑問", "client_request_id": "failed-last"})
    assert response.status_code == 502
    state = client.get(f"/api/sessions/{sid}/state").json()
    assert not state["pending_final_response"]
    assert state["final_exchange"]["failed"]
    assert state["final_exchange"]["assistant_message"] is None
    assert state["closure"]["question_id"] == "q01"


def test_reply_finishing_during_state_load_is_not_lost(client, monkeypatch):
    initialized = initialize_event(client)
    submitted = submit_task(client, initialized)
    repo = client.app.state.repository
    sid, cid = initialized["session_id"], submitted["conversation_id"]
    session = repo.get_session(sid)
    session.timer_ends_at = utc_now() - timedelta(seconds=1)
    repo.save_session(session)
    learner = repo.add_message(ChatMessage(
        conversation_id=cid, sequence_index=repo.next_message_sequence(cid), speaker_type="learner",
        speaker_name="learner", content="最後的問題", operation_status="processing", client_request_id="race",
    ))
    original = repo.get_active_chat_operation

    def finish_then_check(conversation_id):
        assistant = repo.add_message(ChatMessage(
            conversation_id=cid, sequence_index=repo.next_message_sequence(cid), speaker_type="assistant",
            speaker_name="AI", content="剛完成的最後回覆", client_request_id="race",
            metadata={"delivered_after_deadline": True},
        ))
        repo.add_message(learner.model_copy(update={
            "operation_status": "completed", "metadata": {"response_message_id": assistant.id},
        }))
        return original(conversation_id)

    monkeypatch.setattr(repo, "get_active_chat_operation", finish_then_check)
    state = client.app.state.session_service.load_state(sid)
    assert not state.pending_final_response
    assert state.final_exchange.assistant_message == "剛完成的最後回覆"
