"""Compare direct Gemini REST latency with the project's LiteLLM path.

Only public historical content is sent. Results are written under .dev-logs.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx
from litellm import completion


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import load_local_env  # noqa: E402


SYSTEM_PROMPT = (
    "使用繁體中文。你是1793年秋季身處巴黎的馬克西米連·羅伯斯庇爾。"
    "以第一人稱自我介紹，說明共和國當下的一項危機，最後提出一個自然問題。"
    "不得提到AI、prompt、實驗條件或1794年7月28日以後的事件。"
    "只回傳JSON：{\"response\":\"70至140字回應\"}。"
)
USER_PROMPT = "請開始這段位於法國大革命當下的對話。"


def _extract_google_text(payload: dict[str, Any]) -> str:
    parts = payload["candidates"][0]["content"]["parts"]
    texts = [str(part.get("text", "")) for part in parts if not part.get("thought")]
    return "".join(texts).strip()


def _direct_google(model: str, thinking_config: dict[str, Any]) -> str:
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": USER_PROMPT}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
            "thinkingConfig": thinking_config,
        },
    }
    with httpx.Client(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
        response = client.post(url, headers={"x-goog-api-key": key}, json=body)
        response.raise_for_status()
        return _extract_google_text(response.json())


def _litellm_google(model: str) -> str:
    response = completion(
        model=f"gemini/{model}",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ],
        temperature=0.3,
        max_tokens=2048,
        timeout=45,
        reasoning_effort="low",
        response_format={"type": "json_object"},
    )
    return str(response.choices[0].message.content or "").strip()


def _measure(name: str, call: Callable[[], str]) -> dict[str, Any]:
    started = time.perf_counter()
    raw_output: str | None = None
    try:
        raw_output = call()
        parsed = json.loads(raw_output)
        return {
            "name": name,
            "ok": True,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "raw_output": raw_output,
            "response": parsed.get("response"),
        }
    except Exception as exc:
        return {
            "name": name,
            "ok": False,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_output": raw_output,
        }


def main() -> None:
    load_local_env()
    results = [
        _measure(
            "direct_gemini_2.5_flash_thinking_off",
            lambda: _direct_google("gemini-2.5-flash", {"thinkingBudget": 0}),
        ),
        _measure(
            "direct_gemini_3.6_flash_thinking_low",
            lambda: _direct_google("gemini-3.6-flash", {"thinkingLevel": "low"}),
        ),
        _measure(
            "litellm_gemini_3.6_flash_reasoning_low",
            lambda: _litellm_google("gemini-3.6-flash"),
        ),
    ]
    output_dir = PROJECT_ROOT / ".dev-logs" / "llm-benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"gemini-latency-diagnostic-{timestamp}.json"
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompt_scope": "public_synthetic_french_revolution",
        "results": results,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output_path": str(output_path), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
