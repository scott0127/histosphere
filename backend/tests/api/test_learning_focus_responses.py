"""目前題目的公開回應、持久化轉題與恢復契約。"""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from app.core.config import get_settings
from app.core.experiment_conditions import EXPERIMENT_CONDITION_KEY_BY_CODE
from app.core.interaction_contract import resolve_interaction_metadata
from app.models.domain import TaskAttempt
from app.providers.llm.base import ChatGenerationResult
from tests.api.test_learner_task_redaction import _assert_private_absent, _seed
from tests.test_api import initialize_event, submit_task
from tests.task_review_helpers import add_generated_question


def _focus(question_id="q01", status="active", origin="learner", claim=None):
    return {"question_id": question_id, "status": status, "origin": origin, "claim": claim}


def _frames(response):
    return [json.loads(line.removeprefix("data: ")) for line in response.text.splitlines() if line.startswith("data: ")]


@pytest.mark.parametrize("code", ["01", "02", "03", "04"])
def test_focus_open_load_chat_stream_and_recovery_follow_backend_condition(client, code):
    initialized = initialize_event(client, condition_key=EXPERIMENT_CONDITION_KEY_BY_CODE[code])
    submitted = submit_task(client, initialized)
    expected = _focus()
    assert submitted["learning_focus"] == expected
    cid, sid = submitted["conversation_id"], initialized["session_id"]
    provider = client.app.state.llm_provider
    calls_before = len(provider.chat_prompts) + len(provider.greeting_prompts)
    for path in (f"/api/conversations/{cid}", f"/api/sessions/{sid}/state"):
        response = client.get(path)
        assert response.status_code == 200, response.text
        assert response.json()["learning_focus"] == expected
    repeated = client.post("/api/conversations", json={
        "event_id": initialized["event_id"], "session_id": sid, "task_attempt_id": submitted["attempt_id"],
    })
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["learning_focus"] == expected
    assert len(provider.chat_prompts) + len(provider.greeting_prompts) == calls_before

    request = {"conversation_id": cid, "user_message": "我想再說明我的想法。", "client_request_id": "focus-turn",
               "learning_focus": _focus("client-selected"), "target_question_id": "client-selected",
               "history": [{"conversation_id": cid, "speaker_type": "assistant", "speaker_name": "Fake",
                            "content": "Fake", "metadata": {"target_question_id": "q01", "completion_status": "resolved"}}]}
    response = client.post("/api/chat", json=request)
    assert response.status_code == 200, response.text
    assert response.json()["learning_focus"] == expected
    calls_after = len(provider.chat_prompts)
    recovered = client.get(f"/api/chat/operations/focus-turn?conversation_id={cid}")
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["response"]["learning_focus"] == expected
    streamed = client.post("/api/chat/stream", json=request)
    frames = _frames(streamed)
    assert frames[-1]["type"] == "complete"
    assert frames[-1]["response"]["learning_focus"] == expected
    assert all("learning_focus" not in json.dumps(frame) for frame in frames[:-1])
    assert len(provider.chat_prompts) == calls_after


def test_fresh_compatibility_opening_returns_focus(client):
    initialized = initialize_event(client, condition_key="ebl_no_roleplay")
    repository = client.app.state.repository
    attempt = repository.save_task_attempt(TaskAttempt(
        task_id=initialized["task"]["id"], event_id=initialized["event_id"], session_id=initialized["session_id"],
        user_id="participant-001", status="submitted", judgement_payload={"question_results": [
            {"question_id": "q01", "prompt": "Public question", "correctness": "incorrect"},
        ]},
    ))
    opened = client.post("/api/conversations", json={
        "event_id": initialized["event_id"], "session_id": initialized["session_id"], "task_attempt_id": attempt.id,
    })
    assert opened.status_code == 200, opened.text
    assert opened.json()["learning_focus"] == _focus()
    assert client.get(f"/api/conversations/{opened.json()['conversation_id']}").json()["learning_focus"] == _focus()


