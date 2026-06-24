"""Structured LLM output schemas.

本模組定義 LLM 必須回傳的 JSON 結構。Provider 只能把通過 Pydantic
驗證的資料交給 service，避免研究流程吃到鬆散或不可追蹤的自然語言輸出。
"""

from typing import Literal

from pydantic import BaseModel, Field


class EventProfilePayload(BaseModel):
    """事件基本資料；缺乏可信資訊時欄位可為 None 或寫入不詳。"""

    canonical_name: str
    description: str
    century: int | None = None
    start_year: int | None = None
    end_year: int | None = None
    context: str
    source_summary: dict = Field(default_factory=dict)


class GeneratedTaskPayload(BaseModel):
    """Prototype task 初稿；正式實驗可由教師在 admin 覆蓋。"""

    title: str
    story_text: str
    display_text: str
    evaluation_payload: dict = Field(default_factory=dict)


class GeneratedPersonaPayload(BaseModel):
    """單一 primary historical persona。"""

    name: str
    english_name: str | None = None
    role: str | None = None
    biography: str | None = None
    expertise_areas: list[str] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    prompt_profile: dict = Field(default_factory=dict)


class PersonaListPayload(BaseModel):
    """V1 只使用第一位 primary persona。"""

    personas: list[GeneratedPersonaPayload] = Field(default_factory=list, min_length=1)


class TaskJudgementPayload(BaseModel):
    """Task 作答的輕量判斷結果；完整逐題評分後續再正規化。"""

    result: Literal["correct", "partial", "incorrect"]
    misconception_summary: str
    feedback: str
    score: float | None = None
    provider: str = "litellm"


class ChatOutputPayload(BaseModel):
    """聊天回覆結構。"""

    response: str
    annotations: list[dict] = Field(default_factory=list)
    related_events: list[dict] = Field(default_factory=list)
    dynamic_context: str = ""
