"""Conversation API endpoints.

本模組提供 conversation 建立與載入入口。
V1 一般由 task submit 後自動建立 conversation；POST /conversations
主要保留相容性與未來 admin/manual flow。
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_conversation_service
from app.schemas.requests import ConversationCreateRequest
from app.schemas.responses import ConversationCreateResponse, ConversationLoadResponse
from app.services import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationCreateResponse)
async def create_conversation(
    request: ConversationCreateRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationCreateResponse:
    """相容性建立 conversation；新版 learner flow 通常不直接呼叫。"""
    return await service.create_conversation(
        event_id=request.event_id,
        task_attempt_id=request.task_attempt_id,
        session_id=request.session_id,
        user_id=request.user_id,
    )


@router.get("/{conversation_id}", response_model=ConversationLoadResponse)
def load_conversation(
    conversation_id: UUID,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationLoadResponse:
    """載入聊天頁回放所需的完整 conversation 狀態。"""
    return service.load_conversation(str(conversation_id))
