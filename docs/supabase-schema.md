# Supabase Public Schema Export

原結構匯出日期：2026-09-04；後測契約說明更新：2026-09-19。本次依 `202609190001_session_posttests.sql` 與目前後端程式補充後測結構，未重新完整匯出 live schema。該 migration 已套用於本機 Supabase，並完成後測儲存、版本衝突、已提交不可更新與匿名存取拒絕的針對性驗證。

來源：`supabase/migrations/`（schema 單一來源）與 local Supabase Postgres `public` schema。

本文件只記錄 Histosphere app 使用的 `public` schema，不包含 Supabase 內建的 `auth`、`storage`、`realtime`、`extensions` 等 schema。

## Summary

依既有結構匯出與新增後測 migration，本文件列出 15 個 app 使用的 `public` base tables：

| Table | Purpose |
| --- | --- |
| `events` | 歷史事件 workspace。 |
| `experiment_conditions` | 2x2 實驗條件設定。 |
| `experiment_sessions` | 一次受測者/使用者活動的歸屬與 task、chat 狀態；後測提交另存 `session_posttests`。 |
| `session_posttests` | 每次 Session 的占位後測草稿、階段與提交紀錄，目前不是正式量測題本。 |
| `wiki_sources` | Wikipedia/source fetch 結果。 |
| `knowledge_chunks` | 未來 RAG 用知識片段，目前暫緩。 |
| `event_tasks` | 對話前 task 與 story/question payload。 |
| `task_blanks` | 未來 blank-level scoring 設計表，目前暫緩。 |
| `task_attempts` | learner task submission。 |
| `task_answers` | 未來 normalized per-blank answer 表，目前暫緩。 |
| `personas` | 歷史人物 persona。 |
| `participants` | 受測者顯示代號、Auth 對應與 condition 指派清單。 |
| `conversations` | task 後開啟的聊天室。 |
| `messages` | 聊天訊息。 |
| `research_logs` | 研究流程與互動 audit log。 |

## Design Notes

- `experiment_conditions` 不保存 LLM prompt。2x2 condition prompt 由後端 `PromptService` / LLM provider 以程式碼版本控管，避免正式實驗 prompt 隨 DB 狀態漂移。
- `personas.prompt_profile` 仍保留，因為它是歷史人物的 speaking style、knowledge boundary、teacher notes 等 persona 設定，不是 condition-level LLM prompt。
- 研究主鏈的歸屬欄位已由 `202608090001_research_integrity_and_material_lock.sql` 設為 `NOT NULL` 並使用 `ON DELETE RESTRICT`，避免新增孤兒研究紀錄或連帶刪除既有資料。可選 metadata／user 欄位仍維持 nullable。
- `task_blanks` / `task_answers` 已存在但目前正式 flow 仍主要使用 `event_tasks.evaluation_payload.questions[]` 與 `task_attempts.response_payload`。
- `knowledge_chunks.embedding` 是 `vector` 型別，但目前 RAG retrieval 仍是空實作。
- `participants.auth_user_id` 對應 Supabase Auth 使用者。正式 Session 建立時，同時把當下 `participants.id` 凍結到 `experiment_sessions.participant_id`；Auth `user_id` 仍作為請求身分，日後帳號改綁不會改變舊研究紀錄歸屬。Admin test 的 `participant_id` 保持 `NULL`。
- `participants.condition_list` 以 learner-visible condition code 保存分派條件及 Admin 指定執行順序，例如 `{03,01}` 代表先做 03、再做 01。目前不另建 condition assignment table。
- 既有 14 張表的 RLS 記錄為 disabled；新表 `session_posttests` 啟用 RLS，並撤銷 `anon`／`authenticated` 的資料表權限。後端仍使用 Supabase service role，並由 FastAPI 驗證受測者與 Session 歸屬，瀏覽器不能直接存取此表。
- `events.archived_at` 是可逆封存旗標。一般 event management 不刪除 event 或其關聯研究資料。
- `experiment_sessions` timer 欄位在 Task 階段為 `NULL`；Chat 建立後由後端自動開始固定五分鐘倒數，Admin 可在該輪後測尚未開始時重置。
- `experiment_sessions.is_admin_test` 明確區分 Admin 驗證與正式受測 Session；Admin test 不進入 learner 進度或正式研究匯出。
- `events.materials_locked_at` 為最低限度素材鎖定；只有鎖定事件可供 learner 開始，鎖定期間禁止編輯 Event、Task 與 Persona。
- `task_attempts.status` 支援 `in_progress`、`processing`、`submitted`、`failed`，供非同步 task submit 與 polling 使用。
- `task_attempts.session_id` 與 `conversations.session_id` 都有 unique index；一個 Session 最多各有一筆作答與一個對話。
- `session_posttests.session_id` 也唯一；`experiment_sessions.status='completed'` 只表示本輪對話已結束，不代表後測已提交。後測需另有 `stage='completed'` 與 `submitted_at`，才能解鎖下一個已指派條件。
- 四個研究事件的 canonical Error-Elicitation Task 由 `supabase/content/error-elicitation-reading-tasks.json` 管理，migration/seed 只新增缺少的 authoring version，不改寫舊 Task、作答或對話。
- Runtime safety、chat operation、persona 生命週期、研究完整性與 Admin test 分類由既有 migrations 增量建立；`202609190001_session_posttests.sql` 另新增後測資料表，不回填或改寫既有 Session、作答與對話。

