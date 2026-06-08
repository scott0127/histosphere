from typing import Any

from pydantic import BaseModel, Field

from app.models.domain import ChatMessage, ConditionKey


class EventInitializeRequest(BaseModel):
    event_name: str = Field(..., min_length=1)
    condition_key: ConditionKey = "ebl_roleplay"
    rebuild: bool = False
    user_id: str | None = None


class EventCheckRequest(BaseModel):
    event_name: str = Field(..., min_length=1)


class TaskSubmitRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    response_payload: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None


class ConversationCreateRequest(BaseModel):
    event_id: str = Field(..., min_length=1)
    task_attempt_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None


class ChatRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1)
    user_message: str = Field(..., min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    target_persona_id: str | None = None


class PersonaCreateRequest(BaseModel):
    event_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    english_name: str | None = None
    role: str | None = None
    biography: str | None = None
    expertise_areas: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    avatar_url: str | None = None
    prompt_profile: dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    sort_order: int = 0
    revision_state: str = "manual"


class PersonaUpdateRequest(BaseModel):
    name: str | None = None
    english_name: str | None = None
    role: str | None = None
    biography: str | None = None
    expertise_areas: list[str] | None = None
    sources: list[dict[str, Any]] | None = None
    avatar_url: str | None = None
    prompt_profile: dict[str, Any] | None = None
    active: bool | None = None
    sort_order: int | None = None
    revision_state: str | None = None


class EventTaskUpdateRequest(BaseModel):
    title: str | None = None
    story_text: str | None = None
    display_text: str | None = None
    evaluation_payload: dict[str, Any] | None = None
    revision_state: str | None = "teacher_modified"


class ExperimentConditionUpdateRequest(BaseModel):
    label: str | None = None
    ebl_enabled: bool | None = None
    roleplay_enabled: bool | None = None
    agent_mode: str | None = None
    response_policy: str | None = None
    description: str | None = None
    active: bool | None = None
