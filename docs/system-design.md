# 系統設計導讀

更新日期：2026-09-19。

本頁已整併，不再獨立維護第二份系統規格。原本的流程、前後端責任與資料契約已收斂到以下文件：

目前單輪流程為 **Task → Chat → 必要的收尾重述 → 活動回饋（Engagement）→ HAT → 本輪完成**。後測已串接到系統內，支援草稿續填與提交；目前三題活動回饋及兩題 HAT 都是 Pseudo 題，尚未加入正式量表、史料題本或評分。對話結束不等於整輪完成，下一個已指派條件須等本輪後測提交後才開放。

| 想知道什麼 | 唯一主要位置 |
| --- | --- |
| 系統如何運作、各層負責什麼 | [技術架構](architecture.md) |
| 第一次接手，想看圖解 | [後端與資料庫交接手冊](backend-database-handbook.html) |
| 四種 Condition、EBL、人物與 Disclosure | [介入規格](ebl-historical-roleplay-intervention-design.md) |
| 哪些做完、哪些還沒做 | [System Map](histosphere-system-map.html) |
| 後測流程、操作與正式題本的待辦邊界 | [System Map：後測階段](histosphere-system-map.html#posttest-flow) |
| 後測資料表、版本與存取限制 | [Supabase schema](supabase-schema.md#session_posttests) |
| 後測 JSON／CSV、完成狀態與占位資料標記 | [研究資料匯出](research-data-export.md#占位後測欄位) |
| 已確認研究原則 | [記憶.md](../記憶.md) |
| 尚未定案與暫緩項目 | [研究 backlog](research-experiment-backlog.md) |

本檔只為舊連結保留，可在確認外部引用不再需要後刪除。不要再把 API、Judge JSON 或研究待辦複製回此頁。
