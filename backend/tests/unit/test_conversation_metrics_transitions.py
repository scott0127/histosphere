"""Question timing follows delivered introductions and immutable terminal outcomes."""

from datetime import timedelta

from app.services.conversation_metrics import conversation_metrics
from tests.unit.test_conversation_metrics import START, message, session, target


def test_repeated_old_terminal_does_not_close_new_question_or_erase_correction():
    messages = [
        message(0, "assistant", 0, metadata=target("q01")),
        message(1, "learner", 20),
        message(2, "assistant", 30, metadata=target(
            "q01", completion_status="resolved", resolution_criteria_met=True,
            next_target_question_id="q02", next_target_started=True,
        )),
        # Legacy histories can repeat a closed target. Its first terminal result
        # remains authoritative, and q02's ongoing interval must remain open.
        message(3, "learner", 35),
        message(4, "assistant", 40, metadata=target(
            "q01", completion_status="feedback_completed", resolution_criteria_met=False,
            next_target_question_id="q02", next_target_started=True,
        )),
        message(5, "learner", 60),
        message(6, "assistant", 70, metadata=target(
            "q02", completion_status="resolved", resolution_criteria_met=True,
        )),
    ]
    learning = conversation_metrics(messages, session(), now=START + timedelta(seconds=180))["learning"]
    assert learning["corrected_questions"] == 2
    assert learning["average_seconds_per_question"] == 60
    first, second = learning["questions"]
    assert first["outcome"] == second["outcome"] == "corrected"
    assert first["duration_seconds"] == 30
    assert second["started_at"] == (START + timedelta(seconds=30)).isoformat()
    assert second["ended_at"] == (START + timedelta(seconds=70)).isoformat()
    assert second["duration_seconds"] == 40


def test_next_question_without_confirmed_bridge_starts_when_it_is_first_delivered():
    messages = [
        message(0, "assistant", 0, metadata=target("q01")),
        message(1, "learner", 20),
        message(2, "assistant", 30, metadata=target(
            "q01", completion_status="resolved", resolution_criteria_met=True,
            next_target_question_id="q02", next_target_started=False,
        )),
        message(3, "learner", 50),
        message(4, "assistant", 60, metadata=target("q02", completion_status="continue")),
        message(5, "learner", 65),
        message(6, "assistant", 70, metadata=target(
            "q02", completion_status="resolved", resolution_criteria_met=True,
        )),
    ]
    learning = conversation_metrics(messages, session(), now=START + timedelta(seconds=180))["learning"]
    assert learning["duration_seconds"] == 120
    assert learning["corrected_questions"] == 2
    assert learning["average_seconds_per_question"] == 60
    first, second = learning["questions"]
    assert first["duration_seconds"] == 30
    assert second["started_at"] == (START + timedelta(seconds=60)).isoformat()
    assert second["duration_seconds"] == 10


def test_legacy_restatement_without_assessment_does_not_count_as_success():
    messages = [
        message(0, "assistant", 0, metadata=target("q01")),
        message(1, "learner", 20),
        message(2, "assistant", 30, metadata=target(
            "q01", completion_status="corrected_after_feedback",
            resolution_outcome="corrected_after_feedback", resolution_criteria_met=False,
        )),
    ]
    learning = conversation_metrics(messages, session(), now=START + timedelta(seconds=180))["learning"]
    assert learning["corrected_questions"] == 0
    assert learning["denominator"] == 1
    assert learning["average_seconds_per_question"] == 120
    assert learning["questions"][0]["outcome"] == "feedback_completed"
