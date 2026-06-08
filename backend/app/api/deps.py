from fastapi import Header, HTTPException, Request, status

from app.core.config import get_settings
from app.providers.llm import LLMProvider
from app.providers.wikipedia_provider import WikipediaProvider
from app.crud.protocols import RepositoryProtocol
from app.services import (
    ChatService,
    ConversationService,
    EventInitializationService,
    EventService,
    PersonaService,
    PromptService,
    RagPipelineService,
    TaskService,
)


def get_repository(request: Request) -> RepositoryProtocol:
    return request.app.state.repository


def get_wikipedia_provider(request: Request) -> WikipediaProvider:
    return request.app.state.wikipedia_provider


def get_llm_provider(request: Request) -> LLMProvider:
    return request.app.state.llm_provider


def get_rag_pipeline(request: Request) -> RagPipelineService:
    return request.app.state.rag_pipeline


def get_prompt_service(request: Request) -> PromptService:
    return request.app.state.prompt_service


def get_event_service(request: Request) -> EventService:
    return request.app.state.event_service


def get_event_initialization_service(request: Request) -> EventInitializationService:
    return request.app.state.event_initialization_service


def get_conversation_service(request: Request) -> ConversationService:
    return request.app.state.conversation_service


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


def get_persona_service(request: Request) -> PersonaService:
    return request.app.state.persona_service


def get_task_service(request: Request) -> TaskService:
    return request.app.state.task_service


def require_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not x_admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")
