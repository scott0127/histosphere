"""Server response timing, separate from learner thinking and retry idle time."""

from time import perf_counter
from typing import Any

from app.models.domain import utc_now


def start_response_timing() -> tuple[dict[str, Any], float]:
    started_at = utc_now().isoformat()
    return {
        "request_started_at": started_at,
        "original_request_started_at": started_at,
        "response_completed_at": None,
        "response_latency_ms": None,
        "attempt_number": 1,
        "status": "processing",
    }, perf_counter()


def finish_response_timing(
    timing: dict[str, Any], started_clock: float | None, *, status: str = "completed",
) -> dict[str, Any]:
    finished_at = utc_now().isoformat()
    return {
        **timing,
        "finished_at": finished_at,
        "response_completed_at": finished_at if status == "completed" else None,
        # A process restart cannot recover its old monotonic clock. Keep it unknown.
        "response_latency_ms": (
            round(max(0, perf_counter() - started_clock) * 1000, 3)
            if started_clock is not None else None
        ),
        "status": status,
    }
