"""Structured LLM output schemas.

本模組定義 LLM 必須回傳的 JSON 結構。Provider 只能把通過 Pydantic
驗證的資料交給 service，避免研究流程吃到鬆散或不可追蹤的自然語言輸出。

所有 schema 皆透過 ``LLMJsonRunner.run_json()`` 做驗證，
失敗時會自動觸發 repair prompt 重試。
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.core.persona_prompt_contract import PersonaPromptProfile
from app.core.task_payload_validator import validate_task_authoring_payload
from app.core.error_elicitation_contract import ERROR_ELICITATION_CONTRACT_VERSION


class EventProfilePayload(BaseModel):
    """LLM 生成的事件基本資料。

    缺乏可信資訊時 century / start_year / end_year 可為 None。

    Attributes:
        canonical_name: 事件正式名稱。
        description: 事件簡述。
        century: 所屬世紀（可為 None）。
        start_year: 起始年份（可為 None）。
        end_year: 結束年份（可為 None）。
        context: 事件歷史脈絡。
        source_summary: 來源摘要 metadata。
    """

    canonical_name: str
    description: str
    century: int | None = None
    start_year: int | None = None
    end_year: int | None = None
    context: str
    source_summary: dict = Field(default_factory=dict)


class GeneratedTaskPayload(BaseModel):
    """LLM 生成的 prototype task 初稿。

    正式實驗可由教師在 admin 覆蓋修改。

    Attributes:
        title: Task 標題。
        story_text: 完整正確故事文字。
        error_elicitation_task_full_text: 含 ``{{blank:qNN}}`` 題目 token 的顯示用文字。
        evaluation_payload: 含 ``questions[]`` 的評量結構。
    """

    title: str = Field(min_length=1)
    story_text: str = ""
    error_elicitation_task_full_text: str = Field(min_length=1)
    evaluation_payload: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_current_task_contract(self) -> "GeneratedTaskPayload":
        """拒絕舊式空格與鬆散 payload，讓 runner 自動要求 LLM 修復。"""
        questions = self.evaluation_payload.get("questions")
        if self.evaluation_payload.get("contract_version") != ERROR_ELICITATION_CONTRACT_VERSION:
            raise ValueError("Generated tasks must use error_elicitation_v1")
        if not isinstance(questions, list) or not questions:
            raise ValueError("evaluation_payload.questions must contain at least one question")
        if "____" in self.error_elicitation_task_full_text:
            raise ValueError("error_elicitation_task_full_text must use {{blank:qNN}} tokens instead of ____")

        issues = validate_task_authoring_payload(
            error_elicitation_task_full_text=self.error_elicitation_task_full_text,
            evaluation_payload=self.evaluation_payload,
        )
        if issues:
            details = "; ".join(f"{issue['field']}: {issue['message']}" for issue in issues)
            raise ValueError(details)
        return self


class GeneratedPersonaPayload(BaseModel):
    """LLM 生成的單一 primary historical persona。

    Attributes:
        name: 角色中文名稱。
        english_name: 角色英文名稱（可選）。
        role: 角色在事件中的身份（可選）。
        biography: 角色簡傳（可選）。
        expertise_areas: 專業領域清單。
        sources: 角色資料來源引用。
        prompt_profile: 供 prompt 組裝的角色 profile。
    """

    name: str
    english_name: str | None = None
    role: str | None = None
    biography: str | None = None
    expertise_areas: list[str] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    # 在 runner 內驗證，格式錯誤才能進入同一次 structured repair，而不是
    # 等到建立 Persona 時才無法追蹤地失敗。
    prompt_profile: PersonaPromptProfile


class PersonaListPayload(BaseModel):
    """LLM 生成的 persona 清單包裝。

    V1 只使用第一位 primary persona。

    Attributes:
        personas: Persona 清單（至少一位）。
    """

    personas: list[GeneratedPersonaPayload] = Field(min_length=1, max_length=1)


class QuestionJudgementPayload(BaseModel):
    """LLM 對一題開放式作答的即時診斷判定。"""

    question_id: str
    learner_answer: Any = None
    correctness: Literal["correct", "partial", "incorrect", "unanswered"]
    error_code: str | None = None
    classifier_confidence: float | None = None


class TaskJudgementPayload(BaseModel):
    """Task 作答的診斷結果，用於建立後續對話的學習機會。

    Attributes:
        result: 整體診斷狀態；後端會再依逐題結果重新計算。
        misconception_summary: Learner misconception 摘要。
        feedback: Task 處理摘要，不作為前後測分數。
        provider: 執行判斷的 LLM provider 名稱。
    """

    result: Literal["correct", "partial", "incorrect", "unanswered"]
    misconception_summary: str
    feedback: str
    provider: str = "litellm"
    question_results: list[QuestionJudgementPayload] = Field(default_factory=list)


class ChatOutputPayload(BaseModel):
    """聊天回覆的 structured output。

    LLM 回覆必須符合此結構，包含回覆文字、
    歷史標注、關聯事件與動態 context。

    Attributes:
        response: AI 回覆文字。
        annotations: 歷史標注清單（dict 格式）。
        related_events: 關聯事件清單（dict 格式）。
        dynamic_context: 動態 context 補充文字。
    """

    response: str
    annotations: list[dict] = Field(default_factory=list)
    related_events: list[dict] = Field(default_factory=list)
    dynamic_context: str = ""
    dialogue_state: Literal[
        "STANDARD_CHAT",
        "NOTICE_ERROR",
        "REFLECT",
        "SELF_CORRECT",
        "RESOLVED",
    ] | None = None
    dialogue_move: str | None = None
    disclosure_level: Literal["D0", "D1", "D2", "D3", "D4"] | None = None
    # 僅供讀取舊版 L0-L4 completion，新的模型輸出一律使用 disclosure_level。
    scaffold_level: Literal["L0", "L1", "L2", "L3", "L4"] | None = None
    # 這兩個欄位只供研究紀錄與後端決策稽核，不顯示給受測者。
    learner_progress: Literal[
        "not_assessed",
        "no_progress",
        "partial_progress",
        "clear_progress",
        "resolved",
    ] | None = None
    disclosure_reason: str | None = None
    learner_revision_status: Literal["not_yet", "partial", "revised", "unresolved", "not_applicable"] | None = None
    completion_status: Literal[
        "continue",
        "resolved",
        "complete",
        "final_answer_pending",
        "feedback_completed",
    ] | None = None
    # 只判斷 EBL 的認知錯誤、反思與自我修正，不另評 learner 的 Historical Thinking 技能。
    resolution_error_recognized: bool = False
    resolution_error_reflected: bool = False
    resolution_self_corrected: bool = False
    # 同次生成判斷是否需要離題重新導向；僅供後端稽核，不顯示給受測者。
    off_topic_redirect: bool = False
    fidelity_flags: list[str] = Field(default_factory=list)
