<template>
  <!--
    首頁是目前前端的「事件素材庫」入口：
    1. 左側建立或重用歷史事件素材。
    2. 右側列出同一批可被四種實驗活動共用的事件、task、persona。
    3. 點事件卡後才選活動條件，避免把 condition 當成不同素材來源。
  -->
  <div class="historical-home relative min-h-screen overflow-x-hidden bg-[var(--admin-page)] text-[var(--admin-text)]">
    <!-- 背景保留舊 prototype 的歷史地圖質感，但降透明度，避免干擾可讀性。 -->
    <div class="pointer-events-none fixed inset-0 z-0">
      <img src="~/assets/images/landing-bg.png" alt="" class="h-full w-full object-cover opacity-[0.35]" />
      <div class="absolute inset-0 bg-[rgba(242,240,236,0.8)]"></div>
      <div class="absolute inset-0 bg-[radial-gradient(circle_at_26%_42%,rgba(168,141,123,0.18),transparent_45%),linear-gradient(90deg,rgba(47,41,36,0.03),transparent_48%,rgba(47,41,36,0.05))]"></div>
    </div>

    <EventLibraryHeader
      :is-refreshing="isRefreshing"
      :is-authenticated="isAuthenticated"
      :is-admin-mode="isAdminMode"
      :admin-view-mode="adminViewMode"
      :display-name="displayName"
      :admin-mode-pending="adminModePending"
      :admin-mode-error="adminModeError"
      @refresh="refreshEvents"
      @enter-admin-mode="verifyAndEnterAdminMode"
      @exit-admin-mode="handleExitAdminMode"
      @update:admin-view-mode="setAdminViewMode"
    />

    <main class="relative z-10 mx-auto grid min-h-[calc(100vh-68px)] w-full max-w-[1480px] gap-10 px-6 py-10 lg:h-[calc(100vh-68px)] lg:grid-cols-[430px_minmax(0,1fr)] lg:items-stretch xl:gap-14">
      <EventCreatePanel
      />

      <EventLibraryList
        v-model:event-name="eventName"
        :events="events"
        :loading-events="loadingEvents"
        :creating-event="isLoading"
        :create-error="error"
        @create="handleCreateEvent"
        @open="openEventDetail"
      />
    </main>

    <EventDetailModal
      v-if="detailEvent"
      v-model:participant-id="participantId"
      :event="detailEvent"
      :conditions="conditions"
      :progress-by-condition="detailConditionProgress"
      :activity-mode="activityMode"
      @close="closeEventDetail"
      @delete="handleDeleteEvent"
      @participant-change="saveParticipant"
      @start-condition="startCondition"
    />

    <DeleteConfirmationModal
      :show="showDeleteConfirmDialog"
      @confirm="confirmDelete"
      @cancel="showDeleteConfirmDialog = false"
    />
  </div>
</template>

<script setup lang="ts">
// 首頁負責事件素材入口：建立/選擇歷史事件，並在詳情彈窗中啟動 2x2 實驗 condition。
// 設計原則：
// - historical event 是素材單位，source、task、primary persona 應由四種 condition 共用。
// - experiment condition 是活動策略，不應造成事件素材被複製成四份。
// - 目前受測者進度先存在 localStorage，未來可改接 experiment_sessions/research_logs API。
import { computed, onMounted, ref, watch } from 'vue';
import EventCreatePanel from '~/components/event-library/EventCreatePanel.vue';
import EventDetailModal from '~/components/event-library/EventDetailModal.vue';
import EventLibraryHeader from '~/components/event-library/EventLibraryHeader.vue';
import EventLibraryList from '~/components/event-library/EventLibraryList.vue';
import DeleteConfirmationModal from '~/components/modals/DeleteConfirmationModal.vue';
import type { ConditionKey, EventInitializeResponse, EventWithPersonas, ExperimentCondition, UserProgressItem, UserProgressResponse, UserProgressStatus } from '~/types';

definePageMeta({
  layout: false,
  name: 'event-library',
});

type LocalConditionProgress = {
  status: 'not_started' | UserProgressStatus;
  sessionId?: string;
  taskId?: string;
  attemptId?: string;
  conversationId?: string;
  updatedAt: string;
};

const eventName = ref('');
const isLoading = ref(false);
const error = ref<string | null>(null);
const showDeleteConfirmDialog = ref(false);
const pendingDeleteEventId = ref<string | null>(null);
const events = ref<EventWithPersonas[]>([]);
const conditions = ref<ExperimentCondition[]>([]);
const detailEvent = ref<EventWithPersonas | null>(null);
const loadingEvents = ref(false);
const isRefreshing = ref(false);
const adminModePending = ref(false);
const adminModeError = ref<string | null>(null);
const participantId = ref('scott-test');
const localProgress = ref<Record<string, Partial<Record<ConditionKey, LocalConditionProgress>>>>({});
const { displayName, initialize: initializeAuth, isAuthenticated, user } = useAuth();
const {
  activityMode,
  adminViewMode,
  enterAdminMode,
  exitAdminMode,
  initAdminMode,
  isAdminMode,
  setAdminViewMode,
} = useAdminMode();

