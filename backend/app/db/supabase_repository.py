"""Supabase (PostgREST) repository implementation.

本模組透過 httpx 直接呼叫 Supabase PostgREST API 實作
RepositoryProtocol，用於 production 與 staging 環境。
Service 層不直接依賴此實作，而是透過 RepositoryProtocol
進行操作，使測試可替換為 InMemoryRepository。

所有 CRUD 操作皆使用 PostgREST 的 RESTful 語意:
    - GET    → 查詢（select）
    - POST   → 新增 / upsert
    - PATCH  → 部分更新
    - DELETE → 刪除
"""

from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from app.core.experiment_conditions import condition_sort_index
from app.crud.protocols import RepositoryProtocol
from app.models.domain import (
    ChatMessage,
    Conversation,
    Event,
    EventTask,
    ExperimentCondition,
    ExperimentSession,
    KnowledgeChunk,
    Participant,
    Persona,
    ResearchLog,
    TaskAttempt,
    WikiSource,
)


ModelT = TypeVar("ModelT", bound=BaseModel)


class SupabaseRepository(RepositoryProtocol):
    """PostgREST-backed repository.

    透過 httpx.Client 與 Supabase PostgREST API 通訊，
    使用 service_role_key 進行身份驗證以繞過 RLS。
    Service 層透過 RepositoryProtocol 與此實作互動，
    確保測試可無痛切換到 InMemoryRepository。

    Attributes:
        rest_url: PostgREST API 的完整 base URL。
        client: 預設帶有認證標頭的 httpx.Client 實例。
    """

    def __init__(self, supabase_url: str, service_role_key: str) -> None:
        """初始化 PostgREST client。

        Args:
            supabase_url: Supabase 專案 URL（如 ``https://xxx.supabase.co``）。
            service_role_key: Supabase service role API key，
                用於繞過 Row Level Security。
        """
        self.rest_url = f"{supabase_url.rstrip('/')}/rest/v1"
        self.client = httpx.Client(
            base_url=self.rest_url,
            headers={
                "apikey": service_role_key,
                "authorization": f"Bearer {service_role_key}",
                "content-type": "application/json",
            },
            timeout=15.0,
        )

    # ── Internal helpers ───────────────────────────────────────

    def _request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        json: Any | None = None,
        prefer: str | None = None,
    ) -> Any:
        """執行 PostgREST HTTP 請求。

        Args:
            method: HTTP method（GET / POST / PATCH / DELETE）。
            table: 目標資料表名稱。
            params: URL query parameters（PostgREST 篩選語法）。
            json: 請求 body（JSON）。
            prefer: PostgREST Prefer header 值。

        Returns:
            Any: 解析後的 JSON 回應，或 None（無 body 時）。

        Raises:
            httpx.HTTPStatusError: HTTP 回應非 2xx 時。
        """
        headers = {"Prefer": prefer} if prefer else None
        response = self.client.request(
            method,
            f"/{table}",
            params=params,
            json=json,
            headers=headers,
        )
        response.raise_for_status()
        if not response.content:
            return None
        return response.json()

    @staticmethod
    def _payload(model: BaseModel) -> dict[str, Any]:
        """將 Pydantic model 轉為 JSON-serializable dict。

        Args:
            model: 任意 Pydantic BaseModel 實例。

        Returns:
            dict[str, Any]: JSON 模式的 dict。
        """
        return model.model_dump(mode="json", exclude_none=False)

    def _upsert(self, table: str, model: ModelT, *, conflict: str = "id") -> ModelT:
        """Upsert 一筆紀錄（衝突時合併更新）。

        Args:
            table: 目標資料表名稱。
            model: 要 upsert 的 Pydantic model 實例。
            conflict: 衝突偵測用的欄位名稱，預設 ``"id"``。

        Returns:
            ModelT: 從 DB 回傳的完整紀錄（含 DB 端計算欄位）。
        """
        data = self._request(
            "POST",
            table,
            params={"on_conflict": conflict},
            json=self._payload(model),
            prefer="resolution=merge-duplicates,return=representation",
        )
        return type(model)(**data[0])

    def _patch(self, table: str, model_cls: type[ModelT], item_id: str, payload: dict[str, Any]) -> ModelT | None:
        """依 ID 部分更新一筆紀錄。

        Args:
            table: 目標資料表名稱。
            model_cls: 回傳值的 Pydantic model 類別。
            item_id: 目標紀錄的 UUID 字串。
            payload: 要更新的欄位與值。

        Returns:
            ModelT | None: 更新後的紀錄，或 None（紀錄不存在時）。
        """
        data = self._request(
            "PATCH",
            table,
            params={"id": f"eq.{item_id}"},
            json=payload,
            prefer="return=representation",
        )
        return model_cls(**data[0]) if data else None

    def _select_one(self, table: str, model_cls: type[ModelT], params: dict[str, str]) -> ModelT | None:
        """查詢單一紀錄（limit=1）。

        Args:
            table: 目標資料表名稱。
            model_cls: 回傳值的 Pydantic model 類別。
            params: PostgREST 篩選參數。

        Returns:
            ModelT | None: 第一筆匹配紀錄，或 None。
        """
        data = self._request("GET", table, params={**params, "limit": "1"})
        return model_cls(**data[0]) if data else None

    def _select_many(self, table: str, model_cls: type[ModelT], params: dict[str, str] | None = None) -> list[ModelT]:
        """查詢多筆紀錄。

        Args:
            table: 目標資料表名稱。
            model_cls: 回傳值的 Pydantic model 類別。
            params: PostgREST 篩選與排序參數。

        Returns:
            list[ModelT]: 匹配紀錄清單。
        """
        data = self._request("GET", table, params=params or {})
        return [model_cls(**item) for item in data]

    # ── Event ──────────────────────────────────────────────────

    def find_event_by_name(self, event_name: str) -> Event | None:
        """依事件名稱查詢（case-insensitive ilike）。

        Args:
            event_name: 事件名稱字串。

        Returns:
            Event | None: 匹配的事件，或 None。
        """
        return self._select_one(
            "events",
            Event,
            {"canonical_name": f"ilike.{event_name.strip()}"},
        )

    def save_event(self, event: Event) -> Event:
        """Upsert 事件。

        Args:
            event: Event 實例。

        Returns:
            Event: 儲存後的事件。
        """
        return self._upsert("events", event)

    def list_events(self) -> list[Event]:
        """列出所有事件，依建立時間倒序。

        Returns:
            list[Event]: 事件清單。
        """
        return self._select_many("events", Event, {"order": "created_at.desc"})

    def get_event(self, event_id: str) -> Event | None:
        """依 ID 取得事件。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            Event | None: 匹配的事件，或 None。
        """
        return self._select_one("events", Event, {"id": f"eq.{event_id}"})

    def delete_event(self, event_id: str) -> bool:
        """刪除事件（DB cascade 處理關聯資料）。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            bool: 是否成功刪除。
        """
        data = self._request(
            "DELETE",
            "events",
            params={"id": f"eq.{event_id}"},
            prefer="return=representation",
        )
        return bool(data)

    # ── WikiSource ─────────────────────────────────────────────

    def save_wiki_source(self, source: WikiSource) -> WikiSource:
        """Upsert Wikipedia 來源（composite key: event_id + provider + language + fetch_mode）。

        Args:
            source: WikiSource 實例。

        Returns:
            WikiSource: 儲存後的來源。
        """
        return self._upsert("wiki_sources", source, conflict="event_id,provider,language,fetch_mode")

    def list_wiki_sources(self, event_id: str) -> list[WikiSource]:
        """列出指定事件的 Wikipedia 來源，依擷取時間排序。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            list[WikiSource]: 來源清單。
        """
        return self._select_many("wiki_sources", WikiSource, {"event_id": f"eq.{event_id}", "order": "retrieved_at.asc"})

    # ── KnowledgeChunk ─────────────────────────────────────────

    def save_knowledge_chunk(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        """Upsert RAG 知識片段。

        Args:
            chunk: KnowledgeChunk 實例。

        Returns:
            KnowledgeChunk: 儲存後的片段。
        """
        return self._upsert("knowledge_chunks", chunk)

    def list_knowledge_chunks(self, event_id: str) -> list[KnowledgeChunk]:
        """列出指定事件的知識片段，依 chunk_index 排序。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            list[KnowledgeChunk]: 片段清單。
        """
        return self._select_many("knowledge_chunks", KnowledgeChunk, {"event_id": f"eq.{event_id}", "order": "chunk_index.asc"})

    # ── ExperimentCondition ────────────────────────────────────

    def list_conditions(self, active_only: bool = True) -> list[ExperimentCondition]:
        """列出實驗條件，依 learner-facing 01–04 代號排序。

        Args:
            active_only: 若為 True，僅回傳 active=True 的條件。

        Returns:
            list[ExperimentCondition]: 條件清單。
        """
        params = {}
        if active_only:
            params["active"] = "eq.true"
        conditions = self._select_many("experiment_conditions", ExperimentCondition, params)
        return sorted(conditions, key=lambda item: condition_sort_index(item.condition_key))

    def get_condition_by_key(self, condition_key: str) -> ExperimentCondition | None:
        """依 condition_key 取得條件。

        Args:
            condition_key: 條件鍵值字串。

        Returns:
            ExperimentCondition | None: 匹配的條件，或 None。
        """
        return self._select_one("experiment_conditions", ExperimentCondition, {"condition_key": f"eq.{condition_key}"})

    def get_condition(self, condition_id: str) -> ExperimentCondition | None:
        """依 ID 取得條件。

        Args:
            condition_id: 條件 UUID 字串。

        Returns:
            ExperimentCondition | None: 匹配的條件，或 None。
        """
        return self._select_one("experiment_conditions", ExperimentCondition, {"id": f"eq.{condition_id}"})

    def save_condition(self, condition: ExperimentCondition) -> ExperimentCondition:
        """Upsert 實驗條件。

        Args:
            condition: ExperimentCondition 實例。

        Returns:
            ExperimentCondition: 儲存後的條件。
        """
        return self._upsert("experiment_conditions", condition)

    # ── ExperimentSession ──────────────────────────────────────

    def save_session(self, session: ExperimentSession) -> ExperimentSession:
        """Upsert 實驗 session。

        Args:
            session: ExperimentSession 實例。

        Returns:
            ExperimentSession: 儲存後的 session。
        """
        return self._upsert("experiment_sessions", session)

    def get_session(self, session_id: str) -> ExperimentSession | None:
        """依 ID 取得 session。

        Args:
            session_id: Session UUID 字串。

        Returns:
            ExperimentSession | None: 匹配的 session，或 None。
        """
        return self._select_one("experiment_sessions", ExperimentSession, {"id": f"eq.{session_id}"})

    def list_sessions(self) -> list[ExperimentSession]:
        """列出所有 session，依建立時間倒序。

        Returns:
            list[ExperimentSession]: Session 清單。
        """
        return self._select_many("experiment_sessions", ExperimentSession, {"order": "created_at.desc"})

    def list_sessions_for_user(self, user_id: str) -> list[ExperimentSession]:
        """列出指定使用者的 session，依更新時間倒序。

        Args:
            user_id: 使用者識別字串。

        Returns:
            list[ExperimentSession]: Session 清單。
        """
        return self._select_many(
            "experiment_sessions",
            ExperimentSession,
            {"user_id": f"eq.{user_id}", "order": "updated_at.desc"},
        )

    # ── Participant ───────────────────────────────────────────

    def list_participants(self) -> list[Participant]:
        """列出所有受測者，依 code 排序。"""
        return self._select_many("participants", Participant, {"order": "code.asc"})

    def get_participant(self, participant_id: str) -> Participant | None:
        """依 ID 取得受測者。"""
        return self._select_one("participants", Participant, {"id": f"eq.{participant_id}"})

    def get_participant_by_auth_user(self, auth_user_id: str) -> Participant | None:
        """依 Supabase Auth user id 取得 participant。"""
        return self._select_one("participants", Participant, {"auth_user_id": f"eq.{auth_user_id}"})

    def save_participant(self, participant: Participant) -> Participant:
        """Upsert participant。"""
        return self._upsert("participants", participant)

    # ── EventTask ──────────────────────────────────────────────

    def save_event_task(self, task: EventTask) -> EventTask:
        """Upsert task。

        Args:
            task: EventTask 實例。

        Returns:
            EventTask: 儲存後的 task。
        """
        return self._upsert("event_tasks", task)

    def get_event_task(self, task_id: str) -> EventTask | None:
        """依 ID 取得 task。

        Args:
            task_id: Task UUID 字串。

        Returns:
            EventTask | None: 匹配的 task，或 None。
        """
        return self._select_one("event_tasks", EventTask, {"id": f"eq.{task_id}"})

    def get_latest_event_task(self, event_id: str) -> EventTask | None:
        """取得指定事件的最新 task。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            EventTask | None: 最新的 task，或 None。
        """
        return self._select_one(
            "event_tasks",
            EventTask,
            {"event_id": f"eq.{event_id}", "order": "created_at.desc"},
        )

    def list_event_tasks(self, event_id: str) -> list[EventTask]:
        """列出指定事件的所有 task，依建立時間倒序。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            list[EventTask]: Task 清單。
        """
        return self._select_many("event_tasks", EventTask, {"event_id": f"eq.{event_id}", "order": "created_at.desc"})

    # ── TaskAttempt ─────────────────────────────────────────────

    def save_task_attempt(self, attempt: TaskAttempt) -> TaskAttempt:
        """Upsert task attempt。

        Args:
            attempt: TaskAttempt 實例。

        Returns:
            TaskAttempt: 儲存後的 attempt。
        """
        return self._upsert("task_attempts", attempt)

    def get_task_attempt(self, attempt_id: str) -> TaskAttempt | None:
        """依 ID 取得 task attempt。

        Args:
            attempt_id: Attempt UUID 字串。

        Returns:
            TaskAttempt | None: 匹配的 attempt，或 None。
        """
        return self._select_one("task_attempts", TaskAttempt, {"id": f"eq.{attempt_id}"})

    def get_task_attempt_for_session(self, session_id: str, task_id: str | None = None) -> TaskAttempt | None:
        """取得指定 session 的最新 attempt。

        Args:
            session_id: Session UUID 字串。
            task_id: 可選的 Task UUID 字串。

        Returns:
            TaskAttempt | None: 最新的 attempt，或 None。
        """
        params = {
            "session_id": f"eq.{session_id}",
            "order": "updated_at.desc",
        }
        if task_id:
            params["task_id"] = f"eq.{task_id}"
        return self._select_one("task_attempts", TaskAttempt, params)

    # ── Persona ────────────────────────────────────────────────

    def save_persona(self, persona: Persona) -> Persona:
        """Upsert persona。

        Args:
            persona: Persona 實例。

        Returns:
            Persona: 儲存後的 persona。
        """
        return self._upsert("personas", persona)

    def get_persona(self, persona_id: str) -> Persona | None:
        """依 ID 取得 persona。

        Args:
            persona_id: Persona UUID 字串。

        Returns:
            Persona | None: 匹配的 persona，或 None。
        """
        return self._select_one("personas", Persona, {"id": f"eq.{persona_id}"})

    def list_personas(self, event_id: str, active_only: bool = True) -> list[Persona]:
        """列出指定事件的 personas，依 sort_order 排序。

        Args:
            event_id: 事件 UUID 字串。
            active_only: 若為 True，僅回傳 active=True 的角色。

        Returns:
            list[Persona]: Persona 清單。
        """
        params = {"event_id": f"eq.{event_id}", "order": "sort_order.asc,created_at.asc"}
        if active_only:
            params["active"] = "eq.true"
        return self._select_many("personas", Persona, params)

    def delete_persona(self, persona_id: str) -> bool:
        """軟刪除 persona（PATCH active=False）。

        Args:
            persona_id: Persona UUID 字串。

        Returns:
            bool: 是否成功軟刪除。
        """
        return self._patch("personas", Persona, persona_id, {"active": False}) is not None

    # ── Conversation ───────────────────────────────────────────

    def save_conversation(self, conversation: Conversation) -> Conversation:
        """Upsert conversation。

        Args:
            conversation: Conversation 實例。

        Returns:
            Conversation: 儲存後的 conversation。
        """
        return self._upsert("conversations", conversation)

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """依 ID 取得 conversation。

        Args:
            conversation_id: Conversation UUID 字串。

        Returns:
            Conversation | None: 匹配的 conversation，或 None。
        """
        return self._select_one("conversations", Conversation, {"id": f"eq.{conversation_id}"})

    def get_conversation_by_session(self, session_id: str) -> Conversation | None:
        """依 session_id 取得最新的 conversation。

        Args:
            session_id: Session UUID 字串。

        Returns:
            Conversation | None: 最新的 conversation，或 None。
        """
        return self._select_one(
            "conversations",
            Conversation,
            {"session_id": f"eq.{session_id}", "order": "updated_at.desc"},
        )

    # ── ChatMessage ────────────────────────────────────────────

    def next_message_sequence(self, conversation_id: str) -> int:
        """查詢目前最大 sequence_index 並回傳下一個可用值。

        Args:
            conversation_id: Conversation UUID 字串。

        Returns:
            int: 下一個 sequence_index。
        """
        data = self._request(
            "GET",
            "messages",
            params={
                "conversation_id": f"eq.{conversation_id}",
                "select": "sequence_index",
                "order": "sequence_index.desc",
                "limit": "1",
            },
        )
        return int(data[0]["sequence_index"]) + 1 if data else 0

    def add_message(self, message: ChatMessage) -> ChatMessage:
        """Upsert 一則訊息。

        Args:
            message: ChatMessage 實例。

        Returns:
            ChatMessage: 儲存後的訊息。
        """
        return self._upsert("messages", message)

    def list_messages(self, conversation_id: str) -> list[ChatMessage]:
        """列出指定 conversation 的訊息，依 sequence_index 排序。

        Args:
            conversation_id: Conversation UUID 字串。

        Returns:
            list[ChatMessage]: 訊息清單。
        """
        return self._select_many("messages", ChatMessage, {"conversation_id": f"eq.{conversation_id}", "order": "sequence_index.asc"})

    # ── ResearchLog ────────────────────────────────────────────

    def log_research(self, log: ResearchLog) -> ResearchLog:
        """Upsert 流程行為紀錄。

        Args:
            log: ResearchLog 實例。

        Returns:
            ResearchLog: 儲存後的紀錄。
        """
        return self._upsert("research_logs", log)

    def list_research_logs(self, limit: int = 200) -> list[ResearchLog]:
        """列出最近的流程行為紀錄，依建立時間倒序。

        Args:
            limit: 回傳筆數上限。

        Returns:
            list[ResearchLog]: 紀錄清單。
        """
        return self._select_many("research_logs", ResearchLog, {"order": "created_at.desc", "limit": str(limit)})

    # ── ViewCount ──────────────────────────────────────────────

    def increment_view_count(self) -> int:
        """V1 不在 Supabase 追蹤 view count，固定回傳 0。

        Returns:
            int: 固定回傳 0。
        """
        # View count is intentionally local-process only in V1 because it is not
        # part of the thesis experiment data model.
        return 0
