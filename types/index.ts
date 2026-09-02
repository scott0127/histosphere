export type ConditionKey =
  | 'no_ebl_no_roleplay'
  | 'ebl_no_roleplay'
  | 'no_ebl_roleplay'
  | 'ebl_roleplay';

export type SpeakerType = 'learner' | 'assistant' | 'persona';

export type TaskQuestionType = 'short_answer' | 'cloze' | 'multiple_choice' | 'true_false';

export const ERROR_ELICITATION_CONTRACT_VERSION = 'error_elicitation_v1' as const;
export type ErrorElicitationQuestionType = Exclude<TaskQuestionType, 'short_answer'>;
export type ErrorElicitationCorrectness = 'correct' | 'incorrect';

export type TaskAnswerValue = string | boolean | string[] | null;

export type UserProgressStatus =
  | 'task_started'
  | 'task_draft'
  | 'task_submitted'
  | 'chat_started'
  | 'completed'
  | 'archived';

export interface TaskQuestionOption {
  id: string;
  label: string;
  value: string;
}

export interface TaskQuestion {
  id: string;
  type: TaskQuestionType;
  blank_id?: string | null;
  prompt: string;
  placeholder?: string | null;
  source_text?: string | null;
  options?: TaskQuestionOption[];
  required?: boolean;
  correct_answer?: unknown;
  explanation?: string | null;
  // 研究者設定的理由通過標準，不在受測者作答介面顯示。
  reasoning_criteria?: string;
}

export interface ErrorElicitationQuestion extends TaskQuestion {
  type: ErrorElicitationQuestionType;
  required?: true;
  correct_answer: string | boolean | string[];
  reasoning_criteria: string;
}

export interface TaskAllCorrectFallback {
  id: string;
  incorrect_claim: string;
  correct_interpretation: string;
  source_text?: string | null;
  historical_concept?: string | null;
  reasoning_process?: string | null;
  evidence_ids?: string[];
}

export interface TaskEvaluationPayload {
  contract_version?: typeof ERROR_ELICITATION_CONTRACT_VERSION;
  questions?: TaskQuestion[];
  rubric?: string | null;
  target_misconceptions?: string[];
  all_correct_fallback?: TaskAllCorrectFallback | null;
  [key: string]: unknown;
}

export interface ErrorElicitationEvaluationPayload extends TaskEvaluationPayload {
  contract_version: typeof ERROR_ELICITATION_CONTRACT_VERSION;
  questions: ErrorElicitationQuestion[];
}

export interface TaskStudentAnswer {
  question_id: string;
  blank_id?: string | null;
  type: TaskQuestionType;
  prompt: string;
  value: TaskAnswerValue;
  // 分批切換前暫為選填；新版每題都收集學生原始理由。
  rationale?: string;
}

export interface ErrorElicitationResponsePayload {
  contract_version: typeof ERROR_ELICITATION_CONTRACT_VERSION;
  answers: Array<Pick<TaskStudentAnswer, 'question_id'> & {
    value: string | boolean | null;
    rationale: string;
  }>;
}

export interface ErrorElicitationReasoningJudgement {
  question_id: string;
  reasoning_correct: boolean;
  reasoning_issue: 'none' | 'factual_error' | 'unsupported_inference' | 'insufficient_reasoning';
  reasoning_feedback: string;
}

export interface ErrorElicitationQuestionResult extends ErrorElicitationReasoningJudgement {
  answer_correct: boolean;
  correctness: ErrorElicitationCorrectness;
}

