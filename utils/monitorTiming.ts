import { monitorPhase } from '~/utils/taskReview';
import type { AdminMonitorSnapshot } from '~/types/taskReview';

export interface MonitorCountdown {
  title: string;
  display: string;
  detail: string;
  durationLabel: string;
  state: 'waiting' | 'running' | 'expired' | 'unavailable' | 'complete';
}

// Researcher reminders only. These budgets must not change the learner's runtime timer.
const referenceMinutes = { task: 5, chat: 10, posttest: 15 } as const;

export function monitorCountdown(snapshot: AdminMonitorSnapshot, nowMs: number): MonitorCountdown {
  const phase = monitorPhase(snapshot);
  if (phase.id === 'complete' || phase.id === 'archived') {
    return { title: phase.label, display: '已結束', detail: '', durationLabel: '', state: 'complete' };
  }

  let startedAt: string | null | undefined;
  let minutes: number;
  let title: string;
  let detail: string;
  if (phase.id === 'task') {
    minutes = referenceMinutes.task;
    title = '受測者作答中';
    startedAt = snapshot.session.created_at;
    detail = '自活動建立起算；提交後進入人工核對。';
  } else if (phase.id === 'chat') {
    minutes = referenceMinutes.chat;
    title = 'AI 互動中';
    startedAt = snapshot.session.timer_started_at;
    const runtimeMs = Date.parse(snapshot.session.timer_ends_at || '') - Date.parse(startedAt || '');
    detail = Number.isFinite(runtimeMs) && runtimeMs > 0 && runtimeMs !== minutes * 60_000
      ? `受測者現行互動時限為 ${Number((runtimeMs / 60_000).toFixed(1))} 分鐘。`
      : '依受測者進入互動的時間起算。';
  } else if (phase.id === 'posttest') {
    minutes = referenceMinutes.posttest;
    title = snapshot.posttest?.stage === 'hat' ? '歷史思考後測（HAT）' : '後續評量';
    startedAt = snapshot.posttest?.started_at;
    detail = snapshot.posttest
      ? `目前：${snapshot.posttest.stage === 'hat' ? 'HAT' : 'Engagement 問卷'} · HAT 10 分鐘＋Engagement 5 分鐘，共用倒數。`
      : '等待受測者進入後續評量。';
  } else {
    return { title: phase.label, display: '等待中', detail: '', durationLabel: '', state: 'waiting' };
  }

  const durationLabel = `參考時間 ${minutes} 分鐘`;
  if (!startedAt) return { title, display: '尚未開始', detail, durationLabel, state: 'waiting' };
  const start = Date.parse(startedAt);
  if (!Number.isFinite(start) || !Number.isFinite(nowMs)) {
    return { title, display: '暫無計時資料', detail: '請重新同步施測資料。', durationLabel, state: 'unavailable' };
  }
  // Absolute persisted start survives reloads and reconnections; never restart on a draft save.
  const seconds = Math.max(0, Math.min(minutes * 60, Math.ceil((start + minutes * 60_000 - nowMs) / 1000)));
  const display = `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
  return { title, display, detail, durationLabel, state: seconds === 0 ? 'expired' : 'running' };
}
