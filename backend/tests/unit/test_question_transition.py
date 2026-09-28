"""驗證完成進度不受銜接觀察阻擋；不把 mock 結果當成 LLM 語意效度。"""

import asyncio
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from app.core.answer_review import AnswerReviewPayload, confirms_next_target_transition
from app.core.config import Settings, get_settings
from app.core.interaction_contract import INTERACTION_POLICY_VERSION, build_interaction_runtime, resolve_interaction_metadata
from app.db.in_memory import InMemoryRepository
from app.models.domain import ChatMessage, Event
from app.providers.llm.base import ChatGenerationResult
from app.providers.llm.json_runner import LLMCompletion
from app.providers.llm.litellm_provider import LiteLLMProvider
from app.services.answer_delivery_service import deliver_answer
from app.services.answer_review_service import AnswerReviewService
from tests.unit.test_interaction_contract import _condition, _multi_error_attempt


SAME_QUESTION = "這一題你已修正。下一次還能再想想這一題。"
NEXT_QUESTION = "這一題你已修正。我們改談財政危機如何影響革命爆發，你原先為何認為沒有影響？"
NEXT_EXCERPT = "我們改談財政危機如何影響革命爆發，你原先為何認為沒有影響？"


def closing_runtime(code="02", restatement=False):
    runtime = build_interaction_runtime(_condition(code), _multi_error_attempt(), [])
    return replace(
        runtime,
        previous_state="SELF_CORRECT" if restatement else "REFLECT",
        allowed_states=("RESOLVED",) if restatement else ("REFLECT", "SELF_CORRECT", "RESOLVED"),
        previous_disclosure_level="D4" if restatement else "D1",
        previous_completion_status="corrective_resolution_pending" if restatement else "continue",
    )


def closing_metadata(restatement=False):
    return {
        "dialogue_state": "RESOLVED",
        "dialogue_move": "corrective_feedback" if restatement else "resolution",
        "disclosure_level": "D4" if restatement else "D1",
        "completion_status": "feedback_completed" if restatement else "resolved",
        "resolution_error_recognized": not restatement,
        "resolution_error_reflected": not restatement,
        "resolution_self_corrected": not restatement,
    }


@pytest.mark.parametrize("text", [SAME_QUESTION, NEXT_QUESTION])
def test_generation_metadata_or_connector_cannot_confirm_a_transition(text):
    runtime = closing_runtime()
    metadata = resolve_interaction_metadata(runtime, {
        **closing_metadata(), "next_target_started": True, "next_target_question_id": "forged",
    }, text)
    assert metadata["completion_status"] == "resolved"
    assert metadata["next_target_transition_required"] is True
    assert metadata["next_target_question_id"] == "q02"
    assert metadata["next_target_started"] is False
    assert "next_target_transition_missing" not in metadata["fidelity_flags"]
    saved = ChatMessage(conversation_id="test", speaker_type="assistant", speaker_name="AI",
                        content=text, metadata=metadata)
    resumed = build_interaction_runtime(_condition("02"), _multi_error_attempt(), [saved])
    assert resumed.target.question_id == "q02"
    assert resumed.previous_state is None  # 審查停用／背景觀察時，下輪正式引入新題。


@pytest.mark.parametrize("code", ["02", "04"])
@pytest.mark.parametrize("restatement", [False, True])
@pytest.mark.parametrize("introduces_next", [False, True])
def test_completion_advances_without_requiring_a_verbal_transition(
    code, restatement, introduces_next, monkeypatch, tmp_path,
):
    monkeypatch.setattr(get_settings(), "llm_content_validation_enabled", False)
    monkeypatch.setenv("LLM_REJECTION_LOG_PATH", str(tmp_path / "review.jsonl"))
    attempt, runtime = _multi_error_attempt(), closing_runtime(code, restatement)
    generated, reviewed = [], []

    async def generate(prompt):
        generated.append(prompt)
        return ChatGenerationResult(
            response=NEXT_QUESTION if introduces_next else SAME_QUESTION,
            interaction_metadata=closing_metadata(restatement),
        )

    async def review(context):
        reviewed.append(context)
        assert context["runtime"]["next_target_transition_required"] is True
        assert context["next_target"]["question_id"] == "q02"
        # 假審查輸出是固定測試證據：第一句仍談本題，第二句明確邀請思考財政問題。
        introduced = context["candidate"]["response"] == NEXT_QUESTION
        return AnswerReviewPayload(
            findings=[], current_answer_stated=None,
            next_target_transition={
                "question_id": "q02", "introduced": introduced,
                "excerpt": NEXT_EXCERPT if introduced else None,
            },
        ).model_dump()

    generation, metadata, final_prompt = asyncio.run(deliver_answer(
        review_service=AnswerReviewService(InMemoryRepository(), SimpleNamespace(review_answer=review)),
        generate=generate, runtime=runtime,
        event=Event(id=attempt.event_id, canonical_name="法國大革命"), attempt=attempt,
        persona=None, history=[], learner_message="我仍說按等級。" if restatement else "我改為按人數，因為代表應各有一票。",
        base_prompt=runtime.prompt_block(), persist_audit=False,
    ))
    assert generation.response == (NEXT_QUESTION if introduces_next else SAME_QUESTION)
    assert len(generated) == len(reviewed) == 1
    assert metadata["completion_status"] == ("feedback_completed" if restatement else "resolved")
    assert metadata["resolution_criteria_met"] is (not restatement)
    assert metadata["target_question_id"] == "q01"
    assert metadata["next_target_question_id"] == "q02"
    assert metadata["next_target_started"] is introduces_next
    assert metadata["answer_delivery"]["outcome"] == "accepted"
    assert metadata["answer_delivery"]["state_held"] is False
    assert metadata["answer_delivery"]["candidates"][0]["validation_flags"] == []
    assert final_prompt == runtime.prompt_block()
    saved = ChatMessage(conversation_id="test", speaker_type="assistant", speaker_name="AI",
                        content=generation.response, metadata=metadata)
    resumed = build_interaction_runtime(_condition(code), attempt, [saved])
    assert resumed.target.question_id == "q02"
    assert resumed.previous_state == ("NOTICE_ERROR" if introduces_next else None)
    assert resumed.previous_disclosure_level == ("D0" if introduces_next else None)
    if not introduces_next:
        assert resumed.allowed_states == ("NOTICE_ERROR", "REFLECT", "SELF_CORRECT", "RESOLVED")
    assert not resumed.restatement_required


