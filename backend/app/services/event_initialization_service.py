from fastapi import HTTPException, status

from app.crud.protocols import RepositoryProtocol
from app.models.domain import Event, EventTask, ExperimentSession, ResearchLog
from app.providers.llm.base import LLMProvider
from app.providers.wikipedia_provider import WikipediaProvider
from app.schemas.requests import EventInitializeRequest
from app.schemas.responses import EventInitializeResponse
from app.services.event_service import EventService


class EventInitializationService:
    def __init__(
        self,
        repository: RepositoryProtocol,
        wikipedia_provider: WikipediaProvider,
        llm_provider: LLMProvider,
    ) -> None:
        self.repository = repository
        self.wikipedia_provider = wikipedia_provider
        self.llm_provider = llm_provider

    async def initialize(self, request: EventInitializeRequest) -> EventInitializeResponse:
        event_name = request.event_name.strip()
        if not event_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event name is required")

        condition = self.repository.get_condition_by_key(request.condition_key)
        if not condition or not condition.active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment condition not found")

        existing = self.repository.find_event_by_name(event_name)
        if existing and request.rebuild:
            self.repository.delete_event(existing.id)
            existing = None

        if existing:
            event = existing
            sources = self.repository.list_wiki_sources(event.id)
            task = self._ensure_task(event, sources)
            personas = await self._ensure_personas(event, sources)
        else:
            draft_event = Event(canonical_name=event_name)
            sources = await self.wikipedia_provider.fetch_sources(draft_event.id, event_name, fetch_mode="full")
            for source in sources:
                self.repository.save_wiki_source(source)

            profile = await self.llm_provider.generate_event_profile(event_name, sources)
            event = EventService.build_event_from_profile(event_name, profile)
            event.id = draft_event.id
            event = self.repository.save_event(event)

            task = await self.llm_provider.generate_task(event, sources)
            task = self.repository.save_event_task(task)

            generated_personas = await self.llm_provider.generate_personas(event, sources)
            personas = [
                self.repository.save_persona(persona)
                for persona in generated_personas[:3]
            ]

        session = self.repository.save_session(
            ExperimentSession(
                condition_id=condition.id,
                condition_key_snapshot=condition.condition_key,
                user_id=request.user_id,
                event_id=event.id,
            )
        )
        self.repository.log_research(
            ResearchLog(
                user_id=request.user_id,
                session_id=session.id,
                event_id=event.id,
                task_id=task.id,
                action_type="event_initialized",
                payload={
                    "event_name": event_name,
                    "condition_key": condition.condition_key,
                    "rebuild": request.rebuild,
                },
            )
        )

        return EventInitializeResponse(
            event_id=event.id,
            session_id=session.id,
            event=event,
            task=task,
            personas=personas,
            condition=condition,
        )

    def _ensure_task(self, event: Event, sources) -> EventTask:
        task = self.repository.get_latest_event_task(event.id)
        if task:
            return task
        fallback_text = event.context or event.description or event.canonical_name
        return self.repository.save_event_task(
            EventTask(
                event_id=event.id,
                title=f"{event.canonical_name}：歷史故事挖洞",
                story_text=fallback_text,
                display_text=f"{event.canonical_name} 的核心脈絡包含「____」、「____」與「____」。",
                evaluation_payload={"rubric": "Teacher review required."},
                revision_state="manual",
            )
        )

    async def _ensure_personas(self, event: Event, sources) -> list:
        personas = self.repository.list_personas(event.id)
        if personas:
            return personas
        return [
            self.repository.save_persona(persona)
            for persona in (await self.llm_provider.generate_personas(event, sources))[:3]
        ]
