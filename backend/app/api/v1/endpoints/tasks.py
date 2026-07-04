"""Task submission API endpoint.

本模組負責接收 learner 的 task 作答，並交給 TaskService 完成
LLM 判斷、task_attempts 儲存，以及 conversation 解鎖。

Routes:
    PATCH /api/tasks/{task_id}/draft:   保存 task 草稿。
    POST  /api/tasks/{task_id}/submit:  送出 task 作答。
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_task_service
from app.schemas.requests import TaskDraftRequest, TaskSubmitRequest
from app.schemas.responses import TaskDraftResponse, TaskSubmitResponse
from app.services import TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.patch("/{task_id}/draft", response_model=TaskDraftResponse)
def save_task_draft(
    task_id: UUID,
    request: TaskDraftRequest,
    service: TaskService = Depends(get_task_service),
) -> TaskDraftResponse:
    """保存 task 草稿，供 learner 重新整理或換帳號後恢復作答。

    Learner 在作答過程中可隨時呼叫此端點暫存進度。
    草稿會寫入 task_attempts 表，不觸發 LLM 判斷流程，
    也不會建立 conversation。

    Args:
        task_id: 目標 task 的 UUID。
        request: 草稿請求，包含 session_id、response_payload
            與可選 user_id。
        service: 由 Dependency Injection 注入的 TaskService 實例。

    Returns:
        TaskDraftResponse: 包含已儲存的 TaskAttempt 紀錄。
    """
    return service.save_draft(str(task_id), request)


@router.post("/{task_id}/submit", response_model=TaskSubmitResponse)
async def submit_task(
    task_id: UUID,
    request: TaskSubmitRequest,
    service: TaskService = Depends(get_task_service),
) -> TaskSubmitResponse:
    """送出指定 task 的作答；成功後會建立可進入聊天頁的 conversation。

    完整流程：接收 response_payload → LLM 自動評分（judgement）→
    建立 TaskAttempt → 建立 Conversation → 產生 greeting 訊息。
    前端收到回應後即可導向聊天頁。

    Args:
        task_id: 目標 task 的 UUID。
        request: 提交請求，包含 session_id、response_payload
            與可選 user_id。
        service: 由 Dependency Injection 注入的 TaskService 實例。

    Returns:
        TaskSubmitResponse: 包含 attempt_id、conversation_id、
            event、task、personas、condition、attempt、
            judgement、greeting 與初始 history。
    """
    return await service.submit_task(str(task_id), request)
