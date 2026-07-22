"""Conversation loading and compatibility creation service.

本模組負責讀取 conversation 狀態，供前端聊天頁重新載入。
V1 正常流程由 TaskService 在 learner 完成 task 後建立 conversation；
create_conversation 主要保留給相容舊 API 或管理端手動建立。
"""

from fastapi import HTTPException, status

from app.models.domain import ChatMessage, Conversation
from app.schemas.responses import ConversationCreateResponse, ConversationLoadResponse
from app.crud.protocols import RepositoryProtocol
from app.services.conversation_opening_service import ConversationOpeningService
from app.services.session_runtime import expire_session_if_due


class ConversationService:
    """管理 conversation 建立與回放資料載入。"""

    def __init__(
        self,
        repository: RepositoryProtocol,
        opening_service: ConversationOpeningService,
    ) -> None:
        self.repository = repository
        self.opening_service = opening_service

    async def create_conversation(
        self,
        event_id: str,
        task_attempt_id: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> ConversationCreateResponse:
        """相容性建立 conversation；新版主要流程通常不直接呼叫此方法。"""
        event = self.repository.get_event(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        personas = self.repository.list_personas(event.id)

        attempt = self.repository.get_task_attempt(task_attempt_id) if task_attempt_id else None
        session = self.repository.get_session(session_id) if session_id else None
        condition = self.repository.get_condition_by_key(session.condition_key_snapshot) if session else None
        if not condition or not attempt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A task attempt and experiment session are required to create a conversation",
            )
        if event.id != session.event_id or event.id != attempt.event_id or attempt.session_id != session.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event, task attempt, and experiment session must belong to the same workflow",
            )
        if attempt.status != "submitted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Task submission must finish before creating a conversation",
            )
        if user_id and session.user_id and user_id != session.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session belongs to another Auth user")

        conversation = self.repository.get_conversation_by_session(session.id)
        existing_history = self.repository.list_messages(conversation.id) if conversation else []
        if existing_history:
            return ConversationCreateResponse(
                conversation_id=conversation.id,
                event=event,
                personas=personas,
                condition=condition,
                greeting=existing_history[0].content,
                history=existing_history,
            )

        opening = await self.opening_service.generate(
            event=event,
            personas=personas,
            condition=condition,
            attempt=attempt,
        )
        greeting = opening.generation.response
        if not conversation:
            conversation = self.repository.save_conversation(
                Conversation(
                    event_id=event.id,
                    task_attempt_id=attempt.id,
                    session_id=session.id,
                    user_id=user_id or session.user_id,
                )
            )

        greeting_message = ChatMessage(
            conversation_id=conversation.id,
            persona_id=opening.persona.id if opening.persona else None,
            speaker_type="persona" if opening.persona else "assistant",
            speaker_name=opening.persona.name if opening.persona else ("AI Tutor" if condition.ebl_enabled else "AI Assistant"),
            sequence_index=self.repository.next_message_sequence(conversation.id),
            content=greeting,
            annotations=opening.generation.annotations,
            metadata={
                "condition_key": condition.condition_key,
                "task_attempt_id": attempt.id,
                **opening.metadata,
            },
        )
        self.repository.add_message(greeting_message)
        session.status = "conversation_started"
        self.repository.save_session(session)
        return ConversationCreateResponse(
            conversation_id=conversation.id,
            event=event,
            personas=personas,
            condition=condition,
            greeting=greeting,
            history=[greeting_message],
        )

    def load_conversation(self, conversation_id: str) -> ConversationLoadResponse:
        """載入聊天頁需要的 event、personas、messages、condition 與 task_attempt。"""
        conversation = self.repository.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        event = self.repository.get_event(conversation.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        session = self.repository.get_session(conversation.session_id) if conversation.session_id else None
        if session:
            session = expire_session_if_due(self.repository, session)
        condition = self.repository.get_condition_by_key(session.condition_key_snapshot) if session else None
        task_attempt = (
            self.repository.get_task_attempt(conversation.task_attempt_id)
            if conversation.task_attempt_id
            else None
        )
        task = (
            self.repository.get_event_task(task_attempt.task_id)
            if task_attempt
            else None
        )
        if not task:
            task = self.repository.get_latest_event_task(event.id)
        return ConversationLoadResponse(
            conversation_id=conversation.id,
            session=session,
            event=event,
            personas=self.repository.list_personas(event.id),
            messages=self.repository.list_messages(conversation.id),
            condition=condition,
            task=task,
            task_attempt=task_attempt,
            related_events=[],
        )
