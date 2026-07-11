# LLM Runtime Roadmap

最後更新：2026-07-11

## Scope

本 roadmap 聚焦正式實驗中的 completion runtime：prompt composition、多輪 context、provider call、非同步工作、可觀測性與研究可重現性。RAG 先不實作；task authoring GUI 也不在此文件範圍。

## Current Runtime

### Canonical Prompt Composition

所有 chat completion 使用同一個 `PromptService` 組裝 ordered modules：

```text
general_prompt
-> independent_1_prompt
-> independent_2_prompt
-> event_context
-> learner_task
-> conversation_history
-> persona_context
-> source_context
-> runtime_policy
-> user_message
```

`independent_1_prompt` 對應 generic/persona identity；`independent_2_prompt` 對應 direct/EBL interaction。四個 condition 只由這兩軸組合，不應在 provider 或 UI 再藏另一套 condition 規則。

### Persona Contract

`persona_prompt_v1` 已定義保守且可驗證的欄位：語氣、社會位置、時間/地理/知識邊界、立場、source policy、forbidden claims 與 researcher notes。Legacy JSON 會正規化並保留未知欄位。

### Multi-turn Memory

- 來源：Supabase `messages`。
- 順序：`sequence_index`。
- Window：最近 12 則，每則最多 1600 字元。
- 前端 history：不作為 authoritative memory。
- 保存：每次 model message 記錄本次使用的 history message ids。

這已解決重新整理後失去對話 context 的問題，但仍是 bounded short-term memory，不是摘要或長期記憶。

### Async Task Submission

`POST /api/tasks/{task_id}/submit` 回傳 `202 Accepted` 與 persistent `attempt_id`。後端以 FastAPI in-process background task 執行 judgement、conversation 建立與 greeting；前端輪詢 `GET /api/tasks/attempts/{attempt_id}`。若頁面重新整理或 backend 在處理中重啟，下一次 poll 會以 process-local attempt guard 重新掛回 orphaned `processing` 工作。

狀態：

```text
in_progress -> processing -> submitted
                         \-> failed
```

`failed` 保留資料並允許重試，不刪除 learner response。

限制：目前不是 durable job queue。恢復需要前端再次 poll 或重新 submit；若沒有任何 client 回來查詢，backend 不會主動掃描 orphaned `processing` attempt。單一 backend process 內會以 attempt id 去重，正式多 instance 部署仍需資料庫 claim 或外部 queue。

### Admin Review Tools

- Prompt preview：檢視實際 modules 與 rendered prompt，不呼叫 LLM。
- Prompt dry-run：呼叫同一 provider，但不保存 message 或 research log。
- Runtime metadata：保存 prompt hash、persona profile hash、module names、provider、model 與 history ids。

## Runtime Invariants

1. Condition mapping 只能來自 backend canonical condition definitions。
2. Learner 建立 session 前必須通過 `participants.auth_user_id` 綁定、`status=active` 與 `condition_list` 指派檢查。
3. Admin override 可測試所有 condition，但不能改寫 learner assignment 語意。
4. Session timer 預設關閉；只有 Admin 明確啟動才有 `timer_started_at` / `timer_ends_at`。
5. Timer 到期後 backend worker 與 task/chat runtime boundary 都會執行 completion，不能只依賴前端倒數。
6. RAG disabled 時 `source_context` 必須明示沒有 retrieval，不得產生假 citation。
7. 正式 chat 保存 message 與 audit metadata；dry-run 不污染研究資料。

## Roadmap

### Phase 1: Stabilize Current Runtime

Status: implemented in current working tree; merge前仍需整合測試。

- 固定 persona prompt contract 與 module order。
- DB-backed bounded history。
- Async task submit + polling + resume。
- Admin prompt preview / dry-run。
- Provider/model/prompt/profile/history metadata。
- Opt-in timer 與 backend expiry enforcement。
- Event archive 與 learner condition gate。

Acceptance criteria：

