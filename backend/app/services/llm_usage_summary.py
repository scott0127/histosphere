"""整理管理員看到的 Token 與費用；只讀紀錄，不會呼叫模型或查詢帳單。

用量帳本逐次記錄請求，活動 metadata 可能把數次重試合在一起。
兩種來源分開統計，避免把同一筆用量重複相加；未知費用也不能假裝是零。
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.responses import AdminLLMUsageResponse, AdminLLMUsageRow


def read_usage_attempts(path: Path, since: datetime | None = None) -> tuple[list[dict], int]:
    """同一 attempt_id 只保留一份結果，另外回報讀不到的紀錄行數。"""
    attempts: dict[str, dict] = {}
    malformed = 0
    if not path.exists():
        return [], 0
    with path.open(encoding="utf-8") as source:
        for line in source:
            try:
                row = json.loads(line)
                if (
                    not isinstance(row, dict)
                    or not isinstance(row.get("attempt_id"), str)
                    or not row["attempt_id"]
                ):
                    raise ValueError("missing attempt id")
                stamp = datetime.fromisoformat(row["recorded_at"])
                if stamp.tzinfo is None:
                    raise ValueError("missing timezone")
            except (ValueError, KeyError, TypeError):
                malformed += 1
                continue
            # 同一請求會先寫 started 再寫結果；重複的開始紀錄不能蓋掉已完成的用量。
            prior = attempts.get(row["attempt_id"])
            if prior and row.get("status") == "started" and prior.get("status") != "started":
                continue
            attempts[row["attempt_id"]] = row
    rows = list(attempts.values())
    if since:
        rows = [row for row in rows if datetime.fromisoformat(row["recorded_at"]) >= since]
    return rows, malformed


def _number(value):
    """只接受有效的非負數；Python 的 True 雖能當作 1，也不能算成一次用量。"""
    return (
        value
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
        else None
    )


def _reported_count(value, *, count: int, known: bool, ledger: bool) -> int:
    """計算有回報用量的請求數；只有合計值時，不假設每次重試都有完整紀錄。"""
    if not ledger and value is not None:
        return min(count, int(_number(value) or 0))
    return count if known and (ledger or count == 1) else 0


def usage_breakdown(calls: list[dict], *, ledger: bool = False) -> list[AdminLLMUsageRow]:
    """依功能、供應商、模型分組，同時保留總請求數與用量完整度。"""
    groups: dict[tuple, AdminLLMUsageRow] = {}
    for call in calls:
        key = (
            str(call.get("task_name") or "unknown"),
            str(call.get("provider") or "unknown"),
            str(call.get("model") or "unknown"),
        )
        row = groups.setdefault(key, AdminLLMUsageRow(stage=key[0], provider=key[1], model=key[2]))
        count = 1 if ledger else max(1, int(_number(call.get("attempt_count")) or 1))
        row.requests += count
        total = _number(call.get("total_tokens"))
        cost = _number(call.get("estimated_cost_usd"))
        # 舊資料即使有多次嘗試的總用量，也不代表每一次都成功回報。
        reported_tokens = call.get("usage_reported_attempts")
        reported_cost = call.get("cost_reported_attempts")
        row.token_reported_requests += _reported_count(
            reported_tokens, count=count, known=total is not None, ledger=ledger
        )
        row.cost_reported_requests += _reported_count(
            reported_cost, count=count, known=cost is not None, ledger=ledger
        )
        for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
            setattr(row, field, getattr(row, field) + int(_number(call.get(field)) or 0))
        known_cost = _number(call.get("estimated_known_cost_usd"))
        row.estimated_known_cost_usd += known_cost if known_cost is not None else (cost or 0)
    for row in groups.values():
        row.estimated_known_cost_usd = round(row.estimated_known_cost_usd, 10)
    return sorted(groups.values(), key=lambda row: (row.stage, row.provider, row.model))


def ledger_summary(path: Path) -> AdminLLMUsageResponse:
    calls, malformed = read_usage_attempts(path)
    stamps = [datetime.fromisoformat(call["recorded_at"]).astimezone(timezone.utc) for call in calls]
    return AdminLLMUsageResponse(
        rows=usage_breakdown(calls, ledger=True),
        log_available=path.exists(),
        malformed_lines=malformed,
        first_recorded_at=min(stamps).isoformat() if stamps else None,
        last_recorded_at=max(stamps).isoformat() if stamps else None,
    )
