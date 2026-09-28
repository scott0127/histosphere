"""Admin 研究資料重播、統計與匯出服務。"""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Literal

from fastapi import HTTPException, status

from app.core.research_reproducibility import prompt_text_hash, stable_hash
from app.crud.protocols import RepositoryProtocol
from app.models.domain import ChatMessage, ExperimentSession, ResearchLog, TaskAttempt
from app.services.conversation_metrics import conversation_metrics
from app.services.llm_usage_summary import usage_breakdown
from app.schemas.responses import (
    AdminConversationStats,
    AdminMaterialSnapshot,
    AdminPromptRecord,
    AdminSessionResearchResponse,
)


class ResearchExportService:
    """從既有資料表整理研究資料，不建立第二份來源。"""

    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def session_research(self, session_id: str) -> AdminSessionResearchResponse:
        """回傳單一 Session 的完整逐字稿、作答、Prompt 與統計。"""
        session = self.repository.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment session not found")

        event = self.repository.get_event(session.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        # 新 Session 以凍結的 registry id 歸屬；舊資料才退回 Auth 對應。
        participant = (
            self.repository.get_participant(session.participant_id)
            if session.participant_id
            else (
                self.repository.get_participant_by_auth_user(session.user_id)
                if session.user_id
                else None
            )
        )
        participant_bound = participant is not None and not session.is_admin_test
        if session.is_admin_test:
            participant_code = "ADMIN_TEST"
        elif participant:
            participant_code = participant.code
        else:
            participant_code = "UNMAPPED"
        attempt = self.repository.get_task_attempt_for_session(session.id)
        task = (
            self.repository.get_event_task(attempt.task_id)
            if attempt
            else self.repository.get_latest_event_task(event.id)
        )
        conversation = self.repository.get_conversation_by_session(session.id)
        messages = self.repository.list_messages(conversation.id) if conversation else []
        logs = self.repository.list_research_logs_for_session(session.id)

        return AdminSessionResearchResponse(
            participant_code=participant_code,
            participant_bound=participant_bound,
            session=session.model_copy(update={"user_id": None}),
            event=event,
            condition=self.repository.get_condition_by_key(session.condition_key_snapshot),
            task=task,
            attempt=attempt.model_copy(update={"user_id": None}) if attempt else None,
            conversation=(
                conversation.model_copy(update={"user_id": None})
                if conversation
                else None
            ),
            messages=messages,
            stats=self._session_stats(messages, attempt, logs, session),
            material_snapshot=self._material_snapshot(logs),
            prompt_records=self._prompt_records(logs),
            research_logs=[log.model_copy(update={"user_id": None}) for log in logs],
            posttest=self.repository.get_posttest(session.id),
        )

    def export(self, export_format: Literal["json", "csv"]) -> tuple[str, str, str]:
        """只輸出已綁定受測者的正式 Session，不混入 Admin test 或孤兒資料。"""
        records = [
            record
            for session in self.repository.list_sessions()
            if not session.is_admin_test
            for record in [self.session_research(session.id)]
            if record.participant_bound
        ]
        if export_format == "json":
            content = json.dumps(
                [record.model_dump(mode="json") for record in records],
                ensure_ascii=False,
                indent=2,
            )
            return content, "application/json; charset=utf-8", "histosphere-research.json"
        return self._csv(records), "text/csv; charset=utf-8", "histosphere-research.csv"

    @staticmethod
    def _llm_call(message: ChatMessage) -> dict[str, Any]:
        value = message.metadata.get("llm_call", {})
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _judgement_llm_call(attempt: TaskAttempt | None) -> dict[str, Any]:
        if not attempt or not isinstance(attempt.judgement_payload, dict):
            return {}
        value = attempt.judgement_payload.get("llm_call", {})
        return value if isinstance(value, dict) else {}

    def _session_stats(
        self,
        messages: list[ChatMessage],
        attempt: TaskAttempt | None,
        logs: list[ResearchLog],
        session: ExperimentSession | None = None,
    ) -> AdminConversationStats:
        """統計 Task judge、開場、聊天及失敗生成的完整 Session 用量。"""

        learner = [message for message in messages if message.speaker_type == "learner"]
        assistant = [message for message in messages if message.speaker_type in {"assistant", "persona"}
                     and not message.metadata.get("system_fallback")]
        message_calls = [self._llm_call(message) for message in assistant]
        calls: list[dict[str, Any]] = []
        seen_correlation_ids: set[str] = set()

        def append_call(call: dict[str, Any], *, expected: bool = False, stage: str = "unknown") -> None:
            """以 correlation id 去重；預期呼叫缺資料時仍保留以顯示覆蓋率。"""

            if not call and not expected:
                return
            correlation_id = str(call.get("correlation_id") or "").strip()
            if correlation_id and correlation_id in seen_correlation_ids:
                return
            if correlation_id:
                seen_correlation_ids.add(correlation_id)
            calls.append({**call, "task_name": call.get("task_name") or stage})

        if attempt:
            append_call(self._judgement_llm_call(attempt), expected=True, stage="judge_task_attempt")
        for index, call in enumerate(message_calls):
            append_call(call, expected=True, stage="generate_greeting" if index == 0 else "generate_chat_response")
        # 觀察用量單獨計費，但不算一則對話；尚未回報用量時不可假裝成本完整。
        for message in assistant:
            if message.metadata.get("answer_delivery"):
                continue
            review = message.metadata.get("answer_review")
            if isinstance(review, dict):
                append_call(review.get("llm_call") or {}, expected=True, stage="review_answer")
        # 同一候選可能有待審與完成兩筆快照；只計最新版本，再以 call id 去重。
        candidates = {}
        for log in logs:
            if log.action_type == "answer_delivery_candidate":
                candidate = log.payload.get("candidate", {})
                candidates[(log.payload.get("delivery_id"), candidate.get("index"))] = candidate
        for message in messages:
            delivery = message.metadata.get("answer_delivery", {})
            for candidate in delivery.get("candidates", []):
                candidates[(delivery.get("id"), candidate.get("index"))] = candidate
        for candidate in candidates.values():
            append_call(candidate.get("generation_call") or {}, expected=True, stage="generate_chat_response")
            if candidate.get("review") or candidate.get("review_call"):
                append_call(candidate.get("review_call") or {}, expected=True, stage="review_answer")
        # 失敗聊天沒有 AI 訊息，呼叫資料會保存在 learner operation。
        for message in learner:
            if message.operation_status == "failed":
                append_call(self._llm_call(message))
        # 開場失敗時沒有可附掛 metadata 的 AI 訊息，因此從失敗紀錄補回。
        for log in logs:
            if log.action_type not in {"task_submission_failed", "response_generation_failed"}:
                continue
            value = log.payload.get("llm_call")
            append_call(value if isinstance(value, dict) else {})

        calls_with_usage = [call for call in calls if call.get("total_tokens") is not None]
        calls_with_cost = [call for call in calls if call.get("estimated_cost_usd") is not None]

        def token_sum(field: str) -> int:
            return sum(int(call.get(field) or 0) for call in calls_with_usage)

        metrics = conversation_metrics(messages, session, logs=logs)
        first = messages[0].created_at if messages else None
        last = messages[-1].created_at if messages else None
        duration = int((last - first).total_seconds()) if first and last else None
        cost_complete = bool(calls) and len(calls_with_cost) == len(calls)
        breakdown = usage_breakdown(calls)
        requests = sum(row.requests for row in breakdown)
        reported_requests = sum(row.token_reported_requests for row in breakdown)
        coverage = reported_requests / requests if requests else 0.0
        complete_tokens = requests > 0 and reported_requests == requests
        cost_complete = cost_complete and sum(row.cost_reported_requests for row in breakdown) == requests
        return AdminConversationStats(
            total_messages=len(messages),
            learner_messages=len(learner),
            assistant_messages=len(assistant),
            **metrics,
            prompt_tokens=token_sum("prompt_tokens"),
            cached_prompt_tokens=token_sum("cached_prompt_tokens"),
            completion_tokens=token_sum("completion_tokens"),
            reasoning_tokens=token_sum("reasoning_tokens"),
            total_tokens=token_sum("total_tokens"),
            llm_calls_total=len(calls),
            llm_calls_with_usage=len(calls_with_usage),
            llm_messages_total=len(message_calls),
            llm_messages_with_usage=sum(
                1 for call in message_calls if call.get("total_tokens") is not None
            ),
            token_usage_coverage=round(coverage, 4),
            token_usage_complete=complete_tokens,
            estimated_cost_usd=(
                round(sum(float(call["estimated_cost_usd"]) for call in calls_with_cost), 8)
                if cost_complete
                else None
            ),
            cost_usage_complete=cost_complete,
            first_message_at=first.isoformat() if first else None,
            last_message_at=last.isoformat() if last else None,
            duration_seconds=duration,
            usage_breakdown=breakdown,
        )

    @staticmethod
    def _material_snapshot(logs) -> AdminMaterialSnapshot:
        log = next((item for item in logs if item.action_type == "session_material_snapshot"), None)
        if not log:
            return AdminMaterialSnapshot(status="legacy_missing")
        materials = log.payload.get("materials", {})
        material_hash = str(log.payload.get("material_hash") or "")
        return AdminMaterialSnapshot(
            status="captured",
            material_hash=material_hash or None,
            hash_verified=bool(material_hash and stable_hash(materials) == material_hash),
            captured_at=log.created_at.isoformat(),
            materials=materials if isinstance(materials, dict) else {},
        )

    @staticmethod
    def _prompt_records(logs) -> list[AdminPromptRecord]:
        records: list[AdminPromptRecord] = []
        for log in logs:
            if log.action_type != "llm_prompt_snapshot":
                continue
            prompt = str(log.payload.get("prompt") or "")
            prompt_hash = str(log.payload.get("prompt_hash") or "")
            modules = log.payload.get("modules", [])
            records.append(
                AdminPromptRecord(
                    stage=str(log.payload.get("stage") or "unknown"),
                    message_id=log.message_id,
                    prompt_hash=prompt_hash,
                    hash_verified=bool(prompt_hash and prompt_text_hash(prompt) == prompt_hash),
                    prompt=prompt,
                    modules=modules if isinstance(modules, list) else [],
                    llm_call=(
                        log.payload.get("llm_call")
                        if isinstance(log.payload.get("llm_call"), dict)
                        else None
                    ),
                    created_at=log.created_at.isoformat(),
                )
            )
        return records

    def _csv(self, records: list[AdminSessionResearchResponse]) -> str:
        output = io.StringIO()
        fields = [
            "participant_code", "session_id", "event_name", "condition_key", "session_status",
            "timer_started_at", "timer_ends_at", "message_index", "speaker_type", "speaker_name",
            "message", "message_created_at", "provider", "model", "prompt_tokens",
            "delivery_phase", "delivered_after_deadline",
            "cached_prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens",
            "prompt_hash", "material_hash",
            "conversation_total_messages", "learner_messages", "assistant_messages",
            "completed_exchanges", "llm_calls_total", "session_prompt_tokens",
            "session_completion_tokens", "session_total_tokens", "estimated_cost_usd",
            "token_usage_coverage",
            "message_characters", "message_token_usage_complete",
            "conversation_total_characters", "learner_characters", "assistant_characters", "system_characters",
            "assistant_total_tokens", "assistant_average_tokens", "assistant_token_usage_complete",
            "round_trip_index", "round_trip_status", "round_trip_question_id", "round_trip_started_at", "round_trip_response_at",
            "round_trip_thinking_seconds", "round_trip_response_seconds", "round_trip_generation_seconds", "round_trip_elapsed_seconds", "round_trip_timing_source",
            "learning_duration_seconds", "corrected_questions", "learning_denominator", "learning_average_seconds_per_question",
            "learning_timing_source", "learning_is_complete", "learning_questions_json",
            "task_response_json", "task_judgement_json",
            "posttest_stage", "posttest_instrument_version", "posttest_is_placeholder", "posttest_response_json",
        ]
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            messages: list[ChatMessage | None] = record.messages or [None]
            message_metrics = {row.message_id: row for row in record.stats.message_metrics}
            round_trips = {
                message_id: row for row in record.stats.round_trips
                for message_id in (row.learner_message_id, row.assistant_message_id) if message_id
            }
            for message in messages:
                call = self._llm_call(message) if message else {}
                metric = message_metrics.get(message.id) if message else None
                trip = round_trips.get(message.id) if message else None
                learning = record.stats.learning
                writer.writerow({
                    "participant_code": record.participant_code,
                    "session_id": record.session.id,
                    "event_name": record.event.canonical_name,
                    "condition_key": record.session.condition_key_snapshot,
                    "session_status": record.session.status,
                    "timer_started_at": record.session.timer_started_at.isoformat() if record.session.timer_started_at else "",
                    "timer_ends_at": record.session.timer_ends_at.isoformat() if record.session.timer_ends_at else "",
                    "message_index": message.sequence_index if message else "",
                    "speaker_type": message.speaker_type if message else "",
                    "speaker_name": message.speaker_name if message else "",
                    "message": message.content if message else "",
                    "message_created_at": message.created_at.isoformat() if message else "",
                    "delivery_phase": message.metadata.get("delivery_phase", "") if message else "",
                    "delivered_after_deadline": message.metadata.get("delivered_after_deadline", "") if message else "",
                    "provider": call.get("provider", ""),
                    "model": call.get("model", ""),
                    "prompt_tokens": call.get("prompt_tokens", ""),
                    "cached_prompt_tokens": call.get("cached_prompt_tokens", ""),
                    "completion_tokens": call.get("completion_tokens", ""),
                    "reasoning_tokens": call.get("reasoning_tokens", ""),
                    "total_tokens": call.get("total_tokens", ""),
                    "prompt_hash": message.metadata.get("prompt_hash", "") if message else "",
                    "material_hash": record.material_snapshot.material_hash or "",
                    "conversation_total_messages": record.stats.total_messages,
                    "learner_messages": record.stats.learner_messages,
                    "assistant_messages": record.stats.assistant_messages,
                    "completed_exchanges": record.stats.completed_exchanges,
                    "llm_calls_total": record.stats.llm_calls_total,
                    "session_prompt_tokens": record.stats.prompt_tokens,
                    "session_completion_tokens": record.stats.completion_tokens,
                    "session_total_tokens": record.stats.total_tokens,
                    "estimated_cost_usd": (
                        record.stats.estimated_cost_usd
                        if record.stats.estimated_cost_usd is not None
                        else ""
                    ),
                    "token_usage_coverage": record.stats.token_usage_coverage,
                    "message_characters": metric.characters if metric else "",
                    "message_token_usage_complete": metric.token_usage_complete if metric else "",
                    "conversation_total_characters": record.stats.total_characters,
                    "learner_characters": record.stats.learner_characters,
                    "assistant_characters": record.stats.assistant_characters,
                    "system_characters": record.stats.system_characters,
                    "assistant_total_tokens": record.stats.assistant_total_tokens,
                    "assistant_average_tokens": record.stats.assistant_average_tokens,
                    "assistant_token_usage_complete": record.stats.assistant_token_usage_complete,
                    "round_trip_index": trip.index if trip else "",
                    "round_trip_status": trip.status if trip else "",
                    "round_trip_question_id": trip.question_id if trip else "",
                    "round_trip_started_at": trip.started_at if trip else "",
                    "round_trip_response_at": trip.response_at if trip else "",
                    "round_trip_thinking_seconds": trip.thinking_seconds if trip else "",
                    "round_trip_response_seconds": trip.response_seconds if trip else "",
                    "round_trip_generation_seconds": trip.generation_seconds if trip else "",
                    "round_trip_elapsed_seconds": trip.elapsed_seconds if trip else "",
                    "round_trip_timing_source": trip.timing_source if trip else "",
                    "learning_duration_seconds": learning.duration_seconds,
                    "corrected_questions": learning.corrected_questions,
                    "learning_denominator": learning.denominator,
                    "learning_average_seconds_per_question": learning.average_seconds_per_question,
                    "learning_timing_source": learning.timing_source,
                    "learning_is_complete": learning.is_complete,
                    "learning_questions_json": json.dumps([row.model_dump() for row in learning.questions], ensure_ascii=False),
                    "task_response_json": json.dumps(record.attempt.response_payload if record.attempt else {}, ensure_ascii=False),
                    "task_judgement_json": json.dumps(record.attempt.judgement_payload if record.attempt else {}, ensure_ascii=False),
                    "posttest_stage": record.posttest.stage if record.posttest else "",
                    "posttest_instrument_version": record.posttest.instrument_version if record.posttest else "",
                    "posttest_is_placeholder": record.posttest.is_placeholder if record.posttest else "",
                    "posttest_response_json": json.dumps(record.posttest.model_dump(mode="json") if record.posttest else None, ensure_ascii=False),
                })
        # BOM 讓 Excel 直接開啟時正確辨識中文。
        return "\ufeff" + output.getvalue()
