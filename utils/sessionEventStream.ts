export interface SessionEventOptions {
  url: string;
  headers: () => Record<string, string>;
  onChange: () => void;
  onConnectionChange?: (connected: boolean) => void;
}

/** SSE is a change hint. Every (re)connection reloads the durable snapshot. */
export const subscribeSessionEvents = (options: SessionEventOptions): (() => void) => {
  const controller = new AbortController();
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let retryDelay = 1000;

  const connect = async () => {
    try {
      const response = await fetch(options.url, {
        headers: { ...options.headers(), Accept: 'text/event-stream' },
        signal: controller.signal,
        cache: 'no-store',
      });
      if (!response.ok || !response.body) throw new Error('Event connection unavailable');
      if (controller.signal.aborted) return;
      options.onConnectionChange?.(true);
      options.onChange();
      retryDelay = 1000;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      const parser = createSessionEventParser(options.onChange);
      try {
        while (!controller.signal.aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          parser(decoder.decode(value, { stream: true }));
        }
      } finally {
        await reader.cancel().catch(() => {});
        reader.releaseLock();
      }
    } catch {
      // A disconnected device keeps its saved stage. Reconnect with fresh auth.
    } finally {
      if (!controller.signal.aborted) {
        options.onConnectionChange?.(false);
        reconnectTimer = setTimeout(() => { void connect(); }, retryDelay);
        retryDelay = Math.min(retryDelay * 2, 10000);
      }
    }
  };
  void connect();
  return () => {
    controller.abort();
    if (reconnectTimer) clearTimeout(reconnectTimer);
  };
};

/** Handles chunk boundaries and both LF/CRLF without treating heartbeats as changes. */
export const createSessionEventParser = (onChange: () => void) => {
  let buffer = '';
  return (chunk: string) => {
    buffer += chunk;
    let boundary: RegExpExecArray | null;
    while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
      const frame = buffer.slice(0, boundary.index);
      buffer = buffer.slice(boundary.index + boundary[0].length);
      if (frame.split(/\r?\n/).some((line) => /^event:\s*change\s*$/.test(line))) onChange();
    }
  };
};
