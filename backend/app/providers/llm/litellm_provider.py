"""LiteLLM provider.

本模組負責把 Histosphere 的 LLMProvider 介面轉接到 LiteLLM。Runtime
統一透過 LiteLLM 呼叫 Gemini、GPT、本地 OpenAI-compatible 模型或 GPT
OAuth proxy；service 層不應直接依賴任何特定模型 SDK。
"""

from app.core.config import Settings
from app.models.domain import (
    Annotation,
    Event,
    EventTask,
    ExperimentCondition,
    Persona,
    RagSource,
    RelatedEvent,
    TaskAttempt,
    WikiSource,
)
from app.providers.llm.json_runner import LLMJsonRunner
from app.providers.llm.structured import (
    ChatOutputPayload,
    EventProfilePayload,
    GeneratedTaskPayload,
    PersonaListPayload,
    TaskJudgementPayload,
)


BACKEND_SYSTEM_PROMPTS = {
    "no_ebl_no_roleplay": (
        "Do not role-play as a historical figure. Keep answers concise, historically grounded, and transparent about uncertainty."
    ),
    "ebl_no_roleplay": (
        "Use Error-Based Learning scaffolding. Treat mistakes as productive entry points for reflection and historical reasoning."
    ),
    "no_ebl_roleplay": (
        "Speak from the selected persona perspective while preserving historical boundaries. Do not invent facts beyond available context."
    ),
    "ebl_roleplay": (
        "Combine persona role-play with Error-Based Learning scaffolding. Maintain persona voice, historical accuracy, and reflective guidance."
    ),
}


