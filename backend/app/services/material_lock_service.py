"""最低限度的實驗素材鎖定規則。"""

from fastapi import HTTPException, status

from app.core.task_payload_validator import validate_task_authoring_payload, validate_task_closure_payload
from app.crud.protocols import RepositoryProtocol
from app.models.domain import Event, utc_now


EDIT_LOCKED_DETAIL = "Event materials are locked. Unlock them before editing."
ACTIVE_SESSION_STATUSES = {"initialized", "task_submitted", "conversation_started"}


def assert_event_materials_editable(repository: RepositoryProtocol, event_id: str) -> Event:
    """確認事件存在且尚未鎖定，供所有素材修改入口共用。"""
    event = repository.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.materials_locked_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EDIT_LOCKED_DETAIL)
    return event


def set_event_material_lock(
    repository: RepositoryProtocol,
    event_id: str,
    *,
    locked: bool,
) -> Event:
    """鎖定已可實驗的素材；解除鎖定前不得有進行中的 Session。"""
    event = repository.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if locked:
        if event.materials_locked_at:
            return event
        issues = _material_readiness_issues(repository, event)
        if issues:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": "Event materials are not ready to lock.",
                    "issues": issues,
                },
            )
        event.materials_locked_at = utc_now()
    else:
        if not event.materials_locked_at:
            return event
        active_sessions = [
            session
            for session in repository.list_sessions()
            if session.event_id == event.id and session.status in ACTIVE_SESSION_STATUSES
            and session.user_id
            and repository.get_participant_by_auth_user(session.user_id)
        ]
        if active_sessions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active experiment sessions must finish or be archived before materials can be unlocked.",
            )
        event.materials_locked_at = None

    return repository.save_event(event)


def _material_readiness_issues(repository: RepositoryProtocol, event: Event) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if event.archived_at:
        issues.append({"field": "event", "code": "event_archived", "message": "封存事件不能鎖定為實驗素材。"})

    task = repository.get_latest_event_task(event.id)
    if not task:
        issues.append({"field": "task", "code": "task_missing", "message": "至少需要一份 Task。"})
    else:
        issues.extend(
            validate_task_authoring_payload(
                error_elicitation_task_full_text=task.error_elicitation_task_full_text,
                evaluation_payload=task.evaluation_payload,
            )
        )
        issues.extend(validate_task_closure_payload(task.evaluation_payload))

    active_personas = [
        persona
        for persona in repository.list_personas(event.id, active_only=False)
        if persona.active and persona.archived_at is None
    ]
    if len(active_personas) != 1:
        issues.append(
            {
                "field": "personas",
                "code": "active_persona_count",
                "message": "鎖定前必須且只能啟用一位歷史人物。",
            }
        )
    return issues
