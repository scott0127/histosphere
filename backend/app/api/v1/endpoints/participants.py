"""Participant API endpoints.

Learner-facing participant lookup. The formal experiment flow uses
pre-created Supabase Auth users mapped to research participants.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_repository, get_session_service, require_active_participant_actor
from app.core.auth import AuthenticatedActor
from app.crud.protocols import RepositoryProtocol
from app.schemas.responses import ParticipantMeResponse
from app.services import SessionService

router = APIRouter(prefix="/api/participants", tags=["participants"])


@router.get("/me", response_model=ParticipantMeResponse)
def participant_me(
    auth_user_id: str | None = None,
    actor: AuthenticatedActor = Depends(require_active_participant_actor),
    repository: RepositoryProtocol = Depends(get_repository),
    session_service: SessionService = Depends(get_session_service),
) -> ParticipantMeResponse:
    """Return the participant mapped to the logged-in Supabase Auth user.

    Args:
        auth_user_id: Supabase Auth user UUID from the frontend session.
        repository: Data repository.
        session_service: Session/progress service.

    Returns:
        ParticipantMeResponse: Participant registry row and progress list.

    Raises:
        HTTPException: 400 if auth_user_id is blank.
        HTTPException: 404 if no participant is mapped to this auth user.
    """
    verified_auth_user_id = actor.resolve_user_id(auth_user_id)

    participant = repository.get_participant_by_auth_user(verified_auth_user_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant mapping not found")

    progress = session_service.user_progress(verified_auth_user_id).progress
    return ParticipantMeResponse(participant=participant, progress=progress)
