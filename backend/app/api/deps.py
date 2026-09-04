from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth import AuthenticatedActor
from app.core.config import get_settings
from app.models.domain import ExperimentSession
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
    SessionService,
    TaskService,
)

bearer_scheme = HTTPBearer(auto_error=False)


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


def get_session_service(request: Request) -> SessionService:
    return request.app.state.session_service


def require_session_actor(
    actor: AuthenticatedActor,
    repository: RepositoryProtocol,
    session: ExperimentSession | None,
) -> None:
    """驗證 Auth owner 與 Session 凍結的 participant 身分皆一致。"""
    if session is None:
        return
    # 舊的 Admin test fixture 可在第一筆 learner 操作時綁定 Auth；它不屬於正式研究資料。
    if session.is_admin_test and not session.user_id and not session.participant_id:
        return
    actor.require_owner(session.user_id)
    if actor.is_admin or not session.participant_id:
        return

    participant = repository.get_participant_by_auth_user(actor.user_id or "")
    if not participant or participant.id != session.participant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session belongs to another participant assignment",
        )


def require_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    if not is_valid_admin_key(x_admin_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")


def is_valid_admin_key(value: str | None) -> bool:
    """Return whether an optional header contains the configured admin key."""
    return bool(value and value == get_settings().admin_key)


async def require_authenticated_actor(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_admin_key: str | None = Header(default=None),
) -> AuthenticatedActor:
    """Resolve Admin-key access or a verified Supabase Auth bearer token."""
    if is_valid_admin_key(x_admin_key):
        return AuthenticatedActor(user_id=None, is_admin=True)
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid Supabase Auth bearer token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await request.app.state.supabase_jwt_verifier.verify(credentials.credentials)
    return AuthenticatedActor(user_id=user.id)


async def require_active_participant_actor(
    actor: AuthenticatedActor = Depends(require_authenticated_actor),
    repository: RepositoryProtocol = Depends(get_repository),
) -> AuthenticatedActor:
    """限制正式 learner 流程只能由 active participant 使用。

    Admin key 保留管理與測試權限；封存 participant 時只停止實驗存取，
    不解除 Auth 綁定，也不更動既有 session、task 或 conversation 資料。
    """
    if actor.is_admin:
        return actor

    participant = repository.get_participant_by_auth_user(actor.user_id or "")
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Participant mapping not found for this Auth user",
        )
    if participant.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Participant {participant.code} is not active",
        )
    return actor
