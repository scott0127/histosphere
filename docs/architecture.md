# Backend Architecture

Updated: 2026-06-25

This document is the maintenance baseline for the Histosphere FastAPI backend. It must be updated whenever the API contract, database schema, prompt modules, or experiment flow changes.

## Backend Goal

The backend supports a thesis prototype that combines Error-Based Learning (EBL) with AI historical persona role-play. See `system-design.md` for the full research design.

## Directory Structure

```text
backend/
├── main.py                 # Convenience entrypoint that re-exports app.main:app.
├── requirements.txt        # Python backend dependencies.
├── migrations/             # Backend-side SQL migration copies/reference files.
├── tests/                  # Pytest tests and test fixtures.
└── app/
    ├── main.py             # FastAPI app factory, dependency wiring, middleware, router registration.
    ├── __init__.py
    ├── api/                # HTTP API layer.
    │   ├── deps.py         # FastAPI dependency accessors and admin-key guard.
    │   └── v1/
    │       ├── api.py      # Versioned router aggregator.
    │       └── endpoints/  # Endpoint files grouped by API area.
    │           ├── admin.py
    │           ├── chat.py
    │           ├── conditions.py
    │           ├── conversations.py
    │           ├── events.py
    │           ├── personas.py
    │           ├── sessions.py
    │           ├── stats.py
    │           └── tasks.py
    ├── core/               # Global configuration and environment loading.
    │   └── config.py
    ├── crud/               # Repository protocols / persistence interfaces.
    │   └── protocols.py
    ├── db/                 # Repository implementations and database access.
    │   ├── in_memory.py
    │   └── supabase_repository.py
    ├── models/             # Pydantic domain models used inside the backend.
    │   └── domain.py
    ├── schemas/            # API request and response Pydantic schemas.
    │   ├── requests.py
    │   └── responses.py
    ├── seed/               # Reserved for seed data utilities (currently empty).
    ├── services/           # Business workflow orchestration.
    │   ├── event_initialization_service.py
    │   ├── task_service.py
    │   ├── conversation_service.py
    │   ├── chat_service.py
    │   ├── event_service.py
    │   ├── persona_service.py
    │   ├── prompt_service.py
    │   ├── rag_pipeline_service.py
    │   └── session_service.py
    ├── providers/          # External providers such as Wikipedia and LLM runtime.
    │   ├── wikipedia_provider.py
    │   └── llm/
    │       ├── base.py
    │       ├── factory.py
    │       ├── json_runner.py
    │       ├── litellm_provider.py
    │       └── structured.py
    └── utils/              # Small shared utility functions.
```

### Directory Notes

- `api/`: should stay thin. It validates HTTP input, calls services or repositories, and returns response schemas. Avoid placing business logic here.
- `core/`: contains process-wide settings. It should not import services or repositories.
- `crud/`: currently only defines `RepositoryProtocol`. This is acceptable, but the name is slightly misleading because it is not classic CRUD helpers. If this grows, consider renaming it to `repositories/` or `ports/`.
- `db/`: contains concrete persistence adapters such as `SupabaseRepository` and `InMemoryRepository`. This layer should satisfy `RepositoryProtocol`.
- `models/`: currently means Pydantic domain models, not SQLAlchemy ORM models. This works because the project does not use an ORM; database access goes through the Supabase PostgREST repository.
- `schemas/`: contains HTTP request/response shapes only. Do not put internal domain rules here.
- `services/`: contains application workflows such as event initialization, task submission, chat, prompt assembly, session management, and RAG extension points.
- `providers/`: wraps external systems. Provider-specific schemas can live near the provider, as `providers/llm/structured.py` does now.
- `utils/`: should stay small and dependency-light. If a utility starts holding business rules, move it into a service.
- `seed/`: reserved for seed data utilities. Currently empty.

## Runtime Configuration

Repository selection:

- `BACKEND_REPOSITORY=in_memory`: tests only, requires `ALLOW_IN_MEMORY_REPOSITORY=true`.
- `BACKEND_REPOSITORY=supabase`: require Supabase settings.
- `BACKEND_REPOSITORY=auto`: deprecated for runtime; do not use for local development.

Runtime rule: event/task/persona data must be written to Supabase. In-memory repository is forbidden outside explicit tests.

LLM runtime rule: the backend uses `LLM_PROVIDER=litellm` only. `StubLLMProvider` has been removed from runtime so local development and prototype testing use the same provider path as production-like execution. LiteLLM can route to Gemini, OpenAI/GPT, local OpenAI-compatible models, or a GPT OAuth proxy by changing environment variables.

LLM configuration:

- `LLM_PROVIDER=litellm`
- `LLM_MODEL=gemini/gemini-2.5-flash`
- `LLM_API_BASE`: optional; use for local OpenAI-compatible servers or GPT OAuth proxy.
- `LLM_API_KEY`: optional generic key; provider-specific keys such as `GEMINI_API_KEY` or `OPENAI_API_KEY` may also be read by LiteLLM.
- `LLM_TEMPERATURE=0.3`
- `LLM_MAX_OUTPUT_TOKENS=4096`
- `LLM_TIMEOUT_SECONDS=60`

