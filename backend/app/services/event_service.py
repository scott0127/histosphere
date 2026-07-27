"""Event utility service.

本模組提供事件查詢、列表、刪除與 LLM profile 轉換等輔助功能。
事件初始化的完整流程放在 EventInitializationService，避免本服務過度膨脹。
"""

from fastapi import HTTPException, status

from app.models.domain import Event, EventTask
from app.schemas.responses import EventListItem
from app.crud.protocols import RepositoryProtocol
from app.utils.text_normalizer import normalize_display_text


class EventService:
    """封裝事件相關的簡單 CRUD 與轉換邏輯。"""

    def __init__(self, repository: RepositoryProtocol) -> None:
        self.repository = repository

    def check_exists(self, event_name: str) -> bool:
        """檢查 canonical_name 是否已存在可重用事件。"""
        normalized_name = normalize_display_text(event_name.strip()) or event_name.strip()
        return self.repository.find_event_by_name(normalized_name) is not None

    def list_events(self) -> list[EventListItem]:
        """列出事件與非敏感 task 摘要，避免首頁回應提前暴露答案。"""
        items: list[EventListItem] = []
        for event in self.repository.list_events():
            payload = event.model_dump()
            payload["personas"] = self.repository.list_personas(event.id)
            payload["latest_task"] = self._learner_task_summary(
                self.repository.get_latest_event_task(event.id)
            )
            items.append(EventListItem(**payload))
        return items

    @staticmethod
    def _learner_task_summary(task: EventTask | None) -> EventTask | None:
        """保留列表判斷所需 metadata，不回傳故事原文、題目與答案。"""
        if not task:
            return None
        raw_questions = task.evaluation_payload.get("questions")
        question_count = len(raw_questions) if isinstance(raw_questions, list) else 0
        return task.model_copy(
            update={
                "story_text": "",
                "display_text": "",
                "evaluation_payload": {"question_count": question_count},
            }
        )

    def archive_event(self, event_id: str) -> Event:
        """Hide an event from learner selection without deleting research data."""
        event = self.repository.archive_event(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        return event

    def restore_event(self, event_id: str) -> Event:
        """Restore an archived event to the learner event library."""
        event = self.repository.restore_event(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        return event

    def regenerate_background(self, event_id: str) -> dict[str, str | None]:
        """舊圖片背景功能的相容入口；新版研究 UI 不再產生背景圖。"""
        event = self.repository.get_event(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        return {"background_url": None}

    @staticmethod
    def build_event_from_profile(event_name: str, profile: dict) -> Event:
        """把 LLM event profile 轉成 Event domain model。"""
        canonical_name = normalize_display_text(profile.get("canonical_name") or event_name.strip())
        return Event(
            canonical_name=canonical_name or event_name.strip(),
            description=profile.get("description"),
            century=profile.get("century"),
            start_year=profile.get("start_year"),
            end_year=profile.get("end_year"),
            context=profile.get("context"),
            source_summary=profile.get("source_summary") or {},
        )
