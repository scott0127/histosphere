import pytest
from pydantic import ValidationError

from app.core.error_elicitation_contract import ERROR_ELICITATION_CONTRACT_VERSION
from app.core.task_payload_validator import validate_task_authoring_payload
from app.providers.llm.structured import GeneratedTaskPayload


def _valid_payload() -> dict:
    return {
        "title": "法國大革命：歷史思考任務",
        "story_text": "1789 年法國爆發革命。",
        "error_elicitation_task_full_text": "{{blank:q01}}年法國爆發革命。",
        "evaluation_payload": {
            "contract_version": ERROR_ELICITATION_CONTRACT_VERSION,
            "rubric": "檢查時間脈絡。",
            "questions": [
                {
                    "id": "q01",
                    "blank_id": "q01",
                    "type": "cloze",
                    "reasoning_criteria": "說明年份如何符合題文的時間脈絡。",
                    "source_text": "1789",
                    "correct_answer": "1789",
                    "required": True,
                }
            ],
        },
    }


def test_generated_task_accepts_current_inline_question_contract():
    payload = GeneratedTaskPayload.model_validate(_valid_payload())

    assert payload.error_elicitation_task_full_text == "{{blank:q01}}年法國爆發革命。"
    assert payload.evaluation_payload["questions"][0]["correct_answer"] == "1789"


def test_reading_caption_is_optional_text_and_keeps_admin_references():
    raw = _valid_payload()
    material = {
        "id": "m01", "title": "A painting", "text": "Reading passage.",
        "image_url": "https://example.org/image.png",
        "caption": "Artist, 1850; depicting events in 1600.",
        "source_url": "https://example.org/source", "attribution": "Archive credit",
    }
    raw["evaluation_payload"]["materials"] = [material]
    result = GeneratedTaskPayload.model_validate(raw)
    assert result.evaluation_payload["materials"] == [material]

    material["caption"] = 1850
    with pytest.raises(ValidationError):
        GeneratedTaskPayload.model_validate(raw)


def test_generated_task_accepts_complete_all_correct_fallback():
    raw = _valid_payload()
    raw["evaluation_payload"]["all_correct_fallback"] = {
        "id": "fallback-01",
        "incorrect_claim": "法國大革命只由單一事件造成。",
        "correct_interpretation": "法國大革命由多項結構與事件因素共同造成。",
        "evidence_ids": ["E01"],
    }

    payload = GeneratedTaskPayload.model_validate(raw)

    assert payload.evaluation_payload["all_correct_fallback"]["id"] == "fallback-01"


def test_generated_task_rejects_incomplete_all_correct_fallback():
    raw = _valid_payload()
    raw["evaluation_payload"]["all_correct_fallback"] = {
        "id": "fallback-01",
        "incorrect_claim": "法國大革命只由單一事件造成。",
    }

    with pytest.raises(ValidationError):
        GeneratedTaskPayload.model_validate(raw)


@pytest.mark.parametrize(
    ("error_elicitation_task_full_text", "evaluation_payload"),
    [
        ("____年法國爆發革命。", {"rubric": "舊格式"}),
        ("1789 年法國爆發革命。", {"rubric": "缺少 questions"}),
        (
            "{{blank:q01}}年法國爆發革命。",
            {
                "questions": [
                    {
                        "id": "q02",
                        "blank_id": "q02",
                        "type": "cloze",
                        "prompt": "請填入年份。",
                        "correct_answer": "1789",
                    }
                ]
            },
        ),
    ],
)
def test_generated_task_rejects_legacy_or_inconsistent_payloads(
    error_elicitation_task_full_text: str,
    evaluation_payload: dict,
):
    raw = _valid_payload()
    raw["error_elicitation_task_full_text"] = error_elicitation_task_full_text
    raw["evaluation_payload"] = evaluation_payload

    with pytest.raises(ValidationError):
        GeneratedTaskPayload.model_validate(raw)


@pytest.mark.parametrize(
    ("question_type", "answer", "options"),
    [
        ("cloze", ["1789", "一七八九"], None),
        ("true_false", False, None),
        ("multiple_choice", "A", [
            {"id": "a", "label": "選項甲", "value": "A"},
            {"id": "b", "label": "選項乙", "value": "B"},
        ]),
    ],
)
def test_error_elicitation_accepts_three_standalone_types_with_criteria(question_type, answer, options):
    raw = _valid_payload()
    raw["error_elicitation_task_full_text"] = "請逐題作答並說明理由。{{blank:q01}}"
    evaluation = raw["evaluation_payload"]
    evaluation["contract_version"] = ERROR_ELICITATION_CONTRACT_VERSION
    question = evaluation["questions"][0]
    question.update(type=question_type, correct_answer=answer, reasoning_criteria="理由須由素材支持答案。")
    if options:
        question["options"] = options

    result = GeneratedTaskPayload.model_validate(raw)

    assert result.evaluation_payload == evaluation
    assert result.evaluation_payload["questions"][0]["correct_answer"] == answer


@pytest.mark.parametrize(
    ("changes", "expected_code"),
    [
        ({"reasoning_criteria": " "}, "missing_reasoning_criteria"),
        ({"reasoning_criteria": {"text": "不能接受物件"}}, "missing_reasoning_criteria"),
        ({"type": "short_answer"}, "unsupported_question_type"),
        ({"correct_answer": []}, "missing_correct_answer"),
        ({"correct_answer": ["1789", " "]}, "missing_correct_answer"),
        ({"required": False}, "question_must_be_required"),
        ({"id": " q01 "}, "invalid_question_id"),
    ],
)
def test_error_elicitation_rejects_incomplete_authoring_contract(changes, expected_code):
    evaluation = _valid_payload()["evaluation_payload"]
    evaluation["contract_version"] = ERROR_ELICITATION_CONTRACT_VERSION
    evaluation["questions"][0]["reasoning_criteria"] = "理由須由素材支持答案。"
    evaluation["questions"][0].update(changes)

    issues = validate_task_authoring_payload("逐題作答", evaluation)

    assert expected_code in {issue["code"] for issue in issues}


def test_error_elicitation_rejects_duplicate_ids_and_unknown_versions():
    evaluation = _valid_payload()["evaluation_payload"]
    evaluation["contract_version"] = ERROR_ELICITATION_CONTRACT_VERSION
    question = evaluation["questions"][0]
    question["reasoning_criteria"] = "理由須由素材支持答案。"
    evaluation["questions"].append({**question, "blank_id": "another-blank"})
    issues = validate_task_authoring_payload("逐題作答", evaluation)
    assert "duplicate_question_id" in {issue["code"] for issue in issues}

    evaluation["contract_version"] = "unknown-version"
    issues = validate_task_authoring_payload("逐題作答", evaluation)
    assert issues[0]["code"] == "unsupported_task_contract"


def test_error_elicitation_choice_values_are_strings_and_unambiguous():
    evaluation = _valid_payload()["evaluation_payload"]
    evaluation["contract_version"] = ERROR_ELICITATION_CONTRACT_VERSION
    evaluation["questions"][0].update(
        type="multiple_choice",
        correct_answer=1,
        reasoning_criteria="說明選項如何由素材支持。",
        options=[{"value": 1}, {"value": "A"}, {"value": "a"}],
    )
    codes = {issue["code"] for issue in validate_task_authoring_payload("逐題作答", evaluation)}
    assert {"missing_option_value", "duplicate_option_value", "answer_not_in_options"}.issubset(codes)
