from copy import deepcopy
import asyncio
from types import SimpleNamespace

import pytest

from app.core.error_elicitation_contract import ERROR_ELICITATION_JUDGE_CONTRACT_VERSION, validate_task_answers
from app.core.interaction_contract import build_interaction_runtime
from app.models.domain import EventTask
from app.services.task_judgement import enrich_task_judgement


def task_and_response():
    task = EventTask(event_id="event", error_elicitation_task_full_text=(
        "題目共同脈絡。\nQ01：填空並說明理由。{{blank:q01}}\n"
        "Q02：判斷是非並說明理由。{{blank:q02}}\n"
        "Q03：選擇並說明理由。{{blank:q03}}"
    ), evaluation_payload={
        "contract_version": "error_elicitation_v1",
        "questions": [
            {"id": "q01", "type": "cloze", "correct_answer": ["南京", "Nanjing"], "reasoning_criteria": "說明地點依據。"},
            {"id": "q02", "type": "true_false", "correct_answer": False, "reasoning_criteria": "不能以所有畫作都是假的作為理由。"},
            {"id": "q03", "type": "multiple_choice", "options": [{"value": "A"}, {"value": "B"}], "correct_answer": "A", "reasoning_criteria": "提出相關線索。"},
        ],
    })
    response = {"contract_version": "error_elicitation_v1", "answers": [
        {"question_id": "q01", "value": " ＮＡＮＪＩＮＧ ", "rationale": "材料記載了簽約地點。"},
        {"question_id": "q02", "value": False, "rationale": "因為所有画都是假的。"},
        {"question_id": "q03", "value": "B", "rationale": "這個資料記載了五個地點。"},
    ]}
    return task, response


def judge_payload():
    return {"judge_contract_version": ERROR_ELICITATION_JUDGE_CONTRACT_VERSION, "question_results": [
        {"question_id": "q01", "answer_correct": True, "answer_feedback": "指向材料記載的南京。", "reasoning_correct": True, "reasoning_feedback": "所述與材料相符。", "historical_thinking_tags": ["evidence"]},
        {"question_id": "q02", "reasoning_correct": False, "reasoning_feedback": "不能將所有畫作一概視為虛假。", "historical_thinking_tags": ["evidence"]},
        {"question_id": "q03", "reasoning_correct": True, "reasoning_feedback": "所引資料正確。", "historical_thinking_tags": []},
    ], "llm_call": {"model": "test"}}


def test_real_merge_uses_rules_and_reasons_without_overwriting_raw_answers():
    task, response = task_and_response()
    original = deepcopy(response)
    judgement = judge_payload()
    # A model cannot override deterministic choice/boolean grading.
    judgement["question_results"][1].update(answer_correct=False, answer_feedback="ignored")
    judgement["question_results"][2].update(answer_correct=True, answer_feedback="ignored")
    result = enrich_task_judgement(task, response, judgement)
    assert [(row["answer_correct"], row["reasoning_correct"], row["correctness"]) for row in result["question_results"]] == [
        (True, True, "correct"), (True, False, "incorrect"), (False, True, "incorrect"),
    ]
    assert result["question_results"][1]["learner_rationale"] == original["answers"][1]["rationale"]
    assert "error_code" not in result["question_results"][1]
    assert "reasoning_issue_types" not in result["question_results"][1]
    assert result["question_results"][1]["historical_thinking_tags"] == ["evidence"]
    assert result["result"] == "incorrect"
    assert result["llm_call"] == {"model": "test"}
    assert response == original
    assert all(row["answer_feedback"] is None for row in result["question_results"][1:])


