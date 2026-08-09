<template>
  <div>
    <div class="grid gap-3 lg:grid-cols-[minmax(260px,1.4fr)_minmax(180px,0.8fr)_minmax(180px,0.8fr)_150px_150px]">
      <label class="block">
        <span class="admin-label">搜尋紀錄</span>
        <span class="relative mt-1 block">
          <Icon name="mdi:magnify" class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--admin-soft)]" />
          <input
            v-model="filters.search"
            class="admin-field w-full py-2 pl-9 pr-3 text-sm"
            placeholder="動作、人物、受測者或欄位"
          />
        </span>
      </label>

      <label class="block">
        <span class="admin-label">操作類型</span>
        <select v-model="filters.actionType" class="admin-field mt-1 w-full px-3 py-2 text-sm">
          <option value="">全部操作</option>
          <option v-for="action in actionOptions" :key="action" :value="action">
            {{ researchLogActionLabel(action) }}
          </option>
        </select>
      </label>

      <label class="block">
        <span class="admin-label">歷史事件</span>
        <select v-model="filters.eventId" class="admin-field mt-1 w-full px-3 py-2 text-sm">
          <option value="">全部事件</option>
          <option v-for="event in events" :key="event.id" :value="event.id">
            {{ event.canonical_name }}
          </option>
        </select>
      </label>

      <label class="block">
        <span class="admin-label">開始日期</span>
        <input v-model="filters.dateFrom" type="date" class="admin-field mt-1 w-full px-3 py-2 text-sm" />
      </label>

      <label class="block">
        <span class="admin-label">結束日期</span>
        <input v-model="filters.dateTo" type="date" class="admin-field mt-1 w-full px-3 py-2 text-sm" />
      </label>
    </div>

    <div class="mt-4 flex items-center justify-between gap-4 border-t border-[var(--admin-border-soft)] pt-4">
      <p class="admin-caption text-sm font-semibold">
        顯示 {{ filteredLogs.length }} / {{ logs.length }} 筆
      </p>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="admin-button-secondary min-h-10 px-3 text-xs font-bold"
          :disabled="!hasFilters"
          @click="clearFilters"
        >
          清除篩選
        </button>
        <button
          type="button"
          class="admin-button-secondary min-h-10 px-3 text-xs font-bold"
          :disabled="!filteredLogs.length"
          @click="downloadCsv"
        >
          <Icon name="mdi:download-outline" class="h-4 w-4" />
          匯出目前稽核
        </button>
        <button
          type="button"
          class="admin-button-primary min-h-10 px-3 text-xs font-bold"
          @click="$emit('export-research', 'csv')"
        >
          完整研究 CSV
        </button>
        <button
          type="button"
          class="admin-button-primary min-h-10 px-3 text-xs font-bold"
          @click="$emit('export-research', 'json')"
        >
          完整研究 JSON
        </button>
      </div>
    </div>

    <div v-if="filteredLogs.length" class="mt-4 divide-y divide-[var(--admin-border-soft)] border-y border-[var(--admin-border-soft)]">
      <details v-for="log in filteredLogs" :key="log.id" class="group">
        <summary class="grid cursor-pointer list-none gap-3 px-2 py-4 hover:bg-[var(--admin-surface-muted)] md:grid-cols-[190px_minmax(180px,0.8fr)_minmax(0,1fr)_24px] md:items-center">
          <time class="admin-caption text-xs font-semibold">{{ formatDateTime(log.created_at) }}</time>
          <span class="font-bold text-[var(--admin-text)]">{{ researchLogActionLabel(log.action_type) }}</span>
          <span class="truncate text-sm font-semibold text-[var(--admin-copy)]">{{ subjectLabel(log) }}</span>
          <Icon name="mdi:chevron-down" class="h-5 w-5 text-[var(--admin-soft)] transition-transform group-open:rotate-180" />
        </summary>

        <div class="border-t border-[var(--admin-border-soft)] bg-[var(--admin-surface-muted)] px-3 py-4 md:px-5">
          <div v-if="researchLogChanges(log).length" class="overflow-x-auto">
            <table class="w-full min-w-[760px] table-fixed text-left text-sm">
              <thead>
                <tr class="text-xs font-bold text-[var(--admin-coffee)]">
                  <th class="w-40 pb-2 pr-3">變更欄位</th>
                  <th class="pb-2 pr-3">修改前</th>
                  <th class="pb-2">修改後</th>
                </tr>
              </thead>
              <tbody class="align-top">
                <tr
                  v-for="{ field, change } in researchLogChanges(log)"
                  :key="field"
                  class="border-t border-[var(--admin-border-soft)]"
                >
                  <th class="py-3 pr-3 font-mono text-xs text-[var(--admin-text)]">{{ field }}</th>
                  <td class="py-3 pr-3">
                    <pre class="max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-md border border-[var(--admin-border-soft)] bg-[var(--admin-surface)] p-3 text-xs leading-5 text-[var(--admin-copy)]">{{ formatResearchLogValue(change.before) }}</pre>
                  </td>
                  <td class="py-3">
                    <pre class="max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-md border border-[var(--admin-border)] bg-[var(--admin-surface)] p-3 text-xs leading-5 text-[var(--admin-text)]">{{ formatResearchLogValue(change.after) }}</pre>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p v-else class="admin-caption text-sm font-semibold">
            此舊紀錄或流程事件沒有欄位差異資料，可查看完整 payload。
          </p>

          <details class="mt-4">
            <summary class="cursor-pointer text-xs font-bold text-[var(--admin-coffee)]">完整 payload</summary>
            <pre class="admin-code-editor mt-2 max-h-72 overflow-auto whitespace-pre-wrap rounded-md p-3 text-xs leading-5">{{ JSON.stringify(log.payload || {}, null, 2) }}</pre>
          </details>
        </div>
      </details>
    </div>

    <div v-else class="admin-empty-state mt-4 p-6 text-center">
      沒有符合目前條件的研究紀錄。
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue';
import type { EventWithPersonas, ResearchLog } from '~/types';
import {
  filterResearchLogs,
  formatResearchLogValue,
  researchLogActionLabel,
  researchLogChanges,
  researchLogsToCsv,
} from '~/utils/adminResearchLogs';

