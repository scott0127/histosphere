import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


def _load_env_file(path: Path, *, override: bool = False) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = value


def load_local_env() -> None:
    project_root = Path(__file__).resolve().parents[3]
    _load_env_file(project_root / ".env")
    # 本地 Supabase 設定應覆蓋 .env 裡的雲端 URL，避免開發時誤寫雲端或 fallback。
    _load_env_file(project_root / ".env.local.supabase", override=True)


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _default_llm_model() -> str:
    if os.getenv("NVIDIA_API_KEY"):
        return os.getenv("NVIDIA_LLM_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
    return "gemini/gemini-2.5-flash"


def _default_fallback_models(primary_model: str) -> list[str]:
    if os.getenv("LLM_FALLBACK_MODELS"):
        return _split_csv(os.getenv("LLM_FALLBACK_MODELS"))
    if primary_model.startswith("nvidia/"):
        return ["gemini/gemini-2.0-flash-lite", "gemini/gemini-flash-lite-latest"]
    if os.getenv("NVIDIA_API_KEY"):
        return [os.getenv("NVIDIA_LLM_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")]
    return []


class Settings(BaseModel):
    app_name: str = "Histosphere Backend"
    app_version: str = "0.2.0"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    wikipedia_timeout_seconds: float = 8.0
    wikipedia_user_agent: str = "HistosphereThesisPrototype/0.2 (local research prototype)"
    repository_backend: str = "supabase"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    allow_in_memory_repository: bool = False
    admin_key: str = "scott5497"
    llm_provider: str = "litellm"
    llm_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    llm_fallback_models: list[str] = Field(default_factory=list)
    llm_api_base: str | None = None
    llm_api_key: str | None = None
    llm_temperature: float = 0.3
    llm_max_output_tokens: int = 4096
    llm_timeout_seconds: float = 60.0
    nvidia_api_key: str | None = None
    nvidia_api_base: str = "https://integrate.api.nvidia.com/v1"
    nvidia_llm_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    nvidia_enable_thinking: bool = False
    nvidia_reasoning_budget: int = 4096

    @property
    def should_use_supabase(self) -> bool:
        if self.repository_backend == "in_memory" and self.allow_in_memory_repository:
            return False
        if self.repository_backend == "in_memory":
            raise RuntimeError("In-memory repository is disabled outside explicit tests.")
        return bool(self.supabase_url and self.supabase_service_role_key)


@lru_cache
def get_settings() -> Settings:
    load_local_env()
    cors_origins = os.getenv("BACKEND_CORS_ORIGINS")
    origins = (
        [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
        if cors_origins
        else Settings().cors_origins
    )
    service_role_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_KEY_SERVICE_ROLE")
        or os.getenv("SUPABASE_KEY_service_role")
    )
    llm_model = os.getenv("LLM_MODEL", _default_llm_model())
    return Settings(
        environment=os.getenv("BACKEND_ENVIRONMENT", "development"),
        cors_origins=origins,
        wikipedia_timeout_seconds=float(os.getenv("WIKIPEDIA_TIMEOUT_SECONDS", "8.0")),
        wikipedia_user_agent=os.getenv(
            "WIKIPEDIA_USER_AGENT",
            "HistosphereThesisPrototype/0.2 (local research prototype)",
        ),
        repository_backend=os.getenv("BACKEND_REPOSITORY", "supabase"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_service_role_key=service_role_key,
        allow_in_memory_repository=os.getenv("ALLOW_IN_MEMORY_REPOSITORY", "false").lower() == "true",
        admin_key=os.getenv("HISTOSPHERE_ADMIN_KEY", "scott5497"),
        llm_provider=os.getenv("LLM_PROVIDER", "litellm"),
        llm_model=llm_model,
        llm_fallback_models=_default_fallback_models(llm_model),
        llm_api_base=os.getenv("LLM_API_BASE"),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
        llm_max_output_tokens=int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "4096")),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "60.0")),
        nvidia_api_key=os.getenv("NVIDIA_API_KEY"),
        nvidia_api_base=os.getenv("NVIDIA_API_BASE", "https://integrate.api.nvidia.com/v1"),
        nvidia_llm_model=os.getenv("NVIDIA_LLM_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"),
        nvidia_enable_thinking=_env_bool("NVIDIA_ENABLE_THINKING", False),
        nvidia_reasoning_budget=int(os.getenv("NVIDIA_REASONING_BUDGET", "4096")),
    )
