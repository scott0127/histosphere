"""Validated historical-persona profile and event-situated runtime context."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


PERSONA_PROMPT_CONTRACT_VERSION = "persona_prompt_v2"
PERSONA_RETRY_FLAGS = frozenset(
    {
        "persona_first_person_missing",
        "persona_identity_missing_on_opening",
        "persona_event_situation_missing_on_opening",
        "persona_out_of_character_meta_voice",
        "persona_temporal_boundary_violation",
        "persona_unverified_firsthand_claim",
    }
)


class PersonaPromptProfile(BaseModel):
    """Researcher-editable persona data; never a prewritten learner response."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["persona_prompt_v2"] = PERSONA_PROMPT_CONTRACT_VERSION
    speaking_style: str = Field(
        default="清楚、克制，以符合人物社會位置的第一人稱表達",
        validation_alias=AliasChoices("speaking_style", "voice"),
    )
    forms_of_address: str | None = None
    social_position: str = "未明確設定；不得自行捏造"
    relationship_to_event: str | None = None
    event_timepoint: str | None = None
    event_timepoint_year: int | None = None
    event_location: str | None = None
    event_vantage_point: str | None = None
    current_stakes: list[str] = Field(default_factory=list)
    event_anchor_terms: list[str] = Field(default_factory=list)
    knowledge_cutoff_year: int | None = None
    firsthand_experience_allowed: bool = False
    firsthand_experience_scope: list[str] = Field(default_factory=list)
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
    selection_policy: str | None = None
    selection_reason: str | None = None
    provider: str | None = None
    model: str | None = None
    # 生成 provenance 只供研究追蹤，不會被轉成 learner-facing persona 指令。
    llm_call: dict[str, Any] | None = None


def normalize_persona_prompt_profile(value: Any) -> dict[str, Any]:
    """Upgrade legacy profiles, including the seed-era ``voice`` key, to v2."""
    raw = dict(value) if isinstance(value, dict) else {}
    if "speaking_style" not in raw and raw.get("voice"):
        raw["speaking_style"] = raw["voice"]
    raw.pop("voice", None)
    raw["contract_version"] = PERSONA_PROMPT_CONTRACT_VERSION
    return PersonaPromptProfile.model_validate(raw).model_dump()


