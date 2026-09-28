"""Admin API endpoints.

本模組提供系統管理後台 API，使用 x-admin-key 做簡單保護。
可管理 task、persona、condition 設定，並查看 research_logs。

Routes:
    GET   /api/admin/snapshot:                一次載入 admin UI 全部所需資料。
    GET   /api/admin/auth-users:              列出可綁定 participant 的 Supabase Auth users。
    GET   /api/admin/prompt-preview:          預覽聊天 prompt 組裝結果。
    PATCH /api/admin/events/{event_id}:       更新歷史事件基本資料。
    PATCH /api/admin/tasks/{task_id}:         更新 task 文字與評量結構。
    PATCH /api/admin/personas/{persona_id}:   更新 persona 資料。
    PATCH /api/admin/participants/{participant_id}: 更新 participant registry。
    PATCH /api/admin/conditions/{condition_id}: 更新實驗條件設定。
    GET   /api/admin/research-logs:           列出流程行為紀錄。
"""

import os
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import ValidationError

from app.api.deps import (
    get_chat_service,
    get_persona_service,
    get_prompt_service,
    get_rag_pipeline,
    get_repository,
    get_session_service,
    require_admin_key,
)
from app.core.config import get_settings
from app.core.experiment_conditions import normalize_condition_sequence
from app.core.interaction_contract import build_interaction_runtime
from app.core.research_audit import build_change_payload
from app.crud.protocols import RepositoryProtocol
from app.models.domain import Event, EventTask, ExperimentCondition, ExperimentSession, Participant, Persona, ResearchLog
from app.schemas.requests import (
    AdminPromptDryRunRequest,
    EventUpdateRequest,
    MaterialLockRequest,
    EventTaskUpdateRequest,
    ExperimentConditionUpdateRequest,
    ParticipantCreateRequest,
    ParticipantUpdateRequest,
    PersonaUpdateRequest,
    SessionTimerResetRequest,
)
from app.schemas.responses import (
    AdminAuthUserSummary,
    AdminLLMUsageResponse,
    AdminAuthUsersResponse,
    AdminParticipantPreviewResponse,
    AdminPromptDryRunResponse,
    AdminPromptPreviewResponse,
    AdminSessionResearchResponse,
    AdminSnapshotResponse,
    EventListItem,
    PromptPreviewModule,
    SessionRestartResponse,
)
from app.services import ChatService, PersonaService, PromptService, RagPipelineService, SessionService
from app.services.research_export_service import ResearchExportService
from app.services.llm_generation_audit import llm_usage_path
from app.services.llm_usage_summary import ledger_summary
from app.services.material_lock_service import assert_event_materials_editable, set_event_material_lock
from app.services.participant_preview import active_preview_participant, preview_user_id
from app.services.participant_assignments import prepare_assignment_updates
from app.core.task_payload_validator import validate_task_authoring_payload

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_key)],
)


@router.get("/snapshot", response_model=AdminSnapshotResponse)
def admin_snapshot(repository: RepositoryProtocol = Depends(get_repository)) -> AdminSnapshotResponse:
    """一次載入 admin UI 需要的事件、條件、session 與研究紀錄摘要。

    Admin 前端初始化時呼叫，批次取得所有 events（含 personas
    與 latest_task）、conditions、sessions 以及 research_logs，
    避免多次 round-trip。

    Args:
        repository: 由 Dependency Injection 注入的資料存取層實例。

    Returns:
        AdminSnapshotResponse: 包含 events（附帶 personas、
            latest_task）、conditions（含已停用）、sessions
            與 research_logs。
    """
    events: list[EventListItem] = []
    for event in repository.list_events(include_archived=True):
        payload = event.model_dump()
        payload["personas"] = repository.list_personas(event.id, active_only=False)
        payload["latest_task"] = repository.get_latest_event_task(event.id)
        events.append(EventListItem(**payload))
    return AdminSnapshotResponse(
        events=events,
        conditions=repository.list_conditions(active_only=False),
        participants=repository.list_participants(),
        sessions=repository.list_sessions(),
        research_logs=repository.list_research_logs(),
    )


