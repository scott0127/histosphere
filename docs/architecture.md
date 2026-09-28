# 系統技術架構

更新日期：2026-09-06。依目前工作樹核對，不代表已部署或完成正式收案驗收。

本文件是前後端責任、API 與 runtime 契約的技術基準。入門看[工程交接手冊](backend-database-handbook.html)，研究介入看[介入規格](ebl-historical-roleplay-intervention-design.md)，待決事項只在[研究 backlog](research-experiment-backlog.md)維護。

## 架構與責任

| 位置 | 責任 |
| --- | --- |
| `backend/app/api/v1/endpoints/` | HTTP 驗證、權限與回應；不另寫一套研究政策。 |
| `backend/app/services/` | Session、Task、Chat、Prompt、審查與研究資料流程。 |
| `backend/app/core/` | 判題／互動／人物契約、Learner 資料過濾與設定。 |
| `backend/app/providers/llm/` | LiteLLM 結構化呼叫、有限重試、格式修復與用量。 |
| `backend/app/crud/protocols.py`、`backend/app/db/` | Repository 介面及 Supabase／測試用記憶體實作。 |
| `backend/app/models/`、`backend/app/schemas/` | Pydantic domain 與 HTTP request/response；不是 ORM。 |
| `pages/`、`components/`、`composables/` | Nuxt 路由、畫面與流程狀態。 |
| `supabase/migrations/` | 唯一 migration 來源；不維護 backend SQL 副本。 |
| `supabase/content/error-elicitation-reading-tasks.json` | 四事件人工整理的閱讀題組版本。 |

Supabase 保存研究資料，Prompt 政策由後端程式控管。正式 runtime 使用 Supabase；`in_memory` 只供明確開啟的測試。單機背景工作配合持久化狀態，不引入 Redis/Celery 或多機 claim 平台。

## 正式流程與權限

```text
Admin 審查並鎖定事件、Task、唯一啟用人物
→ 綁定 Participant Auth 帳號，分派有順序的 Conditions
→ Learner JWT 登入，開始或恢復同一 Session
→ Error-Elicitation Task：閱讀材料，每題回答案與理由
→ 202 + attempt_id；背景判題與生成開場
→ Chat 可用才開始五分鐘倒數
→ 到期停止 Chat；02/04 有已談到的未完成目標時進入收尾
→ 顯示該題修正與理由，重述一次，再進下一階段
```

- Learner 身分取 JWT，不信任前端 `user_id`；同時檢查 Session 凍結的 `participant_id`，帳號改綁不能讀到前一受測者紀錄。
- 缺少 assignment／Condition 不預設為 04。依分派順序開始，既有活動先恢復，不能自己跳組或重置倒數。
- 每個 Session 最多一份 Attempt、一段 Conversation，由程式與資料庫 unique index 共同約束。
- Admin key 只供管理與明確測試；缺少 `HISTOSPHERE_ADMIN_KEY` 拒絕啟動，沒有 fallback key。
- Admin test 不計入正式進度與正式匯出。事件／人物一般使用封存；不要把管理封存理解為刪除研究資料。

## Error-Elicitation Task 與 Judge

### 資料契約

正式題型只有 `cloze`、`multiple_choice`、`true_false`。Task 契約仍為 `error_elicitation_v1`；新的 Judge 契約為 **`error_elicitation_judge_v4`**。

- `error_elicitation_task_full_text`：完整作答情境、各小題敘述與 `{{blank:qNN}}` 位置。
- `evaluation_payload.materials[]`：閱讀文字、圖片及具體描述材料的小標 `caption`；不是強制分類標籤。
- `evaluation_payload.questions[]`：穩定題號、題型、選項、參考正解、修正說明與每題 `reasoning_criteria`。
- `response_payload`：每題 `value` 與 `rationale` 原文；是非答案使用 JSON Boolean。
- 題號／token 不一致、重複或漏題、空白答案／理由、非法選項在判題前拒絕，不製造假的學習者錯誤。

### 判定責任

