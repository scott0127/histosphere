# Histosphere System Design

Updated: 2026-08-20

Histosphere is a thesis prototype for studying how Error-Based Learning (EBL) and AI historical persona role-play can support historical thinking. Possible transfer to AI literacy is deferred exploratory work, not an assumed outcome.

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
Admin creates and reviews historical event / Task / one active persona
-> Admin locks the material
-> Admin assigns an ordered Condition list to a Participant
-> learner logs in with the bound Supabase Auth account
-> system shows only the active or next assigned Condition
-> learner submits task
-> LLM judges the response asynchronously
-> conversation unlocks
-> chat follows selected condition policy
-> fixed five-minute countdown completes the stage
-> learner explicitly enters the next stage
```

## 2x2 Experiment Design

| | Without EBL | With EBL |
|---|---|---|
| Without AI Role-play | Learner completes a task, then uses a generic Standard Chat assistant. It answers event-related requests naturally without running an EBL sequence. | Learner completes a task, then uses a generic Historical EBL assistant that works through one Task error at a time. |
| With AI Role-play | Learner completes a task, then uses the same Standard Chat policy rendered as one fixed historical persona. | Learner receives the same Historical EBL act as the generic EBL condition, rendered in the fixed persona's first-person voice. |

Condition keys:

- `no_ebl_no_roleplay`
- `ebl_no_roleplay`
- `no_ebl_roleplay`
- `ebl_roleplay`

The abandoned 1x3 condition design is not part of the current system.

Condition assignment changes interaction policy only. Admin stores the permitted Conditions in `participants.condition_list`; its array order is the formal execution order. The learner cannot select another Condition, skip the next item, or start a new one while a formal Session is active. For the same canonical historical event, all four conditions reuse the same `events`, `wiki_sources`, `event_tasks`, and active `personas` material. Generic-chat conditions do not create separate persona resources; they present the response as a generic assistant. EBL conditions use scaffold prompts; non-EBL conditions do not. Each learner/session receives isolated `task_attempts`, `conversations`, `messages`, and `research_logs`.

## Implemented Milestone

Status: implemented in the current working tree.

Backend:

- FastAPI app structure under `backend/app`.
- In-memory repository for deterministic tests.
- Supabase PostgREST repository for local/cloud runtime.
- Wikipedia provider with `summary` and `full` fetch modes.
- Event initialization returns event/task/primary persona/session, not conversation.
- Learner initialization enforces Auth-to-participant mapping, ordered Condition assignment and active-Session resume; only Admin can create or lock new event materials.
- Event material uses reversible archive/restore instead of learner-facing permanent deletion.
- Task submit persists a processing attempt and returns `202`; judgement, conversation and greeting complete asynchronously behind a polling endpoint.
- Chat service switches generic/persona and Standard Chat/Historical EBL behavior from condition and loads bounded multi-turn history from DB messages.
- `persona_prompt_v1` and canonical prompt modules are shared by runtime, Admin preview and non-persisting Admin dry-run.
- A fixed five-minute timer starts when Chat becomes ready, survives refresh, and is enforced by the backend; Admin may reset it.
- Research logs record event/task/conversation/message actions.
- Admin key endpoints manage conditions, tasks, personas, events, and logs.
- Session progress and state reload endpoints.
- Task draft save endpoint.

Frontend:

- `/` event library and current assigned Condition start/resume flow.
- `/sessions/[sessionId]/task` required task submission gate.
- `/conversations/[conversationId]` generic/persona-aware chat UI.
- `/admin` admin-key dashboard with structured task editor.
- `/profile`, `/auth/*` Supabase Auth pages for pre-created participant accounts.

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

Each event may contain multiple archived/inactive persona records but can have at most one active persona. Learners cannot choose or switch persona; Admin controls the single active figure. Runtime generation uses LiteLLM so prototype testing follows the same provider path as production-like execution. Formal experiment material must be reviewed and locked by Admin before learners can start it.

### Task Gate

V1 stores all learner response data in:

- `task_attempts.response_payload`

V1 task display is story-first. `event_tasks.display_text` may include inline blank tokens such as `{{blank:q-cause}}`. Each token maps to one item in `event_tasks.evaluation_payload.questions` through `blank_id` or `id`, allowing the frontend to render cloze, multiple-choice, true/false, and short-answer controls inside the historical story.

V1 stores LLM judgement in:

- `task_attempts.judgement_payload`

Expected judgement shape:

```json
{
  "result": "partial",
  "misconception_summary": "...",
  "feedback": "...",
  "question_results": [
    {
      "question_id": "q01",
      "correctness": "partial",
      "learner_answer": "..."
    }
  ]
}
```

Objective questions are judged by backend rules; open `short_answer` questions are judged by the configured LLM. The only per-question statuses are `correct`, `partial`, `incorrect`, and `unanswered`. These values build the later learning queue and are not Historical Thinking outcome scores.

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

Admin can also archive/restore and lock events, manage the single active persona, assign and reorder each Participant's Conditions, preview prompt modules, run a non-persisting prompt dry-run, reset a Session countdown, and restart a Session without deleting its prior research records.

## Frontend Responsibilities

### `/`

Purpose: start a research session.

Controls:

- current assigned 01–04 Condition code; the underlying experimental label remains hidden from learners.
- existing locked event list with the introduction text hidden.
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
- fixed active persona identity and portrait when `condition.roleplay_enabled = true`; no learner selector.
- task judgement side panel.
- fixed five-minute countdown, expired-stage alert and explicit next-stage button.

### `/admin`

Purpose: teacher/researcher configuration.

Controls:

- admin key input.
- condition editor.
- event editor with metadata fields.
- structured task editor with story-first blank tokens, undo/redo, validation, and learner preview.
- persona `prompt_profile` editor (advanced JSON).
- Participant Auth binding plus ordered Condition assignment controls.
- read-only backend prompt preview for the selected event and condition.
- non-persisting prompt dry-run using the actual provider.
- event archive/restore/material lock and per-session timer reset/restart controls.
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

Existing but not used by the current response bundle:

- `knowledge_chunks`
- `task_blanks`
- `task_answers`

## Postponed Design Questions

### `task_blanks` and `task_answers`

V1 keeps question definitions in `event_tasks.evaluation_payload.questions[]`, learner answers in `task_attempts.response_payload`, and diagnostic results in `task_attempts.judgement_payload`. The normalized legacy tables are not required for the current single-study workflow and should not be expanded without a concrete query or scale requirement.

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

Implemented minimum scope: Admin locks reviewed event material before learner use; each new or restarted Session records an event/task/condition/persona snapshot, and every formal LLM call records the exact Prompt/modules used. SHA-256 verification plus Admin JSON/CSV export supports audit and replay without a new version table. A complete draft/readiness/publish platform and visual rollback remain deferred.

### Research Decisions Still Open

The following change research semantics and require agreement with the supervisor before implementation:

- Historical EBL completion: whether `RESOLVED` requires a correct answer plus evidence/reason/reflection, and what happens after unsuccessful D4 support.
- Treatment of `unanswered` Task items in the later error queue.
- Pre/post-test and Historical Thinking measurement: instrument, timing, dimensions, scoring, missing data and participant-code merge protocol.
- Final events, Task content, experiment timing, counterbalancing and engagement measures.

Disclosure D0/D1 currently uses the approved minimum policy: private answer/evidence context is available for progress judgement, while learner-visible output is restricted and audited. Detailed pending decisions are maintained only in `research-experiment-backlog.md`.

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
