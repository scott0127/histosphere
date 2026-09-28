"""零費用驗證觀察管線與故障隔離；不以 mock 結果聲稱模型語意準確。"""

import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from app.core.answer_review import AnswerReviewPayload, pending_answer_review
from app.core.config import Settings, get_settings
from app.core.interaction_contract import build_interaction_runtime, resolve_interaction_metadata
from app.db.in_memory import InMemoryRepository
from app.db.supabase_repository import SupabaseRepository
from app.models.domain import ChatMessage, Event, ResearchLog
from app.providers.llm.base import ChatGenerationResult
from app.providers.llm.json_runner import LLMCompletion, LLMRunError
from app.providers.llm.litellm_provider import LiteLLMProvider
from app.services.answer_review_service import AnswerReviewService
from app.services.completion_validation import validate_completion_candidate
from app.services.answer_delivery_service import deliver_answer, SYSTEM_FALLBACK
from tests.unit.test_interaction_contract import _condition, _multi_error_attempt


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv("LLM_ANSWER_REVIEW_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def message():
    return ChatMessage(conversation_id="conversation", speaker_type="assistant", speaker_name="AI",
                       content="按人數與按等級，各如何計算？", metadata={"completion_status": "continue"})


def prepared(service, code="02", history=None):
    msg = message()
    attempt = _multi_error_attempt()
    context = service.prepare(msg, runtime=build_interaction_runtime(_condition(code), attempt, []),
                              event=Event(canonical_name="法國大革命"), attempt=attempt,
                              history=history or [], learner_message="我仍不清楚。")
    service.repository.add_message(msg)
    return msg, context


def test_review_scope_and_frozen_input_are_shared_without_generator_self_report(enabled):
    service = AnswerReviewService(InMemoryRepository(), None)
    contexts = []
    for code in ("01", "02", "03", "04"):
        msg, context = prepared(service, code)
        if code in ("01", "03"):
            assert context is None and "answer_review" not in msg.metadata
        else:
            contexts.append(context)
            assert msg.metadata["answer_review"]["status"] == "pending"
            assert "provider_fidelity_flags" not in json.dumps(context)
    assert contexts[0] == contexts[1]
    runtime = build_interaction_runtime(_condition("02"), None, [])
    assert service.prepare(message(), runtime=runtime, event=Event(canonical_name="test"),
                           attempt=None, history=[], learner_message="") is None
    old = message()
    old.metadata["answer_review"] = {"findings": "PRIVATE REVIEW"}
    msg, frozen = prepared(service, history=[old])
    old.content = "changed later"
    assert frozen["history"][0]["content"] != old.content
    assert "PRIVATE REVIEW" not in json.dumps(frozen)
    assert pending_answer_review(frozen) == msg.metadata["answer_review"]


def test_legacy_options_come_from_the_original_session_snapshot(enabled):
    repo = InMemoryRepository()
    attempt = _multi_error_attempt()
    attempt.judgement_payload["question_results"][0]["question_type"] = "multiple_choice"
    frozen_options = [{"value": "A", "label": "按等級"}, {"value": "B", "label": "按人數"}]
    repo.log_research(ResearchLog(
        session_id=attempt.session_id, event_id=attempt.event_id, task_id=attempt.task_id,
        action_type="session_material_snapshot", payload={"materials": {"task": {
            "evaluation_payload": {"questions": [{"id": "q01", "options": frozen_options}]},
        }}},
    ))
    msg = message()
    context = AnswerReviewService(repo, None).prepare(
        msg, runtime=build_interaction_runtime(_condition("04"), attempt, []),
        event=Event(canonical_name="法國大革命"), attempt=attempt, history=[], learner_message="",
    )
    assert context["question_results"][0]["options"] == frozen_options
    assert "options" not in attempt.judgement_payload["question_results"][0]
    frozen_options[0]["label"] = "後來改過的選項"
    assert context["question_results"][0]["options"][0]["label"] == "按等級"


def test_delivery_cancellation_is_recorded_and_restart_never_calls_model(enabled, monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_REJECTION_LOG_PATH", str(tmp_path / "audit.jsonl"))
    repo = InMemoryRepository()
    attempt = _multi_error_attempt()
    # 使用與正式關聯一致的 fixture；只需要讓私有紀錄可歸屬。
    monkeypatch.setattr(repo, "get_session", lambda _: True)
    monkeypatch.setattr(repo, "get_task_attempt", lambda _: attempt)
    async def scenario():
        entered = asyncio.Event()
        async def review(context):
            entered.set()
            await asyncio.Event().wait()
        service = AnswerReviewService(repo, SimpleNamespace(review_answer=review))
        async def generate(prompt):
            return ChatGenerationResult(response="你原先如何作出判斷？", llm_metadata={"llm_call": {
                "correlation_id": "generation", "total_tokens": 10, "estimated_cost_usd": 0.001}})
        job = asyncio.create_task(deliver_answer(review_service=service, generate=generate,
            runtime=build_interaction_runtime(_condition("02"), attempt, []),
            event=Event(id=attempt.event_id, canonical_name="法國大革命"), attempt=attempt,
            persona=None, history=[], learner_message="不清楚", base_prompt="canonical"))
        await asyncio.wait_for(entered.wait(), 1)
        assert len(repo.list_pending_answer_deliveries()) == 1
        job.cancel()
        with pytest.raises(asyncio.CancelledError):
            await job
        assert repo.list_research_logs()[0].payload["candidate"]["status"] == "interrupted"
        # 模擬硬中斷留下的待審紀錄，startup 只改狀態，不重跑付費呼叫。
        log = repo.list_research_logs()[0]
        log.payload["candidate"]["status"] = "review_pending"
        repo.log_research(log)
        service.recover_interrupted()
        assert not repo.list_pending_answer_deliveries()
        assert repo.list_research_logs()[0].payload["candidate"]["failure_type"] == "backend_restart"
    asyncio.run(scenario())


def test_delivery_concern_is_not_a_violation_and_audit_failure_does_not_drop_accepted_reply(enabled, monkeypatch):
    monkeypatch.setenv("LLM_CONTENT_VALIDATION_ENABLED", "false")
    get_settings.cache_clear()
    repo = InMemoryRepository()
    attempt = _multi_error_attempt()
    monkeypatch.setattr(repo, "get_session", lambda _: True)
    monkeypatch.setattr(repo, "get_task_attempt", lambda _: attempt)
    def fail(*args, **kwargs):
        raise OSError("injected storage failure")
    monkeypatch.setattr(repo, "log_research", fail)
    monkeypatch.setattr("app.services.answer_delivery_service.record_rejected_generation", fail)
    async def review(context):
        return {"findings": [{"category": "early_answer_exposure", "severity": "concern",
                              "excerpt": context["candidate"]["response"], "explanation": "語意尚不確定"}],
                "current_answer_stated": None}
    async def generate(prompt):
        return ChatGenerationResult(response="按人數與按等級，各如何計算？")
    generation, metadata, _ = asyncio.run(deliver_answer(
        review_service=AnswerReviewService(repo, SimpleNamespace(review_answer=review)), generate=generate,
        runtime=build_interaction_runtime(_condition("02"), attempt, []),
        event=Event(id=attempt.event_id, canonical_name="法國大革命"), attempt=attempt,
        persona=None, history=[], learner_message="", base_prompt="canonical"))
    assert generation.response != SYSTEM_FALLBACK
    assert metadata["answer_delivery"]["outcome"] == "accepted"
    candidate = metadata["answer_delivery"]["candidates"][0]
    assert candidate["persistence_failure_type"] == "OSError"
    assert candidate["audit_copy_failure_type"] == "OSError"
    assert metadata["answer_review"]["findings"][0]["severity"] == "concern"


@pytest.mark.parametrize("enforce_content", [False, True])
@pytest.mark.parametrize("code", ["01", "02", "03", "04"])
def test_self_reported_answer_flags_never_become_independent_findings_or_retries(code, enforce_content, monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_content_validation_enabled", enforce_content)
    runtime = build_interaction_runtime(_condition(code), _multi_error_attempt(), [])
    flags = ["early_answer_exposure", "next_answer_exposure", "corrective_answer_missing", "corrective_feedback_missing"]
    result = validate_completion_candidate(runtime=runtime, persona_context=None, is_opening=True,
        generation=ChatGenerationResult(response="按人數和按等級的差異是什麼？", interaction_metadata={
            "dialogue_state": "NOTICE_ERROR", "dialogue_move": "error_awareness_prompt",
            "disclosure_level": "D0", "fidelity_flags": flags,
        }))
    assert set(result.metadata["provider_fidelity_flags"]) == set(flags)
    assert not set(flags) & set(result.metadata["fidelity_flags"])
    assert not set(flags) & set(result.metadata["content_validation_flags"])
    assert result.retry_required is False


@pytest.mark.parametrize("code", ["02", "04"])
def test_resolved_alone_cannot_skip_an_unfinished_error(code):
    condition, attempt = _condition(code), _multi_error_attempt()
    runtime = replace(build_interaction_runtime(condition, attempt, []),
                      previous_state="SELF_CORRECT", allowed_states=("SELF_CORRECT", "RESOLVED"),
                      previous_disclosure_level="D2")
    result = resolve_interaction_metadata(runtime, {
        "dialogue_state": "RESOLVED", "dialogue_move": "resolution", "completion_status": "resolved",
        "disclosure_level": "D2", "resolution_self_corrected": True,
    }, "好，下一題。")
    assert result["dialogue_state"] == "SELF_CORRECT"
    assert result["completion_status"] == "continue"
    assert result["next_target_started"] is False
    assert "incomplete_resolution_criteria" in result["fidelity_flags"]
    saved = message().model_copy(update={"metadata": result})
    assert build_interaction_runtime(condition, attempt, [saved]).target.question_id == "q01"


@pytest.mark.parametrize("change", [None, "delete", "edit", "cancel", "timeout", "write_failure"])
def test_background_completion_failure_and_reset_do_not_change_saved_chat(enabled, monkeypatch, change):
    async def run():
        gate, started = asyncio.Event(), asyncio.Event()
        calls = []
        async def review(context):
            calls.append(context)
            started.set()
            await gate.wait()
            if change == "timeout":
                raise TimeoutError()
            return {"findings": [{"category": "early_answer_exposure", "severity": "concern",
                                  "excerpt": context["candidate"]["response"], "explanation": "test finding"}],
                    "current_answer_stated": False,
                    "llm_call": {"correlation_id": "review-call", "total_tokens": 42, "estimated_cost_usd": 0.001}}
        repo = InMemoryRepository()
        service = AnswerReviewService(repo, SimpleNamespace(review_answer=review))
        msg, context = prepared(service)
        original = msg.model_dump()
        service.schedule(msg, context)
        service.schedule(msg, context)
        await asyncio.wait_for(started.wait(), 2)
        assert repo.get_message(msg.id).content == msg.content
        assert repo.get_message(msg.id).metadata["answer_review"]["status"] == "pending"
        if change == "delete":
            repo.messages.pop(msg.conversation_id)
        elif change == "edit":
            repo.add_message(msg.model_copy(update={"content": "edited"}))
        elif change == "write_failure":
            monkeypatch.setattr(repo, "finish_answer_review", lambda *args: (_ for _ in ()).throw(OSError()))
        # 本機紀錄故障也不能吞掉已存訊息或成功審查結果。
        monkeypatch.setattr("app.services.answer_review_service.record_rejected_generation",
                            lambda **kwargs: (_ for _ in ()).throw(OSError()))
        tasks = list(service.tasks.values())
        if change == "cancel":
            await service.close()
        else:
            gate.set()
            await asyncio.gather(*tasks)
        assert len(calls) == 1
        current = repo.get_message(msg.id)
        if change == "delete":
            assert current is None
        elif change in {"edit", "write_failure"}:
            assert current.metadata["answer_review"]["status"] == "pending"
            assert current.content == ("edited" if change == "edit" else msg.content)
        else:
            report = current.metadata.pop("answer_review")
            before = deepcopy(original)
            before["metadata"].pop("answer_review")
            assert current.model_dump() == before
            assert report["status"] == ("unavailable" if change in {"cancel", "timeout"} else "completed")
            if change == "cancel":
                assert report["failure_type"] == "interrupted"
    asyncio.run(run())


def test_restart_marks_pending_as_interrupted_without_paid_calls(enabled):
    repo = InMemoryRepository()
    service = AnswerReviewService(repo, None)
    msg, _ = prepared(service)
    service.recover_interrupted()
    report = repo.get_message(msg.id).metadata["answer_review"]
    assert report["status"] == "unavailable" and report["failure_type"] == "interrupted"
    assert service.tasks == {}
    service.recover_interrupted()
    assert repo.get_message(msg.id).metadata["answer_review"] == report


def test_supabase_review_updates_conditionally_and_never_upserts(monkeypatch):
    repo = SupabaseRepository("http://example.invalid", "fake-key")
    msg = message()
    base = pending_answer_review({"candidate": {"response": msg.content}})
    msg.metadata["answer_review"] = base
    monkeypatch.setattr(repo, "get_message", lambda _id: msg)
    calls = []
    def request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return []  # 模擬查詢後遭刪除；PATCH 不可把原訊息重新建立。
    monkeypatch.setattr(repo, "_request", request)
    assert repo.finish_answer_review(msg.id, base, {**base, "status": "completed"}) is False
    method, path, kwargs = calls[0]
    assert method == "PATCH" and path == "messages"
    assert kwargs["params"]["content"] == f"eq.{msg.content}"
    assert kwargs["params"]["metadata->answer_review->>status"] == "eq.pending"
    assert kwargs["params"]["metadata->answer_review->>input_sha256"] == "eq." + base["input_sha256"]
    assert kwargs["json"] == {"metadata": {**msg.metadata, "answer_review": {**base, "status": "completed"}}}
    assert repo.list_pending_answer_reviews() == []
    assert repo.list_pending_answer_deliveries() == []
    pending_log = ResearchLog(action_type="answer_delivery_candidate", payload={"candidate": {"status": "review_pending"}})
    monkeypatch.setattr(repo, "_request", lambda method, path, **kw:
                        [msg.model_dump(mode="json")] if path == "messages" else [pending_log.model_dump(mode="json")])
    assert repo.list_pending_answer_reviews() == [msg]
    assert repo.list_pending_answer_deliveries() == [pending_log]
    repo.client.close()


@pytest.mark.parametrize("bad_excerpt,bad_authorization", [(False, False), (True, False), (False, True)])
def test_review_adapter_schema_quotes_usage_and_audit_file_failure(monkeypatch, bad_excerpt, bad_authorization):
    provider = LiteLLMProvider(Settings(llm_model="gpt-5.6-terra", openai_api_key="fake-key"))
    calls = []
    async def complete(candidate, **kwargs):
        calls.append(kwargs)
        assert candidate.display_model == "gpt-5.6-terra"
        assert "Do not evaluate persona style" in kwargs["system_prompt"]
        return LLMCompletion(content=json.dumps({
            "findings": [{"category": "early_answer_exposure", "severity": "violation",
                          "excerpt": "invented" if bad_excerpt else "應選 B。", "explanation": "直接選定答案。"}],
            "current_answer_stated": True,
        }), prompt_tokens=100, completion_tokens=20, total_tokens=120, estimated_cost_usd=0.001)
    monkeypatch.setattr(provider.runner, "_complete", complete)
    for writer in ("record_llm_usage", "record_rejected_generation"):
        monkeypatch.setattr(f"app.providers.llm.json_runner.{writer}",
                            lambda **kwargs: (_ for _ in ()).throw(OSError("disk unavailable")))
    context = {"candidate": {"response": "應選 B。"}, "runtime": {"corrective_feedback_required": bad_authorization}}
    if bad_excerpt or bad_authorization:
        with pytest.raises(LLMRunError) as failure:
            asyncio.run(provider.review_answer(context))
        assert failure.value.metadata.total_tokens == 240
        assert len(calls) == 2  # 一次有限格式修復，仍失敗不能冒充通過。
    else:
        result = asyncio.run(provider.review_answer(context))
        AnswerReviewPayload.model_validate({k: v for k, v in result.items() if k != "llm_call"})
        assert result["llm_call"]["total_tokens"] == 120
        assert result["llm_call"]["audit_write_failures"] == ["OSError", "OSError"]
        assert len(calls) == 1
