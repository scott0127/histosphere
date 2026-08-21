<template>
  <section class="space-y-3">
    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--admin-border-soft)] pb-3">
      <div class="flex flex-wrap items-center gap-3">
        <span class="admin-caption text-sm font-bold">
          啟用 {{ activeCount }} 位
        </span>
        <span class="admin-caption text-sm font-bold">
          封存 {{ archivedCount }} 位
        </span>
        <label class="inline-flex min-h-10 cursor-pointer items-center gap-2 text-sm font-bold text-[var(--admin-copy)]">
          <input
            v-model="showArchived"
            type="checkbox"
            class="h-4 w-4 accent-[var(--admin-coffee)]"
          />
          顯示封存
        </label>
      </div>
      <button
        type="button"
        class="admin-button-primary inline-flex min-h-10 items-center justify-center gap-2 px-4 text-sm font-bold"
        @click="openCreateForm"
      >
        <Icon name="mdi:account-plus-outline" class="h-4 w-4" />
        新增受測者
      </button>
    </div>

    <div class="grid gap-3">
      <article
        v-for="row in visibleRows"
        :key="row.participant.id"
        class="admin-panel-inner p-4"
      >
        <div class="grid gap-4 lg:grid-cols-[160px_minmax(0,1fr)_minmax(300px,420px)] lg:items-center">
          <div>
            <p class="admin-kicker">受測者</p>
            <h3 class="admin-heading mt-1 font-serif text-2xl font-bold">{{ row.participant.code }}</h3>
            <div class="mt-3 flex flex-wrap items-center gap-2">
              <span
                class="inline-flex min-h-8 items-center rounded-full border px-3 text-xs font-black"
                :class="row.participant.status === 'active'
                  ? 'border-[var(--admin-line)] bg-[var(--admin-coffee)] text-white'
                  : 'border-[var(--admin-border)] bg-[var(--admin-surface-muted)] text-[var(--admin-copy)]'"
              >
                {{ participantStatusLabel(row.participant.status) }}
              </span>
              <button
                v-if="row.participant.status === 'archived'"
                type="button"
                class="admin-button-secondary min-h-8 px-3 text-xs font-bold"
                :disabled="changingParticipantStatusId === row.participant.id"
                @click="$emit('restore', row.participant)"
              >
                恢復
              </button>
              <button
                v-else
                type="button"
                class="admin-button-secondary min-h-8 px-3 text-xs font-bold"
                :disabled="changingParticipantStatusId === row.participant.id"
                @click="archiveTarget = row"
              >
                封存
              </button>
            </div>
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
                v-for="(condition, index) in row.assignedConditions"
                :key="condition.code"
                class="inline-flex min-h-9 items-center rounded-full border border-[var(--admin-border)] bg-[var(--admin-surface-muted)] px-3 text-xs font-black text-[var(--admin-coffee)]"
              >
                {{ index + 1 }}. {{ condition.code }} {{ condition.label }}
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
          </div>
        </div>

        <div
          v-if="row.sessionHistory.length"
          class="mt-4 border-t border-[var(--admin-border-soft)] pt-4"
        >
          <div class="mb-2 flex items-center justify-between gap-3">
            <p class="admin-kicker">Session 紀錄</p>
            <span class="admin-caption text-xs font-bold">{{ row.sessionHistory.length }} 筆</span>
          </div>
          <div class="divide-y divide-[var(--admin-border-soft)]">
            <div
              v-for="item in row.sessionHistory"
              :key="item.session.id"
              class="grid min-h-12 gap-2 py-2 lg:grid-cols-[minmax(160px,1fr)_minmax(180px,1fr)_minmax(145px,0.8fr)_100px_116px_130px] lg:items-center"
            >
              <span class="admin-copy text-sm font-black">{{ item.eventName }}</span>
              <span class="admin-caption text-xs font-bold">
                {{ item.conditionCode }} {{ item.conditionLabel }}
              </span>
              <span class="admin-caption text-xs font-bold">
                {{ sessionTimerLabel(item.session) }}
              </span>
              <button
                type="button"
                class="admin-button-secondary inline-flex min-h-9 items-center justify-center gap-2 px-3 text-xs font-bold"
                @click="$emit('view-research', item.session.id)"
              >
                <Icon name="mdi:file-document-outline" class="h-4 w-4" />
                查看紀錄
              </button>
              <button
                type="button"
                class="admin-button-primary inline-flex min-h-9 items-center justify-center gap-2 px-3 text-xs font-bold"
                :disabled="item.session.status === 'archived' || !canResetTimer(item.session) || updatingTimerSessionId === item.session.id"
                :title="canResetTimer(item.session) ? '從現在重新開始五分鐘倒數' : '進入 Chat 後才會自動開始倒數'"
                @click="$emit('reset-timer', item.session.id)"
              >
                <Icon
                  :name="updatingTimerSessionId === item.session.id ? 'mdi:loading' : 'mdi:timer-refresh-outline'"
                  class="h-4 w-4"
                  :class="{ 'animate-spin': updatingTimerSessionId === item.session.id }"
                />
                重置 05:00
              </button>
              <button
                type="button"
                class="admin-button-secondary inline-flex min-h-9 items-center justify-center gap-2 px-3 text-xs font-bold"
                :disabled="item.session.status === 'archived' || restartingSessionId === item.session.id"
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

    <div v-if="!visibleRows.length" class="admin-empty-state p-5">
      {{ rows.length ? '目前沒有符合篩選條件的受測者。' : '目前沒有受測者資料。' }}
    </div>

    <Transition
      enter-active-class="transition-opacity duration-150"
      leave-active-class="transition-opacity duration-150"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div
        v-if="showCreateForm"
        class="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(47,41,36,0.5)] p-4 backdrop-blur-sm"
        @click.self="closeCreateForm"
      >
        <article class="w-full max-w-2xl rounded-[12px] border-2 border-[var(--admin-line)] bg-[var(--admin-page)] p-5 shadow-[0_30px_90px_rgba(47,41,36,0.3)]">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="admin-kicker">Participant registry</p>
              <h3 class="admin-heading mt-1 font-serif text-2xl font-bold">新增受測者</h3>
            </div>
            <button type="button" class="admin-button-secondary px-3 py-2 text-xs font-bold" @click="closeCreateForm">
              關閉
            </button>
          </div>

          <div class="mt-5 grid gap-5">
            <label class="block">
              <span class="admin-label">受測者代號</span>
              <input
                v-model="createCode"
                class="admin-field mt-1 w-full px-3 py-2 text-sm font-bold uppercase"
                placeholder="例如 P006"
              />
            </label>

            <label class="block">
              <span class="admin-label">Auth 帳號（可稍後綁定）</span>
              <select v-model="createAuthUserId" class="admin-field mt-1 w-full px-3 py-2 text-sm font-bold">
                <option value="">暫不綁定</option>
                <option
                  v-for="user in unboundAuthUsers"
                  :key="user.id"
                  :value="user.id"
                >
                  {{ user.email || shortId(user.id) }}
                </option>
              </select>
            </label>

            <fieldset>
              <legend class="admin-label">分派模式與執行順序</legend>
              <p class="admin-caption mt-1 text-xs font-bold">勾選模式後，可在下方調整受測者必須依序完成的順序。</p>
              <div class="mt-2 grid gap-2 sm:grid-cols-2">
                <label
                  v-for="condition in conditionOptions"
                  :key="condition.code"
                  class="flex min-h-12 items-center gap-3 rounded-[9px] border border-[var(--admin-border)] bg-[var(--admin-surface)] px-3 text-sm font-black text-[var(--admin-text)]"
                >
                  <input
                    v-model="createConditionCodes"
                    type="checkbox"
                    :value="condition.code"
                    class="h-4 w-4 accent-[var(--admin-coffee)]"
                  />
                  {{ condition.code }} {{ condition.label }}
                </label>
              </div>
              <div v-if="createConditionCodes.length" class="mt-3 grid gap-2">
                <div
                  v-for="(code, index) in createConditionCodes"
                  :key="code"
                  class="flex min-h-11 items-center gap-3 rounded-[9px] border border-[var(--admin-border)] bg-[var(--admin-surface-muted)] px-3"
                >
                  <span class="w-8 text-xs font-black text-[var(--admin-coffee)]">{{ index + 1 }}</span>
                  <span class="min-w-0 flex-1 text-sm font-black text-[var(--admin-text)]">{{ code }} {{ conditionName(code) }}</span>
                  <button
                    type="button"
                    class="admin-button-secondary inline-flex h-8 w-8 items-center justify-center p-0"
                    :disabled="index === 0"
                    title="往前一個階段"
                    @click="moveCondition(createConditionCodes, index, -1)"
                  >
                    <Icon name="mdi:arrow-up" class="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    class="admin-button-secondary inline-flex h-8 w-8 items-center justify-center p-0"
                    :disabled="index === createConditionCodes.length - 1"
                    title="往後一個階段"
                    @click="moveCondition(createConditionCodes, index, 1)"
                  >
                    <Icon name="mdi:arrow-down" class="h-4 w-4" />
                  </button>
                </div>
              </div>
            </fieldset>
          </div>

          <div class="mt-6 flex justify-end gap-2">
            <button type="button" class="admin-button-secondary px-4 py-2 text-sm font-bold" @click="closeCreateForm">
              取消
            </button>
            <button
              type="button"
              class="admin-button-primary inline-flex min-h-10 items-center gap-2 px-4 text-sm font-bold"
              :disabled="creatingParticipant || !createCode.trim()"
              @click="submitCreateForm"
            >
              <Icon :name="creatingParticipant ? 'mdi:loading' : 'mdi:account-plus-outline'" class="h-4 w-4" :class="{ 'animate-spin': creatingParticipant }" />
              建立
            </button>
          </div>
        </article>
      </div>
    </Transition>

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
              <legend class="admin-label">分派模式與執行順序</legend>
              <p class="admin-caption mt-1 text-xs font-bold">已進行中的模式請勿任意移除；順序變更會立即影響下一個可開始的模式。</p>
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
              <div v-if="draftConditionCodes.length" class="mt-3 grid gap-2">
                <div
                  v-for="(code, index) in draftConditionCodes"
                  :key="code"
                  class="flex min-h-11 items-center gap-3 rounded-[9px] border border-[var(--admin-border)] bg-[var(--admin-surface-muted)] px-3"
                >
                  <span class="w-8 text-xs font-black text-[var(--admin-coffee)]">{{ index + 1 }}</span>
                  <span class="min-w-0 flex-1 text-sm font-black text-[var(--admin-text)]">{{ code }} {{ conditionName(code) }}</span>
                  <button
                    type="button"
                    class="admin-button-secondary inline-flex h-8 w-8 items-center justify-center p-0"
                    :disabled="index === 0"
                    title="往前一個階段"
                    @click="moveCondition(draftConditionCodes, index, -1)"
                  >
                    <Icon name="mdi:arrow-up" class="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    class="admin-button-secondary inline-flex h-8 w-8 items-center justify-center p-0"
                    :disabled="index === draftConditionCodes.length - 1"
                    title="往後一個階段"
                    @click="moveCondition(draftConditionCodes, index, 1)"
                  >
                    <Icon name="mdi:arrow-down" class="h-4 w-4" />
                  </button>
                </div>
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

    <ConfirmActionModal
      :show="Boolean(archiveTarget)"
      title="封存受測者"
      :message="archiveConfirmationMessage"
      eyebrow="Participant registry"
      icon="mdi:archive-arrow-down-outline"
      confirm-label="封存"
      cancel-label="取消"
      @confirm="confirmArchive"
      @cancel="archiveTarget = null"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import ConfirmActionModal from '~/components/modals/ConfirmActionModal.vue';
