"""Persona API endpoints.

本模組提供 historical persona 的讀寫 API。
persona 會影響 role-play 條件下的 speaker 與 prompt_profile。
"""

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
    """列出指定事件可用的 personas。"""
    return service.list_personas(event_id)


@router.post("", response_model=Persona)
def create_persona(
    request: PersonaCreateRequest,
    service: PersonaService = Depends(get_persona_service),
) -> Persona:
    """新增 persona，可手動調整事件角色。"""
    return service.create_persona(request)


@router.patch("/{persona_id}", response_model=Persona)
def update_persona(
    persona_id: str,
    request: PersonaUpdateRequest,
    service: PersonaService = Depends(get_persona_service),
) -> Persona:
    """更新 persona profile 或 prompt_profile。"""
    return service.update_persona(persona_id, request)


@router.delete("/{persona_id}")
def delete_persona(
    persona_id: str,
    service: PersonaService = Depends(get_persona_service),
) -> dict[str, bool]:
    """刪除 persona；研究資料固定後需謹慎使用。"""
    return service.delete_persona(persona_id)


@router.post("/{persona_id}/regenerate_avatar")
def regenerate_avatar(
    persona_id: str,
    service: PersonaService = Depends(get_persona_service),
) -> dict[str, str | bool | None]:
    """保留 avatar 擴充入口；V1 不重新生成影片或 persona card。"""
    return service.regenerate_avatar(persona_id)
