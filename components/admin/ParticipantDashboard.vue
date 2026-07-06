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
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { AdminAuthUserSummary } from '~/types';
import type { ParticipantUpdateInput } from '~/utils/histosphereApi';
import {
  conditionDisplayLabel,
  participantConditionLabels,
  participantStageLabels,
  type ParticipantDashboardRow,
  type ParticipantStage,
} from '~/utils/adminParticipantDashboard';

const props = defineProps<{
  rows: ParticipantDashboardRow[];
  authUsers: AdminAuthUserSummary[];
  savingParticipantId: string | null;
}>();

const emit = defineEmits<{
  (event: 'save', participantId: string, payload: ParticipantUpdateInput): void;
}>();

const stages: ParticipantStage[] = ['not_started', 'task', 'chat', 'completed'];
const editingRow = ref<ParticipantDashboardRow | null>(null);
const draftAuthUserId = ref('');
const draftConditionCodes = ref<string[]>([]);

const conditionOptions = computed(() => {
  return Object.keys(participantConditionLabels).map((code) => ({
    code,
    label: participantConditionLabels[code],
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
</script>
