# Histosphere EBL Role-Play System Design

Updated: 2026-06-08

Histosphere is a thesis prototype for studying how Error-Based Learning (EBL) and AI historical persona role-play can support historical thinking and AI literacy.

Core terms used across docs/UI:

- historical thinking
- AI literacy
- productive error
- learner misconceptions
- source interpretation
- evidence-based argumentation
- critical reflection
- perspective-taking

## V1 User Flow

```text
select 2x2 experiment condition
-> input historical event
-> fetch Wikipedia zh/en
-> create event workspace
-> generate editable task / cloze-style text
-> generate 1-3 related personas
-> learner submits task
-> LLM judges correct / incorrect / partial
-> conversation unlocks
-> chat follows selected condition policy
```

## 2x2 Experiment Design

| | Without EBL | With EBL |
|---|---|---|
| Without AI Role-play | Learner does task, then uses generic ChatGPT-style assistant. Assistant may directly answer. | Learner does task, then uses generic tutor chatbot. Tutor guides thinking, argumentation, and source interpretation before giving direct answer. |
| With AI Role-play | Learner does task, then chats with AI historical personas. Persona can give immersive direct answer. | Learner does task, then chats with AI historical personas. Persona uses task misconceptions to scaffold historical thinking and does not directly give answer before self-correction. |

Condition keys:

- `no_ebl_no_roleplay`
- `ebl_no_roleplay`
- `no_ebl_roleplay`
- `ebl_roleplay`

The abandoned 1x3 condition design is not part of the current system.

## Implemented Milestone

Status: implemented in current working tree.

Backend:

- FastAPI app structure under `backend/app`.
- In-memory repository for deterministic tests.
- Supabase PostgREST repository for local/cloud runtime.
- Wikipedia provider with `summary` and `full` fetch modes.
- Event initialization returns event/task/personas/session, not conversation.
- Task submit stores response and LLM judgement, then creates conversation.
- Chat service switches generic/persona and direct/scaffold behavior from condition.
- Research logs record event/task/conversation/message actions.
- Admin key endpoints manage conditions, tasks, personas, and logs.

Frontend:

- `/` condition selection + event input + event list.
- `/task` required task submission gate.
- `/chat` generic/persona-aware chat UI.
- `/admin` minimal admin key dashboard.

## Backend Responsibilities

### Event Workspace

Generate or reuse:

- `events`
- `wiki_sources`
- `event_tasks`
- `personas`
- `experiment_sessions`

Do not fabricate uncertain historical metadata. Store nullable fields as `null`.

### Task Gate

V1 stores all learner response data in:

- `task_attempts.response_payload`

V1 stores LLM judgement in:

- `task_attempts.judgement_payload`

Expected judgement shape:

```json
{
  "result": "partial",
  "misconception_summary": "...",
  "feedback": "..."
}
```

### Conversation

Conversation is created only after task submit.

Messages use:

- `speaker_type`: `learner`, `assistant`, `persona`
- `speaker_name`: display-name snapshot
- `sequence_index`: stable replay order

### Admin

V1 admin uses a simple key:

- frontend page: `/admin`
- header: `x-admin-key`
- env: `HISTOSPHERE_ADMIN_KEY`

Admin can edit:

- condition settings
- task text and evaluation payload
- persona profile and prompt profile
- persona active state

## Frontend Responsibilities

### `/`

Purpose: start a research session.

Controls:

- 2x2 condition selector.
- historical event input.
- existing event list.

Output:

- stores `EventInitializeResponse` in `useState('taskData')`.
- navigates to `/task`.

### `/task`

Purpose: learner task gate.

Controls:

- task display text.
- optional original story text.
- learner answer textarea.
- submit button.

Output:

- calls `POST /api/tasks/{task_id}/submit`.
- stores `TaskSubmitResponse` in `useState('chatData')`.
- navigates to `/chat`.

### `/chat`

Purpose: conversation after task completion.

Controls:

- message list.
- input box.
- persona selector only when `condition.roleplay_enabled = true`.
- task judgement side panel.

### `/admin`

Purpose: teacher/researcher configuration.

Controls:

- admin key input.
- condition editor.
- task editor.
- persona prompt_profile editor.
- research log preview.

## Database Decisions

Implemented core tables:

- `events`
- `wiki_sources`
- `experiment_conditions`
- `experiment_sessions`
- `event_tasks`
- `task_attempts`
- `personas`
- `conversations`
- `messages`
- `research_logs`

Postponed tables:

- `knowledge_chunks`
- `task_blanks`
- `task_answers`

## Postponed Design Questions

### `task_blanks`

Need teacher/research discussion:

- how to score each blank.
- how to accept synonyms.
- how to store partial correctness.
- how to connect blank-level answers to EBL error categories.

### `task_answers`

V1 uses `task_attempts.response_payload`.

Future normalized answers may store:

- blank id.
- learner answer.
- correctness.
- feedback.
- error type.

### RAG

V1 does not perform RAG.

Future design:

```text
Data ingestion
-> Chunking
-> Embedding
-> Indexing
-> Retrieval
```

Potential future provider:

- Gemini embeddings
- OpenAI embeddings
- local embedding model
- Supabase pgvector

### Controlled AI-Generated Inaccuracies

V1 only reserves:

- `personas.prompt_profile.deliberate_error_enabled`
- `PromptService._deliberate_error_slot`

It is disabled by default because deliberate error design may move to post-test.

## Development Order

Current milestone completed:

1. Backend schema/domain/API alignment.
2. Task gate.
3. 2x2 condition policy.
4. Minimal frontend flow.
5. Admin key dashboard.
6. Docs and tests.

Suggested next milestones:

1. Replace stub LLM provider with Gemini provider.
2. Add robust task generation and judgement rubrics.
3. Add session persistence/reload for `/task`.
4. Improve admin dashboard with validation and save status.
5. Add participant IDs and experiment assignment logic.
6. Decide blank-level scoring and EBL coding with advisor.
7. Add export format for thesis analysis.

## Test Checklist

Backend:

- `backend/.venv/Scripts/python.exe -m pytest -q`

Frontend:

- `pnpm build`
- preview flow: `/` -> `/task` -> `/chat`
- desktop and mobile screenshot check.

Database:

- `pnpm supabase:reset`
- verify migration comments and seed conditions.
