from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

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
)


ModelT = TypeVar("ModelT", bound=BaseModel)


class SupabaseRepository(RepositoryProtocol):
    """PostgREST-backed repository.

    The service layer deliberately talks to this repository protocol rather than
    Supabase directly, so tests can use an in-memory repository and production can
    use local/cloud Supabase with the same business logic.
    """

    def __init__(self, supabase_url: str, service_role_key: str) -> None:
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

    def _request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        json: Any | None = None,
        prefer: str | None = None,
    ) -> Any:
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
        return model.model_dump(mode="json", exclude_none=False)

    def _upsert(self, table: str, model: ModelT, *, conflict: str = "id") -> ModelT:
        data = self._request(
            "POST",
            table,
            params={"on_conflict": conflict},
            json=self._payload(model),
            prefer="resolution=merge-duplicates,return=representation",
        )
        return type(model)(**data[0])

    def _patch(self, table: str, model_cls: type[ModelT], item_id: str, payload: dict[str, Any]) -> ModelT | None:
        data = self._request(
            "PATCH",
            table,
            params={"id": f"eq.{item_id}"},
            json=payload,
            prefer="return=representation",
        )
        return model_cls(**data[0]) if data else None

    def _select_one(self, table: str, model_cls: type[ModelT], params: dict[str, str]) -> ModelT | None:
        data = self._request("GET", table, params={**params, "limit": "1"})
        return model_cls(**data[0]) if data else None

    def _select_many(self, table: str, model_cls: type[ModelT], params: dict[str, str] | None = None) -> list[ModelT]:
        data = self._request("GET", table, params=params or {})
        return [model_cls(**item) for item in data]

    def find_event_by_name(self, event_name: str) -> Event | None:
        return self._select_one(
            "events",
            Event,
            {"canonical_name": f"ilike.{event_name.strip()}"},
        )

    def save_event(self, event: Event) -> Event:
        return self._upsert("events", event)

    def list_events(self) -> list[Event]:
        return self._select_many("events", Event, {"order": "created_at.desc"})

    def get_event(self, event_id: str) -> Event | None:
        return self._select_one("events", Event, {"id": f"eq.{event_id}"})

    def delete_event(self, event_id: str) -> bool:
        data = self._request(
            "DELETE",
            "events",
            params={"id": f"eq.{event_id}"},
            prefer="return=representation",
        )
        return bool(data)

    def save_wiki_source(self, source: WikiSource) -> WikiSource:
        return self._upsert("wiki_sources", source)

    def list_wiki_sources(self, event_id: str) -> list[WikiSource]:
        return self._select_many("wiki_sources", WikiSource, {"event_id": f"eq.{event_id}", "order": "retrieved_at.asc"})

    def save_knowledge_chunk(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        return self._upsert("knowledge_chunks", chunk)

    def list_knowledge_chunks(self, event_id: str) -> list[KnowledgeChunk]:
        return self._select_many("knowledge_chunks", KnowledgeChunk, {"event_id": f"eq.{event_id}", "order": "chunk_index.asc"})

    def list_conditions(self, active_only: bool = True) -> list[ExperimentCondition]:
        params = {"order": "condition_key.asc"}
        if active_only:
            params["active"] = "eq.true"
        return self._select_many("experiment_conditions", ExperimentCondition, params)

    def get_condition_by_key(self, condition_key: str) -> ExperimentCondition | None:
        return self._select_one("experiment_conditions", ExperimentCondition, {"condition_key": f"eq.{condition_key}"})

    def get_condition(self, condition_id: str) -> ExperimentCondition | None:
        return self._select_one("experiment_conditions", ExperimentCondition, {"id": f"eq.{condition_id}"})

    def save_condition(self, condition: ExperimentCondition) -> ExperimentCondition:
        return self._upsert("experiment_conditions", condition)

    def save_session(self, session: ExperimentSession) -> ExperimentSession:
        return self._upsert("experiment_sessions", session)

    def get_session(self, session_id: str) -> ExperimentSession | None:
        return self._select_one("experiment_sessions", ExperimentSession, {"id": f"eq.{session_id}"})

    def list_sessions(self) -> list[ExperimentSession]:
        return self._select_many("experiment_sessions", ExperimentSession, {"order": "created_at.desc"})

    def save_event_task(self, task: EventTask) -> EventTask:
        return self._upsert("event_tasks", task)

    def get_event_task(self, task_id: str) -> EventTask | None:
        return self._select_one("event_tasks", EventTask, {"id": f"eq.{task_id}"})

    def get_latest_event_task(self, event_id: str) -> EventTask | None:
        return self._select_one(
            "event_tasks",
            EventTask,
            {"event_id": f"eq.{event_id}", "order": "created_at.desc"},
        )

    def list_event_tasks(self, event_id: str) -> list[EventTask]:
        return self._select_many("event_tasks", EventTask, {"event_id": f"eq.{event_id}", "order": "created_at.desc"})

    def save_task_attempt(self, attempt: TaskAttempt) -> TaskAttempt:
        return self._upsert("task_attempts", attempt)

    def get_task_attempt(self, attempt_id: str) -> TaskAttempt | None:
        return self._select_one("task_attempts", TaskAttempt, {"id": f"eq.{attempt_id}"})

    def save_persona(self, persona: Persona) -> Persona:
        return self._upsert("personas", persona)

    def get_persona(self, persona_id: str) -> Persona | None:
        return self._select_one("personas", Persona, {"id": f"eq.{persona_id}"})

    def list_personas(self, event_id: str, active_only: bool = True) -> list[Persona]:
        params = {"event_id": f"eq.{event_id}", "order": "sort_order.asc,created_at.asc"}
        if active_only:
            params["active"] = "eq.true"
        return self._select_many("personas", Persona, params)

    def delete_persona(self, persona_id: str) -> bool:
        return self._patch("personas", Persona, persona_id, {"active": False}) is not None

    def save_conversation(self, conversation: Conversation) -> Conversation:
        return self._upsert("conversations", conversation)

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self._select_one("conversations", Conversation, {"id": f"eq.{conversation_id}"})

    def next_message_sequence(self, conversation_id: str) -> int:
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
        return self._upsert("messages", message)

    def list_messages(self, conversation_id: str) -> list[ChatMessage]:
        return self._select_many("messages", ChatMessage, {"conversation_id": f"eq.{conversation_id}", "order": "sequence_index.asc"})

    def log_research(self, log: ResearchLog) -> ResearchLog:
        return self._upsert("research_logs", log)

    def list_research_logs(self, limit: int = 200) -> list[ResearchLog]:
        return self._select_many("research_logs", ResearchLog, {"order": "created_at.desc", "limit": str(limit)})

    def increment_view_count(self) -> int:
        # View count is intentionally local-process only in V1 because it is not
        # part of the thesis experiment data model.
        return 0
