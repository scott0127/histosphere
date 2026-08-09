"""In-memory repository implementation.

本模組提供純 Python dict 為後端的 RepositoryProtocol 實作，
主要用於單元測試與無 Supabase 的本地開發。所有資料僅存活
於 process 生命週期內，重啟即清空。

初始化時會自動 seed 四組 2x2 實驗條件。
"""

from app.core.experiment_conditions import EXPERIMENT_CONDITION_DEFINITIONS, condition_sort_index
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
    utc_now,
)


class InMemoryRepository(RepositoryProtocol):
    """純 Python dict 實作的 RepositoryProtocol。

    所有資料以 ``dict[str, Model]`` 形式存放在記憶體中，
    僅適用於測試與本地開發環境。初始化時會呼叫
    ``_seed_conditions()`` 建立四組預設 2x2 實驗條件。

    Attributes:
        events: 事件存儲，key 為 event_id。
        event_names: 正規化事件名稱到 event_id 的反向索引。
        wiki_sources: Wikipedia 來源存儲。
        knowledge_chunks: RAG 知識片段存儲。
        conditions: 實驗條件存儲。
        condition_keys: condition_key 到 condition_id 的反向索引。
        sessions: 實驗 session 存儲。
        event_tasks: Task 存儲。
        task_attempts: Learner 作答紀錄存儲。
        personas: 歷史人物角色存儲。
        conversations: 對話存儲。
        messages: 對話訊息存儲，key 為 conversation_id。
        research_logs: 流程行為紀錄存儲。
    """

    def __init__(self) -> None:
        """初始化所有存儲 dict 並 seed 預設實驗條件。"""
        self.events: dict[str, Event] = {}
        self.event_names: dict[str, str] = {}
        self.wiki_sources: dict[str, WikiSource] = {}
        self.knowledge_chunks: dict[str, KnowledgeChunk] = {}
        self.conditions: dict[str, ExperimentCondition] = {}
        self.condition_keys: dict[str, str] = {}
        self.sessions: dict[str, ExperimentSession] = {}
        self.participants: dict[str, Participant] = {}
        self.event_tasks: dict[str, EventTask] = {}
        self.task_attempts: dict[str, TaskAttempt] = {}
        self.personas: dict[str, Persona] = {}
        self.conversations: dict[str, Conversation] = {}
        self.messages: dict[str, list[ChatMessage]] = {}
        self.research_logs: dict[str, ResearchLog] = {}
        self._seed_conditions()

    @staticmethod
    def normalize_event_name(event_name: str) -> str:
        """將事件名稱正規化為小寫並壓縮空白，供名稱比對使用。

        Args:
            event_name: 原始事件名稱。

        Returns:
            str: 正規化後的名稱字串。
        """
        return " ".join(event_name.strip().lower().split())

    def _seed_conditions(self) -> None:
        """建立四組 2x2 實驗條件預設值。

        條件組合:
            - ``no_ebl_no_roleplay``: 無 EBL + 無 role-play（generic / direct）。
            - ``ebl_no_roleplay``: 有 EBL + 無 role-play（generic / scaffold）。
            - ``no_ebl_roleplay``: 無 EBL + 有 role-play（persona / direct）。
            - ``ebl_roleplay``: 有 EBL + 有 role-play（persona / scaffold）。
        """
        seed = [
            ExperimentCondition(
                condition_key=definition.condition_key,
                label=definition.default_label,
                ebl_enabled=definition.ebl_enabled,
                roleplay_enabled=definition.roleplay_enabled,
                agent_mode=definition.agent_mode,
                response_policy=definition.response_policy,
                description=definition.default_description,
            )
            for definition in EXPERIMENT_CONDITION_DEFINITIONS
        ]
        for condition in seed:
            self.save_condition(condition)

    def find_event_by_name(self, event_name: str, include_archived: bool = False) -> Event | None:
        """依正規化名稱查詢事件。

        Args:
            event_name: 原始事件名稱。

        Returns:
            Event | None: 匹配的事件，或 None。
        """
        event_id = self.event_names.get(self.normalize_event_name(event_name))
        event = self.events.get(event_id) if event_id else None
        if event and event.archived_at and not include_archived:
            return None
        return event

    def save_event(self, event: Event) -> Event:
        """儲存事件並更新名稱索引。

        Args:
            event: 要儲存的 Event 實例。

        Returns:
            Event: 儲存後的 Event（updated_at 已更新）。
        """
        event.updated_at = utc_now()
        self.events[event.id] = event
        self.event_names[self.normalize_event_name(event.canonical_name)] = event.id
        return event

    def list_events(self, include_archived: bool = False) -> list[Event]:
        """列出所有事件，依建立時間倒序。

        Returns:
            list[Event]: 事件清單。
        """
        events = list(self.events.values())
        if not include_archived:
            events = [event for event in events if event.archived_at is None]
        return sorted(events, key=lambda item: item.created_at, reverse=True)

    def get_event(self, event_id: str) -> Event | None:
        """依 ID 取得事件。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            Event | None: 匹配的事件，或 None。
        """
        return self.events.get(event_id)

    def archive_event(self, event_id: str) -> Event | None:
        """Soft archive an event while preserving every related record."""
        event = self.events.get(event_id)
        if not event:
            return None
        event.archived_at = utc_now()
        return self.save_event(event)

    def restore_event(self, event_id: str) -> Event | None:
        """Restore an archived event."""
        event = self.events.get(event_id)
        if not event:
            return None
        event.archived_at = None
        return self.save_event(event)

    def save_wiki_source(self, source: WikiSource) -> WikiSource:
        """儲存 Wikipedia 來源。

        Args:
            source: WikiSource 實例。

        Returns:
            WikiSource: 儲存後的來源。
        """
        self.wiki_sources[source.id] = source
        return source

    def list_wiki_sources(self, event_id: str) -> list[WikiSource]:
        """列出指定事件的 Wikipedia 來源。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            list[WikiSource]: 來源清單。
        """
        return [source for source in self.wiki_sources.values() if source.event_id == event_id]

    def save_knowledge_chunk(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        """儲存 RAG 知識片段。

        Args:
            chunk: KnowledgeChunk 實例。

        Returns:
            KnowledgeChunk: 儲存後的片段。
        """
        self.knowledge_chunks[chunk.id] = chunk
        return chunk

    def list_knowledge_chunks(self, event_id: str) -> list[KnowledgeChunk]:
        """列出指定事件的知識片段。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            list[KnowledgeChunk]: 片段清單。
        """
        return [chunk for chunk in self.knowledge_chunks.values() if chunk.event_id == event_id]

    def list_conditions(self, active_only: bool = True) -> list[ExperimentCondition]:
        """列出實驗條件，依 learner-facing 01–04 代號排序。

        Args:
            active_only: 若為 True，僅回傳 active=True 的條件。

        Returns:
            list[ExperimentCondition]: 條件清單。
        """
        conditions = list(self.conditions.values())
        if active_only:
            conditions = [condition for condition in conditions if condition.active]
        return sorted(conditions, key=lambda item: condition_sort_index(item.condition_key))

    def get_condition_by_key(self, condition_key: str) -> ExperimentCondition | None:
        """依 condition_key 取得條件。

        Args:
            condition_key: 條件鍵值字串。

        Returns:
            ExperimentCondition | None: 匹配的條件，或 None。
        """
        condition_id = self.condition_keys.get(condition_key)
        return self.conditions.get(condition_id) if condition_id else None

    def get_condition(self, condition_id: str) -> ExperimentCondition | None:
        """依 ID 取得條件。

        Args:
            condition_id: 條件 UUID 字串。

        Returns:
            ExperimentCondition | None: 匹配的條件，或 None。
        """
        return self.conditions.get(condition_id)

    def save_condition(self, condition: ExperimentCondition) -> ExperimentCondition:
        """儲存條件並更新 key 索引。

        Args:
            condition: ExperimentCondition 實例。

        Returns:
            ExperimentCondition: 儲存後的條件。
        """
        condition.updated_at = utc_now()
        self.conditions[condition.id] = condition
        self.condition_keys[condition.condition_key] = condition.id
        return condition

    def save_session(self, session: ExperimentSession) -> ExperimentSession:
        """儲存實驗 session。

        Args:
            session: ExperimentSession 實例。

        Returns:
            ExperimentSession: 儲存後的 session。
        """
        session.updated_at = utc_now()
        self.sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> ExperimentSession | None:
        """依 ID 取得 session。

        Args:
            session_id: Session UUID 字串。

        Returns:
            ExperimentSession | None: 匹配的 session，或 None。
        """
        return self.sessions.get(session_id)

    def list_sessions(self) -> list[ExperimentSession]:
        """列出所有 session，依建立時間倒序。

        Returns:
            list[ExperimentSession]: Session 清單。
        """
        return sorted(self.sessions.values(), key=lambda item: item.created_at, reverse=True)

    def list_sessions_for_user(self, user_id: str) -> list[ExperimentSession]:
        """列出指定使用者的 session，依更新時間倒序。

        Args:
            user_id: 使用者識別字串。

        Returns:
            list[ExperimentSession]: Session 清單。
        """
        sessions = [session for session in self.sessions.values() if session.user_id == user_id]
        return sorted(sessions, key=lambda item: item.updated_at, reverse=True)

    def list_participants(self) -> list[Participant]:
        """列出所有受測者，依 code 排序。"""
        return sorted(self.participants.values(), key=lambda item: item.code)

    def get_participant(self, participant_id: str) -> Participant | None:
        """依 ID 取得受測者。"""
        return self.participants.get(participant_id)

    def get_participant_by_auth_user(self, auth_user_id: str) -> Participant | None:
        """依 Supabase Auth user id 取得受測者。"""
        for participant in self.participants.values():
            if participant.auth_user_id == auth_user_id:
                return participant
        return None

    def save_participant(self, participant: Participant) -> Participant:
        """儲存受測者。"""
        participant.updated_at = utc_now()
        self.participants[participant.id] = participant
        return participant

    def save_event_task(self, task: EventTask) -> EventTask:
        """儲存 task。

        Args:
            task: EventTask 實例。

        Returns:
            EventTask: 儲存後的 task。
        """
        task.updated_at = utc_now()
        self.event_tasks[task.id] = task
        return task

    def get_event_task(self, task_id: str) -> EventTask | None:
        """依 ID 取得 task。

        Args:
            task_id: Task UUID 字串。

        Returns:
            EventTask | None: 匹配的 task，或 None。
        """
        return self.event_tasks.get(task_id)

    def get_latest_event_task(self, event_id: str) -> EventTask | None:
        """取得指定事件的最新 task。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            EventTask | None: 最新的 task，或 None。
        """
        tasks = self.list_event_tasks(event_id)
        return tasks[0] if tasks else None

    def list_event_tasks(self, event_id: str) -> list[EventTask]:
        """列出指定事件的所有 task，依建立時間倒序。

        Args:
            event_id: 事件 UUID 字串。

        Returns:
            list[EventTask]: Task 清單。
        """
        tasks = [task for task in self.event_tasks.values() if task.event_id == event_id]
        return sorted(tasks, key=lambda item: item.created_at, reverse=True)

    def save_task_attempt(self, attempt: TaskAttempt) -> TaskAttempt:
        """儲存 task attempt。

        Args:
            attempt: TaskAttempt 實例。

        Returns:
            TaskAttempt: 儲存後的 attempt。
        """
        attempt.updated_at = utc_now()
        self.task_attempts[attempt.id] = attempt
        return attempt

    def get_task_attempt(self, attempt_id: str) -> TaskAttempt | None:
        """依 ID 取得 task attempt。

        Args:
            attempt_id: Attempt UUID 字串。

        Returns:
            TaskAttempt | None: 匹配的 attempt，或 None。
        """
        return self.task_attempts.get(attempt_id)

    def get_task_attempt_for_session(self, session_id: str, task_id: str | None = None) -> TaskAttempt | None:
        """取得指定 session 的最新 attempt。

        可選搭配 task_id 進一步篩選。若有多筆 attempt，
        回傳 updated_at 最新的一筆。

        Args:
            session_id: Session UUID 字串。
            task_id: 可選的 Task UUID 字串。

        Returns:
            TaskAttempt | None: 最新的 attempt，或 None。
        """
        attempts = [attempt for attempt in self.task_attempts.values() if attempt.session_id == session_id]
        if task_id:
            attempts = [attempt for attempt in attempts if attempt.task_id == task_id]
        attempts.sort(key=lambda item: item.updated_at, reverse=True)
        return attempts[0] if attempts else None

    def save_persona(self, persona: Persona) -> Persona:
        """儲存 persona。

        Args:
            persona: Persona 實例。

        Returns:
            Persona: 儲存後的 persona。
        """
        persona.updated_at = utc_now()
        self.personas[persona.id] = persona
        return persona

    def get_persona(self, persona_id: str) -> Persona | None:
        """依 ID 取得 persona。

        Args:
            persona_id: Persona UUID 字串。

        Returns:
            Persona | None: 匹配的 persona，或 None。
        """
        return self.personas.get(persona_id)

    def list_personas(self, event_id: str, active_only: bool = True) -> list[Persona]:
        """列出指定事件的 personas，依 sort_order 與 created_at 排序。

        Args:
            event_id: 事件 UUID 字串。
            active_only: 若為 True，僅回傳 active=True 的角色。

        Returns:
            list[Persona]: Persona 清單。
        """
        personas = [persona for persona in self.personas.values() if persona.event_id == event_id]
        if active_only:
            personas = [persona for persona in personas if persona.active]
        return sorted(personas, key=lambda item: (item.sort_order, item.created_at))

    def delete_persona(self, persona_id: str) -> bool:
        """可恢復封存 persona（停用並記錄 archived_at）。

        Args:
            persona_id: Persona UUID 字串。

        Returns:
            bool: 若 persona 存在且已軟刪除回傳 True，否則 False。
        """
        persona = self.personas.get(persona_id)
        if not persona:
            return False
        persona.active = False
        persona.archived_at = utc_now()
        persona.updated_at = utc_now()
        self.personas[persona_id] = persona
        return True

    def save_conversation(self, conversation: Conversation) -> Conversation:
        """儲存 conversation 並初始化訊息列表。

        Args:
            conversation: Conversation 實例。

        Returns:
            Conversation: 儲存後的 conversation。
        """
        conversation.updated_at = utc_now()
        self.conversations[conversation.id] = conversation
        self.messages.setdefault(conversation.id, [])
        return conversation

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """依 ID 取得 conversation。

        Args:
            conversation_id: Conversation UUID 字串。

        Returns:
            Conversation | None: 匹配的 conversation，或 None。
        """
        return self.conversations.get(conversation_id)

    def get_conversation_by_session(self, session_id: str) -> Conversation | None:
        """依 session_id 取得最新的 conversation。

        Args:
            session_id: Session UUID 字串。

        Returns:
            Conversation | None: 最新的 conversation，或 None。
        """
        conversations = [conversation for conversation in self.conversations.values() if conversation.session_id == session_id]
        conversations.sort(key=lambda item: item.updated_at, reverse=True)
        return conversations[0] if conversations else None

    def next_message_sequence(self, conversation_id: str) -> int:
        """取得下一個可用的 sequence_index。

        Args:
            conversation_id: Conversation UUID 字串。

        Returns:
            int: 當前訊息數量（即下一個 sequence_index）。
        """
        return len(self.messages.get(conversation_id, []))

    def add_message(self, message: ChatMessage) -> ChatMessage:
        """新增或更新訊息，並依 sequence_index 排序。

        Args:
            message: ChatMessage 實例（需含 conversation_id）。

        Returns:
            ChatMessage: 已儲存的訊息。

        Raises:
            ValueError: 當 message.conversation_id 為空時。
        """
        if not message.conversation_id:
            raise ValueError("message.conversation_id is required")
        messages = self.messages.setdefault(message.conversation_id, [])
        existing_index = next(
            (index for index, item in enumerate(messages) if item.id == message.id),
            None,
        )
        if existing_index is None:
            if message.speaker_type == "learner" and message.client_request_id:
                duplicate_request = next(
                    (
                        item
                        for item in messages
                        if item.speaker_type == "learner"
                        and item.client_request_id == message.client_request_id
                    ),
                    None,
                )
                if duplicate_request:
                    raise ValueError("duplicate chat client_request_id")
            if (
                message.speaker_type == "learner"
                and message.operation_status in {"pending", "processing"}
            ):
                active_operation = next(
                    (
                        item
                        for item in messages
                        if item.speaker_type == "learner"
                        and item.operation_status in {"pending", "processing"}
                    ),
                    None,
                )
                if active_operation:
                    raise ValueError("conversation already has an active chat operation")
            messages.append(message)
        else:
            messages[existing_index] = message
        messages.sort(key=lambda item: item.sequence_index)
        return message

    def get_message(self, message_id: str) -> ChatMessage | None:
        """依訊息 ID 取得單一訊息。"""
        for messages in self.messages.values():
            message = next((item for item in messages if item.id == message_id), None)
            if message:
                return message
        return None

    def get_learner_message_by_request(
        self,
        conversation_id: str,
        client_request_id: str,
    ) -> ChatMessage | None:
        """依前端回合識別碼取得 learner 訊息。"""
        return next(
            (
                item
                for item in self.messages.get(conversation_id, [])
                if item.speaker_type == "learner"
                and item.client_request_id == client_request_id
            ),
            None,
        )

    def get_active_chat_operation(self, conversation_id: str) -> ChatMessage | None:
        """取得對話中尚在處理的 learner 回合。"""
        return next(
            (
                item
                for item in self.messages.get(conversation_id, [])
                if item.speaker_type == "learner"
                and item.operation_status in {"pending", "processing"}
            ),
            None,
        )

    def list_active_chat_operations(self) -> list[ChatMessage]:
        """列出所有尚在處理的 learner 回合，供程序重啟時恢復。"""
        return sorted(
            (
                item
                for messages in self.messages.values()
                for item in messages
                if item.speaker_type == "learner"
                and item.operation_status in {"pending", "processing"}
            ),
            key=lambda item: item.created_at,
        )

    def list_messages(self, conversation_id: str) -> list[ChatMessage]:
        """列出指定 conversation 的所有訊息，依 sequence_index 排序。

        Args:
            conversation_id: Conversation UUID 字串。

        Returns:
            list[ChatMessage]: 訊息清單。
        """
        return sorted(self.messages.get(conversation_id, []), key=lambda item: item.sequence_index)

    def log_research(self, log: ResearchLog) -> ResearchLog:
        """新增流程行為紀錄。

        Args:
            log: ResearchLog 實例。

        Returns:
            ResearchLog: 儲存後的紀錄。
        """
        self.research_logs[log.id] = log
        return log

    def list_research_logs(self, limit: int = 200) -> list[ResearchLog]:
        """列出最近的流程行為紀錄，依建立時間倒序。

        Args:
            limit: 回傳筆數上限。

        Returns:
            list[ResearchLog]: 紀錄清單。
        """
        logs = sorted(self.research_logs.values(), key=lambda item: item.created_at, reverse=True)
        return logs[:limit]

    def list_research_logs_for_session(self, session_id: str) -> list[ResearchLog]:
        """列出指定 Session 的完整研究紀錄，依時間正序。"""
        return sorted(
            (log for log in self.research_logs.values() if log.session_id == session_id),
            key=lambda log: log.created_at,
        )
