"""Task submission API endpoint.

本模組負責接收 learner 的 task 作答，並交給 TaskService 完成
LLM 判斷、task_attempts 儲存，以及 conversation 解鎖。
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_task_service
from app.schemas.requests import TaskDraftRequest, TaskSubmitRequest
from app.schemas.responses import TaskDraftResponse, TaskSubmitResponse
from app.services import TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.patch("/{task_id}/draft", response_model=TaskDraftResponse)
def save_task_draft(
    task_id: str,
    request: TaskDraftRequest,
    service: TaskService = Depends(get_task_service),
) -> TaskDraftResponse:
    """保存 task 草稿，供 learner 重新整理或換帳號後恢復作答。"""
    return service.save_draft(task_id, request)


@router.post("/{task_id}/submit", response_model=TaskSubmitResponse)
async def submit_task(
    task_id: str,
    request: TaskSubmitRequest,
    service: TaskService = Depends(get_task_service),
) -> TaskSubmitResponse:
    """送出指定 task 的作答；成功後會建立可進入聊天頁的 conversation。"""
    return await service.submit_task(task_id, request)
