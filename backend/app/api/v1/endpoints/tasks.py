from fastapi import APIRouter, Depends

from app.api.deps import get_task_service
from app.schemas.requests import TaskSubmitRequest
from app.schemas.responses import TaskSubmitResponse
from app.services import TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/{task_id}/submit", response_model=TaskSubmitResponse)
async def submit_task(
    task_id: str,
    request: TaskSubmitRequest,
    service: TaskService = Depends(get_task_service),
) -> TaskSubmitResponse:
    return await service.submit_task(task_id, request)
