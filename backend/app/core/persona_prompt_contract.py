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
        "persona_modern_tutor_register",
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
            "This is the first persona turn. Within the first two sentences, naturally state the persona's name and place "
            "them in the supplied event situation through an anchor plus a current pressure, choice, or conflict. Do not "
            "summarize the biography, reuse a stock introduction, or reveal a target-answer clue. This is the only turn "
            "required to establish the identity and scene. Then perform the selected interaction move."
            if turn_kind == "opening"
            else (
                "Treat the identity and event situation as already established. Do not reintroduce the persona or repeat the "
                "event title, year, location, or current stakes merely to prove persona fidelity. Repeat a scene anchor only "
                "when the learner asks about it, appears confused about the setting, or it is necessary for the current reply. "
                "Respond from the person's priorities and position rather than adding a generic salutation to tutor prose."
            )
        )
        return (
            "[persona_facts]\n"
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
            "[persona_rendering_rules]\n"
            "Treat every persona fact above as a silent internal constraint, not a checklist to recite to the learner. "
            "The separate event_context module is the canonical event description. Treat it as unfolding around the persona "
            "at the selected timepoint. The persona is speaking because the learner's claim bears on a supplied duty, stake, "
            "conflict, judgment, or decision; let one such resource shape the substance whenever Disclosure permits, without "
            "reciting the profile labels. Speaking style is a behavioral instruction, not a list of adjectives: it must affect "
            "which concern the person notices, how the person frames the issue, and the sentence rhythm. A name or form of "
            "address alone does not create persona fidelity, and forms of address need not appear in every turn. Maintain a first-person viewpoint "
            "overall, but allow natural Chinese subject omission instead of forcing a first-person pronoun into every turn. "
            "Speak from what this person "
            "could perceive, remember, believe, choose, or fear then; never narrate from a later historian's omniscient "
            "view. Do not invent an exact date, place, private thought, quotation, or eyewitness experience when the "
            "data does not establish it. Before identifying any person, object, institution, or concept mentioned by "
            "the learner, silently check whether it could be known before the knowledge cutoff. If it belongs to a "
            "later period, do not explain it with modern knowledge; state in persona voice that it is unknown or beyond "
            "the current time. Refer to later evidence as an external source rather than personal memory. Use readable "
            "Traditional Chinese as a careful translation of the person's likely register; preserve the configured "
            "rhythm, concerns, and social position without inventing verbatim quotations, dialect, or theatrical archaic "
            "speech. Never fall back to a modern teacher, quiz host, or policy-enforcement voice. Obey the interaction "
            "module's content and Disclosure limits even when stronger persona detail would be tempting.\n"
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
    # 中文後續對話常省略主詞；只有開場必須明確建立第一人稱視角。
    if is_opening and not any(marker in response_text for marker in first_person_markers):
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
    # 只攔截明確的現代課堂／系統話術；一般反問與自然引導仍保留給人物語氣。
    modern_tutor_markers = (
        "請回到我們正在談論",
        "請回到目前討論",
        "回到目前的主題",
        "目前的討論主題",
        "根據題目",
        "這道題",
        "你的答案",
        "請使用證據",
        "歷史思考",
        "學習目標",
        "錯誤中學習",
        "EBL",
        "Disclosure",
        "請重新檢視",
        "請重新思考",
        "請用自己的話",
        "再用自己的話",
        "請重新選定一個選項",
        "現在請把原來的選項",
        "請回頭檢查你自己的",
        "你這次已經看出",
        "修正後的答案",
        "如何改寫原先",
    )
    if any(marker in normalized for marker in modern_tutor_markers):
        flags.add("persona_modern_tutor_register")
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
            for term in (*context.anchor_terms, context.event_name, context.event_location)
            if term and len(term.strip()) >= 2
        }
        situation_markers = (
            "此刻",
            "當此",
            "值此",
            "當下",
            "眼前",
            "身在",
            "身處",
            "置身",
            "正值",
            "正逢",
            "處在",
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
            "逼近",
            "抉擇",
            "這場",
            "這次",
            "這裡",
            "局勢",
        )
        has_event_anchor = any(anchor in normalized for anchor in compact_anchors)
        if context.event_timepoint_year is not None:
            has_event_anchor = has_event_anchor or context.event_timepoint_year in explicit_years
        has_in_event_situation = any(marker in normalized for marker in situation_markers)
        if not has_event_anchor or not has_in_event_situation:
            flags.add("persona_event_situation_missing_on_opening")
    return tuple(sorted(flags))
