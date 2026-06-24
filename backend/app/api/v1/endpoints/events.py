"""Event API endpoints.

本模組提供歷史事件查詢、初始化、列表與刪除入口。
V1 的核心入口是 /event/initialize：建立 event workspace、
產生 task、產生 personas，並建立 experiment session。
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_event_initialization_service, get_event_service
from app.schemas.requests import EventCheckRequest, EventInitializeRequest
from app.schemas.responses import EventInitializeResponse, EventListItem
from app.services import EventInitializationService, EventService

router = APIRouter(prefix="/api", tags=["events"])


@router.post("/event/check")
def check_event(
    request: EventCheckRequest,
    service: EventService = Depends(get_event_service),
) -> dict[str, bool]:
    """檢查事件名稱是否已經存在，供前端提示 rebuild 或 reuse。"""
    return {"exists": service.check_exists(request.event_name)}


@router.post("/event/initialize", response_model=EventInitializeResponse)
async def initialize_event(
    request: EventInitializeRequest,
    service: EventInitializationService = Depends(get_event_initialization_service),
) -> EventInitializeResponse:
    """建立事件學習工作區，但不直接建立 conversation。"""
    return await service.initialize(request)


@router.get("/events", response_model=list[EventListItem])
def list_events(service: EventService = Depends(get_event_service)) -> list[EventListItem]:
    """列出目前可重用的歷史事件與最新 task/persona 摘要。"""
    return service.list_events()


@router.delete("/event/{event_id}")
def delete_event(
    event_id: str,
    service: EventService = Depends(get_event_service),
) -> dict[str, bool]:
    """刪除指定事件；資料庫 cascade 會一併清除其 task/persona/conversation。"""
    return service.delete_event(event_id)


@router.post("/event/{event_id}/regenerate-background")
def regenerate_background(
    event_id: str,
    service: EventService = Depends(get_event_service),
) -> dict[str, str | None]:
    """相容舊前端的背景更新 endpoint；新版 UI 目前不依賴圖片背景。"""
    return service.regenerate_background(event_id)
