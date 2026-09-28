"""Administrator-only view of one participant's durable experiment progress."""

from fastapi import HTTPException

from app.core.research_reproducibility import get_session_task, stable_hash
from app.crud.protocols import RepositoryProtocol


class SessionMonitorService:
    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def _state(self, session_id: str) -> dict:
        session = self.repository.get_session(session_id)
        if not session:
            raise HTTPException(404, "Experiment session not found")
        attempt = self.repository.get_task_attempt_for_session(session_id)
        conversation = self.repository.get_conversation_by_session(session_id)
        messages = self.repository.list_messages(conversation.id) if conversation else []
        posttest = self.repository.get_posttest(session_id)
        if session.status == "archived":
            stage = "archived"
        elif posttest:
            stage = f"posttest_{posttest.stage}"
        elif session.status == "completed":
            stage = "completed"
        elif attempt and attempt.status == "submitted":
            stage = "conversation"
        else:
            stage = attempt.status if attempt else "in_progress"
        stamps = [session.updated_at]
        stamps.extend(item.updated_at for item in [attempt, conversation, posttest] if item)
        stamps.extend(message.created_at for message in messages)
        return {"session": session, "attempt": attempt, "conversation": conversation,
                "messages": messages, "posttest": posttest, "stage": stage,
                "updated_at": max(stamps).isoformat()}

    def change_token(self, session_id: str) -> dict:
        state = self._state(session_id)
        # Message operation_status can change without a new message timestamp.
        return {"session_id": session_id, "stage": state["stage"], "version": stable_hash(state)}

    def snapshot(self, session_id: str) -> dict:
        state = self._state(session_id)
        session, attempt = state["session"], state["attempt"]
        participant = self.repository.get_participant(session.participant_id) if session.participant_id else None
        if not participant and session.user_id and not session.is_admin_test:
            participant = self.repository.get_participant_by_auth_user(session.user_id)
        return {**state,
                "participant_code": participant.code if participant else ("ADMIN_TEST" if session.is_admin_test else "UNMAPPED"),
                "event": self.repository.get_event(session.event_id),
                "condition": self.repository.get_condition_by_key(session.condition_key_snapshot),
                "task": get_session_task(self.repository, session, attempt)}
