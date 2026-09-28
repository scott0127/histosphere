"""真 LiteLLM/OpenAI adapter、假 HTTP transport：未知模型仍應送往設定的 provider。"""

import asyncio
import json

import httpx
import pytest
from litellm.litellm_core_utils.logging_worker import GLOBAL_LOGGING_WORKER

from app.core.config import Settings
from app.providers.llm.json_runner import LLMJsonRunner


@pytest.mark.parametrize("configured_model", ["gpt-5.6-terra", "openai/gpt-5.6-terra"])
def test_explicit_openai_route_reaches_http_without_changing_model(configured_model, monkeypatch):
    captured = []

    def respond(request):
        body = json.loads(request.content)
        captured.append((str(request.url), body))
        return httpx.Response(200, json={
            "id": "mock-response", "object": "chat.completion", "created": 0,
            "model": "gpt-5.6-terra",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": '{"ok":true}'},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        })

    transport = httpx.MockTransport(respond)

    async def send(client, request, **kwargs):
        # 保留真正 adapter 的 request 建構，所有 async HTTP 在此轉入離線 transport。
        response = await transport.handle_async_request(request)
        response.request = request
        await response.aread()
        return response

    monkeypatch.setattr(httpx.AsyncClient, "send", send)
    # 只測 HTTP 路由；不要讓 SDK 的背景 callback 留在短生命週期測試 event loop。
    monkeypatch.setattr(GLOBAL_LOGGING_WORKER, "ensure_initialized_and_enqueue", lambda async_coroutine: async_coroutine.close())
    runner = LLMJsonRunner(Settings(
        llm_model=configured_model, llm_api_base="https://routing-test.invalid/v1",
        openai_api_key="fake-routing-key", llm_timeout_seconds=2,
    ))
    candidate = runner._candidates()[0]
    assert candidate.model == "openai/gpt-5.6-terra"
    assert candidate.display_model == configured_model
    result = asyncio.run(runner._complete(candidate, system_prompt="Return JSON.", user_prompt="Return ok=true."))
    assert result.content == '{"ok":true}'
    assert result.total_tokens == 15
    assert len(captured) == 1
    url, body = captured[0]
    assert url == "https://routing-test.invalid/v1/chat/completions"
    assert body["model"] == "gpt-5.6-terra"
    assert body["response_format"] == {"type": "json_object"}
    assert "temperature" not in body
