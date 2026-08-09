"""Persona management service.

本模組負責歷史人物 persona 的 CRUD。包含 persona 可由 LLM 生成，
也可在管理後台中修改 biography、role 與 prompt_profile。
"""

from fastapi import HTTPException, status

from app.core.research_audit import build_change_payload
from app.models.domain import Persona, ResearchLog
from app.schemas.requests import PersonaCreateRequest, PersonaUpdateRequest
from app.crud.protocols import RepositoryProtocol
from app.services.material_lock_service import assert_event_materials_editable


class PersonaService:
    """管理單一事件底下的 historical personas。"""

    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def list_personas(self, event_id: str) -> list[Persona]:
        """列出指定事件的 active personas。"""
        event = self.repository.get_event(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        return [
            persona
            for persona in self.repository.list_personas(event_id)
            if persona.archived_at is None
        ]

    def create_persona(self, request: PersonaCreateRequest) -> Persona:
        """手動新增 persona，通常由 admin/teacher 操作。"""
        event = self.repository.get_event(request.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        assert_event_materials_editable(self.repository, request.event_id)
        if request.active:
            self._assert_can_activate(request.event_id)
        persona = Persona(**request.model_dump())
        saved = self.repository.save_persona(persona)
        self.repository.log_research(
            ResearchLog(
                event_id=saved.event_id,
                action_type="persona_created",
                payload=build_change_payload(
                    before=None,
                    after=saved,
                    fields=[
                        "name",
                        "role",
                        "biography",
                        "avatar_url",
                        "prompt_profile",
                        "active",
                        "revision_state",
                    ],
                    subject={
                        "persona_id": saved.id,
                        "persona_name": saved.name,
                        "event_id": saved.event_id,
                    },
                ),
            )
        )
        return saved

    def update_persona(self, persona_id: str, request: PersonaUpdateRequest) -> Persona:
        """更新 persona；prompt_profile 也在此保存，供 prompt assembly 使用。"""
        persona = self.repository.get_persona(persona_id)
        if not persona:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
        assert_event_materials_editable(self.repository, persona.event_id)
        before = persona.model_copy(deep=True)
        updates = request.model_dump(exclude_unset=True)
        if updates.get("active") is True:
            self._assert_can_activate(persona.event_id, persona_id=persona.id)
            # 啟用封存人物等同恢復並啟用，避免 active 與 archived_at 互相矛盾。
            persona.archived_at = None
        for key, value in updates.items():
            setattr(persona, key, value)
        saved = self.repository.save_persona(persona)
        self.repository.log_research(
            ResearchLog(
                event_id=saved.event_id,
                action_type="persona_updated",
                payload=build_change_payload(
                    before=before,
                    after=saved,
                    fields=set(updates.keys()) | ({"archived_at"} if updates.get("active") is True else set()),
                    subject={
                        "persona_id": saved.id,
                        "persona_name": saved.name,
                        "event_id": saved.event_id,
                    },
                ),
            )
        )
        return saved

    def delete_persona(self, persona_id: str) -> dict[str, bool]:
        """可恢復封存 persona，保留既有 conversation 與研究資料關聯。"""
        persona = self.repository.get_persona(persona_id)
        if not persona:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
        assert_event_materials_editable(self.repository, persona.event_id)
        before = persona.model_copy(deep=True)
        deleted = self.repository.delete_persona(persona_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
        saved = self.repository.get_persona(persona_id)
        self.repository.log_research(
            ResearchLog(
                event_id=before.event_id,
                action_type="persona_archived",
                payload=build_change_payload(
                    before=before,
                    after=saved,
                    fields=["active", "archived_at"],
                    subject={
                        "persona_id": before.id,
                        "persona_name": before.name,
                        "event_id": before.event_id,
                    },
                ),
            )
        )
        return {"success": True}

    def restore_persona(self, persona_id: str) -> Persona:
        """將已封存人物恢復為停用狀態，由管理員再決定是否啟用。"""
        persona = self.repository.get_persona(persona_id)
        if not persona:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
        assert_event_materials_editable(self.repository, persona.event_id)
        before = persona.model_copy(deep=True)
        persona.archived_at = None
        persona.active = False
        saved = self.repository.save_persona(persona)
        self.repository.log_research(
            ResearchLog(
                event_id=saved.event_id,
                action_type="persona_restored",
                payload=build_change_payload(
                    before=before,
                    after=saved,
                    fields=["active", "archived_at"],
                    subject={
                        "persona_id": saved.id,
                        "persona_name": saved.name,
                        "event_id": saved.event_id,
                    },
                ),
            )
        )
        return saved

    def _assert_can_activate(self, event_id: str, persona_id: str | None = None) -> None:
        """確保同一事件同時只有一位可供受測者使用的 active persona。"""
        conflict = next(
            (
                persona
                for persona in self.repository.list_personas(event_id, active_only=False)
                if persona.active
                and persona.archived_at is None
                and persona.id != persona_id
            ),
            None,
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Event already has an active persona: {conflict.name}",
            )
