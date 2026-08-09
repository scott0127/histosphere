-- 補強研究資料歸屬關係，並加入最低限度的實驗素材鎖定。
-- 本 migration 不刪除或改寫既有研究紀錄。

ALTER TABLE events
  ADD COLUMN IF NOT EXISTS materials_locked_at TIMESTAMPTZ;

COMMENT ON COLUMN events.materials_locked_at IS
  'Admin 確認事件、Task 與唯一啟用 persona 可供正式實驗使用的時間；NULL 表示仍可編輯。';

-- 這些欄位決定研究紀錄的父層歸屬。現有資料已先經唯讀盤點確認沒有 NULL。
ALTER TABLE experiment_sessions
  ALTER COLUMN condition_id SET NOT NULL,
  ALTER COLUMN event_id SET NOT NULL,
  ALTER COLUMN status SET NOT NULL;

ALTER TABLE wiki_sources
  ALTER COLUMN event_id SET NOT NULL;

ALTER TABLE event_tasks
  ALTER COLUMN event_id SET NOT NULL;

ALTER TABLE task_blanks
  ALTER COLUMN task_id SET NOT NULL;

ALTER TABLE task_attempts
  ALTER COLUMN task_id SET NOT NULL,
  ALTER COLUMN event_id SET NOT NULL,
  ALTER COLUMN session_id SET NOT NULL,
  ALTER COLUMN status SET NOT NULL;

ALTER TABLE task_answers
  ALTER COLUMN attempt_id SET NOT NULL,
  ALTER COLUMN blank_id SET NOT NULL;

ALTER TABLE personas
  ALTER COLUMN event_id SET NOT NULL;

ALTER TABLE conversations
  ALTER COLUMN event_id SET NOT NULL,
  ALTER COLUMN task_attempt_id SET NOT NULL,
  ALTER COLUMN session_id SET NOT NULL;

ALTER TABLE messages
  ALTER COLUMN conversation_id SET NOT NULL;

-- 研究資料一律透過封存保留；直接刪除父資料時由 FK 拒絕，而不是連帶刪除或留下 NULL。
ALTER TABLE experiment_sessions
  DROP CONSTRAINT IF EXISTS experiment_sessions_condition_id_fkey,
  ADD CONSTRAINT experiment_sessions_condition_id_fkey
    FOREIGN KEY (condition_id) REFERENCES experiment_conditions(id) ON DELETE RESTRICT,
  DROP CONSTRAINT IF EXISTS experiment_sessions_event_id_fkey,
  ADD CONSTRAINT experiment_sessions_event_id_fkey
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE RESTRICT;

ALTER TABLE wiki_sources
  DROP CONSTRAINT IF EXISTS wiki_sources_event_id_fkey,
  ADD CONSTRAINT wiki_sources_event_id_fkey
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE RESTRICT;

ALTER TABLE event_tasks
  DROP CONSTRAINT IF EXISTS event_tasks_event_id_fkey,
  ADD CONSTRAINT event_tasks_event_id_fkey
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE RESTRICT;

ALTER TABLE task_blanks
  DROP CONSTRAINT IF EXISTS task_blanks_task_id_fkey,
  ADD CONSTRAINT task_blanks_task_id_fkey
    FOREIGN KEY (task_id) REFERENCES event_tasks(id) ON DELETE RESTRICT;

ALTER TABLE task_attempts
  DROP CONSTRAINT IF EXISTS task_attempts_task_id_fkey,
  ADD CONSTRAINT task_attempts_task_id_fkey
    FOREIGN KEY (task_id) REFERENCES event_tasks(id) ON DELETE RESTRICT,
  DROP CONSTRAINT IF EXISTS task_attempts_event_id_fkey,
  ADD CONSTRAINT task_attempts_event_id_fkey
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE RESTRICT,
  DROP CONSTRAINT IF EXISTS task_attempts_session_id_fkey,
  ADD CONSTRAINT task_attempts_session_id_fkey
    FOREIGN KEY (session_id) REFERENCES experiment_sessions(id) ON DELETE RESTRICT;

ALTER TABLE task_answers
  DROP CONSTRAINT IF EXISTS task_answers_attempt_id_fkey,
  ADD CONSTRAINT task_answers_attempt_id_fkey
    FOREIGN KEY (attempt_id) REFERENCES task_attempts(id) ON DELETE RESTRICT,
  DROP CONSTRAINT IF EXISTS task_answers_blank_id_fkey,
  ADD CONSTRAINT task_answers_blank_id_fkey
    FOREIGN KEY (blank_id) REFERENCES task_blanks(id) ON DELETE RESTRICT;

ALTER TABLE personas
  DROP CONSTRAINT IF EXISTS personas_event_id_fkey,
  ADD CONSTRAINT personas_event_id_fkey
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE RESTRICT;

ALTER TABLE conversations
  DROP CONSTRAINT IF EXISTS conversations_event_id_fkey,
  ADD CONSTRAINT conversations_event_id_fkey
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE RESTRICT,
  DROP CONSTRAINT IF EXISTS conversations_task_attempt_id_fkey,
  ADD CONSTRAINT conversations_task_attempt_id_fkey
    FOREIGN KEY (task_attempt_id) REFERENCES task_attempts(id) ON DELETE RESTRICT,
  DROP CONSTRAINT IF EXISTS conversations_session_id_fkey,
  ADD CONSTRAINT conversations_session_id_fkey
    FOREIGN KEY (session_id) REFERENCES experiment_sessions(id) ON DELETE RESTRICT;

ALTER TABLE messages
  DROP CONSTRAINT IF EXISTS messages_conversation_id_fkey,
  ADD CONSTRAINT messages_conversation_id_fkey
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE RESTRICT;

ALTER TABLE research_logs
  DROP CONSTRAINT IF EXISTS research_logs_event_id_fkey,
  ADD CONSTRAINT research_logs_event_id_fkey
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE RESTRICT,
  DROP CONSTRAINT IF EXISTS research_logs_task_id_fkey,
  ADD CONSTRAINT research_logs_task_id_fkey
    FOREIGN KEY (task_id) REFERENCES event_tasks(id) ON DELETE RESTRICT,
  DROP CONSTRAINT IF EXISTS research_logs_attempt_id_fkey,
  ADD CONSTRAINT research_logs_attempt_id_fkey
    FOREIGN KEY (attempt_id) REFERENCES task_attempts(id) ON DELETE RESTRICT,
  DROP CONSTRAINT IF EXISTS research_logs_conversation_id_fkey,
  ADD CONSTRAINT research_logs_conversation_id_fkey
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE RESTRICT,
  DROP CONSTRAINT IF EXISTS research_logs_message_id_fkey,
  ADD CONSTRAINT research_logs_message_id_fkey
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE RESTRICT;

-- 舊資料有少量已失去 session 的研究 log；NOT VALID 會保留它們，但阻止未來再寫入孤兒 ID。
ALTER TABLE research_logs
  DROP CONSTRAINT IF EXISTS research_logs_session_id_fkey,
  ADD CONSTRAINT research_logs_session_id_fkey
    FOREIGN KEY (session_id) REFERENCES experiment_sessions(id) ON DELETE RESTRICT NOT VALID;

-- Participant 可以尚未綁定 Auth，因此欄位維持 nullable；一旦填入就必須是實際 Auth user。
ALTER TABLE participants
  DROP CONSTRAINT IF EXISTS participants_auth_user_id_fkey,
  ADD CONSTRAINT participants_auth_user_id_fkey
    FOREIGN KEY (auth_user_id) REFERENCES auth.users(id) ON DELETE RESTRICT NOT VALID;