| 項目 | 判定者 | 規則 |
| --- | --- | --- |
| 選擇／是非答案 | Backend | 依選項值或 Boolean 確定對錯，不讓 LLM 改判。 |
| 填空答案 | LLM | 依題意、材料及參考正解作語意判定，接受等義名稱、改寫與句末標點。 |
| 所有題目的理由 | 同一次 LLM 呼叫 | 依研究者的通過標準判定；指出具體問題，不要求說出 HT 術語。 |
| 最終二分結果 | Backend | `answer_correct && reasoning_correct` 才是 `correct`。 |

參考正解不是窮舉白名單。LLM 不能用理由替學習者改寫答案，也不能把錯誤人物、否定或互相矛盾的答案當成等義。填空答案與所有理由合併在原本一個 structured completion 中，不逐題增加呼叫。

逐題內部結果節錄：

```json
{
  "question_id": "q03",
  "answer_correct": true,
  "answer_feedback": "可明確辨識為題目所指的大衛畫稿。",
  "reasoning_correct": false,
  "reasoning_feedback": "把後來的畫稿誤當作事件現場拍攝的紀錄。",
  "correctness": "incorrect",
  "historical_thinking_tags": ["evidence"]
}
```

`answer_feedback` 是填空的判定說明；選擇／是非為 `null`。新版不再輸出 `factual_error`／`reasoning_error` 分類。HT tags 只是描述，不參與計分，也不是 Historical Thinking outcome。

### 持久化、恢復與資訊邊界

`in_progress → processing → submitted`；模型或契約失敗記為 `failed`，不能轉成學生 `incorrect`。原作答保留，可重試。單機 processing 工作可由 polling 重掛，並以 process-local guard 避免重複工作。

成功判題但開場失敗時，只有輸入 hash 及 Judge v4 都一致才重用 pending judgement。已完成的舊 Attempt 不自動重判；舊契約讀取相容不表示舊判分已換成 v4。這次沒有新增資料表或 schema migration。

凍結的逐題答案、理由、判定說明、標準及材料供後續私有 Prompt 使用。02/04 據此處理答案錯或理由錯；01/03 當背景，不強制 EBL。Learner 回應移除正解、標準、`answer_feedback`、`reasoning_feedback` 等私有診斷；Admin 可讀完整資料。

## Prompt 組裝

Opening、Chat、Admin preview/dry-run 共用 `PromptService`。預覽不呼叫 LLM；dry-run 不建立正式 Session／訊息，但實際呼叫仍有用量紀錄。

| 模組 | 給模型的功能 |
| --- | --- |
| `general_prompt` | 四組共同的歷史回應品質、語言、範圍與不捏造原則。 |
| `independent_2_prompt` | 非 EBL Standard Chat 或 EBL 互動。 |
| `event_context`、`learner_task` | 事件、閱讀材料、凍結作答與診斷。 |
| `interaction_runtime` | 唯一目前錯誤、允許狀態、Disclosure 與收尾授權。 |
| `conversation_history` | 資料庫歷史；不採信前端自帶 history。 |
| `independent_1_prompt`、`persona_event_context` | 普通 AI 或人物身分、立場、當下情境與知識邊界。 |
| `source_context` | 來源設定；目前不啟用 RAG，不能宣稱已檢索。 |
| `turn_intent` | 開場／後續回合意圖。 |
| `user_message` | 最新學習者訊息，只放一次；開場沒有此模組。 |
| `runtime_policy` | 最後附上結構化輸出與操作規則。 |

人物 profile 使用嚴格的 `persona_prompt_v2`，不是任意 JSON。受控 AI 歷史錯誤仍停用。主生成是在一次呼叫內整合人物與互動，不是先生成教師稿再另呼叫模型改寫人物稿；**答案審查與修正可能額外呼叫**，見下一節。

目前歷史預算為每則最多 1,600 字元、總計 16,000 字元，從最新往前取；不等於固定 12 則或模型 token 上限。Profile、Prompt、素材 hash 及歷史訊息 ID 供研究回放。

