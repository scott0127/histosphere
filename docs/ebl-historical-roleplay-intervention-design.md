# EBL Historical Role-play Intervention Design

更新日期：2026-08-20

## 1. 文件角色

本文件定義 Histosphere 目前採用的 Historical EBL 與歷史人物 Role-play 介入規格，不負責追蹤完成度或保存待辦。

- 長期已確認原則：根目錄 `記憶.md`
- 子系統完成狀態：`docs/histosphere-system-map.html`
- 尚未定案事項：`docs/research-experiment-backlog.md`
- Backend/API 實作：`docs/architecture.md`

若本文件與程式不一致，需先檢查是否有更新後尚未同步的研究決策，不可直接假設任一方正確。

## 2. 研究範圍

Histosphere 的主流程是：

```text
前置 Task 產生錯誤或知識缺口
-> Task Judge 建立逐題診斷結果
-> AI 對話把目前錯誤轉成學習機會
-> 02／04 使用 Historical EBL 引導修正
-> 另外的前後測評估 Historical Thinking outcome
```

前置 Task 不是前測、後測，也不直接測量六個 Historical Thinking 維度。它只提供後續對話所需的 learner error profile。

「受控 AI 歷史錯誤」不屬於目前主 2x2 介入，正式功能保持停用；若未來作為共同後測，必須先定義錯誤內容、計分與 Debrief。

## 3. 2x2 實驗條件

| Condition | 身分呈現 | 互動方式 | 管理端簡稱 |
| --- | --- | --- | --- |
| 01 | 中性 AI 歷史助教 | Standard Chat | Baseline |
| 02 | 中性 AI 歷史助教 | Historical EBL | AI Error-based Learning |
| 03 | 歷史人物第一人稱 | Standard Chat | AI Role-play Learning |
| 04 | 歷史人物第一人稱 | Historical EBL | EBL AI Role-play |

### 共同固定條件

四組共用：

- 相同事件、Task、題目與參考答案。
- 相同模型、全域模型參數與五分鐘 Chat 時間。
- 相同史實準確性、術語精確性、前後一致性與離題規則。
- 相同 conversation memory 與研究 metadata。
- Role-play 組只能改變人物身分、第一人稱語氣與時代情境。

02 與 04 必須共用相同的目前錯誤、允許 EBL states、Disclosure 範圍、evidence IDs 與答案資訊邊界。04 不得因角色扮演增加額外證據或提示。

## 4. Task Error Profile

### 4.1 判定目的

Task Judge 只判定哪些作答可成為後續對話的學習目標，不產生正式研究分數。

### 4.2 題型責任

- `cloze`、`multiple_choice`、`true_false` 的客觀答案：backend 以固定規則判定。
- 每一題的 learner 理由：LLM 在單次 structured call 中，依完整閱讀材料與研究者設定的 `reasoning_criteria` 判定。

每題只使用二分結果：

- `correct`
- `incorrect`

只有「答案正確且理由正確」才是 `correct`。Judge 可記錄 `factual_error`、`reasoning_error`，並以零至六個 Big Six tags 描述 learner 回覆；tags 不參與對錯、不要求 learner 使用特定術語，也不是 Historical Thinking outcome。

### 4.3 後續用途

- Learner 回顧保留原句，將題目位置顯示為 learner 實際答案，再標示結果。
- Standard Chat 將逐題結果視為背景，不強制逐錯誤處理。
- Historical EBL 依 Task 順序選取未解決目標，一次只處理一個。
- `unanswered` 是否排到最後仍待研究設計確認。

## 5. Historical EBL Scaffold

Historical EBL 決定受測者這一回合練習的歷史思考行為；Disclosure Level 只決定可提供多少資訊。兩者不得混為同一個 level。

### 5.1 對話 states

1. `ELICIT_REASONING`：請 learner 外顯原答案與推論。
2. `INSPECT_EVIDENCE`：定位與目前判斷有關的文本、史料或線索。
3. `CONTEXTUALIZE_OR_COMPARE`：執行合適的時間、脈絡、因果、觀點、證據、延續與變遷、重要性或倫理操作。
4. `REVISE_CLAIM`：由 learner 以主張、證據與理由修正判斷。
5. `REFLECT`：辨認原推論忽略的內容與改變判斷的依據。
6. `RESOLVED`：符合目前 success criteria 後才切換下一個錯誤。