@pytest.mark.parametrize("answer, answer_correct, reasoning_correct", [
    ("大衛的畫稿。", True, True),
    ("大衛描繪網球場宣誓的草稿", True, True),
    ("當天拍攝的照片", False, True),
    ("大衛的畫稿。", True, False),
])
def test_cloze_uses_semantic_judge_without_changing_raw_inputs_or_ebl_rules(
    answer, answer_correct, reasoning_correct,
):
    task, response = task_and_response()
    expected = ["大衛的畫稿"]
    task.evaluation_payload["questions"][0]["correct_answer"] = expected
    response["answers"][0]["value"] = answer
    original = deepcopy(response)
    judgement = judge_payload()
    feedback = "填寫內容指向大衛畫稿。" if answer_correct else "材料是畫稿，不能說成事件當天拍攝的照片。"
    judgement["question_results"][0].update(
        answer_correct=answer_correct, answer_feedback=feedback, reasoning_correct=reasoning_correct,
    )

    enriched = enrich_task_judgement(task, response, judgement)
    result = enriched["question_results"][0]

    assert result["answer_correct"] is answer_correct
    assert result["reasoning_correct"] is reasoning_correct
    assert result["correctness"] == ("correct" if answer_correct and reasoning_correct else "incorrect")
    assert result["learner_answer"] == answer
    assert result["expected_answer"] == expected
    assert result["answer_feedback"] == feedback
    assert response == original
    runtime = build_interaction_runtime(
        SimpleNamespace(condition_key="ebl_roleplay", ebl_enabled=True, roleplay_enabled=True),
        SimpleNamespace(judgement_payload=enriched), [],
    )
    assert runtime.target.question_id == ("q02" if answer_correct and reasoning_correct else "q01")
    if runtime.target.question_id == "q01":
        assert runtime.target.answer_feedback == feedback
        assert feedback in runtime.prompt_block()


@pytest.mark.parametrize("failure", [
    "missing", "extra", "duplicate", "invalid_boolean", "missing_answer", "invalid_answer", "missing_feedback",
])
def test_bad_judge_output_is_rejected_not_converted_to_student_error(failure):
    task, response = task_and_response()
    raw = judge_payload()
    if failure == "missing":
        raw["question_results"].pop()
    elif failure == "extra":
        raw["question_results"].append({**raw["question_results"][0], "question_id": "q99"})
    elif failure == "duplicate":
        raw["question_results"].append(raw["question_results"][0])
    elif failure == "missing_answer":
        raw["question_results"][0].pop("answer_correct")
    elif failure == "invalid_answer":
        raw["question_results"][0]["answer_correct"] = "true"
    elif failure == "missing_feedback":
        raw["question_results"][0].pop("answer_feedback")
    else:
        raw["question_results"][0]["reasoning_correct"] = "false"
    with pytest.raises(ValueError):
        enrich_task_judgement(task, response, raw)


def test_draft_can_be_partial_but_submission_needs_all_answers_and_reasons():
    task, response = task_and_response()
    response["answers"] = [{"question_id": "q02", "value": False, "rationale": "  "}]
    validate_task_answers(task.evaluation_payload, response, complete=False)
    with pytest.raises(ValueError):
        validate_task_answers(task.evaluation_payload, response, complete=True)
    response["answers"][0]["question_id"] = "q99"
    with pytest.raises(ValueError):
        validate_task_answers(task.evaluation_payload, response, complete=False)


@pytest.mark.parametrize("display_text", ["true", "false", "是", "否", "真", "假"])
def test_true_false_answers_use_json_booleans_internally(display_text):
    task, response = task_and_response()
    response["answers"][1]["value"] = display_text

    with pytest.raises(ValueError, match="answer must be a boolean"):
        validate_task_answers(task.evaluation_payload, response, complete=True)


def test_provider_batches_reasons_with_full_context_in_one_call():
    from app.core.config import Settings
    from app.models.domain import Event
    from app.providers.llm.litellm_provider import LiteLLMProvider
    task, response = task_and_response()
    calls = []
    class Runner:
        async def run_json(self, **kwargs):
            calls.append(kwargs)
            payload = judge_payload()
            return SimpleNamespace(
                payload=kwargs["schema"].model_validate({
                    "judge_contract_version": payload["judge_contract_version"],
                    "question_results": payload["question_results"],
                }),
                metadata=SimpleNamespace(provider="fake", model="fake", as_dict=lambda: {"model": "fake"}),
            )
    provider = LiteLLMProvider(Settings())
    provider.runner = Runner()
    result = asyncio.run(provider.judge_task_attempt(Event(canonical_name="測試事件"), task, response))
    assert len(calls) == 1
    assert "error_elicitation_task_full_text" in calls[0]["user_prompt"]
    assert "reasoning_criteria" in calls[0]["user_prompt"]
    assert response["answers"][1]["rationale"] in calls[0]["user_prompt"]
    assert "reasoning_correct must be a JSON boolean" in calls[0]["user_prompt"]
    assert "not an exhaustive whitelist" in calls[0]["user_prompt"]
    assert "backend rules grade answers; return answer_correct=null" in calls[0]["user_prompt"]
    assert result["question_results"][0]["answer_correct"] is True
    assert "reasoning_issue_types" not in calls[0]["user_prompt"]
    assert len(result["question_results"]) == 3
