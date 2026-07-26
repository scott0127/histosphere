"""Chat orchestration service.

本模組是對話流程的核心協調層：讀取 conversation/session/condition，
決定是否使用 historical persona，組裝 prompt，呼叫 LLM provider，
最後把 learner 與 AI 回覆都寫入 messages 與 research_logs。
"""

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException, status

from app.core.interaction_contract import InteractionRuntime, build_interaction_runtime
from app.core.persona_prompt_contract import build_persona_runtime_context
from app.models.domain import ChatMessage, Event, ExperimentCondition, Persona, RagSource, ResearchLog, TaskAttempt
from app.schemas.requests import ChatRequest
from app.schemas.responses import ChatResponse
from app.providers.llm.base import ChatGenerationResult, LLMProvider
from app.crud.protocols import RepositoryProtocol
from app.services.prompt_service import PromptService
from app.services.completion_validation import validate_completion_candidate
from app.services.llm_generation_audit import record_rejected_generation
from app.services.rag_pipeline_service import RagPipelineService
from app.services.session_runtime import expire_session_if_due


MAX_CHAT_GENERATION_ATTEMPTS = 3
MessagePersistedCallback = Callable[[ChatMessage], Awaitable[None]]


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

    async def chat(
        self,
        request: ChatRequest,
        on_user_persisted: MessagePersistedCallback | None = None,
    ) -> ChatResponse:
        """先保存 learner 訊息，再依照 2x2 condition 產生並保存 AI 回覆。"""
        conversation = self.repository.get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        event = self.repository.get_event(conversation.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        # Condition 是實驗操弄的一部分；缺少 session 或 snapshot 時必須停止，不能猜測預設模式。
        if not conversation.session_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conversation is not bound to an experiment session",
            )
        session = self.repository.get_session(conversation.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Experiment session is unavailable",
            )
        session = expire_session_if_due(self.repository, session)
        if session.status in {"completed", "archived"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Experiment session is already closed")
        condition = self.repository.get_condition_by_key(session.condition_key_snapshot)
        if not condition:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Experiment condition snapshot is unavailable",
            )

        # task_attempt 讓 EBL 條件可以引用 learner 的 productive error / misconception。
        task_attempt = (
            self.repository.get_task_attempt(conversation.task_attempt_id)
            if conversation.task_attempt_id
            else None
        )
        prior_messages = self.repository.list_messages(conversation.id)
        personas = self.repository.list_personas(event.id)
        selected = None
        if condition.roleplay_enabled:
            if not personas:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active personas found")
            selected = self._select_persona(
                event.id,
                personas,
                request.target_persona_id,
                prior_messages,
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

        # learner 訊息必須先落盤。即使模型逾時或驗證失敗，重新載入仍能看到原始輸入。
        user_message = self.repository.add_message(
            ChatMessage(
                conversation_id=conversation.id,
                speaker_type="learner",
                speaker_name="learner",
                sequence_index=self.repository.next_message_sequence(conversation.id),
                content=request.user_message,
                metadata={
                    "condition_key": condition.condition_key,
                    "response_status": "pending",
                    "target_persona_id": request.target_persona_id,
                },
            )
        )
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

        try:
            if on_user_persisted:
                await on_user_persisted(user_message)

            generation, interaction_metadata = await self.generate_validated_response(
                event=event,
                selected=selected,
                condition=condition,
                task_attempt=task_attempt,
                user_message=request.user_message,
                base_prompt=prompt,
                rag_sources=rag_sources,
                interaction_runtime=interaction_runtime,
            )

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
                content=generation.response,
                annotations=generation.annotations,
                rag_sources=rag_sources,
                metadata={
                    "condition_key": condition.condition_key,
                    "response_policy": condition.response_policy,
                    "generation_status": "completed",
                    "delivery_mode": "validated_stream",
                    "prompt_preview": prompt[:500],
                    "prompt_hash": prompt_hash,
                    "prompt_modules": [module.name for module in modules],
                    "history_message_ids": [message.id for message in prior_messages],
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
                        "disclosure_level": interaction_metadata.get("disclosure_level"),
                        "allowed_disclosure_levels": interaction_metadata.get("allowed_disclosure_levels", []),
                        "learner_progress": interaction_metadata.get("learner_progress"),
                        "disclosure_reason": interaction_metadata.get("disclosure_reason"),
                        "fidelity_flags": interaction_metadata.get("fidelity_flags", []),
                        "fidelity_retry_count": interaction_metadata.get("generation_retry_count", 0),
                    },
                )
            )

            completed_user_message = user_message.model_copy(
                update={
                    "metadata": {
                        **user_message.metadata,
                        "response_status": "completed",
                        "response_message_id": model_message.id,
                    }
                }
            )
            self.repository.add_message(completed_user_message)

            return ChatResponse(
                response=generation.response,
                selected_persona=selected,
                assistant_name=assistant_name,
                message=model_message,
                annotations=generation.annotations,
                related_events=generation.related_events,
                dynamic_context=generation.dynamic_context,
                rag_sources=rag_sources,
            )
        except HTTPException as exc:
            self._record_generation_failure(
                conversation=conversation,
                event=event,
                condition=condition,
                user_message=user_message,
                failure_type=f"http_{exc.status_code}",
            )
            raise
        except Exception as exc:
            self._record_generation_failure(
                conversation=conversation,
                event=event,
                condition=condition,
                user_message=user_message,
                failure_type=type(exc).__name__,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI 回覆產生失敗，但 learner 訊息已保存。",
            ) from exc

    def _record_generation_failure(
        self,
        *,
        conversation,
        event: Event,
        condition: ExperimentCondition,
        user_message: ChatMessage,
        failure_type: str,
    ) -> None:
        """保存失敗狀態，但不把例外內容或密鑰寫入研究資料。"""
        failed_user_message = user_message.model_copy(
            update={
                "metadata": {
                    **user_message.metadata,
                    "response_status": "failed",
                    "failure_type": failure_type,
                }
            }
        )
        self.repository.add_message(failed_user_message)
        self.repository.log_research(
            ResearchLog(
                user_id=conversation.user_id,
                session_id=conversation.session_id,
                event_id=event.id,
                attempt_id=conversation.task_attempt_id,
                conversation_id=conversation.id,
                message_id=user_message.id,
                action_type="response_generation_failed",
                payload={
                    "condition_key": condition.condition_key,
                    "failure_type": failure_type,
                },
            )
        )

    def _select_persona(
        self,
        event_id: str,
        personas,
        target_persona_id: str | None,
        prior_messages: list[ChatMessage],
    ):
        """Keep one persona identity stable for the full conversation."""
        locked_persona_id = next(
            (message.persona_id for message in prior_messages if message.persona_id),
            None,
        )
        if locked_persona_id:
            if target_persona_id and target_persona_id != locked_persona_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Historical persona is locked for this conversation",
                )
            selected = self.repository.get_persona(locked_persona_id)
            if not selected or selected.event_id != event_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Conversation persona is no longer available",
                )
            return selected
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

    async def generate_validated_response(
        self,
        *,
        event: Event,
        selected: Persona | None,
        condition: ExperimentCondition,
        task_attempt: TaskAttempt | None,
        user_message: str,
        base_prompt: str,
        rag_sources: list[RagSource],
        interaction_runtime: InteractionRuntime,
    ) -> tuple[ChatGenerationResult, dict[str, Any]]:
        """Generate without persistence; shared by runtime chat and Admin dry-run."""
        persona_context = build_persona_runtime_context(event, selected) if selected else None
        rejected_candidates: list[dict[str, Any]] = []
        accumulated_retry_flags: set[str] = set()
        prompt = base_prompt

        for generation_index in range(MAX_CHAT_GENERATION_ATTEMPTS):
            generation = await self.llm_provider.generate_chat_response(
                event=event,
                persona=selected,
                condition=condition,
                task_attempt=task_attempt,
                user_message=user_message,
                prompt=prompt,
                rag_sources=rag_sources,
            )
            validation = validate_completion_candidate(
                runtime=interaction_runtime,
                generation=generation,
                persona_context=persona_context,
                is_opening=False,
            )
            if not validation.retry_required:
                metadata = {
                    **validation.metadata,
                    "generation_retry_count": generation_index,
                    "rejected_candidates": rejected_candidates,
                }
                return (
                    ChatGenerationResult(
                        response=validation.response,
                        annotations=generation.annotations,
                        related_events=generation.related_events,
                        dynamic_context=generation.dynamic_context,
                        interaction_metadata=metadata,
                    ),
                    metadata,
                )

            runner = getattr(self.llm_provider, "runner", None)
            audit_id = record_rejected_generation(
                stage="chat_contract_validation",
                provider=str(getattr(runner, "last_provider", "unknown")),
                model=str(getattr(runner, "last_model", "unknown")),
                task_name="chat_response",
                raw_output=generation.response,
                reasons=list(validation.retry_flags),
                context={
                    "event_id": event.id,
                    "attempt_id": task_attempt.id if task_attempt else None,
                    "condition_key": condition.condition_key,
                    "generation_index": generation_index,
                },
            )
            rejected_candidates.append(
                {
                    "audit_id": audit_id,
                    "sha256": hashlib.sha256(generation.response.encode("utf-8")).hexdigest(),
                    "length": len(generation.response),
                    "flags": list(validation.retry_flags),
                }
            )
            accumulated_retry_flags.update(validation.retry_flags)
            prompt = self.prompt_service.build_retry_prompt(
                base_prompt,
                tuple(sorted(accumulated_retry_flags)),
            )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM response failed interaction/persona validation",
        )

    def _llm_metadata(self) -> dict[str, str]:
        """Read provider metadata without coupling the service to LiteLLMProvider."""
        runner = getattr(self.llm_provider, "runner", None)
        return {
            "provider": str(getattr(runner, "last_provider", "unknown")),
            "model": str(getattr(runner, "last_model", "unknown")),
        }