import type { AdminAuthUserSummary, ExperimentSession, Participant } from '~/types';
import type { ParticipantCreateInput, ParticipantUpdateInput } from '~/utils/histosphereApi';
import {
  conditionDisplayLabel,
  conditionName,
  filterParticipantDashboardRows,
  participantConditionLabels,
  participantStageLabels,
  type ParticipantDashboardRow,
  type ParticipantSessionSummary,
  type ParticipantStage,
} from '~/utils/adminParticipantDashboard';

const props = defineProps<{
  rows: ParticipantDashboardRow[];
  authUsers: AdminAuthUserSummary[];
  creatingParticipant: boolean;
  changingParticipantStatusId: string | null;
  savingParticipantId: string | null;
  updatingTimerSessionId: string | null;
  restartingSessionId: string | null;
}>();

const emit = defineEmits<{
  (event: 'create', payload: ParticipantCreateInput): void;
  (event: 'archive', participant: Participant): void;
  (event: 'restore', participant: Participant): void;
  (event: 'save', participantId: string, payload: ParticipantUpdateInput): void;
  (event: 'reset-timer', sessionId: string): void;
  (event: 'restart-session', sessionId: string): void;
  (event: 'view-research', sessionId: string): void;
}>();

const stages: ParticipantStage[] = ['not_started', 'task', 'chat', 'completed'];
const showArchived = ref(false);
const showCreateForm = ref(false);
const createCode = ref('');
const createAuthUserId = ref('');
const createConditionCodes = ref<string[]>([]);
const editingRow = ref<ParticipantDashboardRow | null>(null);
const draftAuthUserId = ref('');
const draftConditionCodes = ref<string[]>([]);
const restartTarget = ref<ParticipantSessionSummary | null>(null);
const archiveTarget = ref<ParticipantDashboardRow | null>(null);