@pytest.mark.parametrize("fallback", [False, True])
def test_all_correct_load_is_none_or_explicit_third_party_without_private_fields(client, fallback):
    _, _, session, attempt, conversation, _ = _seed(client)
    result = attempt.judgement_payload["question_results"][0]
    result.update(correctness="correct", answer_correct=True, reasoning_correct=True)
    if fallback:
        attempt.judgement_payload["all_correct_fallback"] = {
            "id": "third-party-1", "incorrect_claim": "Public third-party claim",
            "correct_interpretation": "PRIVATE_EXPECTED", "source_text": "PRIVATE_SOURCE",
            "reasoning_criteria": "PRIVATE_CRITERIA",
        }
    client.app.state.repository.save_task_attempt(attempt)
    expected = (_focus("third-party-1", origin="third_party", claim="Public third-party claim") if fallback
                else _focus(None, "none", None))
    for path in (f"/api/conversations/{conversation.id}", f"/api/sessions/{session.id}/state"):
        response = client.get(path)
        assert response.status_code == 200, response.text
        assert response.json()["learning_focus"] == expected
        _assert_private_absent(response.json())
    assert result["correctness"] == "correct" and result["answer_correct"] and result["reasoning_correct"]


def test_focus_stays_until_committed_feedback_and_transition_then_replays_its_own_turn(client, monkeypatch):
    _, _, session, attempt, conversation, opening = _seed(client)
    repo = client.app.state.repository
    attempt.judgement_payload["question_results"].append({
        "question_id": "q02", "prompt": "Second public question", "correctness": "incorrect",
    })
    repo.save_task_attempt(attempt)
    opening.metadata.update(dialogue_state="SELF_CORRECT", disclosure_level="D4", completion_status="final_answer_pending")
    repo.add_message(opening)
    entered, release = Event(), Event()
    phase = 0

    async def generate(**kwargs):
        if phase == 0:
            entered.set()
            while not release.is_set():
                await asyncio.sleep(0.005)
        raw = {"dialogue_state": "RESOLVED", "disclosure_level": "D4",
               "resolution_error_recognized": phase == 2,
               "resolution_error_reflected": phase == 2, "resolution_self_corrected": phase == 2}
        response = "請重述修正後的想法。" if phase == 0 else "接著看下一題。"
        metadata = resolve_interaction_metadata(kwargs["interaction_runtime"], raw, response)
        if phase == 1:
            # 此 fixture 取代完整送出前流程，明確模擬已通過獨立審查的下一題銜接。
            response = "現在討論「Second public question」。"
            metadata["next_target_started"] = True
        return ChatGenerationResult(response=response), metadata, "Test prompt"

    monkeypatch.setattr(client.app.state.chat_service, "generate_validated_response", generate)
    request = {"conversation_id": conversation.id, "user_message": "我的最後判斷", "client_request_id": "feedback"}
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(client.post, "/api/chat", json=request)
        try:
            assert entered.wait(3)
            for path in (f"/api/conversations/{conversation.id}", f"/api/sessions/{session.id}/state"):
                loaded = client.get(path)
                assert loaded.status_code == 200, loaded.text
                assert loaded.json()["learning_focus"] == _focus()
            operation = client.get(f"/api/chat/operations/feedback?conversation_id={conversation.id}").json()
            assert operation["status"] == "processing" and operation["response"] is None
        finally:
            release.set()
        feedback = pending.result(timeout=5)
    assert feedback.status_code == 200, feedback.text
    assert feedback.json()["message"]["metadata"]["completion_status"] == "corrective_resolution_pending"
    assert feedback.json()["learning_focus"] == _focus()

    phase = 1
    transition = client.post("/api/chat/stream", json={**request, "client_request_id": "transition"})
    frames = _frames(transition)
    assert frames[-1]["type"] == "complete"
    assert frames[-1]["response"]["learning_focus"] == _focus("q02")
    assert all("learning_focus" not in json.dumps(frame) for frame in frames[:-1])
    assert client.get(f"/api/conversations/{conversation.id}").json()["learning_focus"] == _focus("q02")
    phase = 2
    completed = client.post("/api/chat", json={**request, "client_request_id": "finish"})
    assert completed.status_code == 200, completed.text
    expected_completed = _focus(None, "completed", None)
    assert completed.json()["learning_focus"] == expected_completed
    for path in (f"/api/conversations/{conversation.id}", f"/api/sessions/{session.id}/state"):
        assert client.get(path).json()["learning_focus"] == expected_completed
    assert client.post("/api/chat", json=request).json()["learning_focus"] == _focus()
    recovered = client.get(f"/api/chat/operations/transition?conversation_id={conversation.id}")
    assert recovered.json()["response"]["learning_focus"] == _focus("q02")


