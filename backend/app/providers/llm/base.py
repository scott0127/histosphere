"""LLM provider protocol definition.

本模組定義 ``LLMProvider`` Protocol，作為所有 LLM 呼叫層的
抽象介面。Service 層依賴此 Protocol 而非具體實作，
使得測試可替換為 mock，production 則使用 LiteLLMProvider。
"""

from typing import Any, Protocol

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


class LLMProvider(Protocol):
    """LLM 呼叫層抽象介面。

    定義所有 LLM 生成任務的方法簽章，涵蓋事件初始化、
    task 生成、作答判斷、persona 生成、greeting 與聊天回覆。
    """

    async def generate_event_profile(self, event_name: str, sources: list[WikiSource]) -> dict[str, Any]:
        """根據事件名稱與 Wikipedia 來源生成事件背景資料。

        Args:
            event_name: 事件名稱。
            sources: Wikipedia 來源清單。

        Returns:
            dict[str, Any]: 包含 canonical_name、description、
                century、start_year、end_year、context、source_summary。
        """
        ...

    async def generate_task(self, event: Event, sources: list[WikiSource]) -> EventTask:
        """為事件生成 prototype historical thinking task。

        Args:
            event: 目標事件。
            sources: Wikipedia 來源清單。

        Returns:
            EventTask: 生成的 task（revision_state 為 llm_generated）。
        """
        ...

    async def judge_task_attempt(
        self,
        event: Event,
        task: EventTask,
        response_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """判斷 learner 的 task 作答結果。

        Args:
            event: 關聯事件。
            task: 關聯 task。
            response_payload: Learner 的作答內容。

        Returns:
            dict[str, Any]: 包含 result、misconception_summary、
                feedback、score、provider。
        """
        ...

    async def generate_personas(self, event: Event, sources: list[WikiSource]) -> list[Persona]:
        """產生事件的 primary historical persona；V1 預期只回傳一位。

        Args:
            event: 目標事件。
            sources: Wikipedia 來源清單。

        Returns:
            list[Persona]: 生成的 persona 清單（通常僅一位）。
        """
        ...

    async def generate_greeting(
        self,
        event: Event,
        personas: list[Persona],
        condition: ExperimentCondition,
        attempt: TaskAttempt,
    ) -> str:
        """依 condition 與 learner task judgement 產生 conversation 開場白。

        Args:
            event: 關聯事件。
            personas: 可用的 persona 清單。
            condition: 當前實驗條件。
            attempt: Learner 的 task attempt（含 judgement）。

        Returns:
            str: 開場白文字。
        """
        ...

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
        """依組裝好的 prompt 產生聊天回覆。

        Args:
            event: 關聯事件。
            persona: 當前使用的 persona（role-play 模式）或 None。
            condition: 當前實驗條件。
            task_attempt: 關聯的 task attempt（可選）。
            user_message: 使用者訊息。
            prompt: PromptService 組裝的完整 prompt。
            rag_sources: RAG 檢索結果。

        Returns:
            tuple: (response, annotations, related_events, dynamic_context)。
        """
        ...
