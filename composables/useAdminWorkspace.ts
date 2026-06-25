// useAdminWorkspace 管理 admin 頁的 snapshot 載入、JSON 編輯狀態與保存流程。
// Page 保留登入畫面與折疊 UI；這裡負責 admin API 的狀態一致性。
import { computed, ref } from 'vue';
import type { ComputedRef, Ref } from 'vue';
import { taskControlQuestions } from '~/composables/useTaskControl';
import type { AdminSnapshotResponse, EventTask, EventWithPersonas, ExperimentCondition, Persona } from '~/types';
import {
  buildAdminEditableJson,
  conditionModeLabel,
  conditionOrdinal,
  eventYearRange,
  sortPromptConditions,
} from '~/utils/adminWorkspaceState';
import {
  fetchAdminSnapshot,
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

  const resetWorkspace = (clearStoredKey = true) => {
    adminKey.value = '';
    snapshot.value = null;
    error.value = null;
    taskJson.value = {};
    personaJson.value = {};
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
      error.value = e.data?.detail || '後台資料載入失敗，請確認 admin key。';
    }
  };

  const taskQuestionCount = (task?: EventTask | null) => {
    if (!task) return 0;
    const evaluationJson = taskJson.value[task.id] || JSON.stringify(task.evaluation_payload || {}, null, 2);
    return taskControlQuestions(task, evaluationJson).length;
  };

  const saveCondition = async (condition: ExperimentCondition) => {
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
  };

  const saveTask = async (task: EventTask) => {
    let evaluationPayload = {};
    try {
      evaluationPayload = JSON.parse(taskJson.value[task.id] || '{}');
    } catch {
      error.value = `Task ${task.id} 的 evaluation_payload 不是合法 JSON。`;
      return;
    }
    await updateAdminTask(adminKey.value, task.id, {
      title: task.title,
      story_text: task.story_text,
      display_text: task.display_text,
      evaluation_payload: evaluationPayload,
      revision_state: 'teacher_modified',
    });
    await loadSnapshot();
  };

  const saveEvent = async (event: EventWithPersonas) => {
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
  };

  const savePersona = async (persona: Persona) => {
    let promptProfile = {};
    try {
      promptProfile = JSON.parse(personaJson.value[persona.id] || '{}');
    } catch {
      error.value = `Persona ${persona.name} 的 prompt_profile 不是合法 JSON。`;
      return;
    }
    await updateAdminPersona(adminKey.value, persona.id, {
      name: persona.name,
      role: persona.role,
      biography: persona.biography,
      prompt_profile: promptProfile,
      active: persona.active,
      revision_state: 'teacher_modified',
    });
    await loadSnapshot();
  };

  return {
    adminKey,
    conditionModeLabel,
    conditionOrdinal,
    error,
    eventYearRange,
    loadSnapshot,
    personaJson,
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
