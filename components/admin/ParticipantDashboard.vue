<template>
  <section class="space-y-3">
    <div class="grid gap-3">
      <article
        v-for="row in rows"
        :key="row.participant.id"
        class="admin-panel-inner p-4"
      >
        <div class="grid gap-4 lg:grid-cols-[160px_minmax(0,1fr)_minmax(300px,420px)] lg:items-center">
          <div>
            <p class="admin-kicker">受測者</p>
            <h3 class="admin-heading mt-1 font-serif text-2xl font-bold">{{ row.participant.code }}</h3>
          </div>

          <div class="space-y-3">
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                class="inline-flex min-h-10 items-center gap-2 rounded-[8px] border px-3 text-sm font-black transition"
                :class="row.isBound ? 'border-[var(--admin-border)] bg-[var(--admin-surface-muted)] text-[var(--admin-text)]' : 'border-[var(--admin-line)] bg-[var(--admin-coffee)] text-white'"
                @click="openEditor(row)"
              >
                <Icon :name="row.isBound ? 'mdi:link-variant' : 'mdi:link-variant-plus'" class="h-4 w-4" />
                {{ row.isBound ? '已綁定' : '未綁定，選擇帳號' }}
              </button>
              <span v-if="row.authUser?.email" class="admin-caption text-xs font-bold">
                {{ row.authUser.email }}
              </span>
              <span v-else-if="row.participant.auth_user_id" class="admin-caption text-xs font-bold">
                {{ shortId(row.participant.auth_user_id) }}
              </span>
            </div>

            <div class="flex flex-wrap gap-2">
              <span
                v-for="condition in row.assignedConditions"
                :key="condition.code"
                class="inline-flex min-h-9 items-center rounded-full border border-[var(--admin-border)] bg-[var(--admin-surface-muted)] px-3 text-xs font-black text-[var(--admin-coffee)]"
              >
                {{ condition.code }} {{ condition.label }}
              </span>
              <button
                v-if="!row.assignedConditions.length"
                type="button"
                class="inline-flex min-h-9 items-center rounded-full border border-[var(--admin-line)] bg-[var(--admin-surface)] px-3 text-xs font-black text-[var(--admin-copy)]"
                @click="openEditor(row)"
              >
                尚未分派模式
              </button>
            </div>
          </div>

          <div>
            <div class="grid grid-cols-4 overflow-hidden rounded-[10px] border border-[var(--admin-border)] bg-[var(--admin-surface)]">
              <span
                v-for="stage in stages"
                :key="stage"
                class="inline-flex min-h-11 items-center justify-center border-r border-[var(--admin-border)] px-2 text-center text-xs font-black last:border-r-0"
                :class="row.currentStage === stage ? 'bg-[var(--admin-coffee)] text-white' : 'bg-[var(--admin-surface-muted)] text-[var(--admin-copy)]'"
              >
                {{ participantStageLabels[stage] }}
              </span>
            </div>
            <p class="admin-caption mt-2 text-right text-xs font-bold">
              {{ row.updatedAt ? `最後活動 ${formatDate(row.updatedAt)}` : '尚無活動紀錄' }}
            </p>
            <div
              v-if="row.latestActiveSession"
              class="mt-3 flex min-h-10 items-center justify-end gap-2 border-t border-[var(--admin-border-soft)] pt-3"
            >
              <template v-if="row.latestActiveSession.timer_ends_at">
                <span class="admin-caption text-xs font-bold">
                  計時至 {{ formatDate(row.latestActiveSession.timer_ends_at) }}
                </span>
                <button
                  type="button"
                  class="admin-button-secondary min-h-9 px-3 text-xs font-bold"
                  :disabled="updatingTimerSessionId === row.latestActiveSession.id"
                  @click="$emit('cancel-timer', row.latestActiveSession.id)"
                >
                  停止計時
                </button>
              </template>
              <template v-else>
                <input
                  :value="timerMinutes[row.participant.id] || 30"
                  type="number"
                  min="1"
                  max="240"
                  class="admin-field h-9 w-20 px-2 text-center text-xs font-bold"
                  title="計時分鐘數"
                  @input="setTimerMinutes(row.participant.id, $event)"
                />
                <button
                  type="button"
                  class="admin-button-primary min-h-9 px-3 text-xs font-bold"
                  :disabled="updatingTimerSessionId === row.latestActiveSession.id"
                  @click="$emit('start-timer', row.latestActiveSession.id, timerMinutes[row.participant.id] || 30)"
                >
                  啟動計時
                </button>
              </template>
            </div>
          </div>
        </div>

        <div
          v-if="row.currentSessions.length"
          class="mt-4 border-t border-[var(--admin-border-soft)] pt-4"
        >
          <div class="mb-2 flex items-center justify-between gap-3">
            <p class="admin-kicker">有效 Session</p>
            <span class="admin-caption text-xs font-bold">{{ row.currentSessions.length }} 筆</span>
          </div>
          <div class="divide-y divide-[var(--admin-border-soft)]">
            <div
              v-for="item in row.currentSessions"
              :key="item.session.id"
              class="grid min-h-12 gap-2 py-2 lg:grid-cols-[minmax(220px,1fr)_minmax(220px,1fr)_100px_130px] lg:items-center"
            >
              <span class="admin-copy text-sm font-black">{{ item.eventName }}</span>
              <span class="admin-caption text-xs font-bold">
                {{ item.conditionCode }} {{ item.conditionLabel }}
              </span>
              <span class="admin-caption text-xs font-bold">{{ sessionStatusLabel(item.session.status) }}</span>
              <button
                type="button"
                class="admin-button-secondary inline-flex min-h-9 items-center justify-center gap-2 px-3 text-xs font-bold"
                :disabled="restartingSessionId === item.session.id"
                @click="restartTarget = item"
              >
                <Icon
                  :name="restartingSessionId === item.session.id ? 'mdi:loading' : 'mdi:restart'"
                  class="h-4 w-4"
                  :class="{ 'animate-spin': restartingSessionId === item.session.id }"
                />
                封存並重建
              </button>
            </div>
          </div>
        </div>
      </article>
    </div>

    <div v-if="!rows.length" class="admin-empty-state p-5">
      目前沒有受測者資料。
    </div>

    <Transition
      enter-active-class="transition-opacity duration-150"
      leave-active-class="transition-opacity duration-150"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div
        v-if="editingRow"
        class="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(47,41,36,0.5)] p-4 backdrop-blur-sm"
        @click.self="closeEditor"
      >
        <article class="w-full max-w-2xl rounded-[12px] border-2 border-[var(--admin-line)] bg-[var(--admin-page)] p-5 shadow-[0_30px_90px_rgba(47,41,36,0.3)]">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="admin-kicker">Participant binding</p>
              <h3 class="admin-heading mt-1 font-serif text-2xl font-bold">{{ editingRow.participant.code }}</h3>
            </div>
            <button type="button" class="admin-button-secondary px-3 py-2 text-xs font-bold" @click="closeEditor">
              關閉
            </button>
          </div>

          <div class="mt-5 grid gap-5">
            <label class="block">
              <span class="admin-label">Auth 帳號</span>
              <select v-model="draftAuthUserId" class="admin-field mt-1 w-full px-3 py-2 text-sm font-bold">
                <option value="">不綁定</option>
                <option
                  v-for="user in selectableAuthUsers"
                  :key="user.id"
                  :value="user.id"
                  :disabled="Boolean(user.bound_participant_id && user.bound_participant_id !== editingRow.participant.id)"
                >
                  {{ user.email || shortId(user.id) }}
                  {{ user.bound_participant_code && user.bound_participant_id !== editingRow.participant.id ? `（已綁定 ${user.bound_participant_code}）` : '' }}
                </option>
              </select>
              <p v-if="!authUsers.length" class="admin-caption mt-2 text-xs font-bold">
                尚未載入 Auth users，請確認 admin key 與 Supabase Auth 狀態。
              </p>
            </label>

            <label class="block">
              <span class="admin-label">或手動輸入 Auth user id</span>
              <input
                v-model="draftAuthUserId"
                class="admin-field mt-1 w-full px-3 py-2 font-mono text-xs"
                placeholder="Supabase Auth user UUID"
              />
            </label>

            <fieldset>
              <legend class="admin-label">分派模式</legend>
              <div class="mt-2 grid gap-2 sm:grid-cols-2">
                <label
                  v-for="condition in conditionOptions"
                  :key="condition.code"
                  class="flex min-h-12 items-center gap-3 rounded-[9px] border border-[var(--admin-border)] bg-[var(--admin-surface)] px-3 text-sm font-black text-[var(--admin-text)]"
                >
                  <input
                    v-model="draftConditionCodes"
                    type="checkbox"
                    :value="condition.code"
                    class="h-4 w-4 accent-[var(--admin-coffee)]"
                  />
                  {{ condition.code }} {{ condition.label }}
                </label>
              </div>
            </fieldset>
          </div>

          <div class="mt-6 flex justify-end gap-2">
            <button type="button" class="admin-button-secondary px-4 py-2 text-sm font-bold" @click="closeEditor">
              取消
            </button>
            <button
              type="button"
              class="admin-button-primary inline-flex min-h-10 items-center gap-2 px-4 text-sm font-bold"
              :disabled="savingParticipantId === editingRow.participant.id"
              @click="saveEditor"
            >
              <Icon :name="savingParticipantId === editingRow.participant.id ? 'mdi:loading' : 'mdi:content-save-outline'" class="h-4 w-4" :class="{ 'animate-spin': savingParticipantId === editingRow.participant.id }" />
              儲存
            </button>
          </div>
        </article>
      </div>
    </Transition>

    <ConfirmActionModal
      :show="Boolean(restartTarget)"
      title="重新建立 Session"
      :message="restartConfirmationMessage"
      eyebrow="受測者流程"
      icon="mdi:restart-alert"
      confirm-label="封存並重建"
      cancel-label="取消"
      @confirm="confirmRestart"
      @cancel="restartTarget = null"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import ConfirmActionModal from '~/components/modals/ConfirmActionModal.vue';