const visibleRows = computed(() => filterParticipantDashboardRows(props.rows, showArchived.value));
const activeCount = computed(() => props.rows.filter((row) => row.participant.status === 'active').length);
const archivedCount = computed(() => props.rows.filter((row) => row.participant.status === 'archived').length);
const unboundAuthUsers = computed(() => props.authUsers.filter((user) => !user.bound_participant_id));

const archiveConfirmationMessage = computed(() => {
  if (!archiveTarget.value) return '';
  return `封存 ${archiveTarget.value.participant.code} 後將停止其實驗存取；Auth 綁定、Session、Task、Chat 與研究紀錄都會保留。`;
});

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

const openCreateForm = () => {
  createCode.value = '';
  createAuthUserId.value = '';
  createConditionCodes.value = [];
  showCreateForm.value = true;
};

const closeCreateForm = () => {
  showCreateForm.value = false;
  createCode.value = '';
  createAuthUserId.value = '';
  createConditionCodes.value = [];
};

const submitCreateForm = () => {
  const code = createCode.value.trim().toUpperCase();
  if (!code) return;
  emit('create', {
    code,
    auth_user_id: createAuthUserId.value || null,
    condition_list: [...createConditionCodes.value],
  });
  closeCreateForm();
};

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

const moveCondition = (codes: string[], index: number, direction: -1 | 1) => {
  const targetIndex = index + direction;
  if (targetIndex < 0 || targetIndex >= codes.length) return;
  const [code] = codes.splice(index, 1);
  if (!code) return;
  codes.splice(targetIndex, 0, code);
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

const canResetTimer = (session: ExperimentSession) => {
  return session.status === 'conversation_started'
    || (session.status === 'completed' && session.completion_reason === 'timer_elapsed');
};

const sessionTimerLabel = (session: ExperimentSession) => {
  if (session.timer_ends_at) {
    const prefix = session.status === 'completed' ? '已結束' : '倒數至';
    return `${prefix} ${formatDate(session.timer_ends_at)}`;
  }
  return `${sessionStatusLabel(session.status)} · Chat 後自動倒數`;
};

const confirmRestart = () => {
  if (!restartTarget.value) return;
  emit('restart-session', restartTarget.value.session.id);
  restartTarget.value = null;
};

const confirmArchive = () => {
  if (!archiveTarget.value) return;
  emit('archive', archiveTarget.value.participant);
  archiveTarget.value = null;
};

const participantStatusLabel = (status: Participant['status']) => {
  if (status === 'archived') return '已封存';
  if (status === 'completed') return '已完成';
  if (status === 'excluded') return '已排除';
  return '使用中';
};

const sessionStatusLabel = (status: string) => {
  if (status === 'completed') return '已完成';
  if (status === 'conversation_started') return 'Chat';
  if (status === 'task_submitted') return 'Task 已提交';
  return 'Task';
};
</script>
