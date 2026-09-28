"""作答保存後初判；每题人工核准後準備開場，由受測者進入時啟動互動計時。
"""

from fastapi import HTTPException, status

from app.crud.protocols import RepositoryProtocol
from app.core.error_elicitation_contract import validate_task_answers
from app.services.learning_focus import build_learning_focus
from app.models.domain import ResearchLog, TaskAttempt, utc_now
from app.providers.llm.base import LLMProvider
from app.schemas.requests import TaskDraftRequest, TaskSubmitRequest
from app.schemas.responses import TaskDraftResponse, TaskSubmissionAcceptedResponse, TaskSubmissionStatusResponse, TaskSubmitResponse
from app.services.conversation_opening_service import ConversationOpeningService
from app.services.session_runtime import EXPERIMENT_CHAT_DURATION_MINUTES, expire_session_if_due
from app.services.task_pipeline import TaskPipeline


class TaskService:
    """管理草稿、提交與背景處理；慢速 LLM 呼叫不放在提交請求裡等待。"""

    def __init__(
        self,
        repository: RepositoryProtocol,
        llm_provider: LLMProvider,
        opening_service: ConversationOpeningService,
    ) -> None:
        self.repository = repository
        self.llm_provider = llm_provider
        self.opening_service = opening_service
        self.pipeline = TaskPipeline(repository, llm_provider, opening_service)

    def save_draft(self, task_id: str, request: TaskDraftRequest) -> TaskDraftResponse:
        """只保存可恢復的作答草稿，不呼叫 LLM。"""
        task, session = self._task_and_session(task_id, request.session_id, request.user_id)
        self._validate_answers(task.evaluation_payload, request.response_payload, complete=False)
        attempt = self.repository.get_task_attempt_for_session(session.id, task.id)
        if attempt and attempt.status != "in_progress":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task already submitted")

        if not attempt:
            attempt = TaskAttempt(
                task_id=task.id,
                event_id=task.event_id,
                session_id=session.id,
                user_id=request.user_id or session.user_id,
            )
        attempt.status = "in_progress"
        if attempt.response_payload != request.response_payload:
            attempt.judgement_payload = {}
        attempt.response_payload = request.response_payload
        attempt.user_id = request.user_id or attempt.user_id or session.user_id
        saved = self.repository.save_task_attempt(attempt)
        self.repository.save_session(session)
        return TaskDraftResponse(attempt=saved)

    def queue_submission(
        self,
        task_id: str,
        request: TaskSubmitRequest,
    ) -> tuple[TaskSubmissionAcceptedResponse, bool]:
        """先存作答並回傳進度；回傳的布林值表示是否需要啟動新的背景工作。"""
        task, session = self._task_and_session(task_id, request.session_id, request.user_id)
        if session.status in {"completed", "archived"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Experiment session is already closed")

        attempt = self.repository.get_task_attempt_for_session(session.id, task.id)
        # 重新整理或重送不能多建一份作答，也不能重複排程付費判題。
        if attempt and attempt.status != "in_progress":
            if attempt.response_payload != request.response_payload:
                raise HTTPException(409, "Submitted task answers cannot be changed")
            if attempt.status == "failed":
                return self.retry_submission(attempt.id), True
            return self._accepted(attempt), False

        self._validate_answers(task.evaluation_payload, request.response_payload, complete=True)

        if not attempt:
            attempt = TaskAttempt(
                task_id=task.id,
                event_id=task.event_id,
                session_id=session.id,
                user_id=request.user_id or session.user_id,
            )
        attempt.status = "processing"
        if attempt.response_payload != request.response_payload:
            attempt.judgement_payload = {}
        attempt.response_payload = request.response_payload
        attempt.submitted_at = utc_now()
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
        """Run only the missing persisted checkpoint; human approval is never automatic."""
        self.pipeline.llm_provider = self.llm_provider
        self.pipeline.opening_service = self.opening_service
        await self.pipeline.process(attempt_id)

    def retry_submission(self, attempt_id: str) -> TaskSubmissionAcceptedResponse:
        attempt = self.repository.get_task_attempt(attempt_id)
        if not attempt:
            raise HTTPException(404, "Task attempt not found")
        self._task_and_session(attempt.task_id, attempt.session_id, attempt.user_id)
        if attempt.status == "failed":
            attempt = attempt.model_copy(deep=True)
            attempt.status = "preparing_chat" if attempt.review_payload.get("approved_at") else "processing"
            attempt.pipeline_error = {}
            attempt = self.repository.save_task_attempt(attempt)
        return self._accepted(attempt)

    def enter_interaction(self, attempt_id: str) -> TaskSubmitResponse:
        attempt = self.repository.get_task_attempt(attempt_id)
        if not attempt:
            raise HTTPException(404, "Task attempt not found")
        self._task_and_session(attempt.task_id, attempt.session_id, attempt.user_id)
        if attempt.status not in {"ready", "submitted"}:
            raise HTTPException(409, "Conversation is not ready")
        if attempt.status == "ready" and not attempt.review_payload.get("approved_at"):
            raise HTTPException(409, "Human approval is required")
        previous_status = attempt.status
        started = self.repository.start_task_interaction(attempt.id, EXPERIMENT_CHAT_DURATION_MINUTES)
        if not started:
            raise HTTPException(409, "Conversation is not ready")
        result = self._submission_result(started)
        if not result:
            raise HTTPException(409, "Conversation opening is not available")
        if previous_status == "ready":
            session = self.repository.get_session(attempt.session_id)
            for action, payload in (
                ("session_timer_started", {"duration_minutes": EXPERIMENT_CHAT_DURATION_MINUTES,
                 "timer_ends_at": session.timer_ends_at.isoformat(), "trigger": "learner_entered"}),
                ("conversation_started", {"condition_key": session.condition_key_snapshot}),
            ):
                self.repository.log_research(ResearchLog(
                    user_id=attempt.user_id, session_id=attempt.session_id, event_id=attempt.event_id,
                    task_id=attempt.task_id, attempt_id=attempt.id, conversation_id=result.conversation_id,
                    action_type=action, payload=payload,
                ))
        return result

    def submission_status(self, attempt_id: str) -> TaskSubmissionStatusResponse:
        """Load polling state and materialize the legacy full result once ready."""
        attempt = self.repository.get_task_attempt(attempt_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task attempt not found")

        result = self._submission_result(attempt) if attempt.status == "submitted" else None
        error = None
        if attempt.status == "failed":
            error = str(attempt.pipeline_error.get("message") or "Task processing failed")
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
            learning_focus=build_learning_focus(condition, attempt, history),
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
    def _validate_answers(evaluation_payload: dict, response_payload: dict, *, complete: bool) -> None:
        try:
            validate_task_answers(evaluation_payload, response_payload, complete=complete)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc

    @staticmethod
    def _accepted(attempt: TaskAttempt) -> TaskSubmissionAcceptedResponse:
        return TaskSubmissionAcceptedResponse(
            attempt_id=attempt.id,
            status=attempt.status,
            poll_url=f"/api/tasks/attempts/{attempt.id}",
        )
