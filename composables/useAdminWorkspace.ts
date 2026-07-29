// useAdminWorkspace 管理 admin 頁的 snapshot 載入、JSON 編輯狀態與保存流程。
// Page 保留登入畫面與折疊 UI；這裡負責 admin API 的狀態一致性。
import { computed, ref, watch } from 'vue';
import { taskControlQuestions } from '~/composables/useTaskControl';
import type {
  AdminPromptPreviewResponse,
  AdminPromptDryRunResponse,
  AdminSnapshotResponse,
  AdminAuthUserSummary,
  EventTask,
  EventWithPersonas,
  ExperimentCondition,
  Participant,
  Persona,
} from '~/types';
import {
  buildAdminEditableJson,
  conditionModeLabel,
  conditionOrdinal,
  eventYearRange,
  sortPromptConditions,
  taskAuthoringSignature,
} from '~/utils/adminWorkspaceState';
import {
  clearAdminSessionKey,
  getAdminSessionKey,
  setAdminSessionKey,
} from '~/utils/adminSession';
import {
  archiveAdminEvent,
  archiveAdminPersona,
  archiveAdminParticipant,
  createAdminPersona,
  createAdminParticipant,
  fetchAdminAuthUsers,
  fetchAdminSnapshot,
  fetchAdminPromptPreview,
  restoreAdminEvent,
  restoreAdminPersona,
  restoreAdminParticipant,
  restartAdminSession,
  runAdminPromptDryRun,
  resetAdminSessionTimer,
  updateAdminCondition,
  updateAdminEvent,
  updateAdminParticipant,
  updateAdminPersona,
  updateAdminTask,
  type ParticipantCreateInput,
  type ParticipantUpdateInput,
} from '~/utils/histosphereApi';

