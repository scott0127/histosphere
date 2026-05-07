# Frontend Audit Notes

更新日期：2026-05-07

## 研究目標對照

參考 `Design_rationale_05-01 (2).pdf`，目前研究目標偏向：

- 建立並實證評估 AI-driven historical role-play system。
- 結合 Error-Based Learning (EBL) 與 contextual scaffolding。
- 培養 beginner-to-intermediate learners 的 historical thinking 與 AI literacy。
- 讓學生練習面對錯誤資訊、AI hallucination、fake/post-truth 資訊。

因此 rebuild 時，前端核心應該服務「學習流程、錯誤辨識、反思、鷹架提示、研究資料收集」，而不是只展示沉浸式歷史角色扮演。

## 目前前端結構摘要

### pages

| 檔案 | 摘要 | 初步判斷 |
|---|---|---|
| `pages/index.vue` | 首頁主流程：事件輸入、事件列表、地圖模式、教學/回饋入口、刪除事件、傳說確認、事件初始化與進入聊天。 | 核心頁，但過大，混合 UI、資料存取、流程控制與 modal 管理。 |
| `pages/chat.vue` | 對話頁：讀取 `conversationId`，載入或接續 `chatData`，處理送訊息、背景重繪、更新人物資料。 | 核心頁，但 API orchestration 與 UI state 可抽成 composable。 |
| `pages/tutorial.vue` | 新手教學導覽，包含互動展示與動畫。 | 若研究流程需要 onboarding 可保留；若改成正式實驗流程，應重寫成研究任務導引。 |
| `pages/profile.vue` | 使用者個人資料、密碼更新、登出。 | 若實驗需要帳號或追蹤學習紀錄可保留；否則可延後。 |
| `pages/auth/login.vue` | 登入頁，依賴 `useAuth`。 | 視研究是否需要帳號制決定。 |
| `pages/auth/register.vue` | 註冊頁。 | 同上。 |
| `pages/auth/forgot-password.vue` | 忘記密碼頁。 | 同上。 |
| `pages/auth/reset-password.vue` | 重設密碼頁。 | 同上。 |
| `pages/EventListOrigin.vue` | 舊版事件列表元件被放在 pages 目錄，但不是 route-oriented page，也沒有被引用。 | 高優先移除候選。 |

### components

| 檔案 | 摘要 | 初步判斷 |
|---|---|---|
| `components/AnnotatedText.vue` | 將訊息中的 annotation term 切成 tooltip 標註。 | 可保留，對 scaffolding 有用。需檢查 regex 與重疊標註。 |
| `components/Typewriter.vue` | 對最新 AI 回覆做逐字顯示，完成後交給 `AnnotatedText`。 | 可保留或降級；研究情境中動畫可能影響閱讀時間與量測。 |
| `components/AuthButton.vue` | 登入狀態按鈕、導向登入/個人資料、登出。 | 取決於帳號需求。 |
| `components/BookInputForm.vue` | 書本視覺版事件輸入表單，含圖片 overlay、placeholder 輪播、外部事件填入。 | 視覺 prototype 味道重；若 rebuild 追求研究可控性，可移除或簡化。 |
| `components/PersonaInputForm.vue` | 卡片式事件輸入表單，含品牌文案、placeholder 輪播、外部事件填入。 | 和 `BookInputForm` 功能重疊，二選一即可。 |
| `components/EventList.vue` | 書本/卡牌風事件列表，含展開詳情、人物、來源、傳說確認、刪除。 | 目前被 `index.vue` 使用；但和 classic/origin/cinematic 重複。 |
| `components/EventListClassic.vue` | 經典卡片式事件列表，功能與 `EventList.vue` 高度相同。 | 若不需要 UI mode toggle，可移除其中一版。 |
| `components/CinematicEventList.vue` | 電影感事件列表，未被引用。 | 高優先移除候選。 |
| `components/HistoricalMap.vue` | Leaflet 地圖，將有座標的事件顯示為 pin，可進入事件。 | 若研究目標需要時空定位可保留；否則是支線功能。 |
| `components/ImmersiveLoading.vue` | 事件初始化時的沉浸式 loading 與進度動畫。 | 可保留簡化；目前偏展示效果。 |
| `components/ChatScreen.vue` | 主要聊天 UI：訊息、人物側欄、關聯事件、指定人物回覆、RAG 來源、卡牌入口、輸入框。 | 核心元件，但太大，內含 API 呼叫、導航、localStorage 與流程邏輯。 |
| `components/HistoricalFiguresList.vue` | 聊天側欄人物列表，顯示人物與重繪頭像。 | 可保留，但重繪頭像較像 prototype/admin 功能。 |
| `components/PersonaCardModal.vue` | 人物卡牌、解鎖挑戰、提示、說話影片生成。 | 功能有 EBL 潛力，但目前是大型 modal 且混合多個研究機制，需重新定義。 |
| `components/modals/DeleteConfirmationModal.vue` | 刪除確認。 | 可保留。 |
| `components/modals/LegendConfirmationModal.vue` | 傳說/非正史確認。 | 若研究聚焦史實與 misinformation，可改成更嚴謹的 source/fiction warning。 |
| `components/modals/FeedbackModal.vue` | 回饋表單，送 `/api/feedback`。 | 若研究資料收集需要可保留；需改成 consent-aware 的研究問卷或事件紀錄。 |

