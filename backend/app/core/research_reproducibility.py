"""研究重現性快照與雜湊工具。

本模組只把 Session 開始時的素材與實際送往 LLM 的 Prompt 寫入既有
``research_logs``。不新增資料表，也不回寫或改動歷史素材。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Iterable

from pydantic import BaseModel

from app.crud.protocols import RepositoryProtocol
from app.models.domain import ExperimentSession, ResearchLog


SNAPSHOT_VERSION = "1"


def _jsonable(value: Any) -> Any:
    """把 Pydantic 與時間欄位轉成可穩定排序的 JSON 資料。"""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    """輸出不受欄位順序影響的 JSON，供研究資料比對。"""
    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def stable_hash(value: Any) -> str:
    """計算研究資料的 SHA-256。"""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def prompt_text_hash(prompt: str) -> str:
    """沿用訊息 metadata 的 Prompt 純文字 SHA-256 算法。"""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def record_session_material_snapshot(
    repository: RepositoryProtocol,
    session: ExperimentSession,
) -> ResearchLog:
    """保存 Session 建立當下的事件、Task、Condition 與人物內容。"""
    event = repository.get_event(session.event_id)
    task = repository.get_latest_event_task(session.event_id)
    condition = repository.get_condition_by_key(session.condition_key_snapshot)
    if not event or not task or not condition:
        raise ValueError("Session material snapshot context is incomplete")

    personas = repository.list_personas(session.event_id, active_only=False)
    materials = {
        "snapshot_version": SNAPSHOT_VERSION,
        "event": event,
        "task": task,
        "condition": condition,
        "personas": personas,
    }
    payload = {
        "snapshot_version": SNAPSHOT_VERSION,
        "material_hash": stable_hash(materials),
        "materials": _jsonable(materials),
    }
    return repository.log_research(
        ResearchLog(
            user_id=session.user_id,
            session_id=session.id,
            event_id=session.event_id,
            task_id=task.id,
            action_type="session_material_snapshot",
            payload=payload,
        )
    )


def record_prompt_snapshot(
    repository: RepositoryProtocol,
    *,
    session_id: str,
    event_id: str,
    prompt: str,
    modules: Iterable[Any],
    stage: str,
    user_id: str | None = None,
    task_id: str | None = None,
    attempt_id: str | None = None,
    conversation_id: str | None = None,
    message_id: str | None = None,
    llm_call: dict[str, Any] | None = None,
) -> ResearchLog:
    """保存一次實際 LLM 呼叫所使用的 Prompt 與模組內容。"""
    prompt_modules = [
        {
            "name": str(getattr(module, "name", "unknown")),
            "content": str(getattr(module, "content", "")),
        }
        for module in modules
    ]
    return repository.log_research(
        ResearchLog(
            user_id=user_id,
            session_id=session_id,
            event_id=event_id,
            task_id=task_id,
            attempt_id=attempt_id,
            conversation_id=conversation_id,
            message_id=message_id,
            action_type="llm_prompt_snapshot",
            payload={
                "snapshot_version": SNAPSHOT_VERSION,
                "stage": stage,
                "prompt_hash": prompt_text_hash(prompt),
                "prompt": prompt,
                "modules": prompt_modules,
                "llm_call": llm_call or None,
            },
        )
    )
