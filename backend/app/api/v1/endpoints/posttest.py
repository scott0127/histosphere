"""Authenticated session-linked posttest endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_repository, require_active_participant_actor, require_session_actor
from app.core.auth import AuthenticatedActor
from app.crud.protocols import RepositoryProtocol
from app.schemas.posttest import PosttestDraftRequest, PosttestRevisionRequest, PosttestStateResponse
from app.services.posttest_service import PosttestService


router = APIRouter(prefix="/api/sessions", tags=["posttest"])


def posttest_service(
    session_id: UUID,
    actor: AuthenticatedActor = Depends(require_active_participant_actor),
    repository: RepositoryProtocol = Depends(get_repository),
) -> PosttestService:
    require_session_actor(actor, repository, repository.get_session(str(session_id)))
    return PosttestService(repository)


@router.get("/{session_id}/posttest", response_model=PosttestStateResponse)
def load_posttest(session_id: UUID, service: PosttestService = Depends(posttest_service)) -> PosttestStateResponse:
    return service.load(str(session_id))


@router.post("/{session_id}/posttest/start", response_model=PosttestStateResponse)
def start_posttest(session_id: UUID, service: PosttestService = Depends(posttest_service)) -> PosttestStateResponse:
    return service.start(str(session_id))


@router.patch("/{session_id}/posttest", response_model=PosttestStateResponse)
def save_posttest(session_id: UUID, request: PosttestDraftRequest, service: PosttestService = Depends(posttest_service)) -> PosttestStateResponse:
    return service.save_draft(str(session_id), request)


@router.post("/{session_id}/posttest/advance", response_model=PosttestStateResponse)
def advance_posttest(session_id: UUID, request: PosttestRevisionRequest, service: PosttestService = Depends(posttest_service)) -> PosttestStateResponse:
    return service.advance(str(session_id), request.revision)


@router.post("/{session_id}/posttest/submit", response_model=PosttestStateResponse)
def submit_posttest(session_id: UUID, request: PosttestRevisionRequest, service: PosttestService = Depends(posttest_service)) -> PosttestStateResponse:
    return service.submit(str(session_id), request.revision)
