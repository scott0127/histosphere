"""Experiment condition API endpoint.

本模組提供前端首頁使用的 2x2 condition 清單。
condition 決定 EBL 與 AI historical persona role-play 的開關。

Routes:
    GET /api/conditions: 列出目前啟用中的實驗條件。
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_repository
from app.crud.protocols import RepositoryProtocol
from app.models.domain import ExperimentCondition

router = APIRouter(prefix="/api/conditions", tags=["conditions"])


@router.get("", response_model=list[ExperimentCondition])
def list_conditions(
    repository: RepositoryProtocol = Depends(get_repository),
) -> list[ExperimentCondition]:
    """回傳目前 active 的實驗條件。

    前端首頁根據此清單讓 learner 選擇實驗條件組合
    （EBL 開/關 × role-play 開/關），決定後續聊天模式。
    僅回傳 active=True 的紀錄，已停用的條件不會出現。

    Args:
        repository: 由 Dependency Injection 注入的資料存取層實例。

    Returns:
        list[ExperimentCondition]: 啟用中的 2x2 實驗條件清單。
    """
    return repository.list_conditions(active_only=True)