### Placeholder Posttest Contract

- `posttest_placeholder_v1` 固定提供三題活動回饋與兩題歷史思考文字作答，全部標示 `is_placeholder=true`，沒有正式題目、效度宣稱、評分或 rubric。
- 草稿可局部完成；API 只接受 `engagement_1` 至 `engagement_3` 的 1–5 整數，以及 `hat_1`、`hat_2` 的文字。進入 `hat` 前需完成三題活動回饋；提交前需完成兩題非空白 HAT 作答。這些題目與階段規則由後端驗證，DB 的 JSONB CHECK 只驗證物件型別。
- 流程依序為 `engagement` → `hat` → `completed`。進入 `hat` 後不能再改活動回饋；提交後所有內容不能修改。後測只在對話結束、且必要的計時後收尾重述完成後開放。
- `revision` 是儲存版本，每次儲存或階段切換加一。Repository 以 `session_id`、原 `revision` 與未完成階段作條件更新，避免多視窗靜默覆寫。重複開始沿用原紀錄；重複提交回傳首次已儲存結果。
- Session state／progress API 的 `posttest_stage` 是查詢時推導欄位，不是 `experiment_sessions` 的新欄位：有後測紀錄就取其 `stage`；對話已完成但尚無紀錄時為 `not_started`；其餘無紀錄時為 `null`。
- `started_at` 記錄首次開始後測，`updated_at` 由服務在成功儲存時更新，`submitted_at` 記錄最終提交；不取代原 Session 的對話完成時間。後測開始後不能重置同一輪對話倒數，需另建活動才能重新測試。

### Error-Elicitation Judge JSONB

