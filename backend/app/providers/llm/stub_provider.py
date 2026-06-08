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


class StubLLMProvider:
    """Deterministic provider for local development and tests."""

    async def generate_event_profile(self, event_name: str, sources: list[WikiSource]) -> dict:
        context = "\n\n".join(source.summary or "" for source in sources).strip()
        return {
            "canonical_name": event_name,
            "description": context[:240] or f"{event_name} 的事件資料待補。",
            "century": None,
            "start_year": None,
            "end_year": None,
            "context": context or f"{event_name} 的背景資料暫時不足，需由教師補充。",
            "source_summary": {
                "provider": "stub",
                "languages": [source.language for source in sources],
                "source_count": len(sources),
            },
        }

    async def generate_task(self, event: Event, sources: list[WikiSource]) -> EventTask:
        summary = (event.context or event.description or event.canonical_name)[:180]
        story_text = (
            f"{event.canonical_name} 是一個需要從時間、地點、參與者與史料脈絡理解的歷史事件。"
            f"根據目前資料，{summary}"
        )
        display_text = (
            f"{event.canonical_name} 是一個需要理解「____」、「____」與「____」的歷史事件。"
            "請先用自己的話補上你認為最重要的概念，再進入對話。"
        )
        return EventTask(
            event_id=event.id,
            title=f"{event.canonical_name}：歷史故事挖洞",
            story_text=story_text,
            display_text=display_text,
            evaluation_payload={
                "rubric": "LLM 判斷是否能指出事件核心時間/地點/人物/因果脈絡之一，第一版不做逐格評分。",
                "expected_points": ["time", "place", "people", "cause", "consequence"],
            },
        )

    async def judge_task_attempt(
        self,
        event: Event,
        task: EventTask,
        response_payload: dict,
    ) -> dict:
        answer_text = str(response_payload.get("answer_text") or response_payload.get("answer") or "").strip()
        result = "incorrect"
        if len(answer_text) >= 24:
            result = "correct"
        elif len(answer_text) >= 8:
            result = "partial"
        return {
            "result": result,
            "misconception_summary": (
                "回答已提供部分理解，但仍需要釐清時間、地點、參與者與因果關係。"
                if result != "correct"
                else "回答已能初步描述事件核心概念。"
            ),
            "feedback": "接下來的對話會根據你的回答延伸提問。",
            "provider": "stub",
        }

    async def generate_personas(self, event: Event, sources: list[WikiSource]) -> list[Persona]:
        context_hint = (sources[0].summary if sources else event.context or "")[:120]
        return [
            Persona(
                event_id=event.id,
                name=f"{event.canonical_name} 見證者",
                english_name=None,
                role="事件親歷者",
                biography=f"一位置身於「{event.canonical_name}」脈絡中的歷史人物，用第一人稱回顧事件現場。{context_hint}",
                expertise_areas=["historical context", "perspective-taking"],
                sources=[
                    {"title": source.title, "url": source.page_url, "language": source.language}
                    for source in sources
                ],
                prompt_profile={
                    "speaking_style": "reflective",
                    "knowledge_boundary": "只回答與自身時代和事件脈絡相符的內容。",
                    "deliberate_error_enabled": False,
                },
                sort_order=0,
            ),
            Persona(
                event_id=event.id,
                name=f"{event.canonical_name} 史料整理者",
                english_name=None,
                role="史料解讀者",
                biography=f"負責整理「{event.canonical_name}」相關資料、辨識資訊缺口與史料限制的角色。",
                expertise_areas=["source interpretation", "evidence-based argumentation"],
                sources=[
                    {"title": source.title, "url": source.page_url, "language": source.language}
                    for source in sources
                ],
                prompt_profile={
                    "speaking_style": "analytical",
                    "knowledge_boundary": "標記不確定與史料不足之處。",
                    "deliberate_error_enabled": False,
                },
                sort_order=1,
            ),
        ]

    async def generate_greeting(
        self,
        event: Event,
        personas: list[Persona],
        condition: ExperimentCondition,
        attempt: TaskAttempt,
    ) -> str:
        judgement = attempt.judgement_payload.get("result", "submitted")
        if not condition.roleplay_enabled:
            if condition.ebl_enabled:
                return (
                    f"你已完成「{event.canonical_name}」的 task（目前判斷：{judgement}）。"
                    "我會先協助你檢查自己的推論、證據與可能誤解，再討論答案。"
                )
            return f"你已完成「{event.canonical_name}」的 task。我是一般 AI 助手，可以直接回答你的問題。"
        names = "、".join(persona.name for persona in personas)
        if condition.ebl_enabled:
            return (
                f"我們是 {names}。我會根據你剛剛 task 中呈現的理解與可能誤解，"
                "透過歷史人物視角引導你重新檢查證據與推論。"
            )
        return f"我們已進入「{event.canonical_name}」的歷史情境。我是 {names}，你可以直接向我們提問。"

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
        misconception = ""
        if task_attempt:
            misconception = task_attempt.judgement_payload.get("misconception_summary", "")

        if condition.roleplay_enabled and persona:
            speaker_intro = f"以「{persona.name}／{persona.role}」的角度來看"
        elif condition.ebl_enabled:
            speaker_intro = "以 EBL tutor 的方式來看"
        else:
            speaker_intro = "以一般 AI 助手的方式來看"

        if condition.response_policy == "scaffold":
            response = (
                f"{speaker_intro}，我先不直接給結論。你問的是：{user_message}\n\n"
                f"請先回頭檢查三件事：事件的時間位置、你使用的證據、以及你的因果推論。"
                f"{' 你剛剛的 task 顯示：' + misconception if misconception else ''}\n\n"
                "接著你可以試著說明：你判斷這個答案的史料根據是什麼？"
            )
        else:
            source_hint = (event.context or event.description or event.canonical_name)[:180]
            response = (
                f"{speaker_intro}，{user_message}\n\n"
                f"直接回答：這個問題需要放回「{event.canonical_name}」的脈絡理解。{source_hint}"
            )

        annotations = [
            Annotation(
                text=event.canonical_name,
                explanation="目前對話的核心歷史事件；第一版主要依 Wikipedia 摘要與 LLM 生成脈絡。",
            )
        ]
        dynamic_context = (
            "EBL scaffold：聚焦 learner misconceptions、historical thinking 與 source interpretation。"
            if condition.ebl_enabled
            else "Direct answer：以直接問答為主。"
        )
        return response, annotations, [], dynamic_context
