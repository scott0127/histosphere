"""Repository protocol definition.

本模組定義 ``RepositoryProtocol``，作為整個後端資料存取層的
抽象介面（structural subtyping）。所有 service 與 endpoint 皆
依賴此 Protocol，而非直接依賴 Supabase 或 in-memory 實作，
確保可在不同環境（測試 / 本地 / 雲端）替換實作。
"""

from typing import Protocol

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


class RepositoryProtocol(Protocol):
    """資料存取層抽象介面。

    透過 Python ``Protocol``（structural subtyping）定義所有
    CRUD 操作簽章，讓 ``InMemoryRepository`` 與
    ``SupabaseRepository`` 皆可無需繼承即滿足此型別。

    方法分組:
        - **Event**: 事件的 CRUD 與名稱查詢。
        - **WikiSource**: Wikipedia 來源的儲存與查詢。
        - **KnowledgeChunk**: RAG 用知識片段的儲存與查詢。
        - **ExperimentCondition**: 2x2 實驗條件的 CRUD。
        - **ExperimentSession**: 實驗 session 的 CRUD。
        - **EventTask**: 事件 task 的 CRUD 與最新 task 查詢。
        - **TaskAttempt**: Learner 作答紀錄的 CRUD。
        - **Persona**: 歷史人物角色的 CRUD。
        - **Conversation**: 對話的 CRUD。
        - **ChatMessage**: 訊息的新增與查詢。
        - **ResearchLog**: 流程行為紀錄。
        - **ViewCount**: 舊版相容計數器。
    """

    # ── Event ──────────────────────────────────────────────────

    def find_event_by_name(self, event_name: str, include_archived: bool = False) -> Event | None:
        """依事件名稱模糊查詢（case-insensitive）。

        Args:
            event_name: 事件名稱字串。

        Returns:
            Event | None: 匹配的事件，或 None。
        """
        ...

    def save_event(self, event: Event) -> Event:
        """新增或更新事件（upsert by id）。

        Args:
            event: 要儲存的 Event 實例。

        Returns:
            Event: 儲存後的 Event（含更新後的 updated_at）。
        """
        ...

    def list_events(self, include_archived: bool = False) -> list[Event]:
        """列出所有事件，依建立時間倒序。

        Returns:
            list[Event]: 事件清單。
        """
        ...

    def get_event(self, event_id: str) -> Event | None:
        """依 ID 取得單一事件。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            Event | None: 匹配的事件，或 None。
        """
        ...

    def archive_event(self, event_id: str) -> Event | None:
        """Soft archive an event without deleting related research data."""
        ...

    def restore_event(self, event_id: str) -> Event | None:
        """Restore a previously archived event."""
        ...

    # ── WikiSource ─────────────────────────────────────────────

    def save_wiki_source(self, source: WikiSource) -> WikiSource:
        """儲存 Wikipedia 來源（upsert by composite key）。

        Args:
            source: WikiSource 實例。

        Returns:
            WikiSource: 儲存後的來源。
        """
        ...

    def list_wiki_sources(self, event_id: str) -> list[WikiSource]:
        """列出指定事件的所有 Wikipedia 來源。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            list[WikiSource]: 來源清單。
        """
        ...

    # ── KnowledgeChunk ─────────────────────────────────────────

    def save_knowledge_chunk(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        """儲存 RAG 用的知識片段。

        Args:
            chunk: KnowledgeChunk 實例。

        Returns:
            KnowledgeChunk: 儲存後的片段。
        """
        ...

    def list_knowledge_chunks(self, event_id: str) -> list[KnowledgeChunk]:
        """列出指定事件的所有知識片段。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            list[KnowledgeChunk]: 片段清單，依 chunk_index 排序。
        """
        ...

    # ── ExperimentCondition ────────────────────────────────────

    def list_conditions(self, active_only: bool = True) -> list[ExperimentCondition]:
        """列出實驗條件，可選僅回傳啟用中的紀錄。

        Args:
            active_only: 若為 True，僅回傳 active=True 的條件。

        Returns:
            list[ExperimentCondition]: 條件清單，依 condition_key 排序。
        """
        ...

    def get_condition_by_key(self, condition_key: str) -> ExperimentCondition | None:
        """依 condition_key 取得單一條件。

        Args:
            condition_key: 條件鍵值（如 ``"ebl_roleplay"``）。

        Returns:
            ExperimentCondition | None: 匹配的條件，或 None。
        """
        ...

    def get_condition(self, condition_id: str) -> ExperimentCondition | None:
        """依 ID 取得單一條件。

        Args:
            condition_id: 條件 UUID 字串。

        Returns:
            ExperimentCondition | None: 匹配的條件，或 None。
        """
        ...

    def save_condition(self, condition: ExperimentCondition) -> ExperimentCondition:
        """新增或更新實驗條件（upsert by id）。

        Args:
            condition: ExperimentCondition 實例。

        Returns:
            ExperimentCondition: 儲存後的條件。
        """
        ...

    # ── ExperimentSession ──────────────────────────────────────

    def save_session(self, session: ExperimentSession) -> ExperimentSession:
        """新增或更新實驗 session（upsert by id）。

        Args:
            session: ExperimentSession 實例。

        Returns:
            ExperimentSession: 儲存後的 session。
        """
        ...

    def get_session(self, session_id: str) -> ExperimentSession | None:
        """依 ID 取得單一 session。

        Args:
            session_id: Session UUID 字串。

        Returns:
            ExperimentSession | None: 匹配的 session，或 None。
        """
        ...

    def list_sessions(self) -> list[ExperimentSession]:
        """列出所有 session，依建立時間倒序。

        Returns:
            list[ExperimentSession]: Session 清單。
        """
        ...

    def list_sessions_for_user(self, user_id: str) -> list[ExperimentSession]:
        """列出指定使用者的所有 session。

        Args:
            user_id: 使用者識別字串。

        Returns:
            list[ExperimentSession]: 該使用者的 session 清單，依更新時間倒序。
        """
        ...

    # ── Participant ───────────────────────────────────────────

    def list_participants(self) -> list[Participant]:
        """列出所有受測者，依 code 排序。

        Returns:
            list[Participant]: 受測者清單。
        """
        ...

    def get_participant(self, participant_id: str) -> Participant | None:
        """依 ID 取得單一受測者。

        Args:
            participant_id: Participant UUID 字串。

        Returns:
            Participant | None: 匹配的受測者，或 None。
        """
        ...

    def get_participant_by_auth_user(self, auth_user_id: str) -> Participant | None:
        """依 Supabase Auth user id 取得對應 participant。

        Args:
            auth_user_id: Supabase Auth user UUID 字串。

        Returns:
            Participant | None: 匹配的受測者，或 None。
        """
        ...

    def save_participant(self, participant: Participant) -> Participant:
        """新增或更新受測者。

        Args:
            participant: Participant 實例。

        Returns:
            Participant: 儲存後的受測者。
        """
        ...

    # ── EventTask ──────────────────────────────────────────────

    def save_event_task(self, task: EventTask) -> EventTask:
        """新增或更新 task（upsert by id）。

        Args:
            task: EventTask 實例。

        Returns:
            EventTask: 儲存後的 task。
        """
        ...

    def get_event_task(self, task_id: str) -> EventTask | None:
        """依 ID 取得單一 task。

        Args:
            task_id: Task UUID 字串。

        Returns:
            EventTask | None: 匹配的 task，或 None。
        """
        ...

    def get_latest_event_task(self, event_id: str) -> EventTask | None:
        """取得指定事件的最新 task。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            EventTask | None: 最新的 task，或 None。
        """
        ...

    def list_event_tasks(self, event_id: str) -> list[EventTask]:
        """列出指定事件的所有 task，依建立時間倒序。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            list[EventTask]: Task 清單。
        """
        ...

    # ── TaskAttempt ─────────────────────────────────────────────

    def save_task_attempt(self, attempt: TaskAttempt) -> TaskAttempt:
        """新增或更新 task attempt（upsert by id）。

        Args:
            attempt: TaskAttempt 實例。

        Returns:
            TaskAttempt: 儲存後的 attempt。
        """
        ...

    def get_task_attempt(self, attempt_id: str) -> TaskAttempt | None:
        """依 ID 取得單一 task attempt。

        Args:
            attempt_id: Attempt UUID 字串。

        Returns:
            TaskAttempt | None: 匹配的 attempt，或 None。
        """
        ...

    def get_task_attempt_for_session(self, session_id: str, task_id: str | None = None) -> TaskAttempt | None:
        """取得指定 session（可選搭配 task_id）的最新 attempt。

        Args:
            session_id: Session UUID 字串。
            task_id: 可選的 Task UUID 字串，用於進一步篩選。

        Returns:
            TaskAttempt | None: 最新的 attempt，或 None。
        """
        ...

    # ── Persona ────────────────────────────────────────────────

    def save_persona(self, persona: Persona) -> Persona:
        """新增或更新 persona（upsert by id）。

        Args:
            persona: Persona 實例。

        Returns:
            Persona: 儲存後的 persona。
        """
        ...

    def get_persona(self, persona_id: str) -> Persona | None:
        """依 ID 取得單一 persona。

        Args:
            persona_id: Persona UUID 字串。

        Returns:
            Persona | None: 匹配的 persona，或 None。
        """
        ...

    def list_personas(self, event_id: str, active_only: bool = True) -> list[Persona]:
        """列出指定事件的 personas。

        Args:
            event_id: 事件 UUID 字串。
            active_only: 若為 True，僅回傳 active=True 的角色。

        Returns:
            list[Persona]: Persona 清單，依 sort_order 與 created_at 排序。
        """
        ...

    def delete_persona(self, persona_id: str) -> bool:
        """軟刪除 persona（設定 active=False）。

        Args:
            persona_id: Persona UUID 字串。

        Returns:
            bool: 是否成功刪除。
        """
        ...

    # ── Conversation ───────────────────────────────────────────

    def save_conversation(self, conversation: Conversation) -> Conversation:
        """新增或更新 conversation（upsert by id）。

        Args:
            conversation: Conversation 實例。

        Returns:
            Conversation: 儲存後的 conversation。
        """
        ...

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """依 ID 取得單一 conversation。

        Args:
            conversation_id: Conversation UUID 字串。

        Returns:
            Conversation | None: 匹配的 conversation，或 None。
        """
        ...

    def get_conversation_by_session(self, session_id: str) -> Conversation | None:
        """依 session_id 取得最新的 conversation。

        Args:
            session_id: Session UUID 字串。

        Returns:
            Conversation | None: 最新的 conversation，或 None。
        """
        ...

    # ── ChatMessage ────────────────────────────────────────────

    def next_message_sequence(self, conversation_id: str) -> int:
        """取得下一個可用的 sequence_index。

        Args:
            conversation_id: Conversation UUID 字串。

        Returns:
            int: 下一個 sequence_index 數值。
        """
        ...

    def add_message(self, message: ChatMessage) -> ChatMessage:
        """新增或更新一則 conversation 訊息。

        Args:
            message: ChatMessage 實例（需含 conversation_id）。

        Returns:
            ChatMessage: 儲存後的訊息。

        Raises:
            ValueError: 當 message.conversation_id 為空時。
        """
        ...

    def get_message(self, message_id: str) -> ChatMessage | None:
        """依訊息 ID 取得單一訊息。"""
        ...

    def get_learner_message_by_request(
        self,
        conversation_id: str,
        client_request_id: str,
    ) -> ChatMessage | None:
        """依前端回合識別碼取得 learner 訊息。"""
        ...

    def get_active_chat_operation(self, conversation_id: str) -> ChatMessage | None:
        """取得對話中唯一一筆尚在生成的 learner 回合。"""
        ...

    def list_active_chat_operations(self) -> list[ChatMessage]:
        """列出後端程序啟動時仍停在生成中的 learner 回合。"""
        ...

    def list_messages(self, conversation_id: str) -> list[ChatMessage]:
        """列出指定 conversation 的所有訊息，依 sequence_index 排序。

        Args:
            conversation_id: Conversation UUID 字串。

        Returns:
            list[ChatMessage]: 訊息清單。
        """
        ...

    # ── ResearchLog ────────────────────────────────────────────

    def log_research(self, log: ResearchLog) -> ResearchLog:
        """新增一筆流程行為紀錄。

        Args:
            log: ResearchLog 實例。

        Returns:
            ResearchLog: 儲存後的紀錄。
        """
        ...

    def list_research_logs(self, limit: int = 200) -> list[ResearchLog]:
        """列出最近的流程行為紀錄。

        Args:
            limit: 回傳筆數上限，預設 200。

        Returns:
            list[ResearchLog]: 紀錄清單，依建立時間倒序。
        """
        ...

    def list_research_logs_for_session(self, session_id: str) -> list[ResearchLog]:
        """列出指定 Session 的完整研究紀錄，依時間正序。"""
        ...
