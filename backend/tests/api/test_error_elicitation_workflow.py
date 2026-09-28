from copy import deepcopy

import pytest

from app.core.error_elicitation_contract import ERROR_ELICITATION_JUDGE_CONTRACT_VERSION
from app.core.interaction_contract import build_interaction_runtime
from app.models.domain import EventTask
from app.providers.llm.json_runner import LLMCallMetadata, LLMRunError
from app.services.task_service import TaskService
from tests.task_review_helpers import review_and_approve, review_and_enter


VERSION = "error_elicitation_v1"
HEADERS = {"x-admin-key": "test-admin"}


def initialize(client, condition):
    async def generate_task(event, sources):
        return EventTask(event_id=event.id, error_elicitation_task_full_text=(
            "資料記載簽約地點為南京。\n"
            "Q01：填寫地點。{{blank:q01}}\n"
            "Q02：所有畫作都不能用作資料。{{blank:q02}}\n"
            "Q03：哪個資料支持這個判斷？{{blank:q03}}"
        ), evaluation_payload={
            "contract_version": VERSION,
            "questions": [
                {"id": "q01", "type": "cloze", "correct_answer": ["南京", "Nanjing"], "reasoning_criteria": "能指出地點依據。"},
                {"id": "q02", "type": "true_false", "correct_answer": False, "reasoning_criteria": "不能一概否認所有畫作。"},
                {"id": "q03", "type": "multiple_choice", "options": [{"value": "A", "label": "條約"}, {"value": "B", "label": "無關材料"}], "correct_answer": "A", "reasoning_criteria": "能將答案連結到材料。"},
            ],
        })
    client.app.state.llm_provider.generate_task = generate_task
    response = client.post("/api/event/initialize", headers=HEADERS, json={
        "event_name": "新版題目驗收事件", "condition_key": condition, "rebuild": False, "user_id": "participant-001",
    })
    assert response.status_code == 200, response.text
    return response.json()


def answers():
    return {"contract_version": VERSION, "answers": [
        {"question_id": "q01", "value": "Nanjing", "rationale": "  根據資料中的簽約地點。\n"},
        {"question_id": "q02", "value": False, "rationale": "因為我猜的。"},
        {"question_id": "q03", "value": "B", "rationale": "沒有理由。"},
    ]}


def judged():
    return {"judge_contract_version": ERROR_ELICITATION_JUDGE_CONTRACT_VERSION, "question_results": [
        {"question_id": "q01", "answer_correct": True, "answer_feedback": "指的是材料中的南京。", "reasoning_correct": True, "reasoning_feedback": "能指出地點依據。", "historical_thinking_tags": ["evidence"]},
        {"question_id": "q02", "reasoning_correct": False, "reasoning_feedback": "尚未說明畫作可以提供哪些資料。", "historical_thinking_tags": ["evidence"]},
        {"question_id": "q03", "reasoning_correct": False, "reasoning_feedback": "沒有連結到材料。", "historical_thinking_tags": []},
    ]}


