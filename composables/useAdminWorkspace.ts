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
  Persona,
} from '~/types';
import {
  buildAdminEditableJson,
  conditionModeLabel,
  conditionOrdinal,
  eventYearRange,
  sortPromptConditions,
} from '~/utils/adminWorkspaceState';
import {
  clearAdminSessionKey,
  getAdminSessionKey,
  setAdminSessionKey,
} from '~/utils/adminSession';
import {
  archiveAdminEvent,
  cancelAdminSessionTimer,
  fetchAdminAuthUsers,
  fetchAdminSnapshot,
  fetchAdminPromptPreview,
  restoreAdminEvent,
  restartAdminSession,
  runAdminPromptDryRun,
  startAdminSessionTimer,
  updateAdminCondition,
  updateAdminEvent,
  updateAdminParticipant,
  updateAdminPersona,
  updateAdminTask,
  type ParticipantUpdateInput,
} from '~/utils/histosphereApi';

export const useAdminWorkspace = () => {
  const adminKey = ref('');
  const snapshot = ref<AdminSnapshotResponse | null>(null);
  const authUsers = ref<AdminAuthUserSummary[]>([]);
  const error = ref<string | null>(null);
  const authUsersError = ref<string | null>(null);
  const taskJson = ref<Record<string, string>>({});
  const personaJson = ref<Record<string, string>>({});
  const selectedConditionId = ref<string | null>(null);
  const selectedEventId = ref<string | null>(null);
  const savingParticipantId = ref<string | null>(null);
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
    personaJson.value = {};
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

  const loadSnapshot = async () => {
    error.value = null;
    try {
      const data = await fetchAdminSnapshot(adminKey.value);
      setAdminSessionKey(adminKey.value);
      const editable = buildAdminEditableJson(data);

      taskJson.value = editable.taskJson;
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
      await loadSnapshot();
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
    try {
      await updateAdminTask(adminKey.value, task.id, {
        title: task.title,
        story_text: task.story_text,
        display_text: task.display_text,
        evaluation_payload: evaluationPayload,
        revision_state: 'teacher_modified',
      });
      await loadSnapshot();
    } catch (e: any) {
      error.value = formatAdminApiError(e, 'Task 儲存失敗。');
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
      await loadSnapshot();
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
      await loadSnapshot();
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
    try {
      await updateAdminPersona(adminKey.value, persona.id, {
        name: persona.name,
        role: persona.role,
        biography: persona.biography,
        prompt_profile: promptProfile,
        active: persona.active,
        revision_state: 'teacher_modified',
      });
      await loadSnapshot();
    } catch (e: any) {
      error.value = formatAdminApiError(e, '人物資料儲存失敗。');
    }
  };

  const saveParticipant = async (participantId: string, body: ParticipantUpdateInput) => {
    savingParticipantId.value = participantId;
    error.value = null;
    try {
      await updateAdminParticipant(adminKey.value, participantId, body);
      await loadSnapshot();
    } catch (e: any) {
      error.value = formatAdminApiError(e, '受測者資料儲存失敗。');
    } finally {
      savingParticipantId.value = null;
    }
  };

  const startSessionTimer = async (sessionId: string, durationMinutes: number) => {
    updatingTimerSessionId.value = sessionId;
    try {
      await startAdminSessionTimer(adminKey.value, sessionId, durationMinutes);
      await loadSnapshot();
    } catch (e: any) {
      error.value = formatAdminApiError(e, 'Session 計時器啟動失敗。');
    } finally {
      updatingTimerSessionId.value = null;
    }
  };

  const cancelSessionTimer = async (sessionId: string) => {
    updatingTimerSessionId.value = sessionId;
    try {
      await cancelAdminSessionTimer(adminKey.value, sessionId);
      await loadSnapshot();
    } catch (e: any) {
      error.value = formatAdminApiError(e, 'Session 計時器停止失敗。');
    } finally {
      updatingTimerSessionId.value = null;
    }
  };

  const restartSession = async (sessionId: string) => {
    restartingSessionId.value = sessionId;
    error.value = null;
    try {
      await restartAdminSession(adminKey.value, sessionId);
      await loadSnapshot();
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
    authUsers,
    authUsersError,
    cancelSessionTimer,
    conditionModeLabel,
    conditionOrdinal,
    error,
    eventYearRange,
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
    restoreStoredAdminKey,
    runPromptDryRun,
    saveCondition,
    saveEvent,
    setEventArchived,
    savePersona,
    saveParticipant,
    saveTask,
    startSessionTimer,
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
