"""API request schemas.

本模組定義所有 API endpoint 接收的請求 body schema。
每個 schema 皆繼承 Pydantic BaseModel，透過 Field 定義
必填/選填、最小長度等驗證規則。
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.persona_prompt_contract import PersonaPromptProfile
from app.models.domain import ChatMessage, ConditionKey


class EventInitializeRequest(BaseModel):
    """事件初始化請求。

    Learner 選擇或輸入事件名稱後送出，觸發事件工作區建立流程。

    Attributes:
        event_name: 事件名稱（至少 1 字元）。
        condition_key: 實驗條件鍵值，預設 ``"ebl_roleplay"``。
        rebuild: 若為 True，強制重建已存在的事件。
        user_id: 受測者識別（可選）。
    """

    event_name: str = Field(..., min_length=1)
    condition_key: ConditionKey = "ebl_roleplay"
    rebuild: bool = False
    user_id: str | None = None


class EventCheckRequest(BaseModel):
    """事件名稱檢查請求。

    前端在 learner 輸入事件名稱後呼叫，檢查是否已存在。

    Attributes:
        event_name: 要檢查的事件名稱（至少 1 字元）。
    """

    event_name: str = Field(..., min_length=1)


class EventUpdateRequest(BaseModel):
    """事件更新請求（Admin PATCH）。

    支援部分更新，僅傳入需修改的欄位。

    Attributes:
        canonical_name: 新的事件名稱（至少 1 字元，可選）。
        description: 新的事件描述（可選）。
        century: 新的世紀值（可選）。
        start_year: 新的起始年份（可選）。
        end_year: 新的結束年份（可選）。
        context: 新的歷史脈絡（可選）。
        source_summary: 新的來源摘要（可選）。
    """

    canonical_name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    century: int | None = None
    start_year: int | None = None
    end_year: int | None = None
    context: str | None = None
    source_summary: dict[str, Any] | None = None


class TaskSubmitRequest(BaseModel):
    """Task 提交請求。

    Learner 完成作答後送出，觸發 LLM 判斷與 conversation 建立。

    Attributes:
        session_id: 關聯的 session UUID（至少 1 字元）。
        response_payload: Learner 的作答內容（JSON）。
        user_id: 受測者識別（可選）。
    """

    session_id: str = Field(..., min_length=1)
    response_payload: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None


class TaskDraftRequest(BaseModel):
    """Task 草稿儲存請求。

    Learner 在作答過程中暫存進度。

    Attributes:
        session_id: 關聯的 session UUID（至少 1 字元）。
        response_payload: 目前的作答內容（JSON）。
        user_id: 受測者識別（可選）。
    """

    session_id: str = Field(..., min_length=1)
    response_payload: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None


class ConversationCreateRequest(BaseModel):
    """Conversation 建立請求。

    主要為相容性保留；正常 learner 流程中 conversation
    由 task submit 自動建立。

    Attributes:
        event_id: 關聯的事件 UUID（至少 1 字元）。
        task_attempt_id: 觸發的 TaskAttempt ID（可選）。
        session_id: 關聯的 session ID（可選）。
        user_id: 受測者識別（可選）。
    """

    event_id: str = Field(..., min_length=1)
    task_attempt_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None


class ChatRequest(BaseModel):
    """聊天訊息請求。

    Learner 送出一則對話訊息。

    Attributes:
        conversation_id: 所屬 Conversation UUID（至少 1 字元）。
        user_message: 使用者訊息內容（至少 1 字元）。
        history: 前端持有的歷史訊息（相容欄位；目前 ChatService 尚未納入 prompt context）。
        target_persona_id: 指定回覆的 Persona ID（可選）。
    """

    conversation_id: str = Field(..., min_length=1)
    user_message: str = Field(..., min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    target_persona_id: str | None = None


class PersonaCreateRequest(BaseModel):
    """Persona 建立請求。

    Admin 或研究者手動新增歷史人物角色。

    Attributes:
        event_id: 關聯的事件 UUID（至少 1 字元）。
        name: 角色名稱（至少 1 字元）。
        english_name: 英文名稱（可選）。
        role: 角色身份（可選）。
        biography: 角色簡傳（可選）。
        expertise_areas: 專業領域清單。
        sources: 資料來源引用清單。
        avatar_url: 頭像 URL（可選）。
        prompt_profile: Prompt 用的角色 profile。
        active: 是否啟用，預設 True。
        sort_order: 排序順序，預設 0。
        revision_state: 修訂狀態，預設 ``"manual"``。
    """

    event_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    english_name: str | None = None
    role: str | None = None
    biography: str | None = None
    expertise_areas: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    avatar_url: str | None = None
    prompt_profile: PersonaPromptProfile = Field(default_factory=PersonaPromptProfile)
    active: bool = True
    sort_order: int = 0
    revision_state: str = "manual"


class PersonaUpdateRequest(BaseModel):
    """Persona 更新請求（PATCH 語意）。

    支援部分更新，僅傳入需修改的欄位。

    Attributes:
        name: 新的角色名稱（可選）。
        english_name: 新的英文名稱（可選）。
        role: 新的角色身份（可選）。
        biography: 新的簡傳（可選）。
        expertise_areas: 新的專業領域清單（可選）。
        sources: 新的來源引用清單（可選）。
        avatar_url: 新的頭像 URL（可選）。
        prompt_profile: 新的 prompt profile（可選）。
        active: 是否啟用（可選）。
        sort_order: 新的排序順序（可選）。
        revision_state: 新的修訂狀態（可選）。
    """

    name: str | None = None
    english_name: str | None = None
    role: str | None = None
    biography: str | None = None
    expertise_areas: list[str] | None = None
    sources: list[dict[str, Any]] | None = None
    avatar_url: str | None = None
    prompt_profile: PersonaPromptProfile | None = None
    active: bool | None = None
    sort_order: int | None = None
    revision_state: str | None = None


class EventTaskUpdateRequest(BaseModel):
    """Task 更新請求（Admin PATCH）。

    支援部分更新。API handler 使用 ``exclude_unset=True``，因此未提供的
    revision_state 會維持原值；前端正式儲存流程會明確送出 ``"teacher_modified"``。

    Attributes:
        title: 新的 task 標題（可選）。
        story_text: 新的完整故事文字（可選）。
        display_text: 新的顯示用文字（可選）。
        evaluation_payload: 新的評量結構（可選）。
        revision_state: 修訂狀態；只有 request 明確提供時才會套用。
    """

    title: str | None = None
    story_text: str | None = None
    display_text: str | None = None
    evaluation_payload: dict[str, Any] | None = None
    revision_state: Literal["llm_generated", "teacher_modified", "manual"] | None = "teacher_modified"


class ExperimentConditionUpdateRequest(BaseModel):
    """實驗條件更新請求（Admin PATCH）。

    支援部分更新。

    Attributes:
        label: 新的條件標籤（可選）。
        ebl_enabled: 是否啟用 EBL（可選）。
        roleplay_enabled: 是否啟用 role-play（可選）。
        agent_mode: 新的 AI 代理模式（可選）。
        response_policy: 新的回覆策略（可選）。
        description: 新的描述（可選）。
        active: 是否啟用（可選）。
    """

    label: str | None = None
    ebl_enabled: bool | None = None
    roleplay_enabled: bool | None = None
    agent_mode: str | None = None
    response_policy: str | None = None
    description: str | None = None
    active: bool | None = None


class ParticipantCreateRequest(BaseModel):
    """建立受測者 registry 紀錄；Auth 帳號可稍後再綁定。"""

    code: str = Field(..., min_length=1)
    auth_user_id: str | None = None
    display_name: str | None = None
    cohort: str | None = None
    condition_list: list[Literal["01", "02", "03", "04"]] = Field(default_factory=list)
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParticipantUpdateRequest(BaseModel):
    """Participant registry 更新請求（Admin PATCH）。

    Participant 只管理研究端顯示與分派資訊；正式實驗紀錄仍使用
    Supabase Auth user id。此 request 不允許修改 participant id/code。
    """

    auth_user_id: str | None = None
    display_name: str | None = None
    cohort: str | None = None
    condition_list: list[Literal["01", "02", "03", "04"]] | None = None
    status: Literal["active", "completed", "excluded", "archived"] | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None


class SessionTimerResetRequest(BaseModel):
    """Admin-only reset of the fixed experiment countdown."""

    duration_minutes: Literal[5] = 5


class AdminPromptDryRunRequest(BaseModel):
    """Admin-only non-persistent persona completion test."""

    event_id: str = Field(..., min_length=1)
    condition_key: ConditionKey
    persona_id: str | None = None
    task_attempt_id: str | None = None
    sample_user_message: str = Field(default="請說明這個事件的重要性。", min_length=1)
