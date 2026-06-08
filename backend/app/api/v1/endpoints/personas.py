from fastapi import APIRouter, Depends, Query

from app.api.deps import get_persona_service
from app.models.domain import Persona
from app.schemas.requests import PersonaCreateRequest, PersonaUpdateRequest
from app.services import PersonaService

router = APIRouter(prefix="/api/personas", tags=["personas"])


@router.get("", response_model=list[Persona])
def list_personas(
    event_id: str = Query(...),
    service: PersonaService = Depends(get_persona_service),
) -> list[Persona]:
    return service.list_personas(event_id)


@router.post("", response_model=Persona)
def create_persona(
    request: PersonaCreateRequest,
    service: PersonaService = Depends(get_persona_service),
) -> Persona:
    return service.create_persona(request)


@router.patch("/{persona_id}", response_model=Persona)
def update_persona(
    persona_id: str,
    request: PersonaUpdateRequest,
    service: PersonaService = Depends(get_persona_service),
) -> Persona:
    return service.update_persona(persona_id, request)


@router.delete("/{persona_id}")
def delete_persona(
    persona_id: str,
    service: PersonaService = Depends(get_persona_service),
) -> dict[str, bool]:
    return service.delete_persona(persona_id)


@router.post("/{persona_id}/regenerate_avatar")
def regenerate_avatar(
    persona_id: str,
    service: PersonaService = Depends(get_persona_service),
) -> dict[str, str | bool | None]:
    return service.regenerate_avatar(persona_id)

