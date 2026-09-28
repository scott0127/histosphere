# 人物回覆流程導讀

更新日期：2026-09-06。

本頁已整併，不再維護另一套 Prompt 或 D4 規格。

- **模型看見什麼、各模組做什麼**：[技術架構的 Prompt 組裝](architecture.md#prompt-組裝)。
- **一次還是多次呼叫、審查後是否重生**：[答案審查與回覆交付](architecture.md#答案審查與回覆交付)。
- **人物語氣如何自然融入 EBL、知識邊界**：[研究介入規格](ebl-historical-roleplay-intervention-design.md)。
- **效果驗收與未決問題**：[System Map](histosphere-system-map.html)、[研究 backlog](research-experiment-backlog.md)。

主回覆由一次 canonical structured completion 組合人物及互動；不是固定「教師稿 → 第二次人物改寫」。啟用交付前答案審查時，會另外呼叫審查及必要修正，因此不能把整個回合描述為永遠只有一次 LLM 呼叫。

本檔為舊連結保留，外部引用移除後可刪除。
