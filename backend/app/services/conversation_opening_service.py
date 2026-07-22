"""Canonical first-turn generation for every experiment condition."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.core.interaction_contract import build_interaction_runtime
from app.core.persona_prompt_contract import build_persona_runtime_context
from app.models.domain import Event, ExperimentCondition, Persona, TaskAttempt
from app.providers.llm.base import ChatGenerationResult, LLMProvider
from app.services.completion_validation import validate_completion_candidate
from app.services.llm_generation_audit import record_rejected_generation
from app.services.prompt_service import PromptModule, PromptService


MAX_OPENING_GENERATION_ATTEMPTS = 3


class OpeningValidationError(RuntimeError):
    """All opening candidates failed without exposing their response text."""

    def __init__(self, rejected_candidates: list[dict[str, Any]]) -> None:
        self.rejected_candidates = rejected_candidates
        flags = sorted(
            {
                str(flag)
                for candidate in rejected_candidates
                for flag in candidate.get("flags", [])
            }
        )
        super().__init__(
            "Opening completion failed interaction/persona validation after "
            f"{MAX_OPENING_GENERATION_ATTEMPTS} attempts; flags={','.join(flags) or 'unknown'}"
        )


@dataclass(frozen=True)
class ConversationOpening:
    """A validated first turn plus non-visible reproducibility metadata."""

    generation: ChatGenerationResult
    metadata: dict[str, Any]
    persona: Persona | None
    prompt: str
    modules: tuple[PromptModule, ...]


class ConversationOpeningService:
    """Generate the opening through the same prompt and validation contracts as chat."""

    def __init__(self, llm_provider: LLMProvider, prompt_service: PromptService) -> None:
        self.llm_provider = llm_provider
        self.prompt_service = prompt_service

    async def generate(
        self,
        *,
        event: Event,
        personas: list[Persona],
        condition: ExperimentCondition,
        attempt: TaskAttempt,
    ) -> ConversationOpening:
        persona = self._select_persona(personas, condition)
        runtime = build_interaction_runtime(condition, attempt, [])
        modules = self.prompt_service.assemble_opening_modules(
            event=event,
            persona=persona,
            condition=condition,
            task_attempt=attempt,
        )
        base_prompt = self.prompt_service.render_modules(modules)
        persona_context = build_persona_runtime_context(event, persona) if persona else None
        rejected_candidates: list[dict[str, Any]] = []
        accumulated_retry_flags: set[str] = set()
        prompt = base_prompt

        for generation_index in range(MAX_OPENING_GENERATION_ATTEMPTS):
            generation = await self.llm_provider.generate_greeting(
                event=event,
                personas=[persona] if persona else [],
                condition=condition,
                attempt=attempt,
                prompt=prompt,
            )
            validation = validate_completion_candidate(
                runtime=runtime,
                generation=generation,
                persona_context=persona_context,
                is_opening=True,
            )
            if not validation.retry_required:
                metadata = {
                    **validation.metadata,
                    "generation_retry_count": generation_index,
                    "rejected_candidates": rejected_candidates,
                }
                return ConversationOpening(
                    generation=ChatGenerationResult(
                        response=validation.response,
                        annotations=generation.annotations,
                        related_events=generation.related_events,
                        dynamic_context=generation.dynamic_context,
                        interaction_metadata=metadata,
                    ),
                    metadata=metadata,
                    persona=persona,
                    prompt=base_prompt,
                    modules=tuple(modules),
                )

            runner = getattr(self.llm_provider, "runner", None)
            audit_id = record_rejected_generation(
                stage="opening_contract_validation",
                provider=str(getattr(runner, "last_provider", "unknown")),
                model=str(getattr(runner, "last_model", "unknown")),
                task_name="conversation_opening",
                raw_output=generation.response,
                reasons=list(validation.retry_flags),
                context={
                    "event_id": event.id,
                    "attempt_id": attempt.id,
                    "condition_key": condition.condition_key,
                    "generation_index": generation_index,
                },
            )
            rejected_candidates.append(
                {
                    "audit_id": audit_id,
                    "sha256": hashlib.sha256(generation.response.encode("utf-8")).hexdigest(),
                    "length": len(generation.response),
                    "flags": list(validation.retry_flags),
                }
            )
            accumulated_retry_flags.update(validation.retry_flags)
            prompt = self.prompt_service.build_retry_prompt(
                base_prompt,
                tuple(sorted(accumulated_retry_flags)),
            )

        raise OpeningValidationError(rejected_candidates)

    @staticmethod
    def _select_persona(
        personas: list[Persona],
        condition: ExperimentCondition,
    ) -> Persona | None:
        if not condition.roleplay_enabled:
            return None
        if not personas:
            raise RuntimeError("Role-play condition requires an active historical persona")
        return personas[0]
