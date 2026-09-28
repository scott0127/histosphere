"""Exercise the real administrator review gate in conversation regression tests."""


ADMIN_HEADERS = {"x-admin-key": "test-admin"}


def add_generated_question(client, question: dict) -> None:
    """Set up a multi-question task before its material snapshot is frozen."""
    generate_task = client.app.state.llm_provider.generate_task

    async def generate(event, sources):
        task = await generate_task(event, sources)
        task.evaluation_payload["questions"].append(question)
        task.error_elicitation_task_full_text += f"\n{question['prompt']} {{{{blank:{question['id']}}}}}"
        return task

    client.app.state.llm_provider.generate_task = generate


def review_and_approve(client, accepted: dict) -> dict:
    """Confirm each fixture verdict through the API, then approve the attempt."""
    polled = client.get(accepted["poll_url"])
    assert polled.status_code == 200, polled.text
    attempt = polled.json()["attempt"]
    assert attempt["status"] == "awaiting_review", polled.text
    monitor = client.get(
        f"/api/admin/monitor/sessions/{attempt['session_id']}", headers=ADMIN_HEADERS,
    )
    assert monitor.status_code == 200, monitor.text
    private_attempt = monitor.json()["attempt"]
    questions = []
    for row in private_attempt["review_payload"]["question_results"]:
        questions.append({
            "question_id": row["question_id"],
            "reviewed": True,
            "answer_correct": row["answer_correct"],
            "reasoning_correct": row["reasoning_correct"],
            "answer_feedback": row.get("answer_feedback") or "研究者核對測試材料後確認答案判定。",
            "reasoning_feedback": row.get("reasoning_feedback") or "研究者核對測試判準後確認理由判定。",
            "override_reason": "",
        })
    reviewed = client.patch(
        f"/api/admin/monitor/attempts/{attempt['id']}/review",
        headers=ADMIN_HEADERS,
        json={"expected_version": private_attempt["review_version"], "question_results": questions},
    )
    assert reviewed.status_code == 200, reviewed.text
    approved = client.post(
        f"/api/admin/monitor/attempts/{attempt['id']}/approve",
        headers=ADMIN_HEADERS,
        json={"expected_version": reviewed.json()["review_version"]},
    )
    assert approved.status_code == 200, approved.text
    return approved.json()


def review_and_enter(client, accepted: dict) -> dict:
    """Run the review gate and learner entry without bypassing workflow state."""
    review_and_approve(client, accepted)
    ready = client.get(accepted["poll_url"])
    assert ready.status_code == 200, ready.text
    assert ready.json()["attempt"]["status"] == "ready", ready.text
    entered = client.post(f"/api/tasks/attempts/{accepted['attempt_id']}/enter")
    assert entered.status_code == 200, entered.text
    result = entered.json()
    assert result["attempt"]["status"] == "submitted"
    assert result["conversation_id"]
    return result
