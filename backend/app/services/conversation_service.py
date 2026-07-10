"""Conversation loading and compatibility creation service.

本模組負責讀取 conversation 狀態，供前端聊天頁重新載入。
V1 正常流程由 TaskService 在 learner 完成 task 後建立 conversation；
create_conversation 主要保留給相容舊 API 或管理端手動建立。
"""

from fastapi import HTTPException, status

from app.models.domain import ChatMessage, Conversation
from app.schemas.responses import ConversationCreateResponse, ConversationLoadResponse
from app.providers.llm.base import LLMProvider
from app.crud.protocols import RepositoryProtocol


class ConversationService:
    """管理 conversation 建立與回放資料載入。"""

    def __init__(self, repository: RepositoryProtocol, llm_provider: LLMProvider) -> None:
        self.repository = repository
        self.llm_provider = llm_provider

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

        conversation = self.repository.save_conversation(
            Conversation(
                event_id=event.id,
                task_attempt_id=attempt.id if attempt else None,
                session_id=session.id if session else None,
                user_id=user_id,
            )
        )
        greeting = "對話已建立。"
        if condition and attempt:
            greeting = await self.llm_provider.generate_greeting(event, personas, condition, attempt)

        greeting_message = ChatMessage(
            conversation_id=conversation.id,
            persona_id=personas[0].id if condition and condition.roleplay_enabled and personas else None,
            speaker_type="persona" if condition and condition.roleplay_enabled and personas else "assistant",
            speaker_name=personas[0].name if condition and condition.roleplay_enabled and personas else "AI Assistant",
            sequence_index=self.repository.next_message_sequence(conversation.id),
            content=greeting,
        )
        self.repository.add_message(greeting_message)
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
            event=event,
            personas=self.repository.list_personas(event.id),
            messages=self.repository.list_messages(conversation.id),
            condition=condition,
            task=task,
            task_attempt=task_attempt,
            related_events=[],
        )
