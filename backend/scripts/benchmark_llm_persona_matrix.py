"""Benchmark the production persona/interaction prompt pipeline without database writes.

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
from app.models.domain import (  # noqa: E402
    ChatMessage,
    Event,
    ExperimentCondition,
    Persona,
    TaskAttempt,
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
    "primary_historical_thinking_move",
    "disclosure_level",
    "target_question_id",
    "historical_thinking_focus",
    "completion_status",
    "fidelity_flags",
    "generation_retry_count",
)
POLICY_MODULES = (
    "general_prompt",
    "independent_2_prompt",
    "event_context",
    "learner_task",
    "interaction_runtime",
    "source_context",
    "runtime_policy",
)


@dataclass(frozen=True)
class ModelSpec:
    """One isolated provider/model configuration."""

    key: str
    model: str
    reasoning_effort: str | None
    provider: str
    cooldown_seconds: float = 3.0


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
                    13.0,
                ),
                ModelSpec(
                    "gemini_3_5_flash_lite_minimal",
                    "gemini/gemini-3.5-flash-lite",
                    "minimal",
                    "gemini",
                    4.2,
                ),
                ModelSpec(
                    "gemini_3_6_flash_low",
                    "gemini/gemini-3.6-flash",
                    "low",
                    "gemini",
                    13.0,
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
                6.0,
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
                1.0,
            )
        )
    else:
        skipped.append({"provider": "nvidia", "reason": "NVIDIA_API_KEY is not configured"})
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
            "gemini_api_key": base.gemini_api_key if spec.provider == "gemini" else None,
            "cohere_api_key": base.cohere_api_key if spec.provider == "cohere" else None,
            "nvidia_api_key": base.nvidia_api_key if spec.provider == "nvidia" else None,
            "nvidia_enable_thinking": False,
        }
    )


def _metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: metadata.get(key) for key in POLICY_METADATA_KEYS}


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


async def _run_condition(
    provider: Any,
    prompt_service: PromptService,
    condition: ExperimentCondition,
    cooldown_seconds: float,
) -> dict[str, Any]:
    event, persona, attempt = _fixture()
    personas = [persona] if condition.roleplay_enabled else []
    opening_service = ConversationOpeningService(provider, prompt_service)
    started = time.perf_counter()
    try:
        opening = await opening_service.generate(
            event=event,
            personas=personas,
            condition=condition,
            attempt=attempt,
        )
        opening_elapsed = round(time.perf_counter() - started, 3)
    except Exception as exc:
        return {
            "ok": False,
            "failed_stage": "opening",
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "error_type": type(exc).__name__,
            "error": _safe_error(provider, exc),
            "rejected_candidates": getattr(exc, "rejected_candidates", []),
        }

    history = [
        ChatMessage(
            conversation_id="benchmark-conversation",
            persona_id=opening.persona.id if opening.persona else None,
            speaker_type="persona" if opening.persona else "assistant",
            speaker_name=opening.persona.name if opening.persona else "AI Assistant",
            sequence_index=0,
            content=opening.generation.response,
            metadata=opening.metadata,
        )
    ]
    # Free-tier model quotas are commonly enforced per minute. Pace the
    # benchmark so quota errors are not misclassified as model failures.
    await asyncio.sleep(cooldown_seconds)
    runtime = build_interaction_runtime(condition, attempt, history)
    modules = prompt_service.assemble_chat_modules(
        event=event,
        persona=opening.persona,
        condition=condition,
        task_attempt=attempt,
        user_message=FOLLOW_UP_MESSAGE,
        rag_sources=[],
        conversation_history=history,
        interaction_runtime=runtime,
    )
    prompt = prompt_service.render_modules(modules)
    chat_service = ChatService(None, provider, prompt_service, None)  # type: ignore[arg-type]
    follow_up_started = time.perf_counter()
    try:
        generation, metadata = await chat_service.generate_validated_response(
            event=event,
            selected=opening.persona,
            condition=condition,
            task_attempt=attempt,
            user_message=FOLLOW_UP_MESSAGE,
            base_prompt=prompt,
            rag_sources=[],
            interaction_runtime=runtime,
        )
        follow_up_elapsed = round(time.perf_counter() - follow_up_started, 3)
    except Exception as exc:
        return {
            "ok": False,
            "failed_stage": "follow_up",
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "opening": {
                "elapsed_seconds": opening_elapsed,
                "response": opening.generation.response,
                "metadata": _metadata(opening.metadata),
                "module_hashes": _module_hashes(opening.modules),
            },
            "error_type": type(exc).__name__,
            "error": _safe_error(provider, exc),
        }

    return {
        "ok": True,
        "provider": str(generation.llm_metadata.get("provider", "unknown")),
        "model": str(generation.llm_metadata.get("model", "unknown")),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "opening": {
            "elapsed_seconds": opening_elapsed,
            "response": opening.generation.response,
            "metadata": _metadata(opening.metadata),
            "quality_flags": _quality_flags(opening.generation.response, condition, opening=True),
            "module_hashes": _module_hashes(opening.modules),
        },
        "follow_up": {
            "elapsed_seconds": follow_up_elapsed,
            "learner_message": FOLLOW_UP_MESSAGE,
            "response": generation.response,
            "metadata": _metadata(metadata),
            "quality_flags": _quality_flags(generation.response, condition, opening=False),
            "module_hashes": _module_hashes(modules),
        },
    }


def _matrix_invariants(conditions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    two = conditions.get("02", {})
    four = conditions.get("04", {})
    if not two.get("ok") or not four.get("ok"):
        return {"checked": False, "reason": "condition 02 or 04 did not complete"}

    opening_hashes_02 = two["opening"]["module_hashes"]
    opening_hashes_04 = four["opening"]["module_hashes"]
    follow_hashes_02 = two["follow_up"]["module_hashes"]
    follow_hashes_04 = four["follow_up"]["module_hashes"]
    return {
        "checked": True,
        "shared_opening_policy_modules": {
            name: opening_hashes_02.get(name) == opening_hashes_04.get(name)
            for name in POLICY_MODULES
        },
        "shared_follow_up_policy_modules": {
            name: follow_hashes_02.get(name) == follow_hashes_04.get(name)
            for name in POLICY_MODULES
        },
        "opening_pedagogical_metadata_equal": (
            two["opening"]["metadata"] | {"generation_retry_count": None}
        ) == (four["opening"]["metadata"] | {"generation_retry_count": None}),
        "follow_up_pedagogical_metadata": {
            "02": two["follow_up"]["metadata"],
            "04": four["follow_up"]["metadata"],
        },
    }


async def _run_spec(base: Settings, spec: ModelSpec, condition_codes: tuple[str, ...]) -> dict[str, Any]:
    settings = _isolated_settings(base, spec)
    provider = build_llm_provider(settings)
    prompt_service = PromptService()
    conditions: dict[str, dict[str, Any]] = {}
    started = time.perf_counter()
    for index, code in enumerate(condition_codes):
        conditions[code] = await _run_condition(
            provider,
            prompt_service,
            _condition(code),
            spec.cooldown_seconds,
        )
        if index < len(condition_codes) - 1:
            await asyncio.sleep(spec.cooldown_seconds)
    return {
        "key": spec.key,
        "configured_provider": spec.provider,
        "configured_model": spec.model,
        "reasoning_effort": spec.reasoning_effort,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "successful_conditions": sum(1 for result in conditions.values() if result.get("ok")),
        "conditions": conditions,
        "matrix_invariants": _matrix_invariants(conditions),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--models",
        nargs="*",
        help="Optional model keys to run; omitted runs every configured provider candidate.",
    )
    parser.add_argument(
        "--conditions",
        nargs="*",
        choices=("01", "02", "03", "04"),
        default=("01", "02", "03", "04"),
        help="Condition codes to run; defaults to the complete matrix.",
    )
    args = parser.parse_args()
    base = get_settings()
    specs, skipped = _available_specs(base)
    if args.models:
        requested = set(args.models)
        specs = [spec for spec in specs if spec.key in requested]
    results = []
    condition_codes = tuple(dict.fromkeys(args.conditions))
    for spec in specs:
        print(f"[benchmark] {spec.key}", flush=True)
        results.append(await _run_spec(base, spec, condition_codes))

    output_dir = PROJECT_ROOT / ".dev-logs" / "llm-benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"persona-matrix-{timestamp}.json"
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fixture_scope": "public_synthetic_french_revolution",
        "database_writes": False,
        "requested_conditions": list(condition_codes),
        "skipped_providers": skipped,
        "results": results,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                "skipped_providers": skipped,
                "models": [
                    {
                        "key": result["key"],
                        "elapsed_seconds": result["elapsed_seconds"],
                        "successful_conditions": result["successful_conditions"],
                    }
                    for result in results
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
