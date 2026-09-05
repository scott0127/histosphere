"""Durable local audit records for rejected LLM generations.

The learner never sees these records. They intentionally retain the raw rejected
completion so prompt/schema failures can be reproduced during development. The
default path lives under ``.dev-logs`` and is excluded from version control.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4


_AUDIT_LOCK = Lock()


def record_llm_usage(*, api_key: str | None, **record: Any) -> None:
    """逐次記錄呼叫開始與結果；沒有用量時保留未知，不當成免費。"""
    path = Path(os.getenv("LLM_USAGE_LOG_PATH", ".dev-logs/llm-usage.jsonl"))
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[3] / path
    entry = {
        **record,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "key_fingerprint": hashlib.sha256(api_key.encode()).hexdigest()[:16] if api_key else None,
        "cost_basis": "provider_usage_litellm_estimate_not_invoice",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with _AUDIT_LOCK:
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")
            file.flush()
            os.fsync(file.fileno())


def _audit_path() -> Path:
    configured = os.getenv("LLM_REJECTION_LOG_PATH")
    if configured:
        path = Path(configured)
        if path.is_absolute():
            return path
    else:
        path = Path(".dev-logs/llm-generation-rejections.jsonl")
    project_root = Path(__file__).resolve().parents[3]
    return project_root / path


def record_rejected_generation(
    *,
    stage: str,
    provider: str,
    model: str,
    task_name: str,
    raw_output: str | None,
    reasons: list[str] | tuple[str, ...],
    context: dict[str, Any] | None = None,
) -> str:
    """Append one rejected completion without storing prompts or credentials."""

    record_id = str(uuid4())
    output = raw_output or ""
    record = {
        "record_id": record_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "provider": provider,
        "model": model,
        "task_name": task_name,
        "reasons": [str(reason) for reason in reasons],
        "raw_output": raw_output,
        "raw_output_length": len(output),
        "raw_output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "context": context or {},
    }
    path = _audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, default=str)
    with _AUDIT_LOCK:
        with path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(line + "\n")
    return record_id
