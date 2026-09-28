"""Chat orchestration service.

先核對活動與 Condition，保存學習者訊息，再組裝 Prompt、生成並檢查 AI 回覆。
同一請求重送時沿用已保存的結果；模型失敗也不會讓學習者剛輸入的文字消失。
正式對話訊息與研究紀錄分開保存，內部審查草稿不當成新的聊天回合。
"""

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException, status

from app.core.interaction_contract import (
    InteractionRuntime,
    build_interaction_runtime,
)
from app.core.persona_prompt_contract import build_persona_runtime_context
from app.core.research_reproducibility import record_prompt_snapshot
from app.models.domain import ChatMessage, Event, ExperimentCondition, Persona, RagSource, ResearchLog, TaskAttempt, new_id
from app.schemas.requests import ChatRequest
from app.schemas.responses import ChatOperationStatusResponse, ChatResponse
from app.providers.llm.base import ChatGenerationResult, LLMProvider
from app.crud.protocols import RepositoryProtocol
from app.services.prompt_service import PromptService
from app.services.completion_validation import validate_completion_candidate
from app.services.llm_generation_audit import record_rejected_generation
from app.services.rag_pipeline_service import RagPipelineService
from app.services.session_runtime import expire_session_if_due
from app.services.answer_delivery_service import deliver_answer
from app.services.learning_focus import build_learning_focus
from app.services.response_timing import finish_response_timing, start_response_timing


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
        self.answer_review_service = None

    async def chat(
        self,
        request: ChatRequest,
        on_user_persisted: MessagePersistedCallback | None = None,
    ) -> ChatResponse:
        """用 client_request_id 辨認同一次送出，避免重新連線後重複生成與計費。"""
        exchange_timing, started_clock = start_response_timing()
        conversation = self.repository.get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        if request.target_persona_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Learners cannot select a historical persona",
            )
        # 舊版跳題會略過最後作答與修正回饋；拒絕請求且不寫入 learner message。
        if request.interaction_action is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Direct error skipping is no longer supported; finish the final answer and feedback step",
            )
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
        session_closed = session.status in {"completed", "archived"}
        if session_closed:
            # 到期後只允許取回已完成的同一回合，不重新生成或接受新訊息。
            saved_operation = self.repository.get_learner_message_by_request(
                conversation.id, request.client_request_id,
            ) if request.client_request_id else None
            if (session.status == "completed" and session.completion_reason == "timer_elapsed"
                    and saved_operation and saved_operation.content == request.user_message
                    and self._operation_state(saved_operation) == "completed"):
                if on_user_persisted:
                    await on_user_persisted(saved_operation)
                return self._completed_response(saved_operation)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Experiment session is already closed")
        condition = self.repository.get_condition_by_key(session.condition_key_snapshot)
        if not condition:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Experiment condition snapshot is unavailable",
            )

        client_request_id = request.client_request_id or new_id()
        stored_messages = self.repository.list_messages(conversation.id)
        task_attempt = (
            self.repository.get_task_attempt(conversation.task_attempt_id)
            if conversation.task_attempt_id
            else None
        )
        existing_operation = self.repository.get_learner_message_by_request(
            conversation.id,
            client_request_id,
        )

        if existing_operation:
            if existing_operation.content != request.user_message:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="client_request_id was already used for different content",
                )
            persisted_action = existing_operation.metadata.get("interaction_action")
            if persisted_action is not None and self._operation_state(existing_operation) != "completed":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A legacy error-skip operation cannot be retried; send a regular chat message",
                )
            operation_status = self._operation_state(existing_operation)
            if operation_status == "completed":
                if on_user_persisted:
                    await on_user_persisted(existing_operation)
                return self._completed_response(existing_operation)
            if operation_status in {"pending", "processing"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This chat operation is still processing",
                )
            if not request.retry_failed:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This chat operation failed and requires an explicit retry",
                )

            # 重試沿用原 learner 訊息，避免產生第二筆相同研究資料。
            retry_metadata = {
                key: value
                for key, value in existing_operation.metadata.items()
                if key not in {"failure_type", "llm_call"}
            }
            original_timing = existing_operation.metadata.get("exchange_timing") or {}
            exchange_timing.update({
                "original_request_started_at": original_timing.get("original_request_started_at")
                    or existing_operation.created_at.isoformat(),
                "attempt_number": int(existing_operation.metadata.get("retry_count", 0)) + 2,
            })
            user_message = existing_operation.model_copy(
                update={
                    "operation_status": "processing",
                    "metadata": {
                        **retry_metadata,
                        "response_status": "pending",
                        "retry_count": int(existing_operation.metadata.get("retry_count", 0)) + 1,
                        "exchange_timing": exchange_timing,
                    },
                }
            )
            self.repository.add_message(user_message)
            prior_messages = [
                message
                for message in stored_messages
                if message.id != existing_operation.id
                and message.id != existing_operation.metadata.get("response_message_id")
            ]
            self.repository.log_research(
                ResearchLog(
                    user_id=conversation.user_id,
                    session_id=conversation.session_id,
                    event_id=event.id,
                    attempt_id=conversation.task_attempt_id,
                    conversation_id=conversation.id,
                    message_id=user_message.id,
                    action_type="response_generation_retried",
                    payload={
                        "client_request_id": client_request_id,
                        "retry_count": user_message.metadata["retry_count"],
                        "condition_key": condition.condition_key,
                        "exchange_timing": exchange_timing,
                    },
                )
            )
        else:
            if request.retry_failed:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The failed chat operation no longer exists",
                )
            active_operation = self.repository.get_active_chat_operation(conversation.id)
            if active_operation:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Another chat operation is already processing",
                )

            prior_messages = stored_messages
            user_message = ChatMessage(
                conversation_id=conversation.id,
                speaker_type="learner",
                speaker_name="learner",
                sequence_index=self.repository.next_message_sequence(conversation.id),
                content=request.user_message,
                client_request_id=client_request_id,
                operation_status="processing",
                metadata={
                    "condition_key": condition.condition_key,
                    "response_status": "pending",
                    "persona_selection": "event_fixed",
                    "client_request_id": client_request_id,
                    "exchange_timing": exchange_timing,
                },
            )
            try:
                user_message = self.repository.add_message(user_message)
            except Exception:
                # 資料庫唯一約束處理不同程序同時送出的競爭；重新查詢後回傳一致語意。
                raced_operation = self.repository.get_learner_message_by_request(
                    conversation.id,
                    client_request_id,
                )
                if raced_operation:
                    if raced_operation.content != request.user_message:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="client_request_id was already used for different content",
                        )
                    if self._operation_state(raced_operation) == "completed":
                        if on_user_persisted:
                            await on_user_persisted(raced_operation)
                        return self._completed_response(raced_operation)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="This chat operation is still processing",
                    )
                if self.repository.get_active_chat_operation(conversation.id):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Another chat operation is already processing",
                    )
                raise

            self.repository.log_research(
                ResearchLog(
                    user_id=conversation.user_id,
                    session_id=conversation.session_id,
                    event_id=event.id,
                    attempt_id=conversation.task_attempt_id,
                    conversation_id=conversation.id,
                    message_id=user_message.id,
                    action_type="message_sent",
                    payload={
                        "persona_selection": "event_fixed",
                        "condition_key": condition.condition_key,
                        "client_request_id": client_request_id,
                    },
                )
            )

        try:
            if on_user_persisted:
                await on_user_persisted(user_message)

            personas = self.repository.list_personas(event.id)
            selected = None
            if condition.roleplay_enabled:
                selected = self._select_persona(
                    event.id,
                    personas,
                    prior_messages,
                )
            # V1 的 RAG 目前是空實作，但保留同一個介面讓未來接 vector retrieval。
            rag_sources = self.rag_pipeline.retrieve(event.id, request.user_message)
            interaction_runtime = build_interaction_runtime(condition, task_attempt, prior_messages)
            learning_target_question_id = (
                interaction_runtime.target.question_id if interaction_runtime.target else None
            )
            user_message = user_message.model_copy(update={"metadata": {
                **user_message.metadata, "learning_target_question_id": learning_target_question_id,
            }})
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

            generation, interaction_metadata, final_prompt = await self.generate_validated_response(
                event=event,
                selected=selected,
                condition=condition,
                task_attempt=task_attempt,
                user_message=request.user_message,
                base_prompt=prompt,
                rag_sources=rag_sources,
                interaction_runtime=interaction_runtime,
                conversation_history=prior_messages,
                persist_answer_audit=True,
            )

            assistant_name = self._assistant_name(condition, selected)
            system_fallback = bool(interaction_metadata.get("system_fallback"))
            if interaction_metadata.get("answer_delivery", {}).get("state_held"):
                modules = []
            if system_fallback:
                assistant_name = "系統提示"
            # 倒數前已接受的回合可於到期後送達；刪除、封存或其他結束原因仍停止寫入。
            current_session = self.repository.get_session(session.id)
            if (not self.repository.get_conversation(conversation.id)
                    or not self.repository.get_message(user_message.id) or not current_session):
                raise HTTPException(status_code=409, detail="Chat activity no longer exists")
            current_session = expire_session_if_due(self.repository, current_session)
            delivered_after_deadline = (
                current_session.status == "completed"
                and current_session.completion_reason == "timer_elapsed"
            )
            if current_session.status == "archived" or (
                current_session.status == "completed" and not delivered_after_deadline
            ):
                raise HTTPException(status_code=409, detail="Experiment session is already closed")
            # role-play 條件使用 persona speaker；非 role-play 條件使用 generic assistant。
            prompt_hash = hashlib.sha256(final_prompt.encode("utf-8")).hexdigest()
            profile_payload = selected.prompt_profile if selected else {}
            profile_hash = hashlib.sha256(
                json.dumps(profile_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            model_message = ChatMessage(
                conversation_id=conversation.id,
                speaker_type="persona" if selected and not system_fallback else "assistant",
                speaker_name=assistant_name,
                persona_id=selected.id if selected and not system_fallback else None,
                sequence_index=self.repository.next_message_sequence(conversation.id),
                content=generation.response,
                annotations=generation.annotations,
                rag_sources=rag_sources,
                client_request_id=client_request_id,
                metadata={
                    "condition_key": condition.condition_key,
                    "client_request_id": client_request_id,
                    "response_policy": condition.response_policy,
                    "generation_status": "completed",
                    "delivery_mode": "validated_stream",
                    "prompt_preview": final_prompt[:500],
                    "prompt_hash": prompt_hash,
                    "prompt_modules": [module.name for module in modules],
                    "history_message_ids": [message.id for message in prior_messages],
                    "history_message_count": len(prior_messages),
                    "persona_profile_contract": profile_payload.get("contract_version") if selected else None,
                    "persona_profile_hash": profile_hash if selected else None,
                    "related_events": [
                        related_event.model_dump(mode="json")
                        for related_event in generation.related_events
                    ],
                    "dynamic_context": generation.dynamic_context,
                    **interaction_metadata,
                    **generation.llm_metadata,
                    "delivered_after_deadline": delivered_after_deadline,
                    "delivery_phase": "post_timer_closure" if delivered_after_deadline else "timed_chat",
                },
            )
            review = self.answer_review_service
            review_context = review.prepare(
                model_message, runtime=interaction_runtime, event=event, attempt=task_attempt,
                history=prior_messages, learner_message=request.user_message,
            ) if review else None
            # Measures through validation/review readiness, before the client stream.
            exchange_timing = finish_response_timing(exchange_timing, started_clock)
            model_message = model_message.model_copy(update={"metadata": {
                **model_message.metadata,
                "exchange_timing": exchange_timing,
                "learning_target_question_id": learning_target_question_id,
            }})
            model_message = self.repository.add_message(model_message)

            record_prompt_snapshot(
                self.repository,
                session_id=session.id,
                event_id=event.id,
                task_id=task_attempt.task_id if task_attempt else None,
                attempt_id=conversation.task_attempt_id,
                conversation_id=conversation.id,
                message_id=model_message.id,
                user_id=conversation.user_id,
                stage="chat_response",
                prompt=final_prompt,
                modules=modules,
                llm_call=generation.llm_metadata.get("llm_call"),
            )

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
                        "client_request_id": client_request_id,
                        "condition_key": condition.condition_key,
                        "speaker_name": assistant_name,
                        "delivered_after_deadline": delivered_after_deadline,
                        "delivery_phase": "post_timer_closure" if delivered_after_deadline else "timed_chat",
                        "response_policy": condition.response_policy,
                        "target_question_id": interaction_metadata.get("target_question_id"),
                        "dialogue_state": interaction_metadata.get("dialogue_state"),
                        "dialogue_move": interaction_metadata.get("dialogue_move"),
                        "disclosure_level": interaction_metadata.get("disclosure_level"),
                        "allowed_disclosure_levels": interaction_metadata.get("allowed_disclosure_levels", []),
                        "learner_progress": interaction_metadata.get("learner_progress"),
                        "disclosure_reason": interaction_metadata.get("disclosure_reason"),
                        "completion_status": interaction_metadata.get("completion_status"),
                        "resolution_outcome": interaction_metadata.get("resolution_outcome"),
                        "probe_kind": interaction_metadata.get("probe_kind"),
                        "error_source": interaction_metadata.get("error_source"),
                        "corrective_feedback_revealed_answer": interaction_metadata.get(
                            "corrective_feedback_revealed_answer",
                            False,
                        ),
                        "resolution_error_recognized": interaction_metadata.get("resolution_error_recognized", False),
                        "resolution_error_reflected": interaction_metadata.get("resolution_error_reflected", False),
                        "resolution_self_corrected": interaction_metadata.get("resolution_self_corrected", False),
                        "resolution_criteria_met": interaction_metadata.get("resolution_criteria_met", False),
                        "off_topic_redirect": interaction_metadata.get("off_topic_redirect", False),
                        "fidelity_flags": interaction_metadata.get("fidelity_flags", []),
                        "fidelity_retry_count": interaction_metadata.get("generation_retry_count", 0),
                        "llm_call": generation.llm_metadata.get("llm_call"),
                        "exchange_timing": exchange_timing,
                    },
                )
            )

            completed_user_message = user_message.model_copy(
                update={
                    "operation_status": "completed",
                    "metadata": {
                        **user_message.metadata,
                        "response_status": "completed",
                        "response_message_id": model_message.id,
                        "exchange_timing": exchange_timing,
                        "learning_target_question_id": learning_target_question_id,
                    }
                }
            )
            self.repository.add_message(completed_user_message)

            if review:
                review.schedule(model_message, review_context)

            return ChatResponse(
                response=generation.response,
                selected_persona=selected if not system_fallback else None,
                assistant_name=assistant_name,
                message=model_message,
                annotations=generation.annotations,
                related_events=generation.related_events,
                dynamic_context=generation.dynamic_context,
                rag_sources=rag_sources,
                learning_focus=build_learning_focus(
                    condition, task_attempt, self.repository.list_messages(conversation.id),
                ),
            )
        except HTTPException as exc:
            self._record_generation_failure(
                conversation=conversation,
                event=event,
                condition=condition,
                user_message=user_message,
                failure_type=f"http_{exc.status_code}",
                started_clock=started_clock,
            )
            raise
        except Exception as exc:
            llm_call = getattr(getattr(exc, "metadata", None), "as_dict", lambda: {})()
            self._record_generation_failure(
                conversation=conversation,
                event=event,
                condition=condition,
                user_message=user_message,
                failure_type=type(exc).__name__,
                llm_call=llm_call,
                started_clock=started_clock,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI 回覆產生失敗，但 learner 訊息已保存。",
            ) from exc

    def get_operation_status(
        self,
        conversation_id: str,
        client_request_id: str,
    ) -> ChatOperationStatusResponse:
        """供前端在斷線或重整後查詢同一聊天回合。"""
        operation = self.repository.get_learner_message_by_request(
            conversation_id,
            client_request_id,
        )
        if not operation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat operation not found",
            )
        operation_status = self._operation_state(operation)
        response = self._completed_response(operation) if operation_status == "completed" else None
        return ChatOperationStatusResponse(
            client_request_id=client_request_id,
            status=operation_status,
            retryable=operation_status == "failed",
            learner_message=operation,
            response=response,
        )

    @staticmethod
    def _operation_state(message: ChatMessage) -> str:
        """從正式欄位讀取狀態，並相容遷移前 metadata。"""
        operation_status = message.operation_status or message.metadata.get("response_status")
        if operation_status not in {"pending", "processing", "completed", "failed"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Chat operation status is unavailable",
            )
        return str(operation_status)

    def _completed_response(self, operation: ChatMessage) -> ChatResponse:
        """從已儲存的 AI 訊息重建回應，重送時不再次呼叫 LLM。"""
        response_message_id = operation.metadata.get("response_message_id")
        response_message = (
            self.repository.get_message(str(response_message_id))
            if response_message_id
            else None
        )
        if not response_message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Completed chat response is unavailable",
            )
        selected_persona = (
            self.repository.get_persona(response_message.persona_id)
            if response_message.persona_id
            else None
        )
        conversation = self.repository.get_conversation(operation.conversation_id)
        session = self.repository.get_session(conversation.session_id) if conversation and conversation.session_id else None
        condition = self.repository.get_condition_by_key(session.condition_key_snapshot) if session else None
        attempt = (
            self.repository.get_task_attempt(conversation.task_attempt_id)
            if conversation and conversation.task_attempt_id else None
        )
        # 重送舊回合時只重建當時已送達的題目，不套用更晚回合的狀態。
        history = [message for message in self.repository.list_messages(operation.conversation_id)
                   if message.sequence_index <= response_message.sequence_index]
        return ChatResponse(
            response=response_message.content,
            selected_persona=selected_persona,
            assistant_name=response_message.speaker_name,
            message=response_message,
            annotations=response_message.annotations,
            related_events=response_message.metadata.get("related_events", []),
            dynamic_context=str(response_message.metadata.get("dynamic_context", "")),
            rag_sources=response_message.rag_sources,
            learning_focus=build_learning_focus(condition, attempt, history),
        )

    def _record_generation_failure(
        self,
        *,
        conversation,
        event: Event,
        condition: ExperimentCondition,
        user_message: ChatMessage,
        failure_type: str,
        llm_call: dict[str, Any] | None = None,
        started_clock: float | None = None,
    ) -> None:
        """保存失敗狀態，但不把例外內容或密鑰寫入研究資料。"""
        if not self.repository.get_conversation(conversation.id) or not self.repository.get_message(user_message.id):
            return
        exchange_timing = finish_response_timing(
            user_message.metadata.get("exchange_timing") or {
                "request_started_at": user_message.created_at.isoformat(),
                "original_request_started_at": user_message.created_at.isoformat(),
                "attempt_number": int(user_message.metadata.get("retry_count", 0)) + 1,
            },
            started_clock,
            status="interrupted" if failure_type == "backend_restart" else "failed",
        )
        failed_user_message = user_message.model_copy(
            update={
                "operation_status": "failed",
                "metadata": {
                    **user_message.metadata,
                    "response_status": "failed",
                    "failure_type": failure_type,
                    "llm_call": llm_call or None,
                    "exchange_timing": exchange_timing,
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
                    "llm_call": llm_call or None,
                    "exchange_timing": exchange_timing,
                },
            )
        )

    def recover_interrupted_operations(self) -> int:
        """把前一個後端程序留下的生成中回合轉成可重試狀態。"""
        recovered_count = 0
        for user_message in self.repository.list_active_chat_operations():
            conversation = self.repository.get_conversation(user_message.conversation_id)
            event = self.repository.get_event(conversation.event_id) if conversation else None
            session = (
                self.repository.get_session(conversation.session_id)
                if conversation and conversation.session_id
                else None
            )
            condition = (
                self.repository.get_condition_by_key(session.condition_key_snapshot)
                if session
                else None
            )

            if conversation and event and condition:
                self._record_generation_failure(
                    conversation=conversation,
                    event=event,
                    condition=condition,
                    user_message=user_message,
                    failure_type="backend_restart",
                )
            else:
                # 即使關聯資料不完整，也不能讓 learner 永遠卡在「處理中」。
                failed_message = user_message.model_copy(
                    update={
                        "operation_status": "failed",
                        "metadata": {
                            **user_message.metadata,
                            "response_status": "failed",
                            "failure_type": "backend_restart",
                            "llm_call": None,
                            "exchange_timing": finish_response_timing(
                                user_message.metadata.get("exchange_timing") or {
                                    "request_started_at": user_message.created_at.isoformat(),
                                    "original_request_started_at": user_message.created_at.isoformat(),
                                    "attempt_number": int(user_message.metadata.get("retry_count", 0)) + 1,
                                },
                                None, status="interrupted",
                            ),
                        },
                    }
                )
                self.repository.add_message(failed_message)
            recovered_count += 1

        return recovered_count

    def _select_persona(
        self,
        event_id: str,
        personas,
        prior_messages: list[ChatMessage],
    ):
        """整段對話沿用同一人物；新對話只接受事件唯一的 active persona。"""
        locked_persona_id = next(
            (message.persona_id for message in prior_messages if message.persona_id),
            None,
        )
        if locked_persona_id:
            selected = self.repository.get_persona(locked_persona_id)
            if not selected or selected.event_id != event_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Conversation persona is no longer available",
                )
            return selected
        if len(personas) != 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Role-play requires exactly one active historical persona",
            )
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
        conversation_history: list[ChatMessage] | None = None,
        persist_answer_audit: bool = False,
    ) -> tuple[ChatGenerationResult, dict[str, Any], str]:
        """共用正式聊天與 Admin 試跑的生成入口；不在這裡保存正式聊天訊息。

        開啟先審再送時交給 deliver_answer；否則走通用驗證流程。
        私有審查紀錄是否落地另由 persist_answer_audit 控制。
        """
        review = self.answer_review_service
        if review and review.before_delivery(interaction_runtime):
            async def generate(candidate_prompt):
                return await self.llm_provider.generate_chat_response(
                    event=event, persona=selected, condition=condition, task_attempt=task_attempt,
                    user_message=user_message, prompt=candidate_prompt, rag_sources=rag_sources)
            return await deliver_answer(
                review_service=review, generate=generate, runtime=interaction_runtime,
                event=event, attempt=task_attempt, persona=selected,
                history=conversation_history or [], learner_message=user_message, base_prompt=base_prompt,
                persist_audit=persist_answer_audit)
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
                        llm_metadata=generation.llm_metadata,
                        request_messages=generation.request_messages,
                    ),
                    metadata,
                    prompt,
                )

            audit_id = record_rejected_generation(
                stage="chat_contract_validation",
                provider=str(generation.llm_metadata.get("provider", "unknown")),
                model=str(generation.llm_metadata.get("model", "unknown")),
                task_name="chat_response",
                raw_output=generation.response,
                reasons=list(validation.retry_flags),
                context={
                    "event_id": event.id,
                    "attempt_id": task_attempt.id if task_attempt else None,
                    "condition_key": condition.condition_key,
                    "generation_index": generation_index,
                    "llm_call": generation.llm_metadata.get("llm_call", {}),
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
