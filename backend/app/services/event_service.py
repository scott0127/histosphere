from fastapi import HTTPException, status

from app.models.domain import Event
from app.schemas.responses import EventListItem
from app.crud.protocols import RepositoryProtocol


class EventService:
    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def check_exists(self, event_name: str) -> bool:
        return self.repository.find_event_by_name(event_name) is not None

    def list_events(self) -> list[EventListItem]:
        items: list[EventListItem] = []
        for event in self.repository.list_events():
            payload = event.model_dump()
            payload["personas"] = self.repository.list_personas(event.id)
            payload["latest_task"] = self.repository.get_latest_event_task(event.id)
            items.append(EventListItem(**payload))
        return items

    def delete_event(self, event_id: str) -> dict[str, bool]:
        deleted = self.repository.delete_event(event_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        return {"success": True}

    def regenerate_background(self, event_id: str) -> dict[str, str | None]:
        event = self.repository.get_event(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        return {"background_url": None}

    @staticmethod
    def build_event_from_profile(event_name: str, profile: dict) -> Event:
        return Event(
            canonical_name=profile.get("canonical_name") or event_name.strip(),
            description=profile.get("description"),
            century=profile.get("century"),
            start_year=profile.get("start_year"),
            end_year=profile.get("end_year"),
            context=profile.get("context"),
            source_summary=profile.get("source_summary") or {},
        )
