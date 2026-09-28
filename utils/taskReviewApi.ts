import type { AdminMonitorSnapshot, TaskReviewAttempt, TaskReviewQuestion } from '~/types/taskReview';

const headers = (key: string) => ({ 'x-admin-key': key });

export const fetchAdminMonitor = (key: string, sessionId: string) =>
  $fetch<AdminMonitorSnapshot>(`/api/admin/monitor/sessions/${encodeURIComponent(sessionId)}`, { headers: headers(key) });

export const saveAdminTaskReview = (key: string, attemptId: string, expectedVersion: number, questions: TaskReviewQuestion[]) =>
  $fetch<TaskReviewAttempt>(`/api/admin/monitor/attempts/${encodeURIComponent(attemptId)}/review`, {
    method: 'PATCH', headers: headers(key), body: { expected_version: expectedVersion, question_results: questions },
  });

export const approveAdminTaskReview = (key: string, attemptId: string, expectedVersion: number) =>
  $fetch<TaskReviewAttempt>(`/api/admin/monitor/attempts/${encodeURIComponent(attemptId)}/approve`, {
    method: 'POST', headers: headers(key), body: { expected_version: expectedVersion },
  });

export const retryAdminTaskProcessing = (key: string, attemptId: string) =>
  $fetch(`/api/admin/monitor/attempts/${encodeURIComponent(attemptId)}/retry`, { method: 'POST', headers: headers(key) });
