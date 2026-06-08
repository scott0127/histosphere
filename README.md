# Histosphere

Histosphere is a thesis prototype for combining Error-Based Learning (EBL) with AI historical persona role-play.

Current V1 flow:

```text
select 2x2 experiment condition
-> input historical event
-> fetch Wikipedia zh/en
-> generate event workspace, task, personas
-> learner submits task
-> backend judges correct / incorrect / partial
-> unlock chat
-> chat follows selected condition policy
```

## Current Scope

Implemented:

- Nuxt frontend with `/`, `/task`, `/chat`, `/admin`.
- FastAPI backend under `backend/app`.
- Local deterministic in-memory repository for tests.
- Supabase PostgREST repository for local/cloud runtime.
- Local Supabase migration schema.
- Wikipedia provider with `summary` and `full` modes.
- 2x2 experiment conditions:
  - Without EBL + Without AI Role-play
  - With EBL + Without AI Role-play
  - Without EBL + With AI Role-play
  - With EBL + With AI Role-play
- Admin key dashboard for conditions, task text, persona prompt profile, and research logs.

Postponed:

- RAG chunking / embeddings / vector search.
- `task_blanks` and `task_answers` scoring.
- controlled AI-generated inaccuracies.
- Supabase Auth / RLS cleanup.
- production LLM provider integration.

## Tech Stack

- Frontend: Nuxt 4, Vue 3, Tailwind CSS, Nuxt Icon.
- Backend: Python, FastAPI, Pydantic, httpx.
- Database: Supabase Postgres.
- Tests: pytest.

## Environment

Copy `.env.example` to `.env` and set values as needed.

Important backend variables:

```env
BACKEND_REPOSITORY=auto
HISTOSPHERE_ADMIN_KEY=change-this-local-admin-key
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SERVICE_ROLE_KEY=...
```

Repository modes:

- `BACKEND_REPOSITORY=in_memory`: local fake repository.
- `BACKEND_REPOSITORY=supabase`: require Supabase.
- `BACKEND_REPOSITORY=auto`: use Supabase if configured, otherwise in-memory.

## Local Development

Install frontend dependencies:

```powershell
pnpm install
```

Create backend venv:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run both frontend and backend:

```powershell
pnpm dev:full
```

Or run manually:

```powershell
# Terminal 1
cd backend
$env:BACKEND_REPOSITORY="in_memory"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2
$env:NUXT_API_URL="http://127.0.0.1:8000"
pnpm dev --host 127.0.0.1 --port 3000
```

Open:

- Frontend: `http://127.0.0.1:3000`
- Backend health: `http://127.0.0.1:8000/health`
- Admin UI: `http://127.0.0.1:3000/admin`

## Local Supabase

Start Supabase:

```powershell
pnpm supabase:start
```

Reset local database with migrations:

```powershell
pnpm supabase:reset
```

Check status:

```powershell
pnpm supabase:status
```

Migration files:

- `supabase/migrations/202605130001_ebl_roleplay_schema.sql`
- `backend/migrations/001_ebl_roleplay_schema.sql`

## Tests

Backend:

```powershell
cd backend
$env:BACKEND_REPOSITORY="in_memory"
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend build:

```powershell
pnpm build
```

## API Summary

Core flow:

- `GET /api/conditions`
- `POST /api/event/initialize`
- `GET /api/events`
- `POST /api/tasks/{task_id}/submit`
- `GET /api/conversations/{conversation_id}`
- `POST /api/chat`

Admin:

- `GET /api/admin/snapshot`
- `PATCH /api/admin/tasks/{task_id}`
- `PATCH /api/admin/personas/{persona_id}`
- `PATCH /api/admin/conditions/{condition_id}`
- `GET /api/admin/research-logs`

All admin routes require:

```http
x-admin-key: <HISTOSPHERE_ADMIN_KEY>
```

## Documentation

- Backend contract: `docs/backend-architecture.md`
- System design: `docs/system-design-ebl-roleplay.md`
- Frontend audit: `docs/frontend-audit.md`

## Maintenance Rules

- Every API change must update `docs/backend-architecture.md`.
- Every schema change must update both migration files and column comments.
- Every prompt module change must update backend architecture docs.
- Every frontend `$fetch('/api/...')` should have a matching documented endpoint.
- RAG and controlled inaccuracies stay disabled until research design is finalized.
