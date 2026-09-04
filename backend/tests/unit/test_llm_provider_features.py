from __future__ import annotations

import asyncio

import pytest

from app.models.domain import Event, EventTask, ExperimentCondition, TaskAttempt, WikiSource
from app.providers.llm.json_runner import LLMCallMetadata, LLMRunResult
from app.providers.llm.litellm_provider import LiteLLMProvider, _validate_generated_task_sources
from app.providers.llm.structured import (
    ChatOutputPayload,
    EventProfilePayload,
    GeneratedTaskPayload,
    PersonaListPayload,
)
from app.core.error_elicitation_contract import ErrorElicitationJudgementPayload
from app.core.config import Settings


def _metadata(task_name: str) -> LLMCallMetadata:
    return LLMCallMetadata(
        correlation_id=f"call-{task_name}",
        task_name=task_name,
        provider="openai",
        model="gpt-5.6-luna",
        status="completed",
        latency_ms=10,
        attempt_count=1,
        transient_retry_count=0,
        schema_repair_count=0,
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        estimated_cost_usd=0.001,
    )


def _generated_task_payload() -> GeneratedTaskPayload:
    questions = [
        {
            "id": "q01",
            "type": "multiple_choice",
            "required": True,
            "options": [
                {"id": "a", "label": "按人數", "value": "按人數"},
                {"id": "b", "label": "按等級", "value": "按等級"},
            ],
            "correct_answer": "按人數",
            "reasoning_criteria": "理由需辨認代表人數與每個等級一票的差異。",
        },
        {
            "id": "q02",
            "type": "true_false",
            "required": True,
            "correct_answer": False,
            "reasoning_criteria": "理由需指出單一原因不足以解釋革命。",
        },
        {
            "id": "q03",
            "type": "cloze",
            "required": True,
            "correct_answer": ["1789", "一七八九年"],
            "reasoning_criteria": "理由需把年份連回三級會議的時間脈絡。",
        },
    ]
    return GeneratedTaskPayload(
        title="法國大革命 Error-Elicitation Task",
        error_elicitation_task_full_text=(
            "閱讀材料後判斷三級會議的代表權爭議。 {{blank:q01}}\n\n"
            "法國大革命只有一個原因。 {{blank:q02}}\n\n"
            "三級會議召開於哪一年？ {{blank:q03}}"
        ),
        evaluation_payload={
            "contract_version": "error_elicitation_v1",
            "materials": [],
            "questions": questions,
            "all_correct_fallback": {
                "id": "fallback-01",
                "incorrect_claim": "革命只由一項因素造成。",
                "correct_interpretation": "革命由多項結構與事件因素共同形成。",
                "evidence_ids": [],
            },
        },
    )


