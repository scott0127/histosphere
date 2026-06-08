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
    return await service.create_conversation(
        event_id=request.event_id,
        task_attempt_id=request.task_attempt_id,
        session_id=request.session_id,
        user_id=request.user_id,
    )


@router.get("/{conversation_id}", response_model=ConversationLoadResponse)
def load_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationLoadResponse:
    return service.load_conversation(conversation_id)
