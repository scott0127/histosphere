"""All conditions persist correction progress independently of EBL scaffolding."""

from copy import deepcopy

import pytest

from app.core.config import get_settings
from app.core.experiment_conditions import EXPERIMENT_CONDITION_KEY_BY_CODE
from app.providers.llm.base import ChatGenerationResult
from tests.api.test_learning_focus_responses import _focus, _frames
from tests.test_api import initialize_event, submit_task


@pytest.mark.parametrize("code", ["01", "02", "03", "04"])
def test_shared_correction_progress_persists_and_replays_without_rewriting_initial_answers(
    client, monkeypatch, code,
):
    initialized = initialize_event(client, condition_key=EXPERIMENT_CONDITION_KEY_BY_CODE[code])
    submitted = submit_task(client, initialized)
    repo = client.app.state.repository
    cid, sid = submitted["conversation_id"], initialized["session_id"]
    attempt = repo.get_task_attempt(submitted["attempt_id"])
    attempt.judgement_payload["question_results"].append({
        "question_id": "q02", "prompt": "第二個問題", "correctness": "incorrect",
        "learner_answer": "原先的判斷", "learner_rationale": "原先的理由",
        "expected_answer": "PRIVATE_SECOND_ANSWER", "source_text": "PRIVATE_SECOND_EXPLANATION",
    })
    repo.save_task_attempt(attempt)
    original_answers = deepcopy(attempt.response_payload)
    original_judgement = deepcopy(attempt.judgement_payload)
    assert submitted["learning_focus"] == _focus()

    # Preserve real prompt, runtime, delivery, persistence, recovery and SSE behavior.
    # Only the external generation result is deterministic in this API test.
    monkeypatch.setattr(get_settings(), "llm_content_validation_enabled", False)
    calls = []
    completed = False

    async def generate(**kwargs):
        calls.append(kwargs)
        ebl = kwargs["condition"].ebl_enabled
        return ChatGenerationResult(
            response=("你已說明原先判斷如何改變。" if completed else "我們繼續討論這個問題。"),
            interaction_metadata={
                "dialogue_state": ("RESOLVED" if completed else "REFLECT") if ebl else "STANDARD_CHAT",
                "dialogue_move": ("resolution" if completed else "reflection_prompt") if ebl else "natural_response",
                "disclosure_level": "D1" if ebl else None,
                "completion_status": "resolved" if completed else "continue",
                "resolution_error_recognized": completed,
                "resolution_error_reflected": completed,
                "resolution_self_corrected": completed,
            },
        )

    monkeypatch.setattr(client.app.state.llm_provider, "generate_chat_response", generate)

    def check_saved_focus(expected):
        for path in (f"/api/conversations/{cid}", f"/api/sessions/{sid}/state"):
            loaded = client.get(path)
            assert loaded.status_code == 200, loaded.text
            assert loaded.json()["learning_focus"] == expected

    def request(turn_id, text):
        return {"conversation_id": cid, "client_request_id": turn_id, "user_message": text}

    pending_request = request("shared-incomplete", "我仍不清楚原本的理由有什麼問題。")
    pending = client.post("/api/chat", json=pending_request)
    assert pending.status_code == 200, pending.text
    assert pending.json()["message"]["metadata"]["completion_status"] == "continue"
    assert pending.json()["learning_focus"] == _focus()
    check_saved_focus(_focus())

    completed = True
    first_request = request("shared-first-resolved", "我知道原先判斷錯在哪裡，也已說明修正後的答案與理由。")
    streamed = client.post("/api/chat/stream", json=first_request)
    assert streamed.status_code == 200, streamed.text
    frames = _frames(streamed)
    assert frames[-1]["type"] == "complete", frames
    first = frames[-1]["response"]
    assert first["learning_focus"] == _focus("q02")
    assert first["message"]["metadata"]["target_question_id"] == "q01"
    assert first["message"]["metadata"]["completion_status"] == "resolved"
    assert "PRIVATE_SECOND_ANSWER" not in streamed.text
    check_saved_focus(_focus("q02"))
    if code in {"01", "03"}:
        metadata = first["message"]["metadata"]
        assert metadata["dialogue_state"] == "STANDARD_CHAT"
        assert metadata["dialogue_move"] == "natural_response"
        assert metadata["disclosure_level"] is None
        assert metadata["primary_ebl_move"] == "none"

    second_request = request("shared-second-resolved", "第二題我也改變原先判斷，修正後的答案與理由如下。")
    second = client.post("/api/chat", json=second_request)
    assert second.status_code == 200, second.text
    assert second.json()["message"]["metadata"]["target_question_id"] == "q02"
    assert second.json()["message"]["metadata"]["completion_status"] == "resolved"
    done = _focus(None, "completed", None)
    assert second.json()["learning_focus"] == done
    check_saved_focus(done)

    # A stale client retry replays its original result; it neither regenerates nor
    # rewinds the currently persisted question. Recovery and SSE agree with REST.
    calls_before_replay = len(calls)
    for old_request, expected, message_id in (
        (pending_request, _focus(), pending.json()["message"]["id"]),
        (first_request, _focus("q02"), first["message"]["id"]),
        (second_request, done, second.json()["message"]["id"]),
    ):
        replay = client.post("/api/chat", json=old_request)
        assert replay.status_code == 200, replay.text
        assert replay.json()["learning_focus"] == expected
        assert replay.json()["message"]["id"] == message_id
        recovery = client.get(f"/api/chat/operations/{old_request['client_request_id']}?conversation_id={cid}")
        assert recovery.status_code == 200, recovery.text
        assert recovery.json()["response"]["learning_focus"] == expected
        assert recovery.json()["response"]["message"]["id"] == message_id
        replay_stream = _frames(client.post("/api/chat/stream", json=old_request))[-1]
        assert replay_stream["type"] == "complete"
        assert replay_stream["response"]["learning_focus"] == expected
    assert len(calls) == calls_before_replay == 3
    check_saved_focus(done)

    # Finishing all targets does not reuse the initial wrong answer as a new target.
    continuation = client.post("/api/chat", json=request("shared-after-completion", "我們可以繼續談事件背景嗎？"))
    assert continuation.status_code == 200, continuation.text
    assert continuation.json()["learning_focus"] == done
    assert continuation.json()["message"]["metadata"]["target_question_id"] is None
    check_saved_focus(done)
    saved_attempt = repo.get_task_attempt(attempt.id)
    assert saved_attempt.response_payload == original_answers
    assert saved_attempt.judgement_payload == original_judgement
