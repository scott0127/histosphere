import assert from 'node:assert/strict';
import { flushEvents, sessionEventHarness } from '../helpers/sessionEventHarness.mjs';

const { waitForReviewedTask } = await globalThis.loadTsModule('utils/taskSubmissionWaiter.ts');
const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
};

test('human review can wait beyond four minutes, then ready enters once despite duplicate change events', async () => {
  const harness = sessionEventHarness();
  const entering = deferred();
  const expected = { conversation_id: 'approved-chat' };
  let stage = 'awaiting_review';
  let enterCalls = 0;
  let settled = false;
  const states = [];
  const waiter = waitForReviewedTask({
    attemptId: 'attempt-one', headers: () => ({ Authorization: 'Bearer learner' }),
    status: async () => ({ attempt: { status: stage } }),
    enter: async () => { enterCalls += 1; return entering.promise; },
    onState: state => states.push(state),
  });
  waiter.result.then(() => { settled = true; }, () => { settled = true; });
  try {
    await flushEvents();
    await harness.advance(5 * 60 * 1000);
    assert.equal(settled, false);
    assert.equal(enterCalls, 0);
    assert.equal(states.at(-1).stage, 'awaiting_review');

    stage = 'ready';
    harness.emit('event: change\ndata: {}\n\nevent: change\ndata: {}\n\n');
    await flushEvents();
    await harness.advance(30000);
    assert.equal(enterCalls, 1, 'events and fallback refresh must not duplicate in-flight entry');
    entering.resolve(expected);
    assert.deepEqual(await waiter.result, expected);
    await flushEvents();
    assert.equal(harness.connections[0].aborted, true);
    assert.equal(harness.timers.size, 0);
  } finally { waiter.stop(); harness.restore(); }
});

test('lost entry response recovers the submitted snapshot without repeating entry', async () => {
  const harness = sessionEventHarness();
  const expected = { conversation_id: 'already-started-chat' };
  let stage = 'ready';
  let enterCalls = 0;
  const waiter = waitForReviewedTask({
    attemptId: 'attempt-two', headers: () => ({}),
    status: async () => ({ attempt: { status: stage }, ...(stage === 'submitted' ? { result: expected } : {}) }),
    enter: async () => {
      enterCalls += 1;
      stage = 'submitted';
      throw new Error('Response lost after server committed entry');
    },
    onState() {},
  });
  try {
    await flushEvents();
    await harness.advance(15000);
    assert.deepEqual(await waiter.result, expected);
    assert.equal(enterCalls, 1);
    assert.equal(harness.timers.size, 0);
  } finally { waiter.stop(); harness.restore(); }
});

test('stopping while entry is in flight rejects the waiter and never resolves a navigation result', async () => {
  const harness = sessionEventHarness();
  const entering = deferred();
  let navigations = 0;
  const states = [];
  const waiter = waitForReviewedTask({
    attemptId: 'attempt-three', headers: () => ({}),
    status: async () => ({ attempt: { status: 'ready' } }),
    enter: () => entering.promise, onState: state => states.push(state),
  });
  const outcome = waiter.result.then(() => { navigations += 1; return null; }, error => error);
  try {
    await flushEvents();
    waiter.stop();
    const stoppedStateCount = states.length;
    assert.equal((await outcome).name, 'AbortError');
    entering.resolve({ conversation_id: 'late-chat' });
    await flushEvents();
    await harness.advance(5 * 60 * 1000);
    assert.equal(navigations, 0);
    assert.equal(states.length, stoppedStateCount);
    assert.equal(harness.timers.size, 0);
    assert.equal(harness.connections[0].aborted, true);
  } finally { waiter.stop(); harness.restore(); }
});
