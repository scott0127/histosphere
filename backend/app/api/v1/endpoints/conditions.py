"""Experiment condition API endpoint.

本模組提供前端首頁使用的 2x2 condition 清單。
condition 決定 EBL 與 AI historical persona role-play 的開關。
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
    """回傳目前 active 的實驗條件。"""
    return repository.list_conditions(active_only=True)
