"""Experiment session progress API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_session_service
from app.schemas.responses import SessionStateResponse, UserProgressResponse
from app.services import SessionService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("/progress", response_model=UserProgressResponse)
def user_progress(
    user_id: str,
    service: SessionService = Depends(get_session_service),
) -> UserProgressResponse:
    """列出受測者在各事件與 condition 的進度摘要。"""
    return service.user_progress(user_id)


@router.get("/{session_id}/state", response_model=SessionStateResponse)
def session_state(
    session_id: UUID,
    service: SessionService = Depends(get_session_service),
) -> SessionStateResponse:
    """載入單一實驗 session 的可恢復狀態。"""
    return service.load_state(str(session_id))
