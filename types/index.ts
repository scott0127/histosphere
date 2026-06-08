export type ConditionKey =
  | 'no_ebl_no_roleplay'
  | 'ebl_no_roleplay'
  | 'no_ebl_roleplay'
  | 'ebl_roleplay';

export type SpeakerType = 'learner' | 'assistant' | 'persona';

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
  response_policy: 'direct' | 'scaffold';
  description?: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EventTask {
  id: string;
  event_id: string;
  title?: string | null;
  story_text: string;
  display_text: string;
  evaluation_payload: Record<string, unknown>;
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
  status: 'in_progress' | 'submitted';
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

export interface ConversationLoadResponse {
  conversation_id: string;
  event: HistoricalEvent;
  personas: Persona[];
  messages: ChatMessage[];
  condition?: ExperimentCondition | null;
  task_attempt?: TaskAttempt | null;
  related_events?: RelatedEvent[];
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

export interface AdminSnapshotResponse {
  events: EventWithPersonas[];
  conditions: ExperimentCondition[];
  sessions: Array<Record<string, unknown>>;
  research_logs: Array<Record<string, unknown>>;
}
