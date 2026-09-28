import type { TaskSubmissionStatusResponse, TaskSubmitResponse } from '~/types';
import { subscribeSessionEvents } from '~/utils/sessionEventStream';

export interface TaskWaitingState {
  stage: string;
  connected: boolean;
}

interface WaitingOptions {
  attemptId: string;
  headers: () => Record<string, string>;
  status: (id: string) => Promise<TaskSubmissionStatusResponse>;
  enter: (id: string) => Promise<TaskSubmitResponse>;
  onState: (state: TaskWaitingState) => void;
}

/** Keeps submitted answers locked until an approved opening is ready. No human-review timeout. */
export const waitForReviewedTask = (options: WaitingOptions) => {
  let active = true;
  let refreshing = false;
  let refreshAgain = false;
  let stage = 'processing';
  let connected = false;
  let unsubscribe = () => {};
  let fallbackTimer: ReturnType<typeof setInterval> | null = null;
  let resolve: (result: TaskSubmitResponse) => void;
  let reject: (error: Error) => void;
  const result = new Promise<TaskSubmitResponse>((done, fail) => { resolve = done; reject = fail; });
  const publish = () => { if (active) options.onState({ stage, connected }); };
  const cleanup = () => {
    active = false;
    unsubscribe();
    if (fallbackTimer) clearInterval(fallbackTimer);
  };

  const refresh = async () => {
    if (!active) return;
    if (refreshing) { refreshAgain = true; return; }
    refreshing = true;
    try {
      const snapshot = await options.status(options.attemptId);
      if (!active) return;
      stage = snapshot.attempt.status;
      publish();
      let final: TaskSubmitResponse | null | undefined;
      if (stage === 'ready') final = await options.enter(options.attemptId);
      else if (stage === 'submitted') final = snapshot.result;
      if (active && final) {
        cleanup();
        resolve!(final);
      }
    } catch {
      // Lost responses (including entry confirmation) are recovered from the next snapshot.
      connected = false;
      publish();
    } finally {
      refreshing = false;
      if (active && refreshAgain) {
        refreshAgain = false;
        void refresh();
      }
    }
  };

  unsubscribe = subscribeSessionEvents({
    url: `/api/tasks/attempts/${options.attemptId}/events`,
    headers: options.headers,
    onChange: () => { void refresh(); },
    onConnectionChange: (value) => { connected = value; publish(); },
  });
  // Low-frequency recovery also covers proxies that buffer/drop the event stream.
  fallbackTimer = setInterval(() => { void refresh(); }, 15000);
  void refresh();
  return { result, stop: () => {
    if (!active) return;
    cleanup();
    reject!(new DOMException('Task page closed', 'AbortError'));
  } };
};