@router.get("/llm-usage", response_model=AdminLLMUsageResponse)
def admin_llm_usage() -> AdminLLMUsageResponse:
    try:
        return ledger_summary(llm_usage_path())
    except (OSError, UnicodeError) as exc:
        raise HTTPException(status_code=503, detail="目前無法讀取用量帳本，請稍後重試。") from exc


@router.get("/auth-users", response_model=AdminAuthUsersResponse)
def list_auth_users(repository: RepositoryProtocol = Depends(get_repository)) -> AdminAuthUsersResponse:
    """列出 Supabase Auth users，供 admin 綁定 participant 使用。

    此 endpoint 只讀取 Supabase Auth Admin API，不修改任何資料。
    回傳值會標示每個 Auth user 是否已綁定 participant。
    """
    settings = get_settings()
    auth_admin_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY_SERVICE_ROLE")
        or os.getenv("SUPABASE_KEY_service_role")
        or settings.supabase_service_role_key
    )
    if not settings.supabase_url or not auth_admin_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase admin credentials are not configured")

    try:
        response = httpx.get(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users",
            headers={
                "apikey": auth_admin_key,
                "authorization": f"Bearer {auth_admin_key}",
            },
            params={"page": "1", "per_page": "200"},
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Supabase service role key is required to list Auth users",
            ) from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to load Supabase Auth users") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to load Supabase Auth users") from exc

    payload = response.json()
    raw_users = payload.get("users") if isinstance(payload, dict) else payload
    if not isinstance(raw_users, list):
        raw_users = []

    participants_by_auth_id = {
        participant.auth_user_id: participant
        for participant in repository.list_participants()
        if participant.auth_user_id
    }
    users: list[AdminAuthUserSummary] = []
    for user in raw_users:
        if not isinstance(user, dict) or not user.get("id"):
            continue
        participant = participants_by_auth_id.get(user["id"])
        users.append(
            AdminAuthUserSummary(
                id=user["id"],
                email=user.get("email"),
                created_at=user.get("created_at"),
                last_sign_in_at=user.get("last_sign_in_at"),
                bound_participant_id=participant.id if participant else None,
                bound_participant_code=participant.code if participant else None,
            )
        )
    users.sort(key=lambda item: (item.email or "", item.id))
    return AdminAuthUsersResponse(users=users)


@router.get("/prompt-preview", response_model=AdminPromptPreviewResponse)
def prompt_preview(
    event_id: str,
    condition_key: str,
    persona_id: str | None = None,
    sample_user_message: str = "請說明這個事件的重要性。",
    repository: RepositoryProtocol = Depends(get_repository),
    prompt_service: PromptService = Depends(get_prompt_service),
    rag_pipeline: RagPipelineService = Depends(get_rag_pipeline),
) -> AdminPromptPreviewResponse:
    """預覽後端實際組裝的聊天 prompt；不呼叫 LLM，也不修改資料。

    Admin 可指定 event、condition 與 persona 組合，搭配範例使用者
    訊息，查看 PromptService 組裝出的各 module 與最終 prompt 文字。
    RAG 檢索會實際執行以提供真實 context，但不會呼叫 LLM 產生回覆。

    Args:
        event_id: 目標事件的 UUID 字串。
        condition_key: 實驗條件鍵值（如 ``"ebl_roleplay"``）。
        persona_id: 可選，指定使用的 persona UUID；未指定時
            自動選取第一個 active persona。
        sample_user_message: 模擬的使用者訊息，預設為
            ``"請說明這個事件的重要性。"``。
        repository: 由 Dependency Injection 注入的資料存取層實例。
        prompt_service: 由 Dependency Injection 注入的 PromptService 實例。
        rag_pipeline: 由 Dependency Injection 注入的 RagPipelineService 實例。

    Returns:
        AdminPromptPreviewResponse: 包含 event、condition、persona、
            sample_user_message、各 prompt module 與完整 prompt 文字。

    Raises:
        HTTPException: 404 — event、condition 或 persona 不存在時。
    """
    event = repository.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    condition = repository.get_condition_by_key(condition_key)
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment condition not found")

    persona = None
    if condition.roleplay_enabled:
        personas = repository.list_personas(event.id)
        if persona_id:
            persona = repository.get_persona(persona_id)
            if not persona or persona.event_id != event.id or not persona.active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected persona not found")
        elif personas:
            persona = personas[0]
        if not persona:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active personas found")

    rag_sources = rag_pipeline.retrieve(event.id, sample_user_message)
    modules = prompt_service.assemble_chat_modules(
        event=event,
        persona=persona,
        condition=condition,
        task_attempt=None,
        user_message=sample_user_message,
        rag_sources=rag_sources,
    )
    return AdminPromptPreviewResponse(
        event=event,
        condition=condition,
        persona=persona,
        sample_user_message=sample_user_message,
        modules=[PromptPreviewModule(name=module.name, content=module.content) for module in modules],
        prompt=prompt_service.render_modules(modules),
    )


