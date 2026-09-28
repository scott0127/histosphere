import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRenderer, createSSRApp, h, nextTick, ref } from 'vue';
import { renderToString } from 'vue/server-renderer';
import ts from 'typescript';
import { reviewSnapshot } from './task-review.test.mjs';
import { reviewQuestionComponent } from './admin-monitor-question.test.mjs';

const dataUrl = source => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const logic = await globalThis.loadTsModule('utils/taskReview.ts');
let compiled = ts.transpileModule(await readFile('composables/useAdminMonitor.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText.replace(/from (['"])vue\1/g, `from '${import.meta.resolve('vue')}'`);
for (const [path, area] of [
  ['~/utils/taskReview', 'logic'], ['~/utils/taskReviewApi', 'api'],
  ['~/utils/adminSession', 'session'], ['~/utils/sessionEventStream', 'events'],
]) {
  const match = [...compiled.matchAll(/import \{([^}]+)\} from ['"]([^'"]+)['"];?/g)].find(item => item[2] === path);
  const delegates = match[1].split(',').map(name => name.trim()).filter(Boolean).map(name =>
    `export const ${name} = (...args) => globalThis.__monitorTest.${area}.${name}(...args);`).join('\n');
  compiled = compiled.replace(match[0], `import { ${match[1]} } from '${dataUrl(delegates)}';`);
}
const { useAdminMonitor } = await import(dataUrl(compiled));
const setup = async () => {
  let stored = reviewSnapshot();
  const previous = globalThis.__monitorTest;
  let state;
  const calls = [];
  globalThis.__monitorTest = {
    logic,
    session: { setAdminSessionKey() {}, clearAdminSessionKey() {}, getAdminSessionKey: () => '' },
    events: { subscribeSessionEvents: () => () => {} },
    api: {
      fetchAdminMonitor: async () => structuredClone(stored),
      saveAdminTaskReview: async (_key, id, version, question_results) => {
        calls.push({ id, version, question_results });
        assert.equal(version, stored.attempt.review_version);
        stored.attempt.review_payload.question_results = structuredClone(question_results);
        stored.attempt.review_version += 1;
        return structuredClone(stored.attempt);
      },
      approveAdminTaskReview: async () => { throw new Error('Unexpected approval'); },
    },
  };
  const app = createSSRApp({ setup() { state = useAdminMonitor(ref('s1')); return () => h('div'); } });
  await renderToString(app);
  state.adminKey.value = 'test-admin';
  await state.refresh();
  return { state, calls, updateServer: fn => fn(stored), dispose() { state.logout(); globalThis.__monitorTest = previous; } };
};

test('monitor preserves dirty review edits when an event refresh arrives and blocks stale saves', async () => {
  const { state, updateServer, calls, dispose } = await setup();
  try {
    state.updateQuestion('q01', { reasoning_feedback: 'Local unsaved explanation' });
    await state.refresh();
    assert.equal(state.drafts.value[0].reasoning_feedback, 'Local unsaved explanation');
    assert.equal(state.dirty.value, true);
    updateServer(snapshot => { snapshot.attempt.review_version = 1; });
    await state.refresh();
    assert.equal(state.conflict.value, true);
    await state.saveQuestion('q01');
    assert.equal(calls.length, 0);
    assert.equal(state.drafts.value[0].reasoning_feedback, 'Local unsaved explanation');
  } finally { dispose(); }
});

test('monitor requires explicit review of every question and editing invalidates a prior confirmation', async () => {
  const { state, calls, dispose } = await setup();
  try {
    assert.equal(state.reviewedCount.value, 0);
    assert.equal(state.canApprove.value, false);
    await state.saveQuestion('q01', true);
    assert.equal(state.reviewedCount.value, 1);
    assert.equal(state.canApprove.value, false);
    await state.saveQuestion('q03', true);
    assert.equal(state.canApprove.value, true);
    assert.deepEqual(calls.map(call => call.version), [0, 1]);
    state.updateQuestion('q03', { reasoning_feedback: 'Revised explanation' });
    assert.equal(state.reviewedCount.value, 1);
    assert.equal(state.canApprove.value, false);
    await state.saveQuestion('q03', false);
    assert.equal(state.dirty.value, false);
    assert.equal(state.canApprove.value, false);
  } finally { dispose(); }
});

test('rendered save and confirm buttons emit to the monitor and call the review API with the edited text', async () => {
  const { state, calls, dispose } = await setup();
  const elements = [];
  const renderer = createRenderer({
    createElement: tag => { const element = { tag, props: {}, text: '', parent: null }; elements.push(element); return element; },
    createText: text => ({ text }), createComment: text => ({ text }),
    insert: (element, parent) => { element.parent = parent; }, remove() {},
    setText: (element, text) => { element.text = text; },
    setElementText: (element, text) => { element.text = text; },
    patchProp: (element, key, _previous, value) => { element.props[key] = value; },
    parentNode: element => element.parent, nextSibling: () => null,
  });
  const app = renderer.createApp({ render() {
    const row = state.questions.value[0];
    return h(reviewQuestionComponent, {
      row, draft: state.drafts.value[0], index: 0, disabled: state.saving.value || state.conflict.value,
      onUpdate: patch => state.updateQuestion(row.question.id, patch),
      onSave: confirmed => state.saveQuestion(row.question.id, confirmed),
    });
  } });
  app.component('Icon', { render: () => h('span') });
  try {
    app.mount({});
    const textarea = elements.find(element => element.props['aria-label'] === 'q01 理由判定說明');
    textarea.props.onInput({ target: { value: 'Reviewed explanation entered through the rendered textarea' } });
    await nextTick();
    assert.equal(state.dirty.value, true);
    const saveButton = elements.find(element => element.tag === 'button' && element.text === '保存草稿');
    saveButton.props.onClick();
    await new Promise(setImmediate);
    await nextTick();
    assert.equal(calls.length, 1);
    assert.equal(calls[0].question_results[0].reviewed, false);
    assert.equal(calls[0].question_results[0].reasoning_feedback, 'Reviewed explanation entered through the rendered textarea');
    assert.match(state.notice.value, /草稿已保存/);
    const confirmButton = elements.find(element => element.tag === 'button' && element.props.class?.includes('admin-button-secondary'));
    confirmButton.props.onClick();
    await new Promise(setImmediate);
    await nextTick();
    assert.equal(calls.length, 2);
    assert.equal(calls[1].question_results[0].reviewed, true);
    assert.equal(state.reviewedCount.value, 1);
  } finally { app.unmount(); dispose(); }
});
