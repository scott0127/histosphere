"""Session progress service.

本模組把既有 experiment_sessions、task_attempts 與 conversations
組合成前端可恢復的學習進度。它不建立新的實驗資料，只讀取與整理
已存在的正式資料來源。
"""

from datetime import timedelta

from fastapi import HTTPException, status

from app.core.research_audit import build_change_payload
from app.core.research_reproducibility import record_session_material_snapshot
from app.crud.protocols import RepositoryProtocol
from app.models.domain import EventTask, ExperimentSession, ResearchLog, utc_now
from app.schemas.responses import (
    SessionRestartResponse,
    SessionStateResponse,
    UserProgressItem,
    UserProgressResponse,
)
from app.services.session_runtime import EXPERIMENT_CHAT_DURATION_MINUTES, expire_session_if_due


class SessionService:
    """讀取 learner session 狀態，供首頁、task 頁與重新整理後恢復流程。"""

    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def load_state(self, session_id: str) -> SessionStateResponse:
        """載入單一 session 的完整狀態。"""
        session = self.repository.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment session not found")

        session = expire_session_if_due(self.repository, session)
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
        for stored_session in self.repository.list_sessions_for_user(user_id.strip()):
            session = expire_session_if_due(self.repository, stored_session)
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

    def reset_timer(self, session_id: str) -> ExperimentSession:
        """由 Admin 將可對話的 session 明確重置為新的五分鐘倒數。"""
        session = self.repository.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment session not found")
        if session.status == "archived":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived session cannot be resumed")
        if session.status == "completed" and session.completion_reason != "timer_elapsed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only a timer-completed session can reset its countdown",
            )
        if not self.repository.get_conversation_by_session(session.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The countdown starts after the Chat stage is ready",
            )
        before = session.model_copy(deep=True)
        now = utc_now()
        session.status = "conversation_started"
        session.timer_started_at = now
        session.timer_ends_at = now + timedelta(minutes=EXPERIMENT_CHAT_DURATION_MINUTES)
        session.completed_at = None
        session.completion_reason = None
        saved = self.repository.save_session(session)
        self.repository.log_research(
            ResearchLog(
                user_id=saved.user_id,
                session_id=saved.id,
                event_id=saved.event_id,
                action_type="session_timer_reset",
                payload=build_change_payload(
                    before=before,
                    after=saved,
                    fields=[
                        "status",
                        "timer_started_at",
                        "timer_ends_at",
                        "completed_at",
                        "completion_reason",
                    ],
                    subject={
                        "session_id": saved.id,
                        "duration_minutes": EXPERIMENT_CHAT_DURATION_MINUTES,
                        "trigger": "admin",
                    },
                ),
            )
        )
        return saved

    def restart_session(self, session_id: str) -> SessionRestartResponse:
        """封存同一受測者在同事件的有效 session，再建立一筆乾淨 session。"""
        source_session = self.repository.get_session(session_id)
        if not source_session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment session not found")

        event = self.repository.get_event(source_session.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        if event.archived_at:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Restore the historical event before restarting its session.",
            )

        if source_session.user_id:
            candidates = [
                session
                for session in self.repository.list_sessions_for_user(source_session.user_id)
                if session.event_id == source_session.event_id and session.status != "archived"
            ]
        else:
            candidates = [source_session] if source_session.status != "archived" else []

        now = utc_now()
        archived_sessions: list[ExperimentSession] = []
        for session in candidates:
            session.status = "archived"
            session.completed_at = session.completed_at or now
            session.completion_reason = "admin_restart"
            session.timer_started_at = None
            session.timer_ends_at = None
            archived_sessions.append(self.repository.save_session(session))

            # 對話一併停止寫入，但 task、訊息與研究紀錄全部保留。
            conversation = self.repository.get_conversation_by_session(session.id)
            if conversation and conversation.status != "archived":
                conversation.status = "archived"
                conversation.archived_at = now
                self.repository.save_conversation(conversation)

        new_session = self.repository.save_session(
            ExperimentSession(
                condition_id=source_session.condition_id,
                condition_key_snapshot=source_session.condition_key_snapshot,
                user_id=source_session.user_id,
                event_id=source_session.event_id,
            )
        )
        record_session_material_snapshot(self.repository, new_session)
        self.repository.log_research(
            ResearchLog(
                user_id=new_session.user_id,
                session_id=new_session.id,
                event_id=new_session.event_id,
                action_type="session_restarted",
                payload={
                    "source_session_id": source_session.id,
                    "archived_session_ids": [session.id for session in archived_sessions],
                    "new_session_id": new_session.id,
                    "condition_key": new_session.condition_key_snapshot,
                },
            )
        )
        return SessionRestartResponse(
            archived_sessions=archived_sessions,
            new_session=new_session,
        )

    def expire_due_sessions(self) -> int:
        """Complete all due five-minute timers; used by the background worker."""
        completed = 0
        for session in self.repository.list_sessions():
            previous_status = session.status
            updated = expire_session_if_due(self.repository, session)
            if previous_status != "completed" and updated.status == "completed":
                completed += 1
        return completed

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
