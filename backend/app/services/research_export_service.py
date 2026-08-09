"""Admin 研究資料重播、統計與匯出服務。"""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Literal

from fastapi import HTTPException, status

from app.core.research_reproducibility import prompt_text_hash, stable_hash
from app.crud.protocols import RepositoryProtocol
from app.models.domain import ChatMessage
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

        participant = (
            self.repository.get_participant_by_auth_user(session.user_id)
            if session.user_id
            else None
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
            stats=self._conversation_stats(messages),
            material_snapshot=self._material_snapshot(logs),
            prompt_records=self._prompt_records(logs),
            research_logs=[log.model_copy(update={"user_id": None}) for log in logs],
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

    def _conversation_stats(self, messages: list[ChatMessage]) -> AdminConversationStats:
        learner = [message for message in messages if message.speaker_type == "learner"]
        assistant = [message for message in messages if message.speaker_type in {"assistant", "persona"}]
        calls = [self._llm_call(message) for message in assistant]
        calls_with_usage = [call for call in calls if call.get("total_tokens") is not None]

        def token_sum(field: str) -> int:
            return sum(int(call.get(field) or 0) for call in calls_with_usage)

        completed_exchanges = sum(
            1
            for message in learner
            if message.operation_status == "completed"
            or message.metadata.get("response_status") == "completed"
        )
        first = messages[0].created_at if messages else None
        last = messages[-1].created_at if messages else None
        duration = int((last - first).total_seconds()) if first and last else None
        coverage = len(calls_with_usage) / len(calls) if calls else 0.0
        return AdminConversationStats(
            total_messages=len(messages),
            learner_messages=len(learner),
            assistant_messages=len(assistant),
            completed_exchanges=completed_exchanges,
            prompt_tokens=token_sum("prompt_tokens"),
            completion_tokens=token_sum("completion_tokens"),
            total_tokens=token_sum("total_tokens"),
            llm_messages_total=len(calls),
            llm_messages_with_usage=len(calls_with_usage),
            token_usage_coverage=round(coverage, 4),
            token_usage_complete=bool(calls) and len(calls_with_usage) == len(calls),
            first_message_at=first.isoformat() if first else None,
            last_message_at=last.isoformat() if last else None,
            duration_seconds=duration,
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
            "completion_tokens", "total_tokens", "prompt_hash", "material_hash",
            "conversation_total_messages", "learner_messages", "assistant_messages",
            "completed_exchanges", "conversation_total_tokens", "token_usage_coverage",
            "task_response_json", "task_judgement_json",
        ]
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            messages: list[ChatMessage | None] = record.messages or [None]
            for message in messages:
                call = self._llm_call(message) if message else {}
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
                    "provider": call.get("provider", ""),
                    "model": call.get("model", ""),
                    "prompt_tokens": call.get("prompt_tokens", ""),
                    "completion_tokens": call.get("completion_tokens", ""),
                    "total_tokens": call.get("total_tokens", ""),
                    "prompt_hash": message.metadata.get("prompt_hash", "") if message else "",
                    "material_hash": record.material_snapshot.material_hash or "",
                    "conversation_total_messages": record.stats.total_messages,
                    "learner_messages": record.stats.learner_messages,
                    "assistant_messages": record.stats.assistant_messages,
                    "completed_exchanges": record.stats.completed_exchanges,
                    "conversation_total_tokens": record.stats.total_tokens,
                    "token_usage_coverage": record.stats.token_usage_coverage,
                    "task_response_json": json.dumps(record.attempt.response_payload if record.attempt else {}, ensure_ascii=False),
                    "task_judgement_json": json.dumps(record.attempt.judgement_payload if record.attempt else {}, ensure_ascii=False),
                })
        # BOM 讓 Excel 直接開啟時正確辨識中文。
        return "\ufeff" + output.getvalue()
