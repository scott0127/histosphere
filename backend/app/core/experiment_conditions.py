"""Canonical 2x2 experiment condition definitions.

The learner-facing code and the runtime condition key represent the same fixed
experimental cell. Keeping the factor values here prevents UI labels, session
snapshots, and LLM policies from silently drifting apart.
"""

from dataclasses import dataclass
from typing import Final, Literal


ConditionCode = Literal["01", "02", "03", "04"]
AgentMode = Literal["generic", "persona"]
ResponsePolicy = Literal["direct", "scaffold"]


@dataclass(frozen=True)
class ExperimentConditionDefinition:
    code: ConditionCode
    condition_key: str
    default_label: str
    ebl_enabled: bool
    roleplay_enabled: bool
    agent_mode: AgentMode
    response_policy: ResponsePolicy
    default_description: str


EXPERIMENT_CONDITION_DEFINITIONS: Final = (
    ExperimentConditionDefinition(
        code="01",
        condition_key="no_ebl_no_roleplay",
        default_label="Without EBL + Without AI Role-play",
        ebl_enabled=False,
        roleplay_enabled=False,
        agent_mode="generic",
        response_policy="direct",
        default_description="一般 ChatGPT 式回答；可直接給正確答案。",
    ),
    ExperimentConditionDefinition(
        code="02",
        condition_key="ebl_no_roleplay",
        default_label="With EBL + Without AI Role-play",
        ebl_enabled=True,
        roleplay_enabled=False,
        agent_mode="generic",
        response_policy="scaffold",
        default_description=(
            "一般 tutor chatbot；引導 historical thinking、"
            "evidence-based argumentation、source interpretation。"
        ),
    ),
    ExperimentConditionDefinition(
        code="03",
        condition_key="no_ebl_roleplay",
        default_label="Without EBL + With AI Role-play",
        ebl_enabled=False,
        roleplay_enabled=True,
        agent_mode="persona",
        response_policy="direct",
        default_description="AI historical persona role-play；沉浸式回答，可直接給答案。",
    ),
    ExperimentConditionDefinition(
        code="04",
        condition_key="ebl_roleplay",
        default_label="With EBL + With AI Role-play",
        ebl_enabled=True,
        roleplay_enabled=True,
        agent_mode="persona",
        response_policy="scaffold",
        default_description=(
            "AI historical persona 基於 learner misconceptions 展開對話並引導 historical thinking。"
        ),
    ),
)

EXPERIMENT_CONDITION_BY_KEY: Final = {
    definition.condition_key: definition
    for definition in EXPERIMENT_CONDITION_DEFINITIONS
}
EXPERIMENT_CONDITION_KEY_BY_CODE: Final = {
    definition.code: definition.condition_key
    for definition in EXPERIMENT_CONDITION_DEFINITIONS
}
EXPERIMENT_CONDITION_ORDER_BY_KEY: Final = {
    definition.condition_key: index
    for index, definition in enumerate(EXPERIMENT_CONDITION_DEFINITIONS)
}


def condition_sort_index(condition_key: str) -> int:
    """Return canonical 01-to-04 order, placing unknown keys last."""
    return EXPERIMENT_CONDITION_ORDER_BY_KEY.get(
        condition_key,
        len(EXPERIMENT_CONDITION_DEFINITIONS),
    )


def sort_condition_codes(codes: list[ConditionCode]) -> list[ConditionCode]:
    """Deduplicate learner-facing codes in canonical 01-to-04 order."""
    selected = set(codes)
    return [
        definition.code
        for definition in EXPERIMENT_CONDITION_DEFINITIONS
        if definition.code in selected
    ]


def validate_condition_behavior(
    condition_key: str,
    *,
    ebl_enabled: bool,
    roleplay_enabled: bool,
    agent_mode: str,
    response_policy: str,
) -> None:
    """Reject a condition row whose runtime factors do not match its fixed key."""
    definition = EXPERIMENT_CONDITION_BY_KEY.get(condition_key)
    if definition is None:
        raise ValueError(f"Unsupported experiment condition key: {condition_key}")

    expected = {
        "ebl_enabled": definition.ebl_enabled,
        "roleplay_enabled": definition.roleplay_enabled,
        "agent_mode": definition.agent_mode,
        "response_policy": definition.response_policy,
    }
    actual = {
        "ebl_enabled": ebl_enabled,
        "roleplay_enabled": roleplay_enabled,
        "agent_mode": agent_mode,
        "response_policy": response_policy,
    }
    mismatches = [
        f"{field}={actual[field]!r} (expected {value!r})"
        for field, value in expected.items()
        if actual[field] != value
    ]
    if mismatches:
        details = ", ".join(mismatches)
        raise ValueError(
            f"Condition {definition.code}/{condition_key} violates the fixed 2x2 matrix: {details}"
        )
