from copy import deepcopy

import pytest

from app.core.error_elicitation_contract import ERROR_ELICITATION_JUDGE_CONTRACT_VERSION
from app.models.domain import EventTask
from app.providers.llm.json_runner import LLMCallMetadata, LLMRunError
from app.services.task_service import TaskService


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
        {"question_id": "q01", "reasoning_correct": True, "reasoning_feedback": "能指出地點依據。", "historical_thinking_tags": ["evidence"]},
        {"question_id": "q02", "reasoning_correct": False, "reasoning_feedback": "尚未說明畫作可以提供哪些資料。", "historical_thinking_tags": ["evidence"]},
        {"question_id": "q03", "reasoning_correct": False, "reasoning_feedback": "沒有連結到材料。", "historical_thinking_tags": []},
    ]}


@pytest.mark.parametrize("condition", ["no_ebl_no_roleplay", "ebl_no_roleplay", "no_ebl_roleplay", "ebl_roleplay"])
def test_new_task_draft_submit_and_research_preserve_both_inputs(client, condition):
    initialized = initialize(client, condition)
    response_payload = answers()
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
    assert status["attempt"]["status"] == "submitted", status
    assert len(calls) == 1
    results = status["result"]["judgement"]["question_results"]
    assert [row["correctness"] for row in results] == ["correct", "incorrect", "incorrect"]
    assert results[1]["answer_correct"] is True
    assert results[1]["reasoning_correct"] is False
    assert all("expected_answer" not in row and "reasoning_feedback" not in row for row in results)
    stored = client.app.state.repository.get_task_attempt(status["attempt"]["id"])
    assert stored.response_payload == response_payload
    assert stored.judgement_payload["question_results"][1]["reasoning_feedback"] == "尚未說明畫作可以提供哪些資料。"
    assert "reasoning_issue_types" not in stored.judgement_payload["question_results"][1]
    research = client.get(f"/api/admin/sessions/{initialized['session_id']}/research", headers=HEADERS).json()
    assert research["attempt"]["judgement_payload"] == stored.judgement_payload
    assert research["material_snapshot"]["hash_verified"] is True


@pytest.mark.parametrize("failure", ["timeout", "missing_question"])
def test_failed_judge_keeps_inputs_and_retries_same_attempt_without_false_grades(client, failure):
    initialized = initialize(client, "no_ebl_no_roleplay")
    request = {"session_id": initialized["session_id"], "user_id": "participant-001", "response_payload": answers()}
    async def broken_judge(*args):
        if failure == "timeout":
            raise TimeoutError("test")
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
    assert complete["attempt"]["status"] == "submitted"
    assert complete["attempt"]["response_payload"] == request["response_payload"]


@pytest.mark.parametrize("retry_path", ["submit", "unchanged_draft", "restart", "answer", "rationale", "task"])
def test_opening_failure_reuses_only_a_valid_unchanged_judgement(client, retry_path):
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
    failed = client.get(accepted["poll_url"], headers=HEADERS).json()
    assert failed["attempt"]["status"] == "failed"
    attempt = state.repository.get_task_attempt(accepted["attempt_id"])
    assert attempt.judgement_payload["judgement_input_hash"]
    assert attempt.judgement_payload["llm_call"] == judge_metadata["llm_call"]
    assert "judgement_input_hash" not in failed["attempt"]["judgement_payload"]
    assert state.repository.get_session(initialized["session_id"]).timer_ends_at is None

    state.opening_service.generate = original_opening
    if retry_path == "answer":
        request["response_payload"]["answers"][0]["value"] = "Osaka"
    elif retry_path == "rationale":
        request["response_payload"]["answers"][0]["rationale"] = "A different reason."
    elif retry_path == "task":
        task = state.repository.get_event_task(initialized["task"]["id"])
        task.evaluation_payload["questions"][0]["reasoning_criteria"] = "An amended criterion."
        state.repository.save_event_task(task)
    elif retry_path == "unchanged_draft":
        assert client.patch(f"{task_url}/draft", headers=HEADERS, json=request).status_code == 200
    elif retry_path == "restart":
        # 模擬判題落盤後程序中斷；新 service 只能從 repository 恢復，不依賴記憶體快取。
        attempt.status = "processing"
        state.repository.save_task_attempt(attempt)
        state.task_service = TaskService(state.repository, state.llm_provider, state.opening_service)

    if retry_path != "restart":
        retried = client.post(f"{task_url}/submit", headers=HEADERS, json=request)
        assert retried.json()["attempt_id"] == accepted["attempt_id"]
    complete = client.get(accepted["poll_url"], headers=HEADERS).json()
    if retry_path == "restart":
        complete = client.get(accepted["poll_url"], headers=HEADERS).json()
    assert complete["attempt"]["status"] == "submitted"
    assert len(judge_calls) == (2 if retry_path in {"answer", "rationale", "task"} else 1)
    saved = state.repository.get_task_attempt(accepted["attempt_id"])
    assert saved.response_payload == request["response_payload"]
    assert saved.judgement_payload["llm_call"] == judge_metadata["llm_call"]
    assert "error" not in saved.judgement_payload
    assert len(state.repository.list_messages(complete["result"]["conversation_id"])) == 1
    assert state.repository.get_session(initialized["session_id"]).timer_ends_at is not None
