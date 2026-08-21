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
import {
  fetchParticipantMe,
  fetchUserProgress,
  initializeEventMaterial,
} from '~/utils/histosphereApi';
import { experimentConditionCodeByKey } from '~/utils/experimentConditions';

export type LocalConditionProgress = {
  status: 'not_started' | UserProgressStatus;
  sessionId?: string;
  taskId?: string;
  attemptId?: string;
  conversationId?: string;
  updatedAt: string;
};

export type ExperimentStartOptions = {
  userId?: string;
  reuseProgress?: boolean;
  adminKey?: string;
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

export const useExperimentSession = (authStorageScope: ComputedRef<string>) => {
  const participant = ref<Participant | null>(null);
  const progressByEvent = ref<Record<string, Partial<Record<ConditionKey, LocalConditionProgress>>>>({});
  const isInitializing = ref(false);
  const isParticipantLoading = ref(false);
  const initializeError = ref<string | null>(null);
  const participantError = ref<string | null>(null);

  const authUserId = computed(() => authStorageScope.value !== 'guest' ? authStorageScope.value : null);

  const assignedConditionCodes = computed(() => {
    return participant.value?.condition_list?.length
      ? participant.value.condition_list
      : [];
  });

  const currentAssignedConditionCode = computed(() => {
    const assigned = assignedConditionCodes.value;
    if (!assigned.length) return null;

    const completedCodes = new Set<string>();
    const activeProgress: Array<{ code: string; updatedAt: string }> = [];
    for (const eventProgress of Object.values(progressByEvent.value)) {
      for (const [conditionKey, progress] of Object.entries(eventProgress)) {
        if (!progress) continue;
        const code = experimentConditionCodeByKey[conditionKey as ConditionKey];
        if (!code || !assigned.includes(code)) continue;
        if (progress.status === 'completed') {
          completedCodes.add(code);
        } else if (progress.status !== 'archived') {
          activeProgress.push({ code, updatedAt: progress.updatedAt });
        }
      }
    }

    if (activeProgress.length) {
      activeProgress.sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt));
      return activeProgress[0]?.code || null;
    }
    return assigned.find((code) => !completedCodes.has(code)) || null;
  });

  const progressStorageKey = () => `histosphere-progress:${authStorageScope.value}`;

  const resetForAuthScope = async () => {
    progressByEvent.value = {};
    participant.value = null;
    participantError.value = null;
  };

  const loadProgressFromApi = async () => {
    if (!authUserId.value) {
      progressByEvent.value = {};
      return;
    }
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
      progressByEvent.value = progressItemsToLocalMap(response.progress || []);
      saveLocalProgress();
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
    if (authStorageScope.value === 'guest') {
      progressByEvent.value = {};
      return;
    }
    try {
      progressByEvent.value = JSON.parse(localStorage.getItem(progressStorageKey()) || '{}');
    } catch {
      progressByEvent.value = {};
    }
  };

  const saveLocalProgress = () => {
    if (!import.meta.client) return;
    if (authStorageScope.value === 'guest') return;
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

  const startCondition = async (
    event: EventWithPersonas,
    condition: ExperimentCondition,
    options: ExperimentStartOptions = {},
  ) => {
    const eventProgress = progressByEvent.value[event.id] || {};
    const eventAlreadyCompleted = Object.values(eventProgress).some(
      (item) => item?.status === 'completed',
    );
    if (!options.adminKey && eventAlreadyCompleted) {
      initializeError.value = '此歷史事件已完成，無法再次進行。若需重做，請由管理員封存舊 session 並重建。';
      return;
    }
    const progress = options.reuseProgress === false
      ? null
      : progressForEvent(event.id, condition.condition_key);
    const requestUserId = options.userId || authUserId.value;
    if (!requestUserId) {
      initializeError.value = '請先登入受測者帳號。';
      return;
    }
    if (progress?.conversationId) {
      await navigateTo({
        path: `/conversations/${progress.conversationId}`,
      });
      return;
    }
    if (progress?.sessionId && progress.taskId) {
      await navigateTo({
        path: `/sessions/${progress.sessionId}/task`,
        query: options.userId ? { authUserId: requestUserId } : undefined,
      });
      return;
    }
    await initializeEvent(event.canonical_name, condition.condition_key, false, true, {
      userId: requestUserId,
      reloadProgress: !options.userId,
      adminKey: options.adminKey,
    });
  };

  const initializeEvent = async (
    name: string,
    conditionKey: ConditionKey,
    rebuild: boolean,
    navigateToTask: boolean,
    runtime: {
      userId?: string;
      reloadProgress?: boolean;
      adminKey?: string;
    } = {},
  ) => {
    isInitializing.value = true;
    initializeError.value = null;
    try {
      const requestUserId = runtime.userId || authUserId.value;
      if (!requestUserId) {
        throw new Error('請先登入受測者帳號。');
      }
      const response: EventInitializeResponse = await initializeEventMaterial({
        eventName: name,
        conditionKey,
        rebuild,
        userId: requestUserId,
        adminKey: runtime.adminKey,
      });

      if (navigateToTask) {
        if (runtime.reloadProgress !== false) {
          markProgress(response.event_id, response.condition.condition_key, {
            status: 'task_started',
            sessionId: response.session_id,
            taskId: response.task.id,
            updatedAt: new Date().toISOString(),
          });
          await loadProgressFromApi();
        }
        const taskData = useState<EventInitializeResponse | null>('taskData', () => null);
        taskData.value = response;
        await navigateTo({
          path: `/sessions/${response.session_id}/task`,
          query: runtime.userId ? { authUserId: runtime.userId } : undefined,
        });
      }
      return response;
    } catch (e: any) {
      initializeError.value = e.data?.detail || e.data?.message || e.message || '建立流程失敗，請稍後再試。';
      return null;
    } finally {
      isInitializing.value = false;
    }
  };

  return {
    initializeError,
    initializeEvent,
    isInitializing,
    isParticipantLoading,
    loadProgressFromApi,
    loadParticipantForAuthUser,
    participant,
    participantError,
    authUserId,
    assignedConditionCodes,
    currentAssignedConditionCode,
    progressByEvent,
    resetForAuthScope,
    startCondition,
  };
};
