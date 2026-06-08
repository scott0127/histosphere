import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.models.domain import WikiSource


class FakeWikipediaProvider:
    async def fetch_sources(self, event_id: str, event_name: str, fetch_mode: str = "summary") -> list[WikiSource]:
        return [
            WikiSource(
                event_id=event_id,
                language="zh",
                title=event_name,
                page_url="https://zh.wikipedia.org/wiki/test",
                summary=f"{event_name} 是一個用於測試的歷史事件。它包含時間、人物與背景資料。",
                fetch_mode=fetch_mode,
            ),
            WikiSource(
                event_id=event_id,
                language="en",
                title=event_name,
                page_url="https://en.wikipedia.org/wiki/test",
                summary=f"{event_name} is a test historical event with context, personas, and source material.",
                fetch_mode=fetch_mode,
            ),
        ]


@pytest.fixture()
def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("BACKEND_REPOSITORY", "in_memory")
    monkeypatch.setenv("HISTOSPHERE_ADMIN_KEY", "test-admin")
    get_settings.cache_clear()
    app = create_app()
    fake_provider = FakeWikipediaProvider()
    app.state.wikipedia_provider = fake_provider
    app.state.event_initialization_service.wikipedia_provider = fake_provider
    return TestClient(app)
