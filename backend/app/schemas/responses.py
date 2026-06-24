from typing import Any

from pydantic import BaseModel, Field

from app.models.domain import (
    Annotation,
    ChatMessage,
    Conversation,
    Event,
    EventTask,
    ExperimentCondition,
    ExperimentSession,
    Persona,
    RagSource,
    RelatedEvent,
    ResearchLog,
    TaskAttempt,
)


class EventInitializeResponse(BaseModel):
    event_id: str
    session_id: str
    event: Event
    task: EventTask
    personas: list[Persona]
    condition: ExperimentCondition


class EventListItem(Event):
    personas: list[Persona] = Field(default_factory=list)
    latest_task: EventTask | None = None


class TaskSubmitResponse(BaseModel):
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


class TaskDraftResponse(BaseModel):
    attempt: TaskAttempt


class ConversationCreateResponse(BaseModel):
    conversation_id: str
    event: Event
    personas: list[Persona]
    condition: ExperimentCondition | None = None
    greeting: str
    history: list[ChatMessage] = Field(default_factory=list)


class ConversationLoadResponse(BaseModel):
    conversation_id: str
    event: Event
    personas: list[Persona]
    messages: list[ChatMessage]
    condition: ExperimentCondition | None = None
    task_attempt: TaskAttempt | None = None
    related_events: list[RelatedEvent] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    selected_persona: Persona | None = None
    assistant_name: str
    message: ChatMessage
    annotations: list[Annotation] = Field(default_factory=list)
    related_events: list[RelatedEvent] = Field(default_factory=list)
    dynamic_context: str = ""
    rag_sources: list[RagSource] = Field(default_factory=list)


class AdminSnapshotResponse(BaseModel):
    events: list[EventListItem] = Field(default_factory=list)
    conditions: list[ExperimentCondition] = Field(default_factory=list)
    sessions: list[ExperimentSession] = Field(default_factory=list)
    research_logs: list[ResearchLog] = Field(default_factory=list)


class SessionStateResponse(BaseModel):
    session: ExperimentSession
    event: Event
    task: EventTask | None = None
    personas: list[Persona] = Field(default_factory=list)
    condition: ExperimentCondition | None = None
    attempt: TaskAttempt | None = None
    conversation_id: str | None = None


class UserProgressItem(BaseModel):
    event_id: str
    condition_key: str
    session_id: str
    task_id: str | None = None
    attempt_id: str | None = None
    conversation_id: str | None = None
    status: str
    updated_at: str


class UserProgressResponse(BaseModel):
    progress: list[UserProgressItem] = Field(default_factory=list)
