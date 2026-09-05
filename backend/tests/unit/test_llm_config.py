from __future__ import annotations

from app.core.config import _default_llm_model


def test_output_budget_defaults_to_16384_and_respects_explicit_override(monkeypatch) -> None:
    from app.core import config

    monkeypatch.setattr(config, "load_local_env", lambda: None)
    monkeypatch.delenv("LLM_MAX_OUTPUT_TOKENS", raising=False)
    assert config.Settings().llm_max_output_tokens == 16384
    assert config.get_settings.__wrapped__().llm_max_output_tokens == 16384
    monkeypatch.setenv("LLM_MAX_OUTPUT_TOKENS", "8192")
    assert config.get_settings.__wrapped__().llm_max_output_tokens == 8192


def test_gemini_is_primary_when_both_provider_keys_exist(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvidia-test-key")
    monkeypatch.delenv("GEMINI_LLM_MODEL", raising=False)

    assert _default_llm_model() == "gemini/gemini-3.5-flash-lite"


def test_nvidia_is_primary_when_gemini_is_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "nvidia-test-key")
    monkeypatch.delenv("NVIDIA_LLM_MODEL", raising=False)

    assert _default_llm_model() == "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"


def test_legacy_fallback_environment_is_ignored(monkeypatch) -> None:
    from app.core import config

    monkeypatch.setattr(config, "load_local_env", lambda: None)
    monkeypatch.setenv("LLM_MODEL", "openai/locked-model")
    monkeypatch.setenv(
        "LLM_FALLBACK_MODELS",
        "gemini/gemini-3.5-flash-lite,nvidia/custom-model",
    )

    settings = config.get_settings.__wrapped__()
    assert settings.llm_model == "openai/locked-model"
    assert "llm_fallback_models" not in settings.model_dump()
