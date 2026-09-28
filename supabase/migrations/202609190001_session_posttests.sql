-- Fixed placeholder posttest. Chat completion remains on experiment_sessions;
-- posttest completion is independent and cannot be mistaken for a validated HAT.
CREATE TABLE public.session_posttests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL UNIQUE REFERENCES public.experiment_sessions(id) ON DELETE RESTRICT,
  instrument_version text NOT NULL DEFAULT 'posttest_placeholder_v1'
    CHECK (instrument_version = 'posttest_placeholder_v1'),
  is_placeholder boolean NOT NULL DEFAULT true CHECK (is_placeholder),
  stage text NOT NULL DEFAULT 'engagement' CHECK (stage IN ('engagement', 'hat', 'completed')),
  engagement_answers jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(engagement_answers) = 'object'),
  hat_answers jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(hat_answers) = 'object'),
  revision integer NOT NULL DEFAULT 0 CHECK (revision >= 0),
  started_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  submitted_at timestamptz,
  CHECK ((stage = 'completed') = (submitted_at IS NOT NULL))
);

-- The existing authenticated backend checks ownership using the session. Learner
-- browsers must not bypass those checks through Supabase's public REST endpoint.
ALTER TABLE public.session_posttests ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.session_posttests FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.session_posttests TO service_role;

CREATE FUNCTION public.protect_submitted_posttest() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
BEGIN
  IF OLD.stage = 'completed' THEN
    RAISE EXCEPTION 'Submitted posttests are immutable';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER protect_submitted_posttest
BEFORE UPDATE ON public.session_posttests
FOR EACH ROW EXECUTE FUNCTION public.protect_submitted_posttest();

COMMENT ON TABLE public.session_posttests IS 'Placeholder posttest flow only; is_placeholder=true means these answers are not validated HAT or engagement measurement data.';
