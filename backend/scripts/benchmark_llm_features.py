"""Test one explicitly selected production LLM feature without database writes.

The fixture contains only public, synthetic French Revolution material. Every
accepted response is retained in the benchmark report; rejected responses are
retained by ``llm_generation_audit`` under ``.dev-logs``.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings, get_settings  # noqa: E402
from app.core.experiment_conditions import EXPERIMENT_CONDITION_DEFINITIONS  # noqa: E402
from app.core.interaction_contract import build_interaction_runtime  # noqa: E402
from app.core.task_payload_validator import validate_task_authoring_payload  # noqa: E402
from app.models.domain import (  # noqa: E402
    ChatMessage,
    Event,
    EventTask,
    ExperimentCondition,
    Persona,
    TaskAttempt,
    WikiSource,
)
from app.providers.llm.factory import build_llm_provider  # noqa: E402
from app.services.chat_service import ChatService  # noqa: E402
from app.services.conversation_opening_service import ConversationOpeningService  # noqa: E402
from app.services.prompt_service import PromptModule, PromptService  # noqa: E402


FOLLOW_UP_MESSAGE = (
    "我覺得第三等級既然只是三個等級之一，就應該繼續按等級表決，"
    "這樣才公平。我的理由有問題嗎？"
)
POLICY_METADATA_KEYS = (
    "interaction_mode",
    "dialogue_state",
    "dialogue_move",
    "primary_ebl_move",
    "disclosure_level",
    "target_question_id",
    "completion_status",
    "fidelity_flags",
    "generation_retry_count",
)
FEATURES = ("event_profile", "task", "persona", "judge", "opening", "chat")


@dataclass(frozen=True)
class ModelSpec:
    """One isolated provider/model configuration."""

    key: str
    model: str
    reasoning_effort: str | None
    provider: str


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


def _fixture() -> tuple[Event, Persona, TaskAttempt]:
    event = Event(
        canonical_name="法國大革命",
        description=(
            "1789 年法國在財政危機、特權制度與代表權爭議下爆發革命，"
            "政治秩序在君主制、共和與戰爭壓力間持續重組。"
        ),
        century=18,
        start_year=1789,
        end_year=1799,
        context=(
            "三級會議的表決方式使第三等級質疑按等級投票的代表性。"
            "革命後的共和政府在 1793 年同時面臨對外戰爭與內部政治衝突。"
        ),
    )
    persona = Persona(
        event_id=event.id,
        name="馬克西米連·羅伯斯庇爾",
        english_name="Maximilien Robespierre",
        role="國民公會代表、公共安全委員會成員",
        biography="曾任第三等級代表，革命期間參與國民公會與公共安全委員會。",
        expertise_areas=["第三等級代表權", "國民公會", "共和政治"],
        prompt_profile={
            "speaking_style": "嚴肅、克制、論辯性強，不使用後世教科書式全知旁白",
            "forms_of_address": "公民",
            "social_position": "1793 年的國民公會代表與公共安全委員會成員",
            "relationship_to_event": "曾任第三等級代表，正處於革命共和政府的政治危機中",
            "event_timepoint": "1793 年秋季，共和政府面臨內外危機之際",
            "event_timepoint_year": 1793,
            "event_location": "巴黎",
            "event_vantage_point": "從國民公會與公共安全委員會的政治位置觀察革命",
            "current_stakes": ["共和國的存續", "內外戰爭", "革命正當性"],
            "event_anchor_terms": ["第三等級", "三級會議", "國民公會", "巴黎"],
            "knowledge_cutoff_year": 1793,
            "firsthand_experience_allowed": True,
            "firsthand_experience_scope": ["1789 年三級會議中的第三等級代表經驗", "1793 年巴黎政治處境"],
            "temporal_boundary": "不得知道或暗示 1793 年之後的事件結果",
            "geographic_boundary": "僅能聲稱合理接觸過的法國政治資訊",
            "knowledge_boundary": "只使用其截至 1793 年依身份可合理知道的資訊",
            "stance": "保留其共和與雅各賓政治立場，但不得將立場宣稱為客觀事實",
            "source_policy": ["不捏造逐字引文", "不把後世評價說成親身記憶"],
            "forbidden_claims": ["1793 年後的知識", "未有資料支持的親身經歷", "全知歷史旁白"],
        },
    )
    attempt = TaskAttempt(
        session_id="benchmark-session",
        task_id="benchmark-task",
        event_id=event.id,
        status="submitted",
        judgement_payload={
            "result": "incorrect",
            "question_results": [
                {
                    "question_id": "q01",
                    "prompt": "第三等級在三級會議中要求採用哪一種表決方式？",
                    "source_text": "第三等級反對每一等級各一票，要求代表權反映其人口比例。",
                    "learner_answer": "按等級",
                    "expected_answer": "按人數",
                    "correctness": "incorrect",
                    "error_code": "representation_confusion",
                    "historical_concept": "historical_perspective",
                    "reasoning_process": "compare_claims_with_contextual_evidence",
                    "evidence_ids": ["task-q01-source"],
                }
            ],
        },
    )
    return event, persona, attempt


def _source_fixture(event_id: str) -> list[WikiSource]:
    """提供所有建材功能共用且可人工核對的公開來源摘要。"""

    return [
        WikiSource(
            event_id=event_id,
            language="zh",
            title="法國大革命",
            page_url="https://zh.wikipedia.org/wiki/%E6%B3%95%E5%9C%8B%E5%A4%A7%E9%9D%A9%E5%91%BD",
            summary=(
                "法國大革命始於 1789 年。三級會議的代表與表決爭議、財政危機及特權制度，"
                "共同構成革命初期的重要背景。"
            ),
            fetch_mode="full",
            sections=[
                {
                    "title": "三級會議",
                    "content": "第三等級反對每個等級各一票，主張按代表人數表決。",
                }
            ],
        ),
        WikiSource(
            event_id=event_id,
            language="en",
            title="French Revolution",
            page_url="https://en.wikipedia.org/wiki/French_Revolution",
            summary=(
                "The French Revolution began in 1789 amid fiscal crisis, disputes over privilege, "
                "and conflict about representation in the Estates-General."
            ),
            fetch_mode="full",
        ),
    ]


def _judge_fixture(event: Event) -> tuple[EventTask, dict[str, Any]]:
    """建立一題可人工核對的真實 Error-Elicitation judge 案例。"""

    task = EventTask(
        event_id=event.id,
        title="三級會議的代表權爭議",
        error_elicitation_task_full_text=(
            "1789 年，三級會議沿用每個等級各一票的方式；第三等級雖代表多數人口，"
            "仍可能被另外兩個等級以二比一否決。"
            "\n\n依據本文，按等級投票能公平反映各等級所代表的人口比例。 {{blank:q01}}"
        ),
        evaluation_payload={
            "contract_version": "error_elicitation_v1",
            "materials": [
                {
                    "id": "m01",
                    "title": "三級會議表決方式摘要",
                    "text": "每個等級各有一票；第三等級要求改採按人數表決。",
                    "source_url": "https://www.britannica.com/event/French-Revolution",
                    "attribution": "研究測試用史實摘要",
                }
            ],
            "questions": [
                {
                    "id": "q01",
                    "type": "true_false",
                    "required": True,
                    "correct_answer": False,
                    "reasoning_criteria": (
                        "理由需辨認每個等級各一票會忽略人口與代表數差異；"
                        "可接受其他能由本文支持的等價說明。"
                    ),
                    "source_text": "第三等級雖代表多數人口，仍可能被二比一否決。",
                }
            ],
        },
    )
    response = {
        "answers": [
            {
                "question_id": "q01",
                "value": True,
                "rationale": "三個等級都只有一票，所以每一方的權利完全相同，這就是公平。",
            }
        ]
    }
    return task, response


def _available_specs(settings: Settings) -> tuple[list[ModelSpec], list[dict[str, str]]]:
    specs: list[ModelSpec] = []
    skipped: list[dict[str, str]] = []
    if settings.gemini_api_key:
        specs.extend(
            [
                ModelSpec(
                    "gemini_2_5_flash_none",
                    "gemini/gemini-2.5-flash",
                    "none",
                    "gemini",
                ),
                ModelSpec(
                    "gemini_3_5_flash_lite_minimal",
                    "gemini/gemini-3.5-flash-lite",
                    "minimal",
                    "gemini",
                ),
                ModelSpec(
                    "gemini_3_6_flash_low",
                    "gemini/gemini-3.6-flash",
                    "low",
                    "gemini",
                ),
            ]
        )
    else:
        skipped.append({"provider": "gemini", "reason": "GEMINI_API_KEY is not configured"})
    if settings.cohere_api_key:
        specs.append(
            ModelSpec(
                "cohere_command_a_plus",
                settings.cohere_llm_model,
                None,
                "cohere",
            )
        )
    else:
        skipped.append({"provider": "cohere", "reason": "COHERE_API_KEY is not configured"})
    if settings.nvidia_api_key:
        specs.append(
            ModelSpec(
                "nvidia_nemotron_nano",
                settings.nvidia_llm_model,
                None,
                "nvidia",
            )
        )
    else:
        skipped.append({"provider": "nvidia", "reason": "NVIDIA_API_KEY is not configured"})
    if settings.openai_api_key:
        specs.extend(
            [
                ModelSpec("openai_gpt_5_6_luna", "gpt-5.6-luna", "low", "openai"),
                ModelSpec("openai_gpt_5_6_terra", "gpt-5.6-terra", "low", "openai"),
            ]
        )
    else:
        skipped.append({"provider": "openai", "reason": "OPENAI_API_KEY is not configured"})
    return specs, skipped


def _isolated_settings(base: Settings, spec: ModelSpec) -> Settings:
    return base.model_copy(
        update={
            "llm_model": spec.model,
            "llm_fallback_models": [],
            "llm_api_base": None,
            "llm_api_key": None,
            "llm_max_output_tokens": 4096,
            "llm_timeout_seconds": 60.0,
            "gemini_reasoning_effort": spec.reasoning_effort or base.gemini_reasoning_effort,
            "openai_reasoning_effort": spec.reasoning_effort or base.openai_reasoning_effort,
            "gemini_api_key": base.gemini_api_key if spec.provider == "gemini" else None,
            "openai_api_key": base.openai_api_key if spec.provider == "openai" else None,
            "cohere_api_key": base.cohere_api_key if spec.provider == "cohere" else None,
            "nvidia_api_key": base.nvidia_api_key if spec.provider == "nvidia" else None,
            "nvidia_enable_thinking": False,
        }
    )


def _metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: metadata.get(key) for key in POLICY_METADATA_KEYS}


def _llm_call(metadata: dict[str, Any]) -> dict[str, Any]:
    value = metadata.get("llm_call", {})
    return value if isinstance(value, dict) else {}


def _module_hashes(modules: tuple[PromptModule, ...] | list[PromptModule]) -> dict[str, str]:
    return {
        module.name: hashlib.sha256(module.content.encode("utf-8")).hexdigest()
        for module in modules
    }


def _quality_flags(response: str, condition: ExperimentCondition, *, opening: bool) -> list[str]:
    compact = response.replace(" ", "").lower()
    flags: list[str] = []
    if not response.strip():
        flags.append("empty_response")
    if len(response) > 700:
        flags.append("overlong_response")
    if any(marker in compact for marker in ("01模式", "02模式", "03模式", "04模式", "prompt", "實驗條件")):
        flags.append("internal_policy_leak")
    if condition.roleplay_enabled:
        if opening and "羅伯斯庇爾" not in response:
            flags.append("persona_identity_not_explicit")
        if "我" not in response:
            flags.append("persona_first_person_missing")
    elif "羅伯斯庇爾" in response or "我是公共安全委員會" in response:
        flags.append("generic_mode_persona_leak")
    if condition.ebl_enabled and "按人數" in response:
        flags.append("early_answer_exposure")
    return flags


def _safe_error(provider: Any, exc: Exception) -> str:
    runner = getattr(provider, "runner", None)
    redactor = getattr(runner, "_safe_error_message", None)
    return redactor(exc) if callable(redactor) else f"{type(exc).__name__}: {exc}"


def _error_llm_call(exc: Exception) -> dict[str, Any]:
    metadata = getattr(exc, "metadata", None)
    return metadata.as_dict() if hasattr(metadata, "as_dict") else {}


async def _run_opening(
    provider: Any,
    prompt_service: PromptService,
    condition: ExperimentCondition,
) -> dict[str, Any]:
    event, persona, attempt = _fixture()
    personas = [persona] if condition.roleplay_enabled else []
    opening_service = ConversationOpeningService(provider, prompt_service)
    llm_calls: list[dict[str, Any]] = []
    original_generate = provider.generate_greeting

    async def tracked_generate(**kwargs):
        try:
            generation = await original_generate(**kwargs)
        except Exception as exc:
            failed_call = _error_llm_call(exc)
            if failed_call:
                llm_calls.append(failed_call)
            raise
        call = _llm_call(generation.llm_metadata)
        if call:
            llm_calls.append(call)
        return generation

    provider.generate_greeting = tracked_generate
    started = time.perf_counter()
    try:
        opening = await opening_service.generate(
            event=event,
            personas=personas,
            condition=condition,
            attempt=attempt,
        )
    except Exception as exc:
        return {
            "ok": False,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "error_type": type(exc).__name__,
            "error": _safe_error(provider, exc),
            "llm_call": _error_llm_call(exc),
            "llm_calls": llm_calls,
            "rejected_candidates": getattr(exc, "rejected_candidates", []),
        }

    return {
        "ok": True,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "response": opening.generation.response,
        "metadata": _metadata(opening.metadata),
        "llm_call": _llm_call(opening.generation.llm_metadata),
        "llm_calls": llm_calls,
        "quality_flags": _quality_flags(opening.generation.response, condition, opening=True),
        "module_hashes": _module_hashes(opening.modules),
    }


async def _run_chat(
    provider: Any,
    prompt_service: PromptService,
    condition: ExperimentCondition,
) -> dict[str, Any]:
    """只測一輪 chat；使用本地固定開場，避免偷偷多付一次 opening 費用。"""

    event, persona, attempt = _fixture()
    selected = persona if condition.roleplay_enabled else None
    opening_text = (
        "我是羅伯斯庇爾。巴黎的政治爭論正在加劇，你想先談三級會議的哪項爭議？"
        if selected
        else "我們來談法國大革命。你想先從三級會議的哪項爭議開始？"
    )
    history = [
        ChatMessage(
            conversation_id="benchmark-conversation",
            persona_id=selected.id if selected else None,
            speaker_type="persona" if selected else "assistant",
            speaker_name=selected.name if selected else "AI Assistant",
            sequence_index=0,
            content=opening_text,
            metadata={"dialogue_state": "NOTICE_ERROR" if condition.ebl_enabled else "STANDARD_CHAT"},
        )
    ]
    runtime = build_interaction_runtime(condition, attempt, history)
    modules = prompt_service.assemble_chat_modules(
        event=event,
        persona=selected,
        condition=condition,
        task_attempt=attempt,
        user_message=FOLLOW_UP_MESSAGE,
        rag_sources=[],
        conversation_history=history,
        interaction_runtime=runtime,
    )
    prompt = prompt_service.render_modules(modules)
    chat_service = ChatService(None, provider, prompt_service, None)  # type: ignore[arg-type]
    llm_calls: list[dict[str, Any]] = []
    original_generate = provider.generate_chat_response

    async def tracked_generate(**kwargs):
        try:
            generation = await original_generate(**kwargs)
        except Exception as exc:
            failed_call = _error_llm_call(exc)
            if failed_call:
                llm_calls.append(failed_call)
            raise
        call = _llm_call(generation.llm_metadata)
        if call:
            llm_calls.append(call)
        return generation

    provider.generate_chat_response = tracked_generate
    started = time.perf_counter()
    try:
        generation, metadata, _effective_prompt = await chat_service.generate_validated_response(
            event=event,
            selected=selected,
            condition=condition,
            task_attempt=attempt,
            user_message=FOLLOW_UP_MESSAGE,
            base_prompt=prompt,
            rag_sources=[],
            interaction_runtime=runtime,
        )
    except Exception as exc:
        return {
            "ok": False,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "error_type": type(exc).__name__,
            "error": _safe_error(provider, exc),
            "llm_call": _error_llm_call(exc),
            "llm_calls": llm_calls,
        }

    return {
        "ok": True,
        "provider": str(generation.llm_metadata.get("provider", "unknown")),
        "model": str(generation.llm_metadata.get("model", "unknown")),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "learner_message": FOLLOW_UP_MESSAGE,
        "response": generation.response,
        "metadata": _metadata(metadata),
        "llm_call": _llm_call(generation.llm_metadata),
        "llm_calls": llm_calls,
        "quality_flags": _quality_flags(generation.response, condition, opening=False),
        "module_hashes": _module_hashes(modules),
    }


async def _run_material_feature(provider: Any, feature: str) -> dict[str, Any]:
    event, _persona, _attempt = _fixture()
    sources = _source_fixture(event.id)
    started = time.perf_counter()
    try:
        if feature == "event_profile":
            result = await provider.generate_event_profile(event.canonical_name, sources)
            source_summary = result.get("source_summary", {})
            flags = [
                name
                for name in ("canonical_name", "description", "context")
                if not str(result.get(name) or "").strip()
            ]
            llm_call = _llm_call(source_summary)
            payload: Any = result
        elif feature == "task":
            task = await provider.generate_task(event, sources)
            flags = [
                f"task_contract:{issue['code']}"
                for issue in validate_task_authoring_payload(
                    task.error_elicitation_task_full_text,
                    task.evaluation_payload,
                )
            ]
            llm_call = _llm_call(task.evaluation_payload)
            payload = task.model_dump()
        elif feature == "persona":
            personas = await provider.generate_personas(event, sources)
            flags = [] if len(personas) == 1 else ["persona_count_must_equal_one"]
            if personas and personas[0].prompt_profile.get("deliberate_error_enabled") is not False:
                flags.append("deliberate_error_must_be_disabled")
            llm_call = _llm_call(personas[0].prompt_profile) if personas else {}
            payload = [persona.model_dump() for persona in personas]
        else:
            raise ValueError(f"Unsupported material feature: {feature}")
    except Exception as exc:
        return {
            "ok": False,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "error_type": type(exc).__name__,
            "error": _safe_error(provider, exc),
            "llm_call": _error_llm_call(exc),
        }
    return {
        "ok": True,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "quality_flags": flags,
        "payload": payload,
        "llm_call": llm_call,
    }


async def _run_judge(provider: Any) -> dict[str, Any]:
    event, _persona, _attempt = _fixture()
    task, response = _judge_fixture(event)
    started = time.perf_counter()
    try:
        result = await provider.judge_task_attempt(event, task, response)
    except Exception as exc:
        return {
            "ok": False,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "error_type": type(exc).__name__,
            "error": _safe_error(provider, exc),
            "llm_call": _error_llm_call(exc),
        }
    question_results = result.get("question_results") or []
    first = question_results[0] if question_results else {}
    flags: list[str] = []
    if result.get("judge_contract_version") != "error_elicitation_judge_v3":
        flags.append("wrong_contract_version")
    if len(question_results) != 1 or first.get("question_id") != "q01":
        flags.append("question_coverage_error")
    if first.get("reasoning_correct") is not False:
        flags.append("incorrect_reasoning_not_detected")
    if not str(first.get("reasoning_feedback") or "").strip():
        flags.append("missing_reasoning_feedback")
    return {
        "ok": True,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "quality_flags": flags,
        "result": result,
        "llm_call": _llm_call(result),
    }


def _usage_summary(result: dict[str, Any]) -> dict[str, Any]:
    calls = result.get("llm_calls") or [result.get("llm_call", {})]
    calls = [call for call in calls if isinstance(call, dict) and call]
    with_tokens = [call for call in calls if call.get("total_tokens") is not None]
    with_cost = [call for call in calls if call.get("estimated_cost_usd") is not None]

    def total(field: str) -> int:
        return sum(int(call.get(field) or 0) for call in with_tokens)

    return {
        "logical_generation_attempts": len(calls),
        "llm_calls_with_usage": len(with_tokens),
        "prompt_tokens": total("prompt_tokens"),
        "cached_prompt_tokens": total("cached_prompt_tokens"),
        "completion_tokens": total("completion_tokens"),
        "reasoning_tokens": total("reasoning_tokens"),
        "total_tokens": total("total_tokens"),
        "estimated_cost_usd": (
            round(sum(float(call["estimated_cost_usd"]) for call in with_cost), 8)
            if calls and len(with_cost) == len(calls)
            else None
        ),
        "cost_complete": bool(calls) and len(with_cost) == len(calls),
    }


async def _run_feature(
    base: Settings,
    spec: ModelSpec,
    feature: str,
    condition_code: str | None,
) -> dict[str, Any]:
    settings = _isolated_settings(base, spec)
    provider = build_llm_provider(settings)
    prompt_service = PromptService()
    started = time.perf_counter()
    if feature in {"event_profile", "task", "persona"}:
        result = await _run_material_feature(provider, feature)
    elif feature == "judge":
        result = await _run_judge(provider)
    elif feature == "opening" and condition_code:
        result = await _run_opening(provider, prompt_service, _condition(condition_code))
    elif feature == "chat" and condition_code:
        result = await _run_chat(provider, prompt_service, _condition(condition_code))
    else:
        raise ValueError(f"Feature {feature} requires a condition code")
    return {
        "key": spec.key,
        "configured_provider": spec.provider,
        "configured_model": spec.model,
        "reasoning_effort": spec.reasoning_effort,
        "feature": feature,
        "condition": condition_code,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "result": result,
        "usage": _usage_summary(result),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run exactly one paid LLM feature and retain its output, usage, and cost.",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="One explicit model key, for example openai_gpt_5_6_luna.",
    )
    parser.add_argument(
        "--feature",
        required=True,
        choices=FEATURES,
        help="Exactly one production LLM function to test.",
    )
    parser.add_argument(
        "--condition",
        choices=("01", "02", "03", "04"),
        help="Required only for opening or chat.",
    )
    parser.add_argument(
        "--execute-paid",
        action="store_true",
        help="Actually call the provider. Without this flag the command only prints the call plan.",
    )
    args = parser.parse_args()
    if args.feature in {"opening", "chat"} and not args.condition:
        parser.error("--condition is required for opening and chat")
    if args.feature not in {"opening", "chat"} and args.condition:
        parser.error("--condition is only valid for opening and chat")

    base = get_settings()
    specs, skipped = _available_specs(base)
    spec = next((item for item in specs if item.key == args.model), None)
    if spec is None:
        available = ", ".join(item.key for item in specs) or "none"
        parser.error(f"Model key is unavailable. Configured choices: {available}")

    max_http_calls = 12 if args.feature in {"opening", "chat"} else 4
    plan = {
        "model": spec.key,
        "feature": args.feature,
        "condition": args.condition,
        "database_writes": False,
        "planned_logical_features": 1,
        "maximum_provider_http_calls_if_all_repairs_and_retries_are_used": max_http_calls,
        "will_execute_paid_call": args.execute_paid,
    }
    print(json.dumps({"call_plan": plan}, ensure_ascii=False, indent=2), flush=True)
    if not args.execute_paid:
        print("No provider call was made. Add --execute-paid only after local tests pass.")
        return

    print(f"[benchmark] {spec.key}:{args.feature}", flush=True)
    result = await _run_feature(base, spec, args.feature, args.condition)

    output_dir = PROJECT_ROOT / ".dev-logs" / "llm-benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    condition_suffix = f"-{args.condition}" if args.condition else ""
    output_path = output_dir / f"llm-{args.feature}{condition_suffix}-{timestamp}.json"
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fixture_scope": "public_synthetic_french_revolution",
        "database_writes": False,
        "pricing_source": "https://developers.openai.com/api/docs/models",
        "pricing_note": "Per-call estimated cost is calculated by LiteLLM from provider usage metadata.",
        "call_plan": plan,
        "skipped_providers": skipped,
        "result": result,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                "model": result["key"],
                "feature": result["feature"],
                "condition": result["condition"],
                "ok": result["result"].get("ok"),
                "quality_flags": result["result"].get("quality_flags", []),
                "usage": result["usage"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
