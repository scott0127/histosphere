"""API response schemas.

本模組定義所有 API endpoint 回傳的回應 body schema。
每個 schema 皆繼承 Pydantic BaseModel，組合 domain model
與額外的 API-specific 欄位。
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.domain import (
    Annotation,
    ChatMessage,
    Conversation,
    Event,
    EventTask,
    ExperimentCondition,
    ExperimentSession,
    Participant,
    Persona,
    RagSource,
    RelatedEvent,
    ResearchLog,
    TaskAttempt,
)


class EventInitializeResponse(BaseModel):
    """事件初始化回應。

    包含初始化流程產生的所有資料，供前端進入 task 作答頁。

    Attributes:
        event_id: 事件 UUID。
        session_id: 實驗 session UUID。
        event: 完整的 Event 資料。
        task: 生成的 EventTask。
        personas: 生成的 Persona 清單。
        condition: 使用的 ExperimentCondition。
    """

    event_id: str
    session_id: str
    event: Event
    task: EventTask
    personas: list[Persona]
    condition: ExperimentCondition


class EventListItem(Event):
    """事件列表項目（含 personas 與 latest_task 摘要）。

    繼承 Event 並擴充 personas 與 latest_task 欄位，
    供事件列表頁與 admin snapshot 使用。

    Attributes:
        personas: 該事件的 Persona 清單。
        latest_task: 該事件最新的 Task（可為 None）。
    """

    personas: list[Persona] = Field(default_factory=list)
    latest_task: EventTask | None = None


class TaskSubmitResponse(BaseModel):
    """Task 提交回應。

    包含判斷結果、建立的 conversation 與 greeting，
    供前端導向聊天頁。

    Attributes:
        attempt_id: TaskAttempt UUID。
        conversation_id: 建立的 Conversation UUID。
        event: 關聯事件。
        task: 關聯 task。
        personas: 可用的 Persona 清單。
        condition: 使用的實驗條件。
        attempt: TaskAttempt 紀錄。
        judgement: LLM 判斷結果（JSON）。
        greeting: AI 開場白文字。
        history: 初始訊息歷史。
    """

    attempt_id: str
    conversation_id: str
    event: Event
    task: EventTask
    personas: list[Persona]
    condition: ExperimentCondition
    attempt: TaskAttempt
    judgement: dict[str, Any] = Field(default_factory=dict)
    greeting: str
    history: list[ChatMessage] = Field(default_factory=list)


class TaskSubmissionAcceptedResponse(BaseModel):
    """Immediate acknowledgement for queued task judgement/greeting work."""

    attempt_id: str
    status: str
    poll_url: str


class TaskSubmissionStatusResponse(BaseModel):
    """Persistent task submission job state used by frontend polling/recovery."""

    attempt: TaskAttempt
    result: TaskSubmitResponse | None = None
    error: str | None = None


class TaskDraftResponse(BaseModel):
    """Task 草稿儲存回應。

    Attributes:
        attempt: 已儲存的 TaskAttempt 紀錄。
    """

    attempt: TaskAttempt


class ConversationCreateResponse(BaseModel):
    """Conversation 建立回應。

    Attributes:
        conversation_id: 建立的 Conversation UUID。
        event: 關聯事件。
        personas: 可用的 Persona 清單。
        condition: 使用的實驗條件（可為 None）。
        greeting: AI 開場白文字。
        history: 初始訊息歷史。
    """

    conversation_id: str
    event: Event
    personas: list[Persona]
    condition: ExperimentCondition | None = None
    greeting: str
    history: list[ChatMessage] = Field(default_factory=list)


class ConversationLoadResponse(BaseModel):
    """Conversation 載入回應。

    前端聊天頁初始化時使用，包含完整的對話狀態。

    Attributes:
        conversation_id: Conversation UUID。
        event: 關聯事件。
        personas: 可用的 Persona 清單。
        messages: 歷史訊息清單。
        condition: 使用的實驗條件（可為 None）。
        task: 關聯的前置任務（可為 None）。
        task_attempt: 關聯的 TaskAttempt（可為 None）。
        related_events: 關聯事件清單。
    """

    conversation_id: str
    session: ExperimentSession | None = None
    event: Event
    personas: list[Persona]
    messages: list[ChatMessage]
    condition: ExperimentCondition | None = None
    task: EventTask | None = None
    task_attempt: TaskAttempt | None = None
    related_events: list[RelatedEvent] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """聊天回覆回應。

    Attributes:
        response: AI 回覆文字。
        selected_persona: 實際使用的 Persona（可為 None）。
        assistant_name: AI 助手顯示名稱。
        message: 已儲存的 ChatMessage 紀錄。
        annotations: 歷史標注清單。
        related_events: 關聯事件清單。
        dynamic_context: 動態 context 補充。
        rag_sources: RAG 檢索來源清單。
    """

    response: str
    selected_persona: Persona | None = None
    assistant_name: str
    message: ChatMessage
    annotations: list[Annotation] = Field(default_factory=list)
    related_events: list[RelatedEvent] = Field(default_factory=list)
    dynamic_context: str = ""
    rag_sources: list[RagSource] = Field(default_factory=list)


class ChatOperationStatusResponse(BaseModel):
    """可供斷線後重新查詢的聊天回合狀態。"""

    client_request_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    retryable: bool = False
    learner_message: ChatMessage
    response: ChatResponse | None = None


class AdminSnapshotResponse(BaseModel):
    """Admin 全頁快照回應。

    一次載入 admin UI 所需的所有資料。

    Attributes:
        events: 事件清單（含 personas 與 latest_task）。
        conditions: 實驗條件清單（含已停用）。
        participants: 受測者清單。
        sessions: 實驗 session 清單。
        research_logs: 流程行為紀錄清單。
    """

    events: list[EventListItem] = Field(default_factory=list)
    conditions: list[ExperimentCondition] = Field(default_factory=list)
    participants: list[Participant] = Field(default_factory=list)
    sessions: list[ExperimentSession] = Field(default_factory=list)
    research_logs: list[ResearchLog] = Field(default_factory=list)


class AdminAuthUserSummary(BaseModel):
    """Admin 綁定 participant 時可選的 Supabase Auth user 摘要。"""

    id: str
    email: str | None = None
    created_at: str | None = None
    last_sign_in_at: str | None = None
    bound_participant_id: str | None = None
    bound_participant_code: str | None = None


class AdminAuthUsersResponse(BaseModel):
    """Admin Auth user 清單回應。"""

    users: list[AdminAuthUserSummary] = Field(default_factory=list)


class PromptPreviewModule(BaseModel):
    """Prompt 預覽模組。

    Attributes:
        name: 模組名稱。
        content: 模組內容文字。
    """

    name: str
    content: str


class AdminPromptPreviewResponse(BaseModel):
    """Admin prompt 預覽回應。

    顯示 PromptService 組裝出的各 module 與最終 prompt。

    Attributes:
        event: 關聯事件。
        condition: 使用的實驗條件。
        persona: 使用的 Persona（可為 None）。
        sample_user_message: 模擬的使用者訊息。
        modules: Prompt module 清單。
        prompt: 組裝後的完整 prompt 文字。
    """

    event: Event
    condition: ExperimentCondition
    persona: Persona | None = None
    sample_user_message: str
    modules: list[PromptPreviewModule] = Field(default_factory=list)
    prompt: str


class AdminPromptDryRunResponse(AdminPromptPreviewResponse):
    """Prompt preview plus an LLM response that is never stored as a message."""

    response: str
    annotations: list[Annotation] = Field(default_factory=list)
    related_events: list[RelatedEvent] = Field(default_factory=list)
    dynamic_context: str = ""
    interaction_metadata: dict = Field(default_factory=dict)
    rag_sources: list[RagSource] = Field(default_factory=list)


class SessionStateResponse(BaseModel):
    """Session 狀態回應。

    前端恢復中斷實驗時使用。

    Attributes:
        session: 實驗 session。
        event: 關聯事件。
        task: 關聯 task（可為 None）。
        personas: Persona 清單。
        condition: 實驗條件（可為 None）。
        attempt: TaskAttempt（可為 None）。
        conversation_id: 已建立的 Conversation ID（可為 None）。
    """

    session: ExperimentSession
    event: Event
    task: EventTask | None = None
    personas: list[Persona] = Field(default_factory=list)
    condition: ExperimentCondition | None = None
    attempt: TaskAttempt | None = None
    conversation_id: str | None = None


class SessionRestartResponse(BaseModel):
    """Admin 封存同事件的舊 session 並建立新 session 後的結果。"""

    archived_sessions: list[ExperimentSession] = Field(default_factory=list)
    new_session: ExperimentSession


class UserProgressItem(BaseModel):
    """使用者進度清單項目。

    Attributes:
        event_id: 事件 UUID。
        condition_key: 實驗條件鍵值。
        session_id: Session UUID。
        task_id: Task UUID（可為 None）。
        attempt_id: Attempt UUID（可為 None）。
        conversation_id: Conversation UUID（可為 None）。
        status: 進度狀態。
        updated_at: 最後更新時間（ISO 格式字串）。
    """

    event_id: str
    condition_key: str
    session_id: str
    task_id: str | None = None
    attempt_id: str | None = None
    conversation_id: str | None = None
    status: str
    updated_at: str


class UserProgressResponse(BaseModel):
    """使用者進度回應。

    Attributes:
        progress: 進度清單。
    """

    progress: list[UserProgressItem] = Field(default_factory=list)


class ParticipantMeResponse(BaseModel):
    """目前登入者對應的 participant 與進度。

    Attributes:
        participant: Auth user 對應的研究受測者。
        progress: 該 Auth user 的 session/task/chat 進度清單。
    """

    participant: Participant
    progress: list[UserProgressItem] = Field(default_factory=list)


class AdminConversationStats(BaseModel):
    """單一 Session 對話的可驗證統計。"""

    total_messages: int = 0
    learner_messages: int = 0
    assistant_messages: int = 0
    completed_exchanges: int = 0
    prompt_tokens: int = 0
    cached_prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    llm_calls_total: int = 0
    llm_calls_with_usage: int = 0
    llm_messages_total: int = 0
    llm_messages_with_usage: int = 0
    token_usage_coverage: float = 0.0
    token_usage_complete: bool = False
    estimated_cost_usd: float | None = None
    cost_usage_complete: bool = False
    first_message_at: str | None = None
    last_message_at: str | None = None
    duration_seconds: int | None = None


class AdminMaterialSnapshot(BaseModel):
    """Session 建立時素材快照；舊 Session 會明確標示缺少。"""

    status: Literal["captured", "legacy_missing"]
    material_hash: str | None = None
    hash_verified: bool = False
    captured_at: str | None = None
    materials: dict[str, Any] = Field(default_factory=dict)


class AdminPromptRecord(BaseModel):
    """一次正式 LLM 回覆所使用的 Prompt 紀錄。"""

    stage: str
    message_id: str | None = None
    prompt_hash: str
    hash_verified: bool = False
    prompt: str
    modules: list[dict[str, str]] = Field(default_factory=list)
    llm_call: dict[str, Any] | None = None
    created_at: str


class AdminSessionResearchResponse(BaseModel):
    """Admin 檢視單一受測者 Session 的完整研究資料。"""

    participant_code: str
    participant_bound: bool = False
    session: ExperimentSession
    event: Event
    condition: ExperimentCondition | None = None
    task: EventTask | None = None
    attempt: TaskAttempt | None = None
    conversation: Conversation | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    stats: AdminConversationStats
    material_snapshot: AdminMaterialSnapshot
    prompt_records: list[AdminPromptRecord] = Field(default_factory=list)
    research_logs: list[ResearchLog] = Field(default_factory=list)