@pytest.mark.parametrize("condition", ["no_ebl_no_roleplay", "ebl_no_roleplay", "no_ebl_roleplay", "ebl_roleplay"])
def test_new_task_draft_submit_and_research_preserve_both_inputs(client, condition):
    initialized = initialize(client, condition)
    response_payload = answers()
    response_payload["answers"][0]["value"] = "南京城。"
    calls = []
    async def judge(event, task, response):
        calls.append(response)
        return judged()
    client.app.state.llm_provider.judge_task_attempt = judge
    request = {"session_id": initialized["session_id"], "user_id": "participant-001", "response_payload": response_payload}
    task_url = f"/api/tasks/{initialized['task']['id']}"
    draft = client.patch(f"{task_url}/draft", headers=HEADERS, json=request)
    assert draft.status_code == 200, draft.text
    resumed = client.get(f"/api/sessions/{initialized['session_id']}/state", headers=HEADERS)
    assert resumed.json()["attempt"]["response_payload"] == response_payload
    assert calls == []

    accepted = client.post(f"{task_url}/submit", headers=HEADERS, json=request)
    assert accepted.status_code == 202, accepted.text
    status = client.get(accepted.json()["poll_url"], headers=HEADERS).json()
    assert status["attempt"]["status"] == "awaiting_review", status
    assert status["result"] is None
    assert len(calls) == 1
    submitted = review_and_enter(client, accepted.json())
    results = submitted["judgement"]["question_results"]
    assert [row["correctness"] for row in results] == ["correct", "incorrect", "incorrect"]
    assert results[1]["answer_correct"] is True
    assert results[1]["reasoning_correct"] is False
    assert all("expected_answer" not in row and "reasoning_feedback" not in row for row in results)
    assert all("answer_feedback" not in row for row in results)
    stored = client.app.state.repository.get_task_attempt(status["attempt"]["id"])
    assert stored.response_payload == response_payload
    assert stored.judgement_payload["question_results"][1]["reasoning_feedback"] == "尚未說明畫作可以提供哪些資料。"
    assert "reasoning_issue_types" not in stored.judgement_payload["question_results"][1]
    assert stored.judgement_payload["question_results"][0]["learner_answer"] == "南京城。"
    assert stored.judgement_payload["question_results"][0]["answer_feedback"] == "指的是材料中的南京。"
    runtime = build_interaction_runtime(
        client.app.state.repository.get_condition_by_key(condition), stored, [],
    )
    assert runtime.target.question_id == "q02"
    assert runtime.target_count == 2
    research = client.get(f"/api/admin/sessions/{initialized['session_id']}/research", headers=HEADERS).json()
    assert research["attempt"]["judgement_payload"] == stored.judgement_payload
    assert research["material_snapshot"]["hash_verified"] is True


@pytest.mark.parametrize("failure", ["timeout", "missing_question", "missing_cloze_judgement"])
def test_failed_judge_keeps_inputs_and_retries_same_attempt_without_false_grades(client, failure):
    initialized = initialize(client, "no_ebl_no_roleplay")
    request = {"session_id": initialized["session_id"], "user_id": "participant-001", "response_payload": answers()}
    async def broken_judge(*args):
        if failure == "timeout":
            raise TimeoutError("test")
        if failure == "missing_cloze_judgement":
            result = judged()
            result["question_results"][0].pop("answer_correct")
            return result
        return {
            "judge_contract_version": ERROR_ELICITATION_JUDGE_CONTRACT_VERSION,
            "question_results": judged()["question_results"][:1],
        }
    client.app.state.llm_provider.judge_task_attempt = broken_judge
    url = f"/api/tasks/{initialized['task']['id']}/submit"
    accepted = client.post(url, headers=HEADERS, json=request)
    assert accepted.status_code == 202
    failed = client.get(accepted.json()["poll_url"], headers=HEADERS).json()
    assert failed["attempt"]["status"] == "failed"
    assert failed["attempt"]["response_payload"] == request["response_payload"]
    assert not failed["attempt"]["judgement_payload"].get("question_results")
    assert failed["result"] is None
    async def recovered_judge(*args):
        return judged()
    client.app.state.llm_provider.judge_task_attempt = recovered_judge
    retried = client.post(url, headers=HEADERS, json=request)
    assert retried.json()["attempt_id"] == accepted.json()["attempt_id"]
    complete = client.get(retried.json()["poll_url"], headers=HEADERS).json()
    assert complete["attempt"]["status"] == "awaiting_review"
    assert complete["attempt"]["response_payload"] == request["response_payload"]
    assert review_and_enter(client, retried.json())["conversation_id"]


