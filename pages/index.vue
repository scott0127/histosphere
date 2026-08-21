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
        :can-create-event="canManageEvents"
        :show-event-introduction="showEventIntroduction"
        @create="handleCreateEvent"
        @open="openEventDetail"
      />
    </main>

    <EventDetailModal
      v-if="detailEvent"
      :event="detailEvent"
      :conditions="visibleConditions"
      :progress-by-condition="detailConditionProgress"
      :activity-mode="activityMode"
      :admin-access="isAdminMode"
      :participant="participant"
      :participant-error="participantError"
      :participant-loading="isParticipantLoading"
      :assigned-condition-codes="assignedConditionCodes"
      @close="closeEventDetail"
      @archive="handleArchiveEvent"
      @start-condition="startCondition"
    />

    <ArchiveConfirmationModal
      :show="showArchiveConfirmDialog"
      @confirm="confirmArchive"
      @cancel="showArchiveConfirmDialog = false"
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
import ArchiveConfirmationModal from '~/components/modals/ArchiveConfirmationModal.vue';
import ConfirmActionModal from '~/components/modals/ConfirmActionModal.vue';
import { studentActivityTitle, studentConditionCode } from '~/composables/useStudentTask';
import type { EventWithPersonas, ExperimentCondition } from '~/types';
import { adminTestUserUuid, shouldExitAdminModeForAuthTransition } from '~/utils/adminMode';
import { shouldShowEventIntroduction } from '~/utils/eventVisibility';
import {
  clearAdminSessionKey,
  getAdminSessionKey,
  setAdminSessionKey,
} from '~/utils/adminSession';
import { fetchAdminSnapshot } from '~/utils/histosphereApi';

definePageMeta({
  layout: false,
  name: 'event-library',
});

const eventName = ref('');
const showArchiveConfirmDialog = ref(false);
const showStartConfirmDialog = ref(false);
const pendingArchiveEventId = ref<string | null>(null);
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
  archiveEvent,
  events,
  fetchEvents,
  findEvent,
  isRefreshing,
  loadEventLibrary,
  loadingEvents,
  refreshEvents,
} = useEventLibrary();
const authStorageScope = computed(() => user.value?.id || 'guest');
const adminTestUserId = computed(() => adminTestUserUuid(`admin-test:${user.value?.id || 'local'}`));
const canManageEvents = computed(() => isAdminMode.value && activityMode.value === 'admin');
const showEventIntroduction = computed(() => shouldShowEventIntroduction(activityMode.value));

const storedAdminKey = () => {
  return getAdminSessionKey();
};
const {
  initializeError,
  initializeEvent,
  isInitializing,
  isParticipantLoading,
  loadParticipantForAuthUser,
  participant,
  participantError,
  assignedConditionCodes,
  currentAssignedConditionCode,
  progressByEvent,
  resetForAuthScope,
  startCondition: startExperimentCondition,
} = useExperimentSession(authStorageScope);

// 詳情彈窗只需要目前事件的 condition 進度，避免元件知道整包 localStorage 結構。
const detailConditionProgress = computed(() => {
  if (!detailEvent.value) return {};
  return progressByEvent.value[detailEvent.value.id] || {};
});

const visibleConditions = computed(() => {
  if (isAdminMode.value) return conditions.value;
  const currentCode = currentAssignedConditionCode.value;
  if (!currentCode) return [];
  return conditions.value.filter((condition) => {
    const code = studentConditionCode(condition);
    return code === currentCode;
  });
});

const pendingStartProgress = computed(() => {
  if (!pendingStartCondition.value) return null;
  if (isAdminMode.value) return null;
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
  await loadEventLibrary();
  if (user.value?.id && !isAdminMode.value) {
    await loadParticipantForAuthUser(user.value.id);
  }
});

watch(authStorageScope, async (nextScope, previousScope) => {
  if (shouldExitAdminModeForAuthTransition(previousScope, nextScope)) {
    await handleExitAdminMode(false);
  }
  detailEvent.value = null;
  await resetForAuthScope();
  if (user.value?.id && !isAdminMode.value) {
    await loadParticipantForAuthUser(user.value.id);
  }
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
    setAdminSessionKey(trimmedKey);
    enterAdminMode();
    await navigateTo('/admin');
  } catch (e: any) {
    exitAdminMode();
    clearAdminSessionKey();
    adminModeError.value = e.data?.detail || 'Admin key 無效，無法進入管理員檢視。';
  } finally {
    adminModePending.value = false;
  }
};

const handleExitAdminMode = async (reloadParticipant = true) => {
  exitAdminMode();
  adminModeError.value = null;
  if (reloadParticipant && user.value?.id) {
    await resetForAuthScope();
    await loadParticipantForAuthUser(user.value.id);
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
  if (!canManageEvents.value) return;
  const trimmed = eventName.value.trim();
  if (!trimmed) return;
  const response = await initializeEvent(trimmed, 'ebl_roleplay', false, false, {
    adminKey: storedAdminKey(),
    userId: adminTestUserId.value,
  });
  if (response) {
    await fetchEvents();
    detailEvent.value = findEvent(response.event_id);
    eventName.value = '';
  }
};

// 啟動指定 condition；若本機已有對話紀錄，直接回到該 conversation。
const startCondition = async (condition: ExperimentCondition) => {
  if (!detailEvent.value) return;
  if (!isAdminMode.value && !participant.value) {
    alert(participantError.value || '請先登入已設定的受測者帳號。');
    await navigateTo('/auth/login');
    return;
  }
  if (
    !isAdminMode.value
    && Object.values(detailConditionProgress.value).some((progress) => progress?.status === 'completed')
  ) {
    alert('此歷史事件已完成，無法再次進行。');
    return;
  }
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
  await startExperimentCondition(
    detailEvent.value,
    condition,
    isAdminMode.value
      ? {
          userId: adminTestUserId.value,
          reuseProgress: false,
          adminKey: storedAdminKey(),
        }
      : undefined,
  );
};

// 開啟事件詳情，讓主頁維持單純的輸入與列表。
const openEventDetail = (event: EventWithPersonas) => {
  detailEvent.value = event;
};

// 關閉事件詳情彈窗。
const closeEventDetail = () => {
  detailEvent.value = null;
};

// 開啟封存確認；只有 Admin mode 會顯示入口。
const handleArchiveEvent = (eventId: string) => {
  if (!canManageEvents.value) return;
  pendingArchiveEventId.value = eventId;
  showArchiveConfirmDialog.value = true;
};

// 封存只隱藏素材，不會刪除任何研究資料。
const confirmArchive = async () => {
  if (!pendingArchiveEventId.value) return;
  try {
    await archiveEvent(storedAdminKey(), pendingArchiveEventId.value);
    if (detailEvent.value?.id === pendingArchiveEventId.value) detailEvent.value = null;
  } catch (e) {
    console.error('Failed to archive event:', e);
    alert('封存失敗，請稍後再試');
  } finally {
    showArchiveConfirmDialog.value = false;
    pendingArchiveEventId.value = null;
  }
};
</script>
