"""Analytics must distinguish verified corrections, delivered turns and missing usage."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.domain import ChatMessage, ExperimentSession, ResearchLog
from app.services.conversation_metrics import conversation_metrics


START = datetime(2026, 9, 28, 1, tzinfo=timezone.utc)


def test_human_review_prepared_opening_does_not_start_learning_before_entry():
    ready_session = session(completed=False)
    ready_session.timer_started_at = ready_session.timer_ends_at = None
    ready_session.status = "initialized"
    opening = message(0, "assistant", 0, metadata=target("q01", judgement={"decision_source": "human_review"}))
    result = conversation_metrics([opening], ready_session, now=START + timedelta(seconds=100))
    assert result["learning"]["duration_seconds"] is None
    assert result["learning"]["started_at"] is None
    assert result["learning"]["questions"] == []


def test_first_thinking_period_excludes_ready_waiting_before_learner_entry():
    active_session = session(seconds=80)
    active_session.timer_started_at = START + timedelta(seconds=50)
    messages = [
        message(0, "assistant", 0, metadata=target("q01", judgement={"decision_source": "human_review"})),
        message(1, "learner", 60),
        message(2, "assistant", 65, metadata=target("q01")),
    ]
    result = conversation_metrics(messages, active_session)
    assert result["round_trips"][0]["thinking_seconds"] == 10
    assert result["round_trips"][0]["elapsed_seconds"] == 15
    assert result["learning"]["duration_seconds"] == 30


def message(index, speaker, seconds, *, text="測 試\n🙂", metadata=None, **kwargs):
    return ChatMessage(
        id=f"m{index}", conversation_id="conversation", sequence_index=index,
        speaker_type=speaker, speaker_name=speaker, content=text,
        created_at=START + timedelta(seconds=seconds), metadata=metadata or {}, **kwargs,
    )


def session(*, seconds=120, completed=True):
    return ExperimentSession(
        id="session", condition_id="condition", condition_key_snapshot="ebl_no_roleplay", event_id="event",
        timer_started_at=START, timer_ends_at=START + timedelta(seconds=300),
        completed_at=START + timedelta(seconds=seconds) if completed else None,
        status="completed" if completed else "conversation_started",
    )


def target(question, **extra):
    return {"target_question_id": question, "learning_target_question_id": question,
            "interaction_mode": "scaffold", **extra}


def test_characters_known_zero_and_partial_retry_usage_are_not_missing():
    messages = [
        message(0, "assistant", 0, metadata={"llm_call": {"total_tokens": 0, "completion_tokens": 0}}),
        message(1, "learner", 10, text="a\t中　！"),
        message(2, "persona", 12, metadata={"llm_call": {"total_tokens": 80, "completion_tokens": 20, "attempt_count": 2, "usage_reported_attempts": 1}}),
        message(3, "assistant", 13, metadata={"system_fallback": True}),
        message(4, "assistant", 14),
    ]
    stats = conversation_metrics(messages)
    assert stats["total_characters"] == 15
    assert stats["learner_characters"] == 3
    assert stats["assistant_characters"] == 9
    assert stats["system_characters"] == 3
    assert stats["assistant_total_tokens"] == 80
    assert stats["assistant_average_tokens"] == 40
    assert stats["assistant_token_usage_complete"] is False
    assert stats["message_metrics"][0]["total_tokens"] == 0
    assert stats["message_metrics"][0]["token_usage_complete"] is True
    assert stats["message_metrics"][2]["token_usage_complete"] is False
    assert stats["message_metrics"][4]["total_tokens"] is None
    unknown = conversation_metrics([message(0, "assistant", 0)])
    assert unknown["assistant_average_tokens"] is None
    assert unknown["assistant_total_tokens"] is None


def test_round_trip_includes_thinking_and_retry_wait_but_separates_generation():
    timing = {
        "original_request_started_at": (START + timedelta(seconds=20)).isoformat(),
        "request_started_at": (START + timedelta(seconds=35)).isoformat(),
        "response_completed_at": (START + timedelta(seconds=40)).isoformat(),
        "response_latency_ms": 5000, "attempt_number": 2,
    }
    messages = [
        message(0, "assistant", 0, metadata=target("q01")),
        message(1, "learner", 20, operation_status="completed", metadata={"response_message_id": "m2"}),
        message(2, "assistant", 39, metadata=target("q01", exchange_timing=timing)),
        message(3, "learner", 50, operation_status="completed", metadata={"response_message_id": "m4"}),
        message(4, "assistant", 51, metadata={"system_fallback": True}),
        message(5, "learner", 60, operation_status="processing"),
    ]
    stats = conversation_metrics(messages)
    assert stats["completed_exchanges"] == 1
    completed, failed, pending = stats["round_trips"]
    assert completed["thinking_seconds"] == 20
    assert completed["response_seconds"] == 20
    assert completed["generation_seconds"] == 5
    assert completed["elapsed_seconds"] == 40
    assert completed["timing_source"] == "recorded"
    assert completed["question_id"] == "q01"
    assert failed["status"] == "failed"
    assert failed["response_seconds"] is None
    assert pending["status"] == "pending"


def test_legacy_round_pairs_by_sequence_without_counting_greeting_or_fallback():
    messages = [message(0, "assistant", 0), message(1, "learner", 10), message(2, "assistant", 14)]
    stats = conversation_metrics(list(reversed(messages)))
    assert stats["completed_exchanges"] == 1
    assert stats["round_trips"][0]["timing_source"] == "message_timestamps"
    assert stats["round_trips"][0]["response_seconds"] == 4
    assert stats["round_trips"][0]["elapsed_seconds"] == 14
    assert stats["learning"]["applicable"] is False
    assert stats["learning"]["average_seconds_per_question"] is None


@pytest.mark.parametrize("corrected_count", [0, 1, 2])
def test_average_uses_successfully_corrected_questions_with_minimum_one(corrected_count):
    messages = [message(0, "assistant", 0, metadata=target("q01"))]
    for index in range(2):
        question = f"q0{index + 1}"
        resolved = index < corrected_count
        messages.extend([
            message(index * 2 + 1, "learner", 20 + index * 40),
            message(index * 2 + 2, "assistant", 30 + index * 40, metadata=target(
                question, completion_status="resolved" if resolved else "feedback_completed",
                resolution_self_corrected=resolved,
                next_target_question_id="q02" if index == 0 else None,
                next_target_started=index == 0,
            )),
        ])
    stats = conversation_metrics(messages, session(), now=START + timedelta(seconds=180))
    learning = stats["learning"]
    assert learning["duration_seconds"] == 120
    assert learning["corrected_questions"] == corrected_count
    assert learning["denominator"] == max(corrected_count, 1)
    assert learning["average_seconds_per_question"] == 120 / max(corrected_count, 1)
    assert [q["duration_seconds"] for q in learning["questions"]] == [30, 40]
    assert [q["completed_exchanges"] for q in learning["questions"]] == [1, 1]
    assert learning["timing_source"] == "session_timer"


def test_held_completion_and_unresolved_close_do_not_claim_success():
    messages = [
        message(0, "assistant", 0, metadata=target("q01")),
        message(1, "learner", 20),
        message(2, "assistant", 30, metadata=target("q01", completion_status="resolved",
            resolution_self_corrected=True, answer_delivery={"state_held": True})),
    ]
    learning = conversation_metrics(messages, session(seconds=90), now=START + timedelta(seconds=180))["learning"]
    assert learning["corrected_questions"] == 0
    assert learning["denominator"] == 1
    assert learning["questions"][0]["outcome"] == "unresolved"
    assert learning["questions"][0]["duration_seconds"] == 90


def test_active_and_expired_sessions_have_honest_point_in_time_durations():
    messages = [message(0, "assistant", 0, metadata=target("q01"))]
    active = conversation_metrics(messages, session(completed=False), now=START + timedelta(seconds=90))["learning"]
    assert active["duration_seconds"] == 90
    assert active["is_complete"] is False
    assert active["questions"][0]["outcome"] == "in_progress"
    expired = conversation_metrics(messages, session(completed=False), now=START + timedelta(seconds=360))["learning"]
    assert expired["duration_seconds"] == 300
    assert expired["is_complete"] is True
    assert expired["questions"][0]["outcome"] == "unresolved"


def test_accepted_late_correction_counts_and_actual_completion_can_exceed_deadline():
    messages = [message(0, "assistant", 0, metadata=target("q01")), message(1, "learner", 298),
                message(2, "assistant", 305, metadata=target("q01", completion_status="resolved", resolution_self_corrected=True))]
    learning = conversation_metrics(messages, session(seconds=308), now=START + timedelta(seconds=360))["learning"]
    assert learning["duration_seconds"] == 308
    assert learning["corrected_questions"] == 1
    assert learning["questions"][0]["duration_seconds"] == 305
    awaiting_close = conversation_metrics(messages, session(completed=False), now=START + timedelta(seconds=360))["learning"]
    assert awaiting_close["duration_seconds"] == 300
    assert awaiting_close["corrected_questions"] == 1


@pytest.mark.parametrize("observed_seconds", [301, 86400])
def test_late_timer_completion_uses_deadline_without_changing_persisted_session(observed_seconds):
    messages = [message(0, "assistant", 0, metadata=target("q01"))]
    expired = session(seconds=observed_seconds).model_copy(update={"completion_reason": "timer_elapsed"})
    learning = conversation_metrics(messages, expired, now=START + timedelta(seconds=observed_seconds))["learning"]

    assert learning["ended_at"] == expired.timer_ends_at.isoformat()
    assert learning["duration_seconds"] == 300
    assert learning["average_seconds_per_question"] == 300
    assert learning["questions"][0]["duration_seconds"] == 300
    assert learning["questions"][0]["outcome"] == "unresolved"
    assert learning["is_complete"] is True
    assert expired.completed_at == START + timedelta(seconds=observed_seconds)


def test_timer_expiry_keeps_late_correction_and_real_response_wait():
    messages = [message(0, "assistant", 0, metadata=target("q01")), message(1, "learner", 298),
                message(2, "assistant", 305, metadata=target("q01", completion_status="resolved", resolution_self_corrected=True))]
    expired = session(seconds=308).model_copy(update={"completion_reason": "timer_elapsed"})
    stats = conversation_metrics(messages, expired, now=START + timedelta(seconds=360))

    assert stats["learning"]["duration_seconds"] == 300
    assert stats["learning"]["corrected_questions"] == 1
    assert stats["learning"]["questions"][0]["duration_seconds"] == 300
    assert stats["round_trips"][0]["response_seconds"] == 7
    assert stats["round_trips"][0]["response_at"] == messages[-1].created_at.isoformat()


def test_expired_reset_timer_uses_extended_deadline_and_original_start():
    messages = [message(0, "assistant", 0, metadata=target("q01")), message(1, "learner", 20)]
    extended = session(seconds=900).model_copy(update={
        "timer_started_at": START + timedelta(seconds=180),
        "timer_ends_at": START + timedelta(seconds=480),
        "completion_reason": "timer_elapsed",
    })
    logs = [ResearchLog(action_type="session_timer_reset", payload={"changes": {
        "timer_started_at": {"before": START.isoformat(), "after": extended.timer_started_at.isoformat()}
    }})]
    learning = conversation_metrics(messages, extended, logs=logs, now=START + timedelta(seconds=1000))["learning"]

    assert learning["started_at"] == START.isoformat()
    assert learning["ended_at"] == extended.timer_ends_at.isoformat()
    assert learning["duration_seconds"] == 480
    assert learning["questions"][0]["duration_seconds"] == 480


@pytest.mark.parametrize("completion_seconds", [90, 308])
def test_non_timer_completion_keeps_actual_end(completion_seconds):
    messages = [message(0, "assistant", 0, metadata=target("q01"))]
    stopped = session(seconds=completion_seconds).model_copy(update={"completion_reason": "manual_stop"})
    learning = conversation_metrics(messages, stopped, now=START + timedelta(seconds=360))["learning"]

    assert learning["ended_at"] == stopped.completed_at.isoformat()
    assert learning["duration_seconds"] == completion_seconds


def test_missing_timestamps_and_negative_intervals_do_not_become_zero():
    assert conversation_metrics([])["learning"]["duration_seconds"] is None
    invalid = [message(0, "assistant", 20), message(1, "learner", 10), message(2, "assistant", 8)]
    trip = conversation_metrics(invalid)["round_trips"][0]
    assert trip["thinking_seconds"] is None
    assert trip["response_seconds"] is None
    assert trip["elapsed_seconds"] is None


@pytest.mark.parametrize("has_audit", [False, True])
def test_timer_reset_preserves_original_learning_start_and_prior_question_time(has_audit):
    messages = [message(0, "assistant", 0, metadata=target("q01")), message(1, "learner", 20),
                message(2, "assistant", 30, metadata=target("q01", completion_status="resolved", resolution_self_corrected=True))]
    reset = session(completed=False).model_copy(update={"timer_started_at": START + timedelta(seconds=60)})
    logs = [ResearchLog(action_type="session_timer_reset", payload={"changes": {
        "timer_started_at": {"before": START.isoformat(), "after": reset.timer_started_at.isoformat()}
    }})] if has_audit else []
    learning = conversation_metrics(messages, reset, logs=logs, now=START + timedelta(seconds=120))["learning"]
    assert learning["duration_seconds"] == 120
    assert learning["questions"][0]["duration_seconds"] == 30
    assert learning["timing_source"] == ("session_timer" if has_audit else "message_timestamps")


def test_assisted_correction_requires_positive_evidence_not_just_restatement_completion():
    messages = [message(0, "assistant", 0, metadata=target("q01")), message(1, "learner", 20),
                message(2, "assistant", 30, metadata=target("q01", completion_status="corrected_after_feedback", resolution_criteria_met=True))]
    assert conversation_metrics(messages, session())["learning"]["corrected_questions"] == 1
    messages[-1].metadata = target("q01", completion_status="corrected_after_feedback", resolution_criteria_met=False)
    assert conversation_metrics(messages, session())["learning"]["corrected_questions"] == 0
    messages[-1].metadata = target("q01", completion_status="feedback_completed", resolution_criteria_met=False)
    assert conversation_metrics(messages, session())["learning"]["corrected_questions"] == 0
