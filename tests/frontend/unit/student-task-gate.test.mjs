import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRenderer, nextTick, ref } from 'vue';
import ts from 'typescript';
import { errorElicitationTask as task } from './student-task.test.mjs';

const logic = await globalThis.loadTsModule('composables/useStudentTask.ts');
const waiter = await globalThis.loadTsModule('utils/taskSubmissionWaiter.ts');
const dataUrl = (source) => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const delegates = (names, area) => dataUrl(names.map((name) => `export const ${name} = (...args) => globalThis.__taskGateTest.${area}.${name}(...args);`).join('\n'));
const source = await readFile('composables/useTaskGate.ts', 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
}).outputText
  .replaceAll("'vue'", JSON.stringify(import.meta.resolve('vue')))
  .replaceAll("'~/composables/useStudentTask'", JSON.stringify(delegates(['buildTaskResponsePayload', 'isTaskAnswerComplete', 'normalizeTaskQuestions', 'restoreTaskAnswers'], 'logic')))
  .replaceAll("'~/utils/histosphereApi'", JSON.stringify(delegates(['fetchSessionState', 'fetchTaskSubmissionStatus', 'saveTaskDraft', 'submitTaskAnswers', 'enterTaskInteraction', 'learnerAuthHeaders'], 'api')))
  .replaceAll("'~/utils/taskSubmissionWaiter'", JSON.stringify(delegates(['waitForReviewedTask'], 'waiter')));
const { useTaskGate } = await import(dataUrl(compiled));

const payload = (answers = []) => ({ contract_version: 'error_elicitation_v1', answers });
const complete = () => [
  { question_id: 'q01', value: 'Answer', rationale: 'First rationale' },
  { question_id: 'q02', value: 'b', rationale: 'Second rationale' },
  { question_id: 'q03', value: false, rationale: 'Third rationale' },
];
const stateFor = (id = 'session-a', answers = null, status = 'in_progress') => ({
  session: { id, status: 'task_started' }, event: { id: 'event-a' }, condition: { key: '01' }, personas: [], task,
  attempt: answers ? { id: 'attempt-a', status, response_payload: payload(answers) } : null,
});
const keyFor = (id = 'session-a') => `histosphere-task-draft:${id}:${task.id}`;
const memoryStorage = () => {
  const data = new Map();
  return { getItem: (key) => data.get(key) ?? null, setItem: (key, value) => data.set(key, String(value)), removeItem: (key) => data.delete(key) };
};
const deferred = () => {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
};
const flush = async () => { await nextTick(); await new Promise(setImmediate); await nextTick(); };

const withGate = async (options, run) => {
  const previous = Object.fromEntries(['window', 'useState', 'navigateTo', '__taskGateTest', 'setTimeout', 'clearTimeout', 'fetch'].map((key) => [key, globalThis[key]]));
  const storage = options.storage || memoryStorage();
  const state = options.state || stateFor();
  const states = new Map();
  const timers = new Map();
  let timerId = 0;
  const calls = { drafts: [], submits: [], navigation: [], status: [] };
  const routeSession = ref(state.session.id);
  globalThis.window = { sessionStorage: storage };
  globalThis.useState = (key, initial) => {
    if (!states.has(key)) states.set(key, ref(initial()));
    return states.get(key);
  };
  globalThis.navigateTo = async (route) => { calls.navigation.push(route); };
  globalThis.setTimeout = (callback, delay) => { const id = ++timerId; timers.set(id, { callback, delay }); return id; };
  globalThis.clearTimeout = (id) => timers.delete(id);
  globalThis.fetch = async () => { throw new Error('SSE offline fixture'); };
  globalThis.__taskGateTest = { logic, waiter, api: {
    learnerAuthHeaders: () => ({}),
    enterTaskInteraction: async () => ({ conversation_id: 'conversation-a', judgement: {} }),
    fetchSessionState: options.fetchState || (async () => state),
    saveTaskDraft: async (taskId, input) => {
      calls.drafts.push({ taskId, ...structuredClone(input) });
      await options.saveDraft?.(input);
      state.attempt = { id: 'attempt-a', status: 'in_progress', response_payload: structuredClone(input.responsePayload) };
      return {};
    },
    submitTaskAnswers: async (taskId, input) => {
      calls.submits.push({ taskId, ...structuredClone(input) });
      return { attempt_id: 'attempt-a' };
    },
    fetchTaskSubmissionStatus: async (id) => {
      calls.status.push(id);
      return options.submissionStatus || { attempt: { status: 'submitted' }, result: { conversation_id: 'conversation-a', judgement: { result: 'correct' } } };
    },
  } };
  const renderer = createRenderer({
    createElement: () => ({}), createText: () => ({}), createComment: () => ({}),
    insert() {}, remove() {}, setText() {}, setElementText() {}, patchProp() {},
    parentNode: () => null, nextSibling: () => null,
  });
  let gate;
  const app = renderer.createApp({ setup() { gate = useTaskGate(routeSession); return () => null; } });
  try {
    app.mount({});
    await flush();
    await run({ gate, storage, state, calls, routeSession, timers, async saveTick() {
      for (const [id, timer] of [...timers]) {
        if (timer.delay !== 700) continue;
        timers.delete(id);
        timer.callback();
      }
      await flush();
    } });
  } finally {
    app.unmount();
    await flush();
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete globalThis[key];
      else globalThis[key] = value;
    }
  }
};

