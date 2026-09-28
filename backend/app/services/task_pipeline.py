"""Resumable persisted checkpoints for initial judging and approved chat preparation."""

import hashlib
import json
import logging
from copy import deepcopy

from app.core.interaction_contract import build_interaction_runtime
from app.core.research_reproducibility import record_prompt_snapshot, stable_hash
from app.models.domain import ChatMessage, Conversation, Event, ResearchLog, TaskAttempt, utc_now
from app.services.conversation_opening_service import ConversationOpening
from app.services.llm_generation_audit import record_rejected_generation
from app.services.task_judgement import enrich_task_judgement
from app.services.task_review_service import initial_review_payload

logger = logging.getLogger(__name__)


class TaskPipeline:
    def __init__(self, repository, llm_provider, opening_service):
        self.repository = repository
        self.llm_provider = llm_provider
        self.opening_service = opening_service
        # The current deployment runs one worker. Persisted checkpoints survive its restart.
        self._active: set[str] = set()

    async def process(self, attempt_id: str) -> None:
        if attempt_id in self._active:
            return
        attempt = self.repository.get_task_attempt(attempt_id)
        if not attempt or attempt.status not in {"processing", "preparing_chat"}:
            return
        self._active.add(attempt_id)
        stage = attempt.status
        try:
            attempt = attempt.model_copy(deep=True)
            task = self.repository.get_event_task(attempt.task_id)
            session = self.repository.get_session(attempt.session_id)
            event = self.repository.get_event(attempt.event_id)
            if not task or not session or not event:
                raise RuntimeError("Task submission context is incomplete")
            if session.status in {"completed", "archived"}:
                return
            if stage == "processing":
                await self._judge(attempt, task, event)
            else:
                await self._prepare(attempt, session, event)
        except Exception as exc:
            logger.exception("Task checkpoint %s failed for %s", stage, attempt_id)
            current = self.repository.get_task_attempt(attempt_id)
            if not current or not self.repository.get_session(current.session_id):
                return
            current = current.model_copy(deep=True)
            current.status = "failed"
            current.pipeline_error = {
                "stage": stage, "message": "Task processing failed. The saved submission can be retried.",
                "error_type": type(exc).__name__, "failed_at": utc_now().isoformat(),
            }
            self.repository.save_task_attempt(current)
            llm_call = getattr(getattr(exc, "metadata", None), "as_dict", lambda: {})()
            self.repository.log_research(ResearchLog(
                user_id=current.user_id, session_id=current.session_id, event_id=current.event_id,
                task_id=current.task_id, attempt_id=current.id, action_type="task_submission_failed",
                payload={"stage": stage, "error_type": type(exc).__name__, "llm_call": llm_call or None},
            ))
        finally:
            self._active.discard(attempt_id)

    async def _judge(self, attempt, task, event):
        judgement = deepcopy(attempt.ai_judgement_payload)
        if not judgement:
            judgement = await self.llm_provider.judge_task_attempt(event, task, attempt.response_payload)
            try:
                judgement = enrich_task_judgement(task, attempt.response_payload, judgement)
                if not judgement.get("question_results"):
                    raise ValueError("The task must have question-level judgements for human review")
            except ValueError as exc:
                record_rejected_generation(
                    stage="task_judgement_contract", provider=str(judgement.get("provider", "unknown")),
                    model=str(judgement.get("model", "unknown")), task_name="judge_task_attempt",
                    raw_output=json.dumps(judgement, ensure_ascii=False), reasons=[str(exc)],
                    context={"attempt_id": attempt.id, "task_id": attempt.task_id},
                )
                raise
            judgement["judgement_input_hash"] = stable_hash({
                "event": event, "task": task, "response_payload": attempt.response_payload,
            })
        current = self.repository.get_task_attempt(attempt.id)
        session = self.repository.get_session(attempt.session_id)
        if not current or not session or session.status in {"completed", "archived"}:
            return
        attempt.ai_judgement_payload = judgement
        attempt.judgement_payload = {}
        attempt.review_payload = attempt.review_payload or initial_review_payload(judgement)
        attempt.pipeline_error = {}
        attempt.status = "awaiting_review"
        self.repository.save_task_attempt(attempt)
        self.repository.log_research(ResearchLog(
            user_id=attempt.user_id, session_id=attempt.session_id, event_id=attempt.event_id,
            task_id=attempt.task_id, attempt_id=attempt.id, action_type="task_awaiting_review",
            payload={"judgement_llm_call": judgement.get("llm_call")},
        ))

    async def _prepare(self, attempt, session, event):
        if not attempt.review_payload.get("approved_at"):
            raise RuntimeError("Human approval is required before preparing the conversation")
        condition = self.repository.get_condition_by_key(session.condition_key_snapshot)
        if not condition:
            raise RuntimeError("Experiment condition is missing")
        conversation = self.repository.get_conversation_by_session(session.id)
        messages = self.repository.list_messages(conversation.id) if conversation else []
        if messages:
            greeting_message = messages[0]
        else:
            opening = await self.opening_service.generate(
                event=event, personas=self.repository.list_personas(event.id), condition=condition, attempt=attempt,
            )
            session = self.repository.get_session(session.id)
            current = self.repository.get_task_attempt(attempt.id)
            if not session or not current:
                return
            if session.status in {"completed", "archived"}:
                return
            if not conversation:
                conversation = self.repository.save_conversation(Conversation(
                    event_id=event.id, task_attempt_id=attempt.id, session_id=session.id, user_id=attempt.user_id,
                ))
            greeting_message = self._store_greeting(conversation.id, condition, opening, attempt, event)
        attempt.status = "ready"
        attempt.pipeline_error = {}
        self.repository.save_task_attempt(attempt)
        # Approval/generation waiting never consumes the learner's interaction time.
        self.repository.log_research(ResearchLog(
            user_id=attempt.user_id, session_id=session.id, event_id=event.id, task_id=attempt.task_id,
            attempt_id=attempt.id, conversation_id=conversation.id, message_id=greeting_message.id,
            action_type="task_submission_processed", payload={
                "judgement_llm_call": attempt.ai_judgement_payload.get("llm_call"),
                "opening_llm_call": greeting_message.metadata.get("llm_call"), "stage": "ready",
            },
        ))

    def _store_greeting(
        self,
        conversation_id: str,
        condition,
        opening: ConversationOpening,
        attempt: TaskAttempt,
        event: Event,
    ) -> ChatMessage:
        persona = opening.persona
        system_fallback = bool(opening.metadata.get("system_fallback"))
        profile_payload = persona.prompt_profile if persona else {}
        profile_hash = hashlib.sha256(
            json.dumps(profile_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        message = ChatMessage(
            conversation_id=conversation_id,
            persona_id=persona.id if persona and not system_fallback else None,
            speaker_type="persona" if persona and not system_fallback else "assistant",
            speaker_name="系統提示" if system_fallback else (persona.name if persona else ("AI Tutor" if condition.ebl_enabled else "AI Assistant")),
            sequence_index=self.repository.next_message_sequence(conversation_id),
            content=opening.generation.response,
            annotations=opening.generation.annotations,
            metadata={
                "condition_key": condition.condition_key,
                "task_attempt_id": attempt.id,
                "judgement": attempt.judgement_payload,
                "prompt_hash": hashlib.sha256(opening.prompt.encode("utf-8")).hexdigest(),
                "prompt_modules": [module.name for module in opening.modules],
                "persona_profile_contract": profile_payload.get("contract_version") if persona else None,
                "persona_profile_hash": profile_hash if persona else None,
                **opening.metadata,
                **opening.generation.llm_metadata,
            },
        )
        review = self.opening_service.answer_review_service
        review_context = review.prepare(
            message, runtime=build_interaction_runtime(condition, attempt, []),
            event=event, attempt=attempt,
            history=[], learner_message="",
        ) if review else None
        message = self.repository.add_message(message)
        if attempt.session_id:
            record_prompt_snapshot(
                self.repository,
                session_id=attempt.session_id,
                event_id=attempt.event_id,
                task_id=attempt.task_id,
                attempt_id=attempt.id,
                conversation_id=conversation_id,
                message_id=message.id,
                user_id=attempt.user_id,
                stage="conversation_opening",
                prompt=opening.prompt,
                modules=opening.modules,
                llm_call=opening.generation.llm_metadata.get("llm_call"),
            )
        if review:
            review.schedule(message, review_context)
        return message
