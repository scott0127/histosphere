import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.models.domain import Event, EventTask, ExperimentCondition, Persona, RagSource, TaskAttempt, WikiSource


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


class FakeLLMProvider:
    async def generate_event_profile(self, event_name: str, sources: list[WikiSource]) -> dict:
        return {
            "canonical_name": event_name,
            "description": f"{event_name} 是一個用於測試的歷史事件，包含人物、時間、地點與制度脈絡。",
            "century": 20,
            "start_year": 1944,
            "end_year": 1944,
            "context": f"{event_name} 的測試脈絡用於驗證事件、任務、人物與對話流程。",
            "source_summary": {"provider": "fake-test", "source_count": len(sources)},
        }

    async def generate_task(self, event: Event, sources: list[WikiSource]) -> EventTask:
        return EventTask(
            event_id=event.id,
            title=f"{event.canonical_name}：歷史思考任務",
            story_text=f"{event.canonical_name} 的測試故事包含原因、證據、人物視角與後果。",
            display_text=f"{event.canonical_name} 的核心問題包含{{{{blank:q01}}}}與不同歷史觀點。",
            evaluation_payload={
                "rubric": "測試 rubric",
                "questions": [
                    {
                        "id": "q01",
                        "blank_id": "q01",
                        "type": "cloze",
                        "prompt": "請填入一個核心問題。",
                        "correct_answer": "原因",
                        "source_text": "原因",
                        "required": True,
                    }
                ],
            },
        )

    async def generate_personas(self, event: Event, sources: list[WikiSource]) -> list[Persona]:
        return [
            Persona(
                event_id=event.id,
                name=f"{event.canonical_name}見證者",
                role="歷史觀察者",
                biography=f"用於測試 {event.canonical_name} 對話流程的歷史人物。",
                expertise_areas=[event.canonical_name],
                prompt_profile={"selection_policy": "fake-test-primary-persona"},
            )
        ]

    async def judge_task_attempt(
        self,
        event: Event,
        task: EventTask,
        response_payload: dict,
    ) -> dict:
        return {
            "result": "partial",
            "score": 0.5,
            "misconception_summary": "測試判斷",
            "feedback": "測試回饋",
            "provider": "fake-test",
        }

    async def generate_greeting(
        self,
        event: Event,
        personas: list[Persona],
        condition: ExperimentCondition,
        attempt: TaskAttempt,
    ) -> str:
        speaker = personas[0].name if condition.roleplay_enabled and personas else "AI Tutor"
        return f"{speaker}：我們來討論 {event.canonical_name}。"

    async def generate_chat_response(
        self,
        event: Event,
        persona: Persona | None,
        condition: ExperimentCondition,
        task_attempt: TaskAttempt | None,
        user_message: str,
        prompt: str,
        rag_sources: list[RagSource],
    ) -> tuple[str, list, list, str]:
        speaker = persona.name if persona else "AI Tutor"
        return (
            f"{speaker} 回覆：{event.canonical_name} 的測試回答。",
            [],
            [],
            "fake dynamic context",
        )


@pytest.fixture()
def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("BACKEND_REPOSITORY", "in_memory")
    monkeypatch.setenv("ALLOW_IN_MEMORY_REPOSITORY", "true")
    monkeypatch.setenv("HISTOSPHERE_ADMIN_KEY", "test-admin")
    get_settings.cache_clear()
    app = create_app()
    fake_provider = FakeWikipediaProvider()
    fake_llm = FakeLLMProvider()
    app.state.wikipedia_provider = fake_provider
    app.state.event_initialization_service.wikipedia_provider = fake_provider
    app.state.llm_provider = fake_llm
    app.state.event_initialization_service.llm_provider = fake_llm
    app.state.conversation_service.llm_provider = fake_llm
    app.state.chat_service.llm_provider = fake_llm
    app.state.task_service.llm_provider = fake_llm
    return TestClient(app)
