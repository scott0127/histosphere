-- Freeze formal participant identity and enforce the one-session-one-record
-- cardinalities already assumed by the application. This migration never
-- deletes or merges existing research data.

ALTER TABLE experiment_sessions
  ADD COLUMN IF NOT EXISTS participant_id UUID;

-- Existing formal sessions can be linked without changing their Auth identity.
UPDATE experiment_sessions AS session
SET participant_id = participant.id
FROM participants AS participant
WHERE session.participant_id IS NULL
  AND session.is_admin_test = FALSE
  AND session.user_id = participant.auth_user_id;

ALTER TABLE experiment_sessions
  DROP CONSTRAINT IF EXISTS experiment_sessions_participant_id_fkey,
  ADD CONSTRAINT experiment_sessions_participant_id_fkey
    FOREIGN KEY (participant_id) REFERENCES participants(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_experiment_sessions_participant
  ON experiment_sessions(participant_id);

COMMENT ON COLUMN experiment_sessions.participant_id IS
  'Participant registry identity frozen when a formal session starts. Auth user_id remains the request identity; Admin test sessions keep this NULL.';

-- Refuse the migration instead of silently deleting or choosing among duplicate
-- research rows. Any legacy duplicate must be reviewed explicitly by Admin.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM task_attempts
    GROUP BY session_id
    HAVING COUNT(*) > 1
  ) THEN
    RAISE EXCEPTION 'Cannot enforce one task_attempt per session: duplicate legacy rows require manual review';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM conversations
    GROUP BY session_id
    HAVING COUNT(*) > 1
  ) THEN
    RAISE EXCEPTION 'Cannot enforce one conversation per session: duplicate legacy rows require manual review';
  END IF;
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_task_attempts_session
  ON task_attempts(session_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_conversations_session
  ON conversations(session_id);

-- The condition key is not merely a label: it fixes both experimental factors
-- and the runtime renderer/policy pair.
ALTER TABLE experiment_conditions
  DROP CONSTRAINT IF EXISTS experiment_conditions_fixed_2x2_matrix,
  ADD CONSTRAINT experiment_conditions_fixed_2x2_matrix CHECK (
    (
      condition_key = 'no_ebl_no_roleplay'
      AND ebl_enabled = FALSE
      AND roleplay_enabled = FALSE
      AND agent_mode = 'generic'
      AND response_policy = 'standard'
    ) OR (
      condition_key = 'ebl_no_roleplay'
      AND ebl_enabled = TRUE
      AND roleplay_enabled = FALSE
      AND agent_mode = 'generic'
      AND response_policy = 'scaffold'
    ) OR (
      condition_key = 'no_ebl_roleplay'
      AND ebl_enabled = FALSE
      AND roleplay_enabled = TRUE
      AND agent_mode = 'persona'
      AND response_policy = 'standard'
    ) OR (
      condition_key = 'ebl_roleplay'
      AND ebl_enabled = TRUE
      AND roleplay_enabled = TRUE
      AND agent_mode = 'persona'
      AND response_policy = 'scaffold'
    )
  );

UPDATE experiment_conditions
SET
  description = CASE condition_key
    WHEN 'no_ebl_no_roleplay' THEN '一般 AI 歷史對話；自然回答與追問，不主動執行 EBL。'
    WHEN 'ebl_no_roleplay' THEN '一般 AI 歷史對話；以發現錯誤、分析／反思、自我修正與最後修正回饋的 EBL 流程互動。'
    WHEN 'no_ebl_roleplay' THEN '歷史人物沉浸式對話；自然回答與追問，不主動執行 EBL。'
    WHEN 'ebl_roleplay' THEN '歷史人物以人物身分執行與 02 相同的錯誤發現、反思、自我修正與修正回饋流程。'
  END,
  updated_at = NOW();
