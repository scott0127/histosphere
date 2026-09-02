import pytest

from app.models.domain import EventTask


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
    return {"question_results": [
        {"question_id": "q01", "reasoning_correct": True, "reasoning_issue": "none", "reasoning_feedback": "能指出地點依據。"},
        {"question_id": "q02", "reasoning_correct": False, "reasoning_issue": "insufficient_reasoning", "reasoning_feedback": "尚未說明畫作可以提供哪些資料。"},
        {"question_id": "q03", "reasoning_correct": False, "reasoning_issue": "insufficient_reasoning", "reasoning_feedback": "沒有連結到材料。"},
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
    assert stored.judgement_payload["question_results"][1]["reasoning_issue"] == "insufficient_reasoning"
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
        return {"question_results": judged()["question_results"][:1]}
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
