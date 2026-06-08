from fastapi import APIRouter, Depends

from app.api.deps import get_repository
from app.crud.protocols import RepositoryProtocol

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.post("/view-count/increment")
def increment_view_count(repository: RepositoryProtocol = Depends(get_repository)) -> dict[str, bool | int]:
    count = repository.increment_view_count()
    return {"success": True, "view_count": count}