### composables

| 檔案 | 摘要 | 初步判斷 |
|---|---|---|
| `composables/useAuth.ts` | Supabase auth 單例，提供登入、註冊、登出、重設密碼、更新 profile、JWT。 | 可保留，但應改用 Nuxt runtime config，並處理 auth listener unsubscribe。 |

## 目前可移除候選清單

先不要直接刪，建議依研究新版需求確認後分批處理。

### 高可信度可移除

- `components/CinematicEventList.vue`：目前沒有被任何檔案引用。
- `pages/EventListOrigin.vue`：看起來是舊版 `EventListClassic.vue` 的備份，而且放在 pages 會變成不必要 route。
- `.nuxt/`：Nuxt 產物，可由 dev/build 重新產生，不應納入整理重點或版本控管。

### 中可信度可移除或合併

- `components/EventListClassic.vue` 或 `components/EventList.vue`：兩者功能重疊，差別主要是視覺風格。rebuild 建議選一個列表體驗。
- `components/BookInputForm.vue` 或 `components/PersonaInputForm.vue`：兩者都是事件輸入。若研究需要穩定、可控、易量測的流程，建議保留較簡潔的一版。
- `pages/tutorial.vue`：若新版研究流程改成 task-based onboarding，可重寫而不是沿用。
- `components/ImmersiveLoading.vue`：若初始化時間短，沉浸式 loading 會增加等待與情緒干擾，可簡化。
- `components/HistoricalMap.vue`：若新版研究問題不測時空地理探索，可先移除支線。

### 需依研究設計決定

- `components/PersonaCardModal.vue`：它有 EBL 的潛力，因為包含挑戰、錯誤回饋、提示與解鎖；但如果研究目標改成「AI hallucination/error detection」，目前的卡牌挑戰可能需要重設。
- Auth 相關 pages 與 `useAuth.ts`：若需要 participant tracking、pre/post test、log attribution，保留；若只是公開 prototype，可暫時移除。
- `components/modals/FeedbackModal.vue`：若作為正式研究資料，不應只是一般意見回饋，需改成有同意書、題項、時間戳與匿名 ID 的資料收集。

## 過往設計問題與風險

### 1. 頁面/元件責任過大

- `pages/index.vue` 約 600+ 行，同時處理 layout、資料抓取、事件初始化、刪除、modal、地圖模式、mobile menu、feedback、view count。
- `components/ChatScreen.vue` 約 500+ 行，除了 UI 還處理 event switching、API 呼叫、navigation、`localStorage`。
- `components/PersonaCardModal.vue` 約 400+ 行，把人物資料、挑戰、提示、影片生成、解鎖流程放在同一個 modal。

