"""Chat API endpoint.

本模組負責接收前端送出的 learner 訊息，並交給 ChatService 根據
2x2 實驗條件產生 generic chatbot 或 historical persona 回覆。

Routes:
    POST /api/chat: 處理單次 learner 對話訊息，回傳 AI 回覆與附加標注。
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_chat_service
from app.schemas.requests import ChatRequest
from app.schemas.responses import ChatResponse
from app.services import ChatService

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
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
    return await service.chat(request)