### 5.2 Historical Thinking 操作

Task Judge 不預先替每題分類六個向度。02／04 的 LLM 依目前錯誤、learner 最新回覆與 backend 提供的 evidence boundary，在當回合選擇一項適合的 Historical Thinking 操作。

Backend 仍負責限制：

- 目前可處理的唯一錯誤。
- 合法 state transition。
- 可用 evidence IDs。
- forbidden answer aliases。
- Disclosure Level 範圍。
- 是否可標記 `RESOLVED`。

LLM 不得自行改變 Condition、跳到第二個錯誤、使用未核准證據或提前揭露正解。

## 6. Disclosure Level D0-D4

`L0-L4` 作為 Historical EBL scaffold 的舊命名已廢除。正式名稱是 Disclosure Level D0-D4。

| Level | 可提供內容 | 禁止內容 |
| --- | --- | --- |
| D0 | 重述 learner 作答、請其說明理由 | 新史實、答案線索 |
| D1 | 指出應檢查的時間、人物、地點、物件、關係或史料位置 | 引用包含正解的內容、新數字或比較結果 |
| D2 | 提供一項既有史料線索、脈絡或關係 | 完整結論、正解或正解同義詞 |
| D3 | 提供兩項線索、比較框架或論證句型，可排除一條錯誤路徑 | 代替 learner 完成主張 |
| D4 | 整理最強證據組合與判斷限制，保留關鍵答案空缺 | 完整正解或正解同義詞 |

### 6.1 選擇規則

- AI 開場使用 D0 與 `learner_progress=not_assessed`。
- 後續每回合由同一次 structured completion 評估 progress、選擇允許的 Disclosure Level 並產生回覆。
- 相對前一回合最多上升、維持或下降一級。
- 沒有進展可增加支援；部分進展可維持；較獨立的推理可降低支援。
- 偏離事件時保持目前錯誤、state 與 Disclosure，不把離題當成 scaffold 失敗。
- D0-D4 都不得直接公布完整正解。

### 6.2 私有資訊邊界

單次 LLM 呼叫可在 private context 取得 `correct_answer`、`source_text` 與 evidence IDs，以判斷 learner progress；這不代表可向 learner 顯示。

Backend 以 Prompt 規則、結構化欄位、合法 transition、正解／來源文字洩漏檢查與 rejection audit 管理可見內容。違規候選必須拒絕並重新生成，不可只修改 metadata。

### 6.3 D4

D4 失敗不自動公布答案或結束。Learner 可繼續互動；只有 learner 主動選擇下一個錯誤時，才記錄 `unresolved_after_max_support` 並從下一題的 D0 開始。

## 7. Standard Chat

01／03 是 Standard Chat，不是「第一句直接公布 Task 正解」。

- 回答 learner 實際提出、且與事件有關的問題。
- 可自然澄清或追問，但不主動執行 evidence-revision-reflection sequence。
- 不依 learner progress 制度化地保留答案或調整 Disclosure。
- 明顯離題時不回答實質內容，只簡短重新定位到目前事件。

03 與 01 的互動政策一致；03 只使用歷史人物第一人稱呈現。

## 8. Historical Persona Renderer

Role-play 是 renderer，不是另一套教學策略。

- 使用第一人稱與人物所處事件的當下情境。
- 維持人物地位、語彙、立場與可知資訊邊界。
- 不知道死亡後事件，不把後世研究說成親身記憶。
- 將同一 pedagogical act 轉為人物自然的回憶、處境、選擇或反問。
- 不使用「請使用證據」「請進行因果思考」等教師或 policy 術語。
- 離題時以該人物自然語氣表達不理解或不屬於其處境，不回答離題問題，也不使用固定拒絕句。

每個事件同時最多一位 active persona。Learner 不得選擇或切換人物；Admin 負責新增、啟用、停用與封存。

## 9. Prompt Pipeline

Opening 與後續對話使用同一套 backend canonical modules，差別只在 `turn_intent` 與是否已有 learner message。

