"""Prompt assembly service.

本模組只負責把 condition、event、task_attempt、persona 與 RAG context
組合成 prompt 區塊；不直接呼叫 LLM。這讓 prompt engineering 可以獨立
review，也方便未來把模組開關做成 admin UI 設定。
"""

from app.models.domain import Event, ExperimentCondition, Persona, RagSource, TaskAttempt


BACKEND_TEACHER_PROMPTS = {
    "no_ebl_no_roleplay": (
        "以一般教學助理身份回應學生。先給出清楚答案，再補充必要歷史脈絡與限制。"
    ),
    "ebl_no_roleplay": (
        "以教師引導方式處理學生的錯誤或不完整理解。優先提問、提示證據與因果關係，不要太早給完整答案。"
    ),
    "no_ebl_roleplay": (
        "以歷史人物角色展開沉浸式對話。可以直接回答學生問題，但需標示角色視角與史實界線。"
    ),
    "ebl_roleplay": (
        "以歷史人物角色回應，同時針對學生任務中的誤解設計追問。引導學生修正理解，而不是立即揭露完整答案。"
    ),
}


class PromptService:
    """組裝聊天回覆所需的 prompt modules。"""

    def assemble_chat_prompt(
        self,
        event: Event,
        persona: Persona | None,
        condition: ExperimentCondition,
        task_attempt: TaskAttempt | None,
        user_message: str,
        rag_sources: list[RagSource],
    ) -> str:
        """依照目前 condition/persona/task 狀態合併 prompt modules。"""
        modules = [
            self._admin_teacher_prompt(condition),
            self._condition_policy(condition),
            self._event_context(event),
            self._learner_misconception_context(task_attempt),
            self._source_context(rag_sources),
            self._speaker_context(persona, condition),
            f"[user_message]\n{user_message}",
        ]
        if persona and persona.prompt_profile.get("deliberate_error_enabled") is True:
            modules.append(self._deliberate_error_slot())
        return "\n\n".join(module for module in modules if module)

    @staticmethod
    def _admin_teacher_prompt(condition: ExperimentCondition) -> str:
        """加入後端維護的 condition teacher-facing 指令。"""
        teacher_prompt = BACKEND_TEACHER_PROMPTS.get(condition.condition_key, "").strip()
        if not teacher_prompt:
            return ""
        return f"[backend_teacher_prompt]\n{teacher_prompt}"

    @staticmethod
    def _condition_policy(condition: ExperimentCondition) -> str:
        """產生 EBL/direct-answer 的主要回覆政策。"""
        if condition.response_policy == "scaffold":
            return (
                "[condition_policy]\n"
                "Use Error-Based Learning. Treat learner misconceptions as productive errors. "
                "Guide historical thinking, evidence-based argumentation, source interpretation, and critical reflection. "
                "Do not directly reveal the final answer before the learner attempts self-correction."
            )
        return (
            "[condition_policy]\n"
            "Use a direct-answer style. Give a concise answer first, then explain the historical context."
        )

    @staticmethod
    def _event_context(event: Event) -> str:
        """放入歷史事件基本脈絡；不詳欄位明確標示避免 LLM 自行腦補。"""
        return (
            "[event_context]\n"
            f"Canonical event name: {event.canonical_name}\n"
            f"Description: {event.description or '不詳'}\n"
            f"Century: {event.century if event.century is not None else '不詳'}\n"
            f"Years: {event.start_year if event.start_year is not None else '不詳'}"
            f" - {event.end_year if event.end_year is not None else '不詳'}\n"
            f"Context: {event.context or '不詳'}"
        )

    @staticmethod
    def _learner_misconception_context(task_attempt: TaskAttempt | None) -> str:
        """放入 learner task 作答與 LLM judgement，供 EBL 條件使用。"""
        if not task_attempt:
            return "[learner_task]\nNo task attempt is attached."
        return (
            "[learner_task]\n"
            f"Response payload: {task_attempt.response_payload}\n"
            f"LLM judgement: {task_attempt.judgement_payload}"
        )

    @staticmethod
    def _source_context(rag_sources: list[RagSource]) -> str:
        """放入 RAG 來源；V1 未啟用 retrieval 時會明確提醒使用已知邊界。"""
        if not rag_sources:
            return "[source_context]\nNo RAG retrieval is enabled in V1. Use event context and known historical boundaries."
        sources = "\n".join(f"- {source.section_title}: {source.content}" for source in rag_sources)
        return f"[source_context]\n{sources}"

    @staticmethod
    def _speaker_context(persona: Persona | None, condition: ExperimentCondition) -> str:
        """根據 role-play 條件決定 generic tutor 或 historical persona 身分。"""
        if not condition.roleplay_enabled or not persona:
            return (
                "[speaker_context]\n"
                "You are a generic AI tutor/chatbot, not a historical persona. "
                "Do not pretend to be a historical figure."
            )
        return (
            "[speaker_context]\n"
            f"You are {persona.name}, role: {persona.role or '不詳'}.\n"
            f"Biography: {persona.biography or '不詳'}\n"
            f"Expertise: {', '.join(persona.expertise_areas) or '不詳'}\n"
            f"Prompt profile: {persona.prompt_profile}\n"
            "Speak from the persona perspective, but keep historical boundaries explicit."
        )

    @staticmethod
    def _deliberate_error_slot() -> str:
        """保留 controlled AI inaccuracies 的 prompt 擴充點，V1 預設停用。"""
        return (
            "[deliberate_error_slot]\n"
            "Reserved for controlled AI-generated inaccuracies. Disabled in V1 unless explicitly enabled by admin."
        )
