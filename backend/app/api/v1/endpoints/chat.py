"""Chat API endpoint.

本模組負責接收前端送出的 learner 訊息，並交給 ChatService 根據
2x2 實驗條件產生 generic chatbot 或 historical persona 回覆。
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
    """處理單次對話訊息，實際政策判斷與訊息儲存由 ChatService 負責。"""
    return await service.chat(request)
