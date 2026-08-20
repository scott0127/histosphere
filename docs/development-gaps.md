# Development Gaps

最後更新：2026-08-09

本文件只列目前仍存在的功能邊界，不把已完成項目繼續列成待辦。Histosphere 是研究者現場控制的碩士實驗系統，因此優先確保 Condition、Session、Task、Chat 與研究資料語意正確，不建立沒有明確研究用途的大型平台功能。

## 已完成的主要能力

- Supabase Auth learner 登入、JWT 驗證、participant 綁定，以及由 Admin 設定並由後端強制執行的有序 condition assignment。
- 共用 Admin key、Admin test mode、Participant 建立／綁定／封存／恢復。
- Event、Task、Persona 的 Admin 管理；Learner 只能使用既有且未封存素材。
- Session 中斷恢復、固定五分鐘倒數、到期後進入下一階段，以及 Admin 重設 Session／倒數。
- Story-first Task 編輯器、inline 題型、預覽、Undo/Redo、草稿、非同步送出與失敗恢復。
- 四種 2x2 Condition、Historical EBL／Disclosure、Persona 邊界與離題重新導向。
- DB-backed 多輪 Chat、持久化 operation、SSE 等待回饋、重複送出保護、同模型暫時性錯誤重試。
- 每次 LLM 呼叫的 provider、model、latency、token、Prompt 與 hash 紀錄。
- Admin 單一 Session 回放、完整逐句對話、Task、訊息／來回／Token 統計及 JSON／CSV 匯出。
- Session 建立時素材快照與每次實際 Prompt 快照；匯出時驗證 SHA-256。
- 前端單元測試、後端測試、Nuxt build、唯讀 Supabase schema smoke 與 runtime smoke 指令。

## 正式收案前仍需決定

### 每題正式計分語意（最高優先）

目前保留每題作答與整體 judgement，但研究者尚未確認填空同義詞、拼字、accepted answers、AI judgement 與 deterministic scoring 的責任邊界。這會改變研究資料語意，不能由工程端自行決定。

### Disclosure D0／D1 的資訊邊界

目前已實作 D0–D4、相鄰升降及輸出洩漏檢查，但單次 structured completion 為判斷 learner progress 仍需要 context。研究者需確認 D0／D1 時 `correct_answer`、`source_text` 與 evidence 是否可進入模型 context，以及不可進入時的一次呼叫策略。

### Historical EBL 的完成標準

目前可依序處理 Task error 並保存推理階段與 Disclosure。仍需確認 `RESOLVED` 是否要求「答案正確 + 證據／理由／反思」，以及 D4 後仍未成功時要持續、跳題或記錄 `unresolved_after_max_support`。

### 前後測與 Historical Thinking 測量整合

目前把前後測留在外部工具，依 participant code 與系統匯出合併。仍需確認施測時點、量表或 rubric、Historical Thinking 維度、計分方法與缺漏資料處理，才能建立正式 outcome protocol。

## 其他既有研究決策

### 受控歷史錯誤與 Debrief（最高優先）

功能維持停用。若要刻意讓歷史人物說出錯誤，必須先定義錯誤清單、適用 Condition、揭露紀錄、修正成功條件與 Session 結束前的 Debrief，避免受測者帶著錯誤離開。

### 是否顯示事件介紹

Learner 目前只在事件首頁看到必要辨識資訊，不顯示事件介紹，以免提前提供 Task 背景。正式收案前研究者需確認這是否符合實驗操弄；Admin 管理視角仍可查看完整介紹。

## 建議要，但可在目前實驗規模暫緩

- 完整 draft/readiness/publish 版本平台。目前已有 Session 素材與 Prompt 快照，可支援稽核，但不提供視覺化版本比較或回滾。
- 自動化 Vue DOM／端對端瀏覽器測試。目前使用純函式／API contract 測試、build 與人工瀏覽器驗收。
- 隔離資料庫的 migration-up 測試。目前 schema smoke 對既有 Supabase 只讀，不重設或刪除研究資料。
- 多機 durable queue。單一受測者、單一 backend 的實驗場景以 DB operation + process worker 足夠。
- 外部後測匯入。現階段可依 participant code 在分析時合併。

## 明確暫緩

- RAG ingestion、embedding、retrieval 與 citation UI。
- 歷史人物情緒／情境圖片動態變化。
- 多管理員角色、個別撤銷與 per-admin audit identity。
- 複雜題目 CRUD API；現有整包 Task PATCH 足以支援研究者編輯規模。

## 已接受的風險邊界

- 實驗由研究者現場監督，不以惡意猜測其他 Session ID 為主要威脅模型；JWT ownership 與 Admin key 仍保留基本隔離。
- Token 只採 Provider 實際回報值。舊訊息缺 usage 時顯示覆蓋率，不做不可靠估算。
- Persona 生成內容具有模型隨機性；系統固定 Condition policy、Historical Thinking 操作、Disclosure、素材與 Prompt 並留下實際輸出供後測與人工稽核，不追求 02／04 逐字相同。

研究匯出細節見 `docs/research-data-export.md`，啟動與品質指令見 `docs/local-development.md`。
