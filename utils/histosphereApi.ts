import type {
  AdminSnapshotResponse,
  AdminPromptPreviewResponse,
  ChatMessage,
  ChatResponse,
  ConditionKey,
  ConversationLoadResponse,
  EventInitializeResponse,
  EventTask,
  EventWithPersonas,
  ExperimentCondition,
  HistoricalEvent,
  ParticipantMeResponse,
  Persona,
  SessionStateResponse,
  TaskDraftResponse,
  TaskSubmitResponse,
  UserProgressResponse,
} from '../types';

export type FrontendFetchOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  headers?: Record<string, string>;
  query?: Record<string, string>;
  body?: unknown;
};

export type FrontendFetcher = <T>(url: string, options?: FrontendFetchOptions) => Promise<T>;

export type InitializeEventInput = {
  eventName: string;
  conditionKey: ConditionKey;
  rebuild: boolean;
  userId?: string | null;
};

export type TaskDraftInput = {
  sessionId: string;
  userId?: string | null;
  responsePayload: Record<string, unknown>;
};

export type TaskSubmitInput = TaskDraftInput;

export type ChatMessageInput = {
  conversationId: string;
  userMessage: string;
  history: ChatMessage[];
  targetPersonaId?: string | null;
};

export type PromptPreviewInput = {
  eventId: string;
  conditionKey: ConditionKey;
  personaId?: string | null;
  sampleUserMessage?: string;
};

export type EventUpdateInput = Pick<
  HistoricalEvent,
  'canonical_name' | 'description' | 'century' | 'start_year' | 'end_year' | 'context' | 'source_summary'
>;

export type TaskUpdateInput = Pick<
  EventTask,
  'title' | 'story_text' | 'display_text' | 'evaluation_payload'
> & {
  revision_state: EventTask['revision_state'];
};

export type PersonaUpdateInput = Pick<
  Persona,
  'name' | 'role' | 'biography' | 'prompt_profile' | 'active' | 'revision_state'
>;

export type ConditionUpdateInput = Pick<
  ExperimentCondition,
  'label' | 'ebl_enabled' | 'roleplay_enabled' | 'agent_mode' | 'response_policy' | 'description' | 'active'
>;

const adminHeaders = (adminKey: string) => ({ 'x-admin-key': adminKey });

export const fetchConditions = (fetcher: FrontendFetcher = $fetch) => {
  return fetcher<ExperimentCondition[]>('/api/conditions');
};

export const fetchEvents = (fetcher: FrontendFetcher = $fetch) => {
  return fetcher<EventWithPersonas[]>('/api/events');
};

export const fetchAdminSnapshot = (adminKey: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<AdminSnapshotResponse>('/api/admin/snapshot', {
    headers: adminHeaders(adminKey),
  });
};

export const fetchAdminPromptPreview = (
  adminKey: string,
  input: PromptPreviewInput,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<AdminPromptPreviewResponse>('/api/admin/prompt-preview', {
    headers: adminHeaders(adminKey),
    query: {
      event_id: input.eventId,
      condition_key: input.conditionKey,
      ...(input.personaId ? { persona_id: input.personaId } : {}),
      ...(input.sampleUserMessage ? { sample_user_message: input.sampleUserMessage } : {}),
    },
  });
};

export const initializeEventMaterial = (input: InitializeEventInput, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<EventInitializeResponse>('/api/event/initialize', {
    method: 'POST',
    body: {
      event_name: input.eventName,
      condition_key: input.conditionKey,
      rebuild: input.rebuild,
      user_id: input.userId || null,
    },
  });
};

export const deleteEventMaterial = (eventId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<{ success: boolean }>(`/api/event/${eventId}`, {
    method: 'DELETE',
  });
};

export const fetchUserProgress = (userId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<UserProgressResponse>('/api/sessions/progress', {
    query: { user_id: userId },
  });
};

export const fetchParticipantMe = (authUserId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<ParticipantMeResponse>('/api/participants/me', {
    query: { auth_user_id: authUserId },
  });
};

export const fetchSessionState = (sessionId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<SessionStateResponse>(`/api/sessions/${sessionId}/state`);
};

export const saveTaskDraft = (taskId: string, input: TaskDraftInput, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<TaskDraftResponse>(`/api/tasks/${taskId}/draft`, {
    method: 'PATCH',
    body: {
      session_id: input.sessionId,
      user_id: input.userId || null,
      response_payload: input.responsePayload,
    },
  });
};

export const submitTaskAnswers = (taskId: string, input: TaskSubmitInput, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<TaskSubmitResponse>(`/api/tasks/${taskId}/submit`, {
    method: 'POST',
    body: {
      session_id: input.sessionId,
      user_id: input.userId || null,
      response_payload: input.responsePayload,
    },
  });
};

export const fetchConversation = (conversationId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<ConversationLoadResponse>(`/api/conversations/${conversationId}`);
};

export const sendChatMessage = (input: ChatMessageInput, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<ChatResponse>('/api/chat', {
    method: 'POST',
    body: {
      conversation_id: input.conversationId,
      user_message: input.userMessage,
      history: input.history,
      target_persona_id: input.targetPersonaId || null,
    },
  });
};

export const updateAdminEvent = (
  adminKey: string,
  eventId: string,
  body: EventUpdateInput,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<HistoricalEvent>(`/api/admin/events/${eventId}`, {
    method: 'PATCH',
    headers: adminHeaders(adminKey),
    body,
  });
};

export const updateAdminTask = (
  adminKey: string,
  taskId: string,
  body: TaskUpdateInput,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<EventTask>(`/api/admin/tasks/${taskId}`, {
    method: 'PATCH',
    headers: adminHeaders(adminKey),
    body,
  });
};

export const updateAdminPersona = (
  adminKey: string,
  personaId: string,
  body: PersonaUpdateInput,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<Persona>(`/api/admin/personas/${personaId}`, {
    method: 'PATCH',
    headers: adminHeaders(adminKey),
    body,
  });
};

export const updateAdminCondition = (
  adminKey: string,
  conditionId: string,
  body: ConditionUpdateInput,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<ExperimentCondition>(`/api/admin/conditions/${conditionId}`, {
    method: 'PATCH',
    headers: adminHeaders(adminKey),
    body,
  });
};