## 答案審查與回覆交付

格式／後端狀態驗證與語意答案審查是不同責任；不要把生成模型自報的 flag 當作獨立審查結論。舊的答案字詞直接比對已移除。

獨立審查只針對 **02/04 且有錯誤目標** 的開場、聊天及授權收尾。01/03、沒有目標時不增加這次答案審查。讀取凍結題目、選項、正解、理由標準、原作答、相關歷史與實際候選文字，檢查：

1. 提前直接替學習者作答或完成仍有錯誤的理由。
2. 提前提供下一題答案。
3. 授權收尾卻沒有給必要修正。

答案相關要素、比較、史實或容易推得答案的線索本身不違規；可以確認學習者已提出的正確答案。這不是人物語氣、情緒、篇幅或全面史實查核工具；疑慮及模型誤判仍可能存在。

```text
未啟用答案審查 → 沿原生成／格式及狀態檢查流程交付
observe → 先保存並交付，再背景審查；不改寫、不推進狀態
before_delivery → 候選先審查
  合格 → 保存正式 AI 訊息並交付
  不合格 → 同模型最多兩次修正候選並再審查
  仍未取得可交付回覆 → 受限引導；必要時明示系統備援
```

只有 concern 而沒有 violation 的審查不單獨阻擋交付；逾時／服務或格式失敗不能當作通過，可直接走系統備援。已授權收尾不能用另一個受限問題取代必要修正，所以該階段不走受限引導。具體分支及總期限以 `answer_delivery_service.py` 為準。備援不冒充歷史人物正常生成，不據此推進 EBL。未採用候選不成為 Learner 可見訊息；Admin 可展開審查／交付紀錄。沒有 findings 不等於保證完全正確。

- `LLM_ANSWER_REVIEW_ENABLED` 控制開關；`LLM_ANSWER_REVIEW_MODE` 選 `observe`／`before_delivery`。支援正式交付前審查，不可只看程式預設就聲稱部署已啟用。
- 通用內容驗證另由 `LLM_CONTENT_VALIDATION_ENABLED` 控制；格式驗證不能被這個開關取代。
- observe 不因重整／讀取舊對話重複付費；遺留待處理審查重啟後記中斷，不自動補跑。
- 審查只寫回仍存在且原文 hash 未變的訊息；刪除活動後不重建舊訊息。額外 audit 寫檔失敗不能使已成功聊天失敗。
- Learner API、SSE、polling、載入對話與下一回合 Prompt 均排除私有審查資訊；不顯示「已通過檢查」。

## Chat、畫面與計時

`chat_service.py` 先保存 Learner 訊息和 operation，再呼叫模型。相同 request 的重播／polling 不重呼叫；失敗後的**明確重試會重新呼叫**，但沿用原提問。每段對話一次只允許一個 active operation。重啟後殘留工作標為中斷／可重試，不建立多機 worker。

`POST /api/chat` 是完整 JSON 回應；`POST /api/chat/stream` 提供 SSE 流程事件，斷線可透過 operation polling 恢復。不要把 SSE 當成已核准文字逐 token 對外暴露。

`learning_focus.py` 決定目前題目；前端 `StudySplitView.vue` 把閱讀材料／當前題目與聊天分開，桌面可拖曳調整比例。01/03 不冒充正在處理某個 EBL 錯誤。四組可查看共用固定材料；圖片給 Learner 看，LLM 未接收圖片像素，只取得相關文字。

計時以後端 `timer_ends_at` 為準。刷新、重開不重置；Admin 可 reset timer。到期未完成的 EBL **已談到的目前題目**，由 `SessionService._closure` 取凍結正解和 `source_text` 修正說明，不另呼叫 LLM、不公布未談過的題目。重述保存為 `session_closure_restatement`、`independent_mastery=false`，不新增聊天回合或算進五分鐘；缺少完整修正資料回報需研究員協助，不猜答案。

