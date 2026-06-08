from fastapi import HTTPException, status

from app.models.domain import ChatMessage, ResearchLog
from app.schemas.requests import ChatRequest
from app.schemas.responses import ChatResponse
from app.providers.llm.base import LLMProvider
from app.crud.protocols import RepositoryProtocol
from app.services.prompt_service import PromptService
from app.services.rag_pipeline_service import RagPipelineService


class ChatService:
    def __init__(
        self,
        repository: RepositoryProtocol,
        llm_provider: LLMProvider,
        prompt_service: PromptService,
        rag_pipeline: RagPipelineService,
    ) -> None:
        self.repository = repository
        self.llm_provider = llm_provider
        self.prompt_service = prompt_service
        self.rag_pipeline = rag_pipeline

    async def chat(self, request: ChatRequest) -> ChatResponse:
        conversation = self.repository.get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        event = self.repository.get_event(conversation.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        session = self.repository.get_session(conversation.session_id) if conversation.session_id else None
        condition = self.repository.get_condition_by_key(session.condition_key_snapshot) if session else None
        if not condition:
            condition = self.repository.get_condition_by_key("ebl_roleplay")
        if not condition:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment condition not found")

        task_attempt = (
            self.repository.get_task_attempt(conversation.task_attempt_id)
            if conversation.task_attempt_id
            else None
        )
        personas = self.repository.list_personas(event.id)
        selected = None
        if condition.roleplay_enabled:
            if not personas:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active personas found")
            selected = self._select_persona(event.id, personas, request.target_persona_id, conversation.id)

        user_message = ChatMessage(
            conversation_id=conversation.id,
            speaker_type="learner",
            speaker_name="learner",
            sequence_index=self.repository.next_message_sequence(conversation.id),
            content=request.user_message,
            metadata={"condition_key": condition.condition_key},
        )
        user_message = self.repository.add_message(user_message)
        self.repository.log_research(
            ResearchLog(
                user_id=conversation.user_id,
                session_id=conversation.session_id,
                event_id=event.id,
                attempt_id=conversation.task_attempt_id,
                conversation_id=conversation.id,
                message_id=user_message.id,
                action_type="message_sent",
                payload={"target_persona_id": request.target_persona_id, "condition_key": condition.condition_key},
            )
        )

        rag_sources = self.rag_pipeline.retrieve(event.id, request.user_message)
        prompt = self.prompt_service.assemble_chat_prompt(
            event=event,
            persona=selected,
            condition=condition,
            task_attempt=task_attempt,
            user_message=request.user_message,
            rag_sources=rag_sources,
        )
        response_text, annotations, related_events, dynamic_context = await self.llm_provider.generate_chat_response(
            event=event,
            persona=selected,
            condition=condition,
            task_attempt=task_attempt,
            user_message=request.user_message,
            prompt=prompt,
            rag_sources=rag_sources,
        )

        assistant_name = self._assistant_name(condition, selected)
        model_message = ChatMessage(
            conversation_id=conversation.id,
            speaker_type="persona" if selected else "assistant",
            speaker_name=assistant_name,
            persona_id=selected.id if selected else None,
            sequence_index=self.repository.next_message_sequence(conversation.id),
            content=response_text,
            annotations=annotations,
            rag_sources=rag_sources,
            metadata={
                "condition_key": condition.condition_key,
                "response_policy": condition.response_policy,
                "prompt_preview": prompt[:500],
            },
        )
        model_message = self.repository.add_message(model_message)

        self.repository.log_research(
            ResearchLog(
                user_id=conversation.user_id,
                session_id=conversation.session_id,
                event_id=event.id,
                attempt_id=conversation.task_attempt_id,
                conversation_id=conversation.id,
                message_id=model_message.id,
                action_type="persona_response_generated" if selected else "assistant_response_generated",
                payload={
                    "condition_key": condition.condition_key,
                    "speaker_name": assistant_name,
                    "response_policy": condition.response_policy,
                },
            )
        )

        return ChatResponse(
            response=response_text,
            selected_persona=selected,
            assistant_name=assistant_name,
            message=model_message,
            annotations=annotations,
            related_events=related_events,
            dynamic_context=dynamic_context,
            rag_sources=rag_sources,
        )

    def _select_persona(self, event_id: str, personas, target_persona_id: str | None, conversation_id: str):
        if target_persona_id:
            selected = self.repository.get_persona(target_persona_id)
            if not selected or selected.event_id != event_id or not selected.active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected persona not found")
            return selected
        persona_messages = [
            message for message in self.repository.list_messages(conversation_id)
            if message.speaker_type == "persona"
        ]
        return personas[len(persona_messages) % len(personas)]

    @staticmethod
    def _assistant_name(condition, selected) -> str:
        if selected:
            return selected.name
        return "AI Tutor" if condition.ebl_enabled else "AI Assistant"
