# Backend Architecture

Updated: 2026-06-08

This document is the maintenance baseline for the Histosphere FastAPI backend. Update it whenever an API, data table, prompt module, or experiment flow changes.

## Backend Goal

The backend supports a thesis prototype that combines Error-Based Learning (EBL) with AI historical persona role-play.

V1 implements this flow:

```text
input historical event
-> fetch Wikipedia zh/en material
-> create event workspace
-> generate editable task / cloze-style prompt
-> generate 1-3 historical personas
-> learner submits task
-> LLM produces simple judgement
-> unlock conversation
-> chat policy follows 2x2 experiment condition
```

RAG is intentionally postponed. The backend stores Wikipedia sources and keeps `knowledge_chunks` as an extension point, but V1 does not write chunks, create embeddings, index vectors, or retrieve vector sources.

## Runtime Architecture

```text
backend/
  main.py
  app/
    main.py                  # FastAPI app factory
    api/
      deps.py                # dependency accessors + admin key guard
      v1/
        api.py               # router aggregation
        endpoints/
          admin.py
          chat.py
          conditions.py
          conversations.py
          events.py
          personas.py
          stats.py
          tasks.py
    core/
      config.py              # .env loading, CORS, repository selection
    crud/
      protocols.py           # repository contract
    db/
      in_memory.py           # deterministic tests/local fallback
      supabase_repository.py # PostgREST runtime repository
    models/
      domain.py              # Pydantic domain models
    schemas/
      requests.py
      responses.py
    services/
      event_initialization_service.py
      task_service.py
      conversation_service.py
      chat_service.py
      event_service.py
      persona_service.py
      prompt_service.py
      rag_pipeline_service.py
    providers/
      wikipedia_provider.py
      llm/
        base.py
        stub_provider.py
```

Repository selection:

- `BACKEND_REPOSITORY=in_memory`: force fake/local repository.
- `BACKEND_REPOSITORY=supabase`: require Supabase settings.
- `BACKEND_REPOSITORY=auto`: use Supabase when `SUPABASE_URL` and service role key exist; otherwise use in-memory.

Supabase service role env names accepted:

- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_KEY_SERVICE_ROLE`
- `SUPABASE_KEY_service_role`

Admin authorization:

- Header: `x-admin-key`
- Env: `HISTOSPHERE_ADMIN_KEY`
- Default local value: `histosphere-local-admin`

## Feature Inventory

### Event Initialization

Purpose: create or reuse an event workspace and start an experiment session.

Input:

- `event_name`
- `condition_key`
- `rebuild`
- `user_id`

Output:

- `event_id`
- `session_id`
- `event`
- `task`
- `personas`
- `condition`

Important:

- This endpoint does not create a conversation.
- `century`, `start_year`, `end_year`, and `context` may remain `null`.
- Missing historical certainty should be shown as `不詳` or `待補` in UI, not fabricated in DB.

### Task Submit / Chat Unlock

Purpose: store learner response, run simple LLM judgement, create conversation, and write research logs.

Input:

- `task_id`
- `session_id`
- `response_payload`
- `user_id`

Output:

- `attempt_id`
- `conversation_id`
- `attempt`
- `judgement`
- `greeting`
- `history`
- `event`
- `task`
- `personas`
- `condition`

V1 judgement:

- `correct`
- `incorrect`
- `partial`
- `misconception_summary`

Detailed blank-level scoring remains postponed in `task_blanks` and `task_answers`.

### Chat

Purpose: generate a response according to the selected 2x2 condition.

Input:

- `conversation_id`
- `user_message`
- `history`
- `target_persona_id`

Output:

- `response`
- `message`
- `assistant_name`
- `selected_persona`
- `annotations`
- `related_events`
- `dynamic_context`
- `rag_sources`

Policy:

- No role-play conditions return `selected_persona: null` and `speaker_type: assistant`.
- Role-play conditions return a persona response and `speaker_type: persona`.
- EBL conditions use scaffolded response policy.
- Non-EBL conditions use direct-answer response policy.

### Persona Management

Purpose: create, edit, deactivate, and list historical personas.

Important fields:

- `sources`: traceable source notes used to generate or verify the persona.
- `prompt_profile`: teacher-editable context-engineering settings, not the final assembled prompt.
- `active`: whether this persona appears in chat.
- `sort_order`: display/default ordering within the event.
- `revision_state`: `llm_generated`, `teacher_modified`, or `manual`.

### Prompt Modules

Current modules in `PromptService`:

- `condition_policy`: direct vs scaffold behavior.
- `event_context`: canonical event facts and nullable metadata.
- `learner_task`: task response and LLM judgement.
- `source_context`: currently notes RAG disabled; future source snippets can enter here.
- `speaker_context`: generic assistant vs historical persona.
- `deliberate_error_slot`: reserved, disabled by default.

## 2x2 Condition Matrix

| condition_key | EBL | Role-play | agent_mode | response_policy | Behavior |
|---|---:|---:|---|---|---|
| `no_ebl_no_roleplay` | no | no | `generic` | `direct` | ChatGPT-style direct answer. |
| `ebl_no_roleplay` | yes | no | `generic` | `scaffold` | Generic tutor guides thinking, argumentation, and source interpretation. |
| `no_ebl_roleplay` | no | yes | `persona` | `direct` | Persona gives immersive direct answer. |
| `ebl_roleplay` | yes | yes | `persona` | `scaffold` | Persona uses learner misconceptions to guide historical thinking. |

## API Contract

### `GET /health`

Purpose: backend health check.

Response:

```json
{ "status": "ok" }
```

### `GET /api/conditions`

Purpose: list active 2x2 experiment conditions.

Response: `ExperimentCondition[]`

Error cases:

- None expected in normal operation.

Frontend caller:

- `pages/index.vue`

### `POST /api/event/check`

Purpose: check whether an event workspace already exists.

Request body:

```json
{ "event_name": "諾曼第登陸" }
```

Response:

```json
{ "exists": true }
```

### `POST /api/event/initialize`

Purpose: create event/task/personas/session workspace.

Request body:

```json
{
  "event_name": "諾曼第登陸",
  "condition_key": "ebl_roleplay",
  "rebuild": false,
  "user_id": null
}
```

Response body:

```json
{
  "event_id": "...",
  "session_id": "...",
  "event": {},
  "task": {},
  "personas": [],
  "condition": {}
}
```

Error cases:

- `400`: empty event name.
- `404`: condition not found or inactive.
- `5xx`: Wikipedia/provider/Supabase failures.

Frontend caller:

- `pages/index.vue`

### `GET /api/events`

Purpose: list events with personas and latest task.

Response: `EventListItem[]`

Frontend caller:

- `pages/index.vue`

### `DELETE /api/event/{event_id}`

Purpose: delete event workspace and cascading data.

Response:

```json
{ "success": true }
```

### `POST /api/tasks/{task_id}/submit`

Purpose: submit task, judge response, create conversation, write research logs.

Request body:

```json
{
  "session_id": "...",
  "response_payload": {
    "answer_text": "..."
  },
  "user_id": null
}
```

Response body:

```json
{
  "attempt_id": "...",
  "conversation_id": "...",
  "event": {},
  "task": {},
  "personas": [],
  "condition": {},
  "attempt": {},
  "judgement": {
    "result": "partial",
    "misconception_summary": "..."
  },
  "greeting": "...",
  "history": []
}
```

Error cases:

- `404`: task/session/event/condition not found.
- `400`: task does not belong to session event.

Frontend caller:

- `pages/task.vue`

### `POST /api/conversations`

Purpose: compatibility/manual conversation creation. Primary V1 flow should prefer task submit.

Request body:

```json
{
  "event_id": "...",
  "task_attempt_id": null,
  "session_id": null,
  "user_id": null
}
```

### `GET /api/conversations/{conversation_id}`

Purpose: reload chat page.

Response body:

```json
{
  "conversation_id": "...",
  "event": {},
  "personas": [],
  "messages": [],
  "condition": {},
  "task_attempt": {},
  "related_events": []
}
```

Frontend caller:

- `pages/chat.vue`

### `POST /api/chat`

Purpose: append learner message and generate assistant/persona response.

Request body:

```json
{
  "conversation_id": "...",
  "user_message": "這場事件的重要性是什麼？",
  "history": [],
  "target_persona_id": null
}
```

Response body:

```json
{
  "response": "...",
  "selected_persona": null,
  "assistant_name": "AI Tutor",
  "message": {},
  "annotations": [],
  "related_events": [],
  "dynamic_context": "...",
  "rag_sources": []
}
```

Frontend caller:

- `pages/chat.vue`

### Persona Endpoints

- `GET /api/personas?event_id=...`
- `POST /api/personas`
- `PATCH /api/personas/{persona_id}`
- `DELETE /api/personas/{persona_id}`
- `POST /api/personas/{persona_id}/regenerate_avatar` compatibility endpoint only.

### Admin Endpoints

All require `x-admin-key`.

- `GET /api/admin/snapshot`
- `PATCH /api/admin/tasks/{task_id}`
- `PATCH /api/admin/personas/{persona_id}`
- `PATCH /api/admin/conditions/{condition_id}`
- `GET /api/admin/research-logs?limit=200`

Frontend caller:

- `pages/admin.vue`

## Data Model

The active schema lives in:

- `supabase/migrations/202605130001_ebl_roleplay_schema.sql`
- `backend/migrations/001_ebl_roleplay_schema.sql`

### Core tables

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

### Postponed tables

- `knowledge_chunks`
- `task_blanks`
- `task_answers`

### Key comments

- `event_tasks.evaluation_payload`: V1 LLM judgement rubric/settings.
- `task_attempts.judgement_payload`: LLM result and misconception summary.
- `personas.prompt_profile`: teacher-editable persona/context engineering settings.
- `messages.metadata`: model/prompt/profile snapshots or research flags.
- `research_logs`: behavioral trace table, not a replacement for `messages`.

## RAG Pipeline Design

Planned pipeline:

1. Data Ingestion
   - Source: Wikipedia zh, Wikipedia en.
   - Output: `wiki_sources`.
   - Metadata: `page_url`, `language`, `title`, `retrieved_at`, `fetch_mode`.
2. Chunking
   - Output: `knowledge_chunks`.
   - Status: postponed.
3. Embedding
   - Provider: Gemini/OpenAI/local, pluggable.
   - Status: postponed.
4. Indexing
   - Future option: Supabase pgvector.
   - Status: postponed.
5. Retrieval
   - Future input: `conversation_id`, `user_message`, `persona_id`.
   - Future output: ranked `rag_sources`.
   - V1 output: empty list.

Design rule: do not mix zh/en source text into untraceable combined chunks.

## Research Logs

Current action types:

- `event_initialized`
- `task_answer_changed`
- `task_submitted`
- `conversation_started`
- `message_sent`
- `persona_response_generated`
- `assistant_response_generated`

Conversation content analysis should read `messages`.

Behavior/process analysis should read `research_logs`.

## Test Checklist

Backend:

- `backend/.venv/Scripts/python.exe -m pytest -q`

Current coverage:

- event initialize creates workspace but not conversation.
- task submit creates attempt, judgement, conversation, greeting, logs.
- 2x2 chat policy direct/scaffold and generic/persona.
- new message shape with `speaker_type`, `speaker_name`, `sequence_index`.
- admin key protection.
- Wikipedia summary/full provider modes.

Frontend:

- `pnpm build`
- Manual/Playwright flow:
  - `/` select condition and input event.
  - `/task` submit answer.
  - `/chat` send message.
  - role-play condition shows persona selector.
  - no-role-play condition hides persona selector.
  - mobile layout has no overlapping text.

## Maintenance Rules

- Every new `/api/...` endpoint must be added to this document.
- Every frontend `$fetch('/api/...')` must map to an API contract here.
- Every table or column change must update the Data Model section and migration comments.
- Every prompt module must document:
  - module name
  - purpose
  - input variables
  - output behavior
  - enabled/disabled default
- `deliberate_error_slot` remains disabled in V1.
- Future TODO items should be marked `implemented`, `postponed`, or `deprecated`.
