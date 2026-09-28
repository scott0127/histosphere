import { computed, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue';
import { clearAdminSessionKey, getAdminSessionKey, setAdminSessionKey } from '~/utils/adminSession';
import { approveAdminTaskReview, fetchAdminMonitor, retryAdminTaskProcessing, saveAdminTaskReview } from '~/utils/taskReviewApi';
import { initialReviewDrafts, reviewQuestionError, reviewQuestionRows } from '~/utils/taskReview';
import { subscribeSessionEvents } from '~/utils/sessionEventStream';
import type { AdminMonitorSnapshot, TaskReviewAttempt, TaskReviewQuestion } from '~/types/taskReview';

const errorMessage = (error: any, fallback: string) => {
  const detail = error?.data?.detail || error?.data?.message;
  if (detail === 'Review changed in another window; reload before saving') return '其他分頁已更新審核，請重新載入後再保存。';
  if (detail === 'Task is not awaiting human review') return '此活動已不在待審階段，請重新同步。';
  if (detail === 'Invalid admin key') return '管理員密碼不正確，請重新輸入。';
  return typeof detail === 'string' ? detail : fallback;
};

export const useAdminMonitor = (sessionId: Ref<string>) => {
  const adminKey = ref('');
  const snapshot = ref<AdminMonitorSnapshot | null>(null);
  const drafts = ref<TaskReviewQuestion[]>([]);
  const loadedVersion = ref(0);
  const savedSignature = ref('[]');
  const loading = ref(false);
  const saving = ref(false);
  const connected = ref(false);
  const error = ref('');
  const syncError = ref('');
  const notice = ref('');
  const lastSyncedAt = ref<string | null>(null);
  const serverClockOffsetMs = ref(0);
  const dirty = computed(() => JSON.stringify(drafts.value) !== savedSignature.value);
  const conflict = computed(() => Boolean(snapshot.value?.attempt
    && snapshot.value.attempt.review_version !== loadedVersion.value && dirty.value));
  const questions = computed(() => snapshot.value ? reviewQuestionRows(snapshot.value) : []);
  const editable = computed(() => snapshot.value?.attempt?.status === 'awaiting_review');
  const reviewedCount = computed(() => drafts.value.filter(question => question.reviewed).length);
  const canApprove = computed(() => editable.value && !saving.value && !dirty.value && !conflict.value
    && questions.value.length > 0 && drafts.value.length === questions.value.length
    && questions.value.every(row => {
      const draft = drafts.value.find(item => item.question_id === row.question.id);
      return Boolean(draft?.reviewed && !reviewQuestionError(row, draft));
    }));
  let stopEvents: (() => void) | null = null;
  let requestVersion = 0;
  let disposed = false;
  let refreshPromise: Promise<void> | null = null;
  let refreshAgain = false;

  const restoreDrafts = () => {
    if (!snapshot.value) return;
    drafts.value = initialReviewDrafts(snapshot.value);
    loadedVersion.value = snapshot.value.attempt?.review_version || 0;
    savedSignature.value = JSON.stringify(drafts.value);
  };

  const stop = () => { stopEvents?.(); stopEvents = null; connected.value = false; };

  const refresh = async (): Promise<void> => {
    if (!adminKey.value.trim() || !sessionId.value || disposed) return;
    if (refreshPromise) { refreshAgain = true; return refreshPromise; }
    const version = requestVersion;
    const key = adminKey.value.trim();
    const id = sessionId.value;
    refreshPromise = (async () => {
      try {
        const result = await fetchAdminMonitor(key, id);
        if (disposed || version !== requestVersion || sessionId.value !== id || adminKey.value.trim() !== key) return;
        const previousAttempt = snapshot.value?.attempt?.id;
        const serverTime = Date.parse(result.server_now || '');
        serverClockOffsetMs.value = Number.isFinite(serverTime) ? serverTime - Date.now() : 0;
        snapshot.value = result;
        if (!saving.value && (!dirty.value || previousAttempt !== result.attempt?.id)) restoreDrafts();
        lastSyncedAt.value = new Date().toISOString();
        setAdminSessionKey(key);
        syncError.value = '';
      } catch (cause: any) {
        if (disposed || version !== requestVersion || adminKey.value.trim() !== key) return;
        if ([401, 403].includes(cause?.statusCode || cause?.response?.status)) {
          stop();
          snapshot.value = null;
          drafts.value = [];
          savedSignature.value = '[]';
          clearAdminSessionKey();
        }
        syncError.value = errorMessage(cause, '無法同步施測資料，請確認連線後重試。');
      } finally {
        refreshPromise = null;
        if (refreshAgain && !disposed) { refreshAgain = false; void refresh(); }
      }
    })();
    return refreshPromise;
  };

  const connect = async () => {
    if (!sessionId.value) { error.value = '請從研究管理選擇要監測的活動紀錄。'; return; }
    if (!adminKey.value.trim()) { error.value = '請輸入管理員密碼。'; return; }
    stop();
    loading.value = true;
    error.value = '';
    syncError.value = '';
    await refresh();
    loading.value = false;
    if (!snapshot.value || disposed) return;
    stopEvents = subscribeSessionEvents({
      url: `/api/admin/monitor/sessions/${encodeURIComponent(sessionId.value)}/events`,
      headers: () => ({ 'x-admin-key': adminKey.value.trim() }),
      onChange: () => { void refresh(); },
      onConnectionChange: value => { connected.value = value; },
    });
  };

  const updateQuestion = (questionId: string, patch: Partial<TaskReviewQuestion>) => {
    if (!editable.value || saving.value) return;
    drafts.value = drafts.value.map(draft => draft.question_id === questionId
      ? { ...draft, ...patch, question_id: questionId, reviewed: false } : draft);
    notice.value = '';
  };

  const applyAttempt = (attempt: TaskReviewAttempt) => {
    if (!snapshot.value) return;
    snapshot.value = { ...snapshot.value, attempt };
    restoreDrafts();
  };

  const saveQuestion = async (questionId: string, confirm = true) => {
    const attempt = snapshot.value?.attempt;
    if (!attempt || !editable.value || saving.value || conflict.value) return;
    const row = questions.value.find(item => item.question.id === questionId);
    const draft = drafts.value.find(item => item.question_id === questionId);
    if (!row || !draft) return;
    const validation = confirm ? reviewQuestionError(row, draft) : null;
    if (validation) { error.value = validation; return; }
    const payload = drafts.value.map(item => ({ ...item, ...(item.question_id === questionId ? { reviewed: confirm } : {}) }));
    saving.value = true;
    error.value = '';
    try {
      applyAttempt(await saveAdminTaskReview(adminKey.value, attempt.id, loadedVersion.value, payload));
      notice.value = confirm ? '此題已核對並保存。' : '審核草稿已保存，尚未確認此題。';
    } catch (cause) {
      error.value = errorMessage(cause, '審核未保存，請保留目前內容並重試。');
    } finally { saving.value = false; }
    await refresh();
  };

  const approve = async () => {
    const attempt = snapshot.value?.attempt;
    if (!attempt || !canApprove.value) return;
    saving.value = true;
    error.value = '';
    try {
      applyAttempt(await approveAdminTaskReview(adminKey.value, attempt.id, loadedVersion.value));
      notice.value = '最終結果已確認。';
    } catch (cause) { error.value = errorMessage(cause, '無法確認最終結果，請重試。'); }
    finally { saving.value = false; }
    await refresh();
  };

  const retry = async () => {
    const attempt = snapshot.value?.attempt;
    if (!attempt || saving.value) return;
    saving.value = true;
    error.value = '';
    try { await retryAdminTaskProcessing(adminKey.value, attempt.id); notice.value = '已重新開始處理。'; }
    catch (cause) { error.value = errorMessage(cause, '無法重新處理，請稍後重試。'); }
    finally { saving.value = false; }
    await refresh();
  };

  const logout = () => {
    requestVersion += 1;
    stop();
    clearAdminSessionKey();
    snapshot.value = null;
    drafts.value = [];
    savedSignature.value = '[]';
    adminKey.value = '';
  };
  const beforeUnload = (event: BeforeUnloadEvent) => {
    if (!dirty.value) return;
    event.preventDefault();
    event.returnValue = '';
  };

  onMounted(() => {
    adminKey.value = getAdminSessionKey();
    if (adminKey.value && sessionId.value) void connect();
    window.addEventListener('beforeunload', beforeUnload);
  });
  watch(sessionId, () => {
    requestVersion += 1;
    stop();
    snapshot.value = null;
    drafts.value = [];
    savedSignature.value = '[]';
    if (adminKey.value) void connect();
  });
  onBeforeUnmount(() => {
    disposed = true;
    requestVersion += 1;
    stop();
    window.removeEventListener('beforeunload', beforeUnload);
  });

  return { adminKey, snapshot, drafts, questions, editable, loading, saving, connected, error: computed(() => error.value || syncError.value), notice, lastSyncedAt, serverClockOffsetMs,
    dirty, conflict, reviewedCount, canApprove, connect, refresh, updateQuestion, saveQuestion, approve, retry, logout, restoreDrafts };
};
