# Histosphere

Histosphere 是用於碩士研究的歷史學習實驗系統，研究 Error-Based Learning（EBL）與 AI 歷史人物 Role-play 對 Historical Thinking 的影響。

系統不是公開 SaaS。正式使用情境是研究者現場控制受測者帳號、Condition、事件素材與實驗流程。

## 實驗流程

```text
Admin 建立並鎖定事件、Task 與唯一啟用人物
-> Admin 綁定 Participant 帳號與 Condition 順序
-> Learner 使用 Supabase Auth 登入
-> 完成前置 Task
-> Backend 建立逐題診斷結果
-> AI 開始 Standard Chat 或 Historical EBL 對話
-> 五分鐘倒數結束
-> Learner 明確進入下一階段
```

前置 Task 只用來產生後續對話的錯誤或知識缺口，不是前測、後測或 Historical Thinking outcome score。

## 2x2 Conditions

| 代號 | 身分呈現 | 互動方式 | 管理端簡稱 |
| --- | --- | --- | --- |
| 01 | 中性 AI 歷史助教 | Standard Chat | Baseline |
| 02 | 中性 AI 歷史助教 | Historical EBL | AI Error-based Learning |
| 03 | 歷史人物第一人稱 | Standard Chat | AI Role-play Learning |
| 04 | 歷史人物第一人稱 | Historical EBL | EBL AI Role-play |

Learner 介面只顯示 01–04，不揭露 Condition 的實驗意義。02 與 04 共用相同 Historical EBL／Disclosure policy；04 只增加 persona renderer。

## 技術架構

- Frontend：Nuxt 4、Vue 3、Tailwind CSS
- Backend：FastAPI、Pydantic、LiteLLM
- Database/Auth：Supabase PostgreSQL、Supabase Auth
- Local runtime：Docker Desktop、Supabase CLI

Supabase 是事件、Task、Persona、Participant、Session、Attempt、Conversation 與研究紀錄的 source of truth。Prompt 與 LLM runtime policy 由 backend 管理。

## 本機啟動

### 1. 安裝依賴

```powershell
pnpm install
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### 2. 設定環境變數

以 [.env.example](./.env.example) 建立 `.env`，至少確認：

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `HISTOSPHERE_ADMIN_KEY`
- `LLM_MODEL` 與對應 provider API key

`HISTOSPHERE_ADMIN_KEY` 沒有程式預設值。正式 runtime 只使用 `LLM_MODEL` 指定的 provider/model，不自動切換 fallback provider。

### 3. 啟動完整環境

```powershell
pnpm dev:full
```

此指令會：

- 檢查 Docker daemon。
- 釋放 frontend `3000` 與 backend `8000`。
- 保留並檢查 Supabase 官方 local ports。
- 重用健康的 Supabase stack，否則啟動必要服務。
- 啟動 FastAPI 與 Nuxt。

預設網址：

- Frontend：<http://127.0.0.1:3000>
- Admin：<http://127.0.0.1:3000/admin>
- Backend health：<http://127.0.0.1:8000/health>
- Supabase API：<http://127.0.0.1:54321>
- Supabase Studio：<http://127.0.0.1:54323>

詳細啟動與 port 排錯請看 [local-development.md](docs/local-development.md)。

## 驗證

```powershell
pnpm test:frontend:unit
pnpm test:backend
pnpm build
```

需要完整本機環境時再執行：

```powershell
pnpm test:supabase:schema
pnpm test:runtime:smoke
```

## 文件管理

### 三份主要管理文件

- [System Map](docs/histosphere-system-map.html)：各子系統與功能完成狀態。
- [記憶.md](記憶.md)：已確認、會長期影響研究或工程的原則。
- [Research Experiment Backlog](docs/research-experiment-backlog.md)：尚未定案、暫緩與已接受風險。

### 支援文件

- [architecture.md](docs/architecture.md)：Backend、API、runtime 與測試 contract。
- [system-design.md](docs/system-design.md)：整體流程與 frontend/backend 責任。
- [ebl-historical-roleplay-intervention-design.md](docs/ebl-historical-roleplay-intervention-design.md)：現行研究介入規格。
- [persona-completion-flow.md](docs/persona-completion-flow.md)：Prompt 組裝與單次 completion pipeline。
- [supabase-schema.md](docs/supabase-schema.md)：Database tables、columns、constraints 與 indexes。
- [research-data-export.md](docs/research-data-export.md)：Session 回放、匯出與 token 統計。
- [local-development.md](docs/local-development.md)：本機啟動、ports 與故障排除。

完成大型研究或工程決策後，先更新 `記憶.md` 與相關規格，再同步 System Map 狀態；尚未定案內容只放進 backlog，避免多份文件互相矛盾。

## Repository 結構

```text
backend/app/       FastAPI production code
backend/tests/     Backend tests
components/        Nuxt UI components
composables/       Frontend state and workflows
pages/             Nuxt routes
utils/             Frontend API and pure helpers
supabase/          Local Supabase config and migrations
scripts/           Development and verification scripts
docs/              Technical and research documentation
```

不將 `.env`、正式 API keys、Supabase service-role key 或真實 Admin key 提交到 Git。
