"""Event initialization service.

本模組負責 V1 的起始流程：接收歷史事件名稱、抓取 Wikipedia、
建立 events/wiki_sources/event_tasks/primary persona，並建立 experiment session。
注意：這裡不建立 conversation，conversation 會等 learner 完成 task 後才建立。
"""

from fastapi import HTTPException, status

from app.core.experiment_conditions import condition_code_for_key
from app.core.research_reproducibility import get_session_task, record_session_material_snapshot
from app.crud.protocols import RepositoryProtocol
from app.models.domain import Event, EventTask, ExperimentCondition, ExperimentSession, Participant, ResearchLog
from app.providers.llm.base import LLMProvider
from app.providers.wikipedia_provider import WikipediaProvider
from app.schemas.requests import EventInitializeRequest
from app.schemas.responses import EventInitializeResponse
from app.services.event_service import EventService
from app.services.participant_assignments import participant_activity_assignments, session_matches_activity
from app.services.participant_preview import active_preview_participant, preview_user_id
from app.services.session_runtime import expire_session_if_due
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
        is_participant_preview = request.preview_participant_id is not None
        if is_participant_preview and not admin_override:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an admin can preview a participant assignment.",
            )
        event_name = normalize_display_text(request.event_name.strip()) or request.event_name.strip()
        if not event_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event name is required")

        condition = self.repository.get_condition_by_key(request.condition_key)
        if not condition or not condition.active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment condition not found")

        participant = None
        preview_context = {}
        if is_participant_preview:
            participant = active_preview_participant(self.repository, request.preview_participant_id)
            self._validate_condition_assignment(participant, condition.condition_key)
            request = request.model_copy(update={"user_id": preview_user_id(participant.id)})
            preview_context = {
                "preview_participant_id": participant.id,
                "preview_participant_code": participant.code,
                "preview_condition_list": list(participant.condition_list),
            }
        elif not admin_override:
            participant = self._validate_participant_assignment(request.user_id, condition.condition_key)
        activity_assignments = participant_activity_assignments(participant) if participant else None
        if activity_assignments is not None:
            preview_context["activity_assignments"] = activity_assignments

        existing = self.repository.find_event_by_name(event_name)
        archived = self.repository.find_event_by_name(event_name, include_archived=True)
        if archived and archived.archived_at and not existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Historical event is archived. An admin must restore it before use.",
            )
        rebuild_ignored = bool(existing and request.rebuild)

        learner_session = None
        if existing:
            # 已存在事件可重用；人物啟用狀態只能由 Admin 管理。
            event = existing
            if not admin_override or is_participant_preview:
                if activity_assignments is not None and not any(
                    item["event_id"] == event.id
                    and item["condition_code"] == condition_code_for_key(condition.condition_key)
                    for item in activity_assignments
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="此事件與模式不符合受測者的活動分派，請選擇已分派的活動。",
                    )
                learner_session = self._learner_session_for_event(
                    request.user_id, event.id, admin_test=is_participant_preview,
                )
                self._validate_participant_execution_order(
                    participant,
                    condition.condition_key,
                    learner_session,
                    session_user_id=request.user_id,
                    admin_test=is_participant_preview,
                )
                if not admin_override and not learner_session and not event.materials_locked_at:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Historical event materials are not locked for the experiment.",
                    )
            sources = self.repository.list_wiki_sources(event.id)
            task = self._ensure_task(event, sources)
            personas = self._ensure_personas(event, condition)
        else:
            if is_participant_preview:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Participant preview requires an existing historical event.",
                )
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

        if learner_session:
            if (
                participant
                and not is_participant_preview
                and learner_session.participant_id
                and learner_session.participant_id != participant.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Session belongs to another participant assignment",
                )
            # 舊 Session 若尚未凍結 participant 對應，於合法本人恢復時補上。
            if participant and not is_participant_preview and not learner_session.participant_id:
                learner_session.participant_id = participant.id
                learner_session = self.repository.save_session(learner_session)
            attempt = self.repository.get_task_attempt_for_session(learner_session.id)
            task = get_session_task(self.repository, learner_session, attempt)
            if not task:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The original session task is unavailable.")
            session_condition = self.repository.get_condition_by_key(learner_session.condition_key_snapshot)
            if not session_condition:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The existing experiment session condition is unavailable. Ask an admin to review it.",
                )
            self.repository.log_research(
                ResearchLog(
                    user_id=request.user_id,
                    session_id=learner_session.id,
                    event_id=event.id,
                    task_id=task.id,
                    action_type="event_session_resumed",
                    payload={
                        "event_name": event_name,
                        "condition_key": learner_session.condition_key_snapshot,
                        "requested_condition_key": condition.condition_key,
                        **preview_context,
                    },
                )
            )
            return EventInitializeResponse(
                event_id=event.id,
                session_id=learner_session.id,
                event=event,
                task=task,
                personas=personas,
                condition=session_condition,
            )

        session = self.repository.save_session(
            ExperimentSession(
                condition_id=condition.id,
                condition_key_snapshot=condition.condition_key,
                user_id=request.user_id,
                participant_id=participant.id if participant and not is_participant_preview else None,
                event_id=event.id,
                is_admin_test=admin_override,
            )
        )
        record_session_material_snapshot(self.repository, session)
        material_llm_calls = [
            call
            for call in (
                event.source_summary.get("llm_call"),
                task.evaluation_payload.get("llm_call"),
                *(persona.prompt_profile.get("llm_call") for persona in personas),
            )
            if isinstance(call, dict)
        ]
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
                    "material_llm_calls": material_llm_calls,
                    **preview_context,
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

    def _learner_session_for_event(
        self,
        user_id: str | None,
        event_id: str,
        *,
        admin_test: bool = False,
    ) -> ExperimentSession | None:
        """接續同事件的有效 session；完成過的事件必須由管理員重建。"""
        matching_sessions = [
            expire_session_if_due(self.repository, session)
            for session in self.repository.list_sessions_for_user((user_id or "").strip())
            if session.event_id == event_id
            and session.status != "archived"
            and session.is_admin_test == admin_test
        ]
        if any(session.status == "completed" for session in matching_sessions):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This historical event has already been completed. "
                    "An admin must archive the previous session and create a new one."
                ),
            )
        return next(
            (
                session
                for session in matching_sessions
                if session.status in {"initialized", "task_submitted", "conversation_started"}
            ),
            None,
        )

    def _validate_participant_assignment(self, user_id: str | None, condition_key: str) -> Participant:
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

        self._validate_condition_assignment(participant, condition_key)
        return participant

    @staticmethod
    def _validate_condition_assignment(participant: Participant, condition_key: str) -> None:
        participant_activity_assignments(participant)
        assigned_code = condition_code_for_key(condition_key)
        if assigned_code not in participant.condition_list:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Condition {assigned_code} is not assigned to participant {participant.code}.",
            )

    def _validate_participant_execution_order(
        self,
        participant: Participant | None,
        condition_key: str,
        learner_session: ExperimentSession | None,
        *,
        session_user_id: str | None = None,
        admin_test: bool = False,
    ) -> None:
        """只允許接續目前 Session，或開始 Admin 分派順序中的下一個 Condition。"""
        progress_user_id = session_user_id or (participant.auth_user_id if participant else None)
        if participant is None or not progress_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Participant mapping is required before starting an experiment.",
            )

        requested_code = condition_code_for_key(condition_key)
        activity_assignments = participant_activity_assignments(participant)
        scoped_sessions = [
            session
            for session in self.repository.list_sessions_for_user(progress_user_id)
            if session.status != "archived" and session.is_admin_test == admin_test
            and (admin_test or not session.participant_id or session.participant_id == participant.id)
        ]
        if activity_assignments is not None and any(
            not session_matches_activity(session, activity_assignments) for session in scoped_sessions
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="既有活動進度與目前分派的事件、模式不一致，請管理員確認原配對或封存相關紀錄。",
            )
        assigned_sessions = [expire_session_if_due(self.repository, session) for session in scoped_sessions]
        active_sessions = [
            session
            for session in assigned_sessions
            if session.status in {"initialized", "task_submitted", "conversation_started"}
        ]
        if active_sessions:
            current_session = max(active_sessions, key=lambda session: session.updated_at)
            current_code = condition_code_for_key(current_session.condition_key_snapshot)
            if (
                learner_session is None
                or learner_session.id != current_session.id
                or requested_code != current_code
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Participant {participant.code} must resume Condition {current_code} "
                        "before starting another assigned condition."
                    ),
                )
            return

        finished_sessions = []
        for session in assigned_sessions:
            if session.status != "completed":
                continue
            posttest = self.repository.get_posttest(session.id)
            if not posttest or posttest.stage != "completed":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="請先完成上一輪的活動回饋與歷史思考後測，再開始下一輪。",
                )
            finished_sessions.append(session)

        completed_codes = {
            condition_code_for_key(session.condition_key_snapshot)
            for session in finished_sessions
            if activity_assignments is None or session_matches_activity(session, activity_assignments)
        }
        expected_code = next(
            (code for code in participant.condition_list if code not in completed_codes),
            None,
        )
        if expected_code is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Participant {participant.code} has completed all assigned conditions.",
            )
        if requested_code != expected_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Participant {participant.code} must complete Condition {expected_code} "
                    f"before Condition {requested_code}."
                ),
            )

    def _ensure_task(self, event: Event, sources) -> EventTask:
        """缺少正式題目時明確停止，不臨時捏造沒有理由標準的替代題。"""
        task = self.repository.get_latest_event_task(event.id)
        if task:
            return task
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This event needs an Error-Elicitation Task prepared by an admin before it can start.",
        )

    def _ensure_personas(
        self,
        event: Event,
        condition: ExperimentCondition,
    ) -> list:
        """讀取 Admin 設定的人物；Learner 流程不得自行建立或啟用人物。"""
        personas = self.repository.list_personas(event.id)
        if len(personas) > 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Event has more than one active historical persona",
            )
        if personas:
            return personas
        if condition.roleplay_enabled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Role-play requires one active historical persona configured by an admin",
            )
        return []

    async def _generate_primary_persona(self, event: Event, sources) -> list:
        """用 LLM provider 產生最能代表事件的一位 historical persona。"""
        generated_personas = await self.llm_provider.generate_personas(event, sources)
        if not generated_personas:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Persona generation failed")
        primary_persona = generated_personas[0]
        primary_persona.sort_order = 0
        return [self.repository.save_persona(primary_persona)]
