// useTaskGate 集中管理 Error-Elicitation Task 的 session reload、draft autosave 與 submit flow。
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
  normalizeTaskQuestions,
  restoreTaskAnswers,
} from '~/composables/useStudentTask';
import {
  fetchSessionState,
  fetchTaskSubmissionStatus,
  saveTaskDraft,
  submitTaskAnswers,
} from '~/utils/histosphereApi';

export const useTaskGate = (
  sessionId: Ref<string> | ComputedRef<string>,
  authUserId?: Ref<string | null> | ComputedRef<string | null>,
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
  const session = ref<SessionStateResponse['session'] | null>(null);
  const isUnmounted = ref(false);
  let draftSavePromise: Promise<void> | null = null;
  let pendingDraftPayload: string | null = null;
  let loadVersion = 0;

  const localDraftKey = (data: Pick<EventInitializeResponse, 'session_id' | 'task'>) => `histosphere-task-draft:${data.session_id}:${data.task.id}`;
  const clearLocalDraft = (key: string) => {
    try { window.sessionStorage.removeItem(key); } catch { /* 本機儲存不可用時，仍以後端紀錄為準。 */ }
  };
  const readLocalDraft = (key: string) => {
    try {
      const draft = JSON.parse(window.sessionStorage.getItem(key) || 'null');
      return draft && typeof draft.basePayload === 'string' && Array.isArray(draft.responsePayload?.answers)
        ? draft as { basePayload: string; pendingPayload?: string; responsePayload: Record<string, unknown> } : null;
    } catch {
      return null;
    }
  };
  const persistLocalDraft = () => {
    if (!taskData.value || lastDraftPayload.value === null) return;
    const key = localDraftKey(taskData.value);
    const responsePayload = buildTaskResponsePayload(answers.value, taskData.value.task);
    const serialized = JSON.stringify(responsePayload);
    if (serialized === lastDraftPayload.value && (!pendingDraftPayload || pendingDraftPayload === serialized)) {
      clearLocalDraft(key);
      return;
    }
    try {
      window.sessionStorage.setItem(key, JSON.stringify({ basePayload: lastDraftPayload.value, pendingPayload: pendingDraftPayload, responsePayload }));
    } catch { /* 瀏覽器儲存停用或額滿，不中斷後端自動暫存。 */ }
  };

  const taskQuestions = computed(() => taskData.value ? normalizeTaskQuestions(taskData.value.task) : []);
  const canSubmit = computed(() => !isLoading.value && !isSubmitting.value
    && taskData.value?.session_id === sessionId.value
    && isTaskAnswerComplete(taskQuestions.value, answers.value, taskData.value?.task));
  const submitError = computed(() => error.value || draftError.value);
  // Learner 身分由 Authorization JWT 決定；只有 Admin test mode 會明確傳入測試 user id。
  const userIdForRequest = computed(() => authUserId?.value || null);

  onMounted(async () => {
    if (sessionId.value) {
      await loadSessionState(sessionId.value);
    }
  });

  watch(sessionId, (id) => { void loadSessionState(id); });

  watch(
    answers,
    () => {
      if (!taskData.value || taskData.value.session_id !== sessionId.value || isLoading.value || isSubmitting.value) return;
      persistLocalDraft();
      scheduleDraftSave();
    },
    { deep: true, flush: 'sync' },
  );

  onBeforeUnmount(() => {
    isUnmounted.value = true;
    clearDraftTimer();
  });

  const submitTask = async () => {
    if (!taskData.value || !canSubmit.value) return;
    const data = taskData.value;
    clearDraftTimer();
    persistLocalDraft();
    isSubmitting.value = true;
    error.value = null;
    draftError.value = null;
    try {
      await draftSavePromise;
      if (isUnmounted.value || sessionId.value !== data.session_id) return;
      const accepted = await submitTaskAnswers(data.task.id, {
        sessionId: data.session_id,
        userId: userIdForRequest.value,
        responsePayload: buildTaskResponsePayload(answers.value, data.task),
      });
      const response = await waitForSubmission(accepted.attempt_id, data.session_id);
      if (!isUnmounted.value && sessionId.value === data.session_id) await finishSubmission(response);
    } catch (e: any) {
      if (!isUnmounted.value && sessionId.value === data.session_id) {
        error.value = e.data?.detail || e.data?.message || e.message || '送出失敗，請稍後再試。';
      }
    } finally {
      if (sessionId.value === data.session_id) isSubmitting.value = false;
    }
  };

  // 以後端 session state 為準：已建立 conversation 就直接導往 conversation route。
  const loadSessionState = async (routeSessionId: string) => {
    const version = ++loadVersion;
    clearDraftTimer();
    isLoading.value = true;
    error.value = null;
    draftError.value = null;
    try {
      await draftSavePromise;
      if (isUnmounted.value || version !== loadVersion) return;
      isSubmitting.value = false;
      taskData.value = null;
      session.value = null;
      judgement.value = null;
      answers.value = [];
      lastDraftPayload.value = null;
      pendingDraftPayload = null;
      if (!routeSessionId) return;
      const state: SessionStateResponse = await fetchSessionState(routeSessionId);
      if (isUnmounted.value || version !== loadVersion) return;
      session.value = state.session;
      if (state.conversation_id) {
        if (state.task) clearLocalDraft(localDraftKey({ session_id: state.session.id, task: state.task }));
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
      answers.value = restoreTaskAnswers(state.task, state.attempt?.response_payload);
      lastDraftPayload.value = JSON.stringify(buildTaskResponsePayload(answers.value, state.task));
      const key = localDraftKey(taskData.value);
      const localDraft = readLocalDraft(key);
      // 僅在後端仍是本機編輯的基底版本時補回未同步內容，避免覆蓋較新的作答。
      if (localDraft && (localDraft.basePayload === lastDraftPayload.value || localDraft.pendingPayload === lastDraftPayload.value)
        && state.attempt?.status !== 'processing' && state.attempt?.status !== 'submitted') {
        answers.value = restoreTaskAnswers(state.task, localDraft.responsePayload);
      } else {
        clearLocalDraft(key);
      }
      if (state.attempt?.status === 'processing') {
        isSubmitting.value = true;
        try {
          const response = await waitForSubmission(state.attempt.id, routeSessionId);
          if (!isUnmounted.value && version === loadVersion) await finishSubmission(response);
        } catch (e: any) {
          if (!isUnmounted.value && version === loadVersion) {
            error.value = e.data?.detail || e.data?.message || e.message || '任務處理失敗，請重新送出。';
          }
        } finally {
          if (version === loadVersion) isSubmitting.value = false;
        }
      } else if (state.attempt?.status === 'failed') {
        error.value = String(state.attempt.judgement_payload?.error || '上次處理失敗，請重新送出。');
      }
    } catch (e: any) {
      if (!isUnmounted.value && version === loadVersion) {
        error.value = e.data?.detail || e.data?.message || '載入任務資料失敗，請回首頁重新開始。';
      }
    } finally {
      if (!isUnmounted.value && version === loadVersion) {
        isLoading.value = false;
        if (taskData.value && JSON.stringify(buildTaskResponsePayload(answers.value, taskData.value.task)) !== lastDraftPayload.value) {
          persistLocalDraft();
          scheduleDraftSave();
        }
      }
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
    if (!taskData.value || taskData.value.session_id !== sessionId.value || isSubmitting.value || isLoading.value || isUnmounted.value) return;
    if (draftSavePromise) return draftSavePromise;
    const data = taskData.value;
    const responsePayload = buildTaskResponsePayload(answers.value, data.task);
    const serialized = JSON.stringify(responsePayload);
    if (serialized === lastDraftPayload.value) return;
    // 記錄送出中的版本，涵蓋後端已保存、前端尚未收到回應就重新整理的情況。
    pendingDraftPayload = serialized;
    persistLocalDraft();

    draftSavePromise = Promise.resolve().then(async () => {
      let saved = false;
      try {
        await saveTaskDraft(data.task.id, {
          sessionId: data.session_id,
          userId: userIdForRequest.value,
          responsePayload,
        });
        lastDraftPayload.value = serialized;
        pendingDraftPayload = null;
        draftError.value = null;
        saved = true;
        persistLocalDraft();
      } catch (e: any) {
        const statusCode = e.statusCode || e.response?.status;
        if (statusCode === 409) return;
        draftError.value = e.data?.detail || e.data?.message || '草稿暫存失敗，請稍後再試。';
      } finally {
        draftSavePromise = null;
        if (saved && !isUnmounted.value && !isLoading.value && !isSubmitting.value
          && JSON.stringify(buildTaskResponsePayload(answers.value, data.task)) !== serialized) scheduleDraftSave();
      }
    });
    return draftSavePromise;
  };

  const waitForSubmission = async (attemptId: string, expectedSessionId: string): Promise<TaskSubmitResponse> => {
    const deadline = Date.now() + 4 * 60 * 1000;
    while (!isUnmounted.value && sessionId.value === expectedSessionId && Date.now() < deadline) {
      const state = await fetchTaskSubmissionStatus(attemptId);
      if (state.attempt.status === 'failed') {
        throw new Error(state.error || 'Task processing failed.');
      }
      if (state.attempt.status === 'submitted' && state.result) {
        return state.result;
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    throw new Error('任務仍在處理中，請重新整理頁面繼續等待。');
  };

  const finishSubmission = async (response: TaskSubmitResponse) => {
    if (taskData.value) clearLocalDraft(localDraftKey(taskData.value));
    judgement.value = response.judgement;
    const chatData = useState<TaskSubmitResponse | null>('chatData', () => null);
    chatData.value = response;
    await navigateTo({ path: `/conversations/${response.conversation_id}` });
  };

  return {
    answers,
    canSubmit,
    isLoading,
    isSubmitting,
    judgement,
    session,
    submitError,
    submitTask,
    taskData,
  };
};
