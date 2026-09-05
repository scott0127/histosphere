"""受管理的單機背景觀察；回覆先保存，審查不影響文字、狀態或倒數。"""

import asyncio
from copy import deepcopy
from dataclasses import asdict
import logging

from app.core.answer_review import pending_answer_review
from app.core.config import get_settings
from app.core.interaction_contract import InteractionRuntime
from app.crud.protocols import RepositoryProtocol
from app.models.domain import ChatMessage, Event, TaskAttempt, utc_now
from app.providers.llm.base import LLMProvider
from app.services.llm_generation_audit import record_rejected_generation

logger = logging.getLogger(__name__)


class AnswerReviewService:
    def __init__(self, repository: RepositoryProtocol, provider: LLMProvider):
        self.repository = repository
        self.provider = provider
        self.tasks: dict[str, asyncio.Task] = {}

    def prepare(
        self, message: ChatMessage, *, runtime: InteractionRuntime, event: Event,
        attempt: TaskAttempt | None, history: list[ChatMessage], learner_message: str,
    ) -> dict | None:
        if message.metadata.get("answer_delivery") or not get_settings().llm_answer_review_enabled or runtime.interaction_mode != "scaffold" or not runtime.target:
            return None
        try:
            context = self.build_context(message, runtime=runtime, event=event, attempt=attempt,
                                         history=history, learner_message=learner_message)
            message.metadata["answer_review"] = pending_answer_review(context)
            return context
        except Exception as exc:
            message.metadata["answer_review"] = {
                "status": "unavailable", "failure_type": type(exc).__name__, "mode": "observe",
            }
            logger.warning("Answer review preparation failed: %s", type(exc).__name__)
            return None

    @staticmethod
    def before_delivery(runtime: InteractionRuntime) -> bool:
        settings = get_settings()
        return bool(settings.llm_answer_review_enabled
                    and settings.llm_answer_review_mode == "before_delivery"
                    and runtime.interaction_mode == "scaffold" and runtime.target)

    def build_context(
        self, message: ChatMessage, *, runtime: InteractionRuntime, event: Event,
        attempt: TaskAttempt | None, history: list[ChatMessage], learner_message: str,
    ) -> dict:
        """送出前與背景審查共用凍結證據，不能把生成模型自評當作授權。"""
        if runtime.target:
            target_ids = {runtime.target.question_id}
            if runtime.next_target:
                target_ids.add(runtime.next_target.question_id)
            judgement = attempt.judgement_payload if attempt else {}
            results = deepcopy([r for r in judgement.get("question_results", [])
                if isinstance(r, dict) and r.get("question_id") in target_ids])
            # 舊判定未複製選項時，只讀原活動快照，不用已被管理員修改的新題目。
            if attempt and any(r.get("question_type") == "multiple_choice" and "options" not in r for r in results):
                snapshot = next((log for log in self.repository.list_research_logs_for_session(attempt.session_id)
                    if log.action_type == "session_material_snapshot" and log.task_id == attempt.task_id), None)
                questions = snapshot.payload.get("materials", {}).get("task", {}).get("evaluation_payload", {}).get("questions", []) if snapshot else []
                options = {q["id"]: q.get("options", []) for q in questions}
                for result in results:
                    result.setdefault("options", options.get(result.get("question_id")))
            context = deepcopy({
                "event": event.canonical_name,
                "current_target": asdict(runtime.target),
                "next_target": asdict(runtime.next_target) if runtime.next_target else None,
                "question_results": results,
                "materials": judgement.get("materials", []),
                "task_full_text": judgement.get("error_elicitation_task_full_text"),
                "history": [{"speaker": m.speaker_type, "content": m.content} for m in history
                            if not m.metadata.get("system_fallback")],
                "learner_message": learner_message,
                "runtime": {
                    "corrective_feedback_required": runtime.corrective_feedback_required,
                    "restatement_required": runtime.restatement_required,
                    "disclosure_level": message.metadata.get("disclosure_level"),
                },
                "candidate": {"response": message.content},
            })
            return context
        raise ValueError("Answer review requires an error target")

    def schedule(self, message: ChatMessage, context: dict | None) -> None:
        if context is None or message.id in self.tasks:
            return
        # 唯一排程入口只由新訊息寫入呼叫；讀取與重連不排程。
        work = self._run(message.model_copy(deep=True), context)
        try:
            task = asyncio.create_task(work)
            self.tasks[message.id] = task
            task.add_done_callback(lambda done: self._finished(message.id, done))
        except Exception:
            work.close()
            logger.warning("Answer review scheduling failed; stored reply is unchanged")

    def _finished(self, message_id: str, task: asyncio.Task) -> None:
        self.tasks.pop(message_id, None)
        if not task.cancelled() and task.exception():
            logger.warning("Answer review background failure: %s", type(task.exception()).__name__)

    async def _run(self, message: ChatMessage, context: dict) -> None:
        base = message.metadata["answer_review"]
        try:
            current = await asyncio.to_thread(self.repository.get_message, message.id)
            if not current or current.metadata.get("answer_review") != base or current.content != message.content:
                return
            result = await self.provider.review_answer(context)
            report = {**base, **result, "status": "completed"}
        except asyncio.CancelledError:
            report = {**base, "status": "unavailable", "failure_type": "interrupted"}
        except Exception as exc:
            call = getattr(exc, "metadata", None)
            report = {**base, "status": "unavailable", "failure_type": type(exc).__name__,
                      "llm_call": call.as_dict() if hasattr(call, "as_dict") else None}
        report["finished_at"] = utc_now().isoformat()
        try:
            saved = await asyncio.to_thread(self.repository.finish_answer_review, message.id, base, report)
        except Exception as exc:
            saved = False
            report["persistence_failure_type"] = type(exc).__name__
        # 本機副本是失敗追查備援，不是另一套答案裁判。
        if report.get("findings") or report["status"] == "unavailable" or not saved:
            try:
                call = report.get("llm_call") or {}
                await asyncio.to_thread(record_rejected_generation,
                    stage="answer_review_observation", provider=str(call.get("provider", "unknown")),
                    model=str(call.get("model", "unknown")), task_name="review_answer",
                    raw_output=message.content, reasons=[f["category"] for f in report.get("findings", [])],
                    context={"delivery_blocked": False, "message_id": message.id, "review": report})
            except Exception as exc:
                logger.warning("Answer review audit copy failed: %s", type(exc).__name__)

    def recover_interrupted(self) -> None:
        # 重啟只標記中斷，不再送出付費請求。
        for log in self.repository.list_pending_answer_deliveries():
            log = log.model_copy(deep=True)
            candidate = log.payload["candidate"]
            candidate.update(status="interrupted", failure_type="backend_restart")
            if candidate.get("review"):
                candidate["review"].update(status="unavailable", failure_type="interrupted")
            self.repository.log_research(log)
        for message in self.repository.list_pending_answer_reviews():
            base = message.metadata["answer_review"]
            self.repository.finish_answer_review(message.id, base, {
                **base, "status": "unavailable", "failure_type": "interrupted",
                "finished_at": utc_now().isoformat(),
            })

    async def close(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
