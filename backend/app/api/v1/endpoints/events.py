"""Event API endpoints.

本模組提供歷史事件查詢、初始化與公開列表入口。
V1 的核心入口是 /event/initialize：建立 event workspace、
產生 task、產生 personas，並建立 experiment session。

Routes:
    POST   /api/event/check:                     檢查事件名稱是否已存在。
    POST   /api/event/initialize:                初始化事件學習工作區。
    GET    /api/events:                          列出所有歷史事件摘要。
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_event_initialization_service, get_event_service, require_active_participant_actor
from app.core.auth import AuthenticatedActor
from app.core.learner_task_view import learner_view
from app.schemas.requests import EventCheckRequest, EventInitializeRequest
from app.schemas.responses import EventInitializeResponse, EventListItem
from app.services import EventInitializationService, EventService

router = APIRouter(prefix="/api", tags=["events"])


@router.post("/event/check")
def check_event(
    request: EventCheckRequest,
    service: EventService = Depends(get_event_service),
) -> dict[str, bool]:
    """檢查事件名稱是否已經存在，供前端提示 rebuild 或 reuse。

    前端在 learner 輸入事件名稱後呼叫此端點，依回傳結果
    決定顯示「重新建立」或「繼續使用」選項。

    Args:
        request: 包含 event_name（至少 1 字元）的檢查請求。
        service: 由 Dependency Injection 注入的 EventService 實例。

    Returns:
        dict[str, bool]: ``{"exists": True/False}``。
    """
    return {"exists": service.check_exists(request.event_name)}


@router.post("/event/initialize", response_model=EventInitializeResponse)
async def initialize_event(
    request: EventInitializeRequest,
    actor: AuthenticatedActor = Depends(require_active_participant_actor),
    service: EventInitializationService = Depends(get_event_initialization_service),
) -> EventInitializeResponse:
    """建立事件學習工作區，但不直接建立 conversation。

    完整流程：透過 LLM 研究事件背景 → 建立/重用 Event 紀錄 →
    產生 EventTask → 產生 Personas → 建立 ExperimentSession。
    回傳初始化結果供前端進入 task 作答頁。

    Args:
        request: 初始化請求，包含 event_name、condition_key、
            rebuild 旗標與可選 user_id。
        service: 由 Dependency Injection 注入的 EventInitializationService 實例。

    Returns:
        EventInitializeResponse: 包含 event_id、session_id、
            event、task、personas 與 condition。
    """
    user_id = request.user_id if actor.is_admin else actor.resolve_user_id()
    verified_request = request.model_copy(update={"user_id": user_id})
    return learner_view(await service.initialize(verified_request, admin_override=actor.is_admin))


@router.get("/events", response_model=list[EventListItem])
def list_events(service: EventService = Depends(get_event_service)) -> list[EventListItem]:
    """列出目前可重用的歷史事件與最新 task/persona 摘要。

    前端事件選擇頁使用，回傳所有 event 並附帶其 personas
    與最新 task 資訊，方便 learner 快速選擇已存在的事件。

    Args:
        service: 由 Dependency Injection 注入的 EventService 實例。

    Returns:
        list[EventListItem]: 含 personas 與 latest_task 的事件清單。
    """
    return learner_view(service.list_events())
