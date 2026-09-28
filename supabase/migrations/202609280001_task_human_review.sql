-- Persist the initial judgement separately from the researcher's final decision.
ALTER TABLE public.task_attempts
  ADD COLUMN ai_judgement_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN review_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN review_version integer NOT NULL DEFAULT 0 CHECK (review_version >= 0),
  ADD COLUMN pipeline_error jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE public.task_attempts DROP CONSTRAINT IF EXISTS task_attempts_status_check;
ALTER TABLE public.task_attempts ADD CONSTRAINT task_attempts_status_check
  CHECK (status IN ('in_progress', 'processing', 'awaiting_review', 'preparing_chat', 'ready', 'submitted', 'failed'));

-- Private review drafts must never be readable through the public browser client.
ALTER TABLE public.task_attempts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.task_attempts FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.task_attempts TO service_role;

CREATE FUNCTION public.protect_task_review_checkpoints() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
BEGIN
  IF OLD.ai_judgement_payload <> '{}'::jsonb AND
     NEW.ai_judgement_payload IS DISTINCT FROM OLD.ai_judgement_payload THEN
    RAISE EXCEPTION 'Saved initial task judgements are immutable';
  END IF;
  IF OLD.review_payload ? 'approved_at' AND
     (NEW.review_payload IS DISTINCT FROM OLD.review_payload OR
      NEW.judgement_payload IS DISTINCT FROM OLD.judgement_payload) THEN
    RAISE EXCEPTION 'Approved task reviews are immutable';
  END IF;
  IF OLD.submitted_at IS NOT NULL AND
     NEW.response_payload IS DISTINCT FROM OLD.response_payload THEN
    RAISE EXCEPTION 'Submitted task answers are immutable';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER protect_task_review_checkpoints
BEFORE UPDATE ON public.task_attempts
FOR EACH ROW EXECUTE FUNCTION public.protect_task_review_checkpoints();

-- One transaction prevents a duplicate enter request from restarting the timer.
CREATE FUNCTION public.start_task_interaction(p_attempt_id uuid, p_duration_minutes integer)
RETURNS SETOF public.task_attempts
LANGUAGE plpgsql SET search_path = public AS $$
DECLARE
  attempt public.task_attempts;
  active_session public.experiment_sessions;
  entered_at timestamptz := now();
BEGIN
  SELECT * INTO attempt FROM public.task_attempts WHERE id = p_attempt_id FOR UPDATE;
  IF NOT FOUND OR attempt.status NOT IN ('ready', 'submitted') THEN RETURN; END IF;
  IF attempt.status = 'ready' AND NOT (attempt.review_payload ? 'approved_at') THEN RETURN; END IF;
  SELECT * INTO active_session FROM public.experiment_sessions WHERE id = attempt.session_id FOR UPDATE;
  IF NOT FOUND OR active_session.status IN ('completed', 'archived') THEN RETURN; END IF;
  IF NOT EXISTS (
    SELECT 1 FROM public.conversations c JOIN public.messages m ON m.conversation_id = c.id
    WHERE c.session_id = attempt.session_id AND c.task_attempt_id = attempt.id
  ) THEN RETURN; END IF;
  UPDATE public.experiment_sessions
    SET status = 'conversation_started',
        timer_started_at = COALESCE(timer_started_at, entered_at),
        timer_ends_at = COALESCE(timer_ends_at, entered_at + make_interval(mins => p_duration_minutes)),
        updated_at = entered_at
    WHERE id = attempt.session_id;
  RETURN QUERY UPDATE public.task_attempts SET status = 'submitted', updated_at = entered_at
    WHERE id = p_attempt_id RETURNING *;
END;
$$;

REVOKE ALL ON FUNCTION public.start_task_interaction(uuid, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.start_task_interaction(uuid, integer) TO service_role;