export const useAdminWorkspace = () => {
  const adminKey = ref('');
  const snapshot = ref<AdminSnapshotResponse | null>(null);
  const authUsers = ref<AdminAuthUserSummary[]>([]);
  const error = ref<string | null>(null);
  const authUsersError = ref<string | null>(null);
  const taskJson = ref<Record<string, string>>({});
  const taskBaselines = ref<Record<string, string>>({});
  const personaJson = ref<Record<string, string>>({});
  const selectedConditionId = ref<string | null>(null);
  const selectedEventId = ref<string | null>(null);
  const creatingParticipant = ref(false);
  const creatingPersona = ref(false);
  const changingParticipantStatusId = ref<string | null>(null);
  const changingPersonaStatusId = ref<string | null>(null);
  const savingParticipantId = ref<string | null>(null);
  const savingPersonaId = ref<string | null>(null);
  const savingTaskId = ref<string | null>(null);
  const updatingTimerSessionId = ref<string | null>(null);
  const restartingSessionId = ref<string | null>(null);
  const promptPreview = ref<AdminPromptPreviewResponse | null>(null);
  const promptDryRun = ref<AdminPromptDryRunResponse | null>(null);
  const promptDryRunLoading = ref(false);
  const promptPreviewLoading = ref(false);
  const promptPreviewMessage = ref('請說明這個事件的重要性。');

  const selectedEvent = computed<EventWithPersonas | null>(() => {
    if (!snapshot.value || !selectedEventId.value) return null;
    return snapshot.value.events.find((event) => event.id === selectedEventId.value) || null;
  });

  const promptConditions = computed(() => sortPromptConditions(snapshot.value?.conditions || []));

  const selectedCondition = computed<ExperimentCondition | null>(() => {
    const conditions = promptConditions.value;
    if (!conditions.length) return null;
    return conditions.find((condition) => condition.id === selectedConditionId.value) || conditions[0] || null;
  });

  const isTaskDirty = (task?: EventTask | null) => {
    if (!task) return false;
    const evaluationJson = taskJson.value[task.id] || '{}';
    return taskAuthoringSignature(task, evaluationJson) !== taskBaselines.value[task.id];
  };

  const hasUnsavedTaskChanges = computed(() => {
    return Boolean(snapshot.value?.events.some((event) => isTaskDirty(event.latest_task)));
  });

  watch([selectedEventId, selectedConditionId, promptPreviewMessage], () => {
    promptPreview.value = null;
    promptDryRun.value = null;
  });

  const resetWorkspace = (clearStoredKey = true) => {
    adminKey.value = '';
    snapshot.value = null;
    authUsers.value = [];
    error.value = null;
    authUsersError.value = null;
    taskJson.value = {};
    taskBaselines.value = {};
    personaJson.value = {};
    creatingPersona.value = false;
    changingPersonaStatusId.value = null;
    savingPersonaId.value = null;
    promptPreview.value = null;
    promptDryRun.value = null;
    selectedConditionId.value = null;
    selectedEventId.value = null;
    if (clearStoredKey) {
      clearAdminSessionKey();
    }
  };

  const restoreStoredAdminKey = () => {
    if (!import.meta.client) return;
    adminKey.value = getAdminSessionKey();
  };

  const loadAuthUsers = async () => {
    authUsersError.value = null;
    try {
      const response = await fetchAdminAuthUsers(adminKey.value);
      authUsers.value = response.users || [];
    } catch (e: any) {
      authUsers.value = [];
      authUsersError.value = formatAdminApiError(e, 'Auth users 載入失敗。');
    }
  };

  type TaskDraftSnapshot = {
    title: string | null | undefined;
    storyText: string;
    displayText: string;
    evaluationJson: string;
  };

  const captureUnsavedTaskDrafts = (exceptTaskId?: string) => {
    const drafts: Record<string, TaskDraftSnapshot> = {};
    for (const event of snapshot.value?.events || []) {
      const task = event.latest_task;
      if (!task || task.id === exceptTaskId || !isTaskDirty(task)) continue;
      drafts[task.id] = {
        title: task.title,
        storyText: task.story_text,
        displayText: task.display_text,
        evaluationJson: taskJson.value[task.id] || '{}',
      };
    }
    return drafts;
  };

  const loadSnapshot = async (options: {
    preserveUnsavedTaskDrafts?: boolean;
    exceptTaskId?: string;
  } = {}) => {
    error.value = null;
    const drafts = options.preserveUnsavedTaskDrafts
      ? captureUnsavedTaskDrafts(options.exceptTaskId)
      : {};
    try {
      const data = await fetchAdminSnapshot(adminKey.value);
      setAdminSessionKey(adminKey.value);
      const editable = buildAdminEditableJson(data);
      const nextBaselines: Record<string, string> = {};

      for (const event of data.events) {
        const task = event.latest_task;
        if (!task) continue;
        const serverEvaluationJson = editable.taskJson[task.id] || '{}';
        nextBaselines[task.id] = taskAuthoringSignature(task, serverEvaluationJson);
        const draft = drafts[task.id];
        if (!draft) continue;
        task.title = draft.title;
        task.story_text = draft.storyText;
        task.display_text = draft.displayText;
        editable.taskJson[task.id] = draft.evaluationJson;
      }

      taskJson.value = editable.taskJson;
      taskBaselines.value = nextBaselines;
      personaJson.value = editable.personaJson;
      snapshot.value = data;

      if (selectedEventId.value && !data.events.some((event) => event.id === selectedEventId.value)) {
        selectedEventId.value = null;
      }
      if (!selectedConditionId.value || !data.conditions.some((condition) => condition.id === selectedConditionId.value)) {
        selectedConditionId.value = sortPromptConditions(data.conditions)[0]?.id || null;
      }
      await loadAuthUsers();
      return true;
    } catch (e: any) {
      clearAdminSessionKey();
      error.value = formatAdminApiError(e, '後台資料載入失敗，請確認 admin key。');
      return false;
    }
  };

  const taskQuestionCount = (task?: EventTask | null) => {
    if (!task) return 0;
    const evaluationJson = taskJson.value[task.id] || JSON.stringify(task.evaluation_payload || {}, null, 2);
    return taskControlQuestions(task, evaluationJson).length;
  };

  const saveCondition = async (condition: ExperimentCondition) => {
    try {
      await updateAdminCondition(adminKey.value, condition.id, {
        label: condition.label,
        ebl_enabled: condition.ebl_enabled,
        roleplay_enabled: condition.roleplay_enabled,
        agent_mode: condition.roleplay_enabled ? 'persona' : 'generic',
        response_policy: condition.response_policy,
        description: condition.description,
        active: condition.active,
      });
      await loadSnapshot({ preserveUnsavedTaskDrafts: true });
    } catch (e: any) {
      error.value = formatAdminApiError(e, 'Condition 儲存失敗。');
    }
  };

  const saveTask = async (task: EventTask) => {
    let evaluationPayload = {};
    try {
      evaluationPayload = JSON.parse(taskJson.value[task.id] || '{}');
    } catch {
      error.value = `Task ${task.id} 的 evaluation_payload 不是合法 JSON。`;
      return;
    }
    savingTaskId.value = task.id;
    error.value = null;
    try {
      await updateAdminTask(adminKey.value, task.id, {
        title: task.title,
        story_text: task.story_text,
        display_text: task.display_text,
        evaluation_payload: evaluationPayload,
        revision_state: 'teacher_modified',
      });
      await loadSnapshot({
        preserveUnsavedTaskDrafts: true,
        exceptTaskId: task.id,
      });
    } catch (e: any) {
      error.value = formatAdminApiError(e, 'Task 儲存失敗。');
    } finally {
      savingTaskId.value = null;
    }
  };

  const saveEvent = async (event: EventWithPersonas) => {
    try {
      await updateAdminEvent(adminKey.value, event.id, {
        canonical_name: event.canonical_name,
        description: event.description,
        century: event.century,
        start_year: event.start_year,
        end_year: event.end_year,
        context: event.context,
        source_summary: event.source_summary || {},
      });
      await loadSnapshot({ preserveUnsavedTaskDrafts: true });
    } catch (e: any) {
      error.value = formatAdminApiError(e, '事件資料儲存失敗。');
    }
  };

  const setEventArchived = async (event: EventWithPersonas, archived: boolean) => {
    try {
      if (archived) {
        await archiveAdminEvent(adminKey.value, event.id);
      } else {
        await restoreAdminEvent(adminKey.value, event.id);
      }
      await loadSnapshot({ preserveUnsavedTaskDrafts: true });
    } catch (e: any) {
      error.value = formatAdminApiError(e, archived ? '事件封存失敗。' : '事件恢復失敗。');
    }
  };

  const savePersona = async (persona: Persona) => {
    let promptProfile = {};
    try {
      promptProfile = JSON.parse(personaJson.value[persona.id] || '{}');
    } catch {
      error.value = `Persona ${persona.name} 的 prompt_profile 不是合法 JSON。`;
      return;
    }
    savingPersonaId.value = persona.id;
    error.value = null;
    try {
      await updateAdminPersona(adminKey.value, persona.id, {
        name: persona.name,
        role: persona.role,
        biography: persona.biography,
        avatar_url: persona.avatar_url,
        prompt_profile: promptProfile,
        active: persona.active,
        revision_state: 'teacher_modified',
      });
      await loadSnapshot({ preserveUnsavedTaskDrafts: true });
    } catch (e: any) {
      error.value = formatAdminApiError(e, '人物資料儲存失敗。');
    } finally {
      savingPersonaId.value = null;
    }
  };

  const createPersona = async (eventId: string) => {
    creatingPersona.value = true;
    error.value = null;
    try {
      await createAdminPersona(adminKey.value, {
        event_id: eventId,
        name: '新歷史人物',
        active: false,
        revision_state: 'manual',
      });
      await loadSnapshot({ preserveUnsavedTaskDrafts: true });
    } catch (e: any) {
      error.value = formatAdminApiError(e, '人物建立失敗。');
    } finally {
      creatingPersona.value = false;
    }
  };

  const setPersonaActive = async (persona: Persona, active: boolean) => {
    changingPersonaStatusId.value = persona.id;
    error.value = null;
    try {
      await updateAdminPersona(adminKey.value, persona.id, { active });
      await loadSnapshot({ preserveUnsavedTaskDrafts: true });
    } catch (e: any) {
      error.value = formatAdminApiError(e, active ? '人物啟用失敗。' : '人物停用失敗。');
    } finally {
      changingPersonaStatusId.value = null;
    }
  };

  const archivePersona = async (persona: Persona) => {
    changingPersonaStatusId.value = persona.id;
    error.value = null;
    try {
      await archiveAdminPersona(adminKey.value, persona.id);
      await loadSnapshot({ preserveUnsavedTaskDrafts: true });
    } catch (e: any) {
      error.value = formatAdminApiError(e, '人物封存失敗。');
    } finally {
      changingPersonaStatusId.value = null;
    }
  };

  const restorePersona = async (persona: Persona) => {
    changingPersonaStatusId.value = persona.id;
    error.value = null;
    try {
      await restoreAdminPersona(adminKey.value, persona.id);
      await loadSnapshot({ preserveUnsavedTaskDrafts: true });
    } catch (e: any) {
      error.value = formatAdminApiError(e, '人物恢復失敗。');
    } finally {
      changingPersonaStatusId.value = null;
    }
  };

  const saveParticipant = async (participantId: string, body: ParticipantUpdateInput) => {
    savingParticipantId.value = participantId;
    error.value = null;
    try {
      await updateAdminParticipant(adminKey.value, participantId, body);
      await loadSnapshot({ preserveUnsavedTaskDrafts: true });
    } catch (e: any) {
      error.value = formatAdminApiError(e, '受測者資料儲存失敗。');
    } finally {
      savingParticipantId.value = null;
    }
  };

  const createParticipant = async (body: ParticipantCreateInput) => {
    creatingParticipant.value = true;
    error.value = null;
    try {
      await createAdminParticipant(adminKey.value, body);
      await loadSnapshot({ preserveUnsavedTaskDrafts: true });
    } catch (e: any) {
      error.value = formatAdminApiError(e, '受測者建立失敗。');
    } finally {
      creatingParticipant.value = false;
    }
  };

  const setParticipantArchived = async (participant: Participant, archived: boolean) => {
    changingParticipantStatusId.value = participant.id;
    error.value = null;
    try {
      if (archived) {
        await archiveAdminParticipant(adminKey.value, participant.id);
      } else {
        await restoreAdminParticipant(adminKey.value, participant.id);
      }
      await loadSnapshot({ preserveUnsavedTaskDrafts: true });
    } catch (e: any) {
      error.value = formatAdminApiError(e, archived ? '受測者封存失敗。' : '受測者恢復失敗。');
    } finally {
      changingParticipantStatusId.value = null;
    }
  };

  const resetSessionTimer = async (sessionId: string) => {
    updatingTimerSessionId.value = sessionId;
    try {
      await resetAdminSessionTimer(adminKey.value, sessionId);
      await loadSnapshot({ preserveUnsavedTaskDrafts: true });
    } catch (e: any) {
      error.value = formatAdminApiError(e, 'Session 倒數重置失敗。');
    } finally {
      updatingTimerSessionId.value = null;
    }
  };

  const restartSession = async (sessionId: string) => {
    restartingSessionId.value = sessionId;
    error.value = null;
    try {
      await restartAdminSession(adminKey.value, sessionId);
      await loadSnapshot({ preserveUnsavedTaskDrafts: true });
    } catch (e: any) {
      error.value = formatAdminApiError(e, 'Session 無法重新建立。');
    } finally {
      restartingSessionId.value = null;
    }
  };

  const loadPromptPreview = async (event: EventWithPersonas, condition: ExperimentCondition) => {
    promptPreviewLoading.value = true;
    error.value = null;
    try {
      const personaId = condition.roleplay_enabled
        ? event.personas.find((persona) => persona.active)?.id || null
        : null;
      promptPreview.value = await fetchAdminPromptPreview(adminKey.value, {
        eventId: event.id,
        conditionKey: condition.condition_key,
        personaId,
        sampleUserMessage: promptPreviewMessage.value,
      });
    } catch (e: any) {
      promptPreview.value = null;
      error.value = formatAdminApiError(e, 'Prompt 預覽載入失敗。');
    } finally {
      promptPreviewLoading.value = false;
    }
  };

  const runPromptDryRun = async (event: EventWithPersonas, condition: ExperimentCondition) => {
    promptDryRunLoading.value = true;
    error.value = null;
    try {
      const personaId = condition.roleplay_enabled
        ? event.personas.find((persona) => persona.active)?.id || null
        : null;
      promptDryRun.value = await runAdminPromptDryRun(adminKey.value, {
        eventId: event.id,
        conditionKey: condition.condition_key,
        personaId,
        sampleUserMessage: promptPreviewMessage.value,
      });
    } catch (e: any) {
      promptDryRun.value = null;
      error.value = formatAdminApiError(e, 'Prompt dry-run 失敗。');
    } finally {
      promptDryRunLoading.value = false;
    }
  };

  return {
    adminKey,
    archivePersona,
    authUsers,
    authUsersError,
    changingParticipantStatusId,
    changingPersonaStatusId,
    conditionModeLabel,
    conditionOrdinal,
    createPersona,
    createParticipant,
    creatingPersona,
    creatingParticipant,
    error,
    eventYearRange,
    hasUnsavedTaskChanges,
    isTaskDirty,
    loadSnapshot,
    loadAuthUsers,
    loadPromptPreview,
    personaJson,
    promptPreview,
    promptDryRun,
    promptDryRunLoading,
    promptPreviewLoading,
    promptPreviewMessage,
    promptConditions,
    resetWorkspace,
    restartSession,
    restartingSessionId,
    restorePersona,
    restoreStoredAdminKey,
    runPromptDryRun,
    saveCondition,
    saveEvent,
    setEventArchived,
    savePersona,
    savingPersonaId,
    saveParticipant,
    setParticipantArchived,
    setPersonaActive,
    saveTask,
    savingTaskId,
    resetSessionTimer,
    updatingTimerSessionId,
    savingParticipantId,
    selectedCondition,
    selectedConditionId,
    selectedEvent,
    selectedEventId,
    snapshot,
    taskJson,
    taskQuestionCount,
  };
};

const formatAdminApiError = (e: any, fallback: string) => {
  const detail = e?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail?.issues && Array.isArray(detail.issues)) {
    const messages = detail.issues
      .map((issue: any) => issue?.message || issue?.field)
      .filter(Boolean);
    return [detail.message, ...messages].filter(Boolean).join('\n');
  }
  return e?.data?.message || fallback;
};