test('task gate restores backend rationale and false without payload type/prompt metadata', async () => {
  await withGate({ state: stateFor('session-a', complete()) }, async ({ gate, calls }) => {
    assert.equal(gate.answers.value[2].value, false);
    assert.equal(gate.answers.value[2].rationale, 'Third rationale');
    assert.equal(gate.canSubmit.value, true);
    assert.equal(calls.drafts.length, 0);
    gate.answers.value[2].rationale = ' \n ';
    assert.equal(gate.canSubmit.value, false);
    await gate.submitTask();
    assert.equal(calls.submits.length, 0);
  });
});

test('task gate writes partial rationale immediately locally and autosaves the same new payload', async () => {
  await withGate({}, async ({ gate, storage, calls, saveTick }) => {
    gate.answers.value = logic.restoreTaskAnswers(task, payload([{ question_id: 'q03', value: false, rationale: '' }]));
    const local = JSON.parse(storage.getItem(keyFor()));
    assert.deepEqual(local.responsePayload, payload([{ question_id: 'q03', value: false, rationale: '' }]));
    assert.equal(gate.canSubmit.value, false);
    await saveTick();
    assert.deepEqual(calls.drafts[0].responsePayload, local.responsePayload);
    assert.equal(calls.drafts[0].sessionId, 'session-a');
    assert.equal(storage.getItem(keyFor()), null);
  });
});

test('task gate recovers unsynced local rationale after a failed save and reload', async () => {
  const storage = memoryStorage();
  const state = stateFor();
  await withGate({ storage, state, saveDraft: async () => { throw new Error('Offline'); } }, async ({ gate, saveTick }) => {
    gate.answers.value = logic.restoreTaskAnswers(task, payload([{ question_id: 'q01', value: null, rationale: 'Unfinished\nreason' }]));
    await saveTick();
    assert.ok(gate.submitError.value);
    assert.ok(storage.getItem(keyFor()));
  });
  await withGate({ storage, state }, async ({ gate, calls, saveTick }) => {
    assert.equal(gate.answers.value[0].value, null);
    assert.equal(gate.answers.value[0].rationale, 'Unfinished\nreason');
    await saveTick();
    assert.equal(calls.drafts[0].responsePayload.answers[0].rationale, 'Unfinished\nreason');
    assert.equal(storage.getItem(keyFor()), null);
  });
});

test('task gate keeps local drafts isolated by session and does not overwrite newer backend data', async () => {
  const storage = memoryStorage();
  storage.setItem(keyFor(), JSON.stringify({ basePayload: JSON.stringify(payload()), responsePayload: payload(complete()) }));
  await withGate({ storage, state: stateFor('session-b') }, async ({ gate, routeSession, state }) => {
    assert.deepEqual(gate.answers.value, []);
    assert.ok(storage.getItem(keyFor()));
    state.session.id = 'session-a';
    state.attempt = { status: 'in_progress', response_payload: payload([{ question_id: 'q01', value: 'New server answer', rationale: 'New server rationale' }]) };
    routeSession.value = 'session-a';
    await flush();
    assert.equal(gate.answers.value[0].value, 'New server answer');
    assert.equal(storage.getItem(keyFor()), null);
  });
});

test('task gate serializes autosaves and preserves edits made during an in-flight save across reload', async () => {
  const storage = memoryStorage();
  const state = stateFor();
  const pending = deferred();
  await withGate({ storage, state, saveDraft: () => pending.promise }, async ({ gate, calls, saveTick }) => {
    gate.answers.value = logic.restoreTaskAnswers(task, payload(complete()));
    await saveTick();
    gate.answers.value = logic.updateTaskAnswer(gate.answers.value, logic.normalizeTaskQuestions(task)[0], { rationale: 'Newest rationale' });
    await saveTick();
    assert.equal(calls.drafts.length, 1);
    pending.resolve();
    await flush();
    assert.equal(JSON.parse(storage.getItem(keyFor())).responsePayload.answers[0].rationale, 'Newest rationale');
  });
  await withGate({ storage, state }, async ({ gate, calls, saveTick }) => {
    assert.equal(gate.answers.value[0].rationale, 'Newest rationale');
    await saveTick();
    assert.equal(calls.drafts[0].responsePayload.answers[0].rationale, 'Newest rationale');
  });
});

