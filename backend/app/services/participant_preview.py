"""Isolated admin test identities for participant-assigned previews."""

from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException, status

from app.crud.protocols import RepositoryProtocol
from app.models.domain import Participant


def preview_user_id(participant_id: str) -> str:
    """Keep preview progress stable without impersonating the participant's Auth user."""
    return str(uuid5(NAMESPACE_URL, f"histosphere:admin-participant-preview:{participant_id}"))


def active_preview_participant(repository: RepositoryProtocol, participant_id: str) -> Participant:
    participant = repository.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    if participant.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Participant {participant.code} is not active.",
        )
    return participant
