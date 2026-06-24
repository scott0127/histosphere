"""Session progress service.

本模組把既有 experiment_sessions、task_attempts 與 conversations
組合成前端可恢復的學習進度。它不建立新的實驗資料，只讀取與整理
已存在的正式資料來源。
"""

from fastapi import HTTPException, status

from app.crud.protocols import RepositoryProtocol
from app.models.domain import EventTask
from app.schemas.responses import SessionStateResponse, UserProgressItem, UserProgressResponse


class SessionService:
    """讀取 learner session 狀態，供首頁、task 頁與重新整理後恢復流程。"""

    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def load_state(self, session_id: str) -> SessionStateResponse:
        """載入單一 session 的完整狀態。"""
        session = self.repository.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment session not found")

        event = self.repository.get_event(session.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        task = self.repository.get_latest_event_task(event.id)
        condition = self.repository.get_condition_by_key(session.condition_key_snapshot)
        attempt = self.repository.get_task_attempt_for_session(session.id, task.id if task else None)
        conversation = self.repository.get_conversation_by_session(session.id)

        return SessionStateResponse(
            session=session,
            event=event,
            task=task,
            personas=self.repository.list_personas(event.id),
            condition=condition,
            attempt=attempt,
            conversation_id=conversation.id if conversation else None,
        )

    def user_progress(self, user_id: str) -> UserProgressResponse:
        """列出某位受測者在各事件與 condition 下的最新進度。"""
        if not user_id.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")

        progress: list[UserProgressItem] = []
        for session in self.repository.list_sessions_for_user(user_id.strip()):
            task = self.repository.get_latest_event_task(session.event_id)
            attempt = self.repository.get_task_attempt_for_session(session.id, task.id if task else None)
            conversation = self.repository.get_conversation_by_session(session.id)
            progress.append(
                UserProgressItem(
                    event_id=session.event_id,
                    condition_key=session.condition_key_snapshot,
                    session_id=session.id,
                    task_id=task.id if isinstance(task, EventTask) else None,
                    attempt_id=attempt.id if attempt else None,
                    conversation_id=conversation.id if conversation else None,
                    status=self._public_status(
                        session.status,
                        attempt.status if attempt else None,
                        conversation is not None,
                    ),
                    updated_at=session.updated_at.isoformat(),
                )
            )
        return UserProgressResponse(progress=progress)

    @staticmethod
    def _public_status(session_status: str, attempt_status: str | None, has_conversation: bool) -> str:
        """把後端 session 狀態轉成首頁需要的穩定顯示狀態。"""
        if session_status == "archived":
            return "archived"
        if session_status == "completed":
            return "completed"
        if has_conversation or session_status == "conversation_started":
            return "chat_started"
        if attempt_status == "submitted" or session_status == "task_submitted":
            return "task_submitted"
        if attempt_status == "in_progress":
            return "task_draft"
        return "task_started"