@router.post("/prompt-dry-run", response_model=AdminPromptDryRunResponse)
async def prompt_dry_run(
    request: AdminPromptDryRunRequest,
    repository: RepositoryProtocol = Depends(get_repository),
    prompt_service: PromptService = Depends(get_prompt_service),
    rag_pipeline: RagPipelineService = Depends(get_rag_pipeline),
    chat_service: ChatService = Depends(get_chat_service),
) -> AdminPromptDryRunResponse:
    """Run the exact persona completion contract without persisting messages or logs."""
    event = repository.get_event(request.event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    condition = repository.get_condition_by_key(request.condition_key)
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment condition not found")

    persona = None
    if condition.roleplay_enabled:
        personas = repository.list_personas(event.id)
        if request.persona_id:
            persona = repository.get_persona(request.persona_id)
            if not persona or persona.event_id != event.id or not persona.active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected persona not found")
        elif personas:
            persona = personas[0]
        if not persona:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active personas found")

    task_attempt = repository.get_task_attempt(request.task_attempt_id) if request.task_attempt_id else None
    if task_attempt and task_attempt.event_id != event.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task attempt does not belong to event")
    if condition.ebl_enabled and not task_attempt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Historical EBL dry-run requires a persisted task_attempt_id",
        )

    rag_sources = rag_pipeline.retrieve(event.id, request.sample_user_message)
    interaction_runtime = build_interaction_runtime(condition, task_attempt, [])
    modules = prompt_service.assemble_chat_modules(
        event=event,
        persona=persona,
        condition=condition,
        task_attempt=task_attempt,
        user_message=request.sample_user_message,
        rag_sources=rag_sources,
        conversation_history=[],
        interaction_runtime=interaction_runtime,
    )
    prompt = prompt_service.render_modules(modules)
    generation, interaction_metadata, final_prompt = await chat_service.generate_validated_response(
        event=event,
        selected=persona,
        condition=condition,
        task_attempt=task_attempt,
        user_message=request.sample_user_message,
        base_prompt=prompt,
        rag_sources=rag_sources,
        interaction_runtime=interaction_runtime,
    )
    delivery_outcome = interaction_metadata.get("answer_delivery", {}).get("outcome")
    if delivery_outcome == "system_fallback":
        final_prompt_kind = "system_fallback"
    elif delivery_outcome == "constrained":
        final_prompt_kind = "constrained"
    else:
        final_prompt_kind = "repair" if final_prompt != prompt else "base"
    return AdminPromptDryRunResponse(
        event=event,
        condition=condition,
        persona=persona,
        sample_user_message=request.sample_user_message,
        modules=[PromptPreviewModule(name=module.name, content=module.content) for module in modules],
        prompt=prompt,
        final_prompt=final_prompt,
        final_prompt_kind=final_prompt_kind,
        final_messages=generation.request_messages,
        schema_repair_count=generation.llm_metadata.get("llm_call", {}).get("schema_repair_count", 0),
        response=generation.response,
        annotations=generation.annotations,
        related_events=generation.related_events,
        dynamic_context=generation.dynamic_context,
        interaction_metadata=interaction_metadata,
        rag_sources=rag_sources,
    )


