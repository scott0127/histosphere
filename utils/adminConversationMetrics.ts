export const metricNumber = (value?: number | null): string =>
  value == null || !Number.isFinite(value) ? '未記錄' : value.toLocaleString('zh-TW', { maximumFractionDigits: 1 });

export const metricDuration = (seconds?: number | null): string => {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return '未記錄';
  if (seconds === 0) return '0 秒';
  if (seconds < 0.1) return '< 0.1 秒';
  const tenths = Math.round(seconds * 10);
  const hours = Math.floor(tenths / 36000);
  const minutes = Math.floor((tenths % 36000) / 600);
  const remainder = (tenths % 600) / 10;
  return `${hours ? `${hours} 小時 ` : ''}${minutes ? `${minutes} 分 ` : ''}${remainder || (!hours && !minutes) ? `${remainder} 秒` : ''}`.trim();
};

export const metricDate = (value?: string | null): string => {
  if (!value || !Number.isFinite(Date.parse(value))) return '未記錄';
  return new Intl.DateTimeFormat('zh-TW', { dateStyle: 'short', timeStyle: 'medium' }).format(new Date(value));
};

export const roundStatusLabel = (status: string): string => ({
  completed: '已完成', failed: '回覆失敗', pending: '尚未回覆', unmatched: '配對資料不足',
}[status] || status);

export const questionOutcomeLabel = (status: string): string => ({
  corrected: '修正成功', feedback_completed: '已提供回饋', unresolved: '未修正成功', in_progress: '討論中',
}[status] || status);
