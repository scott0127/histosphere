# Histosphere

Histosphere 是用於碩士研究的歷史學習實驗系統，研究 Error-Based Learning（EBL）與 AI 歷史人物 Role-play 對 Historical Thinking 的影響。

系統不是公開 SaaS。正式使用情境是研究者現場控制受測者帳號、Condition、事件素材與實驗流程。

## 實驗流程

```text
Admin 建立並鎖定事件、Task 與唯一啟用人物
-> Admin 綁定 Participant 帳號與 Condition 順序
-> Learner 使用 Supabase Auth 登入
-> 閱讀 Error-Elicitation Task，每題回答案與理由
-> Backend 建立逐題診斷結果
-> AI 開始 Standard Chat 或 Historical EBL 對話
-> 五分鐘倒數結束
-> 02/04 若有已談到的未完成目標，先顯示修正並重述一次
-> Learner 明確進入下一階段
```

Error-Elicitation Task 只用來產生後續對話的錯誤或知識缺口，不是前測、後測或 Historical Thinking outcome score。

## 2x2 Conditions

| 代號 | 身分呈現 | 互動方式 | 管理端簡稱 |
| --- | --- | --- | --- |
| 01 | 非 Role-play 普通 AI | Standard Chat | Baseline |
| 02 | 非 Role-play 普通 AI | Historical EBL | AI Error-based Learning |
| 03 | 歷史人物第一人稱 | Standard Chat | AI Role-play Learning |
| 04 | 歷史人物第一人稱 | Historical EBL | EBL AI Role-play |

Learner 介面只顯示 01–04，不揭露 Condition 的實驗意義。02 與 04 共用相同 Historical EBL／Disclosure policy；04 由人物立場與語氣自然承載 EBL，不另增加提前作答權。Historical Thinking 是四組共用的 AI 回應基礎，不是另外明示要求學習者練習的技能。

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

- [後端與資料庫工程交接手冊](docs/backend-database-handbook.html)：新接手者的統一入口，說明架構、流程、資料表、權限、維運與安全修改方式。
- [architecture.md](docs/architecture.md)：前後端責任、Judge v4、Prompt、答案審查、API 與驗證邊界。
- [ebl-historical-roleplay-intervention-design.md](docs/ebl-historical-roleplay-intervention-design.md)：現行研究介入規格。
- [supabase-schema.md](docs/supabase-schema.md)：Database tables、columns、constraints 與 indexes。
- [research-data-export.md](docs/research-data-export.md)：Session 回放、正式匯出、各環節 Token／台幣費用估算與缺漏語意。
- [local-development.md](docs/local-development.md)：本機啟動、ports 與故障排除。

### 已整併、不需獨立維護

- [system-design.md](docs/system-design.md)：原系統責任及流程已併入 architecture，保留短導讀供舊連結使用。
- [persona-completion-flow.md](docs/persona-completion-flow.md)：Prompt 流程已併入 architecture，人物／EBL 規則集中在介入規格。
- 上述兩檔是可刪除候選；本次沒有直接刪除，避免外部書籤失效。其餘文件各有獨立用途，不另建 docs 索引頁或重複 roadmap。
- 工程交接手冊是入門導讀，不維護另一份完整 API schema；精確 API 以 OpenAPI 與後端 schema 為準。

文件同步於 2026-09-06。先完成程式與必要驗證，再依授權更新規格，最後更新 System Map；藍點僅代表所列工程範圍完成，不代表研究效度已驗證。人物與材料的時間界線、正式素材與 Judge 抽樣驗收仍保留在 backlog。

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
