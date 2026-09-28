export const flushEvents = async () => {
  await new Promise(setImmediate);
  await new Promise(setImmediate);
};

/** Fake network/time only; tests exercise the real SSE reader and waiting state machine. */
export const sessionEventHarness = () => {
  const original = Object.fromEntries(['fetch', 'setTimeout', 'clearTimeout', 'setInterval', 'clearInterval'].map(key => [key, globalThis[key]]));
  const originalNow = Date.now;
  const timers = new Map();
  const connections = [];
  let clock = 0;
  let nextId = 0;
  const schedule = (callback, delay = 0, repeat = false) => {
    const id = ++nextId;
    timers.set(id, { callback, at: clock + delay, delay, repeat });
    return id;
  };
  globalThis.setTimeout = (callback, delay) => schedule(callback, delay);
  globalThis.setInterval = (callback, delay) => schedule(callback, delay, true);
  globalThis.clearTimeout = id => timers.delete(id);
  globalThis.clearInterval = id => timers.delete(id);
  Date.now = () => clock;
  globalThis.fetch = async (url, options) => {
    const connection = { url, headers: options.headers, signal: options.signal, aborted: false, controller: null };
    const body = new ReadableStream({ start(controller) { connection.controller = controller; } });
    options.signal.addEventListener('abort', () => {
      connection.aborted = true;
      try { connection.controller.error(new DOMException('Aborted', 'AbortError')); } catch { /* Already closed. */ }
    }, { once: true });
    connections.push(connection);
    return new Response(body, { headers: { 'content-type': 'text/event-stream' } });
  };
  const emit = (text, index = connections.length - 1) => {
    connections[index].controller.enqueue(new TextEncoder().encode(text));
  };
  return {
    connections, timers, emit,
    async advance(ms) {
      const target = clock + ms;
      while (true) {
        const entry = [...timers.entries()].filter(([, timer]) => timer.at <= target).sort((a, b) => a[1].at - b[1].at)[0];
        if (!entry) break;
        const [id, timer] = entry;
        clock = timer.at;
        if (timer.repeat) timer.at += timer.delay;
        else timers.delete(id);
        timer.callback();
        await flushEvents();
      }
      clock = target;
      await flushEvents();
    },
    restore() {
      Object.assign(globalThis, original);
      Date.now = originalNow;
    },
  };
};
