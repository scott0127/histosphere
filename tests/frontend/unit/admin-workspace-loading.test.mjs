import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { effectScope } from 'vue';
import ts from 'typescript';

const dataUrl = (source) => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const logic = await globalThis.loadTsModule('utils/adminWorkspaceState.ts');
const task = await globalThis.loadTsModule('composables/useTaskControl.ts');
let compiled = ts.transpileModule(await readFile('composables/useAdminWorkspace.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText.replace(/from (['"])vue\1/g, `from '${import.meta.resolve('vue')}'`);
for (const [path, area] of [
  ['~/utils/adminWorkspaceState', 'logic'], ['~/composables/useTaskControl', 'task'],
  ['~/utils/adminSession', 'session'], ['~/utils/histosphereApi', 'api'],
]) {
  const match = [...compiled.matchAll(/import \{([^}]+)\} from ['"]([^'"]+)['"];?/g)].find((item) => item[2] === path);
  const delegates = match[1].split(',').map((name) => name.trim()).filter(Boolean).map((name) =>
    `export const ${name} = (...args) => globalThis.__adminWorkspaceLoading.${area}.${name}(...args);`).join('\n');
  compiled = compiled.replace(match[0], `import { ${match[1]} } from '${dataUrl(delegates)}';`);
}
const { useAdminWorkspace } = await import(dataUrl(compiled));
const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const snapshot = (id = 'snapshot-one') => ({ id, events: [], conditions: [], sessions: [], research_logs: [] });
const setup = (api = {}) => {
  const previous = globalThis.__adminWorkspaceLoading;
  const keys = [];
  globalThis.__adminWorkspaceLoading = {
    logic, task,
    session: {
      setAdminSessionKey: (key) => keys.push(['set', key]),
      clearAdminSessionKey: () => keys.push(['clear']),
      getAdminSessionKey: () => '',
    },
    api: { fetchAdminAuthUsers: async () => ({ users: [] }), ...api },
  };
  const scope = effectScope();
  const state = scope.run(useAdminWorkspace);
  state.adminKey.value = 'admin-key';
  return { state, keys, stop: () => scope.stop(), dispose() { scope.stop(); globalThis.__adminWorkspaceLoading = previous; } };
};

test('closing research during refresh suppresses both late success and late failure', async () => {
  for (const outcome of ['success', 'failure']) {
    const response = deferred();
    const workspace = setup({ fetchAdminSessionResearch: () => response.promise });
    try {
      workspace.state.selectedResearchSession.value = { session: { id: 'existing-session' } };
      const pending = workspace.state.loadSessionResearch('existing-session');
      workspace.state.closeSessionResearch();
      assert.equal(workspace.state.researchSessionLoading.value, false);
      if (outcome === 'success') response.resolve({ session: { id: 'existing-session' } });
      else response.reject(new Error('late failure'));
      await pending;
      assert.equal(workspace.state.selectedResearchSession.value, null);
      assert.equal(workspace.state.error.value, null);
    } finally { workspace.dispose(); }
  }
});

test('a superseded research response cannot replace the selected session or clear its pending indicator', async () => {
  const first = deferred();
  const second = deferred();
  const workspace = setup({ fetchAdminSessionResearch: (_key, id) => id === 'first' ? first.promise : second.promise });
  try {
    const oldRequest = workspace.state.loadSessionResearch('first');
    const newRequest = workspace.state.loadSessionResearch('second');
    first.resolve({ session: { id: 'first' } });
    await oldRequest;
    assert.equal(workspace.state.selectedResearchSession.value, null);
    assert.equal(workspace.state.researchSessionLoading.value, true);
    second.resolve({ session: { id: 'second' } });
    await newRequest;
    assert.equal(workspace.state.selectedResearchSession.value.session.id, 'second');
    assert.equal(workspace.state.researchSessionLoading.value, false);
  } finally { workspace.dispose(); }
});

test('changing the admin key during a research request suppresses its content without leaving loading stuck', async () => {
  const response = deferred();
  const workspace = setup({ fetchAdminSessionResearch: () => response.promise });
  try {
    const pending = workspace.state.loadSessionResearch('old-credentials-session');
    workspace.state.adminKey.value = 'different-key';
    response.resolve({ session: { id: 'old-credentials-session' } });
    await pending;
    assert.equal(workspace.state.selectedResearchSession.value, null);
    assert.equal(workspace.state.researchSessionLoading.value, false);
  } finally { workspace.dispose(); }
});

test('workspace reset and scope disposal cancel pending snapshot, auth, and research reads', async () => {
  for (const action of ['reset', 'dispose']) {
    const summary = deferred();
    const users = deferred();
    const research = deferred();
    const workspace = setup({
      fetchAdminSnapshot: () => summary.promise,
      fetchAdminAuthUsers: () => users.promise,
      fetchAdminSessionResearch: () => research.promise,
    });
    try {
      const pendingSnapshot = workspace.state.loadSnapshot();
      const pendingUsers = workspace.state.loadAuthUsers();
      const pendingResearch = workspace.state.loadSessionResearch('session-one');
      if (action === 'reset') workspace.state.resetWorkspace();
      else workspace.stop();
      summary.resolve(snapshot());
      users.resolve({ users: [{ id: 'private-user' }] });
      research.resolve({ session: { id: 'session-one' } });
      assert.equal(await pendingSnapshot, false);
      await Promise.all([pendingUsers, pendingResearch]);
      assert.equal(workspace.state.snapshot.value, null);
      assert.deepEqual(workspace.state.authUsers.value, []);
      assert.equal(workspace.state.selectedResearchSession.value, null);
      assert.equal(workspace.state.researchSessionLoading.value, false);
      assert.equal(workspace.state.error.value, null);
      assert.equal(workspace.keys.some(([operation]) => operation === 'set'), false);
    } finally { workspace.dispose(); }
  }
});

test('reset while snapshot is awaiting auth users returns false and keeps the cleared workspace empty', async () => {
  const users = deferred();
  const workspace = setup({ fetchAdminSnapshot: async () => snapshot(), fetchAdminAuthUsers: () => users.promise });
  try {
    const pending = workspace.state.loadSnapshot();
    await Promise.resolve();
    assert.ok(workspace.state.snapshot.value);
    workspace.state.resetWorkspace();
    users.resolve({ users: [{ id: 'private-user' }] });
    assert.equal(await pending, false);
    assert.equal(workspace.state.snapshot.value, null);
    assert.deepEqual(workspace.state.authUsers.value, []);
    assert.deepEqual(workspace.keys.at(-1), ['clear']);
  } finally { workspace.dispose(); }
});

test('a stale snapshot failure cannot clear a newly loaded snapshot or its admin credentials', async () => {
  const old = deferred();
  let calls = 0;
  const workspace = setup({ fetchAdminSnapshot: () => ++calls === 1 ? old.promise : Promise.resolve(snapshot('newer')) });
  try {
    const previous = workspace.state.loadSnapshot();
    assert.equal(await workspace.state.loadSnapshot(), true);
    old.reject(new Error('old credentials rejected'));
    assert.equal(await previous, false);
    assert.equal(workspace.state.snapshot.value.id, 'newer');
    assert.equal(workspace.state.error.value, null);
    assert.deepEqual(workspace.keys, [['set', 'admin-key']]);
  } finally { workspace.dispose(); }
});
