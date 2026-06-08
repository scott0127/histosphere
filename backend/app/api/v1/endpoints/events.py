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
    return {"exists": service.check_exists(request.event_name)}


@router.post("/event/initialize", response_model=EventInitializeResponse)
async def initialize_event(
    request: EventInitializeRequest,
    service: EventInitializationService = Depends(get_event_initialization_service),
) -> EventInitializeResponse:
    return await service.initialize(request)


@router.get("/events", response_model=list[EventListItem])
def list_events(service: EventService = Depends(get_event_service)) -> list[EventListItem]:
    return service.list_events()


@router.delete("/event/{event_id}")
def delete_event(
    event_id: str,
    service: EventService = Depends(get_event_service),
) -> dict[str, bool]:
    return service.delete_event(event_id)


@router.post("/event/{event_id}/regenerate-background")
def regenerate_background(
    event_id: str,
    service: EventService = Depends(get_event_service),
) -> dict[str, str | None]:
    return service.regenerate_background(event_id)

