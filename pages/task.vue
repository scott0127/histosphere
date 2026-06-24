<template>
  <!-- 前置任務頁：學生/受測者必須先完成 task，才能進入對話。 -->
  <TaskStudentShell>
    <div v-if="!taskData" class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-6 text-[var(--admin-copy)] shadow-[var(--admin-shadow-soft)]">
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

      <TaskStudentStory v-model="answers" :task="taskData.task" />

      <form class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-5 shadow-md" @submit.prevent="submitTask">
        <TaskStudentRenderer v-if="!hasInlineTaskBlanks(taskData.task)" v-model="answers" :task="taskData.task" />
        <TaskStudentSubmitBar
          :class="hasInlineTaskBlanks(taskData.task) ? '' : 'mt-5'"
          :can-submit="canSubmit"
          :is-submitting="isSubmitting"
          :error="error"
          :judgement="judgement"
        />
      </form>
    </section>
  </TaskStudentShell>
</template>

<script setup lang="ts">
// task.vue 負責把 event initialize 的暫存資料送出成 task_attempt。
// 送出成功後才導向 chat，並把 conversationId 寫回本機進度，讓首頁可以顯示已完成/進行中。
import { computed, ref } from 'vue';
import type { EventInitializeResponse, TaskStudentAnswer, TaskSubmitResponse } from '~/types';
import {
  buildTaskResponsePayload,
  hasInlineTaskBlanks,
  isTaskAnswerComplete,
  markStudentConditionProgress,
  normalizeTaskQuestions,
  participantUuid,
  studentActivityTitle,
} from '~/composables/useStudentTask';

definePageMeta({
  layout: false,
  name: 'task-gate',
});

const taskData = useState<EventInitializeResponse | null>('taskData', () => null);
const route = useRoute();
const answers = ref<TaskStudentAnswer[]>([]);
const isSubmitting = ref(false);
const error = ref<string | null>(null);
const judgement = ref<Record<string, any> | null>(null);

const taskQuestions = computed(() => taskData.value ? normalizeTaskQuestions(taskData.value.task) : []);
const canSubmit = computed(() => isTaskAnswerComplete(taskQuestions.value, answers.value));

const submitTask = async () => {
  if (!taskData.value || !canSubmit.value) return;
  isSubmitting.value = true;
  error.value = null;
  try {
    const response = await $fetch<TaskSubmitResponse>(`/api/tasks/${taskData.value.task.id}/submit`, {
      method: 'POST',
      body: {
        session_id: taskData.value.session_id,
        user_id: participantUuid(participantId()),
        response_payload: buildTaskResponsePayload(answers.value),
      },
    });
    judgement.value = response.judgement;
    markStudentConditionProgress(participantId(), response);

    const chatData = useState<TaskSubmitResponse | null>('chatData', () => null);
    chatData.value = response;
    await navigateTo({
      path: '/chat',
      query: {
        conversationId: response.conversation_id,
      },
    });
  } catch (e: any) {
    error.value = e.data?.detail || e.data?.message || '送出失敗，請稍後再試。';
  } finally {
    isSubmitting.value = false;
  }
};

// participantId 目前從首頁 query 帶入；若缺漏就使用開發預設受測者。
const participantId = () => {
  return typeof route.query.participantId === 'string' && route.query.participantId.trim()
    ? route.query.participantId.trim()
    : 'scott-test';
};

</script>