class LiteLLMProvider:
    """正式 runtime LLM provider。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.runner = LLMJsonRunner(settings)

    async def generate_event_profile(self, event_name: str, sources: list[WikiSource]) -> dict:
        """根據事件名稱與 Wikipedia 來源生成 events 表需要的背景資訊。"""
        payload = await self.runner.run_json(
            schema=EventProfilePayload,
            task_name="generate_event_profile",
            system_prompt=self._system_prompt(),
            user_prompt=(
                "Generate a historically accurate event profile for the thesis prototype.\n"
                "Use Traditional Chinese for Chinese content. English names are allowed when historically appropriate.\n"
                "If century, start_year, or end_year is uncertain, use null.\n"
                "Return JSON with keys: canonical_name, description, century, start_year, end_year, context, source_summary.\n\n"
                f"Event name: {event_name}\n\n"
                f"Wikipedia sources:\n{self._format_sources(sources)}"
            ),
        )
        result = payload.model_dump()
        result["source_summary"] = {
            **result.get("source_summary", {}),
            **self._provider_metadata(),
            "source_count": len(sources),
            "source_titles": [source.title for source in sources],
        }
        return result

    async def generate_task(self, event: Event, sources: list[WikiSource]) -> EventTask:
        """產生 prototype task；正式實驗可由教師手動改成 manual/teacher_modified。"""
        payload = await self.runner.run_json(
            schema=GeneratedTaskPayload,
            task_name="generate_task",
            system_prompt=self._system_prompt(),
            user_prompt=(
                "Create one prototype historical thinking task for this event.\n"
                "The task must be historically strict, suitable for a master's thesis prototype, and editable by a teacher.\n"
                "For now, story_text should be the accurate complete story; display_text should include visible blanks using 「____」.\n"
                "evaluation_payload must include: rubric, expected_points, historical_thinking_targets, source_basis, "
                "and prototype_item_types. Include possible item types: cloze, multiple_choice, true_false.\n"
                "Use Traditional Chinese only, except English proper nouns when necessary.\n"
                "Return JSON with keys: title, story_text, display_text, evaluation_payload.\n\n"
                f"Event:\n{event.model_dump()}\n\n"
                f"Wikipedia sources:\n{self._format_sources(sources)}"
            ),
        )
        return EventTask(
            event_id=event.id,
            title=payload.title,
            story_text=payload.story_text,
            display_text=payload.display_text,
            evaluation_payload={
                **payload.evaluation_payload,
                **self._provider_metadata(),
            },
            revision_state="llm_generated",
        )

    async def judge_task_attempt(
        self,
        event: Event,
        task: EventTask,
        response_payload: dict,
    ) -> dict:
        """根據 task 設定與 learner 作答產生初步 judgement。"""
        payload = await self.runner.run_json(
            schema=TaskJudgementPayload,
            task_name="judge_task_attempt",
            system_prompt=self._system_prompt(),
            user_prompt=(
                "Judge the learner response for this historical thinking task.\n"
                "Use result = correct, partial, or incorrect. Do not over-grade vague answers.\n"
                "Focus on historical accuracy, evidence use, causal reasoning, and learner misconceptions.\n"
                "Return JSON with keys: result, misconception_summary, feedback, score, provider.\n\n"
                f"Event:\n{event.model_dump()}\n\n"
                f"Task:\n{task.model_dump()}\n\n"
                f"Learner response payload:\n{response_payload}"
            ),
        )
        result = payload.model_dump()
        result.update(self._provider_metadata())
        return result

    async def generate_personas(self, event: Event, sources: list[WikiSource]) -> list[Persona]:
        """產生事件的一位 primary historical persona。"""
        payload = await self.runner.run_json(
            schema=PersonaListPayload,
            task_name="generate_personas",
            system_prompt=self._system_prompt(),
            user_prompt=(
                "Select exactly one primary historical persona for this event.\n"
                "If the teacher has not specified a persona, choose the figure most central or representative to the event.\n"
                "The persona must be historically defensible. Do not invent fictional people unless the event lacks identifiable figures.\n"
                "prompt_profile must include speaking_style, knowledge_boundary, selection_policy, selection_reason, "
                "and deliberate_error_enabled=false.\n"
                "Return JSON with key personas, containing exactly one object.\n\n"
                f"Event:\n{event.model_dump()}\n\n"
                f"Wikipedia sources:\n{self._format_sources(sources)}"
            ),
        )
        personas: list[Persona] = []
        for index, item in enumerate(payload.personas[:1]):
            personas.append(
                Persona(
                    event_id=event.id,
                    name=item.name,
                    english_name=item.english_name,
                    role=item.role,
                    biography=item.biography,
                    expertise_areas=item.expertise_areas,
                    sources=item.sources or [
                        {"title": source.title, "url": source.page_url, "language": source.language}
                        for source in sources
                    ],
                    prompt_profile={
                        **item.prompt_profile,
                        **self._provider_metadata(),
                        "deliberate_error_enabled": item.prompt_profile.get("deliberate_error_enabled", False),
                    },
                    sort_order=index,
                    revision_state="llm_generated",
                )
            )
        return personas

    async def generate_greeting(
        self,
        event: Event,
        personas: list[Persona],
        condition: ExperimentCondition,
        attempt: TaskAttempt,
    ) -> str:
        """依 condition 與 learner task judgement 產生 conversation 開場白。"""
        persona = personas[0] if personas else None
        payload = await self.runner.run_json(
            schema=ChatOutputPayload,
            task_name="generate_greeting",
            system_prompt=self._system_prompt(condition),
            user_prompt=(
                "Generate a concise opening message after the learner submitted the task.\n"
                "If roleplay is enabled, speak as the historical persona. If EBL is enabled, guide reflection without giving answers too quickly.\n"
                "Return JSON with keys: response, annotations, related_events, dynamic_context.\n\n"
                f"Event:\n{event.model_dump()}\n\n"
                f"Condition:\n{condition.model_dump()}\n\n"
                f"Persona:\n{persona.model_dump() if persona else None}\n\n"
                f"Task attempt:\n{attempt.model_dump()}"
            ),
        )
        return payload.response

    async def generate_chat_response(
        self,
        event: Event,
        persona: Persona | None,
        condition: ExperimentCondition,
        task_attempt: TaskAttempt | None,
        user_message: str,
        prompt: str,
        rag_sources: list[RagSource],
    ) -> tuple[str, list[Annotation], list[RelatedEvent], str]:
        """依組裝好的 prompt 產生聊天回覆。"""
        payload = await self.runner.run_json(
            schema=ChatOutputPayload,
            task_name="generate_chat_response",
            system_prompt=self._system_prompt(condition),
            user_prompt=(
                "Respond to the learner according to the provided prompt modules.\n"
                "Respect role-play boundaries and EBL/direct-answer policy.\n"
                "Use Traditional Chinese unless the user asks otherwise. English terms are allowed only when useful.\n"
                "Return JSON with keys: response, annotations, related_events, dynamic_context.\n\n"
                f"Prompt modules:\n{prompt}\n\n"
                f"User message:\n{user_message}"
            ),
        )
        annotations = [
            Annotation(
                text=str(item.get("text", event.canonical_name)),
                explanation=str(item.get("explanation", "")),
            )
            for item in payload.annotations
            if isinstance(item, dict)
        ]
        related_events = [
            RelatedEvent(
                event_name=str(item.get("event_name", "")),
                event_year=item.get("event_year"),
                event_id=item.get("event_id"),
                relevance_reason=str(item.get("relevance_reason", "")),
                is_explorable=bool(item.get("is_explorable", False)),
            )
            for item in payload.related_events
            if isinstance(item, dict) and item.get("event_name")
        ]
        return payload.response, annotations, related_events, payload.dynamic_context

    @staticmethod
    def _system_prompt(condition: ExperimentCondition | None = None) -> str:
        """共同系統規則，限制語言、史實邊界與 JSON output。"""
        base_prompt = (
            "You are the LLM backend for Histosphere, a master's thesis prototype about "
            "Error-Based Learning and AI historical persona role-play. "
            "Prioritize historical accuracy, source awareness, and clear uncertainty marking. "
            "Chinese output must use Traditional Chinese. Do not use Simplified Chinese. "
            "Return only valid JSON matching the requested schema. Do not include markdown fences."
        )
        if not condition:
            return base_prompt
        condition_system_prompt = BACKEND_SYSTEM_PROMPTS.get(condition.condition_key, "").strip()
        if not condition_system_prompt:
            return base_prompt
        return f"{base_prompt}\n\n[backend_condition_system_prompt]\n{condition_system_prompt}"

    def _provider_metadata(self) -> dict[str, str]:
        """記錄實際完成呼叫的 provider/model，方便研究 log 與後台除錯。"""
        return {
            "provider": self.runner.last_provider,
            "model": self.runner.last_model,
        }

    @staticmethod
    def _format_sources(sources: list[WikiSource]) -> str:
        """把 Wikipedia source 壓縮成 prompt 可讀格式。"""
        if not sources:
            return "No Wikipedia sources available."
        chunks: list[str] = []
        for index, source in enumerate(sources, start=1):
            section_text = "\n".join(
                f"- {section.get('title', 'section')}: {str(section.get('content', ''))[:900]}"
                for section in source.sections[:6]
            )
            chunks.append(
                "\n".join(
                    [
                        f"[source_{index}]",
                        f"language: {source.language}",
                        f"title: {source.title}",
                        f"url: {source.page_url or 'unknown'}",
                        f"summary: {(source.summary or '')[:1200]}",
                        f"sections:\n{section_text}" if section_text else "sections: none",
                    ]
                )
            )
        return "\n\n".join(chunks)