@router.patch("/events/{event_id}", response_model=Event)
def update_event(
    event_id: str,
    request: EventUpdateRequest,
    repository: RepositoryProtocol = Depends(get_repository),
) -> Event:
    """更新歷史事件基本資料；正式資料來源仍是 repository/Supabase。

    支援部分更新（PATCH 語意）。修改後會自動寫入一筆
    ``event_updated`` 類型的 ResearchLog 紀錄。

    Args:
        event_id: 目標事件的 UUID 字串。
        request: 部分更新請求，可包含 canonical_name、description、
            century、start_year、end_year、context、source_summary。
        repository: 由 Dependency Injection 注入的資料存取層實例。

    Returns:
        Event: 更新後的完整事件資料。

    Raises:
        HTTPException: 404 — 指定 event_id 不存在時。
    """
    event = repository.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    assert_event_materials_editable(repository, event_id)

    before = event.model_copy(deep=True)
    updates = request.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(event, key, value)
    saved = repository.save_event(event)
    repository.log_research(
        ResearchLog(
            event_id=saved.id,
            action_type="event_updated",
            payload=build_change_payload(
                before=before,
                after=saved,
                fields=updates.keys(),
                subject={"event_id": saved.id, "event_name": saved.canonical_name},
            ),
        )
    )
    return saved


@router.post("/events/{event_id}/material-lock", response_model=Event)
def update_event_material_lock(
    event_id: str,
    request: MaterialLockRequest,
    repository: RepositoryProtocol = Depends(get_repository),
) -> Event:
    """鎖定正式素材，或在沒有進行中 Session 時解除鎖定。"""
    before = repository.get_event(event_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    before = before.model_copy(deep=True)
    saved = set_event_material_lock(repository, event_id, locked=request.locked)
    if before.materials_locked_at != saved.materials_locked_at:
        repository.log_research(
            ResearchLog(
                event_id=saved.id,
                action_type="event_materials_locked" if request.locked else "event_materials_unlocked",
                payload=build_change_payload(
                    before=before,
                    after=saved,
                    fields=["materials_locked_at"],
                    subject={"event_id": saved.id, "event_name": saved.canonical_name},
                ),
            )
        )
    return saved


@router.post("/events/{event_id}/archive", response_model=Event)
def archive_event(
    event_id: str,
    repository: RepositoryProtocol = Depends(get_repository),
) -> Event:
    """Archive event materials without deleting any related rows."""
    current = repository.get_event(event_id)
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    before = current.model_copy(deep=True)
    event = repository.archive_event(event_id)
    repository.log_research(
        ResearchLog(
            event_id=event.id,
            action_type="event_archived",
            payload=build_change_payload(
                before=before,
                after=event,
                fields=["archived_at"],
                subject={"event_id": event.id, "event_name": event.canonical_name},
            ),
        )
    )
    return event


@router.post("/events/{event_id}/restore", response_model=Event)
def restore_event(
    event_id: str,
    repository: RepositoryProtocol = Depends(get_repository),
) -> Event:
    """Restore archived event materials to the learner library."""
    current = repository.get_event(event_id)
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    before = current.model_copy(deep=True)
    event = repository.restore_event(event_id)
    repository.log_research(
        ResearchLog(
            event_id=event.id,
            action_type="event_restored",
            payload=build_change_payload(
                before=before,
                after=event,
                fields=["archived_at"],
                subject={"event_id": event.id, "event_name": event.canonical_name},
            ),
        )
    )
    return event


@router.patch("/tasks/{task_id}", response_model=EventTask)
def update_task(
    task_id: str,
    request: EventTaskUpdateRequest,
    repository: RepositoryProtocol = Depends(get_repository),
) -> EventTask:
    """更新 task 文字與 evaluation_payload，保存前檢查故事 token 與題目結構。

    先驗證必填欄位不為 null，再透過 ``validate_task_authoring_payload``
    檢查 error_elicitation_task_full_text 與 evaluation_payload 的結構完整性。
    修改後會自動寫入 ``task_updated`` 類型的 ResearchLog 紀錄。

    Args:
        task_id: 目標 task 的 UUID 字串。
        request: 部分更新請求，可包含 title、story_text、
            error_elicitation_task_full_text、evaluation_payload、revision_state。
        repository: 由 Dependency Injection 注入的資料存取層實例。

    Returns:
        EventTask: 更新後的完整 task 資料。

    Raises:
        HTTPException: 404 — 指定 task_id 不存在時。
        HTTPException: 422 — 必填欄位為 null 或 payload 結構驗證失敗時。
    """
    task = repository.get_event_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    assert_event_materials_editable(repository, task.event_id)
    before = task.model_copy(deep=True)
    updates = request.model_dump(exclude_unset=True)
    required_field_issues = [
        {
            "field": field,
            "message": f"{field} cannot be null.",
            "code": "required_field_null",
        }
        for field in ("story_text", "error_elicitation_task_full_text", "evaluation_payload", "revision_state")
        if field in updates and updates[field] is None
    ]
    if required_field_issues:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Task authoring payload failed validation.",
                "issues": required_field_issues,
            },
        )

    next_error_elicitation_task_full_text = updates.get("error_elicitation_task_full_text", task.error_elicitation_task_full_text)
    next_evaluation_payload = updates.get("evaluation_payload", task.evaluation_payload)
    validation_issues = validate_task_authoring_payload(
        error_elicitation_task_full_text=next_error_elicitation_task_full_text,
        evaluation_payload=next_evaluation_payload,
    )
    if validation_issues:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Task authoring payload failed validation.",
                "issues": validation_issues,
            },
        )

    for key, value in updates.items():
        setattr(task, key, value)
    saved = repository.save_event_task(task)
    repository.log_research(
        ResearchLog(
            event_id=saved.event_id,
            task_id=saved.id,
            action_type="task_updated",
            payload=build_change_payload(
                before=before,
                after=saved,
                fields=updates.keys(),
                subject={"task_id": saved.id, "event_id": saved.event_id},
            ),
        )
    )
    return saved