- 四種 condition 的 module 組合可由 Admin preview 逐一檢查。
- 第二輪 chat prompt 包含第一輪 DB messages。
- task submit 在 LLM 等待期間立即回傳 `202`，poll 最終得到 conversation payload 或明確 failed state。
- dry-run 不新增 `messages` 或 `research_logs`。

### Phase 2: Provider Reliability And Observability

Status: next recommended LLM milestone.

- 定義主 provider、fallback provider 與 model allowlist。
- 將 timeout、rate limit、authentication、content filter 與 provider 5xx 分類成穩定 error codes。
- 僅對可重試錯誤使用 bounded retry；避免同一 learner turn 產生重複 message。
- 若未來需要無 client poll 也能恢復，增加 startup reconciliation worker 或 durable queue；多 instance 時使用資料庫 atomic claim。
- 加入 request correlation id、latency、token usage、fallback reason 與 attempt count。
- 對 task judgement、greeting、chat、persona generation 分別設定 temperature、token budget 與 timeout policy。
- 加入 concurrency guard，避免同一 conversation 同時送出兩個 turn。

Acceptance criteria：

- Provider timeout 不會讓 task attempt 永久停在 `processing`。
- Retry/fallback 最多產生一則正式 assistant/persona message。
- Admin 可從 metadata 判斷實際使用的 provider/model 與 fallback 原因。

### Phase 3: Research Reproducibility

Status: deferred until material version strategy is approved.

- 建立 experiment material snapshot/version：event、task、answer key、persona profile、condition prompt modules。
- Session 開始時鎖定 material version，而不是永遠讀最新 row。
- 保存 model configuration snapshot，包括 model、temperature、token budget 與 provider-specific parameters。
- Prompt hash 必須可回查到實際 prompt content/version，而不只是不可逆 hash。
- 建立 admin publish/readiness flow，區分 draft 與正式實驗 material。

這一階段是 **material version lock**，目前明確 deferred，不應在沒有研究者確認 schema 與 publish semantics 前直接實作。

### Phase 4: Evaluation And Safety

Status: planned.

- 建立 persona boundary regression set：時間越界、全知旁白、捏造引文、私人心理、身份跳脫。
- 建立 condition separation tests，確認 direct 不被偷偷變成 EBL，EBL 不會過早揭露完整答案。
- 對 prompt injection、要求揭露 system prompt、要求 chain-of-thought 建立 refusal tests。
- 建立 historical accuracy review dataset 與人工標註流程。
- deliberate-error feature 必須有獨立且經審核的 error contract、適用 condition、曝光記錄與 debrief 規則；在此之前維持禁用。

### Phase 5: RAG

Status: deferred; this roadmap does not implement it.

未來若啟動，需先決定：

- 允許的史料來源、版本與授權。
- ingestion/chunking/embedding pipeline。
- event/persona/time-boundary filters。
- citation payload 與 learner-facing citation UI。
- retrieval snapshot 如何與 material version lock 對齊。
- 沒有命中時的明確 no-evidence behavior。

在上述 contract 未完成前，`knowledge_chunks` 與 `messages.rag_sources` 只保留 schema，不視為可用功能。

## Deferred Items

- Material version lock：deferred。
- RAG：deferred。
- 原需求中未提供具體定義與驗收條件的第 6 項：deferred，等待產品/研究語意確認。
- 原需求第 8 項：若指 RAG，依本文件 deferred；若另有所指，需先補需求與驗收條件。

## Recommended Verification Matrix

| Layer | Verification |
| --- | --- |
| Prompt contract | Unit test exact module order and four condition branches. |
| Multi-turn memory | Create two turns, assert second prompt contains persisted first turn ids/content. |
| Async submit | Assert `202`, processing state, submitted payload, failed retry, idempotent duplicate submit. |
| Dry-run | Compare module names with preview and assert message/log counts unchanged. |
| Timer | Test disabled default, start/cancel, lazy expiry, worker expiry, task/chat rejection after completion. |
| Assignment | Test bound/unbound/inactive/unassigned participant and Admin override. |
| Archive | Test public list excludes archived, Admin snapshot includes it, restore re-enables learner use. |
