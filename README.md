# Histosphere

Updated: 2026-06-09

## English

Histosphere is a master's thesis prototype that combines Error-Based Learning (EBL) with AI historical persona role-play.

The current V1 system supports a full 2x2 experimental design:

- Without EBL + Without AI Role-play
- With EBL + Without AI Role-play
- Without EBL + With AI Role-play
- With EBL + With AI Role-play

The core learning flow is:

```text
select experiment condition
-> input a historical event
-> fetch Wikipedia zh/en sources
-> create an event workspace
-> generate an editable cloze-style task
-> generate one primary historical persona
-> learner submits the task
-> backend produces a simple correct / partial / incorrect judgement
-> unlock conversation
-> chat follows the selected experiment condition
```

### Current Scope

Implemented:

- Nuxt frontend pages: `/`, `/task`, `/chat`, `/admin`.
- FastAPI backend under `backend/app`.
- Deterministic in-memory repository for tests only.
- Supabase PostgREST repository for local or cloud runtime.
- Supabase migration schema for the EBL + role-play design.
- Wikipedia provider with `summary` and `full` fetch modes.
- Task gate before chat.
- One primary historical persona per event. Runtime generation uses LiteLLM, and teachers can edit the generated persona before formal experiment use.
- Condition-based chat policy for generic chatbot vs historical persona and direct answer vs EBL scaffold.
- Admin-key dashboard for experiment conditions, task text, persona profile, persona `prompt_profile`, and research logs.

Postponed:

- RAG chunking, embeddings, indexing, and vector retrieval.
- `task_blanks` and `task_answers` scoring.
- Controlled AI-generated inaccuracies.
- Supabase Auth and RLS cleanup.
- Task scoring normalization and formal research export.

### Tech Stack

- Frontend: Nuxt 4, Vue 3, Tailwind CSS, Nuxt Icon.
- Backend: Python, FastAPI, Pydantic, httpx, LiteLLM.
- Database: Supabase Postgres.
- Tests: pytest.

### Environment

Copy `.env.example` to `.env` and set values as needed.

Important backend variables:

```env
BACKEND_REPOSITORY=auto
HISTOSPHERE_ADMIN_KEY=change-this-local-admin-key
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SERVICE_ROLE_KEY=...
```

Repository modes:

- `BACKEND_REPOSITORY=in_memory`: tests only, requires `ALLOW_IN_MEMORY_REPOSITORY=true`.
- `BACKEND_REPOSITORY=supabase`: require Supabase settings.
- `BACKEND_REPOSITORY=auto`: deprecated for runtime; do not use for local development.

### Local Development

Install frontend dependencies:

```powershell
pnpm install
```

Create backend virtual environment:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run both frontend and backend:

```powershell
pnpm dev:full
```

This starts Nuxt and FastAPI with local Supabase. Before starting, it frees any existing processes listening on ports `3000` and `8000`. Runtime in-memory mode is forbidden. Docker Desktop must already be running; the script can start the local Supabase stack when Docker is ready.

To manually clean up dev server ports without starting the app:

```powershell
pnpm dev:cleanup
```

Or run them manually:

```powershell
# Terminal 1
cd backend
$env:BACKEND_REPOSITORY="supabase"
$env:SUPABASE_URL="http://127.0.0.1:54321"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2
$env:NUXT_API_URL="http://127.0.0.1:8000"
pnpm dev --host 127.0.0.1 --port 3000
```

Open:

- Frontend: `http://127.0.0.1:3000`
- Backend health: `http://127.0.0.1:8000/health`
- Admin UI: `http://127.0.0.1:3000/admin`

### Local Supabase

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

### Tests

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

### API Summary

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

### Documentation

- Backend contract: `docs/backend-architecture.md`
- Backend directory structure: `docs/backend-directory-structure.md`
- System design: `docs/system-design-ebl-roleplay.md`
- Frontend audit: `docs/frontend-audit.md`

### Maintenance Rules

- Documentation must be organized as a complete English version followed by a complete Traditional Chinese version.
- Every API change must update `docs/backend-architecture.md`.
- Every schema change must update both migration files and column comments.
- Every prompt module change must update backend architecture docs.
- Every frontend `$fetch('/api/...')` should have a matching documented endpoint.
- RAG and controlled inaccuracies stay disabled until the research design is finalized.

## 中文版

Histosphere 是一個碩士論文 prototype，用來結合 Error-Based Learning (EBL) 與 AI historical persona role-play。

目前 V1 系統支援完整 2x2 實驗設計：

- Without EBL + Without AI Role-play
- With EBL + Without AI Role-play
- Without EBL + With AI Role-play
- With EBL + With AI Role-play

核心學習流程是：

```text
選擇實驗條件
-> 輸入歷史事件
-> 抓取中英文 Wikipedia 來源
-> 建立事件工作區
-> 產生可編輯的 cloze-style task
-> 產生一位 primary historical persona
-> 學習者完成 task
-> 後端產生 correct / partial / incorrect 的初步判斷
-> 解鎖對話
-> 對話依照所選實驗條件運作
```

### 目前範圍

已完成：