@router.patch("/personas/{persona_id}", response_model=Persona)
def update_admin_persona(
    persona_id: str,
    request: PersonaUpdateRequest,
    service: PersonaService = Depends(get_persona_service),
) -> Persona:
    """更新 persona 基本資料與 prompt_profile。

    Admin 專用的 persona 更新入口，統一交由 PersonaService 驗證。
    支援部分更新（PATCH 語意），可修改 name、biography、
    prompt_profile 等欄位。

    Args:
        persona_id: 目標 persona 的 UUID 字串。
        request: 部分更新請求，僅含需修改的欄位。
        service: 由 Dependency Injection 注入的 PersonaService。

    Returns:
        Persona: 更新後的完整 persona 資料。

    Raises:
        HTTPException: 404 — 指定 persona_id 不存在時。
    """
    return service.update_persona(persona_id, request)


@router.get("/participants/{participant_id}/preview", response_model=AdminParticipantPreviewResponse)
def participant_preview(
    participant_id: str,
    repository: RepositoryProtocol = Depends(get_repository),
    session_service: SessionService = Depends(get_session_service),
) -> AdminParticipantPreviewResponse:
    """Preview assigned conditions using separate admin test progress."""
    participant = active_preview_participant(repository, participant_id)
    test_user_id = preview_user_id(participant.id)
    return AdminParticipantPreviewResponse(
        participant=participant,
        test_user_id=test_user_id,
        progress=session_service.user_progress(test_user_id, admin_test=True).progress,
    )


