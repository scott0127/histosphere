-- =============================================================================
-- Histosphere EBL Role-Play Schema Draft
-- =============================================================================
-- Purpose:
--   Supports Error-Based Learning (EBL) through an editable cloze task before
--   AI historical persona role-play.
--
-- Status:
--   Draft migration for review. Do not apply to production before confirming
--   migration strategy from the old prototype schema.
--
-- Design rules:
--   - Unknown historical metadata should be NULL, not fabricated.
--   - Frontend may render NULL values as "不詳" or "待補".
--   - RAG is schema-ready but not required in the first implementation.
--   - Persona card and video fields are intentionally excluded.
--   - avatar_url is kept for future optional implementation.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- EVENTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name TEXT NOT NULL,
  description TEXT,
  century INT,
  start_year INT,
  end_year INT,
  context TEXT,
  source_summary JSONB DEFAULT '{}'::jsonb,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_canonical_name ON events(canonical_name);
CREATE INDEX IF NOT EXISTS idx_events_created_by ON events(created_by);

DROP TRIGGER IF EXISTS update_events_updated_at ON events;
CREATE TRIGGER update_events_updated_at
  BEFORE UPDATE ON events
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE events IS 'Historical event workspace for EBL role-play.';
COMMENT ON COLUMN events.canonical_name IS 'Standardized event name used by the experiment.';
COMMENT ON COLUMN events.century IS 'Nullable; unknown values must remain NULL rather than fabricated.';
COMMENT ON COLUMN events.context IS 'Nullable when source evidence is insufficient or pending review.';

-- =============================================================================
-- EXPERIMENT CONDITIONS
-- =============================================================================
CREATE TABLE IF NOT EXISTS experiment_conditions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  condition_key TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  ebl_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  roleplay_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  agent_mode TEXT NOT NULL DEFAULT 'generic'
    CHECK (agent_mode IN ('generic', 'persona')),
  response_policy TEXT NOT NULL DEFAULT 'direct'
    CHECK (response_policy IN ('direct', 'scaffold')),
  description TEXT,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_experiment_conditions_active ON experiment_conditions(active);
CREATE INDEX IF NOT EXISTS idx_experiment_conditions_key ON experiment_conditions(condition_key);

DROP TRIGGER IF EXISTS update_experiment_conditions_updated_at ON experiment_conditions;
CREATE TRIGGER update_experiment_conditions_updated_at
  BEFORE UPDATE ON experiment_conditions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE experiment_conditions IS '2x2 實驗條件設定：EBL 有無與 AI historical persona role-play 有無。';
COMMENT ON COLUMN experiment_conditions.condition_key IS '穩定條件代碼，例如 no_ebl_no_roleplay、ebl_roleplay。';
COMMENT ON COLUMN experiment_conditions.label IS '前端顯示名稱。';
COMMENT ON COLUMN experiment_conditions.ebl_enabled IS '是否啟用 Error-Based Learning 鷹架引導。';
COMMENT ON COLUMN experiment_conditions.roleplay_enabled IS '是否使用歷史人物 persona role-play；false 時使用一般 chatbot/tutor。';
COMMENT ON COLUMN experiment_conditions.agent_mode IS 'generic 表示一般 chatbot；persona 表示歷史人物對話。';
COMMENT ON COLUMN experiment_conditions.response_policy IS 'direct 可直接回答；scaffold 會先引導思考、論證與史料解釋。';
COMMENT ON COLUMN experiment_conditions.description IS '教師或研究者可讀的條件說明。';
COMMENT ON COLUMN experiment_conditions.active IS '是否可在前端被選擇。';

INSERT INTO experiment_conditions (
  condition_key,
  label,
  ebl_enabled,
  roleplay_enabled,
  agent_mode,
  response_policy,
  description
) VALUES
  (
    'no_ebl_no_roleplay',
    'Without EBL + Without AI Role-play',
    FALSE,
    FALSE,
    'generic',
    'direct',
    '一般 ChatGPT 式回答；可直接給正確答案。'
  ),
  (
    'ebl_no_roleplay',
    'With EBL + Without AI Role-play',
    TRUE,
    FALSE,
    'generic',
    'scaffold',
    '一般 tutor chatbot；引導 historical thinking、evidence-based argumentation、source interpretation，不先直接給答案。'
  ),
  (
    'no_ebl_roleplay',
    'Without EBL + With AI Role-play',
    FALSE,
    TRUE,
    'persona',
    'direct',
    'AI historical persona role-play；沉浸式回答，可直接給答案。'
  ),
  (
    'ebl_roleplay',
    'With EBL + With AI Role-play',
    TRUE,
    TRUE,
    'persona',
    'scaffold',
    'AI historical persona 會基於 learner misconceptions 展開對話，引導 historical thinking，不先直接給答案。'
  )
