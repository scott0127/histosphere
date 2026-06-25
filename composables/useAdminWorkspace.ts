// useAdminWorkspace 管理 admin 頁的 snapshot 載入、JSON 編輯狀態與保存流程。
// Page 保留登入畫面與折疊 UI；這裡負責 admin API 的狀態一致性。
import { computed, ref, watch } from 'vue';
import type { ComputedRef, Ref } from 'vue';
import { taskControlQuestions } from '~/composables/useTaskControl';
import type {
  AdminPromptPreviewResponse,
  AdminSnapshotResponse,
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
  fetchAdminSnapshot,
  fetchAdminPromptPreview,
  updateAdminCondition,
  updateAdminEvent,
  updateAdminPersona,
  updateAdminTask,
} from '~/utils/histosphereApi';

export const useAdminWorkspace = (
  isAuthenticated: Ref<boolean> | ComputedRef<boolean>,
) => {
  const adminKey = ref('');
  const snapshot = ref<AdminSnapshotResponse | null>(null);
  const error = ref<string | null>(null);
  const taskJson = ref<Record<string, string>>({});
  const personaJson = ref<Record<string, string>>({});
  const selectedConditionId = ref<string | null>(null);
  const selectedEventId = ref<string | null>(null);
  const promptPreview = ref<AdminPromptPreviewResponse | null>(null);
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
    return conditions.find((condition) => condition.id === selectedConditionId.value) || conditions[0];
  });

  watch([selectedEventId, selectedConditionId, promptPreviewMessage], () => {
    promptPreview.value = null;
  });

  const resetWorkspace = (clearStoredKey = true) => {
    adminKey.value = '';
    snapshot.value = null;
    error.value = null;
    taskJson.value = {};
    personaJson.value = {};
    promptPreview.value = null;
    selectedConditionId.value = null;
    selectedEventId.value = null;
    if (clearStoredKey && import.meta.client) {
      localStorage.removeItem('histosphere_admin_key');
    }
  };

  const restoreStoredAdminKey = () => {
    if (!import.meta.client) return;
    adminKey.value = localStorage.getItem('histosphere_admin_key') || '';
  };

  const loadSnapshot = async () => {
    error.value = null;
    if (!isAuthenticated.value) {
      snapshot.value = null;
      error.value = '請先登入管理員帳號。';
      return;
    }

    try {
      if (import.meta.client) {
        localStorage.setItem('histosphere_admin_key', adminKey.value);
      }
      const data = await fetchAdminSnapshot(adminKey.value);
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
    } catch (e: any) {
      error.value = formatAdminApiError(e, '後台資料載入失敗，請確認 admin key。');
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

  return {
    adminKey,
    conditionModeLabel,
    conditionOrdinal,
    error,
    eventYearRange,
    loadSnapshot,
    loadPromptPreview,
    personaJson,
    promptPreview,
    promptPreviewLoading,
    promptPreviewMessage,
    promptConditions,
    resetWorkspace,
    restoreStoredAdminKey,
    saveCondition,
    saveEvent,
    savePersona,
    saveTask,
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
