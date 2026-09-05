import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { createSSRApp, h } from 'vue';
import { renderToString } from 'vue/server-renderer';
import { compileScript, parse } from 'vue/compiler-sfc';
import ts from 'typescript';
import { errorElicitationTask } from './student-task.test.mjs';

const moduleCache = new Map();
const compileModule = async (filename) => {
  if (moduleCache.has(filename)) return moduleCache.get(filename);
  const source = await readFile(filename, 'utf8');
  let script = source;
  if (filename.endsWith('.vue')) {
    const { descriptor, errors } = parse(source, { filename });
    assert.deepEqual(errors, []);
    script = compileScript(descriptor, { id: filename, inlineTemplate: true, templateOptions: { transformAssetUrls: false } }).content;
  }
  let output = ts.transpileModule(script, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
  }).outputText;
  const imports = [...output.matchAll(/from\s+(['"])([^'"]+)\1/g)];
  for (const match of imports) {
    const specifier = match[2];
    let url;
    if (specifier.startsWith('~/') || specifier.startsWith('.')) {
      let dependency = specifier.startsWith('~/')
        ? path.resolve(specifier.slice(2)) : path.resolve(path.dirname(filename), specifier);
      if (!path.extname(dependency)) dependency += '.ts';
      url = await compileModule(dependency);
    } else {
      url = import.meta.resolve(specifier);
    }
    output = output.replace(match[0], `from '${url}'`);
  }
  const url = `data:text/javascript;base64,${Buffer.from(output).toString('base64')}`;
  moduleCache.set(filename, url);
  return url;
};

const loadComponent = async (name) => (await import(await compileModule(path.resolve(`components/task-student/${name}.vue`)))).default;
const render = async (name, props) => {
  const component = await loadComponent(name);
  const app = createSSRApp({ render: () => h(component, props) });
  app.component('Icon', { render: () => h('span') });
  app.component('TaskStudentInlineBlank', { render: () => h('span') });
  app.component('TaskStudentShell', { setup: (_, { slots }) => () => h('div', slots.default?.()) });
  for (const name of ['TaskStudentStory', 'TaskStudentRenderer', 'TaskStudentSubmitBar']) {
    app.component(name, { render: () => h('div') });
  }
  return renderToString(app);
};

test('learner story renders reading text, image and caption before answer/rationale controls without research references', async () => {
  const task = structuredClone(errorElicitationTask);
  task.evaluation_payload.questions[0].prompt = 'DUPLICATE_QUESTION';
  task.evaluation_payload.materials[0].caption = 'Artist, 1850; depicting events in 1600.';
  const html = await render('TaskStudentStory', { task, modelValue: [] });
  for (const id of ['q01', 'q02', 'q03']) {
    assert.equal(html.split(`aria-label="${id} 作答理由"`).length - 1, 1);
    assert.match(html, new RegExp(`aria-label="${id} 答案"`));
  }
  assert.equal(html.split('First statement.').length - 1, 1);
  assert.match(html, /Source text/);
  assert.match(html, /Artist, 1850; depicting events in 1600\./);
  assert.match(html, /src="https:\/\/example.com\/source.png"/);
  assert.doesNotMatch(html, /Source archive|href="https:\/\/example.com\/source"|參考史料|原始來源|>m01</);
  assert.match(html, /href="https:\/\/example.com\/source.png" target="_blank" rel="noopener"/);
  assert.ok(html.indexOf('Source text') < html.indexOf('First statement.'));
  assert.doesNotMatch(html, /DUPLICATE_QUESTION|INTERNAL_KEY|INTERNAL_CRITERIA|blank:q/);
});

test('answer controls display resumed false selection and multiline rationale', async () => {
  const html = await render('TaskStudentAnswerBlock', {
    question: errorElicitationTask.evaluation_payload.questions[2],
    modelValue: false,
    rationale: 'Preserved reason\nsecond line',
  });
  assert.match(html, /value="false" checked/);
  assert.doesNotMatch(html, /value="true" checked/);
  assert.match(html, /Preserved reason\nsecond line/);
});

test('review renders rationale and backend status without exposing grading content', async () => {
  const html = await render('TaskAttemptReview', {
    task: errorElicitationTask,
    attempt: {
      status: 'submitted',
      response_payload: { answers: [{ question_id: 'q03', value: false, rationale: 'LEARNER_REASON' }] },
      judgement_payload: { question_results: [{ question_id: 'q03', correctness: 'correct', expected_answer: 'EXPECTED_ANSWER', reasoning_feedback: 'GRADING_FEEDBACK', reasoning_criteria: 'SECRET_CRITERIA' }] },
    },
  });
  assert.match(html, /LEARNER_REASON/);
  assert.match(html, /答對/);
  assert.doesNotMatch(html, /EXPECTED_ANSWER|GRADING_FEEDBACK|SECRET_CRITERIA|INTERNAL_|Source archive|href=|參考史料/);
  const failed = await render('TaskAnswerReviewItem', {
    review: { label: 'q03', answerText: '否', rationale: 'LEARNER_REASON', status: 'failed' },
  });
  assert.match(failed, /處理失敗/);
  assert.doesNotMatch(failed, /答錯/);
});

test('submit success never renders internal judgement feedback', async () => {
  const html = await render('TaskStudentSubmitBar', {
    canSubmit: true,
    isSubmitting: false,
    error: null,
    judgement: { feedback: 'SECRET_FEEDBACK', misconception_summary: 'SECRET_SUMMARY', reasoning_feedback: 'SECRET_REASONING' },
  });
  assert.match(html, /已送出/);
  assert.doesNotMatch(html, /SECRET_/);
});

test('task gate hides event introduction for learner and admin test views, while admin management can see it', async () => {
  const { activityModeForAdminView } = await globalThis.loadTsModule('utils/adminMode.ts');
  const props = {
    taskData: { task: errorElicitationTask, event: { canonical_name: 'Event', description: 'INTRODUCTION_NOT_FOR_LEARNERS' }, condition: {}, personas: [] },
    modelValue: [], canSubmit: false, isLoading: false, isSubmitting: false, error: null, judgement: null,
  };
  for (const activityMode of [undefined, 'learner', activityModeForAdminView('admin_testmode')]) {
    const html = await render('TaskStudentGate', { ...props, activityMode });
    assert.doesNotMatch(html, /INTRODUCTION_NOT_FOR_LEARNERS/);
  }
  const adminHtml = await render('TaskStudentGate', { ...props, activityMode: activityModeForAdminView('admin_mode') });
  assert.match(adminHtml, /INTRODUCTION_NOT_FOR_LEARNERS/);
});
