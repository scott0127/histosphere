"""Event initialization service.

本模組負責 V1 的起始流程：接收歷史事件名稱、抓取 Wikipedia、
建立 events/wiki_sources/event_tasks/primary persona，並建立 experiment session。
注意：這裡不建立 conversation，conversation 會等 learner 完成 task 後才建立。
"""

from fastapi import HTTPException, status

from app.core.experiment_conditions import condition_code_for_key
from app.crud.protocols import RepositoryProtocol
from app.models.domain import Event, EventTask, ExperimentSession, ResearchLog
from app.providers.llm.base import LLMProvider
from app.providers.wikipedia_provider import WikipediaProvider
from app.schemas.requests import EventInitializeRequest
from app.schemas.responses import EventInitializeResponse
from app.services.event_service import EventService
from app.utils.text_normalizer import normalize_display_text


class EventInitializationService:
    """建立可被 learner 使用的事件學習工作區。"""

    def __init__(
        self,
        repository: RepositoryProtocol,
        wikipedia_provider: WikipediaProvider,
        llm_provider: LLMProvider,
    ) -> None:
        self.repository = repository
        self.wikipedia_provider = wikipedia_provider
        self.llm_provider = llm_provider

    async def initialize(
        self,
        request: EventInitializeRequest,
        *,
        admin_override: bool = False,
    ) -> EventInitializeResponse:
        """初始化事件、task、primary persona 與 session，供前端導向 task 頁。"""
        event_name = normalize_display_text(request.event_name.strip()) or request.event_name.strip()
        if not event_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event name is required")

        condition = self.repository.get_condition_by_key(request.condition_key)
        if not condition or not condition.active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment condition not found")

        if not admin_override:
            self._validate_participant_assignment(request.user_id, condition.condition_key)

        existing = self.repository.find_event_by_name(event_name)
        archived = self.repository.find_event_by_name(event_name, include_archived=True)
        if archived and archived.archived_at and not existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Historical event is archived. An admin must restore it before use.",
            )
        rebuild_ignored = bool(existing and request.rebuild)

        if existing:
            # 已存在事件可重用，但仍要補齊 task/primary persona，避免舊資料不完整。
            event = existing
            sources = self.repository.list_wiki_sources(event.id)
            task = self._ensure_task(event, sources)
            personas = await self._ensure_personas(event, sources)
        else:
            if not admin_override:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only an admin can create new historical event materials.",
                )
            draft_event = Event(canonical_name=event_name)
            # Supabase 有 foreign key 約束；必須先建立 event row，wiki_sources 才能引用 event_id。
            event = self.repository.save_event(draft_event)
            sources = await self.wikipedia_provider.fetch_sources(draft_event.id, event_name, fetch_mode="full")
            for source in sources:
                self.repository.save_wiki_source(source)

            profile = await self.llm_provider.generate_event_profile(event_name, sources)
            profiled_event = EventService.build_event_from_profile(event_name, profile)
            profiled_event.id = event.id
            event = self.repository.save_event(profiled_event)

            task = await self.llm_provider.generate_task(event, sources)
            task = self.repository.save_event_task(task)

            personas = await self._generate_primary_persona(event, sources)

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
                    "rebuild_ignored": rebuild_ignored,
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

    def _validate_participant_assignment(self, user_id: str | None, condition_key: str) -> None:
        """Enforce the Auth user to participant condition assignment at session creation."""
        normalized_user_id = (user_id or "").strip()
        if not normalized_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A participant-bound Supabase Auth user is required.",
            )

        participant = self.repository.get_participant_by_auth_user(normalized_user_id)
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Participant mapping not found for this Auth user.",
            )
        if participant.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Participant {participant.code} is not active.",
            )

        assigned_code = condition_code_for_key(condition_key)
        if assigned_code not in participant.condition_list:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Condition {assigned_code} is not assigned to participant {participant.code}.",
            )

    def _ensure_task(self, event: Event, sources) -> EventTask:
        """確保事件至少有一份可作答 task；缺少時建立保守 fallback。"""
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
        """確保事件有一位 primary persona；舊資料若有多位，只回傳排序第一位。"""
        personas = self.repository.list_personas(event.id)
        if personas:
            return personas[:1]
        return await self._generate_primary_persona(event, sources)

    async def _generate_primary_persona(self, event: Event, sources) -> list:
        """用 LLM provider 產生最能代表事件的一位 historical persona。"""
        generated_personas = await self.llm_provider.generate_personas(event, sources)
        if not generated_personas:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Persona generation failed")
        primary_persona = generated_personas[0]
        primary_persona.sort_order = 0
        return [self.repository.save_persona(primary_persona)]
