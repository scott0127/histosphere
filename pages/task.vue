<template>
  <!-- 前置任務頁：學生/受測者必須先完成 task，才能進入對話。 -->
  <TaskStudentShell>
    <div v-if="isLoadingState" class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-6 text-[var(--admin-copy)] shadow-[var(--admin-shadow-soft)]">
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

      <TaskStudentStory v-model="answers" :task="taskData.task" />

      <form class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-5 shadow-md" @submit.prevent="submitTask">
        <TaskStudentRenderer v-if="!hasInlineTaskBlanks(taskData.task)" v-model="answers" :task="taskData.task" />
        <TaskStudentSubmitBar
          :class="hasInlineTaskBlanks(taskData.task) ? '' : 'mt-5'"
          :can-submit="canSubmit"
          :is-submitting="isSubmitting"
          :error="error || draftError"
          :judgement="judgement"
        />
      </form>
    </section>
  </TaskStudentShell>
</template>

<script setup lang="ts">
// task.vue 負責把 event initialize 的暫存資料送出成 task_attempt。
// 送出成功後才導向 chat，並把 conversationId 寫回本機進度，讓首頁可以顯示已完成/進行中。
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import type { EventInitializeResponse, SessionStateResponse, TaskDraftResponse, TaskStudentAnswer, TaskSubmitResponse } from '~/types';
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
const isLoadingState = ref(false);
const error = ref<string | null>(null);
const draftError = ref<string | null>(null);
const draftSaveTimer = ref<ReturnType<typeof setTimeout> | null>(null);
const lastDraftPayload = ref<string | null>(null);
const judgement = ref<Record<string, any> | null>(null);

const taskQuestions = computed(() => taskData.value ? normalizeTaskQuestions(taskData.value.task) : []);
const canSubmit = computed(() => isTaskAnswerComplete(taskQuestions.value, answers.value));

onMounted(async () => {
  const routeSessionId = sessionId();
  if (routeSessionId && taskData.value?.session_id !== routeSessionId) {
    await loadSessionState(routeSessionId);
  }
});

watch(
  answers,
  () => {
    if (!taskData.value || !sessionId() || isSubmitting.value || answers.value.length === 0) return;
    scheduleDraftSave();
  },
  { deep: true },
);

onBeforeUnmount(() => {
  clearDraftTimer();
});

const submitTask = async () => {
  if (!taskData.value || !canSubmit.value) return;
  clearDraftTimer();
  isSubmitting.value = true;
  error.value = null;
  draftError.value = null;
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

// 重新整理或直接打開 task URL 時，用 sessionId 從後端還原完整任務上下文。
const loadSessionState = async (routeSessionId: string) => {
  isLoadingState.value = true;
  error.value = null;
  try {
    const state = await $fetch<SessionStateResponse>(`/api/sessions/${routeSessionId}/state`);
    if (state.conversation_id) {
      await navigateTo({
        path: '/chat',
        query: { conversationId: state.conversation_id },
      });
      return;
    }
    if (!state.task || !state.condition) {
      error.value = '這個 session 缺少任務或活動條件資料，請回首頁重新開始。';
      return;
    }
    taskData.value = {
      event_id: state.event.id,
      session_id: state.session.id,
      event: state.event,
      task: state.task,
      personas: state.personas,
      condition: state.condition,
    };
    answers.value = answersFromAttempt(state.attempt?.response_payload);
    lastDraftPayload.value = answers.value.length
      ? JSON.stringify(buildTaskResponsePayload(answers.value))
      : null;
  } catch (e: any) {
    error.value = e.data?.detail || e.data?.message || '載入任務資料失敗，請回首頁重新開始。';
  } finally {
    isLoadingState.value = false;
  }
};

const answersFromAttempt = (payload?: Record<string, unknown> | null): TaskStudentAnswer[] => {
  const rawAnswers = Array.isArray(payload?.answers) ? payload.answers : [];
  return rawAnswers
    .filter((answer): answer is TaskStudentAnswer => {
      if (!answer || typeof answer !== 'object') return false;
      const item = answer as Partial<TaskStudentAnswer>;
      return Boolean(item.question_id && item.type && Object.prototype.hasOwnProperty.call(item, 'value'));
    })
    .map((answer) => ({
      question_id: answer.question_id,
      blank_id: answer.blank_id || answer.question_id,
      type: answer.type,
      prompt: answer.prompt || '',
      value: answer.value,
    }));
};

const scheduleDraftSave = () => {
  clearDraftTimer();
  draftSaveTimer.value = setTimeout(() => {
    void saveDraft();
  }, 700);
};

const clearDraftTimer = () => {
  if (!draftSaveTimer.value) return;
  clearTimeout(draftSaveTimer.value);
  draftSaveTimer.value = null;
};

const saveDraft = async () => {
  if (!taskData.value || !sessionId() || isSubmitting.value) return;
  const responsePayload = buildTaskResponsePayload(answers.value);
  const serialized = JSON.stringify(responsePayload);
  if (serialized === lastDraftPayload.value) return;

  try {
    await $fetch<TaskDraftResponse>(`/api/tasks/${taskData.value.task.id}/draft`, {
      method: 'PATCH',
      body: {
        session_id: taskData.value.session_id,
        user_id: participantUuid(participantId()),
        response_payload: responsePayload,
      },
    });
    lastDraftPayload.value = serialized;
    draftError.value = null;
  } catch (e: any) {
    const statusCode = e.statusCode || e.response?.status;
    if (statusCode === 409) return;
    draftError.value = e.data?.detail || e.data?.message || '草稿暫存失敗，請稍後再試。';
  }
};

const sessionId = () => {
  return typeof route.query.sessionId === 'string' && route.query.sessionId.trim()
    ? route.query.sessionId.trim()
    : '';
};

// participantId 目前從首頁 query 帶入；若缺漏就使用開發預設受測者。
const participantId = () => {
  return typeof route.query.participantId === 'string' && route.query.participantId.trim()
    ? route.query.participantId.trim()
    : 'scott-test';
};

</script>
