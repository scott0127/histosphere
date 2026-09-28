"""Derive admin analytics from persisted messages without inventing historical usage.

Characters are Unicode code points excluding whitespace (punctuation is included).
An exchange is one learner submission with a delivered, non-fallback AI response.
Learning time is elapsed wall time, including reading, thinking and response waits;
it is not a measurement of active attention. No new clock runs when reading exports.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from app.models.domain import ChatMessage, ExperimentSession, ResearchLog
from app.services.llm_usage_summary import usage_breakdown


def _stamp(value: Any) -> datetime | None:
    try:
        result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _seconds(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None or end < start:
        return None
    return round((end - start).total_seconds(), 3)


def _number(value: Any) -> int | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
        return int(value)
    return None


def _assistant(message: ChatMessage) -> bool:
    return message.speaker_type in {"assistant", "persona"} and not message.metadata.get("system_fallback")


def _call(message: ChatMessage) -> dict[str, Any]:
    value = message.metadata.get("llm_call")
    return value if isinstance(value, dict) else {}


def _usage_complete(call: dict[str, Any]) -> bool:
    rows = usage_breakdown([call])
    return _number(call.get("total_tokens")) is not None and all(
        row.requests == row.token_reported_requests for row in rows
    )


def _timing(message: ChatMessage) -> dict[str, Any]:
    value = message.metadata.get("exchange_timing") or message.metadata.get("opening_timing")
    return value if isinstance(value, dict) else {}


def _response_at(message: ChatMessage) -> datetime:
    return _stamp(_timing(message).get("response_completed_at")) or _stamp(message.created_at)


def _question_id(message: ChatMessage) -> str | None:
    value = message.metadata.get("learning_target_question_id") or message.metadata.get("target_question_id")
    return value if isinstance(value, str) and value else None


def _round_trips(messages: list[ChatMessage], interaction_start: datetime | None = None) -> list[dict[str, Any]]:
    by_id = {message.id: message for message in messages}
    positions = {message.id: index for index, message in enumerate(messages)}
    used_responses: set[str] = set()
    result = []
    previous_assistant = None
    for position, learner in enumerate(messages):
        if _assistant(learner):
            previous_assistant = learner
            continue
        if learner.speaker_type != "learner":
            continue
        response_id = learner.metadata.get("response_message_id")
        response = by_id.get(response_id)
        fallback_response = bool(response and response.metadata.get("system_fallback"))
        if response is not None and (not _assistant(response) or positions[response.id] <= position):
            response = None
        # A persisted link to a fallback/missing response is not a completed exchange.
        if response is None and not response_id and learner.operation_status != "failed":
            for candidate in messages[position + 1:]:
                if candidate.speaker_type == "learner":
                    break
                if _assistant(candidate) and (
                    not learner.client_request_id or not candidate.client_request_id
                    or learner.client_request_id == candidate.client_request_id
                ):
                    response = candidate
                    break
        if response is not None and response.id in used_responses:
            response = None
        timing = _timing(response) if response else _timing(learner)
        request_at = (
            _stamp(timing.get("original_request_started_at"))
            or _stamp(timing.get("request_started_at")) or _stamp(learner.created_at)
        )
        response_at = _response_at(response) if response else None
        preceding_at = _response_at(previous_assistant) if previous_assistant else None
        if (not result and preceding_at and interaction_start and request_at >= interaction_start
                and previous_assistant.metadata.get("judgement", {}).get("decision_source") == "human_review"):
            # A prepared opening is hidden until the learner enters; that waiting is not thinking time.
            preceding_at = max(preceding_at, interaction_start)
        status = "completed" if response else (
            "failed" if fallback_response or learner.operation_status == "failed" or learner.metadata.get("response_status") == "failed"
            else "pending" if learner.operation_status in {"processing", "pending"}
            else "unmatched"
        )
        latency = timing.get("response_latency_ms")
        result.append({
            "index": len(result) + 1,
            "learner_message_id": learner.id,
            "assistant_message_id": response.id if response else None,
            "question_id": _question_id(learner) or (_question_id(response) if response else None),
            "status": status,
            "started_at": request_at.isoformat(),
            "response_at": response_at.isoformat() if response_at else None,
            "thinking_seconds": _seconds(preceding_at, request_at),
            "response_seconds": _seconds(request_at, response_at),
            "generation_seconds": round(float(latency) / 1000, 3) if _number(latency) is not None else None,
            "elapsed_seconds": _seconds(preceding_at or request_at, response_at),
            "timing_source": "recorded" if _stamp(timing.get("response_completed_at")) else "message_timestamps" if response else "unavailable",
        })
        if response:
            used_responses.add(response.id)
    return result


def _learning(
    messages: list[ChatMessage],
    rounds: list[dict[str, Any]],
    session: ExperimentSession | None,
    now: datetime,
    logs: list[ResearchLog],
) -> dict[str, Any]:
    assistant = [message for message in messages if _assistant(message)]
    start = _stamp(session.timer_started_at) if session else None
    if session and not start and assistant and assistant[0].metadata.get("judgement", {}).get("decision_source") == "human_review":
        assistant = []
    source = "session_timer" if start else "message_timestamps" if assistant else "unavailable"
    timer_starts = [start] if start else []
    for log in logs:
        if log.action_type != "session_timer_reset":
            continue
        change = log.payload.get("changes", {}).get("timer_started_at", {})
        if isinstance(change, dict):
            original = _stamp(change.get("before"))
            if original:
                timer_starts.append(original)
    if timer_starts:
        start = min(timer_starts)
    # Old reset audit logs may be missing. A learner submission before the
    # current timer proves that this was not the original interaction start.
    if start and assistant and any(m.speaker_type == "learner" and _stamp(m.created_at) < start for m in messages):
        start = min(start, _response_at(assistant[0]))
        source = "message_timestamps"
    start = start or (_response_at(assistant[0]) if assistant else None)
    end = _stamp(session.completed_at) if session else None
    deadline = _stamp(session.timer_ends_at) if session else None
    complete = bool(end or (session and session.status in {"completed", "archived"}))
    # Timer completion can be persisted long after the deadline (for example,
    # after a server restart). Use the current, possibly reset deadline rather
    # than that observation time. Late replies retain their actual round-trip
    # timing and accepted corrections still count below.
    if end and deadline and session.completion_reason == "timer_elapsed":
        end = min(end, deadline)
    if end is None and deadline and deadline <= now:
        end = deadline
        complete = True
    if end is None:
        end = (_stamp(messages[-1].created_at) if messages else None) if complete or not session or not session.timer_started_at else now
    duration = _seconds(start, end)
    questions: dict[str, dict[str, Any]] = {}
    prior_at = start
    current_id = None

    def ensure(question_id: str, at: datetime, message: ChatMessage) -> dict[str, Any]:
        if question_id not in questions:
            questions[question_id] = {
                "question_id": question_id,
                "origin": "third_party" if message.metadata.get("error_source") == "researcher_authored_fallback" else "learner",
                "started_at": at.isoformat(), "ended_at": None,
                "duration_seconds": None, "outcome": "in_progress", "completed_exchanges": 0,
                "timing_source": "recorded" if "learning_target_question_id" in message.metadata else "message_timestamps",
            }
        return questions[question_id]

    for message in assistant:
        at = _response_at(message)
        if end is not None:
            at = min(at, end)
        metadata = message.metadata
        question_id = _question_id(message)
        if not question_id:
            prior_at = at
            continue
        if question_id in questions and questions[question_id]["ended_at"] is not None:
            # Old replays/duplicate terminal replies cannot reopen a completed
            # target, downgrade its result, or prematurely close the next target.
            prior_at = at
            continue
        if current_id and current_id != question_id and questions[current_id]["ended_at"] is None:
            questions[current_id]["ended_at"] = (prior_at or at).isoformat()
            questions[current_id]["outcome"] = "unresolved"
        # A new question becomes a learning opportunity when its prompt is
        # delivered. Only an explicit next_target_started starts it earlier in
        # the preceding terminal reply. The initial opening uses the timer start.
        question = ensure(question_id, (start or at) if message is assistant[0] else at, message)
        current_id = question_id
        held = isinstance(metadata.get("answer_delivery"), dict) and metadata["answer_delivery"].get("state_held")
        completion = metadata.get("completion_status")
        if not held and completion in {"resolved", "complete", "corrected_after_feedback", "feedback_completed", "unresolved_after_max_support"}:
            successful = completion in {"resolved", "complete", "corrected_after_feedback"} and (
                metadata.get("resolution_criteria_met") is True
                or metadata.get("resolution_self_corrected") is True
                or metadata.get("resolution_outcome") == "learner_resolved"
            )
            # Restating supplied feedback is recorded separately; it cannot be
            # promoted to independent correction merely because the queue moved.
            question["outcome"] = "corrected" if successful else "feedback_completed" if completion in {"corrected_after_feedback", "feedback_completed"} else "unresolved"
            question["ended_at"] = question["ended_at"] or at.isoformat()
        next_id = metadata.get("next_target_question_id")
        if not held and metadata.get("next_target_started") is True and isinstance(next_id, str) and next_id:
            ensure(next_id, at, message)
            current_id = next_id
        prior_at = at

    for question in questions.values():
        if question["ended_at"] is None and end:
            question["ended_at"] = end.isoformat()
            if complete:
                question["outcome"] = "unresolved"
        question["duration_seconds"] = _seconds(_stamp(question["started_at"]), _stamp(question["ended_at"]))
        question["completed_exchanges"] = sum(
            row["status"] == "completed" and row["question_id"] == question["question_id"] for row in rounds
        )
    corrected = sum(question["outcome"] == "corrected" for question in questions.values())
    denominator = max(corrected, 1)
    mode = next((m.metadata.get("interaction_mode") for m in assistant if m.metadata.get("interaction_mode") in {"scaffold", "standard_chat"}), None)
    return {
        "applicable": bool(questions), "interaction_mode": mode,
        "started_at": start.isoformat() if start else None,
        "ended_at": end.isoformat() if end else None,
        "observed_at": now.isoformat(), "duration_seconds": duration,
        "corrected_questions": corrected, "denominator": denominator,
        "average_seconds_per_question": round(duration / denominator, 3) if duration is not None and questions else None,
        "timing_source": source, "is_complete": complete, "questions": list(questions.values()),
    }


def conversation_metrics(
    messages: list[ChatMessage], session: ExperimentSession | None = None, *, now: datetime | None = None,
    logs: list[ResearchLog] | None = None,
) -> dict[str, Any]:
    """Additional API/CSV metrics; unknown usage stays null rather than zero."""
    messages = sorted(messages, key=lambda message: (message.sequence_index, _stamp(message.created_at)))
    now = _stamp(now) or datetime.now(timezone.utc)
    metrics = []
    counts = {"learner": 0, "assistant": 0, "system": 0}
    for message in messages:
        characters = sum(not character.isspace() for character in message.content)
        counts["learner" if message.speaker_type == "learner" else "assistant" if _assistant(message) else "system"] += characters
        call = _call(message) if _assistant(message) else {}
        metrics.append({
            "message_id": message.id, "characters": characters,
            "total_tokens": _number(call.get("total_tokens")),
            "completion_tokens": _number(call.get("completion_tokens")),
            "token_usage_complete": _usage_complete(call) if call else False,
        })
    ai_metrics = [row for message, row in zip(messages, metrics) if _assistant(message)]
    reported = [row for row in ai_metrics if row["total_tokens"] is not None]
    known_tokens = sum(row["total_tokens"] for row in reported)
    rounds = _round_trips(messages, _stamp(session.timer_started_at) if session else None)
    return {
        "total_characters": sum(counts.values()), "learner_characters": counts["learner"],
        "assistant_characters": counts["assistant"], "system_characters": counts["system"],
        "completed_exchanges": sum(row["status"] == "completed" for row in rounds),
        "assistant_total_tokens": known_tokens if reported else None,
        "assistant_average_tokens": round(known_tokens / len(reported), 2) if reported else None,
        "assistant_token_usage_complete": bool(ai_metrics) and all(row["token_usage_complete"] for row in ai_metrics),
        "message_metrics": metrics, "round_trips": rounds,
        "learning": _learning(messages, rounds, session, now, logs or []),
    }
