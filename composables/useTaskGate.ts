// useTaskGate 集中管理前置任務的 session reload、draft autosave 與 submit flow。
// Page 只提供 route params/query；TaskStudentGate 只負責畫面。
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import type { ComputedRef, Ref } from 'vue';
import type {
  EventInitializeResponse,
  SessionStateResponse,
  TaskStudentAnswer,
  TaskSubmitResponse,
} from '~/types';
import {
  buildTaskResponsePayload,
  isTaskAnswerComplete,
  markStudentConditionProgress,
  normalizeTaskQuestions,
  participantUuid,
} from '~/composables/useStudentTask';
import {
  fetchSessionState,
  saveTaskDraft,
  submitTaskAnswers,
} from '~/utils/histosphereApi';

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

export const useTaskGate = (
  sessionId: Ref<string> | ComputedRef<string>,
  participantId: Ref<string> | ComputedRef<string>,
) => {
  const taskData = useState<EventInitializeResponse | null>('taskData', () => null);
  const answers = ref<TaskStudentAnswer[]>([]);
  const isSubmitting = ref(false);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const draftError = ref<string | null>(null);
  const draftSaveTimer = ref<ReturnType<typeof setTimeout> | null>(null);
  const lastDraftPayload = ref<string | null>(null);
  const judgement = ref<Record<string, any> | null>(null);

  const taskQuestions = computed(() => taskData.value ? normalizeTaskQuestions(taskData.value.task) : []);
  const canSubmit = computed(() => isTaskAnswerComplete(taskQuestions.value, answers.value));
  const submitError = computed(() => error.value || draftError.value);

  onMounted(async () => {
    if (sessionId.value) {
      await loadSessionState(sessionId.value);
    }
  });

  watch(
    answers,
    () => {
      if (!taskData.value || !sessionId.value || isSubmitting.value || answers.value.length === 0) return;
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
      const response: TaskSubmitResponse = await submitTaskAnswers(taskData.value.task.id, {
        sessionId: taskData.value.session_id,
        userId: participantUuid(participantId.value),
        responsePayload: buildTaskResponsePayload(answers.value),
      });
      judgement.value = response.judgement;
      markStudentConditionProgress(participantId.value, response);

      const chatData = useState<TaskSubmitResponse | null>('chatData', () => null);
      chatData.value = response;
      await navigateTo({
        path: `/conversations/${response.conversation_id}`,
      });
    } catch (e: any) {
      error.value = e.data?.detail || e.data?.message || '送出失敗，請稍後再試。';
    } finally {
      isSubmitting.value = false;
    }
  };

  // 以後端 session state 為準：已建立 conversation 就直接導往 conversation route。
  const loadSessionState = async (routeSessionId: string) => {
    isLoading.value = true;
    error.value = null;
    try {
      const state: SessionStateResponse = await fetchSessionState(routeSessionId);
      if (state.conversation_id) {
        await navigateTo({
          path: `/conversations/${state.conversation_id}`,
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
      isLoading.value = false;
    }
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
    if (!taskData.value || !sessionId.value || isSubmitting.value) return;
    const responsePayload = buildTaskResponsePayload(answers.value);
    const serialized = JSON.stringify(responsePayload);
    if (serialized === lastDraftPayload.value) return;

    try {
      await saveTaskDraft(taskData.value.task.id, {
        sessionId: taskData.value.session_id,
        userId: participantUuid(participantId.value),
        responsePayload,
      });
      lastDraftPayload.value = serialized;
      draftError.value = null;
    } catch (e: any) {
      const statusCode = e.statusCode || e.response?.status;
      if (statusCode === 409) return;
      draftError.value = e.data?.detail || e.data?.message || '草稿暫存失敗，請稍後再試。';
    }
  };

  return {
    answers,
    canSubmit,
    isLoading,
    isSubmitting,
    judgement,
    submitError,
    submitTask,
    taskData,
  };
};