def test_all_six_provider_features_use_their_structured_contract_and_keep_usage() -> None:
    """零費用逐項確認六個 production adapter，不以 API 全流程測試代替。"""

    provider = LiteLLMProvider(Settings(llm_model="gpt-5.6-luna", openai_api_key="test-key"))
    calls: list[tuple[str, type]] = []

    async def fake_run_json(*, schema, task_name, **_kwargs):
        calls.append((task_name, schema))
        payloads = {
            "generate_event_profile": EventProfilePayload(
                canonical_name="法國大革命",
                description="1789 年開始的政治與社會變革。",
                century=18,
                start_year=1789,
                end_year=1799,
                context="財政、特權與代表權爭議共同構成事件背景。",
            ),
            "generate_task": _generated_task_payload(),
            "judge_task_attempt": ErrorElicitationJudgementPayload(
                judge_contract_version="error_elicitation_judge_v2",
                question_results=[
                    {
                        "question_id": "q01",
                        "reasoning_correct": False,
                        "reasoning_issue_types": ["reasoning_error"],
                        "reasoning_feedback": "理由忽略了人口與代表數差異。",
                        "historical_thinking_tags": ["evidence"],
                    }
                ],
            ),
            "generate_personas": PersonaListPayload(
                personas=[
                    {
                        "name": "馬克西米連·羅伯斯庇爾",
                        "role": "國民公會代表",
                        "prompt_profile": {
                            "speaking_style": "嚴肅、克制、具論辯性",
                            "social_position": "1793 年國民公會代表",
                            "event_timepoint": "1793 年秋季",
                            "event_timepoint_year": 1793,
                            "event_location": "巴黎",
                            "knowledge_cutoff_year": 1793,
                            "deliberate_error_enabled": False,
                        },
                    }
                ]
            ),
            "generate_greeting": ChatOutputPayload(
                response="我們來談法國大革命。你想先從哪個爭議開始？",
                dialogue_state="STANDARD_CHAT",
                dialogue_move="natural_response",
                learner_progress="not_assessed",
                learner_revision_status="not_applicable",
                completion_status="continue",
            ),
            "generate_chat_response": ChatOutputPayload(
                response="按等級表決未能反映各等級代表人數的差異。",
                dialogue_state="STANDARD_CHAT",
                dialogue_move="natural_response",
                learner_progress="not_assessed",
                learner_revision_status="not_applicable",
                completion_status="continue",
            ),
        }
        return LLMRunResult(payload=payloads[task_name], metadata=_metadata(task_name))

    provider.runner.run_json = fake_run_json
    event = Event(canonical_name="法國大革命")
    source = WikiSource(
        event_id=event.id,
        language="zh",
        title="法國大革命",
        page_url="https://zh.wikipedia.org/wiki/test",
        summary="1789 年法國爆發革命。",
    )
    condition = ExperimentCondition(
        condition_key="no_ebl_no_roleplay",
        label="Baseline",
        ebl_enabled=False,
        roleplay_enabled=False,
    )
    task = EventTask(
        event_id=event.id,
        title="判斷題",
        error_elicitation_task_full_text="判斷代表權主張。 {{blank:q01}}",
        evaluation_payload={
            "contract_version": "error_elicitation_v1",
            "questions": [
                {
                    "id": "q01",
                    "type": "true_false",
                    "required": True,
                    "correct_answer": False,
                    "reasoning_criteria": "理由需辨認代表權差異。",
                }
            ],
        },
    )
    attempt = TaskAttempt(
        session_id="session-1",
        task_id=task.id,
        event_id=event.id,
        status="submitted",
    )

    async def run_features():
        profile = await provider.generate_event_profile(event.canonical_name, [source])
        generated_task = await provider.generate_task(event, [source])
        judgement = await provider.judge_task_attempt(
            event,
            task,
            {
                "contract_version": "error_elicitation_v1",
                "answers": [{"question_id": "q01", "value": True, "rationale": "每級一票很公平。"}],
            },
        )
        personas = await provider.generate_personas(event, [source])
        greeting = await provider.generate_greeting(event, [], condition, attempt, "prompt")
        chat = await provider.generate_chat_response(event, None, condition, attempt, "問題", "prompt", [])
        return profile, generated_task, judgement, personas, greeting, chat

    profile, generated_task, judgement, personas, greeting, chat = asyncio.run(run_features())

    assert [name for name, _schema in calls] == [
        "generate_event_profile",
        "generate_task",
        "judge_task_attempt",
        "generate_personas",
        "generate_greeting",
        "generate_chat_response",
    ]
    assert profile["source_summary"]["llm_call"]["total_tokens"] == 120
    assert generated_task.evaluation_payload["llm_call"]["total_tokens"] == 120
    assert judgement["llm_call"]["total_tokens"] == 120
    assert personas[0].prompt_profile["llm_call"]["total_tokens"] == 120
    assert greeting.llm_metadata["llm_call"]["total_tokens"] == 120
    assert chat.llm_metadata["llm_call"]["total_tokens"] == 120


def test_generated_persona_rejects_unknown_profile_fields_inside_runner_schema() -> None:
    """人物設定錯誤應觸發 structured repair，不應拖到建立 Persona 才失敗。"""

    from pydantic import ValidationError

    try:
        PersonaListPayload.model_validate(
            {"personas": [{"name": "測試人物", "prompt_profile": {"unexpected": "value"}}]}
        )
    except ValidationError:
        return
    raise AssertionError("Unknown persona profile fields must be rejected")


def test_generated_task_sources_must_match_supplied_urls_exactly() -> None:
    payload = GeneratedTaskPayload.model_validate(
        {
            "title": "測試 Task",
            "story_text": "",
            "error_elicitation_task_full_text": "題目 {{blank:q01}}",
            "evaluation_payload": {
                "contract_version": "error_elicitation_v1",
                "materials": [
                    {
                        "id": "m01",
                        "title": "來源",
                        "text": "內容",
                        "source_url": "https://example.com/broken",
                    }
                ],
                "questions": [
                    {
                        "id": "q01",
                        "type": "true_false",
                        "required": True,
                        "correct_answer": True,
                        "reasoning_criteria": "理由需符合材料。",
                    }
                ],
            },
        }
    )

    with pytest.raises(ValueError, match=r"materials\[0\]\.source_url"):
        _validate_generated_task_sources(
            payload,
            allowed_source_urls={"https://example.com/source"},
        )