@router.post("/participants", response_model=Participant, status_code=status.HTTP_201_CREATED)
def create_participant(
    request: ParticipantCreateRequest,
    repository: RepositoryProtocol = Depends(get_repository),
) -> Participant:
    """建立受測者代號，可選擇立即綁定 Auth 帳號與實驗條件。"""
    code = request.code.strip().upper()
    if not code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Participant code is required",
        )
    if any(participant.code.upper() == code for participant in repository.list_participants()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Participant code {code} already exists",
        )

    auth_user_id = request.auth_user_id.strip() if request.auth_user_id else None
    if auth_user_id:
        existing = repository.get_participant_by_auth_user(auth_user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Auth user already bound to participant {existing.code}",
            )

    assignment_updates = prepare_assignment_updates(repository, request.model_dump(exclude_unset=True))
    participant = Participant(
        code=code,
        auth_user_id=auth_user_id,
        display_name=request.display_name,
        cohort=request.cohort,
        condition_list=normalize_condition_sequence(assignment_updates.get("condition_list", request.condition_list)),
        status="active",
        notes=request.notes,
        metadata=assignment_updates.get("metadata", request.metadata),
    )
    saved = repository.save_participant(participant)
    repository.log_research(
        ResearchLog(
            action_type="participant_created",
            payload=build_change_payload(
                before=None,
                after=saved,
                fields=[
                    "code",
                    "auth_user_id",
                    "display_name",
                    "cohort",
                    "condition_list",
                    "status",
                    "notes",
                    "metadata",
                ],
                subject={"participant_id": saved.id, "participant_code": saved.code},
            ),
        )
    )
    return saved


@router.post("/participants/{participant_id}/archive", response_model=Participant)
def archive_participant(
    participant_id: str,
    repository: RepositoryProtocol = Depends(get_repository),
) -> Participant:
    """停止受測者的實驗存取，保留 Auth 綁定與全部研究資料。"""
    participant = repository.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    if participant.status == "archived":
        return participant

    before = participant.model_copy(deep=True)
    participant.status = "archived"
    saved = repository.save_participant(participant)
    repository.log_research(
        ResearchLog(
            action_type="participant_archived",
            payload=build_change_payload(
                before=before,
                after=saved,
                fields=["status"],
                subject={
                    "participant_id": saved.id,
                    "participant_code": saved.code,
                    "auth_user_id": saved.auth_user_id,
                },
            ),
        )
    )
    return saved


@router.post("/participants/{participant_id}/restore", response_model=Participant)
def restore_participant(
    participant_id: str,
    repository: RepositoryProtocol = Depends(get_repository),
) -> Participant:
    """恢復受測者的實驗存取，不建立新帳號或新研究資料。"""
    participant = repository.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    if participant.status == "active":
        return participant

    before = participant.model_copy(deep=True)
    participant.status = "active"
    saved = repository.save_participant(participant)
    repository.log_research(
        ResearchLog(
            action_type="participant_restored",
            payload=build_change_payload(
                before=before,
                after=saved,
                fields=["status"],
                subject={
                    "participant_id": saved.id,
                    "participant_code": saved.code,
                    "auth_user_id": saved.auth_user_id,
                },
            ),
        )
    )
    return saved


@router.patch("/participants/{participant_id}", response_model=Participant)
def update_participant(
    participant_id: str,
    request: ParticipantUpdateRequest,
    repository: RepositoryProtocol = Depends(get_repository),
) -> Participant:
    """更新 participant registry，不修改正式實驗紀錄 identity。

    Participant 僅用於研究端顯示、Auth user 對應與 condition 指派。
    ``experiment_sessions.user_id`` 等正式紀錄仍維持 Supabase Auth user id。
    """
    participant = repository.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    before = participant.model_copy(deep=True)
    updates = prepare_assignment_updates(repository, request.model_dump(exclude_unset=True), participant)
    if "auth_user_id" in updates:
        raw_auth_user_id = updates["auth_user_id"]
        next_auth_user_id = raw_auth_user_id.strip() if isinstance(raw_auth_user_id, str) else None
        updates["auth_user_id"] = next_auth_user_id or None
        if updates["auth_user_id"]:
            existing = repository.get_participant_by_auth_user(updates["auth_user_id"])
            if existing and existing.id != participant.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Auth user already bound to participant {existing.code}",
                )

    if "condition_list" in updates and updates["condition_list"] is not None:
        updates["condition_list"] = normalize_condition_sequence(updates["condition_list"])

    for key, value in updates.items():
        setattr(participant, key, value)

    saved = repository.save_participant(participant)
    repository.log_research(
        ResearchLog(
            action_type="participant_updated",
            payload=build_change_payload(
                before=before,
                after=saved,
                fields=updates.keys(),
                subject={"participant_id": saved.id, "participant_code": saved.code},
            ),
        )
    )
    return saved