ON CONFLICT (condition_key) DO UPDATE SET
  label = EXCLUDED.label,
  ebl_enabled = EXCLUDED.ebl_enabled,
  roleplay_enabled = EXCLUDED.roleplay_enabled,
  agent_mode = EXCLUDED.agent_mode,
  response_policy = EXCLUDED.response_policy,
  description = EXCLUDED.description;

-- =============================================================================
-- EXPERIMENT SESSIONS
-- =============================================================================
CREATE TABLE IF NOT EXISTS experiment_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  condition_id UUID REFERENCES experiment_conditions(id) ON DELETE SET NULL,
  condition_key_snapshot TEXT NOT NULL,
  user_id UUID,
  event_id UUID REFERENCES events(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'initialized'
    CHECK (status IN ('initialized', 'task_submitted', 'conversation_started', 'completed', 'archived')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_experiment_sessions_condition ON experiment_sessions(condition_id);
CREATE INDEX IF NOT EXISTS idx_experiment_sessions_event ON experiment_sessions(event_id);
CREATE INDEX IF NOT EXISTS idx_experiment_sessions_user ON experiment_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_experiment_sessions_status ON experiment_sessions(status);

DROP TRIGGER IF EXISTS update_experiment_sessions_updated_at ON experiment_sessions;
CREATE TRIGGER update_experiment_sessions_updated_at
  BEFORE UPDATE ON experiment_sessions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE experiment_sessions IS '一次受測者/使用者從事件初始化、task 到對話的實驗流程。';
COMMENT ON COLUMN experiment_sessions.condition_id IS '本次 session 使用的 2x2 實驗條件。';
COMMENT ON COLUMN experiment_sessions.condition_key_snapshot IS '建立 session 當下的條件代碼快照，方便之後條件設定被改動時仍可追溯。';
COMMENT ON COLUMN experiment_sessions.user_id IS '預留的受測者 UUID；第一階段不綁 Supabase Auth。';
COMMENT ON COLUMN experiment_sessions.event_id IS '本次 session 使用的歷史事件。';
COMMENT ON COLUMN experiment_sessions.status IS '流程狀態，用於研究流程追蹤與後台檢視。';

-- =============================================================================
-- WIKI SOURCES
-- =============================================================================
CREATE TABLE IF NOT EXISTS wiki_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID REFERENCES events(id) ON DELETE CASCADE,
  language TEXT NOT NULL CHECK (language IN ('zh', 'en')),
  title TEXT NOT NULL,
  page_url TEXT,
  summary TEXT,
  sections JSONB DEFAULT '[]'::jsonb,
  provider TEXT NOT NULL DEFAULT 'wikipedia',
  fetch_mode TEXT NOT NULL DEFAULT 'summary'
    CHECK (fetch_mode IN ('summary', 'full')),
  fetch_status TEXT NOT NULL DEFAULT 'success'
    CHECK (fetch_status IN ('success', 'partial', 'failed', 'fallback')),
  raw_payload JSONB,
  retrieved_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(event_id, provider, language, fetch_mode)
);

CREATE INDEX IF NOT EXISTS idx_wiki_sources_event ON wiki_sources(event_id);
CREATE INDEX IF NOT EXISTS idx_wiki_sources_language ON wiki_sources(language);
CREATE INDEX IF NOT EXISTS idx_wiki_sources_provider ON wiki_sources(provider);
CREATE INDEX IF NOT EXISTS idx_wiki_sources_fetch_mode ON wiki_sources(fetch_mode);

-- =============================================================================
-- KNOWLEDGE CHUNKS
-- =============================================================================
-- Postponed RAG table. First rebuild stage does not write chunks, generate
-- embeddings, or perform vector retrieval.
CREATE TABLE IF NOT EXISTS knowledge_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID REFERENCES events(id) ON DELETE CASCADE,
  wiki_source_id UUID REFERENCES wiki_sources(id) ON DELETE SET NULL,
  source TEXT NOT NULL,
  source_url TEXT,
  section_title TEXT,
  content TEXT NOT NULL,
  language TEXT,
  char_count INT,
  chunk_index INT,
  embedding VECTOR(768),
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_event ON knowledge_chunks(event_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source ON knowledge_chunks(source);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_language ON knowledge_chunks(language);

COMMENT ON TABLE knowledge_chunks IS '暫緩實作的未來 RAG 知識片段表；第一階段不寫入 chunk、不產生 embedding、不做向量檢索。';
COMMENT ON COLUMN knowledge_chunks.id IS '知識片段唯一識別碼。';
COMMENT ON COLUMN knowledge_chunks.event_id IS '知識片段所屬的歷史事件。';
COMMENT ON COLUMN knowledge_chunks.wiki_source_id IS '知識片段來源的 Wikipedia 資料列；來源刪除時保留 chunk 但設為 NULL。';
COMMENT ON COLUMN knowledge_chunks.source IS '來源類型或來源名稱，例如 wikipedia。';
COMMENT ON COLUMN knowledge_chunks.source_url IS '原始資料來源網址。';
COMMENT ON COLUMN knowledge_chunks.section_title IS '原始文件章節標題；沒有章節時可為 NULL。';
COMMENT ON COLUMN knowledge_chunks.content IS '可供未來 RAG 檢索的文字片段。';
COMMENT ON COLUMN knowledge_chunks.language IS '文字片段語言，例如 zh 或 en。';
COMMENT ON COLUMN knowledge_chunks.char_count IS '文字片段字元數，供 chunking 品質檢查使用。';
COMMENT ON COLUMN knowledge_chunks.chunk_index IS '同一來源文件中的 chunk 順序。';
COMMENT ON COLUMN knowledge_chunks.embedding IS '暫緩使用；未來向量檢索用 embedding，例如 Gemini text-embedding-004 768 維。';
COMMENT ON COLUMN knowledge_chunks.metadata IS '未來 RAG pipeline 的延伸資訊，例如 chunking 策略、版本或品質標記。';
COMMENT ON COLUMN knowledge_chunks.created_at IS '資料列建立時間。';

-- =============================================================================
-- EVENT TASKS
-- =============================================================================
CREATE TABLE IF NOT EXISTS event_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID REFERENCES events(id) ON DELETE CASCADE,
  title TEXT,
  story_text TEXT NOT NULL,
  display_text TEXT NOT NULL,
  evaluation_payload JSONB DEFAULT '{}'::jsonb,
  revision_state TEXT DEFAULT 'llm_generated'
    CHECK (revision_state IN ('llm_generated', 'teacher_modified', 'manual')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_tasks_event ON event_tasks(event_id);

DROP TRIGGER IF EXISTS update_event_tasks_updated_at ON event_tasks;
CREATE TRIGGER update_event_tasks_updated_at
  BEFORE UPDATE ON event_tasks
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE event_tasks IS '對話前的 cloze-style / short-answer task，用於 productive error 與 learner misconceptions。';
COMMENT ON COLUMN event_tasks.title IS 'Task 顯示標題，教師可在後台修改。';
COMMENT ON COLUMN event_tasks.story_text IS '完整歷史故事文本；可作為教師檢查或未來重建 display_text 的來源。';
COMMENT ON COLUMN event_tasks.display_text IS '學生看到的挖洞/短答文本；第一階段不要求每個空格正規化。';
COMMENT ON COLUMN event_tasks.evaluation_payload IS '第一版 LLM 正誤判斷設定，例如 rubric、expected_points、acceptable_variants；完整 task_blanks 評分暫緩。';
COMMENT ON COLUMN event_tasks.revision_state IS '標記 task 是 LLM 生成、教師修改或手動建立。';

-- =============================================================================
-- TASK BLANKS
-- =============================================================================
-- Reserved for future blank-level scoring. The first rebuild stage unlocks chat
-- after task submission/completion and postpones scoring, synonym matching, and
-- EBL error-type coding until teacher/research design review.
CREATE TABLE IF NOT EXISTS task_blanks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID REFERENCES event_tasks(id) ON DELETE CASCADE,
  blank_index INT NOT NULL,
  answer TEXT NOT NULL,
  accepted_answers TEXT[] DEFAULT '{}',
  distractors TEXT[] DEFAULT '{}',
  hint TEXT,
  explanation TEXT,
  difficulty TEXT CHECK (difficulty IS NULL OR difficulty IN ('easy', 'medium', 'hard')),
  error_type TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  UNIQUE(task_id, blank_index)
);

CREATE INDEX IF NOT EXISTS idx_task_blanks_task ON task_blanks(task_id);

COMMENT ON TABLE task_blanks IS 'Postponed design table for blank-level scoring, accepted answers, and EBL error-type coding.';
COMMENT ON COLUMN task_blanks.accepted_answers IS 'Postponed: decide how synonymous or acceptable answers should be represented.';
COMMENT ON COLUMN task_blanks.error_type IS 'Postponed: decide EBL error categories with teacher/research design.';

-- =============================================================================
-- TASK ATTEMPTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS task_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID REFERENCES event_tasks(id) ON DELETE CASCADE,
  event_id UUID REFERENCES events(id) ON DELETE CASCADE,
  session_id UUID REFERENCES experiment_sessions(id) ON DELETE SET NULL,
  user_id UUID,
  status TEXT DEFAULT 'in_progress'
    CHECK (status IN ('in_progress', 'submitted')),
  response_payload JSONB DEFAULT '{}'::jsonb,
  judgement_payload JSONB DEFAULT '{}'::jsonb,
  submitted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_attempts_task ON task_attempts(task_id);
CREATE INDEX IF NOT EXISTS idx_task_attempts_event ON task_attempts(event_id);
CREATE INDEX IF NOT EXISTS idx_task_attempts_session ON task_attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_task_attempts_user ON task_attempts(user_id);

DROP TRIGGER IF EXISTS update_task_attempts_updated_at ON task_attempts;
CREATE TRIGGER update_task_attempts_updated_at
  BEFORE UPDATE ON task_attempts
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE task_attempts IS 'Learner task submission gate before conversation unlock.';
COMMENT ON COLUMN task_attempts.session_id IS '連到 experiment_sessions，用於串接 2x2 condition、task 與 conversation。';
COMMENT ON COLUMN task_attempts.response_payload IS 'First-stage flexible storage for learner task responses before task_blanks scoring is finalized.';
COMMENT ON COLUMN task_attempts.judgement_payload IS 'LLM 對本次 task 作答的簡單判斷，例如 correct、incorrect、partial 與 misconception_summary。';
COMMENT ON COLUMN task_attempts.submitted_at IS 'Set when the learner submits the task and chat can be unlocked.';

-- =============================================================================
-- TASK ANSWERS
-- =============================================================================
-- Reserved for future normalized per-blank answers. First-stage implementation
-- stores learner responses in task_attempts.response_payload and unlocks chat
-- through task_attempts.submitted_at.
CREATE TABLE IF NOT EXISTS task_answers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  attempt_id UUID REFERENCES task_attempts(id) ON DELETE CASCADE,
  blank_id UUID REFERENCES task_blanks(id) ON DELETE CASCADE,
  user_answer TEXT,
  is_correct BOOLEAN,
  feedback TEXT,
  answered_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(attempt_id, blank_id)
);

CREATE INDEX IF NOT EXISTS idx_task_answers_attempt ON task_answers(attempt_id);

COMMENT ON TABLE task_answers IS 'Postponed design table for normalized per-blank task answers.';
COMMENT ON COLUMN task_answers.is_correct IS 'Postponed until blank-level scoring rules are finalized.';
COMMENT ON COLUMN task_answers.feedback IS 'Postponed until feedback and EBL error coding design is finalized.';

-- =============================================================================
-- PERSONAS
-- =============================================================================
CREATE TABLE IF NOT EXISTS personas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID REFERENCES events(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  english_name TEXT,
  role TEXT,
  biography TEXT,
  expertise_areas TEXT[] DEFAULT '{}',
  sources JSONB DEFAULT '[]'::jsonb,
  prompt_profile JSONB DEFAULT '{}'::jsonb,
  avatar_url TEXT,
  active BOOLEAN DEFAULT TRUE,
  sort_order INT DEFAULT 0,
  revision_state TEXT DEFAULT 'llm_generated'
    CHECK (revision_state IN ('llm_generated', 'teacher_modified', 'manual')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_personas_event ON personas(event_id);
CREATE INDEX IF NOT EXISTS idx_personas_active ON personas(active);

DROP TRIGGER IF EXISTS update_personas_updated_at ON personas;
CREATE TRIGGER update_personas_updated_at
  BEFORE UPDATE ON personas
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE personas IS 'Historical personas generated or edited for an event. Video and persona card fields are deprecated in the EBL rebuild.';
COMMENT ON COLUMN personas.event_id IS 'Parent historical event that this persona belongs to.';
COMMENT ON COLUMN personas.name IS 'Primary display name shown to learners and used by prompt modules.';
COMMENT ON COLUMN personas.english_name IS 'Optional English or source-language name for cross-lingual lookup and display.';
COMMENT ON COLUMN personas.role IS 'Historical role, title, or relationship to the event.';
COMMENT ON COLUMN personas.biography IS 'Teacher-editable short background used as persona context.';
COMMENT ON COLUMN personas.expertise_areas IS 'Topic tags that help prompt routing and persona response focus.';
COMMENT ON COLUMN personas.sources IS 'Traceable references used to generate or verify this persona, such as Wikipedia pages or source notes.';
COMMENT ON COLUMN personas.prompt_profile IS '教師可編輯的 persona/context engineering 設定，例如 stance、speaking_style、knowledge_boundary、teacher_notes、deliberate_error_enabled；不是最終組好的完整 prompt。';
COMMENT ON COLUMN personas.avatar_url IS 'Reserved for future avatar implementation.';
COMMENT ON COLUMN personas.active IS 'Teacher/admin control for whether this persona is available in the chat experience.';
COMMENT ON COLUMN personas.sort_order IS 'Display and default ordering for personas within the same event.';
COMMENT ON COLUMN personas.revision_state IS 'Tracks whether the persona is LLM-generated, teacher-modified, or manually created.';

-- =============================================================================
-- CONVERSATIONS
-- =============================================================================
CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID REFERENCES events(id) ON DELETE CASCADE,
  task_attempt_id UUID REFERENCES task_attempts(id) ON DELETE SET NULL,
  session_id UUID REFERENCES experiment_sessions(id) ON DELETE SET NULL,
  user_id UUID,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  started_at TIMESTAMPTZ DEFAULT NOW(),
  archived_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_event ON conversations(event_id);
CREATE INDEX IF NOT EXISTS idx_conversations_task_attempt ON conversations(task_attempt_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);

DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
CREATE TRIGGER update_conversations_updated_at
  BEFORE UPDATE ON conversations
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE conversations IS '使用者完成 task 後開始的歷史人物聊天室。';
COMMENT ON COLUMN conversations.id IS '聊天室唯一識別碼。';
COMMENT ON COLUMN conversations.event_id IS '聊天室所屬的歷史事件。';
COMMENT ON COLUMN conversations.task_attempt_id IS '觸發這次聊天室的 task 提交紀錄，用於研究流程追蹤。';
COMMENT ON COLUMN conversations.session_id IS '串起同一輪 2x2 condition、task 與 chat 的 experiment session。';
COMMENT ON COLUMN conversations.user_id IS '預留的使用者或受測者 UUID；第一階段不綁定 Supabase Auth。';
COMMENT ON COLUMN conversations.status IS '聊天室狀態；active 表示可對話，archived 表示已封存。';
COMMENT ON COLUMN conversations.started_at IS '使用者開始或進入這次對話的時間。';
COMMENT ON COLUMN conversations.archived_at IS '聊天室被封存的時間；未封存時為 NULL。';
COMMENT ON COLUMN conversations.created_at IS '資料列建立時間。';
COMMENT ON COLUMN conversations.updated_at IS '資料列最後更新時間。';

-- =============================================================================
-- MESSAGES
-- =============================================================================
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  persona_id UUID REFERENCES personas(id) ON DELETE SET NULL,
  speaker_type TEXT NOT NULL CHECK (speaker_type IN ('learner', 'persona', 'assistant')),
  speaker_name TEXT NOT NULL,
  sequence_index INT NOT NULL CHECK (sequence_index >= 0),
  content TEXT NOT NULL,
  annotations JSONB DEFAULT '[]'::jsonb,
  rag_sources JSONB DEFAULT '[]'::jsonb,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(conversation_id, sequence_index)
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_persona ON messages(persona_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created ON messages(conversation_id, created_at);

COMMENT ON TABLE messages IS '聊天室中的 learner、一般 assistant 與歷史 persona 對話訊息。';
COMMENT ON COLUMN messages.id IS '訊息唯一識別碼。';
COMMENT ON COLUMN messages.conversation_id IS '訊息所屬的聊天室。';
COMMENT ON COLUMN messages.persona_id IS '如果發話者是歷史 persona，連到對應 persona；learner 訊息為 NULL。';
COMMENT ON COLUMN messages.speaker_type IS '發話者類型；learner 表示使用者，assistant 表示一般 chatbot/tutor，persona 表示 AI 歷史人物。';
COMMENT ON COLUMN messages.speaker_name IS '發話者當下顯示名稱快照；learner 訊息固定可用 learner。';
COMMENT ON COLUMN messages.sequence_index IS '同一聊天室中的訊息順序，用於穩定回放與研究匯出。';
COMMENT ON COLUMN messages.content IS '訊息文字內容。';
COMMENT ON COLUMN messages.annotations IS '訊息註解、關鍵詞說明或不確定性標記。';
COMMENT ON COLUMN messages.rag_sources IS '未來 RAG 來源追蹤欄位；第一階段可為空陣列。';
COMMENT ON COLUMN messages.metadata IS '技術或研究用延伸資訊，例如模型、persona prompt_profile 快照、prompt hash、延遲或實驗標記。';
COMMENT ON COLUMN messages.created_at IS '訊息建立時間。';

-- =============================================================================
-- RESEARCH LOGS
-- =============================================================================
CREATE TABLE IF NOT EXISTS research_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  session_id UUID,
  event_id UUID REFERENCES events(id) ON DELETE SET NULL,
  task_id UUID REFERENCES event_tasks(id) ON DELETE SET NULL,
  attempt_id UUID REFERENCES task_attempts(id) ON DELETE SET NULL,
  conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
  message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
  action_type TEXT NOT NULL,
  payload JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_logs_user ON research_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_research_logs_session ON research_logs(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_research_logs_event ON research_logs(event_id);
CREATE INDEX IF NOT EXISTS idx_research_logs_conversation ON research_logs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_research_logs_message ON research_logs(message_id);
CREATE INDEX IF NOT EXISTS idx_research_logs_action ON research_logs(action_type);

COMMENT ON TABLE research_logs IS '論文實驗用的行為軌跡表，記錄使用者與系統互動脈絡；不取代 messages 的對話內容。';
COMMENT ON COLUMN research_logs.id IS '研究紀錄唯一識別碼。';
COMMENT ON COLUMN research_logs.user_id IS '預留的使用者或受測者 UUID；第一階段不綁定 Supabase Auth。';
COMMENT ON COLUMN research_logs.session_id IS '一次實驗流程或一次使用 session 的識別碼，可串起同一輪事件、task 與對話行為。';
COMMENT ON COLUMN research_logs.event_id IS '此行為相關的歷史事件。';
COMMENT ON COLUMN research_logs.task_id IS '此行為相關的 task。';
COMMENT ON COLUMN research_logs.attempt_id IS '此行為相關的 task 作答或提交紀錄。';
COMMENT ON COLUMN research_logs.conversation_id IS '此行為相關的聊天室。';
COMMENT ON COLUMN research_logs.message_id IS '此行為相關的對話訊息；例如送出訊息或 persona 回覆。';
COMMENT ON COLUMN research_logs.action_type IS '行為類型，例如 event_initialized、task_answer_changed、task_submitted、message_sent。';
COMMENT ON COLUMN research_logs.payload IS '行為細節 JSON，例如修改前後答案、選擇的人物、前端狀態或實驗標記。';
COMMENT ON COLUMN research_logs.created_at IS '行為發生或被記錄的時間。';
