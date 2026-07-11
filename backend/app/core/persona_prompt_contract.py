"""Validated persona prompt profile contract used by every completion."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PersonaPromptProfile(BaseModel):
    """Versioned, conservative defaults for historical persona boundaries."""

    model_config = ConfigDict(extra="allow")

    contract_version: Literal["persona_prompt_v1"] = "persona_prompt_v1"
    speaking_style: str = "清楚、克制，以符合人物社會位置的第一人稱表達"
    social_position: str = "未明確設定；不得自行捏造"
    temporal_boundary: str = "不得知道人物生命與事件時間邊界之後的資訊"
    geographic_boundary: str = "僅能聲稱合理接觸過的地域與文化資訊"
    knowledge_boundary: str = "只使用人物依其時代、身份與可得來源能合理知道的資訊"
    stance: str = "保留人物立場，但不可把立場宣稱為客觀全知事實"
    source_policy: list[str] = Field(default_factory=lambda: ["不捏造引文或史料", "不聲稱未知的私人心理"])
    forbidden_claims: list[str] = Field(
        default_factory=lambda: ["時代錯置的知識", "未有來源支持的親身經歷", "全知歷史旁白"]
    )
    teacher_notes: str = ""
    deliberate_error_enabled: bool = False


def normalize_persona_prompt_profile(value: Any) -> dict[str, Any]:
    """Upgrade legacy dict profiles to the versioned contract while preserving extras."""
    raw = value if isinstance(value, dict) else {}
    return PersonaPromptProfile.model_validate(raw).model_dump()
