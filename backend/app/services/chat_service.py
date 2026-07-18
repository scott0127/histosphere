"""Chat orchestration service.

本模組是對話流程的核心協調層：讀取 conversation/session/condition，
決定是否使用 historical persona，組裝 prompt，呼叫 LLM provider，
最後把 learner 與 AI 回覆都寫入 messages 與 research_logs。
"""

import hashlib
import json

from fastapi import HTTPException, status

from app.core.interaction_contract import build_interaction_runtime, enforce_interaction_response
from app.models.domain import ChatMessage, ResearchLog
from app.schemas.requests import ChatRequest
from app.schemas.responses import ChatResponse
from app.providers.llm.base import LLMProvider
from app.crud.protocols import RepositoryProtocol
from app.services.prompt_service import PromptService
from app.services.rag_pipeline_service import RagPipelineService
from app.services.session_runtime import expire_session_if_due


class ChatService:
    """負責執行一次 learner -> AI 的完整聊天回合。"""

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
        """依照 2x2 condition 產生回覆，並保存完整對話與研究紀錄。"""
        conversation = self.repository.get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        event = self.repository.get_event(conversation.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        session = self.repository.get_session(conversation.session_id) if conversation.session_id else None
        if session:
            session = expire_session_if_due(self.repository, session)
            if session.status in {"completed", "archived"}:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Experiment session is already closed")
        condition = self.repository.get_condition_by_key(session.condition_key_snapshot) if session else None
        if not condition:
            condition = self.repository.get_condition_by_key("ebl_roleplay")
        if not condition:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment condition not found")

        # task_attempt 讓 EBL 條件可以引用 learner 的 productive error / misconception。
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

        prior_messages = self.repository.list_messages(conversation.id)
        # learner message 與 AI message 都用 sequence_index，方便前端穩定回放。
        user_message = ChatMessage(
            conversation_id=conversation.id,
            speaker_type="learner",
            speaker_name="learner",
            sequence_index=self.repository.next_message_sequence(conversation.id),
            content=request.user_message,
            metadata={"condition_key": condition.condition_key},
        )
        user_message = self.repository.add_message(user_message)
        # research_logs 記錄行為事件；messages 則保留實際對話內容。
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

        # V1 的 RAG 目前是空實作，但保留同一個介面讓未來接 vector retrieval。
        rag_sources = self.rag_pipeline.retrieve(event.id, request.user_message)
        interaction_runtime = build_interaction_runtime(condition, task_attempt, prior_messages)
        modules = self.prompt_service.assemble_chat_modules(
            event=event,
            persona=selected,
            condition=condition,
            task_attempt=task_attempt,
            user_message=request.user_message,
            rag_sources=rag_sources,
            conversation_history=prior_messages,
            interaction_runtime=interaction_runtime,
        )
        prompt = self.prompt_service.render_modules(modules)
        generation = await self.llm_provider.generate_chat_response(
            event=event,
            persona=selected,
            condition=condition,
            task_attempt=task_attempt,
            user_message=request.user_message,
            prompt=prompt,
            rag_sources=rag_sources,
        )
        enforced_response = enforce_interaction_response(
            interaction_runtime,
            generation.interaction_metadata,
            generation.response,
        )
        interaction_metadata = enforced_response.metadata
        response_annotations = [] if enforced_response.fallback_applied else generation.annotations
        response_related_events = [] if enforced_response.fallback_applied else generation.related_events
        response_dynamic_context = "" if enforced_response.fallback_applied else generation.dynamic_context

        assistant_name = self._assistant_name(condition, selected)
        # role-play 條件使用 persona speaker；非 role-play 條件使用 generic assistant。
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        profile_payload = selected.prompt_profile if selected else {}
        profile_hash = hashlib.sha256(
            json.dumps(profile_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        model_message = ChatMessage(
            conversation_id=conversation.id,
            speaker_type="persona" if selected else "assistant",
            speaker_name=assistant_name,
            persona_id=selected.id if selected else None,
            sequence_index=self.repository.next_message_sequence(conversation.id),
            content=enforced_response.response,
            annotations=response_annotations,
            rag_sources=rag_sources,
            metadata={
                "condition_key": condition.condition_key,
                "response_policy": condition.response_policy,
                "prompt_preview": prompt[:500],
                "prompt_hash": prompt_hash,
                "prompt_modules": [module.name for module in modules],
                "history_message_ids": [message.id for message in prior_messages[-12:]],
                "history_message_count": len(prior_messages),
                "persona_profile_contract": profile_payload.get("contract_version") if selected else None,
                "persona_profile_hash": profile_hash if selected else None,
                **interaction_metadata,
                **self._llm_metadata(),
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
                    "target_question_id": interaction_metadata.get("target_question_id"),
                    "dialogue_state": interaction_metadata.get("dialogue_state"),
                    "dialogue_move": interaction_metadata.get("dialogue_move"),
                    "scaffold_level": interaction_metadata.get("scaffold_level"),
                    "fidelity_flags": interaction_metadata.get("fidelity_flags", []),
                    "fidelity_fallback_applied": interaction_metadata.get("fidelity_fallback_applied", False),
                },
            )
        )

        return ChatResponse(
            response=enforced_response.response,
            selected_persona=selected,
            assistant_name=assistant_name,
            message=model_message,
            annotations=response_annotations,
            related_events=response_related_events,
            dynamic_context=response_dynamic_context,
            rag_sources=rag_sources,
        )

    def _select_persona(self, event_id: str, personas, target_persona_id: str | None, conversation_id: str):
        """選擇要回覆的 persona；V1 預設永遠使用排序第一位 primary persona。"""
        if target_persona_id:
            selected = self.repository.get_persona(target_persona_id)
            if not selected or selected.event_id != event_id or not selected.active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected persona not found")
            return selected
        return personas[0]

    @staticmethod
    def _assistant_name(condition, selected) -> str:
        """回傳前端要顯示的 speaker 名稱。"""
        if selected:
            return selected.name
        return "AI Tutor" if condition.ebl_enabled else "AI Assistant"

    def _llm_metadata(self) -> dict[str, str]:
        """Read provider metadata without coupling the service to LiteLLMProvider."""
        runner = getattr(self.llm_provider, "runner", None)
        return {
            "provider": str(getattr(runner, "last_provider", "unknown")),
            "model": str(getattr(runner, "last_model", "unknown")),
        }
