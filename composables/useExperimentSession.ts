// useExperimentSession 管理首頁啟動實驗 session 所需的 participant、progress、initialize flow。
// 事件列表本身仍由首頁控制，因為它是素材庫 UI 狀態，不是 session flow。
import { computed, ref } from 'vue';
import type { ComputedRef } from 'vue';
import type {
  ConditionKey,
  EventInitializeResponse,
  EventWithPersonas,
  ExperimentCondition,
  Participant,
  UserProgressItem,
  UserProgressResponse,
  UserProgressStatus,
} from '~/types';
import { participantUuid } from '~/composables/useStudentTask';
import {
  fetchParticipantMe,
  fetchUserProgress,
  initializeEventMaterial,
} from '~/utils/histosphereApi';

export type LocalConditionProgress = {
  status: 'not_started' | UserProgressStatus;
  sessionId?: string;
  taskId?: string;
  attemptId?: string;
  conversationId?: string;
  updatedAt: string;
};

const progressItemsToLocalMap = (items: UserProgressItem[]) => {
  const next: Record<string, Partial<Record<ConditionKey, LocalConditionProgress>>> = {};
  for (const item of items) {
    const existing = next[item.event_id]?.[item.condition_key];
    if (existing && Date.parse(existing.updatedAt) >= Date.parse(item.updated_at)) {
      continue;
    }
    next[item.event_id] = {
      ...(next[item.event_id] || {}),
      [item.condition_key]: {
        status: item.status,
        sessionId: item.session_id,
        taskId: item.task_id || undefined,
        attemptId: item.attempt_id || undefined,
        conversationId: item.conversation_id || undefined,
        updatedAt: item.updated_at,
      },
    };
  }
  return next;
};

export const useExperimentSession = (
  authStorageScope: ComputedRef<string>,
  defaultParticipantId: ComputedRef<string>,
) => {
  const participantId = ref('scott-test');
  const participant = ref<Participant | null>(null);
  const progressByEvent = ref<Record<string, Partial<Record<ConditionKey, LocalConditionProgress>>>>({});
  const isInitializing = ref(false);
  const isParticipantLoading = ref(false);
  const initializeError = ref<string | null>(null);
  const participantError = ref<string | null>(null);

  const authUserId = computed(() => {
    return authStorageScope.value !== 'guest'
      ? authStorageScope.value
      : participantUuid(participantId.value);
  });

  const assignedConditionCodes = computed(() => {
    return participant.value?.condition_list?.length
      ? participant.value.condition_list
      : ['01', '02', '03', '04'];
  });

  const participantStorageKey = () => `histosphere-participant-id:${authStorageScope.value}`;
  const progressStorageKey = () => `histosphere-progress:${authStorageScope.value}:${participantId.value || defaultParticipantId.value}`;

  const loadParticipantId = () => {
    if (!import.meta.client) return defaultParticipantId.value;
    return localStorage.getItem(participantStorageKey()) || defaultParticipantId.value;
  };

  const initializeParticipant = () => {
    participantId.value = loadParticipantId();
  };

  const resetForAuthScope = async () => {
    progressByEvent.value = {};
    participant.value = null;
    participantError.value = null;
    participantId.value = loadParticipantId();
  };

  const loadProgressFromApi = async () => {
    try {
      const response: UserProgressResponse = await fetchUserProgress(authUserId.value);
      progressByEvent.value = progressItemsToLocalMap(response.progress || []);
      saveLocalProgress();
    } catch (e) {
      console.warn('Failed to load session progress, using local fallback:', e);
      loadLocalProgress();
    }
  };

  const loadParticipantForAuthUser = async (authUserId: string) => {
    const trimmedAuthUserId = authUserId.trim();
    if (!trimmedAuthUserId) {
      participant.value = null;
      participantError.value = '請先登入受測者帳號。';
      progressByEvent.value = {};
      return null;
    }

    isParticipantLoading.value = true;
    participantError.value = null;
    try {
      const response = await fetchParticipantMe(trimmedAuthUserId);
      participant.value = response.participant;
      participantId.value = response.participant.code;
      progressByEvent.value = progressItemsToLocalMap(response.progress || []);
      saveLocalProgress();
      if (import.meta.client) {
        localStorage.setItem(participantStorageKey(), response.participant.code);
      }
      return response.participant;
    } catch (e: any) {
      participant.value = null;
      progressByEvent.value = {};
      participantError.value = e.data?.detail || e.data?.message || '找不到此登入帳號對應的受測者。';
      return null;
    } finally {
      isParticipantLoading.value = false;
    }
  };

  const loadLocalProgress = () => {
    if (!import.meta.client) return;
    try {
      progressByEvent.value = JSON.parse(localStorage.getItem(progressStorageKey()) || '{}');
    } catch {
      progressByEvent.value = {};
    }
  };

  const saveLocalProgress = () => {
    if (!import.meta.client) return;
    localStorage.setItem(progressStorageKey(), JSON.stringify(progressByEvent.value));
  };

  const markProgress = (eventId: string, conditionKey: ConditionKey, progress: LocalConditionProgress) => {
    progressByEvent.value = {
      ...progressByEvent.value,
      [eventId]: {
        ...(progressByEvent.value[eventId] || {}),
        [conditionKey]: progress,
      },
    };
    saveLocalProgress();
  };

  const progressForEvent = (eventId: string, conditionKey: ConditionKey) => {
    return progressByEvent.value[eventId]?.[conditionKey] || null;
  };

  const startCondition = async (event: EventWithPersonas, condition: ExperimentCondition) => {
    const progress = progressForEvent(event.id, condition.condition_key);
    if (progress?.conversationId) {
      await navigateTo({
        path: `/conversations/${progress.conversationId}`,
      });
      return;
    }
    if (progress?.sessionId && progress.taskId) {
      await navigateTo({
        path: `/sessions/${progress.sessionId}/task`,
        query: {
          participantId: participantId.value,
          authUserId: authUserId.value,
        },
      });
      return;
    }
    await initializeEvent(event.canonical_name, condition.condition_key, false, true);
  };

  const initializeEvent = async (
    name: string,
    conditionKey: ConditionKey,
    rebuild: boolean,
    navigateToTask: boolean,
  ) => {
    isInitializing.value = true;
    initializeError.value = null;
    try {
      const response: EventInitializeResponse = await initializeEventMaterial({
        eventName: name,
        conditionKey,
        rebuild,
        userId: authUserId.value,
      });

      if (navigateToTask) {
        markProgress(response.event_id, conditionKey, {
          status: 'task_started',
          sessionId: response.session_id,
          taskId: response.task.id,
          updatedAt: new Date().toISOString(),
        });
        await loadProgressFromApi();
        const taskData = useState<EventInitializeResponse | null>('taskData', () => null);
        taskData.value = response;
        await navigateTo({
          path: `/sessions/${response.session_id}/task`,
          query: {
            participantId: participantId.value,
            authUserId: authUserId.value,
          },
        });
      }
      return response;
    } catch (e: any) {
      initializeError.value = e.data?.detail || e.data?.message || '建立流程失敗，請稍後再試。';
      return null;
    } finally {
      isInitializing.value = false;
    }
  };

  return {
    initializeError,
    initializeEvent,
    initializeParticipant,
    isInitializing,
    isParticipantLoading,
    loadProgressFromApi,
    loadParticipantForAuthUser,
    participant,
    participantError,
    participantId,
    authUserId,
    assignedConditionCodes,
    progressByEvent,
    resetForAuthScope,
    startCondition,
  };
};
