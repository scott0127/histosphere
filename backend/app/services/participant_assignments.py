"""Validate ordered event/condition assignments stored in participant metadata."""

from fastapi import HTTPException, status
from pydantic import TypeAdapter, ValidationError

from app.core.experiment_conditions import EXPERIMENT_CONDITION_KEY_BY_CODE, condition_code_for_key
from app.crud.protocols import RepositoryProtocol
from app.models.domain import ExperimentSession, Participant
from app.schemas.requests import ParticipantActivityAssignment
from app.services.participant_preview import preview_user_id


ASSIGNMENTS_KEY = "activity_assignments"
_ASSIGNMENTS = TypeAdapter(list[ParticipantActivityAssignment])


def participant_activity_assignments(participant: Participant) -> list[dict[str, str]] | None:
    """Absent metadata keeps the legacy condition-only contract; malformed pairs fail closed."""
    if ASSIGNMENTS_KEY not in participant.metadata:
        return None
    try:
        assignments = [item.model_dump() for item in _ASSIGNMENTS.validate_python(participant.metadata[ASSIGNMENTS_KEY])]
    except ValidationError as exc:
        raise HTTPException(status_code=409, detail="受測者的活動分派資料不一致，請管理員檢查事件、模式與順序。") from exc
    codes = [item["condition_code"] for item in assignments]
    events = [item["event_id"] for item in assignments]
    if len(set(codes)) != len(codes) or len(set(events)) != len(events) or codes != participant.condition_list:
        raise HTTPException(status_code=409, detail="受測者的活動分派資料不一致，請管理員檢查事件、模式與順序。")
    return assignments


def session_matches_activity(session: ExperimentSession, assignments: list[dict[str, str]]) -> bool:
    return any(item["event_id"] == session.event_id
               and item["condition_code"] == condition_code_for_key(session.condition_key_snapshot)
               for item in assignments)


def prepare_assignment_updates(
    repository: RepositoryProtocol,
    updates: dict,
    participant: Participant | None = None,
) -> dict:
    """Reserve paired metadata for the typed field and preserve unrelated metadata keys."""
    updates = dict(updates)
    metadata_patch = updates.get("metadata") or {}
    if ASSIGNMENTS_KEY in metadata_patch:
        raise HTTPException(
            status_code=422,
            detail="請透過活動分派欄位調整事件與模式，不可直接修改其他設定中的配對資料。",
        )
    metadata = {**(participant.metadata if participant else {}), **metadata_patch}
    current_assignments = participant_activity_assignments(participant) if participant else None
    if ASSIGNMENTS_KEY in updates:
        assignments = updates.pop(ASSIGNMENTS_KEY)
        if assignments is None:
            raise HTTPException(status_code=422, detail="活動分派必須是清單；若要清除分派，請傳送空清單。")
        codes = [item["condition_code"] for item in assignments]
        event_ids = [item["event_id"] for item in assignments]
        if len(set(codes)) != len(codes) or len(set(event_ids)) != len(event_ids):
            raise HTTPException(status_code=422, detail="每個歷史事件與模式只能分派一次，請移除重複的活動。")
        if "condition_list" in updates and updates["condition_list"] != codes:
            raise HTTPException(status_code=422, detail="模式清單與活動分派的模式及順序不一致，請重新確認。")
        for item in assignments:
            event = repository.get_event(item["event_id"])
            if not event or event.archived_at:
                raise HTTPException(status_code=422, detail="分派的歷史事件不存在或已封存，請選擇可用事件。")
            condition = repository.get_condition_by_key(EXPERIMENT_CONDITION_KEY_BY_CODE[item["condition_code"]])
            if not condition or not condition.active:
                raise HTTPException(status_code=422, detail="分派的實驗模式尚未啟用，請選擇已啟用的模式。")
        if participant and current_assignments != assignments:
            _validate_history_compatibility(repository, participant, assignments)
        metadata[ASSIGNMENTS_KEY] = assignments
        updates["condition_list"] = codes
        updates["metadata"] = metadata
    elif current_assignments is not None:
        codes = [item["condition_code"] for item in current_assignments]
        if "condition_list" in updates and updates["condition_list"] != codes:
            raise HTTPException(status_code=422, detail="此受測者已設定事件與模式配對，請從活動分派調整，不可只修改模式清單。")
    if "metadata" in updates:
        updates["metadata"] = metadata
    return updates


def _validate_history_compatibility(
    repository: RepositoryProtocol,
    participant: Participant,
    assignments: list[dict[str, str]],
) -> None:
    """Keep started formal and isolated preview rounds attached to their original position."""
    test_user_id = preview_user_id(participant.id)
    codes = [item["condition_code"] for item in assignments]
    for session in repository.list_sessions():
        if session.status == "archived":
            continue
        belongs_to_participant = (
            not session.is_admin_test
            and (session.participant_id == participant.id
                 or (not session.participant_id and participant.auth_user_id
                     and session.user_id == participant.auth_user_id))
        )
        belongs_to_preview = session.is_admin_test and session.user_id == test_user_id
        if not belongs_to_participant and not belongs_to_preview:
            continue
        code = condition_code_for_key(session.condition_key_snapshot)
        changed_position = (code in codes and code in participant.condition_list
                            and codes.index(code) != participant.condition_list.index(code))
        if not session_matches_activity(session, assignments) or changed_position:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="已開始的活動不能更換事件、模式或順序；請保留原配對，或先封存相關正式／測試紀錄。",
            )
