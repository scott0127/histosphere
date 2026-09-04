# Research Experiment Backlog

更新日期：2026-09-04

## 文件用途

本文件是 Histosphere 唯一的詳細待辦清單，只保存尚未定案、暫緩或已接受風險的事項。

- 已確認的長期原則寫入根目錄 `記憶.md`。
- 子系統完成狀態寫入 `docs/histosphere-system-map.html`。
- 已完成項目不在本文件重複維護。
- 系統是研究者現場控制的碩士實驗，不依公開 SaaS 的威脅與規模過度設計。

## 正式收案前必須定案

### 1. 正式事件與素材內容

- 確認正式事件清單。目前簡報列出霧社事件、甲午戰爭、黑船事件到明治維新、法國大革命；系統現有素材包含鴉片戰爭，兩者尚未對齊。
- 完成每個事件的前置 Task 文本、題目、參考答案、rubric 與必要史實審查。
- 確認每個事件唯一啟用的歷史人物、人物知識邊界與肖像。
- Pilot 後鎖定正式素材，確保同一批受測者使用相同內容。

### 2. Historical Thinking outcome 測量

前置 Task 只建立後續對話的錯誤，不是前測、後測或 outcome score。正式成效測量仍需與教授確認：

- 是否採 HAT 式短史料建構題，並使用同事件的新史料。
- rubric 要評哪些 Historical Thinking 能力，以及史實知識是否分開計分。
- 專家審查、少量 think-aloud pilot、盲評與抽樣複評方式。
- 施測時點、題數、時間、評分者訓練與評分者一致性。

### 3. Historical EBL 完成與錯誤切換規則

- `RESOLVED` 是否一律要求正確答案、至少一項證據或理由，以及反思；或依題型設定不同 success criteria。
- 正確但缺乏論證時應停在哪個 EBL state。
- `unanswered` 題目應依原順序處理、排到最後，或不進入錯誤佇列。
- D4 後 learner 主動略過所產生的 `unresolved_after_max_support` 是否可返回，以及實驗結束時如何呈現。

### 4. 正式實驗程序

- 每位 participant 的 rounds、Condition 配對、事件配對與 counterbalancing 表。
- Task 與 Chat 是否各自計時；目前程式只將 Chat 的五分鐘倒數視為正式階段計時。
- 輪間休息、後測、訪談與整體實驗時長。
- Participant 排除、缺漏資料與中途中止的處理規則。

### 5. Engagement 與質性資料

- Role-play engagement／interaction experience 的量表或訪談題綱。
- 是否記錄沉浸感、人物可信度、認知投入與互動負荷。
- 量化結果、完整對話與訪談資料如何以 participant code 合併。

## 重要但暫緩

### 受控 AI 歷史錯誤與 Debrief

目前正式功能保持停用。未來若作為共同後測，需要先定義：

- 研究者撰寫並審查的錯誤內容與版本。
- learner 要進行 detection、correction 還是 evidence-based rebuttal。
- 計分方式、錯誤暴露紀錄與結束後 Debrief。
- 不允許模型自行臨時捏造待測錯誤。

### Learner 是否顯示事件介紹

目前 learner 首頁與事件詳情只顯示事件名稱、年代、插圖、人物及 Task 狀態，不顯示事件介紹。正式收案前需確認背景介紹是否會改變先備知識與 Task 作答。

### 中性史料卡

尚需定義史料卡的來源、引用、evidence ID、可見時機與互動方式。RAG 未啟用前，可先由研究者管理少量固定史料。

### Persona 多狀態肖像

固定人物肖像已支援；同一人物的聆聽、回顧或追問等多狀態圖片暫緩。若實作，必須維持同一人物外貌，不增加新的實驗操弄。

## 技術性暫緩

### RAG

暫不實作。未來需先決定來源授權、chunking、retrieval scope、citation UI、無證據行為，以及與 persona knowledge boundary 的關係。

### 進階 Material Version Schema

目前使用 material lock、研究 metadata 與 prompt/material hash 已足以支援單一批次實驗。只有多批次收案、素材修改後重跑或需要視覺化版本比較時，才建立完整版本表。

### 多機背景工作佇列

目前單機、單一受測者環境以資料庫 operation 狀態、polling 與 process-local worker 恢復即可。Redis、Celery、Kafka 或多 instance claim 暫不需要。

### Multi-admin Roles

目前研究者與指導教授共用一組 Admin key。只有需要個別撤銷、角色權限或逐人 audit 時才重新評估。

## 已採暫行方案

### Disclosure D0／D1 私有資訊邊界

單次 structured completion 可在 private context 讀取 `correct_answer`、`source_text` 與 evidence IDs 來判斷 learner progress，但 learner-visible 回覆必須遵守 Disclosure Level。D0 不新增史實；D1 只指出檢查位置。正解洩漏時後端拒絕候選並重生，同時保存 audit 紀錄。

### Task Judge

正式 Error-Elicitation Task 只使用填空、選擇與是非；每題同時要求答案與理由。Backend 以固定規則判答案，LLM 在一次 structured call 中判所有理由。只有兩者都正確才記為 `correct`，其他情況皆為 `incorrect`。Judge 只以 `factual_error`／`reasoning_error` 說明問題；Big Six tags 為描述性 metadata，不參與對錯，也不是 outcome 測量。
