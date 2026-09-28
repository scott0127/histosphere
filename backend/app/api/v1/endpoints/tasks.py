"""Task submission API endpoint.

本模組負責接收 learner 的 task 作答，並交給 TaskService 完成
LLM 判斷、task_attempts 儲存，以及 conversation 解鎖。

Routes:
    PATCH /api/tasks/{task_id}/draft:   保存 task 草稿。
    POST  /api/tasks/{task_id}/submit:  送出 task 作答。
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from app.api.deps import get_task_service, require_active_participant_actor, require_session_actor
from app.core.auth import AuthenticatedActor
from app.core.learner_task_view import learner_view
from app.api.state_events import state_event_response
from app.api.task_processing import PROCESSING_STAGES, schedule_task_processing
from app.schemas.requests import TaskDraftRequest, TaskSubmitRequest
from app.schemas.responses import (
    TaskDraftResponse,
    TaskSubmissionAcceptedResponse,
    TaskSubmissionStatusResponse,
    TaskSubmitResponse,
)
from app.services import TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _owned_attempt(service: TaskService, actor: AuthenticatedActor, attempt_id: str):
    response = service.submission_status(attempt_id)
    session = service.repository.get_session(response.attempt.session_id)
    actor.require_owner(response.attempt.user_id or (session.user_id if session else None))
    require_session_actor(actor, service.repository, session)
    return response


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
    require_session_actor(actor, service.repository, service.repository.get_session(request.session_id))
    verified_request = request.model_copy(update={"user_id": user_id})
    return learner_view(service.save_draft(str(task_id), verified_request))


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
    """Persist submission, queue initial judgement, then wait for human review."""
    user_id = actor.resolve_user_id(payload.user_id)
    require_session_actor(actor, service.repository, service.repository.get_session(payload.session_id))
    verified_payload = payload.model_copy(update={"user_id": user_id})
    accepted, _ = service.queue_submission(str(task_id), verified_payload)
    if accepted.status in PROCESSING_STAGES:
        schedule_task_processing(http_request, service, accepted.attempt_id, background_tasks)
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
    response = _owned_attempt(service, actor, str(attempt_id))
    if response.attempt.status in PROCESSING_STAGES:
        schedule_task_processing(request, service, str(attempt_id), background_tasks)
    return learner_view(response)


@router.get("/attempts/{attempt_id}/events")
async def task_submission_events(attempt_id: UUID, request: Request,
                                 actor: AuthenticatedActor = Depends(require_active_participant_actor),
                                 service: TaskService = Depends(get_task_service)):
    response = _owned_attempt(service, actor, str(attempt_id))
    if response.attempt.status in PROCESSING_STAGES:
        schedule_task_processing(request, service, str(attempt_id))

    def change_token() -> dict:
        # No initial verdict, admin draft, feedback or private change history.
        attempt = service.repository.get_task_attempt(str(attempt_id))
        return {"attempt_id": str(attempt_id), "stage": attempt.status if attempt else "missing",
                "version": attempt.updated_at.isoformat() if attempt else ""}

    return state_event_response(request, change_token)


@router.post("/attempts/{attempt_id}/enter", response_model=TaskSubmitResponse)
def enter_interaction(attempt_id: UUID,
                      actor: AuthenticatedActor = Depends(require_active_participant_actor),
                      service: TaskService = Depends(get_task_service)) -> TaskSubmitResponse:
    """Enter only an approved, prepared interaction; starts the timer exactly once."""
    _owned_attempt(service, actor, str(attempt_id))
    return learner_view(service.enter_interaction(str(attempt_id)))