@dataclass(frozen=True)
class PersonaRuntimeContext:
    """Dynamic persona/event frame shared by the opening and every later turn."""

    persona_name: str
    persona_role: str
    persona_biography: str
    speaking_style: str
    forms_of_address: str
    social_position: str
    relationship_to_event: str
    event_name: str
    event_timeframe: str
    event_timepoint: str
    event_timepoint_year: int | None
    event_location: str
    event_vantage_point: str
    current_stakes: tuple[str, ...]
    event_description: str
    event_context: str
    temporal_boundary: str
    knowledge_cutoff_year: int | None
    firsthand_experience_allowed: bool
    firsthand_experience_scope: tuple[str, ...]
    geographic_boundary: str
    knowledge_boundary: str
    stance: str
    source_policy: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    anchor_terms: tuple[str, ...]

    def prompt_block(self, *, turn_kind: Literal["opening", "conversation"]) -> str:
        """Render policy plus data, without supplying reusable learner-facing prose."""
        stakes = "; ".join(self.current_stakes) or "Not explicitly specified; infer nothing beyond supplied facts."
        anchors = ", ".join(self.anchor_terms) or self.event_name
        turn_rule = (
            "This is the first persona turn. Compose fresh wording for this conversation. Briefly establish identity "
            "through the current event situation, not through a biography summary, then perform the interaction move. "
            "Do not reuse a stock introduction or mention the experiment condition."
            if turn_kind == "opening"
            else "Continue from the same event situation and persona viewpoint established earlier. Do not reintroduce the persona."
        )
        return (
            "Frame mode: event-situated first-person historical persona\n"
            f"Turn kind: {turn_kind}\n"
            f"Persona: {self.persona_name}\n"
            f"Role: {self.persona_role}\n"
            f"Biographical background (context only, not a script): {self.persona_biography}\n"
            f"Speaking style: {self.speaking_style}\n"
            f"Forms of address: {self.forms_of_address}\n"
            f"Social position: {self.social_position}\n"
            f"Relationship to event: {self.relationship_to_event}\n"
            f"Historical event: {self.event_name}\n"
            f"Event timeframe: {self.event_timeframe}\n"
            f"Selected in-event timepoint: {self.event_timepoint}\n"
            f"Selected in-event year: {self.event_timepoint_year or 'Not explicitly specified'}\n"
            f"Selected in-event location: {self.event_location}\n"
            f"Persona vantage point: {self.event_vantage_point}\n"
            f"Current stakes: {stakes}\n"
            f"Event description: {self.event_description}\n"
            f"Event context: {self.event_context}\n"
            f"Usable event anchors: {anchors}\n"
            f"Temporal boundary: {self.temporal_boundary}\n"
            f"Machine-readable knowledge cutoff year: {self.knowledge_cutoff_year or 'Not explicitly specified'}\n"
            f"Firsthand claims allowed: {self.firsthand_experience_allowed}\n"
            f"Allowed firsthand scope: {list(self.firsthand_experience_scope)}\n"
            f"Geographic boundary: {self.geographic_boundary}\n"
            f"Knowledge boundary: {self.knowledge_boundary}\n"
            f"Stance: {self.stance}\n"
            f"Source policy: {list(self.source_policy)}\n"
            f"Forbidden claims: {list(self.forbidden_claims)}\n"
            "Treat the event as unfolding around the persona at the selected timepoint. Speak from what this person "
            "could perceive, remember, believe, choose, or fear then; never narrate from a later historian's omniscient "
            "view. Do not invent an exact date, place, private thought, quotation, or eyewitness experience when the "
            "data does not establish it. Before identifying any person, object, institution, or concept mentioned by "
            "the learner, silently check whether it could be known before the knowledge cutoff. If it belongs to a "
            "later period, do not explain it with modern knowledge; state in persona voice that it is unknown or beyond "
            "the current time. Refer to later evidence as an external source rather than personal memory.\n"
            f"{turn_rule}"
        )


def build_persona_runtime_context(event: Any, persona: Any) -> PersonaRuntimeContext:
    """Build a conservative scene from persisted event and persona data."""
    profile = PersonaPromptProfile.model_validate(getattr(persona, "prompt_profile", {}))
    start_year = getattr(event, "start_year", None)
    end_year = getattr(event, "end_year", None)
    if start_year is None and end_year is None:
        timeframe = "Not explicitly specified"
    elif end_year is None or end_year == start_year:
        timeframe = str(start_year)
    else:
        timeframe = f"{start_year}-{end_year}"

    event_name = str(getattr(event, "canonical_name", "") or "Unspecified historical event")
    role = str(getattr(persona, "role", "") or "Not explicitly specified")
    profile_anchors = [str(item).strip() for item in profile.event_anchor_terms if str(item).strip()]
    expertise = [str(item).strip() for item in getattr(persona, "expertise_areas", []) if str(item).strip()]
    anchors = tuple(dict.fromkeys([event_name, *profile_anchors, *expertise]))

    return PersonaRuntimeContext(
        persona_name=str(getattr(persona, "name", "") or "Unspecified persona"),
        persona_role=role,
        persona_biography=str(getattr(persona, "biography", "") or "Not explicitly specified"),
        speaking_style=profile.speaking_style,
        forms_of_address=profile.forms_of_address or "Not explicitly specified; use a period-appropriate neutral form.",
        social_position=profile.social_position,
        relationship_to_event=profile.relationship_to_event or role,
        event_name=event_name,
        event_timeframe=timeframe,
        event_timepoint=profile.event_timepoint or timeframe,
        event_timepoint_year=profile.event_timepoint_year,
        event_location=profile.event_location or "Not explicitly specified; do not invent one.",
        event_vantage_point=profile.event_vantage_point or role,
        current_stakes=tuple(profile.current_stakes),
        event_description=str(getattr(event, "description", "") or "Not explicitly specified"),
        event_context=str(getattr(event, "context", "") or "Not explicitly specified"),
        temporal_boundary=profile.temporal_boundary,
        knowledge_cutoff_year=profile.knowledge_cutoff_year or profile.event_timepoint_year,
        firsthand_experience_allowed=profile.firsthand_experience_allowed,
        firsthand_experience_scope=tuple(profile.firsthand_experience_scope),
        geographic_boundary=profile.geographic_boundary,
        knowledge_boundary=profile.knowledge_boundary,
        stance=profile.stance,
        source_policy=tuple(profile.source_policy),
        forbidden_claims=tuple(profile.forbidden_claims),
        anchor_terms=anchors,
    )


