from __future__ import annotations

from app.core.config import _default_fallback_models, _default_llm_model


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


def test_formal_runtime_does_not_build_implicit_fallbacks(monkeypatch) -> None:
    monkeypatch.delenv("LLM_FALLBACK_MODELS", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "nvidia-test-key")
    monkeypatch.delenv("NVIDIA_LLM_MODEL", raising=False)

    assert _default_fallback_models("gemini/gemini-3.5-flash-lite") == []


def test_legacy_fallback_environment_is_ignored(monkeypatch) -> None:
    monkeypatch.setenv(
        "LLM_FALLBACK_MODELS",
        "gemini/gemini-3.5-flash-lite,nvidia/custom-model",
    )

    assert _default_fallback_models("gemini/gemini-3.5-flash-lite") == []