建議：把研究流程拆成 composables，例如 `useEvents`, `useConversation`, `usePersonaCards`, `useResearchSession`。

### 2. Prototype UI 分支太多

`index.vue` 同時保留 book UI、classic UI、map mode、mobile menu、feedback、tutorial。這讓 rebuild 時很難判斷「真正的學習流程」是哪一條。

建議：先定義新版 MVP flow：

1. participant/session setup
2. historical scenario introduction
3. AI role-play interaction
4. deliberate error / hallucination detection task
5. reflection/scaffolding
6. data export or completion

然後只保留服務這條流程的 UI。

### 3. 前端直接依賴大量 backend endpoint

多個元件直接 `$fetch('/api/...')`，包含 `ChatScreen`, `HistoricalFiguresList`, `PersonaCardModal`, `FeedbackModal`, `pages/index.vue`, `pages/chat.vue`。

風險是 endpoint 變動時會散落修改，研究資料紀錄也不容易統一。

建議：集中到 composables 或 API client layer。

### 4. 跨頁資料傳遞脆弱

目前主要靠：

- `useState('chatData')`
- query string `conversationId`
- `localStorage.pendingEventSearch`
- `window.dispatchEvent('fillEventName')`

這些方式在重新整理、SSR、測試、自動化紀錄時容易不穩。

建議：conversation/session 以 URL + backend reload 為主，前端 state 只做 cache。

### 5. 研究目標尚未反映到 UI 架構

PDF 目標強調 EBL、AI literacy、historical thinking、contextual scaffolding，但目前 UI 比較像「歷史事件角色扮演展示」。錯誤辨識、反思、證據比較、AI hallucination handling 還不是主流程。

建議新增/重構：

- error prompt 或 suspicious claim highlight
- source comparison panel
- student judgement input
- confidence rating
- scaffolded hint sequence
- reflection note
- event log for research analysis

### 6. 研究資料與一般互動資料沒有分層

`/api/stats/view-count/increment`、`/api/feedback`、chat message、persona unlock 等行為散落各處。若之後要做論文實驗，應區分 product analytics、learning trace、research survey。

建議：建立 `ResearchSession` 型別與統一 logging composable。

### 7. Auth 設定方式不夠 Nuxt 化

`useAuth.ts` 使用 `import.meta.env.VITE_SUPABASE_URL` 與 `VITE_SUPABASE_ANON_KEY`。Nuxt 專案更適合使用 `runtimeConfig.public`，也更容易在部署時管理。

另外 `onAuthStateChange` 沒有保存 unsubscribe，長期可能重複註冊 listener。

### 8. 使用 browser native alert/confirm

多處使用 `alert()` / `confirm()`。這在研究流程中不利於一致 UI、可近用性與資料紀錄，也不容易測試。

建議統一成 modal/toast/service。

### 9. 視覺隨機性可能影響研究一致性

首頁粒子、教學粒子、loading progress 使用 `Math.random()`。如果研究需要一致刺激或錄製操作流程，這些隨機動畫可能干擾。

建議在研究模式下關閉或使用 deterministic seed。

### 10. 型別有舊版痕跡

`types/index.ts` 有「新增」「原有介面調整」等註解，`HistoryItem`, `Source` 可能是早期 local history 模型。`any` 也出現在 chat/index flow。

建議：以目前 backend contract 重建 type layer，移除舊介面或標記 deprecated。

## 建議 rebuild 順序

1. 決定新版研究流程與是否需要帳號制。
2. 先刪未引用舊 UI：`CinematicEventList.vue`, `pages/EventListOrigin.vue`。
3. 在事件輸入與事件列表中只保留一套 UI。
4. 把 `index.vue` 的 API 與流程抽成 `useEvents` / `useEventInitialization`。
5. 把 `chat.vue` + `ChatScreen.vue` 的 API 與對話 state 抽成 `useConversation`。
6. 重新設計 `PersonaCardModal`：保留 EBL 相關機制，移除與研究無關的影音展示或把它降成 optional。
7. 新增研究模式：logging、反思題、錯誤辨識題、source comparison、AI literacy evidence。