test('task gate waits for pending autosave before submit, sends one new payload, and clears only its draft', async () => {
  const pending = deferred();
  await withGate({ saveDraft: () => pending.promise }, async ({ gate, storage, calls, saveTick }) => {
    storage.setItem(keyFor('other-session'), 'keep');
    gate.answers.value = logic.restoreTaskAnswers(task, payload(complete()));
    await saveTick();
    gate.answers.value[2].rationale = 'Latest false rationale';
    const submission = gate.submitTask();
    await gate.submitTask();
    await flush();
    assert.equal(calls.submits.length, 0);
    pending.resolve();
    await submission;
    assert.equal(calls.submits.length, 1);
    assert.deepEqual(Object.keys(calls.submits[0].responsePayload).sort(), ['answers', 'contract_version']);
    assert.deepEqual(calls.submits[0].responsePayload.answers[2], { question_id: 'q03', value: false, rationale: 'Latest false rationale' });
    assert.equal(storage.getItem(keyFor()), null);
    assert.equal(storage.getItem(keyFor('other-session')), 'keep');
    assert.deepEqual(calls.navigation, [{ path: '/conversations/conversation-a' }]);
  });
});

test('task gate recovers newer edits when reloaded before an older autosave acknowledgement arrives', async () => {
  const storage = memoryStorage();
  const state = stateFor();
  const pending = deferred();
  await withGate({ storage, state, saveDraft: () => pending.promise }, async ({ gate, calls, saveTick }) => {
    gate.answers.value = logic.restoreTaskAnswers(task, payload(complete()));
    await saveTick();
    gate.answers.value[2].rationale = 'Reason typed while the request was in flight';
    state.attempt = { status: 'in_progress', response_payload: calls.drafts[0].responsePayload };
  });
  await withGate({ storage, state }, async ({ gate, saveTick, calls }) => {
    assert.equal(gate.answers.value[2].rationale, 'Reason typed while the request was in flight');
    await saveTick();
    assert.equal(calls.drafts[0].responsePayload.answers[2].rationale, 'Reason typed while the request was in flight');
  });
});

test('task gate keeps submitted answers locked when processing fails while awaiting researcher retry', async () => {
  await withGate({ submissionStatus: { attempt: { status: 'failed' }, error: 'Processing unavailable' } }, async ({ gate, storage, calls }) => {
    gate.answers.value = logic.restoreTaskAnswers(task, payload(complete()));
    void gate.submitTask();
    await flush();
    assert.equal(gate.waitingState.value.stage, 'failed');
    assert.equal(gate.judgement.value, null);
    assert.equal(gate.canSubmit.value, false);
    assert.equal(gate.isSubmitting.value, true);
    assert.equal(gate.answers.value[2].value, false);
    assert.equal(JSON.parse(storage.getItem(keyFor())).responsePayload.answers[2].rationale, 'Third rationale');
    assert.equal(calls.navigation.length, 0);
  });
});

test('task gate resumes processing from backend answers, never an unsent local replacement', async () => {
  const storage = memoryStorage();
  storage.setItem(keyFor(), JSON.stringify({ basePayload: JSON.stringify(payload(complete())), responsePayload: payload([]) }));
  await withGate({ storage, state: stateFor('session-a', complete(), 'processing') }, async ({ gate, calls }) => {
    assert.equal(gate.answers.value[2].value, false);
    assert.equal(gate.answers.value[2].rationale, 'Third rationale');
    assert.equal(calls.submits.length, 0);
    assert.equal(calls.status.length, 1);
    assert.equal(storage.getItem(keyFor()), null);
    assert.equal(calls.navigation.length, 1);
  });
});

test('task gate tolerates malformed or unavailable browser storage without blocking backend autosave', async () => {
  const malformed = memoryStorage();
  malformed.setItem(keyFor(), '{broken');
  const unavailable = { getItem() { throw new Error('Denied'); }, setItem() { throw new Error('Full'); }, removeItem() { throw new Error('Denied'); } };
  for (const storage of [malformed, unavailable]) {
    await withGate({ storage }, async ({ gate, calls, saveTick }) => {
      gate.answers.value = logic.restoreTaskAnswers(task, payload(complete()));
      await saveTick();
      assert.equal(calls.drafts.length, 1);
      assert.equal(gate.submitError.value, null);
    });
  }
});

test('task gate ignores a stale session response after navigating to another session', async () => {
  const old = deferred();
  await withGate({ fetchState: (id) => id === 'session-a' ? old.promise : Promise.resolve(stateFor(id)) }, async ({ gate, routeSession }) => {
    routeSession.value = 'session-b';
    await flush();
    old.resolve(stateFor('session-a', complete()));
    await flush();
    assert.equal(gate.taskData.value.session_id, 'session-b');
    assert.deepEqual(gate.answers.value, []);
  });
});
