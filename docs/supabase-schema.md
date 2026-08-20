# Supabase Public Schema Export

最後更新：2026-08-09

來源：`supabase/migrations/`（schema 單一來源）與 local Supabase Postgres `public` schema。

本文件只記錄 Histosphere app 使用的 `public` schema，不包含 Supabase 內建的 `auth`、`storage`、`realtime`、`extensions` 等 schema。

## Summary

目前 `public` schema 有 14 個 base tables：

| Table | Purpose |
| --- | --- |
| `events` | 歷史事件 workspace。 |
| `experiment_conditions` | 2x2 實驗條件設定。 |
| `experiment_sessions` | 一次受測者/使用者從事件、task 到 chat 的流程。 |
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
- `participants.auth_user_id` 對應 Supabase Auth 使用者。正式實驗 runtime 的 `experiment_sessions.user_id`、`task_attempts.user_id`、`conversations.user_id`、`research_logs.user_id` 仍保存 Auth user id，不保存 `participants.id`。
- `participants.condition_list` 以 learner-visible condition code 保存分派條件及 Admin 指定執行順序，例如 `{03,01}` 代表先做 03、再做 01。目前不另建 condition assignment table。
- 所有 listed public tables 目前 RLS 都是 disabled；後端正式 runtime 使用 Supabase service role 透過 `SupabaseRepository` 讀寫。
- `events.archived_at` 是可逆封存旗標。一般 event management 不刪除 event 或其關聯研究資料。
- `experiment_sessions` timer 欄位在 Task 階段為 `NULL`；Chat 建立後由後端自動開始固定五分鐘倒數，Admin 可重置。
- `experiment_sessions.is_admin_test` 明確區分 Admin 驗證與正式受測 Session；Admin test 不進入 learner 進度或正式研究匯出。
- `events.materials_locked_at` 為最低限度素材鎖定；只有鎖定事件可供 learner 開始，鎖定期間禁止編輯 Event、Task 與 Persona。
- `task_attempts.status` 支援 `in_progress`、`processing`、`submitted`、`failed`，供非同步 task submit 與 polling 使用。
- Runtime safety、chat operation、persona 生命週期、研究完整性與 Admin test 分類分別由 2026-07-11 至 2026-08-09 的 migrations 增量建立；這些 migrations 不刪除既有研究資料。

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
| 5 | `display_text` | `text` | NO |  |
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
| 7 | `response_policy` | `text` | NO | `'direct'::text` |
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

`conversations`, `event_tasks`, `events`, `experiment_conditions`, `experiment_sessions`, `knowledge_chunks`, `messages`, `participants`, `personas`, `research_logs`, `task_answers`, `task_attempts`, `task_blanks`, `wiki_sources`.

### Unique Constraints / Unique Indexes

| Table | Unique key |
| --- | --- |
| `events` | `canonical_name` via `events_canonical_name_unique` |
| `experiment_conditions` | `condition_key` |
| `messages` | `(conversation_id, sequence_index)` |
| `participants` | `code` |
| `participants` | `auth_user_id` |
| `task_answers` | `(attempt_id, blank_id)` |
| `task_blanks` | `(task_id, blank_index)` |
| `wiki_sources` | `(event_id, provider, language, fetch_mode)` |

### Runtime Check Constraints

| Table | Constraint |
| --- | --- |
| `task_attempts` | `status IN ('in_progress', 'processing', 'submitted', 'failed')` |

### Foreign Keys

| Table | Column | References | Delete behavior |
| --- | --- | --- | --- |
| `conversations` | `event_id` | `events(id)` | `ON DELETE RESTRICT` |
| `conversations` | `session_id` | `experiment_sessions(id)` | `ON DELETE RESTRICT` |
| `conversations` | `task_attempt_id` | `task_attempts(id)` | `ON DELETE RESTRICT` |
| `event_tasks` | `event_id` | `events(id)` | `ON DELETE RESTRICT` |
| `experiment_sessions` | `condition_id` | `experiment_conditions(id)` | `ON DELETE RESTRICT` |
| `experiment_sessions` | `event_id` | `events(id)` | `ON DELETE RESTRICT` |
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
| `task_answers` | `idx_task_answers_attempt(attempt_id)` |
| `task_answers` | `task_answers_attempt_id_blank_id_key(attempt_id, blank_id)` |
| `task_attempts` | `idx_task_attempts_event(event_id)` |
| `task_attempts` | `idx_task_attempts_session(session_id)` |
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

All listed `public` tables currently have `relrowsecurity=false` and `relforcerowsecurity=false`.

Formal runtime security is therefore enforced in the FastAPI backend through service-role access and admin key checks, not through Postgres RLS policies.
