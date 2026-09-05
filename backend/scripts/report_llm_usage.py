"""彙總本機 LLM 呼叫帳本；只報估算，不代表供應商實際扣款。"""
import argparse
from datetime import datetime
import json
from pathlib import Path


def summarize(path: Path, since: datetime | None = None) -> dict:
    attempts = {}
    malformed_lines = 0
    for line in path.read_text(encoding="utf-8").splitlines() if path.exists() else []:
        try:
            row = json.loads(line)
            attempt_id = row["attempt_id"]
            stamp = datetime.fromisoformat(row["recorded_at"])
        except (ValueError, KeyError, TypeError):
            malformed_lines += 1
            continue
        if since and stamp < since:
            continue
        # started/result 共用同一 ID；使用最後結果，重複匯入也不再累加。
        attempts[attempt_id] = row
    groups = {}
    for row in attempts.values():
        key = (row["provider"], row["model"], row.get("key_fingerprint"))
        group = groups.setdefault(key, dict(provider=key[0], model=key[1], key_fingerprint=key[2],
            attempts=0, unknown_cost_attempts=0, prompt_tokens=0, completion_tokens=0,
            total_tokens=0, estimated_known_cost_usd=0.0))
        group["attempts"] += 1
        cost = row.get("estimated_cost_usd")
        if cost is None:
            group["unknown_cost_attempts"] += 1
        else:
            group["estimated_known_cost_usd"] += cost
        for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
            group[field] += row.get(field) or 0
    return {"source": str(path), "estimate_not_invoice": True,
            "malformed_lines": malformed_lines, "groups": list(groups.values())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path(__file__).resolve().parents[2] / ".dev-logs/llm-usage.jsonl")
    parser.add_argument("--since", help="ISO timestamp, e.g. 2026-09-04T00:00:00+08:00")
    args = parser.parse_args()
    since = datetime.fromisoformat(args.since) if args.since else None
    if since is not None and since.tzinfo is None:
        parser.error("--since must include a timezone")
    print(json.dumps(summarize(args.path, since), ensure_ascii=False, indent=2))
