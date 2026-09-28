import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRenderer, ref } from 'vue';
import ts from 'typescript';

const compiled = ts.transpileModule(await readFile('composables/useBodyScrollLock.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText.replace(/from (['"])vue\1/g, `from '${import.meta.resolve('vue')}'`);
const { useBodyScrollLock } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);

const renderer = createRenderer({
  createElement: () => ({}), createText: () => ({}), createComment: () => ({}),
  setText() {}, setElementText() {}, patchProp() {}, insert() {}, remove() {},
  parentNode: () => null, nextSibling: () => null,
});

const createPage = (overflow = '', priority = '') => {
  const originalDocument = globalThis.document;
  const values = new Map(overflow ? [['overflow', { value: overflow, priority }]] : []);
  const style = {
    getPropertyValue: (name) => values.get(name)?.value || '',
    getPropertyPriority: (name) => values.get(name)?.priority || '',
    setProperty: (name, value, priority = '') => values.set(name, { value, priority }),
    removeProperty: (name) => values.delete(name),
  };
  globalThis.document = { body: { style } };
  const apps = [];
  return {
    style,
    mount(open = false) {
      const active = ref(open);
      const app = renderer.createApp({
        setup() { useBodyScrollLock(() => active.value); return () => null; },
      });
      let mounted = true;
      const close = () => { if (mounted) { mounted = false; app.unmount(); } };
      apps.push(close);
      app.mount({});
      return { active, unmount: close };
    },
    dispose() {
      apps.reverse().forEach((unmount) => unmount());
      if (originalDocument === undefined) delete globalThis.document;
      else globalThis.document = originalDocument;
    },
  };
};

test('admin overlay mounted open locks scrolling and closing restores the original overflow declaration', () => {
  const page = createPage('auto', 'important');
  try {
    const overlay = page.mount(true);
    assert.equal(page.style.getPropertyValue('overflow'), 'hidden');
    overlay.active.value = false;
    assert.equal(page.style.getPropertyValue('overflow'), 'auto');
    assert.equal(page.style.getPropertyPriority('overflow'), 'important');
    overlay.unmount();
    assert.equal(page.style.getPropertyValue('overflow'), 'auto');
  } finally { page.dispose(); }
});

test('admin overlay supports reopen and route unmount without leaving the page locked', () => {
  const page = createPage();
  try {
    const overlay = page.mount();
    assert.equal(page.style.getPropertyValue('overflow'), '');
    overlay.active.value = true;
    overlay.active.value = false;
    overlay.active.value = true;
    assert.equal(page.style.getPropertyValue('overflow'), 'hidden');
    overlay.unmount();
    assert.equal(page.style.getPropertyValue('overflow'), '');
    overlay.active.value = true;
    assert.equal(page.style.getPropertyValue('overflow'), '');
  } finally { page.dispose(); }
});

test('overlapping admin dialogs remain locked when closed or unmounted out of order', () => {
  const page = createPage('scroll');
  try {
    const editor = page.mount(true);
    const research = page.mount(true);
    editor.active.value = false;
    assert.equal(page.style.getPropertyValue('overflow'), 'hidden');
    editor.active.value = true;
    research.unmount();
    assert.equal(page.style.getPropertyValue('overflow'), 'hidden');
    editor.unmount();
    assert.equal(page.style.getPropertyValue('overflow'), 'scroll');
  } finally { page.dispose(); }
});

test('closing one overlay and unmounting it does not release another overlay twice', () => {
  const page = createPage();
  try {
    const first = page.mount(true);
    const second = page.mount(true);
    first.active.value = false;
    first.unmount();
    assert.equal(page.style.getPropertyValue('overflow'), 'hidden');
    second.active.value = false;
    assert.equal(page.style.getPropertyValue('overflow'), '');
  } finally { page.dispose(); }
});
