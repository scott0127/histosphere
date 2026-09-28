import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createSSRApp, h } from 'vue';
import { renderToString } from 'vue/server-renderer';
import { compileScript, parse } from 'vue/compiler-sfc';
import ts from 'typescript';

const filename = 'components/event-library/EventLibraryHeader.vue';
const { descriptor, errors } = parse(await readFile(filename, 'utf8'), { filename });
assert.deepEqual(errors, []);
const script = compileScript(descriptor, { id: filename, inlineTemplate: true }).content;
const compiled = ts.transpileModule(script, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText.replace(/from (['"])vue\1/g, `from '${import.meta.resolve('vue')}'`);
const component = (await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)).default;

const renderHeader = async (isAdminMode, adminViewMode) => {
  const app = createSSRApp({ render: () => h(component, {
    isRefreshing: false, isAdminMode, adminViewMode,
    displayName: 'Test user', adminModePending: false, adminModeError: null,
  }) });
  app.component('NuxtLink', { setup: (_, { slots }) => () => h('a', { href: '/' }, slots.default?.()) });
  app.component('Icon', { render: () => h('span') });
  app.component('AdminModeSwitch', { render: () => h('button', { 'data-admin-mode-switch': 'true' }, '管理模式切換') });
  return renderToString(app);
};

test('event header renders admin controls only in admin mode and preserves refresh for learners', async () => {
  for (const view of ['admin_mode', 'admin_testmode']) {
    const learner = await renderHeader(false, view);
    assert.doesNotMatch(learner, /data-admin-mode-switch|管理模式切換|切換受測者/);
    assert.match(learner, /<button[^>]+title="重新整理事件"/);

    const admin = await renderHeader(true, view);
    assert.match(admin, /data-admin-mode-switch="true"/);
    assert.match(admin, /<button[^>]+title="重新整理事件"/);
    assert.doesNotMatch(admin, /切換受測者|switch-participant/);
  }
});
