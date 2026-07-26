-- 已綁定 participant 對同一歷史事件只能有一筆未封存 session。
-- Admin test mode 使用未綁定的測試 UUID，因此不受此限制。
CREATE OR REPLACE FUNCTION enforce_one_participant_event_session()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.user_id IS NULL OR NEW.status = 'archived' THEN
    RETURN NEW;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM participants
    WHERE auth_user_id = NEW.user_id
  ) AND EXISTS (
    SELECT 1
    FROM experiment_sessions
    WHERE user_id = NEW.user_id
      AND event_id = NEW.event_id
      AND status <> 'archived'
      AND id <> NEW.id
  ) THEN
    RAISE EXCEPTION
      USING
        ERRCODE = '23505',
        MESSAGE = 'participant already has a non-archived session for this event';
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS enforce_one_participant_event_session_trigger
  ON experiment_sessions;

CREATE TRIGGER enforce_one_participant_event_session_trigger
  BEFORE INSERT OR UPDATE OF user_id, event_id, status
  ON experiment_sessions
  FOR EACH ROW
  EXECUTE FUNCTION enforce_one_participant_event_session();

COMMENT ON FUNCTION enforce_one_participant_event_session() IS
  'Prevents a bound participant from repeating one event until an admin archives the old session.';