export interface HistoricalEvent {
  id: string;
  canonical_name: string;
  description?: string | null;
  century?: number | null;
  start_year?: number | null;
  end_year?: number | null;
  context?: string | null;
  source_summary?: Record<string, unknown>;
  created_by?: string | null;
  archived_at?: string | null;
  materials_locked_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExperimentCondition {
  id: string;
  condition_key: ConditionKey;
  label: string;
  ebl_enabled: boolean;
  roleplay_enabled: boolean;
  agent_mode: 'generic' | 'persona';
  response_policy: 'standard' | 'scaffold';
  description?: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Participant {
  id: string;
  code: string;
  auth_user_id?: string | null;
  display_name?: string | null;
  cohort?: string | null;
  condition_list: string[];
  status: 'active' | 'completed' | 'excluded' | 'archived';
  notes?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface EventTask {
  id: string;
  event_id: string;
  title?: string | null;
  story_text: string;
  display_text: string;
  evaluation_payload: TaskEvaluationPayload;
  revision_state: 'llm_generated' | 'teacher_modified' | 'manual';
  created_at: string;
  updated_at: string;
}

export interface TaskAttempt {
  id: string;
  task_id: string;
  event_id: string;
  session_id?: string | null;
  user_id?: string | null;
  status: 'in_progress' | 'processing' | 'submitted' | 'failed';
  response_payload: Record<string, unknown>;
  judgement_payload: Record<string, unknown>;
  submitted_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Persona {
  id: string;
  event_id: string;
  name: string;
  english_name?: string | null;
  role?: string | null;
  biography?: string | null;
  expertise_areas: string[];
  sources?: Array<Record<string, unknown>>;
  prompt_profile: Record<string, unknown>;
  avatar_url?: string | null;
  active: boolean;
  archived_at?: string | null;
  sort_order: number;
  revision_state: 'llm_generated' | 'teacher_modified' | 'manual';
  created_at: string;
  updated_at: string;
}

export interface Annotation {
  text: string;
  explanation: string;
}

export interface RagSource {
  source: string;
  section_title: string;
  content: string;
}

export interface ChatMessage {
  id?: string;
  conversation_id?: string | null;
  persona_id?: string | null;
  speaker_type: SpeakerType;
  speaker_name: string;
  sequence_index: number;
  content: string;
  annotations?: Annotation[];
  rag_sources?: RagSource[];
  metadata?: Record<string, unknown>;
  client_request_id?: string | null;
  operation_status?: 'pending' | 'processing' | 'completed' | 'failed' | null;
  created_at?: string;
}

export interface RelatedEvent {
  event_name: string;
  event_year: number | null;
  event_id?: string | null;
  relevance_reason: string;
  is_explorable: boolean;
}

export interface EventWithPersonas extends HistoricalEvent {
  personas: Persona[];
  latest_task?: EventTask | null;
}

export interface EventInitializeResponse {
  event_id: string;
  session_id: string;
  event: HistoricalEvent;
  task: EventTask;
  personas: Persona[];
  condition: ExperimentCondition;
}

export interface TaskSubmitResponse {
  attempt_id: string;
  conversation_id: string;
  event: HistoricalEvent;
  task: EventTask;
  personas: Persona[];
  condition: ExperimentCondition;
  attempt: TaskAttempt;
  judgement: Record<string, unknown>;
  greeting: string;
  history: ChatMessage[];
}

export interface TaskSubmissionAcceptedResponse {
  attempt_id: string;
  status: TaskAttempt['status'];
  poll_url: string;
}

export interface TaskSubmissionStatusResponse {
  attempt: TaskAttempt;
  result?: TaskSubmitResponse | null;
  error?: string | null;
}

export interface TaskDraftResponse {
  attempt: TaskAttempt;
}

export interface ConversationLoadResponse {
  conversation_id: string;
  session?: ExperimentSession | null;
  event: HistoricalEvent;
  personas: Persona[];
  messages: ChatMessage[];
  condition?: ExperimentCondition | null;
  task?: EventTask | null;
  task_attempt?: TaskAttempt | null;
  related_events?: RelatedEvent[];
}

export interface ExperimentSession {
  id: string;
  condition_id?: string | null;
  condition_key_snapshot: ConditionKey;
  user_id?: string | null;
  event_id: string;
  is_admin_test: boolean;
  status: 'initialized' | 'task_submitted' | 'conversation_started' | 'completed' | 'archived';
  timer_started_at?: string | null;
  timer_ends_at?: string | null;
  completed_at?: string | null;
  completion_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionRestartResponse {
  archived_sessions: ExperimentSession[];
  new_session: ExperimentSession;
}

export interface SessionStateResponse {
  session: ExperimentSession;
  event: HistoricalEvent;
  task?: EventTask | null;
  personas: Persona[];
  condition?: ExperimentCondition | null;
  attempt?: TaskAttempt | null;
  conversation_id?: string | null;
}

export interface UserProgressItem {
  event_id: string;
  condition_key: ConditionKey;
  session_id: string;
  task_id?: string | null;
  attempt_id?: string | null;
  conversation_id?: string | null;
  status: UserProgressStatus;
  updated_at: string;
}

export interface UserProgressResponse {
  progress: UserProgressItem[];
}

export interface ParticipantMeResponse {
  participant: Participant;
  progress: UserProgressItem[];
}

export interface ChatResponse {
  response: string;
  selected_persona?: Persona | null;
  assistant_name: string;
  message: ChatMessage;
  annotations: Annotation[];
  related_events?: RelatedEvent[];
  dynamic_context?: string;
  rag_sources?: RagSource[];
}

export interface ChatOperationStatusResponse {
  client_request_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  retryable: boolean;
  learner_message: ChatMessage;
  response?: ChatResponse | null;
}

export type ChatStreamEvent =
  | { type: 'user_message'; message: ChatMessage }
  | { type: 'status'; stage: 'generating' | 'streaming'; message: string }
  | { type: 'delta'; content: string }
  | { type: 'complete'; response: ChatResponse }
  | { type: 'error'; detail: string; retryable: boolean };

export interface ResearchLogChange {
  before: unknown;
  after: unknown;
}

export interface ResearchLogPayload {
  updated_fields?: string[];
  changes?: Record<string, ResearchLogChange>;
  [key: string]: unknown;
}

export interface ResearchLog {
  id: string;
  user_id?: string | null;
  session_id?: string | null;
  event_id?: string | null;
  task_id?: string | null;
  attempt_id?: string | null;
  conversation_id?: string | null;
  message_id?: string | null;
  action_type: string;
  payload: ResearchLogPayload;
  created_at: string;
}

export interface AdminSnapshotResponse {
  events: EventWithPersonas[];
  conditions: ExperimentCondition[];
  participants: Participant[];
  sessions: ExperimentSession[];
  research_logs: ResearchLog[];
}

export interface AdminAuthUserSummary {
  id: string;
  email?: string | null;
  created_at?: string | null;
  last_sign_in_at?: string | null;
  bound_participant_id?: string | null;
  bound_participant_code?: string | null;
}

export interface AdminAuthUsersResponse {
  users: AdminAuthUserSummary[];
}

export interface PromptPreviewModule {
  name: string;
  content: string;
}

export interface AdminPromptPreviewResponse {
  event: HistoricalEvent;
  condition: ExperimentCondition;
  persona?: Persona | null;
  sample_user_message: string;
  modules: PromptPreviewModule[];
  prompt: string;
}

export interface AdminPromptDryRunResponse extends AdminPromptPreviewResponse {
  response: string;
  annotations: Annotation[];
  related_events: RelatedEvent[];
  dynamic_context: string;
  rag_sources: RagSource[];
}

export interface AdminConversationStats {
  total_messages: number;
  learner_messages: number;
  assistant_messages: number;
  completed_exchanges: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  llm_messages_total: number;
  llm_messages_with_usage: number;
  token_usage_coverage: number;
  token_usage_complete: boolean;
  first_message_at?: string | null;
  last_message_at?: string | null;
  duration_seconds?: number | null;
}

export interface AdminMaterialSnapshot {
  status: 'captured' | 'legacy_missing';
  material_hash?: string | null;
  hash_verified: boolean;
  captured_at?: string | null;
  materials: Record<string, unknown>;
}

export interface AdminPromptRecord {
  stage: string;
  message_id?: string | null;
  prompt_hash: string;
  hash_verified: boolean;
  prompt: string;
  modules: Array<{ name: string; content: string }>;
  llm_call?: Record<string, unknown> | null;
  created_at: string;
}

export interface AdminSessionResearchResponse {
  participant_code: string;
  participant_bound: boolean;
  session: ExperimentSession;
  event: HistoricalEvent;
  condition?: ExperimentCondition | null;
  task?: EventTask | null;
  attempt?: TaskAttempt | null;
  conversation?: {
    id: string;
    event_id: string;
    task_attempt_id?: string | null;
    session_id?: string | null;
    user_id?: string | null;
    status: 'active' | 'archived';
    started_at: string;
    archived_at?: string | null;
    created_at: string;
    updated_at: string;
  } | null;
  messages: ChatMessage[];
  stats: AdminConversationStats;
  material_snapshot: AdminMaterialSnapshot;
  prompt_records: AdminPromptRecord[];
  research_logs: ResearchLog[];
}
