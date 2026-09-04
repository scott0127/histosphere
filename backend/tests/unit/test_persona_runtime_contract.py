import asyncio

import pytest

from app.core.experiment_conditions import EXPERIMENT_CONDITION_DEFINITIONS
from app.core.persona_prompt_contract import (
    PERSONA_PROMPT_CONTRACT_VERSION,
    audit_persona_response,
    build_persona_runtime_context,
)
from app.models.domain import Event, ExperimentCondition, Persona, TaskAttempt
from app.providers.llm.base import ChatGenerationResult
from app.services.conversation_opening_service import ConversationOpeningService
from app.services.prompt_service import PromptService


def _condition(code: str) -> ExperimentCondition:
    definition = next(item for item in EXPERIMENT_CONDITION_DEFINITIONS if item.code == code)
    return ExperimentCondition(
        condition_key=definition.condition_key,
        label=definition.default_label,
        ebl_enabled=definition.ebl_enabled,
        roleplay_enabled=definition.roleplay_enabled,
        agent_mode=definition.agent_mode,
        response_policy=definition.response_policy,
    )


def _event(name: str = "法國大革命") -> Event:
    return Event(
        id="event-1",
        canonical_name=name,
        description=f"{name}的事件描述",
        start_year=1789,
        end_year=1794,
        context=f"{name}的制度與政治脈絡",
    )


def _persona() -> Persona:
    return Persona(
        id="persona-1",
        event_id="event-1",
        name="馬克西米連·羅伯斯比爾",
        role="國民公會代表",
        biography="法國大革命時期的政治人物。",
        expertise_areas=["法國大革命", "國民公會"],
        prompt_profile={
            "voice": "嚴肅、論辯性強",
            "event_timepoint": "1793 年國民公會統治期間",
            "event_timepoint_year": 1793,
            "event_location": "巴黎",
            "event_vantage_point": "國民公會代表的政治位置",
            "current_stakes": ["共和政體的存續", "戰爭與政治暴力"],
            "event_anchor_terms": ["國民公會", "共和國"],
            "knowledge_cutoff_year": 1793,
        },
    )


def _attempt() -> TaskAttempt:
    return TaskAttempt(
        session_id="session-1",
        task_id="task-1",
        event_id="event-1",
        status="submitted",
        judgement_payload={"result": "partial", "question_results": []},
    )


def _standard_metadata() -> dict:
    return {
        "dialogue_state": "STANDARD_CHAT",
        "dialogue_move": "natural_response",
        "learner_revision_status": "not_applicable",
        "completion_status": "continue",
        "fidelity_flags": [],
    }


def test_legacy_voice_is_normalized_and_used_as_speaking_style():
    persona = _persona()
    context = build_persona_runtime_context(_event(), persona)

    assert persona.prompt_profile["contract_version"] == PERSONA_PROMPT_CONTRACT_VERSION
    assert persona.prompt_profile["speaking_style"] == "嚴肅、論辯性強"
    assert context.speaking_style == "嚴肅、論辯性強"
    assert context.event_timepoint == "1793 年國民公會統治期間"
    assert context.event_location == "巴黎"


def test_runtime_context_changes_with_the_persisted_event():
    persona = _persona()
    french = build_persona_runtime_context(_event("法國大革命"), persona).prompt_block(turn_kind="opening")
    restoration = build_persona_runtime_context(_event("波旁復辟"), persona).prompt_block(turn_kind="opening")

    assert "Historical event: 法國大革命" in french
    assert "Historical event: 波旁復辟" in restoration
    assert french != restoration


def test_persona_prompt_requires_unknown_future_people_to_stay_unknown():
    prompt = build_persona_runtime_context(_event(), _persona()).prompt_block(
        turn_kind="conversation"
    )

    assert "silently check whether it could be known before the knowledge cutoff" in prompt
    assert "do not explain it with modern knowledge" in prompt


def test_persona_prompt_establishes_scene_once_and_keeps_facts_silent_afterward():
    context = build_persona_runtime_context(_event(), _persona())
    opening = context.prompt_block(turn_kind="opening")
    continuation = context.prompt_block(turn_kind="conversation")

    assert "only turn required to establish the identity and scene" in opening
    assert "silent internal constraint, not a checklist to recite" in continuation
    assert "Do not reintroduce the persona" in continuation
    assert "Repeat a scene anchor only" in continuation
    assert "allow natural Chinese subject omission" in continuation


