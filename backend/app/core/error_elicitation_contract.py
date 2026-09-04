"""Error-Elicitation Task 的作答與判定格式，不在此執行 LLM 評分。"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, field_validator, model_validator


ERROR_ELICITATION_CONTRACT_VERSION = "error_elicitation_v1"
ERROR_ELICITATION_JUDGE_CONTRACT_VERSION = "error_elicitation_judge_v3"
ErrorElicitationCorrectness = Literal["correct", "incorrect"]
HistoricalThinkingTag = Literal[
    "historical_significance",
    "evidence",
    "continuity_and_change",
    "cause_and_consequence",
    "historical_perspectives",
    "ethical_dimension",
]


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


def validate_task_answers(evaluation: dict, response: dict, *, complete: bool) -> None:
    """草稿可缺答；送出時題號、題型、答案與理由必須與後端題目一致。"""
    if evaluation.get("contract_version") != ERROR_ELICITATION_CONTRACT_VERSION:
        if "contract_version" in response:
            raise ValueError("Task and answer contracts do not match")
        return
    parsed = ErrorElicitationResponsePayload.model_validate(response)
    questions = {question["id"]: question for question in evaluation["questions"]}
    ids = {answer.question_id for answer in parsed.answers}
    if not ids.issubset(questions) or (complete and ids != set(questions)):
        raise ValueError("Answers must match this task's question ids")
    for answer in parsed.answers:
        question = questions[answer.question_id]
        value = answer.value
        has_answer = value is not None and (not isinstance(value, str) or bool(value.strip()))
        if complete and (not has_answer or not answer.rationale.strip()):
            raise ValueError(f"{answer.question_id}: both answer and rationale are required")
        if not has_answer:
            continue
        if question["type"] == "true_false" and not isinstance(value, bool):
            raise ValueError(f"{answer.question_id}: answer must be a boolean")
        if question["type"] != "true_false" and not isinstance(value, str):
            raise ValueError(f"{answer.question_id}: answer must be a string")
        if question["type"] == "multiple_choice" and value not in {option["value"] for option in question["options"]}:
            raise ValueError(f"{answer.question_id}: answer must be one of the options")


class ErrorElicitationReasoningJudgement(BaseModel):
    """LLM 只判理由；Historical Thinking 標籤不參與對錯。"""

    model_config = ConfigDict(extra="forbid")

    question_id: StrictStr = Field(min_length=1)
    reasoning_correct: StrictBool
    reasoning_feedback: StrictStr = Field(min_length=1)
    historical_thinking_tags: list[HistoricalThinkingTag] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def validate_reasoning_result(self) -> "ErrorElicitationReasoningJudgement":
        if not self.question_id.strip() or self.question_id != self.question_id.strip() or not self.reasoning_feedback.strip():
            raise ValueError("question_id and reasoning_feedback must not be blank")
        if len(self.historical_thinking_tags) != len(set(self.historical_thinking_tags)):
            raise ValueError("historical_thinking_tags must not contain duplicates")
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


class ErrorElicitationJudgementPayload(BaseModel):
    """同一次模型呼叫判斷所有理由，客觀答案與最終對錯由後端決定。"""

    model_config = ConfigDict(extra="forbid")
    judge_contract_version: Literal["error_elicitation_judge_v3"]
    question_results: list[ErrorElicitationReasoningJudgement] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_results(self) -> "ErrorElicitationJudgementPayload":
        ids = [result.question_id for result in self.question_results]
        if len(ids) != len(set(ids)):
            raise ValueError("Judge returned duplicate question ids")
        return self
