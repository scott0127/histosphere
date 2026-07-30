-- 以 learner message 作為持久化聊天 operation，支援冪等、防並行與斷線恢復。
ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS client_request_id TEXT;

ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS operation_status TEXT;

DO $$
BEGIN
  ALTER TABLE messages
    ADD CONSTRAINT messages_operation_status_check
    CHECK (
      operation_status IS NULL
      OR operation_status IN ('pending', 'processing', 'completed', 'failed')
    );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END
$$;

-- 舊資料只回填已確定的終態；舊 pending 資料不應阻擋新的正式回合。
UPDATE messages
SET operation_status = metadata->>'response_status'
WHERE speaker_type = 'learner'
  AND operation_status IS NULL
  AND metadata->>'response_status' IN ('completed', 'failed');

CREATE UNIQUE INDEX IF NOT EXISTS messages_conversation_client_request_unique
  ON messages (conversation_id, client_request_id)
  WHERE speaker_type = 'learner' AND client_request_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS messages_one_active_operation_unique
  ON messages (conversation_id)
  WHERE speaker_type = 'learner'
    AND operation_status IN ('pending', 'processing');
