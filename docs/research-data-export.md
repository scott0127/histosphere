# 研究資料回放、用量與匯出

更新日期：2026-09-19。後測說明依目前後端程式、migration 與 API 測試核對；本次沒有重新匯出全部 live 研究資料。

## Admin 可看什麼

管理員可依受測者與 Session 查看完整五分鐘對話、Task 的答案與理由、Judge 診斷、時間、Condition、素材／Prompt hash、模型及審查紀錄。計時後的輔助重述另存研究紀錄，不冒充五分鐘內聊天。

逐字稿可展開答案審查及交付紀錄；被拒絕的候選不是受測者看見的正式訊息。Learner API、SSE、polling、對話重載均不提供這些私有資料。

Session 研究 API 與 JSON/CSV 匯出另提供 `session_posttests` 的占位後測資料，包含草稿與已提交結果；它不是新增聊天訊息，也不增加 LLM 呼叫。此處描述 API／匯出契約，不代表 Admin 畫面已有專用後測檢視面板。

## 訊息數不等於 LLM 呼叫數

- Learner 訊息數：受測者實際送出的發言。
- AI 訊息數：可見 AI 發言；若要分析開場與一般回答，應另區分。
- 總訊息數：兩者相加，適合使用者所說的「雙方總發言次數」。
- 完成來回數：目前快速指標為兩者較小值，不代表已逐一配對的研究編碼。
- Judge、答案審查、修正候選及格式重試不增加聊天來回數；系統備援不冒充模型生成次數。

## Token 與費用

| 畫面 | 範圍 | 資料來源 |
| --- | --- | --- |
| Admin LLM 用量 | 各階段／模型的已記錄呼叫，包含隔離測試與 dry-run | 本機持久帳本 `.dev-logs/llm-usage.jsonl` |
| Participant / Session 研究紀錄 | 可歸屬該 Session 的 Judge、開場、Chat、審查／修正等 | DB 中已保存的呼叫 metadata |

**兩者範圍重疊，不能相加。** 全域帳本不是教授帳戶的官方帳單：記錄建立前、其他程式或其他主機的消耗不會自動補入。換部署主機需保留帳本；不應將含研究資訊的帳本提交 Git。

- 只加總 provider 真實回報的 prompt、completion、total tokens；同一底層呼叫依識別資訊去重，避免巢狀 metadata 重算。
- 包含已有 usage 的重試、格式修復和審查消耗，不只計算最後成功回覆。
- 缺漏不是 0；覆蓋率不足時只表示已知部分。即使已記錄呼叫覆蓋率 100%，也不等於整支 API key 的完整帳務。
- 美元為模型價格資料的**估算**。無可用價格時保留未知，不捏造費用。
- 台幣用管理員可調的 USD/TWD 匯率換算，並非即時匯率或實際信用卡結算。小額非零費用不應四捨五入成看似完全免費。
- Judge v4 填空語意判定合併在原本那次 Judge 呼叫，不逐題另付一次費用。

## 快照與正式匯出

Session 建立保存 `session_material_snapshot`；LLM 流程保存 Prompt/modules 與 hash，研究回放可核對。hash 只證明內容與所記錄快照一致，不證明史料或模型判斷正確。

正式 JSON/CSV 排除 `is_admin_test=true` 及無法歸屬 Participant 的資料。若仍需合併外部後測，應以每輪的 `session_id` 配對，再使用 `participant_code`、事件與 Condition 核對；同一受測者有多輪時，僅靠 `participant_code` 不能唯一配對。匯出不輸出 Auth user id、Email 或密鑰。JSON 適合完整階層資料，CSV 為分析用長表；不能只以 CSV 的聊天列數推算 LLM 成本。

### 占位後測欄位

目前題本固定為 `posttest_placeholder_v1`，三題 Engagement Likert 與兩題 HAT 文字作答皆是 Pseudo 題，沒有正式量表、評分或 HAT rubric。`is_placeholder=true` 明確標示流程測試資料。

JSON 中每筆 Session 研究紀錄新增 `posttest`；未開始時為 `null`，開始後為下列完整物件：

| 欄位 | 內容 |
| --- | --- |
| `id`、`session_id` | 後測識別碼與所屬那一輪活動。 |
| `instrument_version`、`is_placeholder` | 目前固定為 `posttest_placeholder_v1`、`true`。 |
| `stage` | `engagement`、`hat` 或 `completed`。 |
| `engagement_answers` | `engagement_1` 至 `engagement_3` 的 1–5 整數；草稿可尚未填完。 |
| `hat_answers` | `hat_1`、`hat_2` 的文字；草稿可尚未填完。 |
| `revision` | 成功儲存及階段切換時增加的版本號。 |
| `started_at`、`updated_at`、`submitted_at` | 首次開始、最近儲存、最終提交時間；未提交時 `submitted_at=null`。 |

CSV 新增四欄：

| 欄位 | 有後測紀錄 | 沒有後測紀錄 |
| --- | --- | --- |
| `posttest_stage` | 儲存的階段 | 空字串 |
| `posttest_instrument_version` | `posttest_placeholder_v1` | 空字串 |
| `posttest_is_placeholder` | `True` | 空字串 |
| `posttest_response_json` | 上述完整物件的 JSON 字串 | 字面值 `null` |

CSV 仍以聊天訊息為長表單位，同一 Session 的後測欄位會重複出現在每個訊息列；沒有訊息的 Session 仍有一列。分析後測時須依 `session_id` 去重或拆成一輪一筆，不能把重複的後測欄位當成多次填答。

**占位題本不會自動被正式匯出排除。** 目前的匯出篩選依然只排除 Admin test 與無 Participant 歸屬的 Session；正式歸屬 Session 上的 Pseudo 後測會保留並標示 `is_placeholder=true`。正式量測分析必須另外依題本版本與占位旗標篩選，不能把這些回答當成已驗證的 Engagement 或 HAT 分數。

### 完成狀態的解讀

- `session.status='completed'`、`session.completed_at` 是對話階段結束，不表示後測已送出。
- `posttest.stage='completed'` 且 `posttest.submitted_at` 非空才是本輪後測提交完成；它不表示答案正確或達到學習成效。
- Session state／progress API 的 `posttest_stage` 是衍生摘要，不另存於 Session 表。有後測時取其階段；對話完成但未開始後測為 `not_started`；其他無紀錄狀態為 `null`。這與 CSV 的無後測空字串呈現不同。
- 後測需在對話結束與必要的收尾重述完成後開始；進入 HAT 後鎖定活動回饋，最終提交後不能修改。草稿與提交均使用版本驗證，重複提交沿用首次結果。
- 下一個指派條件需等待前一輪後測提交，不能只靠對話完成解鎖。後測開始後不能重置同一輪對話倒數；管理員另建活動時保留舊後測資料。

## 管理 API

以下都需 `x-admin-key`：

- `GET /api/admin/sessions/{session_id}/research`
- `GET /api/admin/research-export?format=json` 或 `format=csv`
- `GET /api/admin/llm-usage`

舊資料可能沒有用量、完整 Prompt、Judge v4 或審查記錄。保留缺漏與原版本，不自行重判、補算或冒充當時已啟用新規則。
