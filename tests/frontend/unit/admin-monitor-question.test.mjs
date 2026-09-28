import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createSSRApp, h } from 'vue';
import { renderToString } from 'vue/server-renderer';
import { compileScript, parse } from 'vue/compiler-sfc';
import ts from 'typescript';
import { reviewSnapshot } from './task-review.test.mjs';

const logic = await globalThis.loadTsModule('utils/taskReview.ts');
const filename = 'components/admin/monitor/ReviewQuestionPanel.vue';
const { descriptor, errors } = parse(await readFile(filename, 'utf8'), { filename });
assert.deepEqual(errors, []);
const script = compileScript(descriptor, { id: filename, inlineTemplate: true }).content;
let output = ts.transpileModule(script, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
output = output.replace(/from (['"])vue\1/g, `from '${import.meta.resolve('vue')}'`);
const importMatch = [...output.matchAll(/import \{([^}]+)\} from ['"]([^'"]+)['"];?/g)].find(item => item[2] === '~/utils/taskReview');
output = output.replace(importMatch[0], `const { ${importMatch[1]} } = globalThis.__monitorQuestionLogic;`);
globalThis.__monitorQuestionLogic = logic;
export const reviewQuestionComponent = (await import(`data:text/javascript;base64,${Buffer.from(output).toString('base64')}`)).default;
delete globalThis.__monitorQuestionLogic;
const render = async (row, draft) => {
  const app = createSSRApp({ render: () => h(reviewQuestionComponent, { row, draft, index: 0 }) });
  app.component('Icon', { render: () => h('span') });
  return renderToString(app);
};

test('review shows original answers and separate decisions without an on-screen grading-reference section', async () => {
  const snapshot = reviewSnapshot();
  const row = logic.reviewQuestionRows(snapshot)[0];
  row.question.source_text = 'PRIVATE_CRITERION_SOURCE';
  const html = await render(row, logic.initialReviewDrafts(snapshot)[0]);
  assert.match(html, /Original learner answer/);
  assert.match(html, /Original reason/);
  assert.doesNotMatch(html, /評判依據|參考答案|理由判準|Original criteria|Original standard|PRIVATE_CRITERION_SOURCE/);
  assert.match(html, /由 AI 初判預填，可由研究者修訂/);
  assert.match(html, /系統初判/);
  assert.match(html, /aria-labelledby="q01-answer_correct-label"/);
  assert.match(html, /aria-labelledby="q01-reasoning_correct-label"/);
  assert.match(html, /確認此題/);
  assert.doesNotMatch(html, /此題已核對/);
});

test('objective-answer override exposes an explanation field and change reason before confirmation', async () => {
  const snapshot = reviewSnapshot();
  const row = logic.reviewQuestionRows(snapshot)[1];
  const draft = logic.initialReviewDrafts(snapshot)[1];
  const before = await render(row, draft);
  assert.doesNotMatch(before, /aria-label="q03 答案判定說明"/);
  draft.answer_correct = false;
  const after = await render(row, draft);
  assert.match(after, /aria-label="q03 答案判定說明"/);
  assert.match(after, /aria-label="q03 改判原因"/);
  assert.match(after, /<dd>否<\/dd>/);
});

test('review options use the same letter prefixes as the learner answer controls', async () => {
  const snapshot = reviewSnapshot();
  const row = logic.reviewQuestionRows(snapshot)[0];
  row.question.type = 'multiple_choice';
  row.question.options = [{ id: 'one', value: '1', label: 'First option' }, { id: 'two', value: '2', label: 'Second option' }];
  const html = await render(row, logic.initialReviewDrafts(snapshot)[0]);
  assert.match(html, /monitor-option-letter">A\.<\/span><span>First option/);
  assert.match(html, /monitor-option-letter">B\.<\/span><span>Second option/);
});
