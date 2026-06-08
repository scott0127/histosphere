import asyncio

import httpx

from app.core.config import Settings
from app.providers.wikipedia_provider import WikipediaProvider


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.test")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self) -> dict:
        return self._payload


class FakeAsyncClient:
    responses: dict[str, FakeResponse] = {}

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, headers: dict, params: dict | None = None):
        if "zh.wikipedia.org" in url:
            return self.responses["zh"]
        if "en.wikipedia.org" in url:
            return self.responses["en"]
        raise AssertionError(f"Unexpected URL: {url}")


def run(coro):
    return asyncio.run(coro)


def make_provider(monkeypatch) -> WikipediaProvider:
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    return WikipediaProvider(Settings(wikipedia_timeout_seconds=1.0))


def test_fetch_sources_returns_bilingual_sources(monkeypatch):
    FakeAsyncClient.responses = {
        "zh": FakeResponse(
            200,
            {
                "title": "諾曼第登陸",
                "extract": "諾曼第登陸是第二次世界大戰中的重要軍事行動。",
                "content_urls": {"desktop": {"page": "https://zh.wikipedia.org/wiki/諾曼第登陸"}},
            },
        ),
        "en": FakeResponse(
            200,
            {
                "title": "Normandy landings",
                "extract": "The Normandy landings were the landing operations of the Allied invasion of Normandy.",
                "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Normandy_landings"}},
            },
        ),
    }
    provider = make_provider(monkeypatch)

    sources = run(provider.fetch_sources("event-1", "諾曼第登陸"))

    assert [source.language for source in sources] == ["zh", "en"]
    assert sources[0].title == "諾曼第登陸"
    assert sources[1].title == "Normandy landings"
    assert sources[0].page_url.startswith("https://zh.wikipedia.org")
    assert sources[0].summary.startswith("諾曼第登陸")


def test_fetch_sources_keeps_available_language_when_other_language_404(monkeypatch):
    FakeAsyncClient.responses = {
        "zh": FakeResponse(
            200,
            {
                "title": "法國大革命",
                "extract": "法國大革命是十八世紀末法國的重要政治與社會革命。",
                "content_urls": {"desktop": {"page": "https://zh.wikipedia.org/wiki/法國大革命"}},
            },
        ),
        "en": FakeResponse(404),
    }
    provider = make_provider(monkeypatch)

    sources = run(provider.fetch_sources("event-2", "法國大革命"))

    assert len(sources) == 1
    assert sources[0].language == "zh"
    assert sources[0].title == "法國大革命"


def test_fetch_sources_returns_traceable_fallback_when_no_source_available(monkeypatch):
    FakeAsyncClient.responses = {
        "zh": FakeResponse(404),
        "en": FakeResponse(404),
    }
    provider = make_provider(monkeypatch)

    sources = run(provider.fetch_sources("event-3", "不存在的事件"))

    assert len(sources) == 1
    assert sources[0].language == "zh"
    assert sources[0].page_url is None
    assert sources[0].raw_payload == {"provider_status": "fallback"}
    assert "暫時無法取得" in sources[0].summary


def test_fetch_sources_ignores_empty_extract(monkeypatch):
    FakeAsyncClient.responses = {
        "zh": FakeResponse(
            200,
            {
                "title": "空白條目",
                "extract": "",
                "content_urls": {"desktop": {"page": "https://zh.wikipedia.org/wiki/空白條目"}},
            },
        ),
        "en": FakeResponse(
            200,
            {
                "title": "Valid entry",
                "extract": "A usable English extract.",
                "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Valid_entry"}},
            },
        ),
    }
    provider = make_provider(monkeypatch)

    sources = run(provider.fetch_sources("event-4", "空白條目"))

    assert len(sources) == 1
    assert sources[0].language == "en"
    assert sources[0].summary == "A usable English extract."


def test_fetch_sources_supports_full_mode(monkeypatch):
    FakeAsyncClient.responses = {
        "zh": FakeResponse(
            200,
            {
                "query": {
                    "pages": [
                        {
                            "title": "諾曼第登陸",
                            "extract": "完整條目內容，比 summary 更長。",
                            "fullurl": "https://zh.wikipedia.org/wiki/諾曼第登陸",
                        }
                    ]
                }
            },
        ),
        "en": FakeResponse(404),
    }
    provider = make_provider(monkeypatch)

    sources = run(provider.fetch_sources("event-5", "諾曼第登陸", fetch_mode="full"))

    assert len(sources) == 1
    assert sources[0].fetch_mode == "full"
    assert sources[0].summary == "完整條目內容，比 summary 更長。"