@pytest.mark.parametrize("text", [SAME_QUESTION, NEXT_QUESTION])
def test_transition_words_cannot_complete_an_unfinished_question(text):
    runtime = closing_runtime()
    metadata = resolve_interaction_metadata(runtime, {
        "dialogue_state": "REFLECT", "disclosure_level": "D1", "completion_status": "continue",
    }, text)
    assert metadata["completion_status"] == "continue"
    assert metadata["next_target_transition_required"] is False
    saved = ChatMessage(conversation_id="test", speaker_type="assistant", speaker_name="AI",
                        content=text, metadata=metadata)
    resumed = build_interaction_runtime(_condition("02"), _multi_error_attempt(), [saved])
    assert resumed.target.question_id == "q01"


@pytest.mark.parametrize("required,transition,confirmed", [
    (True, {"question_id": "q02", "introduced": True, "excerpt": NEXT_EXCERPT}, True),
    (True, {"question_id": "q01", "introduced": True, "excerpt": NEXT_EXCERPT}, False),
    (True, {"question_id": "q02", "introduced": True, "excerpt": "不存在的引文"}, False),
    (True, {"question_id": "q02", "introduced": True, "excerpt": " "}, False),
    (True, {"question_id": "q02", "introduced": None, "excerpt": NEXT_EXCERPT}, False),
    (True, {"question_id": "q02", "introduced": False, "excerpt": NEXT_EXCERPT}, False),
    (True, None, False),
    (False, {"question_id": "q02", "introduced": True, "excerpt": NEXT_EXCERPT}, False),
])
def test_review_must_match_backend_target_and_actual_reply(required, transition, confirmed):
    context = {
        "runtime": {"next_target_transition_required": required},
        "next_target": {"question_id": "q02"}, "candidate": {"response": NEXT_QUESTION},
    }
    assert confirms_next_target_transition(context, {"next_target_transition": transition}) is confirmed


@pytest.mark.parametrize("status", ["continue", "final_answer_pending"])
def test_d4_feedback_does_not_authorize_transition_before_one_restatement(status):
    runtime = replace(closing_runtime(restatement=True), previous_completion_status=status,
                      allowed_states=("SELF_CORRECT", "RESOLVED"))
    metadata = resolve_interaction_metadata(runtime, {
        "dialogue_state": "SELF_CORRECT", "dialogue_move": "corrective_feedback",
        "disclosure_level": "D4", "completion_status": "corrective_resolution_pending",
    }, "應按人數表決，而非各等級一票。請用自己的話重述理由。")
    service = AnswerReviewService(InMemoryRepository(), None)
    context = service.build_context(
        ChatMessage(conversation_id="test", speaker_type="assistant", speaker_name="AI",
                    content=NEXT_QUESTION, metadata=metadata),
        runtime=runtime, event=Event(canonical_name="法國大革命"), attempt=_multi_error_attempt(),
        history=[], learner_message="不懂。",
    )
    assert metadata["completion_status"] == "corrective_resolution_pending"
    assert context["runtime"]["next_target_transition_required"] is False
    assert not confirms_next_target_transition(context, {"next_target_transition": {
        "question_id": "q02", "introduced": True, "excerpt": NEXT_EXCERPT,
    }})


