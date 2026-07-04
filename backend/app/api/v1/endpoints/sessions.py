"""Experiment session progress API endpoints.

本模組提供實驗 session 狀態查詢，供前端恢復中斷的實驗流程
與顯示受測者跨事件的完成進度。

Routes:
    GET /api/sessions/progress?user_id=:   列出受測者的跨事件進度摘要。
    GET /api/sessions/{session_id}/state:   載入單一 session 可恢復狀態。
"""

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
    """列出受測者在各事件與 condition 的進度摘要。

    前端進度頁呼叫此端點，顯示該 user 已參與的所有實驗
    session 狀態（包含 task 完成情況、conversation 是否已開啟等）。

    Args:
        user_id: 受測者的識別字串。
        service: 由 Dependency Injection 注入的 SessionService 實例。

    Returns:
        UserProgressResponse: 包含 progress 清單，每筆紀錄
            含 event_id、condition_key、session_id、status 等。
    """
    return service.user_progress(user_id)


@router.get("/{session_id}/state", response_model=SessionStateResponse)
def session_state(
    session_id: UUID,
    service: SessionService = Depends(get_session_service),
) -> SessionStateResponse:
    """載入單一實驗 session 的可恢復狀態。

    前端在 learner 重新進入時呼叫，取得 session 當前階段
    （event、task、condition、attempt、conversation_id），
    以便從中斷處繼續實驗流程。

    Args:
        session_id: 目標 session 的 UUID。
        service: 由 Dependency Injection 注入的 SessionService 實例。

    Returns:
        SessionStateResponse: 包含 session、event、task、
            personas、condition、attempt 與 conversation_id。
    """
    return service.load_state(str(session_id))
