"""Admin API endpoints.

本模組提供系統管理後台 API，使用 x-admin-key 做簡單保護。
可管理 task、persona、condition 設定，並查看 research_logs。
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_repository, require_admin_key
from app.crud.protocols import RepositoryProtocol
from app.models.domain import Event, EventTask, ExperimentCondition, Persona, ResearchLog
from app.schemas.requests import (
    EventUpdateRequest,
    EventTaskUpdateRequest,
    ExperimentConditionUpdateRequest,
    PersonaUpdateRequest,
)
from app.schemas.responses import AdminSnapshotResponse, EventListItem

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_key)],
)


@router.get("/snapshot", response_model=AdminSnapshotResponse)
def admin_snapshot(repository: RepositoryProtocol = Depends(get_repository)) -> AdminSnapshotResponse:
    """一次載入 admin UI 需要的事件、條件、session 與研究紀錄摘要。"""
    events: list[EventListItem] = []
    for event in repository.list_events():
        payload = event.model_dump()
        payload["personas"] = repository.list_personas(event.id, active_only=False)
        payload["latest_task"] = repository.get_latest_event_task(event.id)
        events.append(EventListItem(**payload))
    return AdminSnapshotResponse(
        events=events,
        conditions=repository.list_conditions(active_only=False),
        sessions=repository.list_sessions(),
        research_logs=repository.list_research_logs(),
    )


@router.patch("/events/{event_id}", response_model=Event)
def update_event(
    event_id: str,
    request: EventUpdateRequest,
    repository: RepositoryProtocol = Depends(get_repository),
) -> Event:
    """更新歷史事件基本資料；正式資料來源仍是 repository/Supabase。"""
    event = repository.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    updates = request.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(event, key, value)
    saved = repository.save_event(event)
    repository.log_research(
        ResearchLog(
            event_id=saved.id,
            action_type="event_updated",
            payload={"updated_fields": sorted(updates.keys())},
        )
    )
    return saved


@router.patch("/tasks/{task_id}", response_model=EventTask)
def update_task(
    task_id: str,
    request: EventTaskUpdateRequest,
    repository: RepositoryProtocol = Depends(get_repository),
) -> EventTask:
    """更新 task 文字與 evaluation_payload。"""
    task = repository.get_event_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    updates = request.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(task, key, value)
    return repository.save_event_task(task)


@router.patch("/personas/{persona_id}", response_model=Persona)
def update_admin_persona(
    persona_id: str,
    request: PersonaUpdateRequest,
    repository: RepositoryProtocol = Depends(get_repository),
) -> Persona:
    """更新 persona 基本資料與 prompt_profile。"""
    persona = repository.get_persona(persona_id)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    updates = request.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(persona, key, value)
    return repository.save_persona(persona)


@router.patch("/conditions/{condition_id}", response_model=ExperimentCondition)
def update_condition(
    condition_id: str,
    request: ExperimentConditionUpdateRequest,
    repository: RepositoryProtocol = Depends(get_repository),
) -> ExperimentCondition:
    """更新 2x2 實驗條件設定，例如 EBL/role-play 是否啟用。"""
    condition = repository.get_condition(condition_id)
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")
    updates = request.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(condition, key, value)
    return repository.save_condition(condition)


@router.get("/research-logs", response_model=list[ResearchLog])
def list_research_logs(
    limit: int = 200,
    repository: RepositoryProtocol = Depends(get_repository),
) -> list[ResearchLog]:
    """列出流程行為紀錄；對話內容分析仍以 messages 為主。"""
    return repository.list_research_logs(limit=limit)
