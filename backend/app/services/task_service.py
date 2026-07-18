"""Persistent asynchronous task submission workflow."""

from fastapi import HTTPException, status

from app.crud.protocols import RepositoryProtocol
from app.models.domain import ChatMessage, Conversation, ResearchLog, TaskAttempt, utc_now
from app.providers.llm.base import LLMProvider
from app.schemas.requests import TaskDraftRequest, TaskSubmitRequest
from app.schemas.responses import (
    TaskDraftResponse,
    TaskSubmissionAcceptedResponse,
    TaskSubmissionStatusResponse,
    TaskSubmitResponse,
)
from app.core.interaction_contract import initial_greeting_metadata
from app.services.session_runtime import expire_session_if_due
from app.services.task_judgement import enrich_task_judgement


class TaskService:
    """Persist task work first, then perform slow LLM calls out of request path."""

    def __init__(self, repository: RepositoryProtocol, llm_provider: LLMProvider) -> None:
        self.repository = repository
        self.llm_provider = llm_provider

    def save_draft(self, task_id: str, request: TaskDraftRequest) -> TaskDraftResponse:
        """Save a recoverable learner draft without invoking the LLM."""
        task, session = self._task_and_session(task_id, request.session_id, request.user_id)
        attempt = self.repository.get_task_attempt_for_session(session.id, task.id)
        if attempt and attempt.status in {"processing", "submitted"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task already submitted")

        if not attempt:
            attempt = TaskAttempt(
                task_id=task.id,
                event_id=task.event_id,
                session_id=session.id,
                user_id=request.user_id or session.user_id,
            )
        attempt.status = "in_progress"
        attempt.response_payload = request.response_payload
        attempt.judgement_payload = {}
        attempt.user_id = request.user_id or attempt.user_id or session.user_id
        saved = self.repository.save_task_attempt(attempt)
        self.repository.save_session(session)
        return TaskDraftResponse(attempt=saved)

    def queue_submission(
        self,
        task_id: str,
        request: TaskSubmitRequest,
    ) -> tuple[TaskSubmissionAcceptedResponse, bool]:
        """Persist a processing attempt and return before judgement/greeting begins."""
        task, session = self._task_and_session(task_id, request.session_id, request.user_id)
        if session.status in {"completed", "archived"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Experiment session is already closed")

        attempt = self.repository.get_task_attempt_for_session(session.id, task.id)
        if attempt and attempt.status == "submitted":
            return self._accepted(attempt), False
        if attempt and attempt.status == "processing":
            return self._accepted(attempt), False

        if not attempt:
            attempt = TaskAttempt(
                task_id=task.id,
                event_id=task.event_id,
                session_id=session.id,
                user_id=request.user_id or session.user_id,
            )
        attempt.status = "processing"
        attempt.response_payload = request.response_payload
        attempt.judgement_payload = {}
        attempt.submitted_at = None
        attempt.user_id = request.user_id or attempt.user_id or session.user_id
        attempt = self.repository.save_task_attempt(attempt)

        self.repository.log_research(
            ResearchLog(
                user_id=attempt.user_id,
                session_id=session.id,
                event_id=task.event_id,
                task_id=task.id,
                attempt_id=attempt.id,
                action_type="task_answer_changed",
                payload={"response_payload": request.response_payload},
            )
        )
        self.repository.log_research(
            ResearchLog(
                user_id=attempt.user_id,
                session_id=session.id,
                event_id=task.event_id,
                task_id=task.id,
                attempt_id=attempt.id,
                action_type="task_submission_queued",
                payload={"response_payload": request.response_payload},
            )
        )
        return self._accepted(attempt), True

    async def process_submission(self, attempt_id: str) -> None:
        """Perform judgement and greeting for a previously persisted processing attempt."""
        attempt = self.repository.get_task_attempt(attempt_id)
        if not attempt or attempt.status != "processing":
            return

        try:
            task = self.repository.get_event_task(attempt.task_id)
            session = self.repository.get_session(attempt.session_id) if attempt.session_id else None
            event = self.repository.get_event(attempt.event_id)
            if not task or not session or not event:
                raise RuntimeError("Task submission context is incomplete")
            condition = self.repository.get_condition_by_key(session.condition_key_snapshot)
            if not condition:
                raise RuntimeError("Experiment condition is missing")

            judgement = await self.llm_provider.judge_task_attempt(event, task, attempt.response_payload)
            judgement = enrich_task_judgement(task, attempt.response_payload, judgement)
            attempt.status = "submitted"
            attempt.judgement_payload = judgement
            attempt.submitted_at = utc_now()
            attempt = self.repository.save_task_attempt(attempt)

            session.status = "task_submitted"
            self.repository.save_session(session)
            self.repository.log_research(
                ResearchLog(
                    user_id=attempt.user_id,
                    session_id=session.id,
                    event_id=event.id,
                    task_id=task.id,
                    attempt_id=attempt.id,
                    action_type="task_submitted",
                    payload={"judgement": judgement},
                )
            )

            conversation = self.repository.get_conversation_by_session(session.id)
            if not conversation:
                conversation = self.repository.save_conversation(
                    Conversation(
                        event_id=event.id,
                        task_attempt_id=attempt.id,
                        session_id=session.id,
                        user_id=attempt.user_id,
                    )
                )

            personas = self.repository.list_personas(event.id)
            messages = self.repository.list_messages(conversation.id)
            if messages:
                greeting_message = messages[0]
            else:
                greeting = await self.llm_provider.generate_greeting(event, personas, condition, attempt)
                greeting_message = self._store_greeting(conversation.id, personas, condition, greeting, attempt)

            session.status = "conversation_started"
            self.repository.save_session(session)
            self.repository.log_research(
                ResearchLog(
                    user_id=attempt.user_id,
                    session_id=session.id,
                    event_id=event.id,
                    task_id=task.id,
                    attempt_id=attempt.id,
                    conversation_id=conversation.id,
                    message_id=greeting_message.id,
                    action_type="conversation_started",
                    payload={"condition_key": condition.condition_key},
                )
            )
        except Exception as exc:
            attempt.status = "failed"
            attempt.judgement_payload = {
                "error": "Task processing failed. The submission can be retried.",
                "error_type": type(exc).__name__,
            }
            self.repository.save_task_attempt(attempt)
            self.repository.log_research(
                ResearchLog(
                    user_id=attempt.user_id,
                    session_id=attempt.session_id,
                    event_id=attempt.event_id,
                    task_id=attempt.task_id,
                    attempt_id=attempt.id,
                    action_type="task_submission_failed",
                    payload={"error_type": type(exc).__name__},
                )
            )

    def submission_status(self, attempt_id: str) -> TaskSubmissionStatusResponse:
        """Load polling state and materialize the legacy full result once ready."""
        attempt = self.repository.get_task_attempt(attempt_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task attempt not found")

        result = self._submission_result(attempt) if attempt.status == "submitted" else None
        error = None
        if attempt.status == "failed":
            error = str(attempt.judgement_payload.get("error") or "Task processing failed")
        return TaskSubmissionStatusResponse(attempt=attempt, result=result, error=error)

    def _submission_result(self, attempt: TaskAttempt) -> TaskSubmitResponse | None:
        task = self.repository.get_event_task(attempt.task_id)
        event = self.repository.get_event(attempt.event_id)
        session = self.repository.get_session(attempt.session_id) if attempt.session_id else None
        conversation = self.repository.get_conversation_by_session(session.id) if session else None
        condition = self.repository.get_condition_by_key(session.condition_key_snapshot) if session else None
        if not task or not event or not session or not conversation or not condition:
            return None

        personas = self.repository.list_personas(event.id)
        history = self.repository.list_messages(conversation.id)
        if not history:
            return None
        return TaskSubmitResponse(
            attempt_id=attempt.id,
            conversation_id=conversation.id,
            event=event,
            task=task,
            personas=personas,
            condition=condition,
            attempt=attempt,
            judgement=attempt.judgement_payload,
            greeting=history[0].content,
            history=history,
        )

    def _task_and_session(self, task_id: str, session_id: str, user_id: str | None):
        task = self.repository.get_event_task(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        session = self.repository.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment session not found")
        if session.event_id != task.event_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task does not belong to session event")
        session = expire_session_if_due(self.repository, session)
        if session.status in {"completed", "archived"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Experiment session is already closed")
        if user_id and session.user_id and user_id != session.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session belongs to another Auth user")
        if user_id and not session.user_id:
            session.user_id = user_id
        return task, session

    @staticmethod
    def _accepted(attempt: TaskAttempt) -> TaskSubmissionAcceptedResponse:
        return TaskSubmissionAcceptedResponse(
            attempt_id=attempt.id,
            status=attempt.status,
            poll_url=f"/api/tasks/attempts/{attempt.id}",
        )

    def _store_greeting(
        self,
        conversation_id: str,
        personas,
        condition,
        greeting: str,
        attempt: TaskAttempt,
    ) -> ChatMessage:
        persona = personas[0] if condition.roleplay_enabled and personas else None
        message = ChatMessage(
            conversation_id=conversation_id,
            persona_id=persona.id if persona else None,
            speaker_type="persona" if persona else "assistant",
            speaker_name=persona.name if persona else ("AI Tutor" if condition.ebl_enabled else "AI Assistant"),
            sequence_index=self.repository.next_message_sequence(conversation_id),
            content=greeting,
            metadata={
                "condition_key": condition.condition_key,
                "task_attempt_id": attempt.id,
                "judgement": attempt.judgement_payload,
                **initial_greeting_metadata(condition, attempt, greeting),
            },
        )
        return self.repository.add_message(message)