@pytest.mark.parametrize("enabled", [False, True])
def test_disabled_or_background_review_never_retroactively_starts_next_question(enabled, monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_answer_review_enabled", enabled)
    monkeypatch.setattr(get_settings(), "llm_answer_review_mode", "observe")
    runtime, attempt, repository = closing_runtime(), _multi_error_attempt(), InMemoryRepository()
    calls = []

    async def review(context):
        calls.append(context)
        return {"findings": [], "current_answer_stated": None, "next_target_transition": {
            "question_id": "q02", "introduced": True, "excerpt": NEXT_EXCERPT,
        }}

    service = AnswerReviewService(repository, SimpleNamespace(review_answer=review))
    assert service.before_delivery(runtime) is False
    metadata = resolve_interaction_metadata(runtime, closing_metadata(), NEXT_QUESTION)
    message = ChatMessage(conversation_id="test", speaker_type="assistant", speaker_name="AI",
                          content=NEXT_QUESTION, metadata=metadata)
    context = service.prepare(message, runtime=runtime, event=Event(canonical_name="法國大革命"),
                              attempt=attempt, history=[], learner_message="我改為按人數。")
    repository.add_message(message)

    async def finish():
        service.schedule(message, context)
        await asyncio.gather(*service.tasks.values())

    asyncio.run(finish())
    assert len(calls) == int(enabled)
    saved = repository.get_message(message.id)
    assert saved.metadata["completion_status"] == "resolved"
    assert saved.metadata["next_target_started"] is False
    if enabled:
        assert saved.metadata["answer_review"]["next_target_transition"]["introduced"] is True
    resumed = build_interaction_runtime(_condition("02"), attempt, [saved])
    assert resumed.target.question_id == "q02"
    assert resumed.previous_state is None


def test_review_adapter_returns_transition_evidence_in_its_existing_call(monkeypatch):
    provider = LiteLLMProvider(Settings(llm_model="gpt-5.6-terra", openai_api_key="fake-key"))
    calls = []
    report = {"findings": [], "current_answer_stated": None, "next_target_transition": {
        "question_id": "q02", "introduced": True, "excerpt": NEXT_EXCERPT,
    }}

    async def complete(candidate, **kwargs):
        calls.append(kwargs)
        assert "Use meaning in context, not connector words" in kwargs["system_prompt"]
        assert "next_target_transition_required" in kwargs["user_prompt"]
        return LLMCompletion(content=json.dumps(report), prompt_tokens=10, completion_tokens=5, total_tokens=15)

    monkeypatch.setattr(provider.runner, "_complete", complete)
    context = {
        "runtime": {"next_target_transition_required": True},
        "next_target": {"question_id": "q02"}, "candidate": {"response": NEXT_QUESTION},
    }
    result = asyncio.run(provider.review_answer(context))
    assert confirms_next_target_transition(context, result) is True
    assert result["next_target_transition"] == report["next_target_transition"]
    assert len(calls) == 1


@pytest.mark.parametrize("transition", [
    None,
    {"question_id": "q02", "introduced": None, "excerpt": None},
    {"question_id": "other", "introduced": True, "excerpt": NEXT_EXCERPT},
])
def test_unconfirmed_transition_does_not_hold_completed_restatement(transition, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "llm_content_validation_enabled", False)
    monkeypatch.setenv("LLM_REJECTION_LOG_PATH", str(tmp_path / "review.jsonl"))
    condition, attempt = _condition("04"), _multi_error_attempt()
    prior = ChatMessage(conversation_id="test", speaker_type="assistant", speaker_name="AI",
                        content="按人數表決。請用自己的話重述理由。", metadata={
                            "interaction_policy_version": INTERACTION_POLICY_VERSION,
                            "target_question_id": "q01", "dialogue_state": "SELF_CORRECT",
                            "disclosure_level": "D4", "completion_status": "corrective_resolution_pending",
                        })
    runtime = build_interaction_runtime(condition, attempt, [prior])
    calls = []

    async def generate(prompt):
        return ChatGenerationResult(response=NEXT_QUESTION, interaction_metadata=closing_metadata(restatement=True))

    async def review(context):
        calls.append(context)
        return {"findings": [], "current_answer_stated": None, "next_target_transition": transition}

    generation, metadata, _ = asyncio.run(deliver_answer(
        review_service=AnswerReviewService(InMemoryRepository(), SimpleNamespace(review_answer=review)),
        generate=generate, runtime=runtime, event=Event(canonical_name="法國大革命"), attempt=attempt,
        persona=None, history=[prior], learner_message="我仍不明白。", base_prompt=runtime.prompt_block(),
        persist_audit=False,
    ))
    assert len(calls) == 1
    assert generation.response == NEXT_QUESTION
    assert metadata["answer_delivery"]["outcome"] == "accepted"
    assert metadata["answer_delivery"]["state_held"] is False
    assert metadata["completion_status"] == "feedback_completed"
    assert not metadata.get("next_target_started")
    saved = ChatMessage(conversation_id="test", speaker_type="assistant", speaker_name="AI",
                        content=generation.response, metadata=metadata)
    resumed = build_interaction_runtime(condition, attempt, [prior, saved])
    assert resumed.target.question_id == "q02"
    assert resumed.allowed_states == ("NOTICE_ERROR", "REFLECT", "SELF_CORRECT", "RESOLVED")
    assert resumed.restatement_required is False
