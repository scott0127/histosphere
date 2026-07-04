"""Stats compatibility endpoint.

本模組保留舊首頁 view count 的相容入口。
新版研究流程目前不依賴此數值。

Routes:
    POST /api/stats/view-count/increment: 遞增舊版 view count。
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_repository
from app.crud.protocols import RepositoryProtocol

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.post("/view-count/increment")
def increment_view_count(repository: RepositoryProtocol = Depends(get_repository)) -> dict[str, bool | int]:
    """遞增舊版 view count，主要避免舊呼叫直接壞掉。

    此端點為向後相容性保留。舊版前端首頁會在頁面載入時
    自動呼叫此 API 遞增計數器。新版研究流程不依賴此數值，
    但保留以免舊版部署回傳 404。

    Args:
        repository: 由 Dependency Injection 注入的資料存取層實例。

    Returns:
        dict[str, bool | int]: ``{"success": True, "view_count": <int>}``。
    """
    count = repository.increment_view_count()
    return {"success": True, "view_count": count}
