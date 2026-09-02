"""Error-Elicitation Task 的作答與判定格式，不在此執行 LLM 評分。"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, field_validator, model_validator


ERROR_ELICITATION_CONTRACT_VERSION = "error_elicitation_v1"
ErrorElicitationCorrectness = Literal["correct", "incorrect"]
ReasoningIssue = Literal["none", "factual_error", "unsupported_inference", "insufficient_reasoning"]


class ErrorElicitationAnswer(BaseModel):
    """草稿可尚未填完；理由保留學生原文，不裁切或補寫。"""

    model_config = ConfigDict(extra="allow")

    question_id: StrictStr = Field(min_length=1)
    value: StrictStr | StrictBool | None = None
    rationale: StrictStr = ""

    @field_validator("question_id")
    @classmethod
    def validate_question_id(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("question_id must be nonblank and have no surrounding whitespace")
        return value


class ErrorElicitationResponsePayload(BaseModel):
    """既有 response_payload JSONB 內的新版格式，不增加資料表。"""

    model_config = ConfigDict(extra="allow")

    contract_version: Literal["error_elicitation_v1"]
    answers: list[ErrorElicitationAnswer]

    @model_validator(mode="after")
    def validate_unique_answers(self) -> "ErrorElicitationResponsePayload":
        ids = [answer.question_id for answer in self.answers]
        if len(ids) != len(set(ids)):
            raise ValueError("Each question_id may only appear once in answers")
        return self


def validate_versioned_task_response(value: dict[str, Any]) -> dict[str, Any]:
    """分批切換期間只驗證明確標記的新格式，不改寫現有作答內容。"""
    if "contract_version" in value:
        ErrorElicitationResponsePayload.model_validate(value)
    return value


class ErrorElicitationReasoningJudgement(BaseModel):
    """LLM 只判理由；不足不等於已證明學生有錯誤觀念。"""

    model_config = ConfigDict(extra="forbid")

    question_id: StrictStr = Field(min_length=1)
    reasoning_correct: StrictBool
    reasoning_issue: ReasoningIssue
    reasoning_feedback: StrictStr = Field(min_length=1)

    @model_validator(mode="after")
    def validate_reasoning_result(self) -> "ErrorElicitationReasoningJudgement":
        if not self.question_id.strip() or self.question_id != self.question_id.strip() or not self.reasoning_feedback.strip():
            raise ValueError("question_id and reasoning_feedback must not be blank")
        if self.reasoning_correct != (self.reasoning_issue == "none"):
            raise ValueError("reasoning_issue must agree with reasoning_correct")
        return self


class ErrorElicitationQuestionResult(ErrorElicitationReasoningJudgement):
    """後端合併規則答案與 LLM 理由結果，拒絕互相矛盾的整題判定。"""

    answer_correct: StrictBool
    correctness: ErrorElicitationCorrectness

    @model_validator(mode="after")
    def validate_overall_correctness(self) -> "ErrorElicitationQuestionResult":
        expected = "correct" if self.answer_correct and self.reasoning_correct else "incorrect"
        if self.correctness != expected:
            raise ValueError("correctness must be correct only when both answer and reasoning are correct")
        return self
