<template>
  <!-- TaskStudentGate 只負責任務頁畫面；資料載入與送出由 useTaskGate 控制。 -->
  <TaskStudentShell>
    <div v-if="isLoading" class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-6 text-[var(--admin-copy)] shadow-[var(--admin-shadow-soft)]">
      正在載入任務資料...
    </div>

    <div v-else-if="!taskData" class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-6 text-[var(--admin-copy)] shadow-[var(--admin-shadow-soft)]">
      找不到活動資料。請回首頁重新建立流程。
    </div>

    <section v-else class="space-y-7">
      <section class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-1.5 shadow-[var(--admin-shadow-soft)]">
        <div class="rounded-[10px] border border-[var(--admin-border-soft)] p-5 md:p-6">
          <div class="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
            <div class="max-w-3xl">
              <p class="text-xs font-bold uppercase tracking-[0.18em] text-[var(--admin-coffee)]">前置任務</p>
              <h1 class="mt-2 font-serif text-4xl font-bold tracking-[0.02em] text-[var(--admin-text)] md:text-5xl">
                {{ taskData.event.canonical_name }}
              </h1>
              <p class="mt-3 text-base font-semibold leading-8 text-[var(--admin-copy)]">
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

      <TaskStudentStory :model-value="modelValue" :task="taskData.task" @update:model-value="emit('update:modelValue', $event)" />

      <form class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-5 shadow-md" @submit.prevent="openSubmitConfirm">
        <TaskStudentRenderer
          v-if="!hasInlineTaskBlanks(taskData.task)"
          :model-value="modelValue"
          :task="taskData.task"
          @update:model-value="emit('update:modelValue', $event)"
        />
        <TaskStudentSubmitBar
          :class="hasInlineTaskBlanks(taskData.task) ? '' : 'mt-5'"
          :can-submit="canSubmit"
          :is-submitting="isSubmitting"
          :error="error"
          :judgement="judgement"
        />
      </form>
    </section>

    <ConfirmActionModal
      :show="showSubmitConfirmDialog"
      title="送出前置任務"
      message="送出後將進入對話階段。是否確認送出？"
      eyebrow="階段確認"
      icon="mdi:send-check-outline"
      confirm-label="是"
      cancel-label="否"
      @confirm="confirmSubmit"
      @cancel="showSubmitConfirmDialog = false"
    />
  </TaskStudentShell>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import ConfirmActionModal from '~/components/modals/ConfirmActionModal.vue';
import type { EventInitializeResponse, TaskStudentAnswer } from '~/types';
import { hasInlineTaskBlanks, studentActivityTitle } from '~/composables/useStudentTask';

const props = defineProps<{
  taskData: EventInitializeResponse | null;
  modelValue: TaskStudentAnswer[];
  canSubmit: boolean;
  error: string | null;
  isLoading: boolean;
  isSubmitting: boolean;
  judgement: Record<string, any> | null;
}>();

const emit = defineEmits<{
  (event: 'submit'): void;
  (event: 'update:modelValue', value: TaskStudentAnswer[]): void;
}>();

const showSubmitConfirmDialog = ref(false);

const openSubmitConfirm = () => {
  if (!props.canSubmit || props.isSubmitting) return;
  showSubmitConfirmDialog.value = true;
};

const confirmSubmit = () => {
  showSubmitConfirmDialog.value = false;
  emit('submit');
};
</script>