// 詳情彈窗只需要目前事件的 condition 進度，避免元件知道整包 localStorage 結構。
const detailConditionProgress = computed(() => {
  if (!detailEvent.value) return {};
  return localProgress.value[detailEvent.value.id] || {};
});
const authStorageScope = computed(() => user.value?.id || 'guest');

// 保留未來 avatar 顯示規則；目前首頁 UI 暫時不使用 persona 頭像。
onMounted(async () => {
  initAdminMode();
  await initializeAuth();
  participantId.value = loadParticipantId();
  await Promise.all([fetchConditions(), fetchEvents(), loadProgressFromApi()]);
});

watch(authStorageScope, () => {
  handleExitAdminMode();
  detailEvent.value = null;
  localProgress.value = {};
  participantId.value = loadParticipantId();
  loadProgressFromApi();
});

watch(isAuthenticated, (authenticated) => {
  if (!authenticated) {
    handleExitAdminMode();
  }
});

const verifyAndEnterAdminMode = async (adminKey: string) => {
  const trimmedKey = adminKey.trim();
  if (!trimmedKey) {
    adminModeError.value = '請輸入 admin key。';
    return;
  }

  adminModePending.value = true;
  adminModeError.value = null;
  try {
    await $fetch('/api/admin/snapshot', {
      headers: {
        'x-admin-key': trimmedKey,
      },
    });
    localStorage.setItem('histosphere_admin_key', trimmedKey);
    enterAdminMode();
    await navigateTo('/admin');
  } catch (e: any) {
    exitAdminMode();
    localStorage.removeItem('histosphere_admin_key');
    adminModeError.value = e.data?.detail || 'Admin key 無效，無法進入管理員檢視。';
  } finally {
    adminModePending.value = false;
  }
};

const handleExitAdminMode = () => {
  exitAdminMode();
  adminModeError.value = null;
  if (import.meta.client) {
    localStorage.removeItem('histosphere_admin_key');
  }
};

// 讀取 2x2 實驗條件，讓前端不把 condition 寫死。
const fetchConditions = async () => {
  try {
    conditions.value = await $fetch<ExperimentCondition[]>('/api/conditions');
  } catch (e) {
    console.error('Failed to fetch conditions:', e);
  }
};

// 讀取事件列表；若詳情彈窗已開啟，重新對齊最新事件資料。
const fetchEvents = async () => {
  loadingEvents.value = true;
  try {
    events.value = await $fetch<EventWithPersonas[]>('/api/events');
    if (detailEvent.value) {
      detailEvent.value = events.value.find((event) => event.id === detailEvent.value?.id) || null;
    }
  } catch (e) {
    console.error('Failed to fetch events:', e);
  } finally {
    loadingEvents.value = false;
  }
};

// 手動重新整理事件素材列表。
const refreshEvents = async () => {
  isRefreshing.value = true;
  await fetchEvents();
  isRefreshing.value = false;
};

// 建立或重用歷史事件素材；首頁建立時不直接跳 task。
const handleCreateEvent = async () => {
  const trimmed = eventName.value.trim();
  if (!trimmed) return;
  const response = await initializeEvent(trimmed, 'ebl_roleplay', false, false);
  if (response) {
    await fetchEvents();
    detailEvent.value = events.value.find((event) => event.id === response.event_id) || null;
    eventName.value = '';
  }
};

// 啟動指定 condition；若本機已有對話紀錄，直接回到該 conversation。
const startCondition = async (condition: ExperimentCondition) => {
  if (!detailEvent.value) return;
  const progress = progressFor(condition.condition_key);
  if (progress?.conversationId) {
    await navigateTo({
      path: `/conversations/${progress.conversationId}`,
    });
    return;
  }
  if (progress?.sessionId && progress.taskId) {
    await navigateTo({
      path: '/task',
      query: {
        taskId: progress.taskId,
        sessionId: progress.sessionId,
        participantId: participantId.value,
        eventId: detailEvent.value.id,
        conditionKey: condition.condition_key,
      },
    });
    return;
  }
  await initializeEvent(detailEvent.value.canonical_name, condition.condition_key, false, true);
};

// 呼叫後端初始化流程；同一事件會重用同一組素材，condition 只建立 session。
const initializeEvent = async (
  name: string,
  conditionKey: ConditionKey,
  rebuild: boolean,
  navigateToTask: boolean,
) => {
  isLoading.value = true;
  error.value = null;
  try {
    const response = await $fetch<EventInitializeResponse>('/api/event/initialize', {
      method: 'POST',
      body: {
        event_name: name,
        condition_key: conditionKey,
        rebuild,
        user_id: participantUuid(participantId.value),
      },
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
        path: '/task',
        query: {
          taskId: response.task.id,
          sessionId: response.session_id,
          participantId: participantId.value,
          eventId: response.event_id,
          conditionKey,
        },
      });
    }
    return response;
  } catch (e: any) {
    error.value = e.data?.detail || e.data?.message || '建立流程失敗，請稍後再試。';
    return null;
  } finally {
    isLoading.value = false;
  }
};