- `event_tasks.evaluation_payload.questions[]` 保存三種客觀題、正解與研究者的 `reasoning_criteria`。
- `task_attempts.response_payload` 保存每題 learner 的 `value` 與 `rationale` 原文。
- 新判題的 `task_attempts.judgement_payload` 使用 `error_elicitation_judge_v4`：選擇／是非由 backend 判答案；填空答案與所有理由合併在一次 LLM 呼叫。保存 `answer_correct`、`reasoning_correct`、填空 `answer_feedback`、`reasoning_feedback` 與描述性 HT tags，不再輸出 factual/reasoning issue 分類。
- `correct_answer` 可含參考別名，但不是填空等義答案的窮舉表。輸入原文保留；缺少必要判定或格式錯誤是 processing failure，不是 learner incorrect。
- 本次只改既有 JSONB 內容契約，沒有新增表或欄位。已提交舊結果不重判；pending 重用要求相同輸入 hash 與 v4。詳細責任見 [architecture](architecture.md#error-elicitation-task-與-judge)。
- `messages.metadata` 沿用既有 JSONB 保存答案審查、交付及其用量；計時後重述放 `research_logs`，不另建審查或收尾資料表。
- 每題僅有 `correct`／`incorrect`；只有答案和理由都正確才通過。

## Tables And Columns

### `conversations`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `event_id` | `uuid` | NO |  |
| 3 | `task_attempt_id` | `uuid` | NO |  |
| 4 | `session_id` | `uuid` | NO |  |
| 5 | `user_id` | `uuid` | YES |  |
| 6 | `status` | `text` | YES | `'active'::text` |
| 7 | `started_at` | `timestamp with time zone` | YES | `now()` |
| 8 | `archived_at` | `timestamp with time zone` | YES |  |
| 9 | `created_at` | `timestamp with time zone` | YES | `now()` |
| 10 | `updated_at` | `timestamp with time zone` | YES | `now()` |

### `event_tasks`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `event_id` | `uuid` | NO |  |
| 3 | `title` | `text` | YES |  |
| 4 | `story_text` | `text` | NO |  |
| 5 | `error_elicitation_task_full_text` | `text` | NO |  |
| 6 | `evaluation_payload` | `jsonb` | YES | `'{}'::jsonb` |
| 7 | `revision_state` | `text` | YES | `'llm_generated'::text` |
| 8 | `created_at` | `timestamp with time zone` | YES | `now()` |
| 9 | `updated_at` | `timestamp with time zone` | YES | `now()` |

### `events`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `canonical_name` | `text` | NO |  |
| 3 | `description` | `text` | YES |  |
| 4 | `century` | `integer` | YES |  |
| 5 | `start_year` | `integer` | YES |  |
| 6 | `end_year` | `integer` | YES |  |
| 7 | `context` | `text` | YES |  |
| 8 | `source_summary` | `jsonb` | YES | `'{}'::jsonb` |
| 9 | `created_by` | `uuid` | YES |  |
| 10 | `created_at` | `timestamp with time zone` | YES | `now()` |
| 11 | `updated_at` | `timestamp with time zone` | YES | `now()` |
| 12 | `archived_at` | `timestamp with time zone` | YES |  |
| 13 | `materials_locked_at` | `timestamp with time zone` | YES |  |

### `experiment_conditions`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `condition_key` | `text` | NO |  |
| 3 | `label` | `text` | NO |  |
| 4 | `ebl_enabled` | `boolean` | NO | `false` |
| 5 | `roleplay_enabled` | `boolean` | NO | `false` |
| 6 | `agent_mode` | `text` | NO | `'generic'::text` |
| 7 | `response_policy` | `text` | NO | `'standard'::text` |
| 8 | `description` | `text` | YES |  |
| 9 | `active` | `boolean` | YES | `true` |
| 10 | `created_at` | `timestamp with time zone` | YES | `now()` |
| 11 | `updated_at` | `timestamp with time zone` | YES | `now()` |

### `experiment_sessions`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `condition_id` | `uuid` | NO |  |
| 3 | `condition_key_snapshot` | `text` | NO |  |
| 4 | `user_id` | `uuid` | YES |  |
| 5 | `event_id` | `uuid` | NO |  |
| 6 | `status` | `text` | NO | `'initialized'::text` |
| 7 | `created_at` | `timestamp with time zone` | YES | `now()` |
| 8 | `updated_at` | `timestamp with time zone` | YES | `now()` |
| 9 | `timer_started_at` | `timestamp with time zone` | YES |  |
| 10 | `timer_ends_at` | `timestamp with time zone` | YES |  |
| 11 | `completed_at` | `timestamp with time zone` | YES |  |
| 12 | `completion_reason` | `text` | YES |  |
| 13 | `is_admin_test` | `boolean` | NO | `false` |
| 14 | `participant_id` | `uuid` | YES |  |

### `session_posttests`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `session_id` | `uuid` | NO |  |
| 3 | `instrument_version` | `text` | NO | `'posttest_placeholder_v1'::text` |
| 4 | `is_placeholder` | `boolean` | NO | `true` |
| 5 | `stage` | `text` | NO | `'engagement'::text` |
| 6 | `engagement_answers` | `jsonb` | NO | `'{}'::jsonb` |
| 7 | `hat_answers` | `jsonb` | NO | `'{}'::jsonb` |
| 8 | `revision` | `integer` | NO | `0` |
| 9 | `started_at` | `timestamp with time zone` | NO | `now()` |
| 10 | `updated_at` | `timestamp with time zone` | NO | `now()` |
| 11 | `submitted_at` | `timestamp with time zone` | YES |  |

此表不重複保存 Participant、事件或 Condition；以唯一的 `session_id` 連回本輪 `experiment_sessions`。

### `knowledge_chunks`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `event_id` | `uuid` | YES |  |
| 3 | `wiki_source_id` | `uuid` | YES |  |
| 4 | `source` | `text` | NO |  |
| 5 | `source_url` | `text` | YES |  |
| 6 | `section_title` | `text` | YES |  |
| 7 | `content` | `text` | NO |  |
| 8 | `language` | `text` | YES |  |
| 9 | `char_count` | `integer` | YES |  |
| 10 | `chunk_index` | `integer` | YES |  |
| 11 | `embedding` | `vector` | YES |  |
| 12 | `metadata` | `jsonb` | YES | `'{}'::jsonb` |
| 13 | `created_at` | `timestamp with time zone` | YES | `now()` |

### `messages`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `conversation_id` | `uuid` | NO |  |
| 3 | `persona_id` | `uuid` | YES |  |
| 4 | `speaker_type` | `text` | NO |  |
| 5 | `speaker_name` | `text` | NO |  |
| 6 | `sequence_index` | `integer` | NO |  |
| 7 | `content` | `text` | NO |  |
| 8 | `annotations` | `jsonb` | YES | `'[]'::jsonb` |
| 9 | `rag_sources` | `jsonb` | YES | `'[]'::jsonb` |
| 10 | `metadata` | `jsonb` | YES | `'{}'::jsonb` |
| 11 | `created_at` | `timestamp with time zone` | YES | `now()` |
| 12 | `client_request_id` | `text` | YES |  |
| 13 | `operation_status` | `text` | YES |  |

### `personas`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `event_id` | `uuid` | NO |  |
| 3 | `name` | `text` | NO |  |
| 4 | `english_name` | `text` | YES |  |
| 5 | `role` | `text` | YES |  |
| 6 | `biography` | `text` | YES |  |
| 7 | `expertise_areas` | `text[]` | YES | `'{}'::text[]` |
| 8 | `sources` | `jsonb` | YES | `'[]'::jsonb` |
| 9 | `prompt_profile` | `jsonb` | YES | `'{}'::jsonb` |
| 10 | `avatar_url` | `text` | YES |  |
| 11 | `active` | `boolean` | YES | `true` |
| 12 | `sort_order` | `integer` | YES | `0` |
| 13 | `revision_state` | `text` | YES | `'llm_generated'::text` |
| 14 | `created_at` | `timestamp with time zone` | YES | `now()` |
| 15 | `updated_at` | `timestamp with time zone` | YES | `now()` |
| 16 | `archived_at` | `timestamp with time zone` | YES |  |

### `participants`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `code` | `text` | NO |  |
| 3 | `display_name` | `text` | YES |  |
| 4 | `cohort` | `text` | YES |  |
| 5 | `condition_list` | `text[]` | NO | `'{}'::text[]` |
| 6 | `status` | `text` | NO | `'active'::text` |
| 7 | `notes` | `text` | YES |  |
| 8 | `metadata` | `jsonb` | NO | `'{}'::jsonb` |
| 9 | `created_at` | `timestamp with time zone` | YES | `now()` |
| 10 | `updated_at` | `timestamp with time zone` | YES | `now()` |
| 11 | `auth_user_id` | `uuid` | YES |  |

### `research_logs`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `user_id` | `uuid` | YES |  |
| 3 | `session_id` | `uuid` | YES |  |
| 4 | `event_id` | `uuid` | YES |  |
| 5 | `task_id` | `uuid` | YES |  |
| 6 | `attempt_id` | `uuid` | YES |  |
| 7 | `conversation_id` | `uuid` | YES |  |
| 8 | `message_id` | `uuid` | YES |  |
| 9 | `action_type` | `text` | NO |  |
| 10 | `payload` | `jsonb` | YES | `'{}'::jsonb` |
| 11 | `created_at` | `timestamp with time zone` | YES | `now()` |

### `task_answers`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `attempt_id` | `uuid` | NO |  |
| 3 | `blank_id` | `uuid` | NO |  |
| 4 | `user_answer` | `text` | YES |  |
| 5 | `is_correct` | `boolean` | YES |  |
| 6 | `feedback` | `text` | YES |  |
| 7 | `answered_at` | `timestamp with time zone` | YES | `now()` |

### `task_attempts`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `task_id` | `uuid` | NO |  |
| 3 | `event_id` | `uuid` | NO |  |
| 4 | `session_id` | `uuid` | NO |  |
| 5 | `user_id` | `uuid` | YES |  |
| 6 | `status` | `text` | NO | `'in_progress'::text` |
| 7 | `response_payload` | `jsonb` | YES | `'{}'::jsonb` |
| 8 | `judgement_payload` | `jsonb` | YES | `'{}'::jsonb` |
| 9 | `submitted_at` | `timestamp with time zone` | YES |  |
| 10 | `created_at` | `timestamp with time zone` | YES | `now()` |
| 11 | `updated_at` | `timestamp with time zone` | YES | `now()` |

### `task_blanks`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `task_id` | `uuid` | NO |  |
| 3 | `blank_index` | `integer` | NO |  |
| 4 | `answer` | `text` | NO |  |
| 5 | `accepted_answers` | `text[]` | YES | `'{}'::text[]` |
| 6 | `distractors` | `text[]` | YES | `'{}'::text[]` |
| 7 | `hint` | `text` | YES |  |
| 8 | `explanation` | `text` | YES |  |
| 9 | `difficulty` | `text` | YES |  |
| 10 | `error_type` | `text` | YES |  |
| 11 | `metadata` | `jsonb` | YES | `'{}'::jsonb` |

### `wiki_sources`

| # | Column | Type | Nullable | Default |
| --- | --- | --- | --- | --- |
| 1 | `id` | `uuid` | NO | `gen_random_uuid()` |
| 2 | `event_id` | `uuid` | NO |  |
| 3 | `language` | `text` | NO |  |
| 4 | `title` | `text` | NO |  |
| 5 | `page_url` | `text` | YES |  |
| 6 | `summary` | `text` | YES |  |
| 7 | `sections` | `jsonb` | YES | `'[]'::jsonb` |
| 8 | `provider` | `text` | NO | `'wikipedia'::text` |
| 9 | `fetch_mode` | `text` | NO | `'summary'::text` |
| 10 | `fetch_status` | `text` | NO | `'success'::text` |
| 11 | `raw_payload` | `jsonb` | YES |  |
| 12 | `retrieved_at` | `timestamp with time zone` | YES | `now()` |

## Primary Keys, Unique Constraints, And Foreign Keys

### Primary Keys

All public tables use `id uuid` as primary key:

`conversations`, `event_tasks`, `events`, `experiment_conditions`, `experiment_sessions`, `session_posttests`, `knowledge_chunks`, `messages`, `participants`, `personas`, `research_logs`, `task_answers`, `task_attempts`, `task_blanks`, `wiki_sources`.

### Unique Constraints / Unique Indexes

| Table | Unique key |
| --- | --- |
| `events` | `canonical_name` via `events_canonical_name_unique` |
| `experiment_conditions` | `condition_key` |
| `messages` | `(conversation_id, sequence_index)` |
| `participants` | `code` |
| `participants` | `auth_user_id` |
| `session_posttests` | `session_id` |
| `task_answers` | `(attempt_id, blank_id)` |
| `task_blanks` | `(task_id, blank_index)` |
| `wiki_sources` | `(event_id, provider, language, fetch_mode)` |

### Runtime Check Constraints

| Table | Constraint |
| --- | --- |
| `task_attempts` | `status IN ('in_progress', 'processing', 'submitted', 'failed')` |
| `experiment_conditions` | fixed 2×2 mapping between `condition_key`, EBL, Role-play, agent mode and response policy |
| `session_posttests` | `instrument_version = 'posttest_placeholder_v1'`；`is_placeholder = true` |
| `session_posttests` | `stage IN ('engagement', 'hat', 'completed')`；`revision >= 0` |
| `session_posttests` | `engagement_answers` 與 `hat_answers` 的 `jsonb_typeof(...) = 'object'` |
| `session_posttests` | `(stage = 'completed') = (submitted_at IS NOT NULL)` |

`protect_submitted_posttest` 為 `session_posttests` 的 `BEFORE UPDATE` trigger，呼叫同名函式；當舊紀錄 `stage='completed'` 時拒絕所有更新，即使寫入者持有 service role。它不是刪除保護 trigger；目前後測 API 沒有刪除操作。

### Foreign Keys

| Table | Column | References | Delete behavior |
| --- | --- | --- | --- |
| `conversations` | `event_id` | `events(id)` | `ON DELETE RESTRICT` |
| `conversations` | `session_id` | `experiment_sessions(id)` | `ON DELETE RESTRICT` |
| `conversations` | `task_attempt_id` | `task_attempts(id)` | `ON DELETE RESTRICT` |
| `event_tasks` | `event_id` | `events(id)` | `ON DELETE RESTRICT` |
| `experiment_sessions` | `condition_id` | `experiment_conditions(id)` | `ON DELETE RESTRICT` |
| `experiment_sessions` | `event_id` | `events(id)` | `ON DELETE RESTRICT` |
| `experiment_sessions` | `participant_id` | `participants(id)` | `ON DELETE RESTRICT` |
| `knowledge_chunks` | `event_id` | `events(id)` | `ON DELETE CASCADE` |
| `knowledge_chunks` | `wiki_source_id` | `wiki_sources(id)` | `ON DELETE SET NULL` |
| `messages` | `conversation_id` | `conversations(id)` | `ON DELETE RESTRICT` |
| `messages` | `persona_id` | `personas(id)` | `ON DELETE SET NULL` |
| `participants` | `auth_user_id` | `auth.users(id)` | `ON DELETE RESTRICT` (`NOT VALID` for legacy rows) |
| `personas` | `event_id` | `events(id)` | `ON DELETE RESTRICT` |
| `research_logs` | `attempt_id` | `task_attempts(id)` | `ON DELETE RESTRICT` |
| `research_logs` | `conversation_id` | `conversations(id)` | `ON DELETE RESTRICT` |
| `research_logs` | `event_id` | `events(id)` | `ON DELETE RESTRICT` |
| `research_logs` | `message_id` | `messages(id)` | `ON DELETE RESTRICT` |
| `research_logs` | `session_id` | `experiment_sessions(id)` | `ON DELETE RESTRICT` (`NOT VALID` for legacy rows) |
| `research_logs` | `task_id` | `event_tasks(id)` | `ON DELETE RESTRICT` |
| `session_posttests` | `session_id` | `experiment_sessions(id)` | `ON DELETE RESTRICT` |
| `task_answers` | `attempt_id` | `task_attempts(id)` | `ON DELETE RESTRICT` |
| `task_answers` | `blank_id` | `task_blanks(id)` | `ON DELETE RESTRICT` |
| `task_attempts` | `event_id` | `events(id)` | `ON DELETE RESTRICT` |
| `task_attempts` | `session_id` | `experiment_sessions(id)` | `ON DELETE RESTRICT` |
| `task_attempts` | `task_id` | `event_tasks(id)` | `ON DELETE RESTRICT` |
| `task_blanks` | `task_id` | `event_tasks(id)` | `ON DELETE RESTRICT` |
| `wiki_sources` | `event_id` | `events(id)` | `ON DELETE RESTRICT` |

## Indexes

| Table | Index |
| --- | --- |
| `conversations` | `idx_conversations_event(event_id)` |
| `conversations` | `idx_conversations_session(session_id)` |
| `conversations` | `uq_conversations_session(session_id)` unique |
| `conversations` | `idx_conversations_task_attempt(task_attempt_id)` |
| `conversations` | `idx_conversations_user(user_id)` |
| `event_tasks` | `idx_event_tasks_event(event_id)` |
| `events` | `events_canonical_name_unique(canonical_name)` |
| `events` | `idx_events_canonical_name(canonical_name)` |
| `events` | `idx_events_created_by(created_by)` |
| `events` | `idx_events_archived_at(archived_at)` |
| `experiment_conditions` | `idx_experiment_conditions_active(active)` |
| `experiment_conditions` | `idx_experiment_conditions_key(condition_key)` |
| `experiment_sessions` | `idx_experiment_sessions_condition(condition_id)` |
| `experiment_sessions` | `idx_experiment_sessions_event(event_id)` |
| `experiment_sessions` | `idx_experiment_sessions_status(status)` |
| `experiment_sessions` | `idx_experiment_sessions_user(user_id)` |
| `experiment_sessions` | `idx_experiment_sessions_timer_ends_at(timer_ends_at)` partial index for active timed sessions |
| `experiment_sessions` | `idx_experiment_sessions_participant(participant_id)` |
| `knowledge_chunks` | `idx_knowledge_chunks_event(event_id)` |
| `knowledge_chunks` | `idx_knowledge_chunks_language(language)` |
| `knowledge_chunks` | `idx_knowledge_chunks_source(source)` |
| `messages` | `idx_messages_conversation(conversation_id)` |
| `messages` | `idx_messages_conversation_created(conversation_id, created_at)` |
| `messages` | `idx_messages_persona(persona_id)` |
| `messages` | `messages_conversation_id_sequence_index_key(conversation_id, sequence_index)` |
| `messages` | `messages_conversation_client_request_unique(conversation_id, client_request_id)` partial unique index |
| `messages` | `messages_one_active_operation_unique(conversation_id)` partial unique index |
| `participants` | `idx_participants_code(code)` |
| `participants` | `idx_participants_auth_user_id(auth_user_id)` |
| `participants` | `idx_participants_cohort(cohort)` |
| `participants` | `idx_participants_condition_list(condition_list)` |
| `participants` | `idx_participants_status(status)` |
| `personas` | `idx_personas_active(active)` |
| `personas` | `idx_personas_event(event_id)` |
| `personas` | `personas_one_active_per_event_idx(event_id)` partial unique index for non-archived active persona |
| `research_logs` | `idx_research_logs_action(action_type)` |
| `research_logs` | `idx_research_logs_conversation(conversation_id)` |
| `research_logs` | `idx_research_logs_event(event_id)` |
| `research_logs` | `idx_research_logs_message(message_id)` |
| `research_logs` | `idx_research_logs_session(session_id, created_at)` |
| `research_logs` | `idx_research_logs_user(user_id)` |
| `session_posttests` | `session_posttests_pkey(id)` primary key |
| `session_posttests` | `session_posttests_session_id_key(session_id)` unique |
| `task_answers` | `idx_task_answers_attempt(attempt_id)` |
| `task_answers` | `task_answers_attempt_id_blank_id_key(attempt_id, blank_id)` |
| `task_attempts` | `idx_task_attempts_event(event_id)` |
| `task_attempts` | `idx_task_attempts_session(session_id)` |
| `task_attempts` | `uq_task_attempts_session(session_id)` unique |
| `task_attempts` | `idx_task_attempts_task(task_id)` |
| `task_attempts` | `idx_task_attempts_user(user_id)` |
| `task_blanks` | `idx_task_blanks_task(task_id)` |
| `task_blanks` | `task_blanks_task_id_blank_index_key(task_id, blank_index)` |
| `wiki_sources` | `idx_wiki_sources_event(event_id)` |
| `wiki_sources` | `idx_wiki_sources_fetch_mode(fetch_mode)` |
| `wiki_sources` | `idx_wiki_sources_language(language)` |
| `wiki_sources` | `idx_wiki_sources_provider(provider)` |
| `wiki_sources` | `wiki_sources_event_id_provider_language_fetch_mode_key(event_id, provider, language, fetch_mode)` |

## RLS Status

既有 14 張表沿用原匯出的 `relrowsecurity=false`、`relforcerowsecurity=false` 記錄；本次沒有重新逐表查詢。

新表 `session_posttests` 由 migration 啟用 RLS，未啟用 FORCE RLS，也未建立供 `anon`／`authenticated` 使用的 policies；這兩個角色的表權限另被全部撤銷。Migration 明確授予 service role `SELECT`、`INSERT`、`UPDATE`，不宣稱撤銷該角色可能已有的其他 default privileges。

後測請求經 FastAPI 的 active participant／Session owner 驗證，或沿用管理員驗證；DB 由 service role 存取。新增 RLS 並不取代後端的歸屬、階段與版本驗證。
