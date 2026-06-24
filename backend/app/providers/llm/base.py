from typing import Any, Protocol

from app.models.domain import (
    Annotation,
    Event,
    EventTask,
    ExperimentCondition,
    Persona,
    RagSource,
    RelatedEvent,
    TaskAttempt,
    WikiSource,
)


class LLMProvider(Protocol):
    async def generate_event_profile(self, event_name: str, sources: list[WikiSource]) -> dict[str, Any]: ...

    async def generate_task(self, event: Event, sources: list[WikiSource]) -> EventTask: ...

    async def judge_task_attempt(
        self,
        event: Event,
        task: EventTask,
        response_payload: dict[str, Any],
    ) -> dict[str, Any]: ...

    async def generate_personas(self, event: Event, sources: list[WikiSource]) -> list[Persona]:
        """產生事件的 primary historical persona；V1 預期只回傳一位。"""
        ...

    async def generate_greeting(
        self,
        event: Event,
        personas: list[Persona],
        condition: ExperimentCondition,
        attempt: TaskAttempt,
    ) -> str: ...

    async def generate_chat_response(
        self,
        event: Event,
        persona: Persona | None,
        condition: ExperimentCondition,
        task_attempt: TaskAttempt | None,
        user_message: str,
        prompt: str,
        rag_sources: list[RagSource],
    ) -> tuple[str, list[Annotation], list[RelatedEvent], str]: ...
