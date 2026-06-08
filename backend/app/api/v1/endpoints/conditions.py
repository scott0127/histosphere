from fastapi import APIRouter, Depends

from app.api.deps import get_repository
from app.crud.protocols import RepositoryProtocol
from app.models.domain import ExperimentCondition

router = APIRouter(prefix="/api/conditions", tags=["conditions"])


@router.get("", response_model=list[ExperimentCondition])
def list_conditions(
    repository: RepositoryProtocol = Depends(get_repository),
) -> list[ExperimentCondition]:
    return repository.list_conditions(active_only=True)
