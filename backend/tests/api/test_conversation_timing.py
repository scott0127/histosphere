"""Exercise persisted timing through real chat endpoints, including safe retries."""

from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.models.domain import ChatMessage
from app.services import response_timing
from tests.api.test_runtime_safety import admin_initialize, submit_and_poll


def test_chat_records_full_response_timing_and_replay_preserves_it(client, monkeypatch):
    initialized = admin_initialize(client, "對話計時測試", "no_ebl_no_roleplay")
    submitted = submit_and_poll(client, initialized)
    repository = client.app.state.repository
    conversation_id = submitted["conversation_id"]
    opening = repository.list_messages(conversation_id)[0]
    opening_timing = opening.metadata["opening_timing"]
    assert opening_timing["status"] == "completed"
    assert opening_timing["response_latency_ms"] >= 0
    assert opening_timing["response_completed_at"]
    assert opening.metadata["learning_target_question_id"] == opening.metadata["target_question_id"]

    clock = [100.0]
    monkeypatch.setattr(response_timing, "perf_counter", lambda: clock[0])
    original = client.app.state.llm_provider.generate_chat_response

    async def timed_response(**kwargs):
        clock[0] += 2.25
        return await original(**kwargs)

    client.app.state.llm_provider.generate_chat_response = timed_response
    payload = {
        "conversation_id": conversation_id,
        "user_message": "代表們為何還要集會？",
        "client_request_id": "timed-success",
    }
    first = client.post("/api/chat", json=payload)
    assert first.status_code == 200
    timing = first.json()["message"]["metadata"]["exchange_timing"]
    assert timing["status"] == "completed"
    assert timing["attempt_number"] == 1
    assert timing["response_latency_ms"] == 2250
    assert timing["original_request_started_at"] == timing["request_started_at"]
    learner = repository.get_learner_message_by_request(conversation_id, "timed-success")
    assert learner.metadata["exchange_timing"] == timing
    assert learner.metadata["learning_target_question_id"] == first.json()["message"]["metadata"]["target_question_id"]

    clock[0] += 120
    repeated = client.post("/api/chat", json=payload)
    assert repeated.status_code == 200
    assert repeated.json()["message"]["metadata"]["exchange_timing"] == timing
    assert repeated.json()["message"]["id"] == first.json()["message"]["id"]


