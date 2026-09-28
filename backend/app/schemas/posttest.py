"""Fixed placeholder posttest contract; no formal instrument or scoring yet."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

from app.models.domain import SessionPosttest


class PosttestQuestion(BaseModel):
    id: str
    prompt: str


class PosttestInstrument(BaseModel):
    version: Literal["posttest_placeholder_v1"] = "posttest_placeholder_v1"
    is_placeholder: Literal[True] = True
    engagement: list[PosttestQuestion]
    hat: list[PosttestQuestion]


class PosttestStateResponse(BaseModel):
    session_id: str
    conversation_id: str | None = None
    event_name: str
    eligible: bool
    blocked_reason: str | None = None
    response: SessionPosttest | None = None
    instrument: PosttestInstrument


class PosttestRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: Annotated[StrictInt, Field(ge=0)]


class PosttestDraftRequest(PosttestRevisionRequest):
    engagement_answers: dict[Literal["engagement_1", "engagement_2", "engagement_3"], Annotated[StrictInt, Field(ge=1, le=5)]] | None = None
    hat_answers: dict[Literal["hat_1", "hat_2"], Annotated[str, StringConstraints(max_length=10000)]] | None = None
