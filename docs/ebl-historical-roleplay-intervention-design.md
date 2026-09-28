# EBL Historical Role-play Intervention Design

更新日期：2026-09-06。描述已確認並已落地的操作規則，不宣稱已完成研究效度驗證。

## 1. 文件角色

本文件集中定義研究介入；[技術架構](architecture.md)負責實作與呼叫機制，[System Map](histosphere-system-map.html)追蹤完成度，[研究 backlog](research-experiment-backlog.md)保存唯一詳細待決清單，[記憶.md](../記憶.md)保存長期原則。

## 2. 研究範圍

**EBL 是操弄的互動教學鷹架；Historical Thinking 是四組共用的 AI 歷史回應基礎。**

Error-Elicitation Task 讓學習者閱讀材料、給答案及理由，供後續對話建立學習機會；它不是前測、後測或 Historical Thinking outcome score。LLM 不額外要求學習者練習 sourcing、contextualization、corroboration 或指定 HT 技巧。學習者可以自發使用這些能力，成效另外測量。

受控 AI 歷史錯誤與正式 Debrief 仍暫緩；不是允許模型隨意捏造錯誤的理由。

## 3. 2×2 實驗條件

| Condition | Role-play | EBL | 行為 |
| --- | --- | --- | --- |
| 01 | 無，普通 AI | 無，Standard Chat | 回答事件相關問題，不主動執行逐錯誤修正。 |
| 02 | 無，普通 AI | 有 | 聚焦目前錯誤，促進認知、反思、自我修正及回饋。 |
| 03 | 有，固定歷史人物 | 無，Standard Chat | 以人物當下的立場自然對話，不強制 EBL。 |
| 04 | 有，固定歷史人物 | 有 | 人物主導自然歷史對話，將必要 EBL 行為融入其中。 |

同一事件四組共用 Task／材料、模型政策、五分鐘時間、歷史回應品質與記憶。02/04 共用錯誤判定、允許狀態、Disclosure 範圍及收尾授權；04 不另獲得提前作答權。不能把這理解成四組逐字相同、史實數量固定，或已證明實際協助強度完全等值。

Learner 只看 01–04 代號，不顯示 EBL、Role-play、內部 state 或 Disclosure。跨事件材料等值性仍需正式驗收。

## 4. Task Error Profile

- 三種題型：選擇、是非、填空；每題都要答案和理由。
- 選擇／是非答案由規則判定；填空答案與所有理由由**同一次 LLM Judge** 依材料及研究者通過標準判定。
- 填空接受可辨識的等義表述，不要求符合窮舉答案表；仍拒絕錯誤對象、否定、矛盾或無法辨識的答案。
- `answer_correct && reasoning_correct` 才是 `correct`，否則 `incorrect`。不輸出正式研究分數。
- `answer_feedback`（填空）及 `reasoning_feedback` 具體說明判斷原因，供 Admin 與後續私有 Prompt 使用，不提前顯示給 Learner。
- HT tags 為描述，不計分、不要求學生使用術語；不再另分 factual/reasoning issue categories。
- 漏答與格式錯誤先拒絕提交；LLM 失敗是系統處理失敗，不是假學生錯誤。

01/03 可把所有逐題結果當背景，不強制逐錯誤處理。02/04 依凍結的原作答與診斷選取一項目標；答案錯或理由錯都可以成為學習機會。已有第三方 probe 的活動沿用凍結內容，不能把他人的錯誤說成學生原本答錯；無自身錯誤的研究控制仍見 backlog。

## 5. EBL 互動

目前政策為 `ebl-error-reflection-v2`，互動契約為 `2x2-interaction-v15-feedback-restatement`：

| State | 作用 |
| --- | --- |
| `NOTICE_ERROR` | 看見原答案或理由哪裡可能需要修正，不強迫重說已交過的理由。 |
| `REFLECT` | 分析原推理為什麼需要改。 |
| `SELF_CORRECT` | 學生自己重新作答並修正理由。 |
| `RESOLVED` | 鞏固已修正內容，再轉到下一個錯誤。 |

這些是學習行為，不是逐輪必須照念的問句；一個回答可同時展現反思與修正，不為跑完 state 而故意多問。舊 HT 操作名稱只作歷史資料相容，不再是強制給學生的技能清單。

獨立完成須由對話支持三項：**認知哪裡需要改、說明為何要改、修正答案及理由符合原題標準**。可跨回合累積，不要求額外引用史料或特定 HT 標籤。單純選到正解但理由仍錯不能宣告獨立完成；模型自報 RESOLVED 不能跳過後端條件。

## 6. Disclosure Level D0–D4

只限制**解題協助**，不限制所有歷史資訊、人物語氣、情緒或篇幅。材料也不是歷史知識的窮盡白名單，但引用、來源、親身經驗不能捏造。

| Level | 協助方式 |
| --- | --- |
| D0 | 回應原主張，自然邀請重新思考，先保留獨立修正空間。 |
| D1 | 指出值得懷疑的方向、區別或具體對照。 |
| D2 | 提供有用史實，解釋關係與比較，讓學生自己下修正判斷。 |
| D3 | 串起已有資訊、指出矛盾或拆解難點，明確說明推理路徑。 |
| D4 | 整理最強支持，讓學生做最後的獨立答案及理由嘗試。 |

