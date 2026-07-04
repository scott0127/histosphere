-- Participant registry for learner-code based experiment management.
-- 受測者用預建 Supabase Auth 帳號登入；研究端以 code 顯示與管理，condition_list 先用簡單 text[] 保存分派條件。

CREATE TABLE IF NOT EXISTS participants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL UNIQUE,
  display_name TEXT,
  cohort TEXT,
  condition_list TEXT[] NOT NULL DEFAULT '{}'
    CHECK (condition_list <@ ARRAY['01', '02', '03', '04']::text[]),
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'completed', 'excluded', 'archived')),
  notes TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_participants_code ON participants(code);
CREATE INDEX IF NOT EXISTS idx_participants_status ON participants(status);
CREATE INDEX IF NOT EXISTS idx_participants_cohort ON participants(cohort);
CREATE INDEX IF NOT EXISTS idx_participants_condition_list ON participants USING GIN(condition_list);

DROP TRIGGER IF EXISTS update_participants_updated_at ON participants;
CREATE TRIGGER update_participants_updated_at
  BEFORE UPDATE ON participants
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE participants IS 'Participant registry for learner-code based experiment management. Learners log in with pre-created Supabase Auth accounts; admin-facing identity uses participant code.';
COMMENT ON COLUMN participants.id IS 'Participant registry UUID. Experiment runtime records use Supabase Auth user_id fields, not this id.';
COMMENT ON COLUMN participants.code IS 'Human-readable participant code, such as P001.';
COMMENT ON COLUMN participants.display_name IS 'Optional admin-facing display name.';
COMMENT ON COLUMN participants.cohort IS 'Optional experiment cohort or batch label.';
COMMENT ON COLUMN participants.condition_list IS 'Assigned learner-visible condition codes, e.g. {01,03}.';
COMMENT ON COLUMN participants.status IS 'Research/admin status for this participant.';
COMMENT ON COLUMN participants.notes IS 'Admin notes that are not shown to learners.';
COMMENT ON COLUMN participants.metadata IS 'Flexible admin metadata for future participant management.';
