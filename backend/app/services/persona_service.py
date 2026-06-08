from fastapi import HTTPException, status

from app.models.domain import Persona
from app.schemas.requests import PersonaCreateRequest, PersonaUpdateRequest
from app.crud.protocols import RepositoryProtocol


class PersonaService:
    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def list_personas(self, event_id: str) -> list[Persona]:
        event = self.repository.get_event(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        return self.repository.list_personas(event_id)

    def create_persona(self, request: PersonaCreateRequest) -> Persona:
        event = self.repository.get_event(request.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        persona = Persona(**request.model_dump())
        return self.repository.save_persona(persona)

    def update_persona(self, persona_id: str, request: PersonaUpdateRequest) -> Persona:
        persona = self.repository.get_persona(persona_id)
        if not persona:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
        updates = request.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(persona, key, value)
        return self.repository.save_persona(persona)

    def delete_persona(self, persona_id: str) -> dict[str, bool]:
        deleted = self.repository.delete_persona(persona_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
        return {"success": True}

    def regenerate_avatar(self, persona_id: str) -> dict[str, str | bool | None]:
        persona = self.repository.get_persona(persona_id)
        if not persona:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
        return {"success": True, "avatar_url": persona.avatar_url}

