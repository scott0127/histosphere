"""Task submission service.

本模組負責 task gate：保存 learner 作答、呼叫 LLM 做初步的正誤判斷、
建立 task_attempts，並在作答完成後解鎖 conversation。
"""

from fastapi import HTTPException, status

from app.crud.protocols import RepositoryProtocol
from app.models.domain import ChatMessage, Conversation, ResearchLog, TaskAttempt, utc_now
from app.providers.llm.base import LLMProvider
from app.schemas.requests import TaskDraftRequest, TaskSubmitRequest
from app.schemas.responses import TaskDraftResponse, TaskSubmitResponse


class TaskService:
    """處理 learner 完成 task 到開啟對話的過渡流程。"""

    def __init__(self, repository: RepositoryProtocol, llm_provider: LLMProvider) -> None:
        self.repository = repository
        self.llm_provider = llm_provider

    def save_draft(self, task_id: str, request: TaskDraftRequest) -> TaskDraftResponse:
        """保存 learner task 草稿；不呼叫 LLM，也不解鎖 conversation。"""
        task = self.repository.get_event_task(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        session = self.repository.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment session not found")
        if session.event_id != task.event_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task does not belong to session event")
        if request.user_id and not session.user_id:
            session.user_id = request.user_id

        attempt = self.repository.get_task_attempt_for_session(session.id, task.id)
        if attempt and attempt.status == "submitted":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task already submitted")

        if not attempt:
            attempt = TaskAttempt(
                task_id=task.id,
                event_id=task.event_id,
                session_id=session.id,
                user_id=request.user_id or session.user_id,
                status="in_progress",
            )

        attempt.response_payload = request.response_payload
        attempt.user_id = request.user_id or attempt.user_id or session.user_id
        saved = self.repository.save_task_attempt(attempt)
        self.repository.save_session(session)
        return TaskDraftResponse(attempt=saved)

    async def submit_task(self, task_id: str, request: TaskSubmitRequest) -> TaskSubmitResponse:
        """送出 task 作答，產生 judgement，並建立 conversation/greeting。"""
        task = self.repository.get_event_task(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        session = self.repository.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment session not found")
        if session.event_id != task.event_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task does not belong to session event")
        if request.user_id and not session.user_id:
            session.user_id = request.user_id

        event = self.repository.get_event(task.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        condition = self.repository.get_condition_by_key(session.condition_key_snapshot)
        if not condition:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment condition not found")

        # V1 只記錄最後送出的 response_payload；細格答案表先 postponed。
        self.repository.log_research(
            ResearchLog(
                user_id=request.user_id or session.user_id,
                session_id=session.id,
                event_id=event.id,
                task_id=task.id,
                action_type="task_answer_changed",
                payload={"response_payload": request.response_payload},
            )
        )

        # LLM judgement 是輕量 rubric 判斷，不等同正式評分表。
        judgement = await self.llm_provider.judge_task_attempt(event, task, request.response_payload)
        attempt = self.repository.save_task_attempt(
            TaskAttempt(
                task_id=task.id,
                event_id=event.id,
                session_id=session.id,
                user_id=request.user_id or session.user_id,
                status="submitted",
                response_payload=request.response_payload,
                judgement_payload=judgement,
                submitted_at=utc_now(),
            )
        )

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

        conversation = self.repository.save_conversation(
            Conversation(
                event_id=event.id,
                task_attempt_id=attempt.id,
                session_id=session.id,
                user_id=attempt.user_id,
            )
        )

        session.status = "conversation_started"
        self.repository.save_session(session)

        # greeting 也寫入 messages，讓重新整理聊天頁時可完整回放。
        personas = self.repository.list_personas(event.id)
        greeting = await self.llm_provider.generate_greeting(event, personas, condition, attempt)
        greeting_message = self._store_greeting(conversation.id, personas, condition, greeting, attempt)

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

        return TaskSubmitResponse(
            attempt_id=attempt.id,
            conversation_id=conversation.id,
            event=event,
            task=task,
            personas=personas,
            condition=condition,
            attempt=attempt,
            judgement=judgement,
            greeting=greeting,
            history=[greeting_message],
        )

    def _store_greeting(
        self,
        conversation_id: str,
        personas,
        condition,
        greeting: str,
        attempt: TaskAttempt,
    ) -> ChatMessage:
        """把系統開場白存成第一則 AI message。"""
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
            },
        )
        return self.repository.add_message(message)
