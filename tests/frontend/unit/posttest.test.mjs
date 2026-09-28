import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRenderer, nextTick } from 'vue';
import ts from 'typescript';

const logic = await globalThis.loadTsModule('utils/posttest.ts');
const api = await globalThis.loadTsModule('utils/histosphereApi.ts');
const auth = await globalThis.loadTsModule('utils/authSession.ts');
const dataUrl = (source) => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const delegates = (names, area) => dataUrl(names.map((name) =>
  `export const ${name} = (...args) => globalThis.__posttestTest.${area}.${name}(...args);`).join('\n'));
const source = await readFile('composables/usePosttest.ts', 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
}).outputText
  .replaceAll("'vue'", JSON.stringify(import.meta.resolve('vue')))
  .replaceAll("'~/utils/posttest'", JSON.stringify(delegates([
    'isEngagementComplete', 'isHatComplete', 'posttestDraftPayload', 'posttestDraftSignature',
  ], 'logic')))
  .replaceAll("'~/utils/histosphereApi'", JSON.stringify(delegates([
    'advancePosttest', 'fetchPosttest', 'savePosttestDraft', 'startPosttest', 'submitPosttest',
  ], 'api')));
const { usePosttest } = await import(dataUrl(compiled));

const completedEngagement = () => ({ engagement_1: 1, engagement_2: 3, engagement_3: 5 });
const completedHat = () => ({ hat_1: 'My judgment', hat_2: 'My explanation\nwith evidence' });
const stateFor = (stage = 'engagement', overrides = {}) => ({
  eligible: true,
  response: {
    id: 'response-a', session_id: 'session-a', stage, revision: 1,
    engagement_answers: stage === 'engagement' ? {} : completedEngagement(),
    hat_answers: stage === 'completed' ? completedHat() : {},
    ...overrides,
  },
});
const storageKey = (id = 'session-a') => `histosphere-posttest-draft:${id}`;
const memoryStorage = () => {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
  };
};
const deferred = () => {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
};
const flush = async () => { await nextTick(); await new Promise(setImmediate); await nextTick(); };

