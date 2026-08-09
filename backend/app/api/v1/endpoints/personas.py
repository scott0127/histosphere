"""Persona API endpoints.

本模組提供 historical persona 的讀寫 API。
persona 會影響 role-play 條件下的 speaker 與 prompt_profile。

Routes:
    GET    /api/personas?event_id=:         列出指定事件的 personas。
    POST   /api/personas:                   新增 persona。
    PATCH  /api/personas/{persona_id}:      更新 persona。
    DELETE /api/personas/{persona_id}:      刪除 persona。
    POST   /api/personas/{persona_id}/restore: 恢復已封存 persona。
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_persona_service, require_admin_key
from app.models.domain import Persona
from app.schemas.requests import PersonaCreateRequest, PersonaUpdateRequest
from app.services import PersonaService

router = APIRouter(prefix="/api/personas", tags=["personas"])


@router.get("", response_model=list[Persona])
def list_personas(
    event_id: str = Query(...),
    service: PersonaService = Depends(get_persona_service),
) -> list[Persona]:
    """列出指定事件可用的 personas。

    回傳該事件下所有 active 的歷史人物角色。前端聊天頁
    與 admin 管理頁皆透過此端點取得角色清單。

    Args:
        event_id: 目標事件的 UUID 字串（必填 query parameter）。
        service: 由 Dependency Injection 注入的 PersonaService 實例。

    Returns:
        list[Persona]: 該事件下的 active persona 清單。
    """
    return service.list_personas(event_id)


@router.post("", response_model=Persona)
def create_persona(
    request: PersonaCreateRequest,
    _admin: None = Depends(require_admin_key),
    service: PersonaService = Depends(get_persona_service),
) -> Persona:
    """新增 persona，可手動調整事件角色。

    支援 admin 或研究者手動新增歷史人物。必填 event_id 與 name，
    其餘 biography、expertise_areas、prompt_profile 等可選填。

    Args:
        request: 建立請求，包含 event_id、name 等 persona 欄位。
        service: 由 Dependency Injection 注入的 PersonaService 實例。

    Returns:
        Persona: 成功建立的 persona 完整資料。
    """
    return service.create_persona(request)


@router.patch("/{persona_id}", response_model=Persona)
def update_persona(
    persona_id: str,
    request: PersonaUpdateRequest,
    _admin: None = Depends(require_admin_key),
    service: PersonaService = Depends(get_persona_service),
) -> Persona:
    """更新 persona profile 或 prompt_profile。

    支援部分更新（PATCH 語意）。可修改角色名稱、biography、
    expertise_areas、prompt_profile 等欄位，未提供的欄位保持不變。

    Args:
        persona_id: 目標 persona 的 UUID 字串。
        request: 部分更新請求，僅含需修改的欄位。
        service: 由 Dependency Injection 注入的 PersonaService 實例。

    Returns:
        Persona: 更新後的 persona 完整資料。
    """
    return service.update_persona(persona_id, request)


@router.delete("/{persona_id}")
def delete_persona(
    persona_id: str,
    _admin: None = Depends(require_admin_key),
    service: PersonaService = Depends(get_persona_service),
) -> dict[str, bool]:
    """封存 persona，保留既有對話與研究資料關聯。

    此操作會將人物設為停用並寫入封存時間，不會永久刪除資料。

    Args:
        persona_id: 要刪除的 persona UUID 字串。
        service: 由 Dependency Injection 注入的 PersonaService 實例。

    Returns:
        dict[str, bool]: ``{"success": True/False}``。
    """
    return service.delete_persona(persona_id)


@router.post("/{persona_id}/restore", response_model=Persona)
def restore_persona(
    persona_id: str,
    _admin: None = Depends(require_admin_key),
    service: PersonaService = Depends(get_persona_service),
) -> Persona:
    """恢復已封存人物，但不直接啟用，避免意外取代正式人物。"""
    return service.restore_persona(persona_id)
