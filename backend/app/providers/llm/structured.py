"""Structured LLM output schemas.

本模組定義 LLM 必須回傳的 JSON 結構。Provider 只能把通過 Pydantic
驗證的資料交給 service，避免研究流程吃到鬆散或不可追蹤的自然語言輸出。

所有 schema 皆透過 ``LLMJsonRunner.run_json()`` 做驗證，
失敗時會自動觸發 repair prompt 重試。
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


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
        display_text: 含空格「____」的顯示用文字。
        evaluation_payload: 評量結構（rubric、expected_points 等）。
    """

    title: str
    story_text: str
    display_text: str
    evaluation_payload: dict = Field(default_factory=dict)


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
    prompt_profile: dict = Field(default_factory=dict)


class PersonaListPayload(BaseModel):
    """LLM 生成的 persona 清單包裝。

    V1 只使用第一位 primary persona。

    Attributes:
        personas: Persona 清單（至少一位）。
    """

    personas: list[GeneratedPersonaPayload] = Field(default_factory=list, min_length=1)


class QuestionJudgementPayload(BaseModel):
    """Optional LLM classification for one task question."""

    question_id: str
    learner_answer: Any = None
    correctness: Literal["correct", "partial", "incorrect", "unanswered", "ungraded"]
    expected_answer: Any = None
    error_code: str | None = None
    historical_concept: str | None = None
    reasoning_process: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    classifier_confidence: float | None = None
    teacher_review_status: str = "unreviewed"


class TaskJudgementPayload(BaseModel):
    """Task 作答的輕量判斷結果。

    完整逐題評分後續再正規化。

    Attributes:
        result: 判斷結果（``"correct"`` / ``"partial"`` / ``"incorrect"``）。
        misconception_summary: Learner misconception 摘要。
        feedback: 給 learner 的回饋文字。
        score: 數值分數（可選）。
        provider: 執行判斷的 LLM provider 名稱。
    """

    result: Literal["correct", "partial", "incorrect"]
    misconception_summary: str
    feedback: str
    score: float | None = None
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
        "ELICIT_REASONING",
        "INSPECT_EVIDENCE",
        "CONTEXTUALIZE_OR_COMPARE",
        "REVISE_CLAIM",
        "REFLECT",
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
    completion_status: Literal["continue", "resolved", "complete"] | None = None
    fidelity_flags: list[str] = Field(default_factory=list)
