# Histosphere System Design

Updated: 2026-06-25

Histosphere is a thesis prototype for studying how Error-Based Learning (EBL) and AI historical persona role-play can support historical thinking and AI literacy.

This document describes the system-level design, experimental conditions, frontend/backend responsibilities, postponed design questions, and recommended development order.

## Core Terms

The following terms should be used consistently across documentation and UI:

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
-> generate one primary historical persona
-> learner submits task
-> LLM judges correct / incorrect / partial
-> conversation unlocks
-> chat follows selected condition policy
```

## 2x2 Experiment Design

| | Without EBL | With EBL |
|---|---|---|
| Without AI Role-play | Learner completes a task, then uses a generic ChatGPT-style assistant. The assistant may directly answer. | Learner completes a task, then uses a generic tutor chatbot. The tutor guides thinking, argumentation, and source interpretation before giving a direct answer. |
| With AI Role-play | Learner completes a task, then chats with AI historical personas. The persona can give an immersive direct answer. | Learner completes a task, then chats with AI historical personas. The persona uses task misconceptions to scaffold historical thinking and does not directly give the answer before self-correction. |

Condition keys:

- `no_ebl_no_roleplay`
- `ebl_no_roleplay`
- `no_ebl_roleplay`
- `ebl_roleplay`

The abandoned 1x3 condition design is not part of the current system.

Condition selection changes interaction policy only. For the same canonical historical event, all four conditions must reuse the same `events`, `wiki_sources`, `event_tasks`, and primary `personas` data. Generic-chat conditions do not create separate persona resources; they simply present the response as a generic assistant. EBL conditions use scaffold prompts; non-EBL conditions do not. Each learner/session receives isolated `task_attempts`, `conversations`, `messages`, and `research_logs`.

## Implemented Milestone

Status: implemented in the current working tree.

Backend:

- FastAPI app structure under `backend/app`.
- In-memory repository for deterministic tests.
- Supabase PostgREST repository for local/cloud runtime.
- Wikipedia provider with `summary` and `full` fetch modes.
- Event initialization returns event/task/primary persona/session, not conversation.
- Learner initialization enforces Auth-to-participant mapping and assigned condition; only Admin can create new event materials.
- Event material uses reversible archive/restore instead of learner-facing permanent deletion.
- Task submit persists a processing attempt and returns `202`; judgement, conversation and greeting complete asynchronously behind a polling endpoint.
- Chat service switches generic/persona and direct/EBL behavior from condition and loads bounded multi-turn history from DB messages.
- `persona_prompt_v1` and canonical prompt modules are shared by runtime, Admin preview and non-persisting Admin dry-run.
- Session timer is disabled by default and may be started/cancelled by Admin; backend enforces expiry.
- Research logs record event/task/conversation/message actions.
- Admin key endpoints manage conditions, tasks, personas, events, and logs.
- Session progress and state reload endpoints.
- Task draft save endpoint.

Frontend:

- `/` event library and condition start flow.
- `/sessions/[sessionId]/task` required task submission gate.
- `/conversations/[conversationId]` generic/persona-aware chat UI.
- `/admin` admin-key dashboard with structured task editor.
- `/tutorial` legacy tutorial/demo (candidate for rewrite into experiment onboarding).
- `/profile`, `/auth/*` Supabase auth pages (keep only if participant accounts are required).

## Backend Responsibilities

### Event Workspace

Generate or reuse:

- `events`
- `wiki_sources`
- `event_tasks`
- `personas`
- `experiment_sessions`

The backend should not fabricate uncertain historical metadata. Store nullable fields as `null`.

Learner runtime can only reuse an existing, non-archived event. A valid Admin override is required to generate new event/task/persona material. Archiving sets `events.archived_at`; restoring clears it, so related sessions and research data are never removed as part of ordinary event management.

Each event should have one primary historical persona in V1. Runtime generation uses LiteLLM so prototype testing follows the same provider path as production-like execution. Formal experiment material should still be reviewed or edited by teacher/admin users. If the teacher has not specified the persona, the LLM provider should select the most historically central or representative figure for the event.

### Task Gate

V1 stores all learner response data in:

- `task_attempts.response_payload`

V1 task display is story-first. `event_tasks.display_text` may include inline blank tokens such as `{{blank:q-cause}}`. Each token maps to one item in `event_tasks.evaluation_payload.questions` through `blank_id` or `id`. This keeps blank-level scoring postponed while still allowing the frontend to render cloze, multiple-choice, true/false, and short-answer blanks inside the historical story.

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

Submission is asynchronous:

```text
POST submit -> 202 + attempt_id -> poll attempt -> submitted + conversation
                                   \-> failed (saved and retryable)
```

### Conversation

Conversation is created only after task submit.

Messages use:

- `speaker_type`: `learner`, `assistant`, `persona`
- `speaker_name`: display-name snapshot
- `sequence_index`: stable replay order

Each completion loads persisted conversation turns from `messages` and fills a 16,000-character history budget from newest to oldest, with at most 1,600 characters per message. Generated-message metadata records prompt/profile hashes, module names, history message ids, actual provider/model, latency and provider-reported token usage.

### Admin

V1 admin uses a simple key:

- frontend page: `/admin`
- header: `x-admin-key`
- env: `HISTOSPHERE_ADMIN_KEY`

Admin can edit:

- condition settings
- event metadata (name, description, years, context, source summary)
- task text and evaluation payload
- persona profile and prompt profile
- persona active state

Admin can also archive/restore events, preview prompt modules, run a non-persisting prompt dry-run, and start/cancel an optional session timer.

## Frontend Responsibilities

### `/`

Purpose: start a research session.

Controls:

- 2x2 condition selector.
- existing event list.
- Admin-only historical event creation input.
- Admin archive confirmation; learners cannot create or archive event materials.

Output:

- starts an experiment session through `useExperimentSession`.
- navigates to `/sessions/[sessionId]/task`.

### `/sessions/[sessionId]/task`

Purpose: learner task gate.

Controls:

- task display text with inline story blanks.
- optional original story text.
- cloze, multiple-choice, true/false, or short-answer controls rendered from `evaluation_payload.questions`.
- submit button.

Output:

- calls `POST /api/tasks/{task_id}/submit` and receives `202 Accepted`.
- polls `GET /api/tasks/attempts/{attemptId}` while the transition screen explains the LLM wait.
- stores the final task/conversation payload when processing reaches `submitted`.
- navigates to `/conversations/[conversationId]`.

### `/conversations/[conversationId]`

Purpose: conversation after task completion.

Controls:

- message list.
- input box.
- persona selector only when `condition.roleplay_enabled = true`.
- task judgement side panel.
- optional session countdown banner when Admin has enabled a timer.

### `/admin`

Purpose: teacher/researcher configuration.

Controls:

- admin key input.
- condition editor.
- event editor with metadata fields.
- structured task editor with story-first blank tokens, undo/redo, validation, and learner preview.
- persona `prompt_profile` editor (advanced JSON).
- read-only backend prompt preview for the selected event and condition.
- non-persisting prompt dry-run using the actual provider.
- event archive/restore and per-session timer controls.
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

Needs teacher/research discussion:

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

RAG is explicitly deferred. Runtime must say retrieval is disabled and must not imply citations were retrieved.

Future design:

```text
Data ingestion
-> Chunking
-> Embedding
-> Indexing
-> Retrieval
```

Potential future providers:

- Gemini embeddings
- OpenAI embeddings
- local embedding model
- Supabase pgvector

### Material Version Lock

Each new or restarted Session records an event/task/condition/persona material snapshot, and every formal LLM call records the exact Prompt/modules used. SHA-256 verification plus Admin JSON/CSV export supports audit and replay without a new version table. A complete draft/readiness/publish platform and visual rollback remain deferred.

### Unspecified Requirements

The earlier numbered requirements 6 and 8 remain deferred because their behavior and acceptance criteria were not fully specified. If item 8 refers to RAG, the RAG deferral above applies.

### Controlled AI-Generated Inaccuracies

V1 only reserves:

- `personas.prompt_profile.deliberate_error_enabled`
- `PromptService._deliberate_error_slot`

It is disabled by default because deliberate error design may move to a later experimental phase.

## Test Checklist

Backend:

```powershell
backend/.venv/Scripts/python.exe -m pytest -q
```

Frontend:

```powershell
pnpm test:frontend:unit
pnpm build
```

Preview flow:

```text
/ -> /sessions/[sessionId]/task -> /conversations/[conversationId]
```

Database:

```powershell
pnpm exec supabase status
pnpm exec supabase migration list --local
```

Do not use `supabase db reset` against a database containing local research data. Migration/reset smoke tests must run against an isolated disposable database.
