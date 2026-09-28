import type { AdminLLMUsageRow } from '~/types';

// A user-editable budgeting assumption, not a live market exchange rate.
export const DEFAULT_USD_TWD_ESTIMATE = 32;
export const validEstimateRate = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value) && value > 0 && value <= 1000;

export const formatEstimatedTwd = (usd: unknown, rate: unknown) => {
  if (typeof usd !== 'number' || !Number.isFinite(usd) || usd < 0 || !validEstimateRate(rate)) return '未能估算';
  const twd = usd * rate;
  if (twd > 0 && twd < 0.0001) return '< NT$0.0001';
  return `NT$${twd.toLocaleString('zh-TW', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
};

export const formatCallCost = (call: Record<string, unknown>, rate: unknown) => {
  const attempts = Number(call.attempt_count || 1);
  const complete = typeof call.estimated_cost_usd === 'number'
    && (call.cost_reported_attempts == null ? attempts === 1 : call.cost_reported_attempts === attempts);
  const usd = call.estimated_known_cost_usd ?? call.estimated_cost_usd;
  if (typeof usd !== 'number' || !Number.isFinite(usd) || usd < 0) return '費用未回報';
  return `${formatEstimatedTwd(usd, rate)}（US$${usd.toFixed(6)}${complete ? '' : '，僅已知費用'}）`;
};

const labels: Record<string, string> = {
  generate_event_profile: '事件資料生成', generate_task: 'Task 出題',
  judge_task_attempt: 'Task 答案與理由判定', generate_personas: '歷史人物生成',
  generate_greeting: '開場回覆（含重生）', conversation_opening: '開場回覆（含重生）',
  generate_chat_response: '聊天回覆（含重生）', chat_response: '聊天回覆（含重生）',
  review_answer: '答案審查', generate_recovery_continuation: '受限引導備援',
  unknown: '未記錄環節',
};
export const llmStageLabel = (stage: string) => labels[stage] || `其他／測試：${stage}`;

export const sumUsageRows = (rows: AdminLLMUsageRow[]) => rows.reduce((sum, row) => ({
  ...sum,
  requests: sum.requests + row.requests,
  token_reported_requests: sum.token_reported_requests + row.token_reported_requests,
  cost_reported_requests: sum.cost_reported_requests + row.cost_reported_requests,
  prompt_tokens: sum.prompt_tokens + row.prompt_tokens,
  completion_tokens: sum.completion_tokens + row.completion_tokens,
  total_tokens: sum.total_tokens + row.total_tokens,
  estimated_known_cost_usd: sum.estimated_known_cost_usd + row.estimated_known_cost_usd,
}), { stage: 'total', provider: '', model: '', requests: 0, token_reported_requests: 0, cost_reported_requests: 0,
  prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, estimated_known_cost_usd: 0 } as AdminLLMUsageRow);
