# LLM Runtime Roadmap

最後更新：2026-08-09

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
- Window：由最新訊息往前裝入最多 16,000 字元；每則最多 1,600 字元，不以固定訊息數截斷。
- 前端 history：不作為 authoritative memory。
- 保存：每次 model message 記錄本次使用的 history message ids。

這已解決重新整理後失去對話 context 的問題，但仍是 bounded short-term memory，不是摘要或長期記憶。

### Current Transport Boundary

- Task judgement/greeting: `202 Accepted` + persisted attempt + FastAPI BackgroundTask + HTTP polling.
- Chat completion: learner message 先保存成持久化 operation；`POST /api/chat/stream` 以 SSE 回報保存、生成、驗證與完成狀態，重新整理後可依相同 request id 查詢或重試。
- SSE delta 是等待體驗，不會把未通過後端驗證的原始 Provider token 直接交給 Learner。DB 中的 message/operation 仍是 authoritative state。
- 目前不使用 WebSocket、Redis 或外部 queue；單機研究環境以資料庫 operation 與 process worker 控制重複送出。

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
- Prompt dry-run：呼叫同一 provider，但不保存正式 message 或 Session 研究紀錄。
- Runtime metadata：保存完整 Prompt snapshot/hash、persona profile hash、module names、provider、model、latency、token usage、retry 與 history ids。

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

Status: implemented and locally verified on 2026-07-11 with backend/frontend tests, Nuxt typecheck/build, real local Supabase smoke checks, and browser prompt-preview verification.

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

Status: implemented for the current single-provider research deployment.

- Chat 使用可持久化 operation、同一 turn duplicate guard 與明確失敗／重試狀態。
- timeout、rate limit、provider 5xx 最多在同一 model 自動 retry 一次；authentication、content filter 與 invalid request 不自動重試。
- 正式實驗禁止自動切換 Provider/model，避免 Condition 以外的新變因；metadata 的 `provider_switching_enabled` 固定為 false。
- 若未來需要無 client poll 也能恢復，增加 startup reconciliation worker 或 durable queue；多 instance 時使用資料庫 atomic claim。
- 已保存 request correlation id、latency、token usage、retry reason 與 attempt count。
- 各功能目前共用全域模型設定與 4096 max output tokens；除非實際驗證顯示截斷，不增加每功能參數 UI。
- 加入 concurrency guard，避免同一 conversation 同時送出兩個 turn。

Acceptance criteria：

- Provider timeout 不會讓 task attempt 永久停在 `processing`。
- Retry/fallback 最多產生一則正式 assistant/persona message。
- Admin 可從 metadata 判斷實際使用的 provider/model 與 fallback 原因。

### Phase 3: Research Reproducibility

Status: minimal reproducibility implemented; full publishing platform deferred.

- Session 建立時保存 event、task、condition、personas 的完整素材快照與 SHA-256。
- 每次正式 LLM 呼叫保存實際 Prompt、modules、model metadata 與 SHA-256，可由 hash 回查內容。
- Admin 可按 Session 回放 Task、完整對話與 token/message 統計，並匯出匿名化 JSON／CSV。
- 完整 draft/readiness/publish、視覺化版本比較與 material rollback 仍暫緩。

這一階段是 **material version lock/schema**，目前只保留為待討論設計，不應在沒有研究者確認 schema 與 publish semantics 前直接實作。

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
- Task per-question scoring / accepted-answer / answer-key audit：待詳細討論後實作。
- Formal session completion / debrief：待詳細討論後實作。
- Research data export：已完成；格式與統計邊界見 `docs/research-data-export.md`。
- Controlled deliberate historical errors：待討論，維持 disabled。
- Multi-admin roles：目前不需要；共用 Admin key 符合研究部署方式。
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
