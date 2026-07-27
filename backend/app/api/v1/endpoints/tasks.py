"""Task submission API endpoint.

本模組負責接收 learner 的 task 作答，並交給 TaskService 完成
LLM 判斷、task_attempts 儲存，以及 conversation 解鎖。

Routes:
    PATCH /api/tasks/{task_id}/draft:   保存 task 草稿。
    POST  /api/tasks/{task_id}/submit:  送出 task 作答。
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from app.api.deps import get_task_service, require_active_participant_actor
from app.core.auth import AuthenticatedActor
from app.schemas.requests import TaskDraftRequest, TaskSubmitRequest
from app.schemas.responses import (
    TaskDraftResponse,
    TaskSubmissionAcceptedResponse,
    TaskSubmissionStatusResponse,
)
from app.services import TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


async def _process_and_release(request: Request, service: TaskService, attempt_id: str) -> None:
    try:
        await service.process_submission(attempt_id)
    finally:
        request.app.state.active_task_attempts.discard(attempt_id)


def _schedule_processing(
    request: Request,
    background_tasks: BackgroundTasks,
    service: TaskService,
    attempt_id: str,
) -> None:
    active = getattr(request.app.state, "active_task_attempts", None)
    if active is None:
        active = set()
        request.app.state.active_task_attempts = active
    if attempt_id in active:
        return
    active.add(attempt_id)
    background_tasks.add_task(_process_and_release, request, service, attempt_id)


@router.patch("/{task_id}/draft", response_model=TaskDraftResponse)
def save_task_draft(
    task_id: UUID,
    request: TaskDraftRequest,
    actor: AuthenticatedActor = Depends(require_active_participant_actor),
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
    user_id = actor.resolve_user_id(request.user_id)
    verified_request = request.model_copy(update={"user_id": user_id})
    return service.save_draft(str(task_id), verified_request)


@router.post(
    "/{task_id}/submit",
    response_model=TaskSubmissionAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_task(
    task_id: UUID,
    payload: TaskSubmitRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    actor: AuthenticatedActor = Depends(require_active_participant_actor),
    service: TaskService = Depends(get_task_service),
) -> TaskSubmissionAcceptedResponse:
    """Queue task judgement and return a persistent polling id immediately.

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
    user_id = actor.resolve_user_id(payload.user_id)
    verified_payload = payload.model_copy(update={"user_id": user_id})
    accepted, _ = service.queue_submission(str(task_id), verified_payload)
    if accepted.status == "processing":
        _schedule_processing(http_request, background_tasks, service, accepted.attempt_id)
    return accepted


@router.get("/attempts/{attempt_id}", response_model=TaskSubmissionStatusResponse)
def task_submission_status(
    attempt_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    actor: AuthenticatedActor = Depends(require_active_participant_actor),
    service: TaskService = Depends(get_task_service),
) -> TaskSubmissionStatusResponse:
    """Return queued task processing state and the final navigation payload."""
    response = service.submission_status(str(attempt_id))
    owner_user_id = response.attempt.user_id
    if not owner_user_id and response.attempt.session_id:
        session = service.repository.get_session(response.attempt.session_id)
        owner_user_id = session.user_id if session else None
    actor.require_owner(owner_user_id)
    if response.attempt.status == "processing":
        _schedule_processing(request, background_tasks, service, str(attempt_id))
    return response
