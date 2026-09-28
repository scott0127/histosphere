"""Private administrator requests for the pre-conversation human review."""

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class TaskReviewQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1)
    reviewed: StrictBool = False
    answer_correct: StrictBool
    reasoning_correct: StrictBool
    answer_feedback: str | None = None
    reasoning_feedback: str = ""
    override_reason: str = ""


class TaskReviewDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=0)
    question_results: list[TaskReviewQuestion]


class TaskReviewApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=0)
