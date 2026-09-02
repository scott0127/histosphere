import type { AdminSnapshotResponse, EventTask, EventWithPersonas, ExperimentCondition } from '../types';
import { parseTaskEvaluationJson, syncTaskQuestionOrder, validateTaskControlPayload } from '~/composables/useTaskControl';

export const conditionModeOrder: ExperimentCondition['condition_key'][] = [
  'no_ebl_no_roleplay',
  'ebl_no_roleplay',
  'no_ebl_roleplay',
  'ebl_roleplay',
];

export const conditionModeLabels: Record<ExperimentCondition['condition_key'], string> = {
  no_ebl_no_roleplay: '01 without EBL + without role-play',
  ebl_no_roleplay: '02 EBL + without role-play',
  no_ebl_roleplay: '03 without EBL + role-play',
  ebl_roleplay: '04 EBL + role-play',
};

export const buildAdminEditableJson = (snapshot: AdminSnapshotResponse) => {
  const taskJson: Record<string, string> = {};
  const personaJson: Record<string, string> = {};

  for (const event of snapshot.events) {
    if (event.latest_task) {
      taskJson[event.latest_task.id] = JSON.stringify(event.latest_task.evaluation_payload || {}, null, 2);
    }
    for (const persona of event.personas) {
      personaJson[persona.id] = JSON.stringify(persona.prompt_profile || {}, null, 2);
    }
  }

  return { taskJson, personaJson };
};

export const taskAuthoringSignature = (task: EventTask, evaluationJson: string) => {
  return JSON.stringify({
    title: task.title || '',
    error_elicitation_task_full_text: task.error_elicitation_task_full_text || '',
    evaluation_json: evaluationJson || '{}',
  });
};

export const buildAdminTaskPatch = (task: EventTask, evaluationJson: string) => {
  const issues = validateTaskControlPayload(task, evaluationJson);
  if (issues.length) throw new Error(issues.join('\n'));
  const { payload } = parseTaskEvaluationJson(syncTaskQuestionOrder(evaluationJson, task.error_elicitation_task_full_text));
  return {
    title: task.title,
    error_elicitation_task_full_text: task.error_elicitation_task_full_text,
    evaluation_payload: payload,
    revision_state: 'teacher_modified' as const,
  };
};

export const sortPromptConditions = (conditions: ExperimentCondition[]) => {
  return [...conditions].sort((a, b) => {
    const aIndex = conditionModeOrder.indexOf(a.condition_key);
    const bIndex = conditionModeOrder.indexOf(b.condition_key);
    const normalizedA = aIndex === -1 ? Number.MAX_SAFE_INTEGER : aIndex;
    const normalizedB = bIndex === -1 ? Number.MAX_SAFE_INTEGER : bIndex;
    return normalizedA - normalizedB;
  });
};

export const eventYearRange = (event: EventWithPersonas) => {
  if (event.start_year && event.end_year && event.start_year !== event.end_year) {
    return `${event.start_year} - ${event.end_year}`;
  }
  if (event.start_year || event.end_year) {
    return String(event.start_year || event.end_year);
  }
  if (event.century) {
    return `${event.century} 世紀`;
  }
  return '未設定';
};

export const conditionOrdinal = (condition: ExperimentCondition) => {
  const index = conditionModeOrder.indexOf(condition.condition_key);
  if (index === -1) return '--';
  return String(index + 1).padStart(2, '0');
};

export const conditionModeLabel = (condition: ExperimentCondition) => {
  return conditionModeLabels[condition.condition_key] || condition.label;
};