def test_opening_audit_requires_identity_event_anchor_and_in_event_situation():
    context = build_persona_runtime_context(_event(), _persona())

    generic = audit_persona_response(
        "我是羅伯斯比爾。法國大革命具有深遠的歷史影響。",
        context,
        is_opening=True,
    )
    immersive = audit_persona_response(
        "我是羅伯斯比爾。此刻國民公會的爭論正在巴黎升高，我必須面對共和國能否存續的抉擇。",
        context,
        is_opening=True,
    )

    assert "persona_event_situation_missing_on_opening" in generic
    assert immersive == ()


def test_opening_audit_accepts_natural_in_event_situation_language():
    context = build_persona_runtime_context(_event(), _persona())

    flags = audit_persona_response(
        "公民，我是羅伯斯比爾。當此共和國安危存亡之際，我們在國民公會面對內外壓力。",
        context,
        is_opening=True,
    )

    assert flags == ()

    alternative = audit_persona_response(
        "公民，我是羅伯斯比爾。我們正處於共和國存亡與國民公會爭論交織的危機。",
        context,
        is_opening=True,
    )
    assert alternative == ()

    facing_crisis = audit_persona_response(
        "公民，我是羅伯斯比爾。在 1793 年國民公會面臨內外危機的時刻，我們必須作出抉擇。",
        context,
        is_opening=True,
    )
    assert facing_crisis == ()

    situated = audit_persona_response(
        "我是羅伯斯比爾，正置身國民公會的政治爭論之中。",
        context,
        is_opening=True,
    )
    assert situated == ()

    natural_timepoint = audit_persona_response(
        "我是羅伯斯比爾，身在國民公會，正值共和國存亡的關頭。",
        context,
        is_opening=True,
    )
    assert natural_timepoint == ()

    location_and_year = audit_persona_response(
        "我是羅伯斯比爾，身在 1793 年的巴黎，眼前局勢正逼近抉擇。",
        context,
        is_opening=True,
    )
    assert location_and_year == ()


def test_persona_audit_rejects_ai_meta_voice():
    context = build_persona_runtime_context(_event(), _persona())
    flags = audit_persona_response(
        "作為 AI，我將扮演羅伯斯比爾；此刻法國大革命正在發生。",
        context,
        is_opening=True,
    )

    assert "persona_out_of_character_meta_voice" in flags


def test_persona_audit_rejects_modern_teacher_redirect_but_accepts_in_character_boundary():
    context = build_persona_runtime_context(_event(), _persona())

    teacher_redirect = audit_persona_response(
        "我不清楚 Python。請回到我們正在談論的事情上，想想看題目的答案。",
        context,
        is_opening=False,
    )
    in_character_redirect = audit_persona_response(
        "我不識得你所說的 Python。此刻共和國的存亡已逼近眼前；公民，你若願意，便談談國民公會的爭論。",
        context,
        is_opening=False,
    )

    assert "persona_modern_tutor_register" in teacher_redirect
    assert in_character_redirect == ()


def test_persona_audit_rejects_observed_classroom_ebl_wording():
    context = build_persona_runtime_context(_event(), _persona())

    observed_phrasings = (
        "你已經指出代表人數的問題，請重新檢視原本的判斷，並改寫原先的答案。",
        "請重新選定一個選項，再用自己的話說明理由。",
        "你這次已經看出資料不同，現在請把原來的選項改一次。",
        "請回頭檢查你自己的兩句話。",
    )

    for response_text in observed_phrasings:
        flags = audit_persona_response(response_text, context, is_opening=False)
        assert "persona_modern_tutor_register" in flags


def test_persona_audit_allows_natural_subject_omission_after_opening():
    context = build_persona_runtime_context(_event(), _persona())

    flags = audit_persona_response(
        "若只歸因於糧價，便忽略了國民公會內外同時逼近的壓力。",
        context,
        is_opening=False,
    )

    assert flags == ()


def test_persona_audit_still_requires_first_person_viewpoint_on_opening():
    context = build_persona_runtime_context(_event(), _persona())

    flags = audit_persona_response(
        "羅伯斯比爾此刻正在國民公會面對共和國的危機。",
        context,
        is_opening=True,
    )

    assert "persona_first_person_missing" in flags


