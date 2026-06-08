import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_local_env() -> None:
    project_root = Path(__file__).resolve().parents[3]
    _load_env_file(project_root / ".env")
    _load_env_file(project_root / ".env.local.supabase")


class Settings(BaseModel):
    app_name: str = "Histosphere Backend"
    app_version: str = "0.2.0"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    wikipedia_timeout_seconds: float = 8.0
    repository_backend: str = "auto"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    admin_key: str = "histosphere-local-admin"

    @property
    def should_use_supabase(self) -> bool:
        if self.repository_backend == "in_memory":
            return False
        if self.repository_backend == "supabase":
            return True
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
        or os.getenv("SUPABASE_KEY_SERVICE_ROLE")
        or os.getenv("SUPABASE_KEY_service_role")
    )
    return Settings(
        environment=os.getenv("BACKEND_ENVIRONMENT", "development"),
        cors_origins=origins,
        wikipedia_timeout_seconds=float(os.getenv("WIKIPEDIA_TIMEOUT_SECONDS", "8.0")),
        repository_backend=os.getenv("BACKEND_REPOSITORY", "auto"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_service_role_key=service_role_key,
        admin_key=os.getenv("HISTOSPHERE_ADMIN_KEY", "histosphere-local-admin"),
    )
