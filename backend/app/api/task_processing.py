"""Run durable task checkpoints once per application process.

The database owns progress. Reopening either screen resumes unfinished work;
the local set only prevents duplicate work within the single-server deployment.
"""

import asyncio
import logging

from fastapi import BackgroundTasks, Request

from app.services import TaskService

logger = logging.getLogger(__name__)
PROCESSING_STAGES = {"processing", "preparing_chat"}


def schedule_task_processing(
    request: Request,
    service: TaskService,
    attempt_id: str,
    background_tasks: BackgroundTasks | None = None,
) -> None:
    active = request.app.state.active_task_attempts
    if attempt_id in active:
        return
    active.add(attempt_id)

    async def run() -> None:
        try:
            await service.process_submission(attempt_id)
        except Exception:
            logger.exception("Task checkpoint processing failed: %s", attempt_id)
        finally:
            active.discard(attempt_id)

    if background_tasks is not None:
        background_tasks.add_task(run)
    else:
        # A StreamingResponse runs BackgroundTasks only after its stream closes.
        # Keep this task alive independently so SSE clients see the next checkpoint.
        task = asyncio.create_task(run())
        request.app.state.task_stream_workers.add(task)
        task.add_done_callback(request.app.state.task_stream_workers.discard)