def test_persona_audit_rejects_explicit_knowledge_after_the_scene_cutoff():
    context = build_persona_runtime_context(_event(), _persona())

    violation = audit_persona_response(
        "我知道 1799 年拿破崙將發動霧月政變。",
        context,
        is_opening=False,
    )
    uncertainty = audit_persona_response(
        "1799 年仍是未來，我無從得知那時將發生什麼。",
        context,
        is_opening=False,
    )

    assert "persona_temporal_boundary_violation" in violation
    assert "persona_temporal_boundary_violation" not in uncertainty


def test_roleplay_opening_requires_exactly_one_active_persona():
    with pytest.raises(
        RuntimeError,
        match="exactly one active historical persona",
    ):
        ConversationOpeningService._select_persona(
            [_persona(), _persona().model_copy(update={"id": "persona-2"})],
            _condition("03"),
        )


class _SequenceOpeningProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.prompts: list[str] = []

    async def generate_greeting(self, **kwargs) -> ChatGenerationResult:
        self.prompts.append(kwargs["prompt"])
        response = self.responses[min(len(self.prompts) - 1, len(self.responses) - 1)]
        return ChatGenerationResult(response=response, interaction_metadata=_standard_metadata())


def test_opening_service_regenerates_a_generic_persona_candidate():
    provider = _SequenceOpeningProvider(
        [
            "羅伯斯比爾是法國大革命的重要人物。",
            "我是羅伯斯比爾。此刻國民公會的局勢正在巴黎收緊，你想先談眼前哪一項衝突？",
        ]
    )
    service = ConversationOpeningService(provider, PromptService())

    opening = asyncio.run(
        service.generate(
            event=_event(),
            personas=[_persona()],
            condition=_condition("03"),
            attempt=_attempt(),
        )
    )

    assert len(provider.prompts) == 2
    assert "[validation_retry]" in provider.prompts[1]
    assert "opening turn" in provider.prompts[1]
    assert "explicit first-person viewpoint" in provider.prompts[1]
    assert "selected in-event moment" in provider.prompts[1]
    assert opening.metadata["generation_retry_count"] == 1
    assert len(opening.metadata["rejected_candidates"]) == 1
    assert opening.generation.response.startswith("我是羅伯斯比爾")
    assert "羅伯斯比爾是法國大革命的重要人物" not in opening.generation.response


def test_opening_service_rejects_internal_condition_leakage():
    provider = _SequenceOpeningProvider(
        [
            "我是羅伯斯比爾。此刻國民公會的局勢正在巴黎升高，這是 03模式，你想談什麼？",
            "我是羅伯斯比爾。此刻國民公會的局勢正在巴黎升高，你想先談哪項衝突？",
        ]
    )
    service = ConversationOpeningService(provider, PromptService())

    opening = asyncio.run(
        service.generate(
            event=_event(),
            personas=[_persona()],
            condition=_condition("03"),
            attempt=_attempt(),
        )
    )

    assert opening.metadata["generation_retry_count"] == 1
    assert opening.metadata["rejected_candidates"][0]["flags"] == ["internal_condition_leak"]
    assert "03模式" not in opening.generation.response


def test_opening_service_never_returns_a_repeatedly_invalid_candidate():
    provider = _SequenceOpeningProvider(["羅伯斯比爾是法國大革命的重要人物。"])
    service = ConversationOpeningService(provider, PromptService())

    with pytest.raises(RuntimeError, match="failed interaction/persona validation"):
        asyncio.run(
            service.generate(
                event=_event(),
                personas=[_persona()],
                condition=_condition("03"),
                attempt=_attempt(),
            )
        )

    assert len(provider.prompts) == 3


def test_opening_retry_keeps_prior_remediation_requirements():
    provider = _SequenceOpeningProvider(
        [
            "羅伯斯比爾是法國大革命的重要人物。",
            "我是羅伯斯比爾。國民公會值得討論。",
            "我是羅伯斯比爾。當此國民公會面臨危機之際，我們必須作出抉擇。",
        ]
    )
    service = ConversationOpeningService(provider, PromptService())

    opening = asyncio.run(
        service.generate(
            event=_event(),
            personas=[_persona()],
            condition=_condition("03"),
            attempt=_attempt(),
        )
    )

    assert opening.metadata["generation_retry_count"] == 2
    assert "opening turn" in provider.prompts[2]
    assert "explicit first-person viewpoint" in provider.prompts[2]
    assert "selected in-event moment" in provider.prompts[2]