前端流程責任：`useExperimentSession` 管初始化／恢復，`useTaskGate` 管草稿／提交／polling，`useConversationSession` 管載入／SSE／重試，`useAdminWorkspace` 管管理資料。

## API 索引

以下是流程索引，不重複維護完整 request schema；精確欄位以 FastAPI `/openapi.json` 與 `schemas/requests.py`、`responses.py` 為準。

| 用途 | 入口 |
| --- | --- |
| Catalog | `GET /health`、`GET /api/conditions`、`GET /api/events`、`GET /api/personas`、`POST /api/event/check` |
| 初始化／受測者 | `POST /api/event/initialize`、`GET /api/participants/me` |
| Session | `GET /api/sessions/progress`、`GET /api/sessions/{session_id}/state`、`POST /api/sessions/{session_id}/closure` |
| Task | `PATCH /api/tasks/{task_id}/draft`、`POST /api/tasks/{task_id}/submit`、`GET /api/tasks/attempts/{attempt_id}` |
| Conversation | `POST /api/conversations`（相容入口）、`GET /api/conversations/{conversation_id}` |
| Chat | `POST /api/chat`、`POST /api/chat/stream`、`GET /api/chat/operations/{client_request_id}` |
| Admin | `/api/admin/*`：snapshot、participants、events、tasks、personas、conditions、prompt-preview／dry-run、sessions timer／restart、research logs／replay／export |
| 全域 LLM 用量 | `GET /api/admin/llm-usage`，同樣需 `x-admin-key`。 |

公開事件清單只帶 Task 摘要，不含文章、題目與正解；Learner Task／Conversation 依階段過濾，Admin snapshot 保留完整資料。Persona 的新增／編輯／DELETE 相容路由有 Admin 保護，DELETE 是封存。背景圖重新生成的空端點不再是正式功能。

## 設定與紀錄

- `LLM_PROVIDER=litellm`；`LLM_MODEL` 及相應 API key 決定實際模型，不自動切 provider。文件不把某次實測模型當作永久設定。
- 全域預設 temperature 0.3、max output tokens **16384**、timeout 60 秒；上限不是目標篇幅，也不能保證絕不截斷。
- 暫時性 provider 錯誤同模型最多重試一次，結構格式可修復一次；這與交付前兩次內容修正是不同預算。
- DB 使用 `SUPABASE_SERVICE_ROLE_KEY` 等後端設定；密鑰不可進前端、文件或匯出。
- `messages.metadata` 保存回覆、模型／用量及審查資料；`research_logs` 保存素材／Prompt 快照、行為與收尾。
- `.dev-logs/llm-usage.jsonl` 是獨立持久用量帳本，包含 dry-run／隔離測試等不建立 Session 的呼叫。
- Admin 的各階段 Token、美元估算及可調匯率台幣換算，詳見[研究資料與用量](research-data-export.md)。全域帳本與 Session 統計有重疊，不能相加。
- DB 表、FK、NOT NULL、unique 與 JSONB 職責見[Schema](supabase-schema.md)。不另建逐題判分表、審查表或版本平台。

## 驗證紀錄與限制

2026-09-06 填空 Judge v4 改動後，前一輪執行的範圍：

- 聚焦後端回歸：362 passed；既有 4 則 HTTP 422 deprecation warnings。
- 前端單元測試：101 passed。該次未重跑 Nuxt build。
- 單次真實 Terra low，法國大革命同一題四個判例：句末標點、等義改寫均通過；錯誤材料不通過；答案對但理由錯仍為 incorrect。
- 3,762 tokens，8.449 秒，估算 US$0.013694；用量帳本 correlation ID：`ec42f8e7-4896-4f1b-9049-49708627f092`。
- 無 DB 寫入、無重試。這是小樣本，不是正式判分信效度或完整四事件驗收。

本輪僅同步文件；沒有重跑上述程式測試或新增付費呼叫。之後修改判題應更新既有測試，不重複建立同樣測試。正式材料、Judge 抽樣複核、人物時間界線與 HAT 設計仍見 backlog。