def audit_persona_response(
    response_text: str,
    context: PersonaRuntimeContext,
    *,
    is_opening: bool,
) -> tuple[str, ...]:
    """Return deterministic persona-fidelity failures that require regeneration."""
    normalized = re.sub(r"\s+", "", response_text)
    flags: set[str] = set()
    first_person_markers = ("我", "我們", "本人", "本席", "吾", "寡人", "朕")
    if not any(marker in response_text for marker in first_person_markers):
        flags.add("persona_first_person_missing")
    identity_aliases = {
        re.sub(r"[\s·・\-]", "", item)
        for item in re.split(r"[\s·・\-]+", context.persona_name)
        if len(item.strip()) >= 2
    }
    identity_aliases.add(re.sub(r"[\s·・\-]", "", context.persona_name))
    if is_opening and not any(alias and alias in normalized for alias in identity_aliases):
        flags.add("persona_identity_missing_on_opening")
    meta_markers = (
        "作為AI",
        "身為AI",
        "我是AI",
        "作為語言模型",
        "我將扮演",
        "這位歷史人物",
        "根據歷史資料",
        "根據後世研究",
    )
    if any(marker in normalized for marker in meta_markers):
        flags.add("persona_out_of_character_meta_voice")
    explicit_years = {
        int(year)
        for year in re.findall(r"(?<!\d)(1[0-9]{3}|20[0-9]{2})(?!\d)", response_text)
    }
    future_uncertainty_markers = ("我不知道", "我無從得知", "尚未發生", "未來", "後人", "後世")
    if (
        context.knowledge_cutoff_year is not None
        and any(year > context.knowledge_cutoff_year for year in explicit_years)
        and not any(marker in normalized for marker in future_uncertainty_markers)
    ):
        flags.add("persona_temporal_boundary_violation")
    firsthand_markers = ("我親眼看見", "我親眼目睹", "我親自在場", "我親耳聽見")
    if (
        not context.firsthand_experience_allowed
        and any(marker in normalized for marker in firsthand_markers)
    ):
        flags.add("persona_unverified_firsthand_claim")
    if is_opening:
        compact_anchors = {
            re.sub(r"\s+", "", term)
            for term in context.anchor_terms
            if term and len(term.strip()) >= 2
        }
        situation_markers = (
            "此刻",
            "當此",
            "值此",
            "當下",
            "眼前",
            "身處",
            "正在",
            "正與",
            "面對",
            "面臨",
            "處於",
            "危機",
            "存亡",
            "戰爭",
            "衝突",
            "動盪",
            "壓力",
            "如今",
            "今日",
            "目前",
            "剛剛",
            "方才",
            "即將",
            "這場",
            "這次",
            "這裡",
            "局勢",
        )
        has_event_anchor = any(anchor in normalized for anchor in compact_anchors)
        has_in_event_situation = any(marker in normalized for marker in situation_markers)
        if not has_event_anchor or not has_in_event_situation:
            flags.add("persona_event_situation_missing_on_opening")
    return tuple(sorted(flags))