Event material reuse rule: one canonical historical event owns exactly one reusable material set. `events`, `wiki_sources`, `event_tasks`, and the primary `personas` row belong to the event, not to an experiment condition. Selecting a different condition only creates a new `experiment_session`, `task_attempt`, `conversation`, `messages`, and `research_logs`.

Accepted Supabase service role environment variable names:

- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_KEY`
- `SUPABASE_KEY_SERVICE_ROLE`
- `SUPABASE_KEY_service_role`

Admin authorization:

- Header: `x-admin-key`
- Env: `HISTOSPHERE_ADMIN_KEY`
- Default local value: `histosphere-local-admin`

## Feature Inventory

### Event Initialization

Purpose: create or reuse an event workspace and start an experiment session.

Input: `event_name`, `condition_key`, `rebuild`, `user_id`

Output: `event_id`, `session_id`, `event`, `task`, `personas`, `condition`

Important rules:

- This endpoint does not create a conversation.
- V1 creates or reuses one primary historical persona per event.
- Event profile, prototype task, and primary persona are generated through LiteLLM when no teacher/manual material exists.
- `century`, `start_year`, `end_year`, and `context` may remain `null`.

### Task Submit / Chat Unlock

Purpose: store learner response, run simple LLM judgement, create conversation, and write research logs.

Input: `task_id`, `session_id`, `response_payload`, `user_id`

Output: `attempt_id`, `conversation_id`, `attempt`, `judgement`, `greeting`, `history`, `event`, `task`, `personas`, `condition`

V1 judgement values: `correct`, `incorrect`, `partial`.

### Chat

Purpose: generate a response according to the selected 2x2 condition.

Input: `conversation_id`, `user_message`, `history`, `target_persona_id`

Output: `response`, `message`, `assistant_name`, `selected_persona`, `annotations`, `related_events`, `dynamic_context`, `rag_sources`

### Prompt Modules

Current modules in `PromptService`:

- `condition_policy`: direct vs scaffold behavior.
- `event_context`: canonical event facts and nullable metadata.
- `learner_task`: task response and LLM judgement.
- `source_context`: currently notes RAG disabled; future source snippets can enter here.
- `speaker_context`: generic assistant vs historical persona.
- `deliberate_error_slot`: reserved and disabled by default.

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

Response: `{ "status": "ok" }`

---

### `GET /api/conditions`

Purpose: list active 2x2 experiment conditions.

Response: `ExperimentCondition[]`

Frontend caller: `pages/index.vue`

---

### `POST /api/event/check`

Purpose: check whether an event workspace already exists.

Request body: `{ "event_name": "..." }`

Response: `{ "exists": true }`

---

### `POST /api/event/initialize`

Purpose: create an event/task/personas/session workspace.

Request body:

```json
{
  "event_name": "Normandy landings",
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

Error cases: `400` empty event name, `404` condition not found, `5xx` Wikipedia/provider/Supabase failures.

Frontend caller: `pages/index.vue` through `useExperimentSession`

---

### `GET /api/events`

Purpose: list events with personas and latest task.

Response: `EventListItem[]`

Frontend caller: `pages/index.vue`

---

### `DELETE /api/event/{event_id}`

Purpose: delete event workspace and cascading data.

Response: `{ "success": true }`

---

### `POST /api/event/{event_id}/regenerate-background`

Purpose: regenerate event background image or metadata.

---

### `PATCH /api/tasks/{task_id}/draft`

Purpose: save task draft without full submit.

Response: `TaskDraftResponse`

---

### `POST /api/tasks/{task_id}/submit`

Purpose: submit task, judge response, create conversation, and write research logs.

Request body:

```json
{
  "session_id": "...",
  "response_payload": { "answer_text": "..." },
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
  "judgement": { "result": "partial", "misconception_summary": "..." },
  "greeting": "...",
  "history": []
}
```

Error cases: `404` task/session/event/condition not found, `400` task does not belong to session event.

Frontend caller: `pages/sessions/[sessionId]/task.vue` through `useTaskGate`, then `/conversations/[conversationId]`

---

### `POST /api/conversations`

Purpose: compatibility/manual conversation creation. The primary V1 flow should prefer task submit.

---

### `GET /api/conversations/{conversation_id}`

Purpose: reload the conversation page.

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

Frontend caller: `pages/conversations/[conversationId].vue` through `useConversationSession`

---

### `POST /api/chat`

Purpose: append learner message and generate assistant/persona response.

Request body:

```json
{
  "conversation_id": "...",
  "user_message": "Why was this event important?",
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

Frontend caller: `useConversationSession`

---

### Persona Endpoints

- `GET /api/personas?event_id=...`
- `POST /api/personas`
- `PATCH /api/personas/{persona_id}`
- `DELETE /api/personas/{persona_id}`
- `POST /api/personas/{persona_id}/regenerate_avatar` (compatibility endpoint only)

---

### Session Endpoints

- `GET /api/sessions/progress` — returns user progress across sessions.
- `GET /api/sessions/{session_id}/state` — reload session state for `/sessions/[sessionId]/task` refresh safety.

Response: `UserProgressResponse` / `SessionStateResponse`

---

### Stats Endpoints

- `POST /api/stats/view-count/increment` — increment page/event view counter.

---

### Admin Endpoints

All admin endpoints require `x-admin-key`.

- `GET /api/admin/snapshot`
- `PATCH /api/admin/events/{event_id}`
- `PATCH /api/admin/tasks/{task_id}` — validates structured `display_text` blank tokens against `evaluation_payload.questions` before saving. Validation errors return `422` with `detail.message` and `detail.issues[]`.
- `PATCH /api/admin/personas/{persona_id}`
- `PATCH /api/admin/conditions/{condition_id}`
- `GET /api/admin/research-logs?limit=200`

Frontend caller: `pages/admin.vue`

## Data Model

The active schema lives in:

- `supabase/migrations/202605130001_ebl_roleplay_schema.sql`
- `backend/migrations/001_ebl_roleplay_schema.sql`

See `supabase-schema.md` for the full table/column/FK/index reference.

Core tables: `events`, `wiki_sources`, `experiment_conditions`, `experiment_sessions`, `event_tasks`, `task_attempts`, `personas`, `conversations`, `messages`, `research_logs`.

Postponed tables: `knowledge_chunks`, `task_blanks`, `task_answers`.

Key comments:

- `event_tasks.evaluation_payload`: V1 LLM judgement rubric/settings.
- `task_attempts.judgement_payload`: LLM result and misconception summary.
- `personas.prompt_profile`: teacher-editable persona/context engineering settings.
- `messages.metadata`: model/prompt/profile snapshots or research flags.
- `research_logs`: behavioral trace table, not a replacement for `messages`.

## Research Logs

Current action types:

- `event_initialized`
- `event_updated`
- `task_answer_changed`
- `task_updated`
- `task_submitted`
- `conversation_started`
- `message_sent`
- `persona_response_generated`
- `assistant_response_generated`

Conversation content analysis should read `messages`. Behavior/process analysis should read `research_logs`.

## Test Checklist

Backend:

```powershell
backend/.venv/Scripts/python.exe -m pytest -q
```

Current coverage:

- event initialize creates workspace but not conversation.
- task submit creates attempt, judgement, conversation, greeting, and logs.
- task draft save persists recoverable in-progress attempts.
- admin task update rejects corrupt story tokens/questions and logs `task_updated` on success.
- session state reload returns event/task/personas/condition/attempt/conversation id for `/sessions/[sessionId]/task`.
- session progress returns per-user event/condition status for homepage recovery.
- invalid UUID route parameters return validation errors instead of backend 500s.
- 2x2 chat policy direct/scaffold and generic/persona.
- message shape with `speaker_type`, `speaker_name`, and `sequence_index`.
- admin key protection.
- Wikipedia summary/full provider modes.

Frontend:

- `pnpm test:frontend:unit`
- `pnpm build`
- Manual/Playwright flow: `/` → `/sessions/[sessionId]/task` → `/conversations/[conversationId]`

Current frontend unit coverage:

- `utils/histosphereApi.ts` endpoint contract calls for public event data, admin snapshot/writes, event initialization, session progress/state, task draft/submit, conversation load, chat send, and event delete.
- `useStudentTask` pure task logic: question normalization, inline story segment rendering, answer completeness, response payload serialization, boolean answer text, and deterministic participant UUID.
- `utils/adminWorkspaceState.ts` admin state helpers: editable JSON map generation, 01-04 condition ordering, condition labels, and event year range formatting.

Frontend orchestration boundaries:

- `useExperimentSession` owns participant/session initialization, progress recovery, and route handoff to task/conversation.
- `useEventLibrary` owns homepage condition/event list loading, refresh, lookup, and deletion.
- `useTaskGate` owns task state reload, draft autosave, submit, and route handoff to conversation.
- `useConversationSession` owns conversation reload and chat send.
- `useAdminWorkspace` owns admin snapshot loading, editable task/persona JSON maps, selected event/condition state, and admin save flows.

## Maintenance Rules

- Every new `/api/...` endpoint must be added to this document.
- Every frontend `$fetch('/api/...')` must map to an API contract here.
- Every table or column change must update the Data Model section and `supabase-schema.md`.
- Every prompt module must document module name, purpose, input variables, output behavior, and enabled/disabled default.
- `deliberate_error_slot` remains disabled in V1.
- Future TODO items should be marked `implemented`, `postponed`, or `deprecated`.
