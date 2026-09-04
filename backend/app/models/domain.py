"""Domain model definitions.

本模組定義 Histosphere 後端的所有 Pydantic domain model，
對應 Supabase/PostgreSQL 資料表結構。所有 model 皆繼承
``BaseModel``，欄位預設值與型別約束透過 Pydantic 驗證。

Type aliases:
    - ``ConditionKey``: 2x2 實驗條件鍵值的合法字串。
    - ``SpeakerType``: 聊天訊息發言者角色。
    - ``ResponsePolicy``: AI 回覆策略（standard / scaffold）。

Utility functions:
    - ``utc_now()``: 取得 UTC 時間戳。
    - ``new_id()``: 產生 UUID v4 字串。
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.experiment_conditions import validate_condition_behavior
from app.core.persona_prompt_contract import normalize_persona_prompt_profile


ConditionKey = Literal[
    "no_ebl_no_roleplay",
    "ebl_no_roleplay",
    "no_ebl_roleplay",
    "ebl_roleplay",
]
"""2x2 實驗條件鍵值的合法字串聯集。"""

SpeakerType = Literal["learner", "assistant", "persona"]
ChatOperationStatus = Literal["pending", "processing", "completed", "failed"]
"""聊天訊息發言者角色：learner / assistant（generic）/ persona（role-play）。"""

ResponsePolicy = Literal["standard", "scaffold"]
"""AI 回覆策略：direct（可直接給答案）/ scaffold（引導式教學）。"""


def utc_now() -> datetime:
    """取得當前 UTC 時間戳。

    Returns:
        datetime: 帶有 UTC timezone 的 datetime 物件。
    """
    return datetime.now(timezone.utc)


def new_id() -> str:
    """產生 UUID v4 字串，用於各 model 的預設 id。

    Returns:
        str: UUID v4 字串。
    """
    return str(uuid4())


class Event(BaseModel):
    """歷史事件。

    對應 ``events`` 資料表，儲存事件基本資料與 LLM 生成的背景資訊。

    Attributes:
        id: 事件 UUID。
        canonical_name: 事件正式名稱（用於查詢與顯示）。
        description: 事件簡述。
        century: 所屬世紀（如 19 表示 19 世紀）。
        start_year: 事件起始年份。
        end_year: 事件結束年份。
        context: LLM 生成的事件歷史脈絡。
        source_summary: 來源摘要與 LLM provider metadata。
        created_by: 建立者識別（可選）。
        materials_locked_at: Admin 確認可供正式實驗使用的時間。
        created_at: 建立時間。
        updated_at: 最後更新時間。
    """

    id: str = Field(default_factory=new_id)
    canonical_name: str
    description: str | None = None
    century: int | None = None
    start_year: int | None = None
    end_year: int | None = None
    context: str | None = None
    source_summary: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None
    archived_at: datetime | None = None
    materials_locked_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class WikiSource(BaseModel):
    """Wikipedia 來源紀錄。

    對應 ``wiki_sources`` 資料表，儲存從 Wikipedia API 擷取的
    事件來源資料，支援 zh/en 雙語與 summary/full 兩種模式。

    Attributes:
        id: 來源 UUID。
        event_id: 關聯事件 ID。
        language: 語言代碼（``"zh"`` / ``"en"``）。
        title: Wikipedia 頁面標題。
        page_url: 頁面 URL。
        summary: 擷取的摘要文字。
        sections: 完整模式下的分段內容。
        provider: 來源提供者名稱（固定 ``"wikipedia"``）。
        fetch_mode: 擷取模式（``"summary"`` / ``"full"``）。
        fetch_status: 擷取結果狀態。
        raw_payload: 原始 API 回應（供除錯）。
        retrieved_at: 擷取時間。
    """

    id: str = Field(default_factory=new_id)
    event_id: str
    language: Literal["zh", "en"]
    title: str
    page_url: str | None = None
    summary: str | None = None
    sections: list[dict[str, Any]] = Field(default_factory=list)
    provider: str = "wikipedia"
    fetch_mode: Literal["summary", "full"] = "summary"
    fetch_status: Literal["success", "partial", "failed", "fallback"] = "success"
    raw_payload: dict[str, Any] | None = None
    retrieved_at: datetime = Field(default_factory=utc_now)


class KnowledgeChunk(BaseModel):
    """RAG 用知識片段。

    對應 ``knowledge_chunks`` 資料表，將 WikiSource 內容切分為
    較小片段，供 RAG pipeline 做 similarity 檢索。

    Attributes:
        id: 片段 UUID。
        event_id: 關聯事件 ID。
        wiki_source_id: 來源的 WikiSource ID（可選）。
        source: 來源名稱標示。
        source_url: 來源 URL。
        section_title: 所屬段落標題。
        content: 片段文字內容。
        language: 語言代碼。
        char_count: 字元數。
        chunk_index: 片段在來源中的順序索引。
        metadata: 額外的 metadata。
        created_at: 建立時間。
    """

    id: str = Field(default_factory=new_id)
    event_id: str
    wiki_source_id: str | None = None
    source: str
    source_url: str | None = None
    section_title: str | None = None
    content: str
    language: str | None = None
    char_count: int | None = None
    chunk_index: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ExperimentCondition(BaseModel):
    """2x2 實驗條件設定。

    對應 ``experiment_conditions`` 資料表，定義 EBL 與 AI role-play
    的開關組合，決定 AI 回覆模式與教學策略。

    Attributes:
        id: 條件 UUID。
        condition_key: 條件鍵值（四種 2x2 組合之一）。
        label: 人類可讀的條件標籤。
        ebl_enabled: 是否啟用 Error-Based Learning。
        roleplay_enabled: 是否啟用 AI historical persona role-play。
        agent_mode: AI 代理模式（``"generic"`` / ``"persona"``）。
        response_policy: 回覆策略（``"standard"`` / ``"scaffold"``）。
        description: 條件描述（中文）。
        active: 是否啟用此條件。
        created_at: 建立時間。
        updated_at: 最後更新時間。
    """

    id: str = Field(default_factory=new_id)
    condition_key: ConditionKey
    label: str
    ebl_enabled: bool = False
    roleplay_enabled: bool = False
    agent_mode: Literal["generic", "persona"] = "generic"
    response_policy: ResponsePolicy = "standard"
    description: str | None = None
    active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="before")
    @classmethod
    def upgrade_legacy_response_policy(cls, value: Any) -> Any:
        """Read existing ``direct`` rows as the approved Standard Chat policy."""
        if isinstance(value, dict) and value.get("response_policy") == "direct":
            return {**value, "response_policy": "standard"}
        return value

    @model_validator(mode="after")
    def validate_fixed_factor_matrix(self) -> "ExperimentCondition":
        """Keep each condition key bound to its canonical 2x2 behavior."""
        validate_condition_behavior(
            self.condition_key,
            ebl_enabled=self.ebl_enabled,
            roleplay_enabled=self.roleplay_enabled,
            agent_mode=self.agent_mode,
            response_policy=self.response_policy,
        )
        return self


class Participant(BaseModel):
    """研究受測者 registry。

    對應 ``participants`` 資料表。Supabase Auth user id 負責驗證請求；
    正式 Session 另凍結 participant id，避免日後帳號改綁改變舊資料歸屬。
    Participant record 管理顯示代號、condition 指派與研究端 metadata。

    Attributes:
        id: Participant UUID。
        code: 研究端可讀的受測者代號。
        auth_user_id: Supabase Auth user id 對應。
        display_name: 管理端顯示名稱。
        cohort: 實驗批次或群組。
        condition_list: 指派給受測者的 learner-visible condition code，陣列順序即執行順序。
        status: 受測者研究狀態。
        notes: 管理端備註。
        metadata: 彈性 metadata。
        created_at: 建立時間。
        updated_at: 最後更新時間。
    """

    id: str = Field(default_factory=new_id)
    code: str
    auth_user_id: str | None = None
    display_name: str | None = None
    cohort: str | None = None
    condition_list: list[str] = Field(default_factory=list)
    status: Literal["active", "completed", "excluded", "archived"] = "active"
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ExperimentSession(BaseModel):
    """實驗 session。

    對應 ``experiment_sessions`` 資料表，追蹤 learner 在
    特定事件 + 條件組合下的實驗進度。

    Attributes:
        id: Session UUID。
        condition_id: 關聯的 ExperimentCondition ID。
        condition_key_snapshot: 建立時的 condition_key 快照。
        user_id: Supabase Auth 使用者識別。
        participant_id: Session 建立時凍結的受測者 registry 識別；Admin test 為空。
        event_id: 關聯事件 ID。
        is_admin_test: 是否由 Admin 測試模式建立，不得混入正式研究匯出。
        status: Session 進度狀態。
        created_at: 建立時間。
        updated_at: 最後更新時間。
    """

    id: str = Field(default_factory=new_id)
    condition_id: str
    condition_key_snapshot: ConditionKey
    user_id: str | None = None
    participant_id: str | None = None
    event_id: str
    is_admin_test: bool = False
    status: Literal[
        "initialized",
        "task_submitted",
        "conversation_started",
        "completed",
        "archived",
    ] = "initialized"
    timer_started_at: datetime | None = None
    timer_ends_at: datetime | None = None
    completed_at: datetime | None = None
    completion_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class EventTask(BaseModel):
    """事件學習任務。

    對應 ``event_tasks`` 資料表，儲存 LLM 生成或教師手動編輯的
    Error-Elicitation Task 內容與判定結構，作為後續對話的學習起點。

    Attributes:
        id: Task UUID。
        event_id: 關聯事件 ID。
        title: Task 標題。
        story_text: 舊版原始文本欄位；新版完整題目只使用 full_text 欄位。
        error_elicitation_task_full_text: 共用脈絡與全部題目敘述，以 ``{{blank:qNN}}`` 標記作答區域。
        evaluation_payload: 評量結構，包含 rubric 與 questions 題目定義。
        revision_state: 修訂狀態（LLM 生成 / 教師修改 / 手動）。
        created_at: 建立時間。
        updated_at: 最後更新時間。
    """

    id: str = Field(default_factory=new_id)
    event_id: str
    title: str | None = None
    story_text: str = ""
    error_elicitation_task_full_text: str
    evaluation_payload: dict[str, Any] = Field(default_factory=dict)
    revision_state: Literal["llm_generated", "teacher_modified", "manual"] = "llm_generated"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TaskAttempt(BaseModel):
    """Learner 的 task 作答紀錄。

    對應 ``task_attempts`` 資料表，記錄 learner 的作答內容
    與 backend 客觀答案判定、LLM 理由診斷的合併結果。

    Attributes:
        id: Attempt UUID。
        task_id: 關聯 Task ID。
        event_id: 關聯事件 ID。
        session_id: 關聯 Session ID。
        user_id: 受測者識別。
        status: 作答狀態（``"in_progress"`` / ``"submitted"``）。
        response_payload: Learner 的作答內容（JSON）。
        judgement_payload: LLM 自動判斷結果（JSON）。
        submitted_at: 提交時間。
        created_at: 建立時間。
        updated_at: 最後更新時間。
    """

    id: str = Field(default_factory=new_id)
    task_id: str
    event_id: str
    session_id: str
    user_id: str | None = None
    status: Literal["in_progress", "processing", "submitted", "failed"] = "in_progress"
    response_payload: dict[str, Any] = Field(default_factory=dict)
    judgement_payload: dict[str, Any] = Field(default_factory=dict)
    submitted_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Persona(BaseModel):
    """歷史人物角色（AI persona）。

    對應 ``personas`` 資料表，儲存 LLM 生成或手動建立的
    歷史人物資料，用於 role-play 條件下的 AI 回覆。

    Attributes:
        id: Persona UUID。
        event_id: 關聯事件 ID。
        name: 角色中文名稱。
        english_name: 角色英文名稱。
        role: 角色在事件中的身份。
        biography: 角色簡傳。
        expertise_areas: 專業領域清單。
        sources: 角色資料來源引用。
        prompt_profile: 供 prompt 組裝的角色 profile（含 speaking_style 等）。
        avatar_url: 角色頭像 URL。
        active: 是否啟用。
        archived_at: 封存時間；封存後仍保留既有研究資料關聯。
        sort_order: 排序順序。
        revision_state: 修訂狀態。
        created_at: 建立時間。
        updated_at: 最後更新時間。
    """

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=new_id)
    event_id: str
    name: str
    english_name: str | None = None
    role: str | None = None
    biography: str | None = None
    expertise_areas: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    prompt_profile: dict[str, Any] = Field(default_factory=dict)
    avatar_url: str | None = None
    active: bool = True
    archived_at: datetime | None = None
    sort_order: int = 0
    revision_state: Literal["llm_generated", "teacher_modified", "manual"] = "llm_generated"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("prompt_profile", mode="before")
    @classmethod
    def validate_prompt_contract(cls, value: Any) -> dict[str, Any]:
        """Normalize legacy profiles into the current persona prompt contract."""
        return normalize_persona_prompt_profile(value)


class Conversation(BaseModel):
    """聊天對話。

    對應 ``conversations`` 資料表，代表 learner 與 AI 之間
    的一次完整對話 session。

    Attributes:
        id: Conversation UUID。
        event_id: 關聯事件 ID。
        task_attempt_id: 觸發此對話的 TaskAttempt ID。
        session_id: 關聯 ExperimentSession ID。
        user_id: 受測者識別。
        status: 對話狀態（``"active"`` / ``"archived"``）。
        started_at: 對話開始時間。
        archived_at: 封存時間。
        created_at: 建立時間。
        updated_at: 最後更新時間。
    """

    id: str = Field(default_factory=new_id)
    event_id: str
    task_attempt_id: str
    session_id: str
    user_id: str | None = None
    status: Literal["active", "archived"] = "active"
    started_at: datetime = Field(default_factory=utc_now)
    archived_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Annotation(BaseModel):
    """聊天回覆中的歷史標注。

    LLM 在回覆中標記的關鍵歷史詞彙或概念，附帶簡要說明。

    Attributes:
        text: 被標注的文字。
        explanation: 標注的解釋說明。
    """

    text: str
    explanation: str


class RagSource(BaseModel):
    """RAG 檢索結果來源。

    聊天回覆中使用的知識片段來源資訊，供前端顯示引用來源。

    Attributes:
        source: 來源名稱。
        section_title: 來源段落標題。
        content: 檢索到的片段內容。
    """

    source: str = "unknown"
    section_title: str = "Source"
    content: str


class RelatedEvent(BaseModel):
    """與當前事件相關的其他歷史事件。

    LLM 在回覆中提及的關聯事件，可選擇性標記為可探索。

    Attributes:
        event_name: 關聯事件名稱。
        event_year: 關聯事件年份。
        event_id: 若系統中已存在該事件，提供其 ID。
        relevance_reason: 關聯原因說明。
        is_explorable: 前端是否可導向該事件。
    """

    event_name: str
    event_year: int | None = None
    event_id: str | None = None
    relevance_reason: str
    is_explorable: bool = False


class ChatMessage(BaseModel):
    """聊天訊息。

    對應 ``messages`` 資料表，記錄 learner 與 AI 之間的
    每一則對話訊息，含標注與 RAG 來源。

    Attributes:
        id: 訊息 UUID。
        conversation_id: 所屬 Conversation ID。
        persona_id: 發言 Persona ID（僅 persona 類型適用）。
        speaker_type: 發言者角色。
        speaker_name: 發言者顯示名稱。
        sequence_index: 訊息在對話中的排序索引。
        content: 訊息文字內容。
        annotations: 歷史標注清單。
        rag_sources: RAG 來源清單。
        metadata: 額外 metadata（如 provider、model 等）。
        client_request_id: 前端送出回合的穩定識別碼，用於防止重複建立。
        operation_status: learner 回合的生成狀態；AI 訊息通常為 None。
        created_at: 建立時間。
    """

    id: str = Field(default_factory=new_id)
    conversation_id: str
    persona_id: str | None = None
    speaker_type: SpeakerType
    speaker_name: str
    sequence_index: int = 0
    content: str
    annotations: list[Annotation] = Field(default_factory=list)
    rag_sources: list[RagSource] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    client_request_id: str | None = None
    operation_status: ChatOperationStatus | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ResearchLog(BaseModel):
    """流程行為紀錄。

    對應 ``research_logs`` 資料表，記錄 admin 操作、
    task 建立/更新等系統行為，供研究分析使用。

    Attributes:
        id: 紀錄 UUID。
        user_id: 操作者識別。
        session_id: 關聯 Session ID。
        event_id: 關聯事件 ID。
        task_id: 關聯 Task ID。
        attempt_id: 關聯 Attempt ID。
        conversation_id: 關聯 Conversation ID。
        message_id: 關聯 Message ID。
        action_type: 行為類型字串（如 ``"event_updated"``）。
        payload: 行為詳細資料（JSON）。
        created_at: 建立時間。
    """

    id: str = Field(default_factory=new_id)
    user_id: str | None = None
    session_id: str | None = None
    event_id: str | None = None
    task_id: str | None = None
    attempt_id: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None
    action_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