// 開啟事件詳情，讓主頁維持單純的輸入與列表。
const openEventDetail = (event: EventWithPersonas) => {
  detailEvent.value = event;
};

// 關閉事件詳情彈窗。
const closeEventDetail = () => {
  detailEvent.value = null;
};

// 儲存目前測試用受測者代號；後端仍使用 deterministic UUID。
const saveParticipant = () => {
  const next = participantId.value.trim() || defaultParticipantId();
  participantId.value = next;
  localStorage.setItem(participantStorageKey(), next);
  loadProgressFromApi();
};

const defaultParticipantId = () => {
  const emailPrefix = user.value?.email?.split('@')[0]?.trim();
  return emailPrefix || 'scott-test';
};

const participantStorageKey = () => `histosphere-participant-id:${authStorageScope.value}`;

const loadParticipantId = () => {
  if (!import.meta.client) return defaultParticipantId();
  return localStorage.getItem(participantStorageKey()) || defaultParticipantId();
};

// 將受測者代號轉成穩定 UUID，避免 Supabase uuid 欄位收到任意字串。
const participantUuid = (value: string) => {
  let hash = 2166136261;
  for (const char of value || 'scott-test') {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  const hex = Math.abs(hash).toString(16).padStart(8, '0');
  return `${hex}${hex}${hex}${hex}`.replace(
    /^(.{8})(.{4})(.{4})(.{4})(.{12}).*$/,
    '$1-$2-$3-$4-$5',
  );
};

const progressStorageKey = () => `histosphere-progress:${authStorageScope.value}:${participantId.value || defaultParticipantId()}`;

// 優先從後端讀取目前受測者的 condition 進度；localStorage 僅作為開發 fallback。
const loadProgressFromApi = async () => {
  const userId = participantUuid(participantId.value);
  try {
    const response = await $fetch<UserProgressResponse>('/api/sessions/progress', {
      query: { user_id: userId },
    });
    localProgress.value = progressItemsToLocalMap(response.progress || []);
    saveLocalProgress();
  } catch (e) {
    console.warn('Failed to load session progress, using local fallback:', e);
    loadLocalProgress();
  }
};

const progressItemsToLocalMap = (items: UserProgressItem[]) => {
  const next: Record<string, Partial<Record<ConditionKey, LocalConditionProgress>>> = {};
  for (const item of items) {
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

// 從 localStorage 讀取目前受測者的 condition 完成狀態，僅供 API 暫時失敗時 fallback。
const loadLocalProgress = () => {
  if (!import.meta.client) return;
  try {
    localProgress.value = JSON.parse(localStorage.getItem(progressStorageKey()) || '{}');
  } catch {
    localProgress.value = {};
  }
};

// 寫回本機進度；第一版先供開發測試，後續可改接 research/session API。
const saveLocalProgress = () => {
  if (!import.meta.client) return;
  localStorage.setItem(progressStorageKey(), JSON.stringify(localProgress.value));
};

// 更新某事件某 condition 的本機進度。
const markProgress = (eventId: string, conditionKey: ConditionKey, progress: LocalConditionProgress) => {
  localProgress.value = {
    ...localProgress.value,
    [eventId]: {
      ...(localProgress.value[eventId] || {}),
      [conditionKey]: progress,
    },
  };
  saveLocalProgress();
};

// 取得目前詳情事件在某 condition 的本機進度。
const progressFor = (conditionKey: ConditionKey) => {
  if (!detailEvent.value) return null;
  return localProgress.value[detailEvent.value.id]?.[conditionKey] || null;
};

// 開啟刪除確認。
const handleDeleteEvent = (eventId: string) => {
  pendingDeleteEventId.value = eventId;
  showDeleteConfirmDialog.value = true;
};

// 確認刪除事件素材。
const confirmDelete = async () => {
  if (!pendingDeleteEventId.value) return;
  try {
    await $fetch(`/api/event/${pendingDeleteEventId.value}`, { method: 'DELETE' });
    if (detailEvent.value?.id === pendingDeleteEventId.value) detailEvent.value = null;
    await fetchEvents();
  } catch (e) {
    console.error('Failed to delete event:', e);
    alert('刪除失敗，請稍後再試');
  } finally {
    showDeleteConfirmDialog.value = false;
    pendingDeleteEventId.value = null;
  }
};
</script>

<style scoped>
.historical-home {
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.historical-home :deep(.font-serif),
.historical-home .font-serif {
  font-family: Georgia, "Times New Roman", "Noto Serif TC", serif;
}
</style>
