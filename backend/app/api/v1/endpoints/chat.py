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
    return await service.chat(request)

