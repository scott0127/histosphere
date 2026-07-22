"""Application configuration and environment loading.

本模組負責從環境變數與 .env 檔載入全域設定，並透過 Pydantic
BaseModel 提供型別安全的 Settings 實例。所有後端元件透過
``get_settings()`` 取得唯一的快取設定。

主要職責:
    - 載入 .env / .env.local.supabase 環境檔。
    - 定義 Settings 資料模型（應用、CORS、Supabase、LLM、NVIDIA）。
    - 提供 ``get_settings()`` 單例工廠函式。
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


def _load_env_file(path: Path, *, override: bool = False) -> None:
    """從指定路徑讀取 .env 格式的環境變數檔並注入 ``os.environ``。

    逐行解析 KEY=VALUE 格式，自動略過空行與 ``#`` 開頭的註解行，
    並移除值兩側的引號（單引號或雙引號）。

    Args:
        path: .env 檔案的 ``Path`` 物件。
        override: 若為 True，即使 ``os.environ`` 已存在該 key 也會覆寫；
            預設 False 表示僅在環境中尚未設定時才寫入。
    """
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
    """載入專案根目錄的本地環境檔。

    依序載入:
        1. ``.env`` — 基礎環境變數（不覆寫已存在的 key）。
        2. ``.env.local.supabase`` — 本地 Supabase 連線設定
           （**覆寫模式**），避免開發時意外連到雲端資料庫。
    """
    project_root = Path(__file__).resolve().parents[3]
    _load_env_file(project_root / ".env")
    # 本地 Supabase 設定應覆蓋 .env 裡的雲端 URL，避免開發時誤寫雲端或 fallback。
    _load_env_file(project_root / ".env.local.supabase", override=True)


def _split_csv(value: str | None) -> list[str]:
    """將逗號分隔的字串拆為清單，自動去除空白與空項目。

    Args:
        value: 逗號分隔字串，可為 None。

    Returns:
        list[str]: 拆分後的非空字串清單；若 value 為 None 則回傳空清單。
    """
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_bool(name: str, default: bool = False) -> bool:
    """從環境變數讀取布林值。

    支援 ``"1"``、``"true"``、``"yes"``、``"on"``（不分大小寫）
    作為 True；其餘值（含未設定）回傳 ``default``。

    Args:
        name: 環境變數名稱。
        default: 環境變數未設定時的預設值。

    Returns:
        bool: 解析後的布林值。
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _default_llm_model() -> str:
    """根據可用的 API key 決定預設 LLM 模型名稱。

    優先順序:
        1. 若已設定 ``GEMINI_API_KEY``，使用 ``GEMINI_LLM_MODEL``
           環境變數（預設 ``gemini/gemini-3.5-flash-lite``）。
        2. 否則若已設定 ``NVIDIA_API_KEY``，使用 ``NVIDIA_LLM_MODEL``。
        3. 兩者皆未設定時仍回傳 Gemini 預設值，讓啟動時的設定可預期。

    Returns:
        str: LiteLLM 格式的模型識別字串。
    """
    if os.getenv("GEMINI_API_KEY"):
        return os.getenv("GEMINI_LLM_MODEL", "gemini/gemini-3.5-flash-lite")
    if os.getenv("NVIDIA_API_KEY"):
        return os.getenv("NVIDIA_LLM_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
    return "gemini/gemini-3.5-flash-lite"


def _default_fallback_models(primary_model: str) -> list[str]:
    """根據主模型與環境設定決定 LLM fallback 模型清單。

    解析邏輯:
        1. 若已設定 ``LLM_FALLBACK_MODELS`` 環境變數，直接拆分使用。
        2. 若主模型為 NVIDIA 系列且 Gemini key 可用，fallback 到 Gemini Flash。
        3. 若有 ``NVIDIA_API_KEY`` 但主模型非 NVIDIA，fallback 到 NVIDIA 模型。
        4. 以上皆不符合則回傳空清單（無 fallback）。

    Args:
        primary_model: 當前主要 LLM 模型名稱。

    Returns:
        list[str]: Fallback 模型名稱清單，依優先順序排列。
    """
    if os.getenv("LLM_FALLBACK_MODELS"):
        return _split_csv(os.getenv("LLM_FALLBACK_MODELS"))
    if primary_model.startswith("nvidia/") and os.getenv("GEMINI_API_KEY"):
        return [os.getenv("GEMINI_LLM_MODEL", "gemini/gemini-3.5-flash-lite")]
    if os.getenv("NVIDIA_API_KEY"):
        return [os.getenv("NVIDIA_LLM_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")]
    return []


class Settings(BaseModel):
    """全域應用設定，透過 Pydantic BaseModel 提供型別驗證。

    所有欄位皆可透過環境變數覆寫，``get_settings()`` 負責
    從環境變數映射到各欄位。

    Attributes:
        app_name: 應用程式名稱，用於日誌與 API 文件標題。
        app_version: 應用程式版本號。
        environment: 執行環境（``"development"`` / ``"production"``）。
        cors_origins: 允許的 CORS 來源清單。
        wikipedia_timeout_seconds: Wikipedia API 請求逾時秒數。
        wikipedia_user_agent: Wikipedia API 請求的 User-Agent 標頭。
        repository_backend: 資料存取層後端類型
            （``"supabase"`` / ``"in_memory"``）。
        supabase_url: Supabase 專案 URL。
        supabase_service_role_key: Supabase service role API key。
        allow_in_memory_repository: 是否允許 in-memory 資料存取
            （僅供測試使用）。
        admin_key: Admin API 的 x-admin-key 驗證金鑰。
        llm_provider: LLM 呼叫層提供者（預設 ``"litellm"``）。
        llm_model: 主要 LLM 模型名稱（LiteLLM 格式）。
        llm_fallback_models: LLM fallback 模型清單。
        llm_api_base: 自訂 LLM API base URL（可選）。
        llm_api_key: 自訂 LLM API key（可選）。
        llm_temperature: LLM 生成溫度。
        llm_max_output_tokens: LLM 最大輸出 token 數。
        llm_timeout_seconds: LLM 請求逾時秒數。
        gemini_api_key: Gemini API key（可選）。
        gemini_reasoning_effort: Gemini thinking 強度；即時對話預設 ``low``。
        nvidia_api_key: NVIDIA NIM API key（可選）。
        nvidia_api_base: NVIDIA NIM API base URL。
        nvidia_llm_model: NVIDIA 專用的模型名稱。
        nvidia_enable_thinking: 是否啟用 NVIDIA 推理思考模式。
        nvidia_reasoning_budget: NVIDIA 推理思考的 token 預算。
        cohere_api_key: Cohere API key（可選）。
        cohere_llm_model: Cohere 備選模型名稱。
    """

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
    llm_model: str = "gemini/gemini-3.5-flash-lite"
    llm_fallback_models: list[str] = Field(default_factory=list)
    llm_api_base: str | None = None
    llm_api_key: str | None = None
    llm_temperature: float = 0.3
    llm_max_output_tokens: int = 4096
    llm_timeout_seconds: float = 60.0
    gemini_api_key: str | None = None
    gemini_reasoning_effort: str = "minimal"
    nvidia_api_key: str | None = None
    nvidia_api_base: str = "https://integrate.api.nvidia.com/v1"
    nvidia_llm_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    nvidia_enable_thinking: bool = False
    nvidia_reasoning_budget: int = 4096
    cohere_api_key: str | None = None
    cohere_llm_model: str = "cohere/command-a-plus-05-2026"

    @property
    def should_use_supabase(self) -> bool:
        """判斷是否應使用 Supabase 作為資料存取層後端。

        判斷邏輯:
            1. 若 ``repository_backend`` 為 ``"in_memory"`` 且
               ``allow_in_memory_repository`` 為 True，回傳 False。
            2. 若 ``repository_backend`` 為 ``"in_memory"`` 但
               ``allow_in_memory_repository`` 為 False，拋出
               ``RuntimeError``（防止非測試環境意外使用 in-memory）。
            3. 其餘情況，檢查 ``supabase_url`` 與
               ``supabase_service_role_key`` 是否皆已設定。

        Returns:
            bool: True 表示應初始化 Supabase client。

        Raises:
            RuntimeError: 嘗試在未明確允許的環境使用 in-memory repository 時。
        """
        if self.repository_backend == "in_memory" and self.allow_in_memory_repository:
            return False
        if self.repository_backend == "in_memory":
            raise RuntimeError("In-memory repository is disabled outside explicit tests.")
        return bool(self.supabase_url and self.supabase_service_role_key)


@lru_cache
def get_settings() -> Settings:
    """建立並快取全域 Settings 單例。

    首次呼叫時載入本地 .env 檔，從 ``os.environ`` 讀取所有設定值
    並建構 ``Settings`` 實例。後續呼叫直接回傳快取結果（``@lru_cache``）。

    環境變數對應:
        - ``BACKEND_ENVIRONMENT`` → ``environment``
        - ``BACKEND_CORS_ORIGINS`` → ``cors_origins``（逗號分隔）
        - ``BACKEND_REPOSITORY`` → ``repository_backend``
        - ``SUPABASE_URL`` → ``supabase_url``
        - ``SUPABASE_SERVICE_ROLE_KEY`` / ``SUPABASE_KEY`` → ``supabase_service_role_key``
        - ``LLM_PROVIDER`` / ``LLM_MODEL`` / ``LLM_*`` → LLM 相關設定
        - ``NVIDIA_API_KEY`` / ``NVIDIA_*`` → NVIDIA NIM 相關設定

    Returns:
        Settings: 全域設定單例。
    """
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
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_reasoning_effort=os.getenv("GEMINI_REASONING_EFFORT", "minimal"),
        nvidia_api_key=os.getenv("NVIDIA_API_KEY"),
        nvidia_api_base=os.getenv("NVIDIA_API_BASE", "https://integrate.api.nvidia.com/v1"),
        nvidia_llm_model=os.getenv("NVIDIA_LLM_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"),
        nvidia_enable_thinking=_env_bool("NVIDIA_ENABLE_THINKING", False),
        nvidia_reasoning_budget=int(os.getenv("NVIDIA_REASONING_BUDGET", "4096")),
        cohere_api_key=os.getenv("COHERE_API_KEY"),
        cohere_llm_model=os.getenv("COHERE_LLM_MODEL", "cohere/command-a-plus-05-2026"),
    )
