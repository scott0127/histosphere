# 研究資料回放與匯出

最後更新：2026-08-09

## 目的

Admin 可依 Session 查看一次實驗的完整紀錄，也可將全部 Session 匯出為 JSON 或 CSV。正式匯出只使用受測者代號，不包含 Supabase Auth user id、Email、Admin key 或 API key。

## Admin 可查看的內容

- 受測者代號、事件、Condition、Session 狀態與時間。
- Task 作答內容與後端 judgement。
- 依 `sequence_index` 排序的完整 Learner / AI 對話。
- Learner 訊息數、AI 訊息數、總訊息數與完成來回數。
- Provider 實際回報的 prompt、completion 與 total token。
- 實際使用的 model、provider、Prompt hash 與素材快照 hash。
- Session 相關 research logs。

「完成來回數」取 `min(Learner 訊息數, AI 訊息數)`，用於快速描述已有多少組問答；總來回數若採「所有人發言次數」語意，應直接使用總訊息數。

## Token 統計邊界

Token 僅加總 LLM Provider 實際回報的 usage，不從文字長度推估。畫面同時顯示 token usage 覆蓋率：

- `100%`：每一則 LLM 訊息都有 usage，可將總 Token 視為完整值。
- 小於 `100%`：部分舊訊息或 Provider 回覆沒有 usage；畫面顯示的是已知下限，不代表完整花費。

## 可重現性紀錄

系統不新增版本平台，而是沿用 `research_logs` 保存兩種最小快照：

1. `session_material_snapshot`：Session 建立時的 event、task、condition 與 personas，以及 SHA-256。
2. `llm_prompt_snapshot`：每次正式 LLM 呼叫實際使用的完整 Prompt、modules、model metadata，以及 SHA-256。

Admin 回放時會重新計算 hash 並顯示是否一致。這可證明匯出的內容沒有在記錄後被悄悄改寫，但不等於完整的 draft/publish 版本管理系統。

## API

- `GET /api/admin/sessions/{session_id}/research`：單一 Session 回放與統計。
- `GET /api/admin/research-export?format=json`：全部 Session 的階層式研究資料。
- `GET /api/admin/research-export?format=csv`：每則對話一列的分析用長表。

以上入口都需要 `x-admin-key`。

## Legacy 資料

新功能部署前建立的 Session 可能沒有素材或完整 Prompt 快照；回放會保留對話，但對應快照顯示缺漏。舊資料不會被猜測或補寫成看似精確的版本。

## 目前刻意不做

- 不建立新的研究資料表。
- 不估算缺漏 Token。
- 不輸出 Auth user id 或 Email。
- 不做多管理員權限與個別操作人追蹤。
- 不把外部後測強行塞進 Session；後測可用 participant code 另行合併。
