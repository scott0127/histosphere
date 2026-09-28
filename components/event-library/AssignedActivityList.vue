<template>
  <section class="flex min-h-0 min-w-0 flex-col">
    <div class="mb-6 flex items-end justify-between gap-4 border-b border-[var(--admin-border)] pb-4">
      <div>
        <p class="text-xs font-bold tracking-[0.15em] text-[var(--admin-coffee)]">學習活動</p>
        <h2 class="mt-2 font-serif text-3xl font-bold">我的活動</h2>
        <p class="mt-3 text-sm text-[var(--admin-copy)]">請依序完成指定活動與後測，再進入下一場。</p>
      </div>
      <span class="shrink-0 text-sm font-semibold text-[var(--admin-coffee)]">{{ assignments.length }} 場</span>
    </div>
    <p v-if="error" role="alert" class="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{{ error }}</p>
    <p v-if="loading" role="status" class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-8">載入分派活動…</p>
    <ol v-else-if="assignments.length" class="min-h-0 space-y-5 overflow-y-auto pr-1">
      <li v-for="(assignment, index) in assignments" :key="assignment.event_id" class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-6 shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <p class="text-sm font-bold text-[var(--admin-coffee)]">第 {{ index + 1 }} 場 · {{ assignment.condition_code }} 模式</p>
          <span class="rounded-full bg-[var(--admin-surface-muted)] px-3 py-1 text-xs font-semibold">{{ statusLabel(assignment) }}</span>
        </div>
        <h3 class="mt-4 font-serif text-3xl font-bold">{{ eventFor(assignment)?.canonical_name || '教材尚未開放' }}</h3>
        <div class="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--admin-border-soft)] pt-4">
          <p class="text-sm leading-6 text-[var(--admin-copy)]">{{ activityHint(assignment) }}</p>
          <button
            type="button"
            :disabled="!canOpen(assignment)"
            :aria-label="`第 ${index + 1} 場 ${eventFor(assignment)?.canonical_name || '教材尚未開放'} ${assignment.condition_code}模式 ${buttonLabel(assignment)}`"
            class="min-h-11 rounded-lg border border-[var(--admin-coffee)] bg-[var(--admin-coffee)] px-5 py-2 text-sm font-bold text-white transition hover:bg-[var(--admin-coffee-hover)] disabled:cursor-not-allowed disabled:border-[var(--admin-border)] disabled:bg-[var(--admin-surface-muted)] disabled:text-[var(--admin-soft)]"
            @click="openActivity(assignment)"
          >{{ buttonLabel(assignment) }}</button>
        </div>
      </li>
    </ol>
    <div v-else class="rounded-xl border border-dashed border-[var(--admin-border)] bg-[var(--admin-surface)] p-8">
      <h3 class="text-xl font-bold">尚未分派活動</h3>
      <p class="mt-3 text-sm leading-7 text-[var(--admin-copy)]">{{ emptyMessage }}</p>
      <NuxtLink v-if="participantPreview" to="/admin" class="mt-4 inline-flex min-h-11 items-center font-bold text-[var(--admin-coffee)] underline underline-offset-4">前往管理端設定活動分派</NuxtLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ConditionKey, EventWithPersonas, ParticipantActivityAssignment } from '~/types';
import type { LocalConditionProgress } from '~/composables/useExperimentSession';
import { conditionKeyForActivity } from '~/utils/participantActivities';

const props = defineProps<{
  assignments: ParticipantActivityAssignment[];
  events: EventWithPersonas[];
  currentEventId?: string;
  progressByEvent: Record<string, Partial<Record<ConditionKey, LocalConditionProgress>>>;
  loading: boolean;
  error?: string | null;
  emptyMessage: string;
  participantPreview: boolean;
}>();
const emit = defineEmits<{ (event: 'open', value: EventWithPersonas): void }>();
const eventFor = (assignment: ParticipantActivityAssignment) => props.events.find((event) => event.id === assignment.event_id && !event.archived_at);
const progressFor = (assignment: ParticipantActivityAssignment) => props.progressByEvent[assignment.event_id]?.[conditionKeyForActivity(assignment)];
const isComplete = (assignment: ParticipantActivityAssignment) => {
  const progress = progressFor(assignment);
  return progress?.status === 'completed' && progress.posttestStage === 'completed';
};
const canOpen = (assignment: ParticipantActivityAssignment) => Boolean(eventFor(assignment)) && props.currentEventId === assignment.event_id && !isComplete(assignment);
const statusLabel = (assignment: ParticipantActivityAssignment) => {
  if (isComplete(assignment)) return '已完成';
  if (!eventFor(assignment)) return '尚未開放';
  if (props.currentEventId !== assignment.event_id) return '等待前一場完成';
  const progress = progressFor(assignment);
  return progress && progress.status !== 'archived' ? '進行中' : '目前活動';
};
const activityHint = (assignment: ParticipantActivityAssignment) => {
  if (isComplete(assignment)) return '活動與後測皆已完成。';
  if (!eventFor(assignment)) return '請聯絡研究者確認這場活動的教材。';
  if (props.currentEventId !== assignment.event_id) return '完成前一場活動與後測後開放。';
  return '閱讀材料、完成作答，再進入對話。';
};
const buttonLabel = (assignment: ParticipantActivityAssignment) => {
  if (isComplete(assignment)) return '已完成';
  if (!canOpen(assignment)) return '尚未開放';
  const progress = progressFor(assignment);
  return progress && progress.status !== 'archived' ? '繼續活動' : '開始活動';
};
const openActivity = (assignment: ParticipantActivityAssignment) => {
  const event = eventFor(assignment);
  if (event && canOpen(assignment)) emit('open', event);
};
</script>
