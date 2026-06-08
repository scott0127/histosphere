from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


ConditionKey = Literal[
    "no_ebl_no_roleplay",
    "ebl_no_roleplay",
    "no_ebl_roleplay",
    "ebl_roleplay",
]
SpeakerType = Literal["learner", "assistant", "persona"]
ResponsePolicy = Literal["direct", "scaffold"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Event(BaseModel):
    id: str = Field(default_factory=new_id)
    canonical_name: str
    description: str | None = None
    century: int | None = None
    start_year: int | None = None
    end_year: int | None = None
    context: str | None = None
    source_summary: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class WikiSource(BaseModel):
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
    id: str = Field(default_factory=new_id)
    condition_key: ConditionKey
    label: str
    ebl_enabled: bool = False
    roleplay_enabled: bool = False
    agent_mode: Literal["generic", "persona"] = "generic"
    response_policy: ResponsePolicy = "direct"
    description: str | None = None
    active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ExperimentSession(BaseModel):
    id: str = Field(default_factory=new_id)
    condition_id: str | None = None
    condition_key_snapshot: ConditionKey
    user_id: str | None = None
    event_id: str
    status: Literal[
        "initialized",
        "task_submitted",
        "conversation_started",
        "completed",
        "archived",
    ] = "initialized"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class EventTask(BaseModel):
    id: str = Field(default_factory=new_id)
    event_id: str
    title: str | None = None
    story_text: str
    display_text: str
    evaluation_payload: dict[str, Any] = Field(default_factory=dict)
    revision_state: Literal["llm_generated", "teacher_modified", "manual"] = "llm_generated"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TaskAttempt(BaseModel):
    id: str = Field(default_factory=new_id)
    task_id: str
    event_id: str
    session_id: str | None = None
    user_id: str | None = None
    status: Literal["in_progress", "submitted"] = "in_progress"
    response_payload: dict[str, Any] = Field(default_factory=dict)
    judgement_payload: dict[str, Any] = Field(default_factory=dict)
    submitted_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Persona(BaseModel):
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
    sort_order: int = 0
    revision_state: Literal["llm_generated", "teacher_modified", "manual"] = "llm_generated"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Conversation(BaseModel):
    id: str = Field(default_factory=new_id)
    event_id: str
    task_attempt_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    status: Literal["active", "archived"] = "active"
    started_at: datetime = Field(default_factory=utc_now)
    archived_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Annotation(BaseModel):
    text: str
    explanation: str


class RagSource(BaseModel):
    source: str = "unknown"
    section_title: str = "Source"
    content: str


class RelatedEvent(BaseModel):
    event_name: str
    event_year: int | None = None
    event_id: str | None = None
    relevance_reason: str
    is_explorable: bool = False


class ChatMessage(BaseModel):
    id: str = Field(default_factory=new_id)
    conversation_id: str | None = None
    persona_id: str | None = None
    speaker_type: SpeakerType
    speaker_name: str
    sequence_index: int = 0
    content: str
    annotations: list[Annotation] = Field(default_factory=list)
    rag_sources: list[RagSource] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ResearchLog(BaseModel):
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