@router.post("/sessions/{session_id}/timer", response_model=ExperimentSession)
def reset_session_timer(
    session_id: str,
    request: SessionTimerResetRequest,
    service: SessionService = Depends(get_session_service),
) -> ExperimentSession:
    """Reset a Chat-ready session to the fixed ten-minute countdown."""
    return service.reset_timer(session_id)


@router.post("/sessions/{session_id}/restart", response_model=SessionRestartResponse)
def restart_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> SessionRestartResponse:
    """封存舊 session 與對話，保留研究資料後建立同事件的新 session。"""
    return service.restart_session(session_id)


@router.patch("/conditions/{condition_id}", response_model=ExperimentCondition)
def update_condition(
    condition_id: str,
    request: ExperimentConditionUpdateRequest,
    repository: RepositoryProtocol = Depends(get_repository),
) -> ExperimentCondition:
    """更新 2x2 實驗條件的可編輯資料。

    label、description 與 active 可調整；EBL、role-play、agent mode 與
    response policy 必須維持 condition key 對應的固定實驗矩陣。

    Args:
        condition_id: 目標 condition 的 UUID 字串。
        request: 部分更新請求，僅含需修改的欄位。
        repository: 由 Dependency Injection 注入的資料存取層實例。

    Returns:
        ExperimentCondition: 更新後的完整實驗條件資料。

    Raises:
        HTTPException: 404 — 指定 condition_id 不存在時。
        ValidationError: 更新內容違反固定 2x2 矩陣時。
    """
    condition = repository.get_condition(condition_id)
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")
    before = condition.model_copy(deep=True)
    updates = request.model_dump(exclude_unset=True)
    try:
        validated = ExperimentCondition.model_validate({**condition.model_dump(), **updates})
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Condition behavior must match its fixed 01-04 experiment mapping",
        ) from exc
    saved = repository.save_condition(validated)
    repository.log_research(
        ResearchLog(
            action_type="condition_updated",
            payload=build_change_payload(
                before=before,
                after=saved,
                fields=updates.keys(),
                subject={
                    "condition_id": saved.id,
                    "condition_key": saved.condition_key,
                },
            ),
        )
    )
    return saved


@router.get("/research-logs", response_model=list[ResearchLog])
def list_research_logs(
    limit: int = 200,
    repository: RepositoryProtocol = Depends(get_repository),
) -> list[ResearchLog]:
    """列出流程行為紀錄；對話內容分析仍以 messages 為主。

    回傳最近的 ResearchLog 紀錄，記錄 event_updated、
    task_updated 等管理操作。對話內容不在此紀錄中，
    需透過 conversation messages 查詢。

    Args:
        limit: 回傳筆數上限，預設 200。
        repository: 由 Dependency Injection 注入的資料存取層實例。

    Returns:
        list[ResearchLog]: 依時間倒序的流程行為紀錄清單。
    """
    return repository.list_research_logs(limit=limit)


@router.get("/sessions/{session_id}/research", response_model=AdminSessionResearchResponse)
def session_research(
    session_id: str,
    repository: RepositoryProtocol = Depends(get_repository),
) -> AdminSessionResearchResponse:
    """以受測者代號載入單一 Session 的完整對話與研究統計。"""
    return ResearchExportService(repository).session_research(session_id)


@router.get("/research-export")
def export_research_data(
    format: Literal["json", "csv"] = "json",
    repository: RepositoryProtocol = Depends(get_repository),
) -> Response:
    """匯出正式研究資料；不包含 Supabase Auth user id 或 email。"""
    content, media_type, filename = ResearchExportService(repository).export(format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
