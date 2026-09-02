<template>
  <!-- TaskStudentGate 只負責任務頁畫面；資料載入與送出由 useTaskGate 控制。 -->
  <TaskStudentShell>
    <div v-if="isLoading" class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-6 text-[var(--admin-copy)] shadow-[var(--admin-shadow-soft)]">
      正在載入任務資料...
    </div>

    <div v-else-if="!taskData" class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-6 text-[var(--admin-copy)] shadow-[var(--admin-shadow-soft)]">
      {{ error || '找不到活動資料。請回首頁重新建立流程。' }}
    </div>

    <section v-else class="space-y-7">
      <SessionTimerBanner :session="session" />
      <section class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-1.5 shadow-[var(--admin-shadow-soft)]">
        <div class="rounded-[10px] border border-[var(--admin-border-soft)] p-5 md:p-6">
          <div class="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
            <div class="max-w-3xl">
              <p class="text-xs font-bold text-[var(--admin-coffee)]">Error-Elicitation Task</p>
              <h1 class="mt-2 font-serif text-4xl font-bold tracking-[0.02em] text-[var(--admin-text)] md:text-5xl">
                {{ taskData.event.canonical_name }}
              </h1>
              <p v-if="showEventIntroduction" class="mt-3 text-base font-semibold leading-8 text-[var(--admin-copy)]">
                {{ taskData.event.description || '請先完成這個歷史故事任務，再進入後續對話。' }}
              </p>
            </div>

            <aside class="w-full rounded-[10px] border border-[var(--admin-border-soft)] bg-[var(--admin-surface-muted)] p-5 md:w-[280px]">
              <p class="text-xs font-bold uppercase tracking-[0.18em] text-[var(--admin-coffee)]">活動</p>
              <p class="mt-2 text-lg font-bold text-[var(--admin-text)]">{{ studentActivityTitle(taskData.condition) }}</p>
              <p v-if="taskData.personas[0]" class="mt-3 text-sm font-semibold leading-6 text-[var(--admin-copy)]">
                {{ taskData.personas[0].name }}
              </p>
            </aside>
          </div>
        </div>
      </section>

      <p v-if="configurationError" role="alert" class="text-sm font-semibold text-[var(--admin-danger)]">{{ configurationError }}</p>
      <fieldset :disabled="sessionClosed || isSubmitting || Boolean(configurationError)" class="min-w-0 space-y-7 disabled:opacity-70">
      <TaskStudentStory :model-value="modelValue" :task="taskData.task" @update:model-value="emit('update:modelValue', $event)" />

      <form class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-5 shadow-md" @submit.prevent="openSubmitConfirm">
        <TaskStudentRenderer
          v-if="!isErrorElicitationTask(taskData.task) && !hasInlineTaskBlanks(taskData.task)"
          :model-value="modelValue"
          :task="taskData.task"
          @update:model-value="emit('update:modelValue', $event)"
        />
        <TaskStudentSubmitBar
          :class="hasInlineTaskBlanks(taskData.task) ? '' : 'mt-5'"
          :can-submit="submissionReady"
          :is-submitting="isSubmitting"
          :error="error"
          :judgement="judgement"
        />
      </form>
      </fieldset>
    </section>

    <ConfirmActionModal
      :show="showSubmitConfirmDialog"
      title="TASK"
      message="點選「是」進入下一階段 [CHAT]"
      eyebrow="階段確認"
      icon="mdi:send-check-outline"
      confirm-label="是"
      cancel-label="否"
      @confirm="confirmSubmit"
      @cancel="showSubmitConfirmDialog = false"
    />

    <TaskTransitionOverlay
      :show="isSubmitting"
      :event-name="taskData?.event.canonical_name || '歷史事件'"
      :start-year="taskData?.event.start_year"
      :end-year="taskData?.event.end_year"
    />
  </TaskStudentShell>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import ConfirmActionModal from '~/components/modals/ConfirmActionModal.vue';
import TaskTransitionOverlay from '~/components/task-student/TaskTransitionOverlay.vue';
import type { EventInitializeResponse, ExperimentSession, TaskStudentAnswer } from '~/types';
import SessionTimerBanner from '~/components/session/SessionTimerBanner.vue';
import { hasInlineTaskBlanks, isErrorElicitationTask, isTaskAnswerComplete, normalizeTaskQuestions, studentActivityTitle, taskConfigurationError } from '~/composables/useStudentTask';
import { shouldShowEventIntroduction, type EventIntroductionMode } from '~/utils/eventVisibility';

const props = defineProps<{
  taskData: EventInitializeResponse | null;
  modelValue: TaskStudentAnswer[];
  canSubmit: boolean;
  error: string | null;
  isLoading: boolean;
  isSubmitting: boolean;
  judgement: Record<string, any> | null;
  session?: ExperimentSession | null;
  activityMode?: EventIntroductionMode;
}>();

const emit = defineEmits<{
  (event: 'submit'): void;
  (event: 'update:modelValue', value: TaskStudentAnswer[]): void;
}>();

const showSubmitConfirmDialog = ref(false);
const showEventIntroduction = computed(() => shouldShowEventIntroduction(props.activityMode || 'learner'));
const configurationError = computed(() => props.taskData ? taskConfigurationError(props.taskData.task) : null);
const submissionReady = computed(() => Boolean(props.canSubmit && props.taskData
  && isTaskAnswerComplete(normalizeTaskQuestions(props.taskData.task), props.modelValue, props.taskData.task)));
const now = ref(Date.now());
let timerId: ReturnType<typeof setInterval> | null = null;
const sessionClosed = computed(() => {
  return props.session?.status === 'completed'
    || props.session?.status === 'archived'
    || Boolean(props.session?.timer_ends_at && Date.parse(props.session.timer_ends_at) <= now.value);
});

onMounted(() => { timerId = setInterval(() => { now.value = Date.now(); }, 1000); });
onBeforeUnmount(() => { if (timerId) clearInterval(timerId); });

const openSubmitConfirm = () => {
  if (!submissionReady.value || props.isSubmitting || sessionClosed.value) return;
  showSubmitConfirmDialog.value = true;
};

const confirmSubmit = () => {
  showSubmitConfirmDialog.value = false;
  if (!submissionReady.value || props.isSubmitting || sessionClosed.value) return;
  emit('submit');
};
</script>
