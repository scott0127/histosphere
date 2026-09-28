"""Persist an independent posttest after the chat and its required closure."""

from fastapi import HTTPException

from app.crud.protocols import RepositoryProtocol
from app.models.domain import SessionPosttest, utc_now
from app.schemas.posttest import PosttestDraftRequest, PosttestInstrument, PosttestStateResponse
from app.services.session_service import SessionService


INSTRUMENT = PosttestInstrument(
    engagement=[{"id": f"engagement_{index}", "prompt": f"Pseudo 題 {index}"} for index in range(1, 4)],
    hat=[{"id": f"hat_{index}", "prompt": f"Pseudo 題 {index}"} for index in range(1, 3)],
)


class PosttestService:
    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def load(self, session_id: str) -> PosttestStateResponse:
        state = SessionService(self.repository).load_state(session_id)
        blocked_reason = None
        if state.session.status == "archived":
            blocked_reason = "此活動已封存，無法填寫後測。"
        elif state.session.status != "completed" or not state.conversation_id:
            blocked_reason = "請先完成本輪對話，再開始後測。"
        elif state.pending_final_response:
            blocked_reason = "最後一輪回覆仍在處理，請稍候完成收尾再開始後測。"
        elif state.closure and not state.closure.completed_at:
            blocked_reason = "請先完成對話的收尾重述，再開始後測。"
        return PosttestStateResponse(
            session_id=session_id,
            conversation_id=state.conversation_id,
            event_name=state.event.canonical_name,
            eligible=blocked_reason is None,
            blocked_reason=blocked_reason,
            response=self.repository.get_posttest(session_id),
            instrument=INSTRUMENT,
        )

    def _ready(self, session_id: str) -> PosttestStateResponse:
        state = self.load(session_id)
        if not state.eligible:
            raise HTTPException(status_code=409, detail=state.blocked_reason)
        return state

    def start(self, session_id: str) -> PosttestStateResponse:
        state = self._ready(session_id)
        state.response = self.repository.create_posttest(SessionPosttest(session_id=session_id))
        return state

    @staticmethod
    def _draft(state: PosttestStateResponse, revision: int) -> SessionPosttest:
        response = state.response
        if response is None:
            raise HTTPException(status_code=409, detail="請先開始後測。")
        if response.stage == "completed":
            raise HTTPException(status_code=409, detail="後測已提交，無法再次修改。")
        if response.revision != revision:
            raise HTTPException(status_code=409, detail="後測內容已在其他視窗更新，請重新載入。")
        return response

    def _save(self, state: PosttestStateResponse, response: SessionPosttest) -> PosttestStateResponse:
        revision = response.revision
        response = response.model_copy(update={"revision": revision + 1, "updated_at": utc_now()})
        saved = self.repository.update_posttest(response, revision)
        if saved is None:
            current = self.repository.get_posttest(response.session_id)
            if response.stage == "completed" and current and current.stage == "completed":
                state.response = current
                return state
            raise HTTPException(status_code=409, detail="後測內容已更新，請重新載入後再操作。")
        state.response = saved
        return state

    def save_draft(self, session_id: str, request: PosttestDraftRequest) -> PosttestStateResponse:
        state = self._ready(session_id)
        response = self._draft(state, request.revision)
        if response.stage == "engagement":
            if request.hat_answers is not None:
                raise HTTPException(status_code=409, detail="請先完成活動回饋，再填寫歷史思考後測。")
            if request.engagement_answers is not None:
                response.engagement_answers = dict(request.engagement_answers)
        else:
            if request.engagement_answers is not None:
                raise HTTPException(status_code=409, detail="活動回饋已確認，無法在後測階段修改。")
            if request.hat_answers is not None:
                response.hat_answers = dict(request.hat_answers)
        return self._save(state, response)

    def advance(self, session_id: str, revision: int) -> PosttestStateResponse:
        state = self._ready(session_id)
        response = self._draft(state, revision)
        if response.stage != "engagement":
            raise HTTPException(status_code=409, detail="目前已進入歷史思考後測。")
        if not all(question.id in response.engagement_answers for question in INSTRUMENT.engagement):
            raise HTTPException(status_code=422, detail="請完成全部活動回饋題目。")
        response.stage = "hat"
        return self._save(state, response)

    def submit(self, session_id: str, revision: int) -> PosttestStateResponse:
        state = self._ready(session_id)
        # A retried submission never overwrites the first persisted response.
        if state.response and state.response.stage == "completed":
            return state
        response = self._draft(state, revision)
        if response.stage != "hat":
            raise HTTPException(status_code=409, detail="請依序完成活動回饋與歷史思考後測。")
        if not all(response.hat_answers.get(question.id, "").strip() for question in INSTRUMENT.hat):
            raise HTTPException(status_code=422, detail="請完成全部歷史思考後測題目。")
        response.hat_answers = {key: value.strip() for key, value in response.hat_answers.items()}
        response.stage = "completed"
        response.submitted_at = utc_now()
        return self._save(state, response)