import type { AdminAuthUserSummary } from '~/types';
import type { ParticipantUpdateInput } from '~/utils/histosphereApi';
import {
  conditionDisplayLabel,
  conditionName,
  participantConditionLabels,
  participantStageLabels,
  type ParticipantDashboardRow,
  type ParticipantSessionSummary,
  type ParticipantStage,
} from '~/utils/adminParticipantDashboard';

const props = defineProps<{
  rows: ParticipantDashboardRow[];
  authUsers: AdminAuthUserSummary[];
  savingParticipantId: string | null;
  updatingTimerSessionId: string | null;
  restartingSessionId: string | null;
}>();

const emit = defineEmits<{
  (event: 'save', participantId: string, payload: ParticipantUpdateInput): void;
  (event: 'start-timer', sessionId: string, durationMinutes: number): void;
  (event: 'cancel-timer', sessionId: string): void;
  (event: 'restart-session', sessionId: string): void;
}>();

const stages: ParticipantStage[] = ['not_started', 'task', 'chat', 'completed'];
const editingRow = ref<ParticipantDashboardRow | null>(null);
const draftAuthUserId = ref('');
const draftConditionCodes = ref<string[]>([]);
const timerMinutes = ref<Record<string, number>>({});
const restartTarget = ref<ParticipantSessionSummary | null>(null);

