"""Stats compatibility endpoint.

本模組保留舊首頁 view count 的相容入口。
新版研究流程目前不依賴此數值。
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_repository
from app.crud.protocols import RepositoryProtocol

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.post("/view-count/increment")
def increment_view_count(repository: RepositoryProtocol = Depends(get_repository)) -> dict[str, bool | int]:
    """遞增舊版 view count，主要避免舊呼叫直接壞掉。"""
    count = repository.increment_view_count()
    return {"success": True, "view_count": count}
