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
  PosttestStage,
  UserProgressItem,
  UserProgressResponse,
  UserProgressStatus,
} from '~/types';
import {
  fetchAdminParticipantPreview,
  fetchParticipantMe,
  fetchUserProgress,
  initializeEventMaterial,
} from '~/utils/histosphereApi';
import { experimentConditionCodeByKey } from '~/utils/experimentConditions';
import { currentParticipantActivity, getParticipantActivities } from '~/utils/participantActivities';

export type LocalConditionProgress = {
  status: 'not_started' | UserProgressStatus;
  sessionId?: string;
  taskId?: string;
  attemptId?: string;
  conversationId?: string;
  posttestStage?: PosttestStage | 'not_started' | null;
  updatedAt: string;
};

export type ExperimentStartOptions = {
  userId?: string;
  reuseProgress?: boolean;
  adminKey?: string;
  previewParticipantId?: string;
};

const progressItemsToLocalMap = (items: UserProgressItem[]) => {
  const next: Record<string, Partial<Record<ConditionKey, LocalConditionProgress>>> = {};
  for (const item of items) {
    if (item.status === 'archived') continue;
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
        posttestStage: item.posttest_stage,
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
  const previewTestUserId = ref<string | null>(null);
  let previewRuntime: { adminKey: string; participantId: string } | null = null;
  let participantLoadVersion = 0;

  const authUserId = computed(() => authStorageScope.value !== 'guest' ? authStorageScope.value : null);
  const assignedActivities = computed(() => getParticipantActivities(participant.value));
  const hasActivityAssignments = computed(() => participant.value?.metadata?.activity_assignments !== undefined);
  const currentAssignedActivity = computed(() => currentParticipantActivity(assignedActivities.value, progressByEvent.value));

  const assignedConditionCodes = computed(() => {
    if (hasActivityAssignments.value) return assignedActivities.value.map((item) => item.condition_code);
    return participant.value?.condition_list?.length
      ? participant.value.condition_list
      : [];
  });

  const currentAssignedConditionCode = computed(() => {
    if (hasActivityAssignments.value) return currentAssignedActivity.value?.condition_code || null;
    const assigned = assignedConditionCodes.value;
    if (!assigned.length) return null;

    const completedCodes = new Set<string>();
    const activeProgress: Array<{ code: string; updatedAt: string }> = [];
    for (const eventProgress of Object.values(progressByEvent.value)) {
      for (const [conditionKey, progress] of Object.entries(eventProgress)) {
        if (!progress) continue;
        const code = experimentConditionCodeByKey[conditionKey as ConditionKey];
        if (!code || !assigned.includes(code)) continue;
        if (progress.status === 'completed' && progress.posttestStage === 'completed') {
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
    participantLoadVersion += 1;
    previewRuntime = null;
    previewTestUserId.value = null;
    progressByEvent.value = {};
    participant.value = null;
    participantError.value = null;
    isParticipantLoading.value = false;
    initializeError.value = null;
  };

  const loadAdminParticipantPreview = async (adminKey: string, participantId: string) => {
    const version = ++participantLoadVersion;
    previewRuntime = { adminKey, participantId };
    participant.value = null;
    previewTestUserId.value = null;
    progressByEvent.value = {};
    participantError.value = null;
    isParticipantLoading.value = true;
    try {
      const response = await fetchAdminParticipantPreview(adminKey, participantId);
      if (version !== participantLoadVersion) return null;
      participant.value = response.participant;
      previewTestUserId.value = response.test_user_id;
      progressByEvent.value = progressItemsToLocalMap(response.progress || []);
      return response.participant;
    } catch (e: any) {
      if (version === participantLoadVersion) {
        participantError.value = e.data?.detail || e.data?.message || '無法載入受測者測試設定，請重新整理。';
      }
      return null;
    } finally {
      if (version === participantLoadVersion) isParticipantLoading.value = false;
    }
  };

  const loadProgressFromApi = async () => {
    if (previewRuntime) {
      await loadAdminParticipantPreview(previewRuntime.adminKey, previewRuntime.participantId);
      return;
    }
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
    const version = ++participantLoadVersion;
    previewRuntime = null;
    previewTestUserId.value = null;
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
      if (version !== participantLoadVersion) return null;
      participant.value = response.participant;
      progressByEvent.value = progressItemsToLocalMap(response.progress || []);
      saveLocalProgress();
      return response.participant;
    } catch (e: any) {
      if (version !== participantLoadVersion) return null;
      participant.value = null;
      progressByEvent.value = {};
      participantError.value = e.data?.detail || e.data?.message || '找不到此登入帳號對應的受測者。';
      return null;
    } finally {
      if (version === participantLoadVersion) isParticipantLoading.value = false;
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
    // Preview progress belongs to the API's isolated test identity, never the signed-in account.
    if (previewRuntime) return;
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
    if ((!options.adminKey || options.previewParticipantId) && hasActivityAssignments.value) {
      const current = currentAssignedActivity.value;
      if (!current || current.event_id !== event.id
        || current.condition_code !== experimentConditionCodeByKey[condition.condition_key]) {
        initializeError.value = '請依分派順序，進行指定歷史事件與模式的活動。';
        return;
      }
    }
    const eventProgress = progressByEvent.value[event.id] || {};
    const eventAlreadyCompleted = Object.values(eventProgress).some(
      (item) => item?.status === 'completed' && item.posttestStage === 'completed',
    );
    if ((!options.adminKey || options.previewParticipantId) && eventAlreadyCompleted) {
      initializeError.value = '此歷史事件已完成，無法再次進行。若需重做，請由管理員封存舊 session 並重建。';
      return;
    }
    const progress = options.reuseProgress === false
      ? null
      : progressForEvent(event.id, condition.condition_key);
    if (options.previewParticipantId && (
      participant.value?.id !== options.previewParticipantId
      || participant.value.status !== 'active'
      || currentAssignedConditionCode.value !== experimentConditionCodeByKey[condition.condition_key]
    )) {
      initializeError.value = '請依目前受測者的分派順序開始活動。';
      return;
    }
    const requestUserId = options.previewParticipantId
      ? previewTestUserId.value
      : options.userId || authUserId.value;
    if (!requestUserId) {
      initializeError.value = '請先登入受測者帳號。';
      return;
    }
    if (progress?.sessionId && progress.posttestStage && progress.posttestStage !== 'not_started') {
      await navigateTo(`/posttest/${progress.sessionId}`);
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
      reloadProgress: Boolean(options.previewParticipantId) || !options.userId,
      adminKey: options.adminKey,
      previewParticipantId: options.previewParticipantId,
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
      previewParticipantId?: string;
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
        previewParticipantId: runtime.previewParticipantId,
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
    loadAdminParticipantPreview,
    previewTestUserId,
    participant,
    participantError,
    authUserId,
    assignedConditionCodes,
    assignedActivities,
    currentAssignedActivity,
    currentAssignedConditionCode,
    progressByEvent,
    resetForAuthScope,
    startCondition,
  };
};