const restartConfirmationMessage = computed(() => {
  if (!restartTarget.value) return '';
  return `這會封存「${restartTarget.value.eventName}」的舊 session 與對話，保留所有研究資料，再建立一筆新的 ${restartTarget.value.conditionCode} session。`;
});

const conditionOptions = computed(() => {
  return Object.keys(participantConditionLabels).map((code) => ({
    code,
    label: conditionName(code),
    display: conditionDisplayLabel(code),
  }));
});

const selectableAuthUsers = computed(() => {
  const currentAuthId = editingRow.value?.participant.auth_user_id;
  return props.authUsers.filter((user) => {
    return !user.bound_participant_id
      || user.bound_participant_id === editingRow.value?.participant.id
      || user.id === currentAuthId;
  });
});

const openEditor = (row: ParticipantDashboardRow) => {
  editingRow.value = row;
  draftAuthUserId.value = row.participant.auth_user_id || '';
  draftConditionCodes.value = [...(row.participant.condition_list || [])];
};

const closeEditor = () => {
  editingRow.value = null;
  draftAuthUserId.value = '';
  draftConditionCodes.value = [];
};

const saveEditor = () => {
  if (!editingRow.value) return;
  emit('save', editingRow.value.participant.id, {
    auth_user_id: draftAuthUserId.value || null,
    condition_list: [...draftConditionCodes.value],
  });
  closeEditor();
};

const shortId = (id: string) => {
  return `${id.slice(0, 8)}...${id.slice(-4)}`;
};

const formatDate = (value: string) => {
  return new Intl.DateTimeFormat('zh-TW', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
};

const setTimerMinutes = (participantId: string, event: Event) => {
  const value = Number((event.target as HTMLInputElement).value);
  timerMinutes.value[participantId] = Math.min(240, Math.max(1, Number.isFinite(value) ? value : 30));
};

const confirmRestart = () => {
  if (!restartTarget.value) return;
  emit('restart-session', restartTarget.value.session.id);
  restartTarget.value = null;
};

const sessionStatusLabel = (status: string) => {
  if (status === 'completed') return '已完成';
  if (status === 'conversation_started') return 'Chat';
  if (status === 'task_submitted') return 'Task 已提交';
  return 'Task';
};
</script>