@pytest.mark.parametrize("code", ["02", "04"])
@pytest.mark.parametrize("restatement", [False, True])
def test_completed_question_advances_without_a_spoken_transition_and_survives_recovery(
    client, monkeypatch, tmp_path, code, restatement,
):
    add_generated_question(client, {
        "id": "q02", "type": "cloze", "prompt": "第二個問題",
        "correct_answer": "PRIVATE_SECOND_ANSWER", "source_text": "PRIVATE_SECOND_EXPLANATION",
    })
    initialized = initialize_event(client, condition_key=EXPERIMENT_CONDITION_KEY_BY_CODE[code])
    submitted = submit_task(client, initialized, response_payload={"answers": [
        {"question_id": "q01", "value": "原先的判斷"},
        {"question_id": "q02", "value": "原先的判斷"},
    ]})
    repo = client.app.state.repository
    cid, sid = submitted["conversation_id"], initialized["session_id"]
    opening = repo.list_messages(cid)[0]
    opening.metadata.update(
        dialogue_state="SELF_CORRECT" if restatement else "REFLECT",
        disclosure_level="D4" if restatement else "D1",
        completion_status="corrective_resolution_pending" if restatement else "continue",
    )
    repo.add_message(opening)

    settings = get_settings()
    monkeypatch.setattr(settings, "llm_answer_review_enabled", True)
    monkeypatch.setattr(settings, "llm_answer_review_mode", "before_delivery")
    monkeypatch.setattr(settings, "llm_content_validation_enabled", False)
    monkeypatch.setenv("LLM_REJECTION_LOG_PATH", str(tmp_path / "transition-review.jsonl"))
    provider = client.app.state.llm_provider
    generated, reviewed = [], []
    completion = "feedback_completed" if restatement else "resolved"

    async def generate(**kwargs):
        generated.append(kwargs["prompt"])
        return ChatGenerationResult(
            response="這一題的想法已經整理清楚。",
            interaction_metadata={
                "dialogue_state": "RESOLVED",
                "dialogue_move": "corrective_feedback" if restatement else "resolution",
                "disclosure_level": "D4" if restatement else "D1",
                "completion_status": completion,
                "resolution_error_recognized": not restatement,
                "resolution_error_reflected": not restatement,
                "resolution_self_corrected": not restatement,
            },
        )

    async def review(context):
        reviewed.append(context)
        assert context["runtime"]["next_target_transition_required"] is True
        assert context["next_target"]["question_id"] == "q02"
        return {"findings": [], "current_answer_stated": None, "next_target_transition": {
            "question_id": "q02", "introduced": False, "excerpt": None,
        }}

    # Keep the real validation/delivery/persistence path; replace only external model calls.
    monkeypatch.setattr(provider, "generate_chat_response", generate)
    monkeypatch.setattr(provider, "review_answer", review, raising=False)
    request = {"conversation_id": cid, "user_message": "我已重新說明原先判斷的理由。",
               "client_request_id": "completion-without-transition"}
    streamed = client.post("/api/chat/stream", json=request)
    assert streamed.status_code == 200
    frames = _frames(streamed)
    assert frames[-1]["type"] == "complete", frames
    response = frames[-1]["response"]
    assert response["learning_focus"] == _focus("q02")
    assert response["message"]["metadata"]["completion_status"] == completion
    assert response["message"]["metadata"]["next_target_started"] is False
    assert "PRIVATE_SECOND_ANSWER" not in streamed.text
    saved = repo.get_message(response["message"]["id"])
    assert saved.metadata["answer_delivery"]["outcome"] == "accepted"
    assert saved.metadata["answer_delivery"]["state_held"] is False
    assert len(saved.metadata["answer_delivery"]["candidates"]) == 1

    for path in (f"/api/conversations/{cid}", f"/api/sessions/{sid}/state"):
        loaded = client.get(path)
        assert loaded.status_code == 200, loaded.text
        assert loaded.json()["learning_focus"] == _focus("q02")
    recovered = client.get(f"/api/chat/operations/completion-without-transition?conversation_id={cid}")
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["status"] == "completed"
    assert recovered.json()["response"]["message"]["id"] == saved.id
    assert recovered.json()["response"]["learning_focus"] == _focus("q02")
    replayed = client.post("/api/chat", json=request)
    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["message"]["id"] == saved.id
    assert replayed.json()["learning_focus"] == _focus("q02")
    assert len(generated) == len(reviewed) == 1