共同上限：**正式收尾授權前，不代替學習者宣布正確選項、填空、是非結論或仍待修正的完整理由**。答案相關要素、比較或引述本身不違規；讓答案容易推得也不等於直接作答。學習者已提出的正確部分可確認。

- D0/D1 的私有 context 可以包含正解、修正說明與材料；可讀不代表可直接說。
- 開場 D0；後續由同一次主生成評估進展、在後端允許範圍選擇相鄰等級，通常最多升降一級。
- 無關問題不自動增加提示、不當成修正失敗。04 的合理歷史話題也可自然回應並保持當前目標；必要收尾不能因此被略過。
- 全面 corrective feedback 是**後端另行授權的收尾**，不是新增 D5，也不是只要模型填 D4 就可公布答案。

## 7. 修正、切題與五分鐘收尾

### 學生已獨立修正

三項條件成立 → 確認正確答案／理由 → 自然轉下一個錯誤。沒有剩餘目標則繼續歷史對話直到計時結束，不製造新錯誤或提前結束時間。

### D4 仍未修正

```text
D4 的最後獨立嘗試仍未完成
→ 先說明目前題目的正解與為何需要修正
→ 請學生用自己的話重述一次
→ 回應這次重述；若仍有錯簡短重申修正
→ 進下一個目標，不要求反覆達到完美
```

已答對但理由錯，就確認答案並修正理由。重述前使用 `corrective_resolution_pending`；重述後為 `feedback_completed`，記錄 `assisted_restatement_completed`，不冒充獨立學會。不再使用 D4 無限等待加「略過」按鈕的舊規則。

### 五分鐘到期

Chat 停止。02/04 若目前已談到的目標尚未完成，另外顯示該題凍結正解與修正解說，要求一次自己的話重述，再進下一階段。只記為計時後輔助收尾，不另呼叫 Judge，不算聊天回合，不公布未談過的其他題目。第一題可在對話內收尾，第二題可能在對話或到期畫面完成。

此操作已實作；**後測前答案暴露及額外收尾時間的研究影響仍須與教授確認**。

## 8. 歷史人物對話

人物不是現代教師套人物稱呼。03/04 的回覆要整體像處於事件當下的人，以其關注、判斷、立場及合理語氣說話；04 把 EBL 融入這段對話，不逐句排斥自然的引導問句。

- 開場自然交代人物與情境，後續不機械重複姓名、年份、地點。
- 保持人物視角，不要求每回合一定出現「我」。
- 不知道尚未發生的事，不把後世研究當作親身記憶；情緒反應是合理模擬，不宣稱真實歷史逐字紀錄。
- 遇到陌生現代／離題問題，用人物語氣表示不明白並回到原歷史話題。不復述、分類或講解自己無從知道的概念，不為每種亂問硬編一條拒絕句。
- 歷史素材可在 Learner 獨立區域呈現，不代表人物知道該出版品或看過圖片。
- **人物可否討論學習者帶來的後世資料仍未定案**，不默認放寬時間邊界。

同事件最多一位 active persona，由 Admin 啟停；Learner 不可選擇或切換。固定肖像與文字情緒不同，動態情緒圖片仍不需要。

## 9. 主生成與審查

Prompt 由共用模組及兩個因子組裝，一次主呼叫決定回覆與進展，不使用固定的第二次人物改寫流程。獨立答案審查可能再呼叫模型，交付前模式可有限修正、受限引導及明示系統備援；完整技術分支見[技術架構](architecture.md#答案審查與回覆交付)。

語意審查針對提前作答、下一題答案、授權收尾缺少修正，不是人物措辭裁判或全面史實保證。模型自報 flags 不等於獨立審查結果。Learner 不看審查狀態或被拒絕候選。

## 10. 史料素材呈現

研究者預先選定真實文本或圖片，允許不破壞事實的改寫。小標具體說明材料是什麼、何時形成，而不是只寫「圖片／史料」分類。

四組可查看固定材料。當前題目與聊天分開，桌面可調比例；後端提供目前目標，不由前端猜測。模型未使用影像辨識，不能說它「看過」圖像細節。跨事件的類型、數量、閱讀負荷與呈現一致性仍是最高優先驗收。

## 11. 研究紀錄

保存原答案／理由、Judge 版本與回饋、目前目標、EBL state、Disclosure、進展、獨立／輔助完成、審查與實際用量。歷史由資料庫載入，刷新不重新開場或重置五分鐘。Token／台幣估算及聊天回合的分別見[研究資料](research-data-export.md)。

## 12. 測量與證據邊界

Task 的 correct/incorrect 是介入診斷，不是 Historical Thinking 分數。HAT 式評量仍為候選方向，正式材料、rubric、時間與評分者一致性尚未凍結。

以下文獻項目沿用既有來源紀錄；本次同步是操作規格整理，沒有重新做全文文獻審查。D0–D4、三項完成條件、一次重述及五分鐘收尾是專案決策，不能說原文獻直接驗證了這整套自動化流程。

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
