# Research Experiment Backlog

更新日期：2026-08-09

## 文件目的

本系統用於研究者現場控制的碩士實驗，不是公開 SaaS。此文件區分：近期必須完成、需要先詳細設計、已接受的低風險，以及暫緩研究功能。避免依照一般大型產品假設過度設計。

## 已完成的近期實作

### 1. Chat 非同步 operation 與重複送出保護

Learner 訊息會先保存成可持久化 operation；前端使用 SSE 取得保存、生成、驗證與完成狀態，重新整理後可用相同 request id 查詢或重試。

最小實作目標：

- learner message 先保存，再建立可持久化 chat operation。
- SSE 提供等待狀態；operation status endpoint 支援重新連線。
- 同一 conversation 同一 operation 不得因連點或重新整理重複建立正式 model message。
- 失敗時保留 learner message、錯誤狀態及可重試資訊。
- 不引入 Redis、Celery、Kafka 或大型 queue framework；目前單機研究環境使用資料庫狀態加 process-local worker 即可。

目前 SSE 只傳送通過後端驗證後的顯示 delta；DB 中的 operation/message 仍是 authoritative state。

### 2. 最小 Provider 失敗與重試

需要處理的最小情境：

- timeout
- rate limit
- provider 5xx / 暫時不可用
- authentication / invalid request

行為：

- timeout、rate limit、provider 5xx：同一 model 最多自動 retry 一次。
- authentication、invalid request：不自動 retry，直接顯示固定錯誤。
- 自動 retry 或使用者按「重試」都沿用相同 operation id，不新增第二則 learner message。
- 前端顯示明確失敗狀態與重試按鈕，不建立複雜的 retry policy UI。
- 保存 provider、model、attempt count、failure category、token 與 latency；正式研究禁止自動切換 Provider。

### 3. 必要測試與檢查

- 已有後端 API／service、前端純函式／API contract、Provider failure、重複 operation 與四種 Condition regression tests。
- 已有唯讀 Supabase OpenAPI schema smoke、runtime smoke 與 Nuxt build 指令。
- Disposable database migration-up 與自動化 Vue DOM／瀏覽器 E2E 因目前單機研究規模暫緩；正式變更仍需人工瀏覽器驗收。

## 待詳細討論後實作

### Task 每題評分與答案稽核

此項會直接影響研究資料語意，不能只補幾個欄位。

需要決定：

- 填空、選擇、是非是否採完全比對、正規化比對或 accepted answers。
- 多個可接受答案、同義詞、錯字與標點如何處理。
- AI judgement 和 deterministic scoring 的責任邊界。
- 每題保存 learner answer、正確答案版本、結果、判定方法與人工覆核。
- answer key 修改後，舊 attempt 應指向哪一版答案。
- 匯出時如何呈現每題分數與 misconception。

在規格確認前，維持現有完整 answer bundle 與整體 judgement。

### Session 正式完成與 Debrief

需要決定：

- learner 主動完成、timer 到期、Admin 強制完成的狀態轉移。
- Chat 結束後是否需要確認畫面與 debrief。
- 完成後是否禁止繼續發言，以及 Admin test mode 是否可重新開啟。
- 中途離開、重新登入與恢復流程。
- completion reason、completed_at 與研究紀錄匯出的正式定義。

### 研究資料匯出（已完成）

Admin 可查看單一 Session 的 Task、完整逐句對話、時間、訊息／來回／Token 統計，並匯出只含 participant code 的 JSON／CSV。素材與完整 Prompt 快照附 SHA-256；詳細定義見 `docs/research-data-export.md`。

### RAG

維持暫緩。待討論來源授權、chunking、retrieval scope、citation UI、無證據行為及與 persona knowledge boundary 的關係。

### 受控歷史錯誤

維持 disabled。待討論錯誤類型、適用 condition、暴露紀錄、修正時機與 debrief，避免模型任意捏造錯誤。

### Material Version Schema

目前不重要，因研究者會在正式實驗前凍結最終版本，確保所有受測者使用相同程式與素材。仍保留為待討論項目，以防未來需要多批次實驗、修改後重跑或稽核舊資料。

## 已接受的低優先風險

### Participant Session Ownership 強化

受測者會在研究者控制的電腦與流程中操作，不以惡意猜測其他 session id 為威脅模型。保留現有 Auth-to-participant mapping 與 condition assignment enforcement；暫不建立大型 authorization framework。

### Multi-admin Roles

目前不需要。現行部署只有研究者與指導教授，共用一組 Admin key 即可。

Multi-admin roles 原本指：

- 每位管理員有獨立帳號。
- 可分 researcher、reviewer、read-only 等權限。
- 可撤銷單一管理員而不更換所有人的密碼。
- Audit log 能指出是哪一位管理員修改資料。

只有在人數增加、需要個別撤銷權限、需要區分可編輯/唯讀，或論文稽核必須追蹤個人操作時才需要重新評估。
