-- Link pre-created Supabase Auth users to research participants.

ALTER TABLE participants
ADD COLUMN IF NOT EXISTS auth_user_id UUID UNIQUE;

CREATE INDEX IF NOT EXISTS idx_participants_auth_user_id ON participants(auth_user_id);

COMMENT ON COLUMN participants.auth_user_id IS
'Supabase Auth user id mapped to this research participant. Learner flow resolves participant by the logged-in auth user; experiment record user_id fields keep using this auth user id.';
