"""Human review is the only transition from an initial judgement to chat preparation."""

from copy import deepcopy

from fastapi import HTTPException

from app.crud.protocols import RepositoryProtocol
from app.models.domain import ResearchLog, TaskAttempt, utc_now
from app.schemas.task_review import TaskReviewDraftRequest, TaskReviewQuestion


def initial_review_payload(judgement: dict) -> dict:
    questions = []
    for row in judgement.get("question_results", []):
        correct = row.get("correctness") == "correct"
        questions.append(TaskReviewQuestion(
            question_id=row["question_id"],
            answer_correct=row.get("answer_correct", correct),
            reasoning_correct=row.get("reasoning_correct", correct),
            answer_feedback=row.get("answer_feedback"),
            reasoning_feedback=row.get("reasoning_feedback", ""),
        ).model_dump())
    return {"question_results": questions, "judged_at": utc_now().isoformat()}


class TaskReviewService:
    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def load(self, attempt_id: str) -> TaskAttempt:
        attempt = self.repository.get_task_attempt(attempt_id)
        if not attempt:
            raise HTTPException(404, "Task attempt not found")
        return attempt.model_copy(deep=True)

    def _editable(self, attempt_id: str, expected_version: int) -> TaskAttempt:
        attempt = self.load(attempt_id)
        session = self.repository.get_session(attempt.session_id)
        if not session or session.status in {"completed", "archived"}:
            raise HTTPException(409, "Experiment session is already closed")
        if attempt.status != "awaiting_review":
            raise HTTPException(409, "Task is not awaiting human review")
        if attempt.review_version != expected_version:
            raise HTTPException(409, "Review changed in another window; reload before saving")
        return attempt

    @staticmethod
    def _questions(attempt: TaskAttempt, rows: list[TaskReviewQuestion]) -> dict[str, dict]:
        original = {row["question_id"]: row for row in attempt.ai_judgement_payload.get("question_results", [])}
        ids = [row.question_id for row in rows]
        if not original or len(ids) != len(set(ids)) or set(ids) != set(original):
            raise HTTPException(422, "Review must contain each submitted question exactly once")
        return original

    def _save(self, attempt: TaskAttempt, expected_version: int) -> TaskAttempt:
        attempt.review_version = expected_version + 1
        saved = self.repository.save_task_review(attempt, expected_version)
        if not saved:
            raise HTTPException(409, "Review changed in another window; reload before saving")
        return saved

    def save_draft(self, attempt_id: str, request: TaskReviewDraftRequest) -> TaskAttempt:
        attempt = self._editable(attempt_id, request.expected_version)
        self._questions(attempt, request.question_results)
        attempt.review_payload = {
            **attempt.review_payload,
            "question_results": [row.model_dump() for row in request.question_results],
            "updated_at": utc_now().isoformat(),
        }
        return self._save(attempt, request.expected_version)

    def approve(self, attempt_id: str, expected_version: int, reviewer_id: str = "administrator") -> TaskAttempt:
        current = self.load(attempt_id)
        # A lost HTTP response may cause a second click; an approved checkpoint is never rewritten.
        if current.review_payload.get("approved_at"):
            return current
        attempt = self._editable(attempt_id, expected_version)
        rows = [TaskReviewQuestion.model_validate(row) for row in attempt.review_payload.get("question_results", [])]
        originals = self._questions(attempt, rows)
        final_rows = []
        for row in rows:
            original = originals[row.question_id]
            initial = initial_review_payload({"question_results": [original]})["question_results"][0]
            if not row.reviewed:
                raise HTTPException(422, f"{row.question_id}: every question must be reviewed")
            if not row.reasoning_feedback.strip():
                raise HTTPException(422, f"{row.question_id}: an approved reasoning explanation is required")
            if original.get("question_type") == "cloze" and not (row.answer_feedback or "").strip():
                raise HTTPException(422, f"{row.question_id}: an approved answer explanation is required")
            answer_changed = row.answer_correct != initial["answer_correct"]
            reasoning_changed = row.reasoning_correct != initial["reasoning_correct"]
            if (answer_changed or reasoning_changed) and not row.override_reason.strip():
                raise HTTPException(422, f"{row.question_id}: provide a reason for changing the judgement")
            if reasoning_changed and row.reasoning_feedback.strip() == initial["reasoning_feedback"].strip():
                raise HTTPException(422, f"{row.question_id}: update the explanation to match the revised reasoning judgement")
            if answer_changed and (row.answer_feedback or "").strip() == (initial["answer_feedback"] or "").strip():
                raise HTTPException(422, f"{row.question_id}: update the explanation to match the revised answer judgement")
            final = {
                **deepcopy(original),
                **row.model_dump(exclude={"reviewed", "override_reason"}),
                "correctness": "correct" if row.answer_correct and row.reasoning_correct else "incorrect",
            }
            if final["correctness"] == "correct":
                final["error_code"] = None
            final_rows.append(final)
        approved_at = utc_now().isoformat()
        attempt.review_payload = {
            **attempt.review_payload, "approved_at": approved_at, "reviewer_id": reviewer_id,
        }
        attempt.judgement_payload = {
            **deepcopy(attempt.ai_judgement_payload),
            "question_results": final_rows,
            "result": "correct" if all(row["correctness"] == "correct" for row in final_rows) else "incorrect",
            "decision_source": "human_review",
            "approved_at": approved_at,
        }
        attempt.status = "preparing_chat"
        attempt.pipeline_error = {}
        saved = self._save(attempt, expected_version)
        self.repository.log_research(ResearchLog(
            user_id=attempt.user_id, session_id=attempt.session_id, event_id=attempt.event_id,
            task_id=attempt.task_id, attempt_id=attempt.id, action_type="task_review_approved",
            payload={"reviewer_id": reviewer_id, "review_version": saved.review_version,
                     "approved_at": approved_at,
                     "changed_question_ids": [row.question_id for row in rows if row.override_reason.strip()]},
        ))
        return saved
