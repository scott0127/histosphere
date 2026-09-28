import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRenderer, nextTick } from 'vue';
import { parse, compileScript } from 'vue/compiler-sfc';
import ts from 'typescript';

const dataUrl = (value) => `data:text/javascript;base64,${Buffer.from(value).toString('base64')}`;
const filename = 'components/session/SessionClosureDialog.vue';
const { descriptor } = parse(await readFile(filename, 'utf8'), { filename });
const script = compileScript(descriptor, { id: filename, inlineTemplate: true }).content;
const output = ts.transpileModule(script, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText
  .replaceAll('from "vue"', `from ${JSON.stringify(import.meta.resolve('vue'))}`)
  .replaceAll("from 'vue'", `from ${JSON.stringify(import.meta.resolve('vue'))}`)
  .replaceAll("'~/utils/histosphereApi'", JSON.stringify(dataUrl(`
    export const fetchSessionState = (...args) => globalThis.__closureApi.fetch(...args);
    export const submitSessionClosure = (...args) => globalThis.__closureApi.submit(...args);
  `)));
const component = (await import(dataUrl(output))).default;
const node = (type, text = '') => ({ type, text, props: {}, children: [], parent: null, showModal() {}, close() {}, addEventListener() {}, removeEventListener() {} });
const renderer = createRenderer({
  createElement: (type) => node(type), createText: (text) => node('text', text), createComment: () => node('comment'),
  setText: (target, text) => { target.text = text; },
  setElementText: (target, text) => { target.text = text; target.children = []; },
  patchProp: (target, key, before, after) => { target.props[key] = after; },
  parentNode: (target) => target.parent,
  nextSibling: (target) => target.parent?.children[target.parent.children.indexOf(target) + 1] || null,
  insert(target, parent, anchor = null) {
    if (target.parent) target.parent.children.splice(target.parent.children.indexOf(target), 1);
    target.parent = parent;
    const index = anchor ? parent.children.indexOf(anchor) : -1;
    if (index < 0) parent.children.push(target); else parent.children.splice(index, 0, target);
  },
  remove(target) { target.parent?.children.splice(target.parent.children.indexOf(target), 1); },
});
const textOf = (target) => [target.text, ...target.children.map(textOf)].join(' ');
const flush = async () => { await new Promise(setImmediate); await nextTick(); };

test('closure waits for the final response and displays the real last exchange before restatement', async () => {
  const saved = { api: globalThis.__closureApi, timeout: globalThis.setTimeout, clear: globalThis.clearTimeout };
  const timers = new Map();
  let timer = 0;
  let state = { session: { status: 'completed' }, pending_final_response: true,
    final_exchange: { learner_message: '最後的材料問題', assistant_message: null } };
  globalThis.setTimeout = (callback) => { timers.set(++timer, callback); return timer; };
  globalThis.clearTimeout = (id) => timers.delete(id);
  globalThis.__closureApi = { fetch: async () => structuredClone(state), submit: async () => assert.fail('Must not submit while waiting') };
  const root = node('root');
  const app = renderer.createApp(component, { sessionId: 'session-1' });
  app.component('Icon', { render: () => null });
  try {
    app.mount(root);
    await flush();
    assert.match(textOf(root), /最後的材料問題/);
    assert.match(textOf(root), /最後一輪回覆仍在處理/);
    assert.doesNotMatch(textOf(root), /繼續：本輪後測/);
    state = { session: { status: 'completed' }, pending_final_response: false,
      final_exchange: { learner_message: '最後的材料問題', assistant_name: '莫那魯道', assistant_message: '實際最後回覆', delivered_after_deadline: true },
      closure: { closure_id: 'closure-1', question: '當前題目', answer: 'C', explanation: '核對過的解說' } };
    const refresh = [...timers.values()][0];
    assert.ok(refresh);
    refresh();
    await flush();
    const rendered = textOf(root);
    for (const text of ['最後的材料問題', '莫那魯道的最後回覆', '實際最後回覆', '核對過的解說', '繼續：本輪後測']) assert.ok(rendered.includes(text), text);
    assert.ok(rendered.indexOf('實際最後回覆') < rendered.indexOf('核對過的解說'));
    assert.doesNotMatch(rendered, /最後一輪回覆仍在處理/);
  } finally {
    app.unmount();
    globalThis.__closureApi = saved.api;
    globalThis.setTimeout = saved.timeout;
    globalThis.clearTimeout = saved.clear;
  }
});
