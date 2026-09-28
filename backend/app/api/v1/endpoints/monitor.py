"""Private monitoring and per-question review; no learner route exposes this data."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.api.deps import get_repository, get_task_service, require_admin_key
from app.api.state_events import state_event_response
from app.api.task_processing import PROCESSING_STAGES, schedule_task_processing
from app.crud.protocols import RepositoryProtocol
from app.models.domain import TaskAttempt
from app.schemas.responses import TaskSubmissionAcceptedResponse
from app.schemas.task_review import TaskReviewApproveRequest, TaskReviewDraftRequest
from app.services import TaskService
from app.services.session_monitor import SessionMonitorService
from app.services.task_review_service import TaskReviewService

router = APIRouter(prefix="/api/admin/monitor", tags=["admin-monitor"], dependencies=[Depends(require_admin_key)])


@router.get("/sessions/{session_id}")
def monitor_session(session_id: UUID, request: Request, background_tasks: BackgroundTasks,
                    repository: RepositoryProtocol = Depends(get_repository),
                    service: TaskService = Depends(get_task_service)) -> dict:
    snapshot = SessionMonitorService(repository).snapshot(str(session_id))
    attempt = snapshot["attempt"]
    if attempt and attempt.status in PROCESSING_STAGES:
        schedule_task_processing(request, service, attempt.id, background_tasks)
    return snapshot


@router.get("/sessions/{session_id}/events")
async def monitor_events(session_id: UUID, request: Request,
                         repository: RepositoryProtocol = Depends(get_repository),
                         service: TaskService = Depends(get_task_service)):
    monitor = SessionMonitorService(repository)
    snapshot = monitor.snapshot(str(session_id))
    attempt = snapshot["attempt"]
    if attempt and attempt.status in PROCESSING_STAGES:
        schedule_task_processing(request, service, attempt.id)
    return state_event_response(request, lambda: monitor.change_token(str(session_id)))


@router.patch("/attempts/{attempt_id}/review", response_model=TaskAttempt)
def save_review(attempt_id: UUID, payload: TaskReviewDraftRequest,
                repository: RepositoryProtocol = Depends(get_repository)) -> TaskAttempt:
    return TaskReviewService(repository).save_draft(str(attempt_id), payload)


@router.post("/attempts/{attempt_id}/approve", response_model=TaskAttempt)
def approve_review(attempt_id: UUID, payload: TaskReviewApproveRequest, request: Request,
                   background_tasks: BackgroundTasks, repository: RepositoryProtocol = Depends(get_repository),
                   service: TaskService = Depends(get_task_service)) -> TaskAttempt:
    attempt = TaskReviewService(repository).approve(str(attempt_id), payload.expected_version)
    if attempt.status in PROCESSING_STAGES:
        schedule_task_processing(request, service, attempt.id, background_tasks)
    return attempt


@router.post("/attempts/{attempt_id}/retry", response_model=TaskSubmissionAcceptedResponse)
def retry_processing(attempt_id: UUID, request: Request, background_tasks: BackgroundTasks,
                     service: TaskService = Depends(get_task_service)) -> TaskSubmissionAcceptedResponse:
    accepted = service.retry_submission(str(attempt_id))
    if accepted.status in PROCESSING_STAGES:
        schedule_task_processing(request, service, accepted.attempt_id, background_tasks)
    return accepted
