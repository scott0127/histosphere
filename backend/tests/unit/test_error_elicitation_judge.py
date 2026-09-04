from copy import deepcopy
import asyncio
from types import SimpleNamespace

import pytest

from app.core.error_elicitation_contract import validate_task_answers
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
    return {"judge_contract_version": "error_elicitation_judge_v2", "question_results": [
        {"question_id": "q01", "reasoning_correct": True, "reasoning_issue_types": [], "reasoning_feedback": "所述與材料相符。", "historical_thinking_tags": ["evidence"]},
        {"question_id": "q02", "reasoning_correct": False, "reasoning_issue_types": ["reasoning_error"], "reasoning_feedback": "不能將所有畫作一概視為虛假。", "historical_thinking_tags": ["evidence"]},
        {"question_id": "q03", "reasoning_correct": True, "reasoning_issue_types": [], "reasoning_feedback": "所引資料正確。", "historical_thinking_tags": []},
    ], "llm_call": {"model": "test"}}


def test_real_merge_uses_rules_and_reasons_without_overwriting_raw_answers():
    task, response = task_and_response()
    original = deepcopy(response)
    result = enrich_task_judgement(task, response, judge_payload())
    assert [(row["answer_correct"], row["reasoning_correct"], row["correctness"]) for row in result["question_results"]] == [
        (True, True, "correct"), (True, False, "incorrect"), (False, True, "incorrect"),
    ]
    assert result["question_results"][1]["learner_rationale"] == original["answers"][1]["rationale"]
    assert result["question_results"][1]["error_code"] == "reasoning_error"
    assert result["question_results"][1]["historical_thinking_tags"] == ["evidence"]
    assert result["result"] == "incorrect"
    assert result["llm_call"] == {"model": "test"}
    assert response == original


@pytest.mark.parametrize("failure", ["missing", "extra", "duplicate", "contradictory"])
def test_bad_judge_output_is_rejected_not_converted_to_student_error(failure):
    task, response = task_and_response()
    raw = judge_payload()
    if failure == "missing":
        raw["question_results"].pop()
    elif failure == "extra":
        raw["question_results"].append({**raw["question_results"][0], "question_id": "q99"})
    elif failure == "duplicate":
        raw["question_results"].append(raw["question_results"][0])
    else:
        raw["question_results"][0]["reasoning_correct"] = False
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
    assert len(result["question_results"]) == 3
