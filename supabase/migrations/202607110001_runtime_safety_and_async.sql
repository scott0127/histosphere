-- Runtime safety fields for event archiving, asynchronous task submission,
-- and opt-in experiment session timers. This migration does not delete data.

ALTER TABLE events
  ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_events_archived_at ON events(archived_at);

COMMENT ON COLUMN events.archived_at IS
  'NULL for active materials; set by an admin to hide an event without deleting any related research data.';

ALTER TABLE experiment_sessions
  ADD COLUMN IF NOT EXISTS timer_started_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS timer_ends_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS completion_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_experiment_sessions_timer_ends_at
  ON experiment_sessions(timer_ends_at)
  WHERE timer_ends_at IS NOT NULL AND status NOT IN ('completed', 'archived');

COMMENT ON COLUMN experiment_sessions.timer_started_at IS
  'Opt-in timer start. NULL means the timer feature is disabled for this session.';
COMMENT ON COLUMN experiment_sessions.timer_ends_at IS
  'When set, the backend worker completes the session after this timestamp.';
COMMENT ON COLUMN experiment_sessions.completed_at IS
  'Timestamp when the experiment session reached completed status.';
COMMENT ON COLUMN experiment_sessions.completion_reason IS
  'Completion source such as timer_elapsed, learner, or admin.';

ALTER TABLE task_attempts
  DROP CONSTRAINT IF EXISTS task_attempts_status_check;

ALTER TABLE task_attempts
  ADD CONSTRAINT task_attempts_status_check
  CHECK (status IN ('in_progress', 'processing', 'submitted', 'failed'));

COMMENT ON COLUMN task_attempts.status IS
  'in_progress=draft, processing=queued LLM work, submitted=conversation ready, failed=retryable processing failure.';
