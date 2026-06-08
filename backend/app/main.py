from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.db import InMemoryRepository, SupabaseRepository
from app.providers import WikipediaProvider
from app.providers.llm import StubLLMProvider
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


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    if settings.should_use_supabase and settings.supabase_url and settings.supabase_service_role_key:
        repository = SupabaseRepository(settings.supabase_url, settings.supabase_service_role_key)
    else:
        repository = InMemoryRepository()
    wikipedia_provider = WikipediaProvider(settings)
    llm_provider = StubLLMProvider()
    rag_pipeline = RagPipelineService(repository)
    prompt_service = PromptService()

    app.state.repository = repository
    app.state.wikipedia_provider = wikipedia_provider
    app.state.llm_provider = llm_provider
    app.state.rag_pipeline = rag_pipeline
    app.state.prompt_service = prompt_service
    app.state.event_service = EventService(repository)
    app.state.event_initialization_service = EventInitializationService(
        repository=repository,
        wikipedia_provider=wikipedia_provider,
        llm_provider=llm_provider,
    )
    app.state.conversation_service = ConversationService(repository, llm_provider)
    app.state.chat_service = ChatService(repository, llm_provider, prompt_service, rag_pipeline)
    app.state.persona_service = PersonaService(repository)
    app.state.task_service = TaskService(repository, llm_provider)

    app.include_router(api_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
