import os

import pytest
from fastapi.testclient import TestClient

# app.main 在匯入時會建立正式 app；測試必須在匯入前明確提供隔離設定。
os.environ.setdefault("BACKEND_REPOSITORY", "in_memory")
os.environ.setdefault("ALLOW_IN_MEMORY_REPOSITORY", "true")
os.environ.setdefault("HISTOSPHERE_ADMIN_KEY", "test-admin")

from app.core.auth import AuthenticatedUser
from app.core.config import get_settings
from app.main import create_app
from app.models.domain import Event, EventTask, ExperimentCondition, Participant, Persona, RagSource, TaskAttempt, WikiSource
from app.providers.llm.base import ChatGenerationResult


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
    def __init__(self) -> None:
        self.chat_prompts: list[str] = []
        self.greeting_prompts: list[str] = []

    @staticmethod
    def _llm_metadata(task_name: str) -> dict:
        return {
            "provider": "fake-test",
            "model": "fake-model",
            "llm_call": {
                "correlation_id": f"fake-{task_name}",
                "task_name": task_name,
                "provider": "fake-test",
                "model": "fake-model",
                "status": "completed",
                "latency_ms": 1,
                "attempt_count": 1,
                "transient_retry_count": 0,
                "schema_repair_count": 0,
                "provider_switching_enabled": False,
                "fallback_reason": None,
                "prompt_tokens": 11,
                "cached_prompt_tokens": 4,
                "completion_tokens": 7,
                "reasoning_tokens": 2,
                "total_tokens": 18,
                "estimated_cost_usd": 0.0001,
                "finish_reason": "stop",
            },
        }

    async def generate_event_profile(self, event_name: str, sources: list[WikiSource]) -> dict:
        return {
            "canonical_name": event_name,
            "description": f"{event_name} 是一個用於測試的歷史事件，包含人物、時間、地點與制度脈絡。",
            "century": 20,
            "start_year": 1944,
            "end_year": 1944,
            "context": f"{event_name} 的測試脈絡用於驗證事件、任務、人物與對話流程。",
            "source_summary": {
                **self._llm_metadata("generate_event_profile"),
                "source_count": len(sources),
            },
        }

    async def generate_task(self, event: Event, sources: list[WikiSource]) -> EventTask:
        return EventTask(
            event_id=event.id,
            title=f"{event.canonical_name}：歷史思考任務",
            story_text=f"{event.canonical_name} 的測試故事包含原因、證據、人物視角與後果。",
            error_elicitation_task_full_text=f"{event.canonical_name} 的核心問題包含{{{{blank:q01}}}}與不同歷史觀點。",
            evaluation_payload={
                "rubric": "測試 rubric",
                **self._llm_metadata("generate_task"),
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
                prompt_profile={
                    "selection_policy": "fake-test-primary-persona",
                    **self._llm_metadata("generate_personas"),
                },
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
            **self._llm_metadata("judge_task_attempt"),
        }

    async def generate_greeting(
        self,
        event: Event,
        personas: list[Persona],
        condition: ExperimentCondition,
        attempt: TaskAttempt,
        prompt: str,
    ) -> ChatGenerationResult:
        self.greeting_prompts.append(prompt)
        speaker = personas[0].name if condition.roleplay_enabled and personas else "AI Tutor"
        if condition.ebl_enabled:
            if condition.roleplay_enabled:
                response = (
                    f"我是{speaker}。{event.canonical_name}的局勢正在我眼前展開；"
                    "我想先聽你說明，你剛才是根據什麼理由作答？"
                )
            else:
                response = f"我們從{event.canonical_name}開始。你剛才是根據什麼理由作答？"
            metadata = {
                "dialogue_state": "NOTICE_ERROR",
                "dialogue_move": "error_awareness_prompt",
                "disclosure_level": "D0",
                "learner_revision_status": "not_yet",
                "completion_status": "continue",
                "fidelity_flags": [],
            }
        elif condition.roleplay_enabled:
            response = (
                f"我是{speaker}。我正身處{event.canonical_name}的局勢之中；"
                "你想先從人物、衝突，還是事件背景談起？"
            )
            metadata = {
                "dialogue_state": "STANDARD_CHAT",
                "dialogue_move": "natural_response",
                "learner_revision_status": "not_applicable",
                "completion_status": "continue",
                "fidelity_flags": [],
            }
        else:
            response = f"我們來談{event.canonical_name}。你想先從哪個面向開始？"
            metadata = {
                "dialogue_state": "STANDARD_CHAT",
                "dialogue_move": "natural_response",
                "learner_revision_status": "not_applicable",
                "completion_status": "continue",
                "fidelity_flags": [],
            }
        return ChatGenerationResult(
            response=response,
            interaction_metadata=metadata,
            llm_metadata=self._llm_metadata("generate_greeting"),
        )

    async def generate_chat_response(
        self,
        event: Event,
        persona: Persona | None,
        condition: ExperimentCondition,
        task_attempt: TaskAttempt | None,
        user_message: str,
        prompt: str,
        rag_sources: list[RagSource],
    ) -> ChatGenerationResult:
        self.chat_prompts.append(prompt)
        speaker = persona.name if persona else "AI Tutor"
        if condition.ebl_enabled:
            voice = "我請你" if persona else "請"
            response = (
                f"{speaker}：{voice}再想一想，原本的答案有哪裡需要改變，為什麼？"
            )
            interaction_metadata = {
                "dialogue_state": "REFLECT",
                "dialogue_move": "reflection_prompt",
                "disclosure_level": "D1",
                "learner_revision_status": "not_yet",
                "completion_status": "continue",
                "fidelity_flags": [],
            }
        else:
            voice = "依我所見" if persona else "一般來說"
            response = (
                f"{speaker}：{voice}，{event.canonical_name} 的重要性在於它改變了制度與歷史發展。"
            )
            interaction_metadata = {
                "dialogue_state": "STANDARD_CHAT",
                "dialogue_move": "natural_response",
                "learner_revision_status": "not_applicable",
                "completion_status": "continue",
                "fidelity_flags": [],
            }
        return ChatGenerationResult(
            response=response,
            annotations=[],
            related_events=[],
            dynamic_context="fake dynamic context",
            interaction_metadata=interaction_metadata,
            llm_metadata=self._llm_metadata("generate_chat_response"),
        )


class FakeSupabaseJWTVerifier:
    """Treat the bearer token as the verified Auth user id for API tests."""

    async def verify(self, token: str) -> AuthenticatedUser:
        return AuthenticatedUser(id=token)


@pytest.fixture()
def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("BACKEND_REPOSITORY", "in_memory")
    monkeypatch.setenv("ALLOW_IN_MEMORY_REPOSITORY", "true")
    monkeypatch.setenv("HISTOSPHERE_ADMIN_KEY", "test-admin")
    get_settings.cache_clear()
    app = create_app()
    app.state.supabase_jwt_verifier = FakeSupabaseJWTVerifier()
    app.state.repository.save_participant(
        Participant(
            code="PTEST",
            auth_user_id="participant-001",
            condition_list=["04"],
        )
    )
    fake_provider = FakeWikipediaProvider()
    fake_llm = FakeLLMProvider()
    app.state.wikipedia_provider = fake_provider
    app.state.event_initialization_service.wikipedia_provider = fake_provider
    app.state.llm_provider = fake_llm
    app.state.event_initialization_service.llm_provider = fake_llm
    app.state.opening_service.llm_provider = fake_llm
    app.state.chat_service.llm_provider = fake_llm
    app.state.task_service.llm_provider = fake_llm
    return TestClient(app, headers={"Authorization": "Bearer participant-001"})