const props = defineProps<{
  logs: ResearchLog[];
  events: EventWithPersonas[];
}>();
defineEmits<{ (event: 'export-research', format: 'json' | 'csv'): void }>();

const filters = reactive({
  search: '',
  actionType: '',
  eventId: '',
  dateFrom: '',
  dateTo: '',
});

const actionOptions = computed(() => {
  return [...new Set(props.logs.map((log) => log.action_type))].sort((a, b) => a.localeCompare(b));
});

const filteredLogs = computed(() => filterResearchLogs(props.logs, filters));
const eventNames = computed(() => {
  return Object.fromEntries(props.events.map((event) => [event.id, event.canonical_name]));
});
const hasFilters = computed(() => Object.values(filters).some(Boolean));

const clearFilters = () => {
  filters.search = '';
  filters.actionType = '';
  filters.eventId = '';
  filters.dateFrom = '';
  filters.dateTo = '';
};

const formatDateTime = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
};

const subjectLabel = (log: ResearchLog) => {
  const payload = log.payload || {};
  if (payload.participant_code) return `受測者 ${payload.participant_code}`;
  if (payload.persona_name) return String(payload.persona_name);
  if (log.event_id) return eventNames.value[log.event_id] || `事件 ${log.event_id}`;
  if (log.session_id) return `Session ${log.session_id}`;
  return '系統操作';
};

const downloadCsv = () => {
  if (!import.meta.client || !filteredLogs.value.length) return;
  const content = researchLogsToCsv(filteredLogs.value, eventNames.value);
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `histosphere-research-logs-${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
};
</script>
