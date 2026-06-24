from app.crud.protocols import RepositoryProtocol
from app.models.domain import (
    ChatMessage,
    Conversation,
    Event,
    EventTask,
    ExperimentCondition,
    ExperimentSession,
    KnowledgeChunk,
    Persona,
    ResearchLog,
    TaskAttempt,
    WikiSource,
    utc_now,
)


class InMemoryRepository(RepositoryProtocol):
    def __init__(self) -> None:
        self.events: dict[str, Event] = {}
        self.event_names: dict[str, str] = {}
        self.wiki_sources: dict[str, WikiSource] = {}
        self.knowledge_chunks: dict[str, KnowledgeChunk] = {}
        self.conditions: dict[str, ExperimentCondition] = {}
        self.condition_keys: dict[str, str] = {}
        self.sessions: dict[str, ExperimentSession] = {}
        self.event_tasks: dict[str, EventTask] = {}
        self.task_attempts: dict[str, TaskAttempt] = {}
        self.personas: dict[str, Persona] = {}
        self.conversations: dict[str, Conversation] = {}
        self.messages: dict[str, list[ChatMessage]] = {}
        self.research_logs: dict[str, ResearchLog] = {}
        self.view_count = 0
        self._seed_conditions()

    @staticmethod
    def normalize_event_name(event_name: str) -> str:
        return " ".join(event_name.strip().lower().split())

    def _seed_conditions(self) -> None:
        seed = [
            ExperimentCondition(
                condition_key="no_ebl_no_roleplay",
                label="Without EBL + Without AI Role-play",
                ebl_enabled=False,
                roleplay_enabled=False,
                agent_mode="generic",
                response_policy="direct",
                description="一般 ChatGPT 式回答；可直接給正確答案。",
            ),
            ExperimentCondition(
                condition_key="ebl_no_roleplay",
                label="With EBL + Without AI Role-play",
                ebl_enabled=True,
                roleplay_enabled=False,
                agent_mode="generic",
                response_policy="scaffold",
                description="一般 tutor chatbot；引導 historical thinking、evidence-based argumentation、source interpretation。",
            ),
            ExperimentCondition(
                condition_key="no_ebl_roleplay",
                label="Without EBL + With AI Role-play",
                ebl_enabled=False,
                roleplay_enabled=True,
                agent_mode="persona",
                response_policy="direct",
                description="AI historical persona role-play；沉浸式回答，可直接給答案。",
            ),
            ExperimentCondition(
                condition_key="ebl_roleplay",
                label="With EBL + With AI Role-play",
                ebl_enabled=True,
                roleplay_enabled=True,
                agent_mode="persona",
                response_policy="scaffold",
                description="AI historical persona 基於 learner misconceptions 展開對話並引導 historical thinking。",
            ),
        ]
        for condition in seed:
            self.save_condition(condition)

    def find_event_by_name(self, event_name: str) -> Event | None:
        event_id = self.event_names.get(self.normalize_event_name(event_name))
        return self.events.get(event_id) if event_id else None

    def save_event(self, event: Event) -> Event:
        event.updated_at = utc_now()
        self.events[event.id] = event
        self.event_names[self.normalize_event_name(event.canonical_name)] = event.id
        return event

    def list_events(self) -> list[Event]:
        return sorted(self.events.values(), key=lambda item: item.created_at, reverse=True)

    def get_event(self, event_id: str) -> Event | None:
        return self.events.get(event_id)

    def delete_event(self, event_id: str) -> bool:
        event = self.events.pop(event_id, None)
        if not event:
            return False
        self.event_names.pop(self.normalize_event_name(event.canonical_name), None)
        for source_id in [s.id for s in self.wiki_sources.values() if s.event_id == event_id]:
            self.wiki_sources.pop(source_id, None)
        for chunk_id in [c.id for c in self.knowledge_chunks.values() if c.event_id == event_id]:
            self.knowledge_chunks.pop(chunk_id, None)
        for task_id in [t.id for t in self.event_tasks.values() if t.event_id == event_id]:
            self.event_tasks.pop(task_id, None)
        for attempt_id in [a.id for a in self.task_attempts.values() if a.event_id == event_id]:
            self.task_attempts.pop(attempt_id, None)
        for persona_id in [p.id for p in self.personas.values() if p.event_id == event_id]:
            self.personas.pop(persona_id, None)
        for session_id in [s.id for s in self.sessions.values() if s.event_id == event_id]:
            self.sessions.pop(session_id, None)
        for conversation_id in [c.id for c in self.conversations.values() if c.event_id == event_id]:
            self.conversations.pop(conversation_id, None)
            self.messages.pop(conversation_id, None)
        return True

    def save_wiki_source(self, source: WikiSource) -> WikiSource:
        self.wiki_sources[source.id] = source
        return source

    def list_wiki_sources(self, event_id: str) -> list[WikiSource]:
        return [source for source in self.wiki_sources.values() if source.event_id == event_id]

    def save_knowledge_chunk(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        self.knowledge_chunks[chunk.id] = chunk
        return chunk

    def list_knowledge_chunks(self, event_id: str) -> list[KnowledgeChunk]:
        return [chunk for chunk in self.knowledge_chunks.values() if chunk.event_id == event_id]

    def list_conditions(self, active_only: bool = True) -> list[ExperimentCondition]:
        conditions = list(self.conditions.values())
        if active_only:
            conditions = [condition for condition in conditions if condition.active]
        return sorted(conditions, key=lambda item: item.condition_key)

    def get_condition_by_key(self, condition_key: str) -> ExperimentCondition | None:
        condition_id = self.condition_keys.get(condition_key)
        return self.conditions.get(condition_id) if condition_id else None

    def get_condition(self, condition_id: str) -> ExperimentCondition | None:
        return self.conditions.get(condition_id)

    def save_condition(self, condition: ExperimentCondition) -> ExperimentCondition:
        condition.updated_at = utc_now()
        self.conditions[condition.id] = condition
        self.condition_keys[condition.condition_key] = condition.id
        return condition

    def save_session(self, session: ExperimentSession) -> ExperimentSession:
        session.updated_at = utc_now()
        self.sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> ExperimentSession | None:
        return self.sessions.get(session_id)

    def list_sessions(self) -> list[ExperimentSession]:
        return sorted(self.sessions.values(), key=lambda item: item.created_at, reverse=True)

    def list_sessions_for_user(self, user_id: str) -> list[ExperimentSession]:
        sessions = [session for session in self.sessions.values() if session.user_id == user_id]
        return sorted(sessions, key=lambda item: item.updated_at, reverse=True)

    def save_event_task(self, task: EventTask) -> EventTask:
        task.updated_at = utc_now()
        self.event_tasks[task.id] = task
        return task

    def get_event_task(self, task_id: str) -> EventTask | None:
        return self.event_tasks.get(task_id)

    def get_latest_event_task(self, event_id: str) -> EventTask | None:
        tasks = self.list_event_tasks(event_id)
        return tasks[0] if tasks else None

    def list_event_tasks(self, event_id: str) -> list[EventTask]:
        tasks = [task for task in self.event_tasks.values() if task.event_id == event_id]
        return sorted(tasks, key=lambda item: item.created_at, reverse=True)

    def save_task_attempt(self, attempt: TaskAttempt) -> TaskAttempt:
        attempt.updated_at = utc_now()
        self.task_attempts[attempt.id] = attempt
        return attempt

    def get_task_attempt(self, attempt_id: str) -> TaskAttempt | None:
        return self.task_attempts.get(attempt_id)

    def get_task_attempt_for_session(self, session_id: str, task_id: str | None = None) -> TaskAttempt | None:
        attempts = [attempt for attempt in self.task_attempts.values() if attempt.session_id == session_id]
        if task_id:
            attempts = [attempt for attempt in attempts if attempt.task_id == task_id]
        attempts.sort(key=lambda item: item.updated_at, reverse=True)
        return attempts[0] if attempts else None

    def save_persona(self, persona: Persona) -> Persona:
        persona.updated_at = utc_now()
        self.personas[persona.id] = persona
        return persona

    def get_persona(self, persona_id: str) -> Persona | None:
        return self.personas.get(persona_id)

    def list_personas(self, event_id: str, active_only: bool = True) -> list[Persona]:
        personas = [persona for persona in self.personas.values() if persona.event_id == event_id]
        if active_only:
            personas = [persona for persona in personas if persona.active]
        return sorted(personas, key=lambda item: (item.sort_order, item.created_at))

    def delete_persona(self, persona_id: str) -> bool:
        persona = self.personas.get(persona_id)
        if not persona:
            return False
        persona.active = False
        persona.updated_at = utc_now()
        self.personas[persona_id] = persona
        return True

    def save_conversation(self, conversation: Conversation) -> Conversation:
        conversation.updated_at = utc_now()
        self.conversations[conversation.id] = conversation
        self.messages.setdefault(conversation.id, [])
        return conversation

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self.conversations.get(conversation_id)

    def get_conversation_by_session(self, session_id: str) -> Conversation | None:
        conversations = [conversation for conversation in self.conversations.values() if conversation.session_id == session_id]
        conversations.sort(key=lambda item: item.updated_at, reverse=True)
        return conversations[0] if conversations else None

    def next_message_sequence(self, conversation_id: str) -> int:
        return len(self.messages.get(conversation_id, []))

    def add_message(self, message: ChatMessage) -> ChatMessage:
        if not message.conversation_id:
            raise ValueError("message.conversation_id is required")
        self.messages.setdefault(message.conversation_id, []).append(message)
        self.messages[message.conversation_id].sort(key=lambda item: item.sequence_index)
        return message

    def list_messages(self, conversation_id: str) -> list[ChatMessage]:
        return sorted(self.messages.get(conversation_id, []), key=lambda item: item.sequence_index)

    def log_research(self, log: ResearchLog) -> ResearchLog:
        self.research_logs[log.id] = log
        return log

    def list_research_logs(self, limit: int = 200) -> list[ResearchLog]:
        logs = sorted(self.research_logs.values(), key=lambda item: item.created_at, reverse=True)
        return logs[:limit]

    def increment_view_count(self) -> int:
        self.view_count += 1
        return self.view_count
