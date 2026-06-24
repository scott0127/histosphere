"""Persona management service.

本模組負責歷史人物 persona 的 CRUD。包含 persona 可由 LLM 生成，
也可在管理後台中修改 biography、role 與 prompt_profile。
"""

from fastapi import HTTPException, status

from app.models.domain import Persona
from app.schemas.requests import PersonaCreateRequest, PersonaUpdateRequest
from app.crud.protocols import RepositoryProtocol


class PersonaService:
    """管理單一事件底下的 historical personas。"""

    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def list_personas(self, event_id: str) -> list[Persona]:
        """列出指定事件的 active personas。"""
        event = self.repository.get_event(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        return self.repository.list_personas(event_id)

    def create_persona(self, request: PersonaCreateRequest) -> Persona:
        """手動新增 persona，通常由 admin/teacher 操作。"""
        event = self.repository.get_event(request.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        persona = Persona(**request.model_dump())
        return self.repository.save_persona(persona)

    def update_persona(self, persona_id: str, request: PersonaUpdateRequest) -> Persona:
        """更新 persona；prompt_profile 也在此保存，供 prompt assembly 使用。"""
        persona = self.repository.get_persona(persona_id)
        if not persona:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
        updates = request.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(persona, key, value)
        return self.repository.save_persona(persona)

    def delete_persona(self, persona_id: str) -> dict[str, bool]:
        """刪除 persona；若只是暫停使用，後續可改用 active=false。"""
        deleted = self.repository.delete_persona(persona_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
        return {"success": True}

    def regenerate_avatar(self, persona_id: str) -> dict[str, str | bool | None]:
        """保留 avatar 擴充點；影片與 persona card 已棄用。"""
        persona = self.repository.get_persona(persona_id)
        if not persona:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
        return {"success": True, "avatar_url": persona.avatar_url}
