import pytest

from app.db.in_memory import InMemoryRepository
from app.models.domain import Conversation, TaskAttempt


def test_session_has_only_one_attempt_and_one_conversation():
    repository = InMemoryRepository()
    attempt = TaskAttempt(
        session_id="session-1",
        task_id="task-1",
        event_id="event-1",
    )
    repository.save_task_attempt(attempt)
    repository.save_task_attempt(attempt)

    with pytest.raises(ValueError, match="one task attempt"):
        repository.save_task_attempt(
            TaskAttempt(
                session_id="session-1",
                task_id="task-1",
                event_id="event-1",
            )
        )

    conversation = Conversation(
        session_id="session-1",
        task_attempt_id=attempt.id,
        event_id="event-1",
    )
    repository.save_conversation(conversation)
    repository.save_conversation(conversation)

    with pytest.raises(ValueError, match="one conversation"):
        repository.save_conversation(
            Conversation(
                session_id="session-1",
                task_attempt_id=attempt.id,
                event_id="event-1",
            )
        )