- Nuxt 前端頁面：`/`、`/task`、`/chat`、`/admin`。
- FastAPI 後端，位於 `backend/app`。
- 僅供測試使用的 deterministic in-memory repository。
- local/cloud runtime 可用的 Supabase PostgREST repository。
- 對應 EBL + role-play 設計的 Supabase migration schema。
- Wikipedia provider，支援 `summary` 與 `full` 兩種抓取模式。
- 聊天前必須完成 task 的 task gate。
- 每個事件預設一位 primary historical persona。Runtime generation 使用 LiteLLM，正式實驗前教師可再編輯生成的人物資料。
- 依實驗條件切換 generic chatbot / historical persona，以及 direct answer / EBL scaffold。
- 使用 admin key 保護的後台，可管理實驗條件、task 文字、persona profile、persona `prompt_profile` 與 research logs。

暫緩：

- RAG chunking、embedding、indexing、vector retrieval。
- `task_blanks` 與 `task_answers` 的細格計分。
- controlled AI-generated inaccuracies。
- Supabase Auth 與 RLS 的正式整理。
- task scoring 正規化與正式研究資料匯出。

### 技術棧

- 前端：Nuxt 4、Vue 3、Tailwind CSS、Nuxt Icon。
- 後端：Python、FastAPI、Pydantic、httpx、LiteLLM。
- 資料庫：Supabase Postgres。
- 測試：pytest。

### 環境變數

複製 `.env.example` 成 `.env`，再依需求設定。

重要後端變數：

```env
BACKEND_REPOSITORY=auto
HISTOSPHERE_ADMIN_KEY=change-this-local-admin-key
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SERVICE_ROLE_KEY=...
```

Repository 模式：

- `BACKEND_REPOSITORY=in_memory`：僅供測試使用，必須搭配 `ALLOW_IN_MEMORY_REPOSITORY=true`。
- `BACKEND_REPOSITORY=supabase`：強制使用 Supabase，缺少設定時會報錯。
- `BACKEND_REPOSITORY=auto`：runtime 已棄用，本地開發不要使用。

### 本地開發

安裝前端套件：

```powershell
pnpm install
```

建立後端 virtual environment：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

同時啟動前後端：

```powershell
pnpm dev:full
```

這個指令會使用本地 Supabase 啟動 Nuxt 與 FastAPI。啟動前會先釋放正在占用 `3000` 與 `8000` 的既有程序。Runtime 禁止 in-memory mode。Docker Desktop 必須先開好；只要 Docker ready，script 可以在需要時啟動本地 Supabase stack。

如果只想手動清掉 dev server ports、不啟動 app：

```powershell
pnpm dev:cleanup
```

或手動分開啟動：

```powershell
# Terminal 1
cd backend
$env:BACKEND_REPOSITORY="supabase"
$env:SUPABASE_URL="http://127.0.0.1:54321"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2
$env:NUXT_API_URL="http://127.0.0.1:8000"
pnpm dev --host 127.0.0.1 --port 3000
```

開啟：

- 前端：`http://127.0.0.1:3000`
- 後端健康檢查：`http://127.0.0.1:8000/health`
- Admin UI：`http://127.0.0.1:3000/admin`

### 本地 Supabase

啟動 Supabase：

```powershell
pnpm supabase:start
```

用 migration 重設本地資料庫：

```powershell
pnpm supabase:reset
```

檢查狀態：

```powershell
pnpm supabase:status
```

Migration 檔案：

- `supabase/migrations/202605130001_ebl_roleplay_schema.sql`
- `backend/migrations/001_ebl_roleplay_schema.sql`

### 測試

後端：

```powershell
cd backend
$env:BACKEND_REPOSITORY="in_memory"
.\.venv\Scripts\python.exe -m pytest -q
```

前端 build：

```powershell
pnpm build
```

### API 摘要

核心流程：

- `GET /api/conditions`
- `POST /api/event/initialize`
- `GET /api/events`
- `POST /api/tasks/{task_id}/submit`
- `GET /api/conversations/{conversation_id}`
- `POST /api/chat`

Admin：

- `GET /api/admin/snapshot`
- `PATCH /api/admin/tasks/{task_id}`
- `PATCH /api/admin/personas/{persona_id}`
- `PATCH /api/admin/conditions/{condition_id}`
- `GET /api/admin/research-logs`

所有 admin routes 都需要：

```http
x-admin-key: <HISTOSPHERE_ADMIN_KEY>
```

### 文件

- 後端 contract：`docs/backend-architecture.md`
- 後端目錄結構：`docs/backend-directory-structure.md`
- 系統設計：`docs/system-design-ebl-roleplay.md`
- 前端 audit：`docs/frontend-audit.md`

### 維護規則

- 文件必須採用「完整英文版在前，完整中文版在後」的結構。
- 每次 API 修改，都要更新 `docs/backend-architecture.md`。
- 每次 schema 修改，都要同步更新兩份 migration 與欄位註解。
- 每次 prompt module 修改，都要更新後端架構文件。
- 每個前端 `$fetch('/api/...')` 都應該在文件中有對應 endpoint。
- RAG 與 controlled inaccuracies 在研究設計確認前保持 disabled。
