"""LLM provider factory.

本模組是 runtime 建立 LLM provider 的唯一入口。產品後端固定使用
LiteLLMProvider；若未來要支援其他 provider，也應在這裡顯式分流。
"""

from app.core.config import Settings
from app.providers.llm.base import LLMProvider
from app.providers.llm.litellm_provider import LiteLLMProvider


def build_llm_provider(settings: Settings) -> LLMProvider:
    """依設定建立正式 LLM provider；runtime 不再支援 stub fallback。"""
    if settings.llm_provider != "litellm":
        raise RuntimeError("Only LLM_PROVIDER=litellm is supported in runtime.")
    return LiteLLMProvider(settings)
