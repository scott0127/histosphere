import type { ResearchLog, ResearchLogChange } from '~/types';

export interface AdminResearchLogFilters {
  search: string;
  actionType: string;
  eventId: string;
  dateFrom: string;
  dateTo: string;
}

const ACTION_LABELS: Record<string, string> = {
  assistant_response_generated: '一般 AI 回覆完成',
  condition_updated: '條件設定更新',
  conversation_started: '對話開始',
  event_archived: '事件封存',
  event_initialized: '事件流程建立',
  event_restored: '事件恢復',
  event_session_resumed: '事件流程恢復',
  event_updated: '事件資料更新',
  message_sent: '受測者訊息送出',
  participant_archived: '受測者封存',
  participant_created: '受測者建立',
  participant_restored: '受測者恢復',
  participant_updated: '受測者資料更新',
  persona_archived: '歷史人物封存',
  persona_created: '歷史人物建立',
  persona_response_generated: '歷史人物回覆完成',
  persona_restored: '歷史人物恢復',
  persona_updated: '歷史人物更新',
  response_generation_failed: 'AI 回覆產生失敗',
  response_generation_retried: 'AI 回覆重新產生',
  session_completed: '階段完成',
  session_restarted: 'Session 重新建立',
  session_timer_cancelled: '倒數取消',
  session_timer_reset: '倒數重置',
  session_timer_started: '倒數開始',
  task_answer_changed: 'Task 答案變更',
  task_submission_failed: 'Task 送出失敗',
  task_submission_processed: 'Task 評分完成',
  task_submission_queued: 'Task 等待評分',
  task_submitted: 'Task 已送出',
  task_updated: 'Task 更新',
};

export const researchLogActionLabel = (actionType: string) => {
  return ACTION_LABELS[actionType] || actionType.replaceAll('_', ' ');
};

export const researchLogChanges = (log: ResearchLog): Array<{
  field: string;
  change: ResearchLogChange;
}> => {
  const changes = log.payload?.changes;
  if (!changes || typeof changes !== 'object') return [];
  return Object.entries(changes)
    .filter((entry): entry is [string, ResearchLogChange] => {
      const value = entry[1];
      return Boolean(value && typeof value === 'object' && 'before' in value && 'after' in value);
    })
    .map(([field, change]) => ({ field, change }));
};

export const formatResearchLogValue = (value: unknown) => {
  if (value === null || value === undefined || value === '') return '未設定';
  if (typeof value === 'string') return value;
  return JSON.stringify(value, null, 2);
};

export const filterResearchLogs = (
  logs: ResearchLog[],
  filters: AdminResearchLogFilters,
) => {
  const search = filters.search.trim().toLocaleLowerCase();
  return logs.filter((log) => {
    if (filters.actionType && log.action_type !== filters.actionType) return false;
    if (filters.eventId && log.event_id !== filters.eventId) return false;

    const date = log.created_at.slice(0, 10);
    if (filters.dateFrom && date < filters.dateFrom) return false;
    if (filters.dateTo && date > filters.dateTo) return false;

    if (!search) return true;
    const searchable = [
      log.action_type,
      researchLogActionLabel(log.action_type),
      log.event_id,
      log.session_id,
      log.task_id,
      log.payload?.participant_code,
      log.payload?.persona_name,
      log.payload?.event_name,
      JSON.stringify(log.payload),
    ]
      .filter(Boolean)
      .join(' ')
      .toLocaleLowerCase();
    return searchable.includes(search);
  });
};

const csvCell = (value: unknown) => {
  return `"${String(value ?? '').replaceAll('"', '""')}"`;
};

export const researchLogsToCsv = (
  logs: ResearchLog[],
  eventNames: Record<string, string> = {},
) => {
  const header = [
    'created_at',
    'action_type',
    'action_label',
    'event',
    'event_id',
    'session_id',
    'task_id',
    'participant_code',
    'updated_fields',
    'payload',
  ];
  const rows = logs.map((log) => [
    log.created_at,
    log.action_type,
    researchLogActionLabel(log.action_type),
    log.event_id ? eventNames[log.event_id] || '' : '',
    log.event_id || '',
    log.session_id || '',
    log.task_id || '',
    log.payload?.participant_code || '',
    researchLogChanges(log).map(({ field }) => field).join('|'),
    JSON.stringify(log.payload || {}),
  ]);
  return `\uFEFF${[header, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n')}`;
};