@pytest.mark.parametrize("retry_path", ["retry", "restart"])
def test_opening_failure_preserves_approved_judgement_and_resumes_without_regrading(client, retry_path):
    initialized = initialize(client, "no_ebl_no_roleplay")
    state = client.app.state
    request = {"session_id": initialized["session_id"], "user_id": "participant-001", "response_payload": answers()}
    task_url = f"/api/tasks/{initialized['task']['id']}"
    judge_calls = []
    judge_metadata = state.llm_provider._llm_metadata("judge_task_attempt")

    async def judge(event, task, response):
        judge_calls.append(deepcopy(response))
        return {**judged(), **judge_metadata}

    original_opening = state.opening_service.generate

    async def failed_opening(**kwargs):
        raise LLMRunError("Opening timed out", LLMCallMetadata(
            correlation_id="failed-opening", task_name="generate_greeting", provider="fake-test",
            model="fake-model", status="failed", latency_ms=1, attempt_count=1,
            transient_retry_count=0, schema_repair_count=0, total_tokens=9,
        ))

    state.llm_provider.judge_task_attempt = judge
    state.opening_service.generate = failed_opening
    accepted = client.post(f"{task_url}/submit", headers=HEADERS, json=request).json()
    review_and_approve(client, accepted)
    failed = client.get(accepted["poll_url"], headers=HEADERS).json()
    assert failed["attempt"]["status"] == "failed"
    attempt = state.repository.get_task_attempt(accepted["attempt_id"])
    assert attempt.judgement_payload["judgement_input_hash"]
    assert attempt.judgement_payload["llm_call"] == judge_metadata["llm_call"]
    assert attempt.judgement_payload["decision_source"] == "human_review"
    final_judgement = deepcopy(attempt.judgement_payload)
    approved_review = deepcopy(attempt.review_payload)
    original_judgement = deepcopy(attempt.ai_judgement_payload)
    assert "judgement_input_hash" not in failed["attempt"]["judgement_payload"]
    assert state.repository.get_session(initialized["session_id"]).timer_ends_at is None

    state.opening_service.generate = original_opening
    if retry_path == "restart":
        # 模擬已核可但開場工作中斷；新 service 從持久化資料恢復。
        attempt.status = "preparing_chat"
        state.repository.save_task_attempt(attempt)
        state.task_service = TaskService(state.repository, state.llm_provider, state.opening_service)
        state.active_task_attempts = set()
    else:
        retried = client.post(f"/api/admin/monitor/attempts/{attempt.id}/retry", headers=HEADERS)
        assert retried.status_code == 200, retried.text
    complete = client.get(accepted["poll_url"], headers=HEADERS).json()
    if retry_path == "restart":
        complete = client.get(accepted["poll_url"], headers=HEADERS).json()
    assert complete["attempt"]["status"] == "ready"
    assert len(judge_calls) == 1
    saved = state.repository.get_task_attempt(accepted["attempt_id"])
    assert saved.response_payload == request["response_payload"]
    assert saved.judgement_payload == final_judgement
    assert saved.ai_judgement_payload == original_judgement
    assert saved.review_payload == approved_review
    assert state.repository.get_session(initialized["session_id"]).timer_ends_at is None
    entered = client.post(f"/api/tasks/attempts/{attempt.id}/enter")
    assert entered.status_code == 200, entered.text
    assert len(state.repository.list_messages(entered.json()["conversation_id"])) == 1
    assert state.repository.get_session(initialized["session_id"]).timer_ends_at is not None


@pytest.mark.parametrize("changed_field", ["value", "rationale"])
@pytest.mark.parametrize("stage", ["awaiting_review", "ready", "failed_opening"])
def test_submitted_answers_remain_frozen_through_review_and_opening(client, changed_field, stage):
    initialized = initialize(client, "no_ebl_no_roleplay")
    state = client.app.state

    async def judge(*args):
        return judged()

    async def failed_opening(**kwargs):
        raise TimeoutError("Opening unavailable")

    state.llm_provider.judge_task_attempt = judge
    if stage == "failed_opening":
        state.opening_service.generate = failed_opening
    original_answers = answers()
    request = {"session_id": initialized["session_id"], "response_payload": deepcopy(original_answers)}
    task_url = f"/api/tasks/{initialized['task']['id']}"
    accepted = client.post(f"{task_url}/submit", json=request)
    assert accepted.status_code == 202, accepted.text
    if stage != "awaiting_review":
        review_and_approve(client, accepted.json())
    attempt_id = accepted.json()["attempt_id"]
    before = deepcopy(state.repository.get_task_attempt(attempt_id).model_dump())
    request["response_payload"]["answers"][0][changed_field] = "不同的已提交內容"
    assert client.patch(f"{task_url}/draft", json=request).status_code == 409
    assert client.post(f"{task_url}/submit", json=request).status_code == 409
    assert state.repository.get_task_attempt(attempt_id).model_dump() == before
    assert state.repository.get_task_attempt(attempt_id).response_payload == original_answers
