import type {
  AdminAuthUsersResponse,
  AdminPromptDryRunResponse,
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
  ExperimentSession,
  HistoricalEvent,
  ParticipantMeResponse,
  Participant,
  Persona,
  SessionStateResponse,
  TaskDraftResponse,
  TaskSubmissionAcceptedResponse,
  TaskSubmissionStatusResponse,
  UserProgressResponse,
} from '../types';
import { getAdminSessionKey } from '~/utils/adminSession';
import { getCurrentAccessToken } from '~/utils/authSession';

export type FrontendFetchOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  headers?: Record<string, string>;
  query?: Record<string, string>;
  body?: any;
};

export type FrontendFetcher = <T>(url: string, options?: FrontendFetchOptions) => Promise<T>;

export type InitializeEventInput = {
  eventName: string;
  conditionKey: ConditionKey;
  rebuild: boolean;
  userId?: string | null;
  adminKey?: string | null;
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

export type ParticipantUpdateInput = Partial<Pick<
  Participant,
  'auth_user_id' | 'display_name' | 'cohort' | 'condition_list' | 'status' | 'notes' | 'metadata'
>>;

const adminHeaders = (adminKey: string) => ({ 'x-admin-key': adminKey });
const learnerAuthOptions = () => {
  const adminKey = getAdminSessionKey();
  if (adminKey) {
    return { headers: adminHeaders(adminKey) };
  }
  const accessToken = getCurrentAccessToken();
  return accessToken
    ? { headers: { Authorization: `Bearer ${accessToken}` } }
    : {};
};

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

export const fetchAdminAuthUsers = (adminKey: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<AdminAuthUsersResponse>('/api/admin/auth-users', {
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

export const runAdminPromptDryRun = (
  adminKey: string,
  input: PromptPreviewInput,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<AdminPromptDryRunResponse>('/api/admin/prompt-dry-run', {
    method: 'POST',
    headers: adminHeaders(adminKey),
    body: {
      event_id: input.eventId,
      condition_key: input.conditionKey,
      persona_id: input.personaId || null,
      sample_user_message: input.sampleUserMessage || '請說明這個事件的重要性。',
    },
  });
};

export const initializeEventMaterial = (input: InitializeEventInput, fetcher: FrontendFetcher = $fetch) => {
  const authOptions = input.adminKey
    ? { headers: adminHeaders(input.adminKey) }
    : learnerAuthOptions();
  return fetcher<EventInitializeResponse>('/api/event/initialize', {
    method: 'POST',
    ...authOptions,
    body: {
      event_name: input.eventName,
      condition_key: input.conditionKey,
      rebuild: input.rebuild,
      user_id: input.userId || null,
    },
  });
};

export const archiveAdminEvent = (adminKey: string, eventId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<HistoricalEvent>(`/api/admin/events/${eventId}/archive`, {
    method: 'POST',
    headers: adminHeaders(adminKey),
  });
};

export const restoreAdminEvent = (adminKey: string, eventId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<HistoricalEvent>(`/api/admin/events/${eventId}/restore`, {
    method: 'POST',
    headers: adminHeaders(adminKey),
  });
};

export const fetchUserProgress = (userId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<UserProgressResponse>('/api/sessions/progress', {
    ...learnerAuthOptions(),
    query: { user_id: userId },
  });
};

export const fetchParticipantMe = (authUserId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<ParticipantMeResponse>('/api/participants/me', {
    ...learnerAuthOptions(),
    query: { auth_user_id: authUserId },
  });
};

export const fetchSessionState = (sessionId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<SessionStateResponse>(`/api/sessions/${sessionId}/state`, learnerAuthOptions());
};

export const saveTaskDraft = (taskId: string, input: TaskDraftInput, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<TaskDraftResponse>(`/api/tasks/${taskId}/draft`, {
    method: 'PATCH',
    ...learnerAuthOptions(),
    body: {
      session_id: input.sessionId,
      user_id: input.userId || null,
      response_payload: input.responsePayload,
    },
  });
};

export const submitTaskAnswers = (taskId: string, input: TaskSubmitInput, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<TaskSubmissionAcceptedResponse>(`/api/tasks/${taskId}/submit`, {
    method: 'POST',
    ...learnerAuthOptions(),
    body: {
      session_id: input.sessionId,
      user_id: input.userId || null,
      response_payload: input.responsePayload,
    },
  });
};

export const fetchTaskSubmissionStatus = (attemptId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<TaskSubmissionStatusResponse>(`/api/tasks/attempts/${attemptId}`, learnerAuthOptions());
};

export const fetchConversation = (conversationId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<ConversationLoadResponse>(`/api/conversations/${conversationId}`, learnerAuthOptions());
};

export const sendChatMessage = (input: ChatMessageInput, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<ChatResponse>('/api/chat', {
    method: 'POST',
    ...learnerAuthOptions(),
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

export const updateAdminParticipant = (
  adminKey: string,
  participantId: string,
  body: ParticipantUpdateInput,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<Participant>(`/api/admin/participants/${participantId}`, {
    method: 'PATCH',
    headers: adminHeaders(adminKey),
    body,
  });
};

export const startAdminSessionTimer = (
  adminKey: string,
  sessionId: string,
  durationMinutes: number,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<ExperimentSession>(`/api/admin/sessions/${sessionId}/timer`, {
    method: 'POST',
    headers: adminHeaders(adminKey),
    body: { duration_minutes: durationMinutes },
  });
};

export const cancelAdminSessionTimer = (
  adminKey: string,
  sessionId: string,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<ExperimentSession>(`/api/admin/sessions/${sessionId}/timer`, {
    method: 'DELETE',
    headers: adminHeaders(adminKey),
  });
};
