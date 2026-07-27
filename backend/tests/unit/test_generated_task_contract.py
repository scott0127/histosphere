import pytest
from pydantic import ValidationError

from app.providers.llm.structured import GeneratedTaskPayload


def _valid_payload() -> dict:
    return {
        "title": "法國大革命：歷史思考任務",
        "story_text": "1789 年法國爆發革命。",
        "display_text": "{{blank:q01}}年法國爆發革命。",
        "evaluation_payload": {
            "rubric": "檢查時間脈絡。",
            "questions": [
                {
                    "id": "q01",
                    "blank_id": "q01",
                    "type": "cloze",
                    "prompt": "請填入革命爆發年份。",
                    "source_text": "1789",
                    "correct_answer": "1789",
                    "required": True,
                }
            ],
        },
    }


def test_generated_task_accepts_current_inline_question_contract():
    payload = GeneratedTaskPayload.model_validate(_valid_payload())

    assert payload.display_text == "{{blank:q01}}年法國爆發革命。"
    assert payload.evaluation_payload["questions"][0]["correct_answer"] == "1789"


@pytest.mark.parametrize(
    ("display_text", "evaluation_payload"),
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
    display_text: str,
    evaluation_payload: dict,
):
    raw = _valid_payload()
    raw["display_text"] = display_text
    raw["evaluation_payload"] = evaluation_payload

    with pytest.raises(ValidationError):
        GeneratedTaskPayload.model_validate(raw)
