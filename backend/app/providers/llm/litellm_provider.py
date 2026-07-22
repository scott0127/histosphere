"""LiteLLM provider.

本模組負責把 Histosphere 的 LLMProvider 介面轉接到 LiteLLM。Runtime
統一透過 LiteLLM 呼叫 Gemini、GPT、本地 OpenAI-compatible 模型或 GPT
OAuth proxy；service 層不應直接依賴任何特定模型 SDK。

主要職責:
    - 組裝各生成任務（event profile、task、persona、greeting、chat）的 prompt。
    - 透過 ``LLMJsonRunner`` 呼叫 LLM 並取得 structured JSON 回覆。
    - 將 structured payload 轉換為 domain model。
    - 在 source_summary / prompt_profile 中嵌入 provider metadata。
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
from app.providers.llm.base import ChatGenerationResult
from app.providers.llm.structured import (
    ChatOutputPayload,
    EventProfilePayload,
    GeneratedTaskPayload,
    PersonaListPayload,
    TaskJudgementPayload,
)


CHAT_OUTPUT_JSON_CONTRACT = (
    'Return exactly one JSON object with every key in this shape: '
    '{"response":"learner-facing Traditional Chinese text","annotations":[],'
    '"related_events":[],"dynamic_context":"","dialogue_state":"STATE",'
    '"dialogue_move":"MOVE","disclosure_level":null,'
    '"learner_revision_status":"STATUS","completion_status":"STATUS",'
    '"fidelity_flags":[]}. '
    "Use the interaction_runtime values for STATE, MOVE, disclosure_level, and statuses. "
    "fidelity_flags must contain only suspected rule violations; otherwise return an empty list. "
    "Do not add keys outside this object or wrap it in markdown."
)
"""Structured completion contract shared by opening and later chat turns."""


class LiteLLMProvider:
    """正式 runtime LLM provider，透過 LiteLLM 統一呼叫各模型。

    所有生成任務皆透過 ``LLMJsonRunner`` 執行，確保回覆
    為 structured JSON 並通過 Pydantic 驗證。

    Attributes:
        settings: 全域設定實例。
        runner: LLM JSON 執行器。
    """

    def __init__(self, settings: Settings) -> None:
        """初始化 LiteLLM provider。

        Args:
            settings: 全域 Settings 實例，傳遞給 ``LLMJsonRunner``。
        """
        self.settings = settings
        self.runner = LLMJsonRunner(settings)

    async def generate_event_profile(self, event_name: str, sources: list[WikiSource]) -> dict:
        """根據事件名稱與 Wikipedia 來源生成 events 表需要的背景資訊。

        產生 canonical_name、description、century、start_year、end_year、
        context 與 source_summary，並在 source_summary 中嵌入
        provider metadata。

        Args:
            event_name: 事件名稱。
            sources: Wikipedia 來源清單。

        Returns:
            dict: 事件 profile 的欄位字典。
        """
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
        """產生 prototype task；正式實驗可由教師手動改成 manual/teacher_modified。

        生成含 story_text、display_text（含「____」空格）與
        evaluation_payload（rubric、expected_points 等）的 task。

        Args:
            event: 目標事件。
            sources: Wikipedia 來源清單。

        Returns:
            EventTask: 生成的 task（revision_state 為 ``"llm_generated"``）。
        """
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
        """根據 task 設定與 learner 作答產生初步 judgement。

        評估重點：historical accuracy、evidence use、causal reasoning
        與 learner misconceptions。

        Args:
            event: 關聯事件。
            task: 關聯 task。
            response_payload: Learner 的作答內容。

        Returns:
            dict: 包含 result、misconception_summary、feedback、
                score、provider、model。
        """
        payload = await self.runner.run_json(
            schema=TaskJudgementPayload,
            task_name="judge_task_attempt",
            system_prompt=self._system_prompt(),
            user_prompt=(
                "Judge the learner response for this historical thinking task.\n"
                "Use result = correct, partial, or incorrect. Do not over-grade vague answers.\n"
                "Focus on historical accuracy, evidence use, causal reasoning, and learner misconceptions.\n"
                "Return JSON with keys: result, misconception_summary, feedback, score, provider, and question_results. "
                "question_results must contain one object per task question with question_id, learner_answer, correctness, "
                "expected_answer, error_code, historical_concept, reasoning_process, evidence_ids, classifier_confidence, "
                "and teacher_review_status. Use unclassified when an error type is uncertain.\n\n"
                f"Event:\n{event.model_dump()}\n\n"
                f"Task:\n{task.model_dump()}\n\n"
                f"Learner response payload:\n{response_payload}"
            ),
        )
        result = payload.model_dump()
        result.update(self._provider_metadata())
        return result

    async def generate_personas(self, event: Event, sources: list[WikiSource]) -> list[Persona]:
        """產生事件的一位 primary historical persona。

        選取該事件最具代表性的歷史人物，生成含 prompt_profile
        （speaking_style、knowledge_boundary 等）的 Persona。

        Args:
            event: 目標事件。
            sources: Wikipedia 來源清單。

        Returns:
            list[Persona]: 僅含一位 persona 的清單。
        """
        payload = await self.runner.run_json(
            schema=PersonaListPayload,
            task_name="generate_personas",
            system_prompt=self._system_prompt(),
            user_prompt=(
                "Select exactly one primary historical persona for this event.\n"
                "If the teacher has not specified a persona, choose the figure most central or representative to the event.\n"
                "The persona must be historically defensible. Do not invent fictional people unless the event lacks identifiable figures.\n"
                "prompt_profile must contain structured data rather than a prewritten greeting. Include speaking_style, "
                "forms_of_address, social_position, relationship_to_event, event_timepoint, event_timepoint_year, "
                "event_location, event_vantage_point, current_stakes, event_anchor_terms, knowledge_cutoff_year, "
                "firsthand_experience_allowed, firsthand_experience_scope, temporal_boundary, geographic_boundary, "
                "knowledge_boundary, stance, selection_policy, selection_reason, and deliberate_error_enabled=false. "
                "The selected timepoint and knowledge cutoff must not extend beyond the person's life or the chosen "
                "in-event scene. Do not provide a prewritten greeting.\n"
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
        prompt: str,
    ) -> ChatGenerationResult:
        """Generate the first turn from the canonical modules also used by later chat."""
        payload = await self.runner.run_json(
            schema=ChatOutputPayload,
            task_name="generate_greeting",
            system_prompt=self._system_prompt(),
            user_prompt=(
                "Generate the first learner-facing conversation turn from the canonical prompt modules below.\n"
                f"{CHAT_OUTPUT_JSON_CONTRACT}\n\n"
                f"Prompt modules:\n{prompt}"
            ),
        )
        return self._chat_generation_result(payload, event)

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
        """依組裝好的 prompt 產生聊天回覆。

        尊重 role-play 邊界與 EBL/Standard Chat 策略，
        使用繁體中文回覆（除非使用者要求其他語言）。

        Args:
            event: 關聯事件。
            persona: 當前使用的 persona 或 None。
            condition: 當前實驗條件。
            task_attempt: 關聯的 task attempt（可選）。
            user_message: 使用者訊息。
            prompt: PromptService 組裝的完整 prompt。
            rag_sources: RAG 檢索結果。

        Returns:
            ChatGenerationResult: Visible response plus hidden interaction metadata。
        """
        payload = await self.runner.run_json(
            schema=ChatOutputPayload,
            task_name="generate_chat_response",
            system_prompt=self._system_prompt(),
            user_prompt=(
                "Respond to the learner according to the provided prompt modules.\n"
                "Respect role-play boundaries and the EBL/Standard Chat policy.\n"
                "Use Traditional Chinese unless the user asks otherwise. English terms are allowed only when useful.\n"
                f"{CHAT_OUTPUT_JSON_CONTRACT}\n\n"
                f"Prompt modules:\n{prompt}\n\n"
                f"User message:\n{user_message}"
            ),
        )
        return self._chat_generation_result(payload, event)

    @staticmethod
    def _chat_generation_result(payload: ChatOutputPayload, event: Event) -> ChatGenerationResult:
        """Map the one structured completion schema used by opening and chat."""
        legacy_disclosure = {
            "L0": "D0",
            "L1": "D1",
            "L2": "D2",
            "L3": "D3",
            "L4": "D4",
        }.get(payload.scaffold_level)
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
        return ChatGenerationResult(
            response=payload.response,
            annotations=annotations,
            related_events=related_events,
            dynamic_context=payload.dynamic_context,
            interaction_metadata={
                "dialogue_state": payload.dialogue_state,
                "dialogue_move": payload.dialogue_move,
                "disclosure_level": payload.disclosure_level or legacy_disclosure,
                "learner_revision_status": payload.learner_revision_status,
                "completion_status": payload.completion_status,
                "fidelity_flags": payload.fidelity_flags,
            },
        )

    # ── Internal helpers ───────────────────────────────────────

    @staticmethod
    def _system_prompt() -> str:
        """組裝 LLM system prompt。

        基礎 prompt 規定語言（繁體中文）、史實邊界與 JSON 輸出格式。
        Returns:
            str: 完整的 system prompt。
        """
        base_prompt = (
            "You are the LLM backend for Histosphere, a master's thesis prototype about "
            "Error-Based Learning and AI historical persona role-play. "
            "Prioritize historical accuracy, source awareness, and clear uncertainty marking. "
            "Chinese output must use Traditional Chinese. Do not use Simplified Chinese. "
            "Return only valid JSON matching the requested schema. Do not include markdown fences."
        )
        return base_prompt

    def _provider_metadata(self) -> dict[str, str]:
        """取得最近一次成功呼叫的 provider/model metadata。

        用於嵌入 source_summary、evaluation_payload 與
        prompt_profile，方便研究 log 與後台除錯。

        Returns:
            dict[str, str]: 包含 ``"provider"`` 與 ``"model"`` 鍵值。
        """
        return {
            "provider": self.runner.last_provider,
            "model": self.runner.last_model,
        }

    @staticmethod
    def _format_sources(sources: list[WikiSource]) -> str:
        """把 Wikipedia source 壓縮成 prompt 可讀格式。

        每個來源顯示 language、title、url、summary（截斷 1200 字元）
        與最多 6 個 section（各截斷 900 字元）。

        Args:
            sources: WikiSource 清單。

        Returns:
            str: 格式化後的來源文字，各來源以空行分隔。
        """
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
