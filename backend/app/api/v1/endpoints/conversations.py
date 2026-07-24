"""Conversation API endpoints.

本模組提供 conversation 建立與載入入口。
V1 一般由 task submit 後自動建立 conversation；POST /conversations
主要保留相容性與未來 admin/manual flow。

Routes:
    POST /api/conversations:      建立新 conversation（相容性入口）。
    GET  /api/conversations/{id}:  載入既有 conversation 完整狀態。
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_conversation_service, require_authenticated_actor
from app.core.auth import AuthenticatedActor
from app.schemas.requests import ConversationCreateRequest
from app.schemas.responses import ConversationCreateResponse, ConversationLoadResponse
from app.services import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationCreateResponse)
async def create_conversation(
    request: ConversationCreateRequest,
    actor: AuthenticatedActor = Depends(require_authenticated_actor),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationCreateResponse:
    """相容性建立 conversation；新版 learner flow 通常不直接呼叫。

    此入口保留給 admin 或手動流程使用。正常 learner 流程中，
    conversation 會在 task submit 成功後由 TaskService 自動建立。

    Args:
        request: 建立請求，包含 event_id、可選的 task_attempt_id、
            session_id 與 user_id。
        service: 由 Dependency Injection 注入的 ConversationService 實例。

    Returns:
        ConversationCreateResponse: 包含 conversation_id、event、
            personas、condition、greeting 與初始 history。
    """
    user_id = actor.resolve_user_id(request.user_id)
    return await service.create_conversation(
        event_id=request.event_id,
        task_attempt_id=request.task_attempt_id,
        session_id=request.session_id,
        user_id=user_id,
    )


@router.get("/{conversation_id}", response_model=ConversationLoadResponse)
def load_conversation(
    conversation_id: UUID,
    actor: AuthenticatedActor = Depends(require_authenticated_actor),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationLoadResponse:
    """載入聊天頁回放所需的完整 conversation 狀態。

    前端聊天頁初始化或重新整理時呼叫，取得 event 脈絡、
    personas、歷史訊息、condition 設定與關聯的 task_attempt。

    Args:
        conversation_id: 目標 conversation 的 UUID。
        service: 由 Dependency Injection 注入的 ConversationService 實例。

    Returns:
        ConversationLoadResponse: 包含 conversation_id、event、
            personas、messages、condition、task_attempt
            與 related_events。
    """
    response = service.load_conversation(str(conversation_id))
    conversation = service.repository.get_conversation(str(conversation_id))
    actor.require_owner(conversation.user_id if conversation else response.session.user_id if response.session else None)
    return response