const withPosttest = async (options, run) => {
  const previous = Object.fromEntries([
    'window', 'sessionStorage', '__posttestTest', 'setTimeout', 'clearTimeout',
  ].map((key) => [key, globalThis[key]]));
  const storage = options.storage || memoryStorage();
  const server = options.server || stateFor();
  const calls = { fetches: [], starts: [], saves: [], advances: [], submits: [] };
  const timers = new Map();
  const listeners = new Map();
  let timerId = 0;
  globalThis.sessionStorage = storage;
  globalThis.window = {
    sessionStorage: storage,
    addEventListener: (name, callback) => listeners.set(name, callback),
    removeEventListener: (name, callback) => { if (listeners.get(name) === callback) listeners.delete(name); },
  };
  globalThis.setTimeout = (callback, delay) => {
    const id = ++timerId;
    timers.set(id, { callback, delay });
    return id;
  };
  globalThis.clearTimeout = (id) => timers.delete(id);
  const checkRevision = (revision) => {
    if (revision !== server.response.revision) throw { statusCode: 409 };
  };
  globalThis.__posttestTest = { logic, api: {
    fetchPosttest: async (id) => { calls.fetches.push(id); return structuredClone(server); },
    startPosttest: async (id) => {
      calls.starts.push(id);
      server.response = stateFor().response;
      return structuredClone(server);
    },
    savePosttestDraft: async (id, input) => {
      calls.saves.push({ id, input: structuredClone(input) });
      await options.beforeSave?.(input);
      checkRevision(input.revision);
      if (input.engagement_answers) server.response.engagement_answers = structuredClone(input.engagement_answers);
      if (input.hat_answers) server.response.hat_answers = structuredClone(input.hat_answers);
      server.response.revision += 1;
      const accepted = structuredClone(server);
      await options.afterSave?.(input);
      return accepted;
    },
    advancePosttest: async (id, revision) => {
      calls.advances.push({ id, revision });
      checkRevision(revision);
      server.response.stage = 'hat';
      server.response.revision += 1;
      return structuredClone(server);
    },
    submitPosttest: async (id, revision) => {
      calls.submits.push({ id, revision });
      await options.beforeSubmit?.();
      checkRevision(revision);
      server.response.stage = 'completed';
      server.response.revision += 1;
      return structuredClone(server);
    },
  } };
  const renderer = createRenderer({
    createElement: () => ({}), createText: () => ({}), createComment: () => ({}),
    insert() {}, remove() {}, setText() {}, setElementText() {}, patchProp() {},
    parentNode: () => null, nextSibling: () => null,
  });
  let posttest;
  const app = renderer.createApp({ setup() {
    posttest = usePosttest(options.sessionId || 'session-a');
    return () => null;
  } });
  try {
    app.mount({});
    await flush();
    await run({ posttest, storage, server, calls, listeners, async saveTick() {
      for (const [id, timer] of [...timers]) {
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

test('posttest validation requires each explicit Likert answer and nonblank bounded HAT responses', () => {
  assert.equal(logic.isEngagementComplete({}), false);
  assert.equal(logic.isEngagementComplete({ ...completedEngagement(), engagement_2: null }), false);
  for (const invalid of [0, 6, 2.5, '3', NaN]) {
    assert.equal(logic.isEngagementComplete({ ...completedEngagement(), engagement_2: invalid }), false);
  }
  assert.equal(logic.isEngagementComplete(completedEngagement()), true);
  assert.equal(logic.isHatComplete({}), false);
  assert.equal(logic.isHatComplete({ ...completedHat(), hat_2: ' \n ' }), false);
  assert.equal(logic.isHatComplete({ ...completedHat(), hat_2: 'x'.repeat(10001) }), false);
  assert.equal(logic.isHatComplete(completedHat()), true);
});

test('posttest draft payload only contains authored IDs from the active stage and does not preselect answers', () => {
  const engagement = { engagement_1: null, engagement_2: 4, unknown: 2 };
  const hat = { hat_1: 'Preserved answer', unknown: 'Do not submit' };
  assert.deepEqual(logic.posttestDraftPayload(stateFor().response, engagement, hat), {
    revision: 1, engagement_answers: { engagement_2: 4 },
  });
  assert.deepEqual(logic.posttestDraftPayload(stateFor('hat').response, engagement, hat), {
    revision: 1, hat_answers: { hat_1: 'Preserved answer', hat_2: '' },
  });
  const payload = { revision: 1, engagement_answers: { engagement_2: 4 } };
  assert.equal(logic.posttestDraftSignature(payload), logic.posttestDraftSignature({ ...payload, revision: 2 }));
});

test('posttest API sends the session endpoint, bearer authentication, and explicit revision to every mutation', async () => {
  const previousWindow = globalThis.window;
  const token = auth.getCurrentAccessToken();
  const storage = memoryStorage();
  globalThis.window = { localStorage: memoryStorage(), sessionStorage: storage };
  auth.setCurrentAccessToken('posttest-test-token');
  try {
    const calls = [];
    const fetcher = async (url, options) => { calls.push({ url, options }); return { accepted: true }; };
    const draft = { revision: 7, hat_answers: completedHat() };
    await api.fetchPosttest('session-a', fetcher);
    await api.startPosttest('session-a', fetcher);
    await api.savePosttestDraft('session-a', draft, fetcher);
    await api.advancePosttest('session-a', 8, fetcher);
    await api.submitPosttest('session-a', 9, fetcher);
    assert.deepEqual(calls.map(({ url, options }) => [options.method || 'GET', url, options.body]), [
      ['GET', '/api/sessions/session-a/posttest', undefined],
      ['POST', '/api/sessions/session-a/posttest/start', undefined],
      ['PATCH', '/api/sessions/session-a/posttest', draft],
      ['POST', '/api/sessions/session-a/posttest/advance', { revision: 8 }],
      ['POST', '/api/sessions/session-a/posttest/submit', { revision: 9 }],
    ]);
    for (const { options } of calls) assert.deepEqual(options.headers, { Authorization: 'Bearer posttest-test-token' });
    storage.setItem('histosphere_admin_key', 'posttest-admin-test');
    await api.fetchPosttest('session-a', fetcher);
    assert.deepEqual(calls.at(-1).options.headers, { 'x-admin-key': 'posttest-admin-test' });
  } finally {
    auth.setCurrentAccessToken(token);
    globalThis.window = previousWindow;
  }
});

test('posttest starts an eligible session with unanswered inputs and never starts an ineligible session', async () => {
  await withPosttest({ server: { eligible: true, response: null } }, async ({ posttest, calls }) => {
    assert.deepEqual(calls.starts, ['session-a']);
    assert.deepEqual(posttest.engagement.value, {});
    assert.deepEqual(posttest.hat.value, {});
    assert.equal(posttest.completedCount.value, 0);
    assert.equal(posttest.canContinue.value, false);
    await posttest.continueStage();
    assert.equal(calls.advances.length, 0);
  });
  await withPosttest({ server: { eligible: false, response: null } }, async ({ calls }) => {
    assert.equal(calls.starts.length, 0);
    assert.equal(calls.saves.length, 0);
  });
});

test('posttest retains edits during an in-flight save and serializes the next save with the acknowledged revision', async () => {
  const pending = deferred();
  await withPosttest({ server: stateFor('hat'), beforeSave: () => pending.promise }, async ({ posttest, calls, storage, server, saveTick }) => {
    posttest.updateHat({ hat_1: 'First draft' });
    await saveTick();
    posttest.updateHat({ hat_1: 'Newest draft', hat_2: 'Extra rationale' });
    await saveTick();
    assert.equal(calls.saves.length, 1);
    assert.equal(JSON.parse(storage.getItem(storageKey())).payload.hat_answers.hat_1, 'Newest draft');
    pending.resolve();
    await flush();
    assert.equal(calls.saves.length, 2);
    assert.deepEqual(calls.saves.map(({ input }) => input.revision), [1, 2]);
    assert.equal(server.response.hat_answers.hat_1, 'Newest draft');
    assert.equal(posttest.hat.value.hat_1, 'Newest draft');
    assert.equal(posttest.dirty.value, false);
    assert.equal(storage.getItem(storageKey()), null);
  });
});

test('posttest waits for autosave before advancing and submits only after a successful server acknowledgement', async () => {
  const pending = deferred();
  await withPosttest({ beforeSave: () => pending.promise }, async ({ posttest, calls, saveTick }) => {
    posttest.updateEngagement(completedEngagement());
    await saveTick();
    const advancing = posttest.continueStage();
    await posttest.continueStage();
    await flush();
    assert.equal(calls.advances.length, 0);
    pending.resolve();
    await advancing;
    assert.deepEqual(calls.advances, [{ id: 'session-a', revision: 2 }]);
    assert.equal(posttest.stage.value, 'hat');
    assert.equal(posttest.canContinue.value, false);
    posttest.updateHat(completedHat());
    await posttest.continueStage();
    assert.equal(posttest.stage.value, 'completed');
    assert.deepEqual(calls.submits, [{ id: 'session-a', revision: 4 }]);
  });
});

test('posttest failed save preserves the local draft and resumes it after reload without changing sessions', async () => {
  const storage = memoryStorage();
  const server = stateFor('hat');
  storage.setItem(storageKey('other-session'), 'keep');
  await withPosttest({ storage, server, beforeSave: async () => { throw new Error('Offline'); } }, async ({ posttest, saveTick }) => {
    posttest.updateHat({ hat_1: 'Unsent draft\nline two' });
    await saveTick();
    assert.ok(posttest.error.value);
    assert.equal(posttest.dirty.value, true);
    assert.ok(storage.getItem(storageKey()));
  });
  await withPosttest({ storage, server }, async ({ posttest, saveTick, calls }) => {
    assert.equal(posttest.hat.value.hat_1, 'Unsent draft\nline two');
    assert.equal(posttest.conflict.value, false);
    await saveTick();
    assert.equal(calls.saves[0].input.hat_answers.hat_1, 'Unsent draft\nline two');
    assert.equal(storage.getItem(storageKey()), null);
    assert.equal(storage.getItem(storageKey('other-session')), 'keep');
  });
});

test('posttest recovers newer typing when the server accepted an older save but its acknowledgement was lost', async () => {
  const storage = memoryStorage();
  const server = stateFor('hat');
  const acknowledgement = deferred();
  await withPosttest({ storage, server, afterSave: () => acknowledgement.promise }, async ({ posttest, saveTick }) => {
    posttest.updateHat({ hat_1: 'Accepted older draft' });
    await saveTick();
    assert.equal(server.response.hat_answers.hat_1, 'Accepted older draft');
    posttest.updateHat({ hat_1: 'New typing before reload' });
  });
  await withPosttest({ storage, server }, async ({ posttest, calls, saveTick }) => {
    assert.equal(posttest.hat.value.hat_1, 'New typing before reload');
    assert.equal(posttest.conflict.value, false);
    await saveTick();
    assert.equal(calls.saves[0].input.revision, 2);
    assert.equal(server.response.hat_answers.hat_1, 'New typing before reload');
    assert.equal(storage.getItem(storageKey()), null);
  });
});

test('posttest handles a truly newer server draft as a conflict and never overwrites it automatically', async () => {
  const storage = memoryStorage();
  const server = stateFor('hat');
  await withPosttest({ storage, server, beforeSave: async () => { throw new Error('Offline'); } }, async ({ posttest, saveTick }) => {
    posttest.updateHat({ hat_1: 'Local draft' });
    await saveTick();
  });
  server.response.hat_answers = { hat_1: 'Changed on another tab' };
  server.response.revision += 1;
  await withPosttest({ storage, server }, async ({ posttest, calls, saveTick }) => {
    assert.equal(posttest.conflict.value, true);
    assert.equal(posttest.hat.value.hat_1, 'Local draft');
    await saveTick();
    assert.equal(calls.saves.length, 0);
    assert.equal(server.response.hat_answers.hat_1, 'Changed on another tab');
    await posttest.load();
    assert.equal(posttest.conflict.value, true);
    assert.equal(posttest.hat.value.hat_1, 'Local draft');
    await saveTick();
    assert.equal(calls.saves.length, 0);
    await posttest.load(true);
    assert.equal(posttest.conflict.value, false);
    assert.equal(posttest.hat.value.hat_1, 'Changed on another tab');
    assert.equal(storage.getItem(storageKey()), null);
  });
});

test('posttest retries a lost acknowledgement against the actual server revision without losing newer typing', async () => {
  let loseAcknowledgement = true;
  await withPosttest({ server: stateFor('hat'), afterSave: async () => {
    if (loseAcknowledgement) { loseAcknowledgement = false; throw new Error('Connection dropped after commit'); }
  } }, async ({ posttest, server, calls, saveTick, storage }) => {
    posttest.updateHat({ hat_1: 'Accepted despite lost response' });
    await saveTick();
    assert.equal(server.response.revision, 2);
    assert.equal(posttest.response.value.revision, 1);
    assert.ok(posttest.error.value);
    posttest.updateHat({ hat_1: 'New typing after lost response' });
    await saveTick();
    assert.equal(posttest.conflict.value, false);
    assert.equal(posttest.error.value, '');
    assert.deepEqual(calls.saves.map(({ input }) => input.revision), [1, 2]);
    assert.equal(server.response.hat_answers.hat_1, 'New typing after lost response');
    assert.equal(posttest.dirty.value, false);
    assert.equal(storage.getItem(storageKey()), null);
  });
});

test('posttest failed final submission stays in HAT with preserved answers and permits retry', async () => {
  let offline = true;
  await withPosttest({ server: stateFor('hat'), beforeSubmit: async () => { if (offline) throw new Error('Offline'); } }, async ({ posttest, server, calls }) => {
    posttest.updateHat(completedHat());
    await posttest.continueStage();
    assert.equal(posttest.stage.value, 'hat');
    assert.equal(server.response.stage, 'hat');
    assert.deepEqual(posttest.hat.value, completedHat());
    assert.equal(posttest.submitting.value, false);
    assert.equal(posttest.canContinue.value, true);
    assert.ok(posttest.error.value);
    offline = false;
    await posttest.continueStage();
    assert.equal(calls.submits.length, 2);
    assert.equal(posttest.stage.value, 'completed');
  });
});

test('posttest completed sessions ignore stale local drafts and do not autosave additional edits', async () => {
  const storage = memoryStorage();
  storage.setItem(storageKey(), JSON.stringify({ stage: 'hat', base: '{}', payload: { revision: 1, hat_answers: { hat_1: 'Stale' } } }));
  await withPosttest({ storage, server: stateFor('completed') }, async ({ posttest, calls, saveTick }) => {
    assert.equal(posttest.stage.value, 'completed');
    assert.deepEqual(posttest.hat.value, completedHat());
    assert.equal(posttest.canContinue.value, false);
    await posttest.continueStage();
    assert.equal(calls.submits.length, 0);
    assert.equal(storage.getItem(storageKey()), null);
    posttest.updateHat({ hat_1: 'Ignored update' });
    await saveTick();
    assert.equal(calls.saves.length, 0);
  });
});

test('posttest tolerates unavailable browser storage while server autosave remains functional', async () => {
  const storage = {
    getItem() { throw new Error('Storage denied'); },
    setItem() { throw new Error('Storage denied'); },
    removeItem() { throw new Error('Storage denied'); },
  };
  await withPosttest({ storage }, async ({ posttest, calls, saveTick }) => {
    posttest.updateEngagement(completedEngagement());
    await saveTick();
    assert.equal(calls.saves.length, 1);
    assert.equal(posttest.error.value, '');
    assert.equal(posttest.dirty.value, false);
  });
});