```text
General Prompt
-> independent_2 Prompt：Standard Chat 或 Historical EBL
-> Event Context
-> Learner Task / current error
-> Interaction Runtime
-> DB-backed Conversation History
-> independent_1 Prompt：Generic 或 Persona renderer
-> Persona Event Context
-> Source Context
-> Turn Intent
-> Runtime Policy
-> Current Learner Message
-> 單次 structured LLM completion
-> Backend validation
-> Persist message and research metadata
```

正式 runtime 鎖定單一 provider/model；暫時錯誤最多使用同一模型重試一次，不自動切換 provider。

## 10. Structured Output 與後端驗證

主要欄位：

- `response`
- `dialogue_state`
- `dialogue_move`
- `disclosure_level`
- `learner_progress`
- `disclosure_reason`
- `learner_revision_status`
- `completion_status`
- `off_topic_redirect`
- `fidelity_flags`

Standard Chat 固定使用 `STANDARD_CHAT`、`natural_response`、`completion_status=continue`，且沒有 Disclosure Level。

Historical EBL 的 backend 會驗證 state、move、Disclosure 相鄰限制、正解洩漏、人物邊界、下一錯誤切換與離題行為。未通過的候選不保存為正式 AI message。

## 11. Conversation Memory 與研究紀錄

- 對話歷史由 database `messages` 依 `sequence_index` 還原，不信任前端傳入的 history。
- 不固定只取 12 則；由最新訊息往前填入 16,000 字元總預算，每則最多 1,600 字元。
- Learner message 先保存，再進行 LLM 生成。
- 每次 LLM 呼叫保存 provider、model、prompt/profile/material hash、latency、token、attempt、repair、failure category 與 finish reason。
- 02／04 另保存實際 state、Disclosure、progress、target question、evidence 與 fidelity flags。

## 12. Measurement Boundary

Task Judge 的 `correct / incorrect` 只用來建立後續對話的 learner error profile，不應直接當作 Historical Thinking outcome。

正式 outcome 應由獨立前後測或建構題 rubric 測量。HAT 式短史料建構題是目前候選方向，但正式維度、題數、評分規則與評分者一致性仍需和教授定案。

## 13. Evidence Basis

### Core literature

- [Tirado-Olivares et al. (2023), Training future primary teachers in historical thinking through error-based learning and learning analytics](https://www.nature.com/articles/s41599-023-01537-w)：支持把受控錯誤用於 detection、correction 與 reflection；不直接驗證 LLM persona conversation。
- [López-Fernández et al. (2023), Putting critical thinking at the center of history lessons in primary education through error- and historical thinking-based instruction](https://www.sciencedirect.com/science/article/pii/S1871187123000858)：支持歷史教育中的 error-based activities 與資訊真實性反思；研究形式不同於本系統。
- [Park et al. (2025), Ask Sir Oliver Ingham](https://doi.org/10.1145/3706599.3719728)：支持 teacher-controlled historical simulation、learning objective alignment 與 limited character perspectives；對學生 outcome 主要是間接證據。
- [Kim et al. (2025), HistoChat](https://doi.org/10.1145/3757534)：支持歷史人物對話、perspective-taking、conversation history 與適度主動引導；未驗證 Histosphere 的 EBL state machine。

### Framework sources

- [Van Drie and Van Boxtel (2008)](https://link.springer.com/article/10.1007/s10648-007-9056-1)：historical reasoning process framework。
- Seixas and Morton (2013), *The Big Six Historical Thinking Concepts*：Historical Thinking second-order concepts。
- [Van de Pol, Volman, and Beishuizen (2010)](https://link.springer.com/article/10.1007/s10648-010-9127-6)：contingency、fading 與 transfer of responsibility；屬間接 scaffold 依據。
- [Loibl and Leuders (2019)](https://doi.org/10.1016/j.learninstruc.2019.03.002)：error exposure 之外仍需要 elaboration／comparison prompts；不直接驗證歷史人物對話。

## 14. 主張限制

- D0-D4、相鄰升降與目前 state machine 是 Histosphere 的操作化設計，不可宣稱文獻已直接驗證這套 enum。
- 不可預設 Role-play 必然提升 Historical Thinking；這是研究要測量的效果。
- 不可預設 Historical Thinking 必然遷移到 AI literacy。
- 不可把模型自行產生的 hallucination 當作 EBL controlled error。
