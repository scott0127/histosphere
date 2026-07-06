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

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_prompt_service, get_rag_pipeline, get_repository, require_admin_key
from app.core.config import get_settings
from app.crud.protocols import RepositoryProtocol
from app.models.domain import Event, EventTask, ExperimentCondition, Participant, Persona, ResearchLog
from app.schemas.requests import (
    EventUpdateRequest,
    EventTaskUpdateRequest,
    ExperimentConditionUpdateRequest,
    ParticipantUpdateRequest,
    PersonaUpdateRequest,
)
from app.schemas.responses import (
    AdminAuthUserSummary,
    AdminAuthUsersResponse,
    AdminPromptPreviewResponse,
    AdminSnapshotResponse,
    EventListItem,
    PromptPreviewModule,
)
from app.services import PromptService, RagPipelineService
from app.services.task_payload_validator import validate_task_authoring_payload

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
    for event in repository.list_events():
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
    """更新 task 文字與 evaluation_payload，保存前檢查故事 token 與題目結構。

    先驗證必填欄位不為 null，再透過 ``validate_task_authoring_payload``
    檢查 display_text 與 evaluation_payload 的結構完整性。
    修改後會自動寫入 ``task_updated`` 類型的 ResearchLog 紀錄。

    Args:
        task_id: 目標 task 的 UUID 字串。
        request: 部分更新請求，可包含 title、story_text、
            display_text、evaluation_payload、revision_state。
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
    updates = request.model_dump(exclude_unset=True)
    required_field_issues = [
        {
            "field": field,
            "message": f"{field} cannot be null.",
            "code": "required_field_null",
        }
        for field in ("story_text", "display_text", "evaluation_payload", "revision_state")
        if field in updates and updates[field] is None
    ]
    if required_field_issues:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Task authoring payload failed validation.",
                "issues": required_field_issues,
            },
        )

    next_display_text = updates.get("display_text", task.display_text)
    next_evaluation_payload = updates.get("evaluation_payload", task.evaluation_payload)
    validation_issues = validate_task_authoring_payload(
        display_text=next_display_text,
        evaluation_payload=next_evaluation_payload,
    )
    if validation_issues:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
            payload={"updated_fields": sorted(updates.keys())},
        )
    )
    return saved


@router.patch("/personas/{persona_id}", response_model=Persona)
def update_admin_persona(
    persona_id: str,
    request: PersonaUpdateRequest,
    repository: RepositoryProtocol = Depends(get_repository),
) -> Persona:
    """更新 persona 基本資料與 prompt_profile。

    Admin 專用的 persona 更新入口，直接操作 repository。
    支援部分更新（PATCH 語意），可修改 name、biography、
    prompt_profile 等欄位。

    Args:
        persona_id: 目標 persona 的 UUID 字串。
        request: 部分更新請求，僅含需修改的欄位。
        repository: 由 Dependency Injection 注入的資料存取層實例。

    Returns:
        Persona: 更新後的完整 persona 資料。

    Raises:
        HTTPException: 404 — 指定 persona_id 不存在時。
    """
    persona = repository.get_persona(persona_id)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    updates = request.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(persona, key, value)
    return repository.save_persona(persona)


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

    updates = request.model_dump(exclude_unset=True)
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
        order = {"01": 1, "02": 2, "03": 3, "04": 4}
        updates["condition_list"] = sorted(set(updates["condition_list"]), key=lambda code: order[code])

    for key, value in updates.items():
        setattr(participant, key, value)

    saved = repository.save_participant(participant)
    repository.log_research(
        ResearchLog(
            action_type="participant_updated",
            payload={
                "participant_id": saved.id,
                "participant_code": saved.code,
                "updated_fields": sorted(updates.keys()),
            },
        )
    )
    return saved


@router.patch("/conditions/{condition_id}", response_model=ExperimentCondition)
def update_condition(
    condition_id: str,
    request: ExperimentConditionUpdateRequest,
    repository: RepositoryProtocol = Depends(get_repository),
) -> ExperimentCondition:
    """更新 2x2 實驗條件設定，例如 EBL/role-play 是否啟用。

    可修改 label、ebl_enabled、roleplay_enabled、agent_mode、
    response_policy、description 與 active 等欄位。
    支援部分更新（PATCH 語意）。

    Args:
        condition_id: 目標 condition 的 UUID 字串。
        request: 部分更新請求，僅含需修改的欄位。
        repository: 由 Dependency Injection 注入的資料存取層實例。

    Returns:
        ExperimentCondition: 更新後的完整實驗條件資料。

    Raises:
        HTTPException: 404 — 指定 condition_id 不存在時。
    """
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
