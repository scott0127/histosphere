"""恢復實驗進度、處理到期收尾，以及管理員的倒數重置與活動重開。

一般載入沿用已保存的活動、作答和對話，不重新開始倒數。
收尾重述另外存研究紀錄；管理員重置／重開則走各自明確的操作，並非單純讀取。
"""

from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException, status

from app.core.research_audit import build_change_payload
from app.core.research_reproducibility import get_session_task, record_session_material_snapshot, stable_hash
from app.core.interaction_contract import build_interaction_runtime
from app.crud.protocols import RepositoryProtocol
from app.models.domain import EventTask, ExperimentSession, ResearchLog, utc_now
from app.schemas.responses import (
    SessionRestartResponse,
    SessionClosureResponse,
    SessionFinalExchange,
    SessionStateResponse,
    UserProgressItem,
    UserProgressResponse,
)
from app.services.session_runtime import EXPERIMENT_CHAT_DURATION_MINUTES, expire_session_if_due
from app.services.learning_focus import build_learning_focus


class SessionService:
    """整理受測者進度與收尾狀態，並提供管理員專用的重置操作。"""

    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def load_state(self, session_id: str) -> SessionStateResponse:
        """載入單一活動；若期限已過，先標記結束，再提供可恢復的畫面資料。"""
        session = self.repository.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment session not found")

        session = expire_session_if_due(self.repository, session)
        event = self.repository.get_event(session.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        attempt = self.repository.get_task_attempt_for_session(session.id)
        task = get_session_task(self.repository, session, attempt)
        condition = self.repository.get_condition_by_key(session.condition_key_snapshot)
        conversation = self.repository.get_conversation_by_session(session.id)
        entered = bool(attempt and attempt.status == "submitted")
        if not entered:
            conversation = None
        posttest = self.repository.get_posttest(session.id)
        pending_final_response = bool(
            session.status == "completed" and conversation
            and self.repository.get_active_chat_operation(conversation.id)
        )
        # 先看是否仍在處理，再讀訊息；反過來會漏掉恰在兩次查詢之間完成的最後回覆。
        history = self.repository.list_messages(conversation.id) if conversation else []

        return SessionStateResponse(
            session=session,
            event=event,
            task=task,
            personas=self.repository.list_personas(event.id),
            condition=condition,
            attempt=attempt,
            conversation_id=conversation.id if conversation else None,
            closure=None if pending_final_response else self._closure(session, attempt, condition, conversation, history),
            pending_final_response=pending_final_response,
            final_exchange=self._final_exchange(history) if session.status == "completed" else None,
            learning_focus=build_learning_focus(
                condition, attempt, history,
            ) if entered else None,
            posttest_stage=posttest.stage if posttest else ("not_started" if session.status == "completed" else None),
        )

    @staticmethod
    def _final_exchange(history) -> SessionFinalExchange | None:
        learner = next((m for m in reversed(history) if m.speaker_type == "learner"), None)
        if not learner:
            return None
        assistant = next((m for m in history if m.id == learner.metadata.get("response_message_id")), None)
        return SessionFinalExchange(
            learner_message=learner.content,
            assistant_name=assistant.speaker_name if assistant else None,
            assistant_message=assistant.content if assistant else None,
            delivered_after_deadline=bool(assistant and assistant.metadata.get("delivered_after_deadline")),
            failed=learner.operation_status == "failed",
        )

    def _closure(self, session, attempt, condition, conversation, history) -> SessionClosureResponse | None:
        """只為到期時正在處理的那題準備正解與重述畫面，不順便公布其他題答案。"""
        # 正解只在計時已結束的 EBL 活動提供；不改動對話、不公布尚未談到的其他題目。
        if not (
            session.status == "completed"
            and session.completion_reason == "timer_elapsed"
            and condition
            and condition.ebl_enabled
            and attempt
            and conversation
        ):
            return None
        late_messages = [m for m in history if m.metadata.get("delivered_after_deadline")]
        # 收尾只整理倒數期間已討論的題目；最後送達的文字不額外開啟一題。
        history = [m for m in history if not m.metadata.get("delivered_after_deadline")]
        # 系統備援或保留原進度的回覆，不算 AI 已正式引入下一題。
        spoken = [
            m for m in history
            if m.speaker_type != "learner"
            and not m.metadata.get("system_fallback")
            and not m.metadata.get("answer_delivery", {}).get("state_held")
        ]
        if not spoken:
            return None
        runtime = build_interaction_runtime(condition, attempt, history)
        target = runtime.target
        if not target:
            return None
        if any(
            m.metadata.get("target_question_id") == target.question_id
            and m.metadata.get("completion_status") in {"resolved", "feedback_completed"}
            and not m.metadata.get("answer_delivery", {}).get("state_held")
            for m in late_messages
        ):
            return None
        last = spoken[-1].metadata
        if last.get("target_question_id") != target.question_id and not (
            last.get("next_target_started") and last.get("next_target_question_id") == target.question_id
        ):
            return None
        result = next(
            (
                r for r in attempt.judgement_payload.get("question_results", [])
                if r.get("question_id") == target.question_id
            ),
            {},
        )
        answer = target.expected_answer
        if isinstance(answer, bool):
            answer_text = "是" if answer else "否"
        elif isinstance(answer, list):
            answer_text = str(answer[0]) if answer else ""
        else:
            answer_text = "" if answer is None else str(answer)
        options = result.get("options") or []
        if not options:
            snapshot = next(
                (
                    log for log in self.repository.list_research_logs_for_session(session.id)
                    if log.action_type == "session_material_snapshot"
                ),
                None,
            )
            questions = (
                snapshot.payload.get("materials", {})
                .get("task", {})
                .get("evaluation_payload", {})
                .get("questions", [])
                if snapshot else []
            )
            options = next(
                (q.get("options", []) for q in questions if q.get("id") == target.question_id),
                [],
            )
        for option in options:
            if isinstance(option, dict) and str(option.get("value")) == answer_text:
                answer_text = f"{answer_text}：{option.get('label', answer_text)}"
                break
        # 使用判定時已凍結的正解解說，不把 rubric 或 LLM 診斷指令當作答案顯示。
        explanation = str(target.source_text or "").strip()
        if not answer_text or not explanation:
            raise HTTPException(status_code=409, detail="本題缺少完整修正說明，請研究人員協助收尾。")
        # 相同到期時間與題目會得到同一個識別碼，重新整理後能找回已送出的重述。
        closure_id = stable_hash([session.id, session.timer_ends_at, target.question_id, answer_text, explanation])
        for log in self.repository.list_research_logs_for_session(session.id):
            if log.action_type == "session_closure_restatement" and log.payload.get("closure_id") == closure_id:
                return SessionClosureResponse.model_validate(log.payload)
        return SessionClosureResponse(
            closure_id=closure_id,
            question_id=target.question_id,
            question=target.prompt,
            answer=answer_text,
            explanation=explanation,
        )

    def submit_closure(self, session_id: str, closure_id: str, reflection: str) -> SessionClosureResponse:
        """重述保存於研究紀錄，不新增聊天回合，也不把閱讀正解後的重述當作獨立學會。"""
        state = self.load_state(session_id)
        closure = state.closure
        if not closure or closure.closure_id != closure_id:
            raise HTTPException(status_code=409, detail="收尾狀態已變更，請重新載入。")
        if closure.completed_at:
            return closure
        if not reflection.strip():
            raise HTTPException(status_code=422, detail="請先用自己的話寫下修正後的想法。")
        saved = closure.model_copy(update={"reflection": reflection.strip(), "completed_at": utc_now().isoformat()})
        self.repository.log_research(
            ResearchLog(
                id=str(uuid5(NAMESPACE_URL, f"histosphere:closure:{closure_id}")),
                user_id=state.session.user_id,
                session_id=session_id,
                event_id=state.session.event_id,
                task_id=state.attempt.task_id,
                attempt_id=state.attempt.id,
                conversation_id=state.conversation_id,
                action_type="session_closure_restatement",
                payload={
                    **saved.model_dump(),
                    "phase": "post_timer_closure",
                    "outcome": "assisted_restatement_recorded",
                    "independent_mastery": False,
                },
            )
        )
        return saved

    def user_progress(
        self,
        user_id: str,
        participant_id: str | None = None,
        *,
        admin_test: bool = False,
    ) -> UserProgressResponse:
        """列出某位受測者在各事件與 condition 下的最新進度。"""
        if not user_id.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")

        progress: list[UserProgressItem] = []
        for stored_session in self.repository.list_sessions_for_user(user_id.strip()):
            if stored_session.is_admin_test != admin_test:
                continue
            if admin_test and stored_session.status == "archived":
                continue
            if participant_id and stored_session.participant_id != participant_id:
                continue
            session = expire_session_if_due(self.repository, stored_session)
            attempt = self.repository.get_task_attempt_for_session(session.id)
            task = get_session_task(self.repository, session, attempt)
            conversation = self.repository.get_conversation_by_session(session.id)
            posttest = self.repository.get_posttest(session.id)
            progress.append(
                UserProgressItem(
                    event_id=session.event_id,
                    condition_key=session.condition_key_snapshot,
                    session_id=session.id,
                    task_id=task.id if isinstance(task, EventTask) else None,
                    attempt_id=attempt.id if attempt else None,
                    conversation_id=conversation.id if conversation and attempt and attempt.status == "submitted" else None,
                    status=self._public_status(
                        session.status,
                        attempt.status if attempt else None,
                        conversation is not None,
                    ),
                    updated_at=session.updated_at.isoformat(),
                    posttest_stage=posttest.stage if posttest else ("not_started" if session.status == "completed" else None),
                )
            )
        return UserProgressResponse(progress=progress)

    def reset_timer(self, session_id: str) -> ExperimentSession:
        """由 Admin 將可對話的 session 明確重置為新的五分鐘倒數。"""
        session = self.repository.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment session not found")
        if session.status == "archived":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived session cannot be resumed")
        if self.repository.get_posttest(session_id):
            raise HTTPException(status_code=409, detail="後測已開始，不能重開本輪對話；請另建測試活動。")
        if session.status == "completed" and session.completion_reason != "timer_elapsed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only a timer-completed session can reset its countdown",
            )
        if not self.repository.get_conversation_by_session(session.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The countdown starts after the Chat stage is ready",
            )
        before = session.model_copy(deep=True)
        now = utc_now()
        session.status = "conversation_started"
        session.timer_started_at = now
        session.timer_ends_at = now + timedelta(minutes=EXPERIMENT_CHAT_DURATION_MINUTES)
        session.completed_at = None
        session.completion_reason = None
        saved = self.repository.save_session(session)
        self.repository.log_research(
            ResearchLog(
                user_id=saved.user_id,
                session_id=saved.id,
                event_id=saved.event_id,
                action_type="session_timer_reset",
                payload=build_change_payload(
                    before=before,
                    after=saved,
                    fields=[
                        "status",
                        "timer_started_at",
                        "timer_ends_at",
                        "completed_at",
                        "completion_reason",
                    ],
                    subject={
                        "session_id": saved.id,
                        "duration_minutes": EXPERIMENT_CHAT_DURATION_MINUTES,
                        "trigger": "admin",
                    },
                ),
            )
        )
        return saved

    def restart_session(self, session_id: str) -> SessionRestartResponse:
        """封存同一受測者在同事件的有效 session，再建立一筆乾淨 session。"""
        source_session = self.repository.get_session(session_id)
        if not source_session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment session not found")

        event = self.repository.get_event(source_session.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        if event.archived_at:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Restore the historical event before restarting its session.",
            )

        if source_session.user_id:
            candidates = [
                session
                for session in self.repository.list_sessions_for_user(source_session.user_id)
                if session.event_id == source_session.event_id and session.status != "archived"
            ]
        else:
            candidates = [source_session] if source_session.status != "archived" else []

        now = utc_now()
        archived_sessions: list[ExperimentSession] = []
        for session in candidates:
            session.status = "archived"
            session.completed_at = session.completed_at or now
            session.completion_reason = "admin_restart"
            session.timer_started_at = None
            session.timer_ends_at = None
            archived_sessions.append(self.repository.save_session(session))

            # 對話一併停止寫入，但 task、訊息與研究紀錄全部保留。
            conversation = self.repository.get_conversation_by_session(session.id)
            if conversation and conversation.status != "archived":
                conversation.status = "archived"
                conversation.archived_at = now
                self.repository.save_conversation(conversation)

        new_session = self.repository.save_session(
            ExperimentSession(
                condition_id=source_session.condition_id,
                condition_key_snapshot=source_session.condition_key_snapshot,
                user_id=source_session.user_id,
                participant_id=source_session.participant_id,
                event_id=source_session.event_id,
                is_admin_test=source_session.is_admin_test,
            )
        )
        record_session_material_snapshot(self.repository, new_session)
        self.repository.log_research(
            ResearchLog(
                user_id=new_session.user_id,
                session_id=new_session.id,
                event_id=new_session.event_id,
                action_type="session_restarted",
                payload={
                    "source_session_id": source_session.id,
                    "archived_session_ids": [session.id for session in archived_sessions],
                    "new_session_id": new_session.id,
                    "condition_key": new_session.condition_key_snapshot,
                },
            )
        )
        return SessionRestartResponse(
            archived_sessions=archived_sessions,
            new_session=new_session,
        )

    def expire_due_sessions(self) -> int:
        """Complete all due five-minute timers; used by the background worker."""
        completed = 0
        for session in self.repository.list_sessions():
            previous_status = session.status
            updated = expire_session_if_due(self.repository, session)
            if previous_status != "completed" and updated.status == "completed":
                completed += 1
        return completed

    @staticmethod
    def _public_status(session_status: str, attempt_status: str | None, has_conversation: bool) -> str:
        """把後端 session 狀態轉成首頁需要的穩定顯示狀態。"""
        if session_status == "archived":
            return "archived"
        if session_status == "completed":
            return "completed"
        if attempt_status == "submitted" and (has_conversation or session_status == "conversation_started"):
            return "chat_started"
        if attempt_status in {"processing", "awaiting_review", "preparing_chat", "ready", "submitted", "failed"} or session_status == "task_submitted":
            return "task_submitted"
        if attempt_status == "in_progress":
            return "task_draft"
        return "task_started"