def test_retry_preserves_first_send_but_excludes_retry_idle_from_processing(client, monkeypatch):
    initialized = admin_initialize(client, "重試計時測試", "no_ebl_no_roleplay")
    submitted = submit_and_poll(client, initialized)
    repository = client.app.state.repository
    conversation_id = submitted["conversation_id"]
    clock = [100.0]
    wall = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    monkeypatch.setattr(response_timing, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(response_timing, "utc_now", lambda: wall[0])
    original = client.app.state.llm_provider.generate_chat_response

    async def failed_response(**kwargs):
        clock[0] += 3
        wall[0] += timedelta(seconds=3)
        raise TimeoutError("simulated timeout")

    client.app.state.llm_provider.generate_chat_response = failed_response
    payload = {
        "conversation_id": conversation_id,
        "user_message": "同一則訊息重試。",
        "client_request_id": "timed-retry",
    }
    assert client.post("/api/chat", json=payload).status_code == 502
    failed = repository.get_learner_message_by_request(conversation_id, "timed-retry")
    failed_timing = failed.metadata["exchange_timing"]
    assert failed_timing["status"] == "failed"
    assert failed_timing["response_completed_at"] is None
    assert failed_timing["response_latency_ms"] == 3000
    failure_log = next(log for log in repository.list_research_logs()
                       if log.message_id == failed.id and log.action_type == "response_generation_failed")
    assert failure_log.payload["exchange_timing"] == failed_timing

    clock[0] += 600
    wall[0] += timedelta(seconds=600)

    async def successful_retry(**kwargs):
        clock[0] += 2
        wall[0] += timedelta(seconds=2)
        return await original(**kwargs)

    client.app.state.llm_provider.generate_chat_response = successful_retry
    retried = client.post("/api/chat", json={**payload, "retry_failed": True})
    assert retried.status_code == 200
    timing = retried.json()["message"]["metadata"]["exchange_timing"]
    assert timing["status"] == "completed"
    assert timing["attempt_number"] == 2
    assert timing["response_latency_ms"] == 2000
    assert timing["original_request_started_at"] == failed_timing["original_request_started_at"]
    assert timing["request_started_at"] != timing["original_request_started_at"]
    assert (datetime.fromisoformat(timing["response_completed_at"])
            - datetime.fromisoformat(timing["original_request_started_at"])).total_seconds() == 605
    assert repository.get_learner_message_by_request(conversation_id, "timed-retry").id == failed.id
    assert failure_log.payload["exchange_timing"]["status"] == "failed"


def test_restart_marks_unknown_processing_duration_without_fabricating_latency(client):
    initialized = admin_initialize(client, "重啟計時測試", "no_ebl_no_roleplay")
    submitted = submit_and_poll(client, initialized)
    repository = client.app.state.repository
    timing, _ = response_timing.start_response_timing()
    interrupted = repository.add_message(ChatMessage(
        conversation_id=submitted["conversation_id"], speaker_type="learner", speaker_name="learner",
        sequence_index=repository.next_message_sequence(submitted["conversation_id"]),
        content="程序中斷的回合", client_request_id="timed-interrupted", operation_status="processing",
        metadata={"response_status": "pending", "exchange_timing": timing},
    ))
    assert client.app.state.chat_service.recover_interrupted_operations() == 1
    saved = repository.get_message(interrupted.id)
    assert saved.operation_status == "failed"
    assert saved.metadata["exchange_timing"]["status"] == "interrupted"
    assert saved.metadata["exchange_timing"]["response_latency_ms"] is None
    assert saved.metadata["exchange_timing"]["response_completed_at"] is None


def test_processing_duration_uses_monotonic_clock_when_wall_clock_changes(monkeypatch):
    clock = [10.0]
    wall = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    monkeypatch.setattr(response_timing, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(response_timing, "utc_now", lambda: wall[0])
    timing, started_clock = response_timing.start_response_timing()
    wall[0] -= timedelta(hours=1)
    clock[0] += 4.5
    finished = response_timing.finish_response_timing(timing, started_clock)
    assert finished["response_latency_ms"] == 4500


def test_opening_and_chat_timings_include_synchronous_answer_review(client, monkeypatch):
    monkeypatch.setenv("LLM_ANSWER_REVIEW_ENABLED", "true")
    monkeypatch.setenv("LLM_ANSWER_REVIEW_MODE", "before_delivery")
    monkeypatch.setenv("LLM_CONTENT_VALIDATION_ENABLED", "false")
    get_settings.cache_clear()
    provider = client.app.state.llm_provider
    clock = [100.0]
    monkeypatch.setattr(response_timing, "perf_counter", lambda: clock[0])

    async def review(context):
        clock[0] += 5
        return {"findings": [], "current_answer_stated": False,
                "llm_call": provider._llm_metadata("review_answer")["llm_call"]}

    monkeypatch.setattr(provider, "review_answer", review, raising=False)
    initialized = admin_initialize(client, "審查計時測試", "ebl_no_roleplay")
    submitted = submit_and_poll(client, initialized)
    messages = client.app.state.repository.list_messages(submitted["conversation_id"])
    assert messages[0].metadata["opening_timing"]["response_latency_ms"] == 5000
    original = provider.generate_chat_response

    async def generate(**kwargs):
        clock[0] += 2
        return await original(**kwargs)

    monkeypatch.setattr(provider, "generate_chat_response", generate)
    response = client.post("/api/chat", json={
        "conversation_id": submitted["conversation_id"], "user_message": "我還不清楚。",
    })
    assert response.status_code == 200
    assert response.json()["message"]["metadata"]["exchange_timing"]["response_latency_ms"] == 7000
    get_settings.cache_clear()
