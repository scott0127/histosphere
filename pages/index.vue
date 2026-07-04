<template>
  <!--
    首頁是目前前端的「事件素材庫」入口：
    1. 左側建立或重用歷史事件素材。
    2. 右側列出同一批可被四種實驗活動共用的事件、task、persona。
    3. 點事件卡後才選活動條件，避免把 condition 當成不同素材來源。
  -->
  <div class="historical-home relative min-h-screen overflow-x-hidden bg-[var(--admin-page)] font-[ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe_UI',sans-serif] text-[var(--admin-text)] [&_.font-serif]:font-[Georgia,'Times_New_Roman','Noto_Serif_TC',serif]">
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
      @refresh="refreshEventLibrary"
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
        :creating-event="isInitializing"
        :create-error="initializeError"
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

    <ConfirmActionModal
      :show="showStartConfirmDialog"
      :title="startConfirmTitle"
      :message="startConfirmMessage"
      eyebrow="活動確認"
      icon="mdi:play-circle-outline"
      confirm-label="是"
      cancel-label="否"
      @confirm="confirmStartCondition"
      @cancel="cancelStartCondition"
    />
  </div>
</template>

<script setup lang="ts">
// 首頁負責事件素材入口：建立/選擇歷史事件，並在詳情彈窗中啟動 2x2 實驗 condition。
// 設計原則：
// - historical event 是素材單位，source、task、primary persona 應由四種 condition 共用。
// - experiment condition 是活動策略，不應造成事件素材被複製成四份。
import { computed, onMounted, ref, watch } from 'vue';
import EventCreatePanel from '~/components/event-library/EventCreatePanel.vue';
import EventDetailModal from '~/components/event-library/EventDetailModal.vue';
import EventLibraryHeader from '~/components/event-library/EventLibraryHeader.vue';
import EventLibraryList from '~/components/event-library/EventLibraryList.vue';
import ConfirmActionModal from '~/components/modals/ConfirmActionModal.vue';
import DeleteConfirmationModal from '~/components/modals/DeleteConfirmationModal.vue';
import { studentActivityTitle } from '~/composables/useStudentTask';
import type { EventWithPersonas, ExperimentCondition } from '~/types';
import { fetchAdminSnapshot } from '~/utils/histosphereApi';

definePageMeta({
  layout: false,
  name: 'event-library',
});

const eventName = ref('');
const showDeleteConfirmDialog = ref(false);
const showStartConfirmDialog = ref(false);
const pendingDeleteEventId = ref<string | null>(null);
const pendingStartCondition = ref<ExperimentCondition | null>(null);
const detailEvent = ref<EventWithPersonas | null>(null);
const adminModePending = ref(false);
const adminModeError = ref<string | null>(null);
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
const {
  conditions,
  deleteEvent,
  events,
  fetchEvents,
  findEvent,
  isRefreshing,
  loadEventLibrary,
  loadingEvents,
  refreshEvents,
} = useEventLibrary();
const authStorageScope = computed(() => user.value?.id || 'guest');
const defaultParticipantId = computed(() => {
  const emailPrefix = user.value?.email?.split('@')[0]?.trim();
  return emailPrefix || 'scott-test';
});
const {
  initializeError,
  initializeEvent,
  initializeParticipant,
  isInitializing,
  loadProgressFromApi,
  participantId,
  progressByEvent,
  resetForAuthScope,
  saveParticipant,
  startCondition: startExperimentCondition,
} = useExperimentSession(authStorageScope, defaultParticipantId);

// 詳情彈窗只需要目前事件的 condition 進度，避免元件知道整包 localStorage 結構。
const detailConditionProgress = computed(() => {
  if (!detailEvent.value) return {};
  return progressByEvent.value[detailEvent.value.id] || {};
});

const pendingStartProgress = computed(() => {
  if (!pendingStartCondition.value) return null;
  return detailConditionProgress.value[pendingStartCondition.value.condition_key] || null;
});

const pendingStartLabel = computed(() => {
  return pendingStartCondition.value ? studentActivityTitle(pendingStartCondition.value) : '活動';
});

const startConfirmTitle = computed(() => {
  return pendingStartLabel.value;
});

const startConfirmMessage = computed(() => {
  if (pendingStartProgress.value?.conversationId) {
    return '點選「是」繼續上一階段 [CHAT]';
  }
  if (pendingStartProgress.value?.sessionId) {
    return '點選「是」回到上一階段 [TASK]';
  }
  return '點選「是」進入下一階段 [TASK]';
});

// 保留未來 avatar 顯示規則；目前首頁 UI 暫時不使用 persona 頭像。
onMounted(async () => {
  initAdminMode();
  await initializeAuth();
  initializeParticipant();
  await Promise.all([loadEventLibrary(), loadProgressFromApi()]);
});

watch(authStorageScope, async () => {
  handleExitAdminMode();
  detailEvent.value = null;
  await resetForAuthScope();
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
    await fetchAdminSnapshot(trimmedKey);
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

// 手動重新整理事件素材列表；若詳情彈窗已開啟，對齊最新事件資料。
const refreshEventLibrary = async () => {
  await refreshEvents();
  if (detailEvent.value) {
    detailEvent.value = findEvent(detailEvent.value.id);
  }
};

// 建立或重用歷史事件素材；首頁建立時不直接跳 task。
const handleCreateEvent = async () => {
  const trimmed = eventName.value.trim();
  if (!trimmed) return;
  const response = await initializeEvent(trimmed, 'ebl_roleplay', false, false);
  if (response) {
    await fetchEvents();
    detailEvent.value = findEvent(response.event_id);
    eventName.value = '';
  }
};

// 啟動指定 condition；若本機已有對話紀錄，直接回到該 conversation。
const startCondition = async (condition: ExperimentCondition) => {
  if (!detailEvent.value) return;
  await saveParticipant();
  pendingStartCondition.value = condition;
  showStartConfirmDialog.value = true;
};

const cancelStartCondition = () => {
  showStartConfirmDialog.value = false;
  pendingStartCondition.value = null;
};

const confirmStartCondition = async () => {
  if (!detailEvent.value || !pendingStartCondition.value) return;
  const condition = pendingStartCondition.value;
  showStartConfirmDialog.value = false;
  pendingStartCondition.value = null;
  await startExperimentCondition(detailEvent.value, condition);
};

// 開啟事件詳情，讓主頁維持單純的輸入與列表。
const openEventDetail = (event: EventWithPersonas) => {
  detailEvent.value = event;
};

// 關閉事件詳情彈窗。
const closeEventDetail = () => {
  detailEvent.value = null;
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
    await deleteEvent(pendingDeleteEventId.value);
    if (detailEvent.value?.id === pendingDeleteEventId.value) detailEvent.value = null;
  } catch (e) {
    console.error('Failed to delete event:', e);
    alert('刪除失敗，請稍後再試');
  } finally {
    showDeleteConfirmDialog.value = false;
    pendingDeleteEventId.value = null;
  }
};
</script>
