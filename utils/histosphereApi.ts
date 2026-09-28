import type {
  AdminAuthUsersResponse,
  AdminParticipantPreviewResponse,
  AdminLLMUsageResponse,
  AdminPromptDryRunResponse,
  AdminSessionResearchResponse,
  AdminSnapshotResponse,
  AdminPromptPreviewResponse,
  ChatMessage,
  ChatOperationStatusResponse,
  ChatResponse,
  ChatStreamEvent,
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
  ParticipantActivityAssignment,
  PosttestDraftInput,
  PosttestStateResponse,
  Persona,
  SessionRestartResponse,
  SessionClosure,
  SessionStateResponse,
  TaskDraftResponse,
  TaskSubmissionAcceptedResponse,
  TaskSubmissionStatusResponse,
  TaskSubmitResponse,
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
  previewParticipantId?: string | null;
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
  clientRequestId?: string;
  retryFailed?: boolean;
  interactionAction?: 'next_error';
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
  'title' | 'story_text' | 'error_elicitation_task_full_text' | 'evaluation_payload'
> & {
  revision_state: EventTask['revision_state'];
};

export type PersonaUpdateInput = Partial<Pick<
  Persona,
  'name' | 'role' | 'biography' | 'avatar_url' | 'prompt_profile' | 'active' | 'revision_state'
>>;

export type PersonaCreateInput = Pick<Persona, 'event_id' | 'name'> & Partial<Pick<
  Persona,
  'english_name' | 'role' | 'biography' | 'avatar_url' | 'prompt_profile' | 'active' | 'sort_order' | 'revision_state'
>>;

export type ConditionUpdateInput = Pick<
  ExperimentCondition,
  'label' | 'ebl_enabled' | 'roleplay_enabled' | 'agent_mode' | 'response_policy' | 'description' | 'active'
>;

export type ParticipantUpdateInput = Partial<Pick<
  Participant,
  'auth_user_id' | 'display_name' | 'cohort' | 'condition_list' | 'status' | 'notes' | 'metadata'
>> & { activity_assignments?: ParticipantActivityAssignment[] };

export type ParticipantCreateInput = Pick<Participant, 'code'> & Partial<Pick<
  Participant,
  'auth_user_id' | 'display_name' | 'cohort' | 'condition_list' | 'notes' | 'metadata'
>> & { activity_assignments?: ParticipantActivityAssignment[] };

const adminHeaders = (adminKey: string) => ({ 'x-admin-key': adminKey });
export const learnerAuthHeaders = (): Record<string, string> => {
  const adminKey = getAdminSessionKey();
  if (adminKey) return adminHeaders(adminKey);
  const accessToken = getCurrentAccessToken();
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
};
const learnerAuthOptions = (): { headers?: Record<string, string> } => {
  const headers = learnerAuthHeaders();
  return Object.keys(headers).length > 0 ? { headers } : {};
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

export const fetchAdminParticipantPreview = (
  adminKey: string,
  participantId: string,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<AdminParticipantPreviewResponse>(`/api/admin/participants/${participantId}/preview`, {
    headers: adminHeaders(adminKey),
  });
};

export const fetchAdminSessionResearch = (
  adminKey: string,
  sessionId: string,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<AdminSessionResearchResponse>(`/api/admin/sessions/${sessionId}/research`, {
    headers: adminHeaders(adminKey),
  });
};

export const fetchAdminLlmUsage = (adminKey: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<AdminLLMUsageResponse>('/api/admin/llm-usage', { headers: adminHeaders(adminKey) });
};

export const downloadAdminResearchExport = async (
  adminKey: string,
  format: 'json' | 'csv',
) => {
  const response = await fetch(`/api/admin/research-export?format=${format}`, {
    headers: adminHeaders(adminKey),
  });
  if (!response.ok) throw new Error(`研究資料匯出失敗（${response.status}）`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `histosphere-research.${format}`;
  anchor.click();
  URL.revokeObjectURL(url);
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
      ...(input.previewParticipantId ? { preview_participant_id: input.previewParticipantId } : {}),
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

export const setAdminEventMaterialLock = (
  adminKey: string,
  eventId: string,
  locked: boolean,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<HistoricalEvent>(`/api/admin/events/${eventId}/material-lock`, {
    method: 'POST',
    headers: adminHeaders(adminKey),
    body: { locked },
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

export const submitSessionClosure = (sessionId: string, closureId: string, reflection: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<SessionClosure>(`/api/sessions/${sessionId}/closure`, {
    method: 'POST', ...learnerAuthOptions(), body: { closure_id: closureId, reflection },
  });
};

export const fetchPosttest = (sessionId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<PosttestStateResponse>(`/api/sessions/${sessionId}/posttest`, learnerAuthOptions());
};

export const startPosttest = (sessionId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<PosttestStateResponse>(`/api/sessions/${sessionId}/posttest/start`, {
    method: 'POST', ...learnerAuthOptions(),
  });
};

export const savePosttestDraft = (sessionId: string, input: PosttestDraftInput, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<PosttestStateResponse>(`/api/sessions/${sessionId}/posttest`, {
    method: 'PATCH', ...learnerAuthOptions(), body: input,
  });
};

export const advancePosttest = (sessionId: string, revision: number, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<PosttestStateResponse>(`/api/sessions/${sessionId}/posttest/advance`, {
    method: 'POST', ...learnerAuthOptions(), body: { revision },
  });
};

export const submitPosttest = (sessionId: string, revision: number, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<PosttestStateResponse>(`/api/sessions/${sessionId}/posttest/submit`, {
    method: 'POST', ...learnerAuthOptions(), body: { revision },
  });
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

export const enterTaskInteraction = (attemptId: string, fetcher: FrontendFetcher = $fetch) => {
  return fetcher<TaskSubmitResponse>(`/api/tasks/attempts/${attemptId}/enter`, { ...learnerAuthOptions(), method: 'POST' });
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
      client_request_id: input.clientRequestId,
      retry_failed: input.retryFailed || false,
      interaction_action: input.interactionAction,
    },
  });
};

export const fetchChatOperationStatus = (
  conversationId: string,
  clientRequestId: string,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<ChatOperationStatusResponse>(
    `/api/chat/operations/${encodeURIComponent(clientRequestId)}`,
    {
      ...learnerAuthOptions(),
      query: { conversation_id: conversationId },
    },
  );
};

export const parseChatStreamFrame = (frame: string): ChatStreamEvent | null => {
  const data = frame
    .split('\n')
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n');
  if (!data) return null;
  return JSON.parse(data) as ChatStreamEvent;
};

export const sendChatMessageStream = async (
  input: ChatMessageInput,
  onEvent: (event: ChatStreamEvent) => void | Promise<void>,
  fetcher: typeof fetch = globalThis.fetch.bind(globalThis),
) => {
  const response = await fetcher('/api/chat/stream', {
    method: 'POST',
    headers: {
      ...learnerAuthHeaders(),
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      conversation_id: input.conversationId,
      user_message: input.userMessage,
      history: input.history,
      client_request_id: input.clientRequestId,
      retry_failed: input.retryFailed || false,
      interaction_action: input.interactionAction,
    }),
  });

  if (!response.ok) {
    const rawError = await response.text();
    let detail = `聊天請求失敗（${response.status}）`;
    try {
      const parsed = JSON.parse(rawError) as { detail?: string };
      detail = parsed.detail || detail;
    } catch {
      if (rawError.trim()) detail = rawError.trim();
    }
    throw new Error(detail);
  }
  if (!response.body) throw new Error('瀏覽器不支援串流回覆。');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let completedResponse: ChatResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    buffer = (buffer + decoder.decode(value, { stream: !done })).replace(/\r\n/g, '\n');

    let separatorIndex = buffer.indexOf('\n\n');
    while (separatorIndex >= 0) {
      const frame = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);
      const event = parseChatStreamFrame(frame);
      if (event) {
        await onEvent(event);
        if (event.type === 'complete') completedResponse = event.response;
        if (event.type === 'error') throw new Error(event.detail);
      }
      separatorIndex = buffer.indexOf('\n\n');
    }
    if (done) break;
  }

  if (!completedResponse) throw new Error('串流在完成前中斷，訊息已由後端保存。');
  return completedResponse;
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

export const createAdminPersona = (
  adminKey: string,
  body: PersonaCreateInput,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<Persona>('/api/personas', {
    method: 'POST',
    headers: adminHeaders(adminKey),
    body,
  });
};

export const archiveAdminPersona = (
  adminKey: string,
  personaId: string,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<{ success: boolean }>(`/api/personas/${personaId}`, {
    method: 'DELETE',
    headers: adminHeaders(adminKey),
  });
};

export const restoreAdminPersona = (
  adminKey: string,
  personaId: string,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<Persona>(`/api/personas/${personaId}/restore`, {
    method: 'POST',
    headers: adminHeaders(adminKey),
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

export const createAdminParticipant = (
  adminKey: string,
  body: ParticipantCreateInput,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<Participant>('/api/admin/participants', {
    method: 'POST',
    headers: adminHeaders(adminKey),
    body,
  });
};

export const archiveAdminParticipant = (
  adminKey: string,
  participantId: string,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<Participant>(`/api/admin/participants/${participantId}/archive`, {
    method: 'POST',
    headers: adminHeaders(adminKey),
  });
};

export const restoreAdminParticipant = (
  adminKey: string,
  participantId: string,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<Participant>(`/api/admin/participants/${participantId}/restore`, {
    method: 'POST',
    headers: adminHeaders(adminKey),
  });
};

export const resetAdminSessionTimer = (
  adminKey: string,
  sessionId: string,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<ExperimentSession>(`/api/admin/sessions/${sessionId}/timer`, {
    method: 'POST',
    headers: adminHeaders(adminKey),
    body: { duration_minutes: 5 },
  });
};

export const restartAdminSession = (
  adminKey: string,
  sessionId: string,
  fetcher: FrontendFetcher = $fetch,
) => {
  return fetcher<SessionRestartResponse>(`/api/admin/sessions/${sessionId}/restart`, {
    method: 'POST',
    headers: adminHeaders(adminKey),
  });
};
