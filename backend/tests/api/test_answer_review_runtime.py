"""實際 API 與背景工作一起跑；慢觀察不得阻塞送出、恢復或下一回合。"""

import asyncio
import json
from itertools import count
from threading import Event
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest

from app.core.config import get_settings
from app.models.domain import ResearchLog, utc_now
from app.core.interaction_contract import build_interaction_runtime
from app.providers.llm.base import ChatGenerationResult
from app.services.answer_delivery_service import SYSTEM_FALLBACK
from tests.test_api import initialize_event, submit_task


@pytest.fixture
def delivery(client, monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_ANSWER_REVIEW_ENABLED", "true")
    monkeypatch.setenv("LLM_ANSWER_REVIEW_MODE", "before_delivery")
    monkeypatch.setenv("LLM_CONTENT_VALIDATION_ENABLED", "false")
    monkeypatch.setenv("LLM_REJECTION_LOG_PATH", str(tmp_path / "rejections.jsonl"))
    get_settings.cache_clear()
    provider = client.app.state.llm_provider
    serial = count(1)
    original = provider._llm_metadata
    def metadata(name):
        data = original(name)
        data["llm_call"]["correlation_id"] = f"call-{next(serial)}"
        return data
    monkeypatch.setattr(provider, "_llm_metadata", metadata)
    calls = []
    async def review(context):
        calls.append(context)
        response = context["candidate"]["response"]
        findings = [] if "PRIVATE BAD" not in response else [{
            "category": "early_answer_exposure", "severity": "violation", "excerpt": response,
            "explanation": "PRIVATE FINDING: 直接取代受測者的答案。"}]
        return {"findings": findings, "current_answer_stated": False,
                "llm_call": metadata("review_answer")["llm_call"]}
    monkeypatch.setattr(provider, "review_answer", review, raising=False)
    yield provider, calls
    get_settings.cache_clear()


@pytest.mark.parametrize("condition", ["no_ebl_no_roleplay", "ebl_no_roleplay", "no_ebl_roleplay", "ebl_roleplay"])
def test_delivery_repairs_unseen_draft_once_and_scope_is_correct(client, delivery, monkeypatch, condition):
    provider, calls = delivery
    with client:
        init = initialize_event(client, "法國大革命送出前檢查", condition)
        submitted = submit_task(client, init)
        assert len(calls) == (1 if condition.startswith("ebl_") else 0)
        cid = submitted["conversation_id"]
        original = provider.generate_chat_response
        generated = []
        async def generate(**kwargs):
            generated.append(kwargs["prompt"])
            result = await original(**kwargs)
            if len(generated) == 1:
                result.response = "PRIVATE BAD: 正解與完整理由。"
            return result
        monkeypatch.setattr(provider, "generate_chat_response", generate)
        request = {"conversation_id": cid, "user_message": "我不清楚。", "client_request_id": "repair"}
        response = client.post("/api/chat", json=request)
        assert response.status_code == 200, response.text
        ebl = condition.startswith("ebl_")
        assert len(generated) == (2 if ebl else 1)
        assert ("PRIVATE BAD" not in response.text) == ebl
        assert "answer_delivery" not in response.text
        if not ebl:
            return
        assert "NEVER shown" in generated[1] and "PRIVATE FINDING" in generated[1]
        assert not client.app.state.answer_review_service.tasks
        review_url = f"/api/admin/sessions/{init['session_id']}/research"
        records = client.get(review_url, headers={"x-admin-key": "test-admin"}).json()
        assert "PRIVATE BAD" in json.dumps(records)
        assert records["stats"]["llm_calls_total"] == 7  # judge + opening/review + two draft/review pairs
        assert records["stats"]["total_tokens"] == 7 * 18
        assert records["stats"]["assistant_messages"] == 2
        assert records["stats"]["completed_exchanges"] == 1
        count_before = len(calls)
        for path in (f"/api/conversations/{cid}", f"/api/sessions/{init['session_id']}/state",
                     f"/api/chat/operations/repair?conversation_id={cid}"):
            loaded = client.get(path)
            assert loaded.status_code == 200
            assert "PRIVATE BAD" not in loaded.text and "answer_delivery" not in loaded.text
        stream = client.post("/api/chat/stream", json=request)
        assert "PRIVATE BAD" not in stream.text and "answer_delivery" not in stream.text
        assert len(calls) == count_before
        assert client.get(review_url, headers={"x-admin-key": "test-admin"}).json()["stats"] == records["stats"]
        client.post("/api/chat", json={**request, "client_request_id": "next"})
        assert "PRIVATE BAD" not in generated[-1] and "PRIVATE FINDING" not in generated[-1]


@pytest.mark.parametrize("scenario", ["constrained", "all_rejected", "review_failed", "generation_failed", "deadline", "terminal"])
def test_delivery_fallback_never_advances_ebl_or_impersonates_a_persona(client, delivery, monkeypatch, scenario):
    provider, calls = delivery
    with client:
        init = initialize_event(client)
        submitted = submit_task(client, init)
        cid = submitted["conversation_id"]
        repo = client.app.state.repository
        attempt = repo.get_task_attempt(submitted["attempt_id"])
        condition = repo.get_condition_by_key("ebl_roleplay")
        history = repo.list_messages(cid)
        if scenario == "terminal":
            history[0].metadata.update(completion_status="final_answer_pending", disclosure_level="D4")
            repo.add_message(history[0])
        before = build_interaction_runtime(condition, attempt, history)
        generated, recovery_inputs = [], []
        async def generate(**kwargs):
            generated.append(kwargs)
            if scenario == "generation_failed":
                raise RuntimeError("injected outage")
            return ChatGenerationResult(response="PRIVATE BAD: 尚未修正的完整答案。",
                interaction_metadata={"dialogue_state": "RESOLVED", "completion_status": "resolved"},
                llm_metadata=provider._llm_metadata("generate_chat_response"))
        async def recovery(context):
            recovery_inputs.append(context)
            return ChatGenerationResult(response="PRIVATE BAD" if scenario == "all_rejected" else "你原先這樣判斷，是怎麼想的？",
                                        llm_metadata=provider._llm_metadata("recovery"))
        monkeypatch.setattr(provider, "generate_chat_response", generate)
        monkeypatch.setattr(provider, "generate_recovery_continuation", recovery, raising=False)
        if scenario in {"review_failed", "deadline"}:
            async def unavailable(context):
                if scenario == "deadline":
                    await asyncio.sleep(2)
                raise RuntimeError("injected review outage")
            monkeypatch.setattr(provider, "review_answer", unavailable)
        if scenario == "deadline":
            monkeypatch.setenv("LLM_ANSWER_DELIVERY_TIMEOUT_SECONDS", "0.04")
            get_settings.cache_clear()
        response = client.post("/api/chat", json={"conversation_id": cid, "user_message": "仍不清楚", "client_request_id": "fallback"})
        assert response.status_code == 200, response.text
        data = response.json()
        system = scenario != "constrained"
        if system:
            assert data["response"] == SYSTEM_FALLBACK
            assert data["assistant_name"] == "系統提示" and data["selected_persona"] is None
            assert data["message"]["persona_id"] is None and data["message"]["speaker_type"] == "assistant"
        else:
            assert data["message"]["speaker_type"] == "persona"
            assert len(generated) == 3 and len(recovery_inputs) == 1
        assert "PRIVATE BAD" not in response.text
        after = build_interaction_runtime(condition, attempt, repo.list_messages(cid))
        assert after == before
        assert len(recovery_inputs) == (1 if scenario in {"constrained", "all_rejected"} else 0)
        if recovery_inputs:
            payload = json.dumps(recovery_inputs[0])
            assert "expected_answer" not in payload and "reasoning_criteria" not in payload and "PRIVATE BAD" not in payload
        records = client.get(f"/api/admin/sessions/{init['session_id']}/research", headers={"x-admin-key": "test-admin"}).json()
        assert records["stats"]["assistant_messages"] == (1 if system else 2)
        assert records["stats"]["completed_exchanges"] == (0 if system else 1)
        assert records["messages"][-1]["metadata"]["answer_delivery"]["state_held"] is True
        if scenario in {"generation_failed", "review_failed", "deadline"}:
            assert records["stats"]["cost_usage_complete"] is False
        else:
            assert records["stats"]["llm_calls_total"] == (9 if scenario == "terminal" else 11)
        last_prompt = records["prompt_records"][-1]["prompt"]
        if system:
            assert last_prompt == ""
        else:
            assert "Only voice, question and learner context" in last_prompt
            assert "reasoning_criteria" not in last_prompt and "PRIVATE BAD" not in last_prompt
        from app.services.prompt_service import PromptService
        assert SYSTEM_FALLBACK not in PromptService._conversation_history(repo.list_messages(cid))


@pytest.mark.parametrize("change", ["none", "delete", "expire"])
def test_pending_review_is_not_public_and_late_response_cannot_restore_activity(client, delivery, monkeypatch, change):
    provider, calls = delivery
    with client:
        init = initialize_event(client)
        submitted = submit_task(client, init)
        cid, sid = submitted["conversation_id"], init["session_id"]
        repo = client.app.state.repository
        entered, release = Event(), Event()
        original_review = provider.review_answer
        async def slow(context):
            entered.set()
            while not release.is_set():
                await asyncio.sleep(0.005)
            return await original_review(context)
        monkeypatch.setattr(provider, "review_answer", slow)
        with ThreadPoolExecutor() as pool:
            request = {"conversation_id": cid, "user_message": "還不太清楚", "client_request_id": "slow"}
            future = pool.submit(client.post, "/api/chat", json=request)
            assert entered.wait(3)
            try:
                loaded = client.get(f"/api/conversations/{cid}")
                assert loaded.status_code == 200, loaded.text
                assert len(loaded.json()["messages"]) == 2  # opening + durable learner, no candidate
                assert not future.done()
                assert "answer_delivery" not in loaded.text
                assert client.post("/api/chat", json=request).status_code == 409
                assert client.post("/api/chat", json={**request, "client_request_id": "other"}).status_code == 409
                if change == "delete":
                    repo.messages.pop(cid, None)
                    repo.conversations.pop(cid)
                elif change == "expire":
                    session = repo.get_session(sid)
                    session.timer_ends_at = utc_now() - timedelta(seconds=1)
                    repo.save_session(session)
            finally:
                release.set()
            result = future.result(5)
            assert result.status_code == (200 if change == "none" else 409), result.text
        if change == "delete":
            assert repo.get_conversation(cid) is None and repo.list_messages(cid) == []
        elif change == "expire":
            assert len(repo.list_messages(cid)) == 2


def test_slow_review_does_not_block_chat_or_repeat_on_reload_and_admin_usage_is_deduplicated(client, monkeypatch):
    release = Event()
    calls = []
    async def review(context):
        calls.append(context)
        call_id = f"review-{len(calls)}"
        async def wait_release():
            while not release.is_set():
                await asyncio.sleep(0.005)
        await asyncio.wait_for(wait_release(), 10)
        return {"findings": [{"category": "early_answer_exposure", "severity": "concern",
                              "excerpt": context["candidate"]["response"], "explanation": "PRIVATE REVIEW EXPLANATION"}],
                "current_answer_stated": None, "llm_call": {
                    "correlation_id": call_id, "task_name": "review_answer", "provider": "fake",
                    "model": "fake", "prompt_tokens": 10, "completion_tokens": 2,
                    "total_tokens": 12, "estimated_cost_usd": 0.0001,
                }}
    client.app.state.answer_review_service.provider.review_answer = review
    provider = client.app.state.llm_provider
    original_metadata = provider._llm_metadata
    serial = count(1)
    # 舊 fake 每個功能固定同一 ID；多輪測試必須像正式 runner 一樣每次呼叫有獨立 ID。
    def unique_metadata(task_name):
        metadata = original_metadata(task_name)
        metadata["llm_call"]["correlation_id"] = f"generation-{next(serial)}"
        return metadata
    monkeypatch.setattr(provider, "_llm_metadata", unique_metadata)
    monkeypatch.setenv("LLM_ANSWER_REVIEW_ENABLED", "true")
    monkeypatch.setenv("LLM_CONTENT_VALIDATION_ENABLED", "false")
    get_settings.cache_clear()
    with client:
        initialized = initialize_event(client, "法國大革命背景觀察測試", "ebl_no_roleplay")
        submitted = submit_task(client, initialized)
        cid, sid = submitted["conversation_id"], initialized["session_id"]
        first = {"conversation_id": cid, "user_message": "我仍不清楚。", "client_request_id": "review-turn-1"}
        response = client.post("/api/chat", json=first)
        assert response.status_code == 200, response.text
        second = client.post("/api/chat", json={**first, "user_message": "請接著說。", "client_request_id": "review-turn-2"})
        assert second.status_code == 200, second.text
        assert not release.is_set()
        repository = client.app.state.repository
        for payload in (submitted, response.json(), second.json()):
            assert "answer_review" not in json.dumps(payload)
        async def wait_started():
            while len(calls) < 3:
                await asyncio.sleep(0.005)
        client.portal.call(asyncio.wait_for, wait_started(), 2)
        assert all(m.metadata["answer_review"]["status"] == "pending"
                   for m in repository.list_messages(cid) if m.speaker_type != "learner")
        # 同一請求、串流重連、載入舊對話均不得多排觀察。
        for path in (f"/api/conversations/{cid}", f"/api/sessions/{sid}/state",
                     f"/api/chat/operations/review-turn-1?conversation_id={cid}"):
            loaded = client.get(path)
            assert loaded.status_code == 200
            assert "answer_review" not in loaded.text
        assert client.post("/api/chat", json=first).json()["response"] == response.json()["response"]
        stream = client.post("/api/chat/stream", json=first)
        assert stream.status_code == 200
        assert "answer_review" not in stream.text and "已通過檢查" not in stream.text
        assert len(calls) == 3
        assert all("PRIVATE REVIEW" not in json.dumps(context) for context in calls)
        records_url = f"/api/admin/sessions/{sid}/research"
        pending = client.get(records_url, headers={"x-admin-key": "test-admin"}).json()
        assert pending["stats"]["cost_usage_complete"] is False
        assert pending["messages"][0]["metadata"]["answer_review"]["status"] == "pending"
        release.set()
        async def finish():
            await asyncio.gather(*list(client.app.state.answer_review_service.tasks.values()))
        client.portal.call(finish)
        records = client.get(records_url, headers={"x-admin-key": "test-admin"}).json()
        assert records["stats"]["total_messages"] == 5
        assert records["stats"]["completed_exchanges"] == 2
        assert records["stats"]["llm_calls_total"] == 7
        assert records["stats"]["total_tokens"] == 4 * 18 + 3 * 12
        assert records["stats"]["estimated_cost_usd"] == 0.0007
        review_call = records["messages"][0]["metadata"]["answer_review"]["llm_call"]
        repository.log_research(ResearchLog(session_id=sid, event_id=initialized["event_id"],
            action_type="response_generation_failed", payload={"llm_call": review_call}))
        reloaded = client.get(records_url, headers={"x-admin-key": "test-admin"}).json()
        assert reloaded["stats"] == records["stats"]
        assert "PRIVATE REVIEW EXPLANATION" in json.dumps(records)
        assert "PRIVATE REVIEW" not in client.get(f"/api/conversations/{cid}").text
        assert all("answer_review" not in record["prompt"] for record in records["prompt_records"])
        continued = client.post("/api/chat", json={**first, "client_request_id": "after-review"})
        assert continued.status_code == 200
        client.portal.call(finish)
        latest = client.get(records_url, headers={"x-admin-key": "test-admin"}).json()
        assert all("PRIVATE REVIEW" not in record["prompt"] for record in latest["prompt_records"])
    get_settings.cache_clear()
