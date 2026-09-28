"""Shared experiment session completion and timer invariants."""

from app.crud.protocols import RepositoryProtocol
from app.models.domain import ExperimentSession, ResearchLog, utc_now


EXPERIMENT_CHAT_DURATION_MINUTES = 10


def complete_session(
    repository: RepositoryProtocol,
    session: ExperimentSession,
    *,
    reason: str,
) -> ExperimentSession:
    """Complete a session once and record the reason without deleting runtime data."""
    if session.status in {"completed", "archived"}:
        return session
    now = utc_now()
    session.status = "completed"
    session.completed_at = now
    session.completion_reason = reason
    saved = repository.save_session(session)
    repository.log_research(
        ResearchLog(
            user_id=saved.user_id,
            session_id=saved.id,
            event_id=saved.event_id,
            action_type="session_completed",
            payload={"completion_reason": reason},
        )
    )
    return saved


def expire_session_if_due(
    repository: RepositoryProtocol,
    session: ExperimentSession,
) -> ExperimentSession:
    """Lazily enforce an enabled timer at every runtime boundary."""
    if (
        session.timer_ends_at
        and session.status not in {"completed", "archived"}
        and session.timer_ends_at <= utc_now()
    ):
        return complete_session(repository, session, reason="timer_elapsed")
    return session
