import assert from 'node:assert/strict';
import { flushEvents, sessionEventHarness } from '../helpers/sessionEventHarness.mjs';

const { createSessionEventParser, subscribeSessionEvents } = await globalThis.loadTsModule('utils/sessionEventStream.ts');

test('SSE parser preserves split frames across CRLF boundaries and ignores heartbeats', () => {
  let changes = 0;
  const parse = createSessionEventParser(() => { changes += 1; });
  parse(': keepalive\r\n\r');
  parse('\nevent: cha');
  assert.equal(changes, 0);
  parse('nge\r\ndata: {"revision":1}\r\n\r');
  assert.equal(changes, 0);
  parse('\n: heartbeat\n\nevent: change\ndata: {}\n\nevent: other\ndata: {}\n\n');
  assert.equal(changes, 2);
  parse('event: change\ndata: {"revision":3}');
  assert.equal(changes, 2);
  parse('\n\n');
  assert.equal(changes, 3);
});

test('SSE reconnect reloads durable state with fresh credentials and cleanup cancels the connection', async () => {
  const harness = sessionEventHarness();
  let key = 'old-credential';
  let changes = 0;
  const connected = [];
  const stop = subscribeSessionEvents({
    url: '/api/example/events', headers: () => ({ 'x-admin-key': key }),
    onChange: () => { changes += 1; }, onConnectionChange: value => connected.push(value),
  });
  try {
    await flushEvents();
    assert.equal(changes, 1, 'opening a connection always requests a fresh snapshot');
    assert.equal(harness.connections[0].headers['x-admin-key'], 'old-credential');
    harness.emit(': heartbeat\n\n');
    await flushEvents();
    assert.equal(changes, 1);
    harness.emit('event: change\ndata: {}\n\n');
    await flushEvents();
    assert.equal(changes, 2);

    harness.connections[0].controller.close();
    await flushEvents();
    assert.deepEqual(connected, [true, false]);
    key = 'renewed-credential';
    await harness.advance(1000);
    assert.equal(harness.connections.length, 2);
    assert.equal(harness.connections[1].headers['x-admin-key'], 'renewed-credential');
    assert.equal(changes, 3, 'reconnect refreshes even without a change event');

    stop();
    await flushEvents();
    assert.equal(harness.connections[1].aborted, true);
    await harness.advance(60000);
    assert.equal(harness.connections.length, 2);
    assert.equal(harness.timers.size, 0);
  } finally { stop(); harness.restore(); }
});

test('SSE cleanup also cancels a scheduled reconnect after a disconnected stream', async () => {
  const harness = sessionEventHarness();
  const stop = subscribeSessionEvents({ url: '/events', headers: () => ({}), onChange() {} });
  try {
    await flushEvents();
    harness.connections[0].controller.close();
    await flushEvents();
    assert.equal(harness.timers.size, 1);
    stop();
    await harness.advance(60000);
    assert.equal(harness.timers.size, 0);
    assert.equal(harness.connections.length, 1);
  } finally { stop(); harness.restore(); }
});
