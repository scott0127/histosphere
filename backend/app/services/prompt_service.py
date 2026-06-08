from app.models.domain import Event, ExperimentCondition, Persona, RagSource, TaskAttempt


class PromptService:
    def assemble_chat_prompt(
        self,
        event: Event,
        persona: Persona | None,
        condition: ExperimentCondition,
        task_attempt: TaskAttempt | None,
        user_message: str,
        rag_sources: list[RagSource],
    ) -> str:
        modules = [
            self._condition_policy(condition),
            self._event_context(event),
            self._learner_misconception_context(task_attempt),
            self._source_context(rag_sources),
            self._speaker_context(persona, condition),
            f"[user_message]\n{user_message}",
        ]
        if persona and persona.prompt_profile.get("deliberate_error_enabled") is True:
            modules.append(self._deliberate_error_slot())
        return "\n\n".join(module for module in modules if module)

    @staticmethod
    def _condition_policy(condition: ExperimentCondition) -> str:
        if condition.response_policy == "scaffold":
            return (
                "[condition_policy]\n"
                "Use Error-Based Learning. Treat learner misconceptions as productive errors. "
                "Guide historical thinking, evidence-based argumentation, source interpretation, and critical reflection. "
                "Do not directly reveal the final answer before the learner attempts self-correction."
            )
        return (
            "[condition_policy]\n"
            "Use a direct-answer style. Give a concise answer first, then explain the historical context."
        )

    @staticmethod
    def _event_context(event: Event) -> str:
        return (
            "[event_context]\n"
            f"Canonical event name: {event.canonical_name}\n"
            f"Description: {event.description or '不詳'}\n"
            f"Century: {event.century if event.century is not None else '不詳'}\n"
            f"Years: {event.start_year if event.start_year is not None else '不詳'}"
            f" - {event.end_year if event.end_year is not None else '不詳'}\n"
            f"Context: {event.context or '不詳'}"
        )

    @staticmethod
    def _learner_misconception_context(task_attempt: TaskAttempt | None) -> str:
        if not task_attempt:
            return "[learner_task]\nNo task attempt is attached."
        return (
            "[learner_task]\n"
            f"Response payload: {task_attempt.response_payload}\n"
            f"LLM judgement: {task_attempt.judgement_payload}"
        )

    @staticmethod
    def _source_context(rag_sources: list[RagSource]) -> str:
        if not rag_sources:
            return "[source_context]\nNo RAG retrieval is enabled in V1. Use event context and known historical boundaries."
        sources = "\n".join(f"- {source.section_title}: {source.content}" for source in rag_sources)
        return f"[source_context]\n{sources}"

    @staticmethod
    def _speaker_context(persona: Persona | None, condition: ExperimentCondition) -> str:
        if not condition.roleplay_enabled or not persona:
            return (
                "[speaker_context]\n"
                "You are a generic AI tutor/chatbot, not a historical persona. "
                "Do not pretend to be a historical figure."
            )
        return (
            "[speaker_context]\n"
            f"You are {persona.name}, role: {persona.role or '不詳'}.\n"
            f"Biography: {persona.biography or '不詳'}\n"
            f"Expertise: {', '.join(persona.expertise_areas) or '不詳'}\n"
            f"Prompt profile: {persona.prompt_profile}\n"
            "Speak from the persona perspective, but keep historical boundaries explicit."
        )

    @staticmethod
    def _deliberate_error_slot() -> str:
        return (
            "[deliberate_error_slot]\n"
            "Reserved for controlled AI-generated inaccuracies. Disabled in V1 unless explicitly enabled by admin."
        )
