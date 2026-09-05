"""Shared validation for opening and conversational LLM completions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.core.interaction_contract import (
    INTERACTION_RETRY_FLAGS,
    InteractionRuntime,
    enforce_interaction_response,
)
from app.core.persona_prompt_contract import (
    PERSONA_RETRY_FLAGS,
    PersonaRuntimeContext,
    audit_persona_response,
)
from app.providers.llm.base import ChatGenerationResult


INTERNAL_LEAK_MARKERS = (
    "01模式",
    "02模式",
    "03模式",
    "04模式",
    "ebl_roleplay",
    "ebl_no_roleplay",
    "no_ebl_roleplay",
    "no_ebl_no_roleplay",
    "實驗條件",
    "錯誤中學習模式",
    "interaction_runtime",
    "independent_1_prompt",
    "independent_2_prompt",
    "prompt module",
)

# 答案由背景語意觀察處理；生成模型的自評不具有獨立裁判資格。
ANSWER_OBSERVATION_FLAGS = frozenset({
    "early_answer_exposure", "next_answer_exposure", "corrective_answer_missing",
    "corrective_feedback_missing",
})


@dataclass(frozen=True)
class CompletionCandidateValidation:
    """Completion audit with an optional enforcement decision."""

    response: str
    metadata: dict[str, Any]
    retry_required: bool
    retry_flags: tuple[str, ...]


def validate_completion_candidate(
    *,
    runtime: InteractionRuntime,
    generation: ChatGenerationResult,
    persona_context: PersonaRuntimeContext | None,
    is_opening: bool,
) -> CompletionCandidateValidation:
    """Apply the same interaction and persona checks to every learner-facing turn."""

    interaction = enforce_interaction_response(
        runtime,
        generation.interaction_metadata,
        generation.response,
    )
    metadata = dict(interaction.metadata)
    flags = set(metadata.get("fidelity_flags", []))
    provider_flags = set(metadata.get("provider_fidelity_flags", []))
    flags.update(provider_flags - ANSWER_OBSERVATION_FLAGS)
    compact_response = generation.response.replace(" ", "").lower()
    if any(marker.replace(" ", "").lower() in compact_response for marker in INTERNAL_LEAK_MARKERS):
        flags.add("internal_condition_leak")

    persona_flags: tuple[str, ...] = ()
    if persona_context is not None:
        persona_flags = audit_persona_response(
            generation.response,
            persona_context,
            is_opening=is_opening,
        )
        flags.update(persona_flags)

    retry_flags = set()
    retry_flags.update(set(metadata.get("fidelity_flags", [])) & INTERACTION_RETRY_FLAGS)
    retry_flags.update(
        flag
        for flag in provider_flags
        if (runtime.interaction_mode == "scaffold" and flag in INTERACTION_RETRY_FLAGS)
        or (persona_context is not None and flag in PERSONA_RETRY_FLAGS)
    )
    retry_flags.update(flag for flag in persona_flags if flag in PERSONA_RETRY_FLAGS)
    if "internal_condition_leak" in flags:
        retry_flags.add("internal_condition_leak")

    metadata["persona_fidelity_flags"] = list(persona_flags)
    metadata["fidelity_flags"] = sorted(flags)
    enforce_content = get_settings().llm_content_validation_enabled
    # 觀察模式保留原文與旗標，避免舊內容規則觸發重生；狀態正規化仍維持。
    metadata["content_validation_mode"] = "enforce" if enforce_content else "observe"
    metadata["content_validation_would_retry"] = bool(retry_flags)
    metadata["content_validation_flags"] = sorted(retry_flags)
    metadata["fidelity_retry_required"] = enforce_content and bool(retry_flags)
    if not enforce_content:
        metadata["raw_interaction_metadata"] = dict(generation.interaction_metadata or {})
        metadata.pop("rejected_response_sha256", None)
        metadata.pop("rejected_response_length", None)
    return CompletionCandidateValidation(
        response=interaction.response if enforce_content else generation.response,
        metadata=metadata,
        retry_required=enforce_content and bool(retry_flags),
        retry_flags=tuple(sorted(retry_flags)) if enforce_content else (),
    )
