"""Chat API endpoint.

本模組負責接收前端送出的 learner 訊息，並交給 ChatService 根據
2x2 實驗條件產生 generic chatbot 或 historical persona 回覆。

Routes:
    POST /api/chat: 處理單次 learner 對話訊息，回傳 AI 回覆與附加標注。
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_chat_service, require_authenticated_actor
from app.core.auth import AuthenticatedActor
from app.schemas.requests import ChatRequest
from app.schemas.responses import ChatResponse
from app.services import ChatService

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    actor: AuthenticatedActor = Depends(require_authenticated_actor),
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """處理單次對話訊息，實際政策判斷與訊息儲存由 ChatService 負責。

    根據 conversation 關聯的 2x2 實驗條件，決定使用 generic chatbot 模式
    或 historical persona role-play 模式回覆。ChatService 內部會完成
    prompt 組裝、LLM 呼叫、annotation 擷取與訊息持久化。

    Args:
        request: 聊天請求，包含 conversation_id、user_message、
            可選的 history 與 target_persona_id。
        service: 由 Dependency Injection 注入的 ChatService 實例。

    Returns:
        ChatResponse: 包含 AI 回覆文字、選用的 persona、assistant 名稱、
            ChatMessage 紀錄、annotations、related_events、
            dynamic_context 以及 rag_sources。
    """
    conversation = service.repository.get_conversation(request.conversation_id)
    if not conversation:
        return await service.chat(request)
    owner_user_id = conversation.user_id
    if not owner_user_id and conversation.session_id:
        session = service.repository.get_session(conversation.session_id)
        owner_user_id = session.user_id if session else None
    actor.require_owner(owner_user_id)
    return await service.chat(request)
