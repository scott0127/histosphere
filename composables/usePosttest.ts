import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import type { PosttestDraftInput, PosttestStateResponse } from '~/types';
import { advancePosttest, fetchPosttest, savePosttestDraft, startPosttest, submitPosttest } from '~/utils/histosphereApi';
import { isEngagementComplete, isHatComplete, posttestDraftPayload, posttestDraftSignature } from '~/utils/posttest';

export const usePosttest = (sessionId: string) => {
  const state = ref<PosttestStateResponse | null>(null);
  const engagement = ref<Record<string, number | null>>({});
  const hat = ref<Record<string, string>>({});
  const loading = ref(true);
  const saving = ref(false);
  const submitting = ref(false);
  const error = ref('');
  const conflict = ref(false);
  const dirty = ref(false);
  const localKey = `histosphere-posttest-draft:${sessionId}`;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let pendingSave: Promise<boolean> | null = null;
  let disposed = false;
  let savedSignature = '';
  let inFlightSignature: string | null = null;

  const response = computed(() => state.value?.response || null);
  const stage = computed(() => response.value?.stage || 'engagement');
  const completedCount = computed(() => stage.value === 'engagement'
    ? Object.values(engagement.value).filter((value) => value != null).length
    : Object.values(hat.value).filter((value) => value.trim()).length);
  const canContinue = computed(() => !!response.value && stage.value !== 'completed'
    && !loading.value && !submitting.value && !conflict.value
    && (stage.value === 'engagement' ? isEngagementComplete(engagement.value) : isHatComplete(hat.value)));

  const clearTimer = () => { if (timer) clearTimeout(timer); timer = null; };
  const clearBackup = () => { try { sessionStorage.removeItem(localKey); } catch { /* Server remains authoritative. */ } };
  const payload = () => response.value ? posttestDraftPayload(response.value, engagement.value, hat.value) : null;
  const backup = () => {
    const draft = payload();
    if (!draft || !dirty.value || conflict.value) return;
    try { sessionStorage.setItem(localKey, JSON.stringify({ stage: stage.value, base: savedSignature, pending: inFlightSignature, payload: draft })); }
    catch { /* Saving to the server still works when browser storage is disabled. */ }
  };
  const adopt = (next: PosttestStateResponse) => {
    state.value = next;
    engagement.value = { ...(next.response?.engagement_answers || {}) };
    hat.value = { ...(next.response?.hat_answers || {}) };
    savedSignature = next.response ? posttestDraftSignature(payload()!) : '';
    dirty.value = false;
  };
  const message = (e: any) => typeof e?.data?.detail === 'string' ? e.data.detail : '目前無法儲存，請確認連線後重試。';
  const handleFailure = (e: any) => {
    conflict.value = (e?.statusCode || e?.response?.status) === 409;
    error.value = conflict.value
      ? '這份作答已在其他分頁更新。請先複製需要保留的內容，再按「載入伺服器作答」。'
      : message(e);
    backup();
  };

  const save = async (): Promise<boolean> => {
    clearTimer();
    if (pendingSave) {
      if (!await pendingSave) return false;
      return dirty.value ? save() : true;
    }
    if (!dirty.value) return true;
    if (conflict.value || disposed || !response.value || stage.value === 'completed') return false;
    saving.value = true;
    error.value = '';
    pendingSave = (async () => {
      try {
        if (inFlightSignature) {
          // A failed acknowledgement can hide a successful save. Reconcile before retrying.
          const current = await fetchPosttest(sessionId);
          if (disposed) return false;
          if (!current.response || current.response.stage !== stage.value) throw { statusCode: 409 };
          const currentSignature = posttestDraftSignature(posttestDraftPayload(
            current.response, current.response.engagement_answers, current.response.hat_answers,
          ));
          if (currentSignature !== savedSignature && currentSignature !== inFlightSignature) throw { statusCode: 409 };
          state.value = current;
          savedSignature = currentSignature;
          inFlightSignature = null;
          dirty.value = posttestDraftSignature(payload()!) !== savedSignature;
          if (!dirty.value) { clearBackup(); return true; }
        }
        const sent = payload()!;
        const sentSignature = posttestDraftSignature(sent);
        inFlightSignature = sentSignature;
        backup();
        const next = await savePosttestDraft(sessionId, sent);
        if (disposed) return false;
        // Keep keystrokes made during the request; the next save uses the new revision.
        state.value = next;
        savedSignature = sentSignature;
        inFlightSignature = null;
        dirty.value = posttestDraftSignature(payload()!) !== savedSignature;
        if (dirty.value) backup(); else clearBackup();
        return true;
      } catch (e) {
        if (!disposed) handleFailure(e);
        return false;
      } finally {
        pendingSave = null;
        saving.value = false;
      }
    })();
    const saved = await pendingSave;
    if (saved && dirty.value && !disposed) return save();
    return saved;
  };

  const changed = () => {
    if (!response.value || submitting.value || stage.value === 'completed') return;
    dirty.value = posttestDraftSignature(payload()!) !== savedSignature;
    backup();
    clearTimer();
    if (dirty.value && !conflict.value) timer = setTimeout(() => void save(), 500);
    if (!dirty.value) clearBackup();
  };
  const updateEngagement = (answers: Record<string, number | null>) => { engagement.value = answers; changed(); };
  const updateHat = (answers: Record<string, string>) => { hat.value = answers; changed(); };

  const load = async (discardLocal = false) => {
    clearTimer();
    loading.value = true;
    error.value = '';
    conflict.value = false;
    try {
      await pendingSave;
      let next = await fetchPosttest(sessionId);
      if (next.eligible && !next.response) next = await startPosttest(sessionId);
      if (disposed) return;
      adopt(next);
      if (discardLocal || next.response?.stage === 'completed') clearBackup();
      if (next.response && next.response.stage !== 'completed' && !discardLocal) {
        let cached: { stage: string; base: string; pending?: string; payload: PosttestDraftInput } | null = null;
        try { cached = JSON.parse(sessionStorage.getItem(localKey) || 'null'); } catch { /* No recoverable browser draft. */ }
        if (cached?.stage === stage.value && cached.payload) {
          const localSignature = posttestDraftSignature(cached.payload);
          if (localSignature === savedSignature) clearBackup();
          else {
            if (cached.payload.engagement_answers) engagement.value = cached.payload.engagement_answers;
            if (cached.payload.hat_answers) hat.value = cached.payload.hat_answers;
            dirty.value = true;
            if (cached.base !== savedSignature && cached.pending !== savedSignature) handleFailure({ statusCode: 409 });
            else timer = setTimeout(() => void save(), 0);
          }
        } else clearBackup();
      }
    } catch (e) { error.value = message(e); }
    finally { loading.value = false; }
  };

  const continueStage = async () => {
    if (!canContinue.value) return;
    submitting.value = true;
    error.value = '';
    try {
      if (!await save() || !response.value) return;
      const next = stage.value === 'engagement'
        ? await advancePosttest(sessionId, response.value.revision)
        : await submitPosttest(sessionId, response.value.revision);
      adopt(next);
      clearBackup();
    } catch (e) { handleFailure(e); }
    finally { submitting.value = false; }
  };
  const beforeUnload = (event: BeforeUnloadEvent) => {
    if (dirty.value || saving.value || submitting.value) {
      backup(); event.preventDefault(); event.returnValue = '';
    }
  };
  const online = () => { if (dirty.value && !conflict.value) void save(); };
  onMounted(() => {
    window.addEventListener('beforeunload', beforeUnload);
    window.addEventListener('online', online);
    void load();
  });
  onBeforeUnmount(() => {
    backup(); disposed = true; clearTimer();
    window.removeEventListener('beforeunload', beforeUnload);
    window.removeEventListener('online', online);
  });

  return { state, response, engagement, hat, loading, saving, submitting, error, conflict, dirty,
    stage, completedCount, canContinue, updateEngagement, updateHat, load, save, continueStage };
};
