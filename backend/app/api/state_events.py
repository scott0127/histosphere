"""Small SSE change notifications derived from durable database state."""

import asyncio
import json
import time
from collections.abc import Callable

from fastapi import Request
from fastapi.responses import StreamingResponse


def state_event_response(request: Request, read_state: Callable[[], dict]) -> StreamingResponse:
    async def events():
        previous = None
        started = heartbeat = time.monotonic()
        # Periodic reconnection revalidates authentication. No event replay is needed:
        # every connection emits current state, and clients reload the DB snapshot.
        while time.monotonic() - started < 45:
            if await request.is_disconnected():
                return
            state = await asyncio.to_thread(read_state)
            payload = json.dumps(state, ensure_ascii=False, sort_keys=True)
            if payload != previous:
                yield f"event: change\ndata: {payload}\n\n"
                previous = payload
            if time.monotonic() - heartbeat >= 10:
                yield ": keep-alive\n\n"
                heartbeat = time.monotonic()
            await asyncio.sleep(1)

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no",
    })
