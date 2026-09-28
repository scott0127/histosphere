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

test('discussion review follows only the confirmed backend target and shows its full question, choices and original rationale', async () => {
  const attempt = {
    status: 'submitted',
    response_payload: { answers: [
      { question_id: 'q01', value: 'OLD_ANSWER', rationale: 'OLD_REASON' },
      { question_id: 'q02', value: 'a', rationale: 'CURRENT_REASON' },
    ] },
    judgement_payload: { question_results: [{ question_id: 'q02', correctness: 'incorrect', reasoning_feedback: 'PRIVATE_FEEDBACK' }] },
  };
  const html = await render('TaskAttemptReview', {
    task: errorElicitationTask, attempt,
    learningFocus: { status: 'active', origin: 'learner', question_id: 'q02', claim: null },
  });
  assert.match(html, /第 2 題/);
  assert.match(html, /Second statement\./);
  assert.match(html, /First option/);
  assert.match(html, /Second option/);
  assert.match(html, /CURRENT_REASON/);
  assert.match(html, /原始作答/);
  assert.doesNotMatch(html, /OLD_REASON|OLD_ANSWER|PRIVATE_FEEDBACK|INTERNAL_/);
  for (const learningFocus of [{ status: 'completed' }, { status: 'none' }]) {
    const inactive = await render('TaskAttemptReview', { task: errorElicitationTask, attempt, learningFocus });
    assert.doesNotMatch(inactive, /CURRENT_REASON|OLD_REASON|第 2 題/);
  }
  const thirdParty = await render('TaskAttemptReview', {
    task: errorElicitationTask, attempt,
    learningFocus: { status: 'active', origin: 'third_party', question_id: 'fallback', claim: 'THIRD_PARTY_CLAIM' },
  });
  assert.match(thirdParty, /另一個人的說法/);
  assert.match(thirdParty, /THIRD_PARTY_CLAIM/);
  assert.doesNotMatch(thirdParty, /答錯|OLD_REASON|CURRENT_REASON/);
  for (const learningFocus of [undefined, null]) {
    const legacy = await render('TaskAttemptReview', { task: errorElicitationTask, attempt, learningFocus });
    assert.doesNotMatch(legacy, /目前討論|目前題目|EBL|Error-Elicitation/);
    assert.match(legacy, /OLD_REASON/);
    assert.match(legacy, /CURRENT_REASON/);
  }
});

test('progress notice restores confirmed correction and next question without relying on persona wording', async () => {
  const props = {
    task: errorElicitationTask,
    learningFocus: { status: 'active', origin: 'learner', question_id: 'q02' },
    history: [{ id: 'saved-reply', speaker_type: 'persona', content: 'A natural character response.',
      metadata: { target_question_id: 'q01', completion_status: 'resolved', answer_delivery: { state_held: false } } }],
  };
  const html = await render('TaskProgressNotice', props);
  assert.match(html, /第 1 題已完成修正 → 目前討論第 2 題/);
  assert.match(html, /role="status"/);
  assert.doesNotMatch(html, /A natural character response/);

  const pending = await render('TaskProgressNotice', { ...props,
    learningFocus: { status: 'active', origin: 'learner', question_id: 'q01' },
  });
  assert.match(pending, /目前討論第 1 題/);
  assert.doesNotMatch(pending, /已完成修正|→/);
  for (const history of [[], [{ ...props.history[0], operation_status: 'processing' }],
    [{ ...props.history[0], metadata: { ...props.history[0].metadata, answer_delivery: { state_held: true } } }],
    [{ ...props.history[0], content: '你已完成修正', metadata: { completion_status: 'continue' } }]]) {
    const unconfirmed = await render('TaskProgressNotice', { ...props, history });
    assert.match(unconfirmed, /目前討論第 2 題/);
    assert.doesNotMatch(unconfirmed, /已完成修正|→/);
  }
  const final = await render('TaskProgressNotice', { ...props,
    learningFocus: { status: 'completed', question_id: null, origin: null },
    history: [{ ...props.history[0], metadata: { target_question_id: 'q03', completion_status: 'resolved' } }],
  });
  assert.match(final, /第 3 題已完成修正 → 本輪題目已討論完畢/);
  const assisted = await render('TaskProgressNotice', { ...props,
    history: [{ ...props.history[0], metadata: { target_question_id: 'q01', completion_status: 'feedback_completed' } }],
  });
  assert.match(assisted, /第 1 題已完成修正 → 目前討論第 2 題/);
  assert.doesNotMatch(assisted, /已完成回饋與重述/);
  for (const learningFocus of [undefined, null, { status: 'none' }]) {
    const unfocused = await render('TaskProgressNotice', { ...props, learningFocus });
    assert.doesNotMatch(unfocused, /目前討論|已完成|role="status"/);
  }
});

test('correction review keeps original answer and completion status without a shortcut button', async () => {
  const html = await render('TaskAnswerReviewItem', {
    review: { label: '第 1 題', answerText: 'ORIGINAL_ANSWER', rationale: 'ORIGINAL_REASON', status: 'incorrect' },
    discussion: { status: 'corrected', label: '已完成修正', messageId: 'saved-correction', linkLabel: '查看修正對話' },
  });
  assert.match(html, /原始作答/);
  assert.match(html, /答錯/);
  assert.match(html, /ORIGINAL_ANSWER/);
  assert.match(html, /ORIGINAL_REASON/);
  assert.match(html, /已完成修正/);
  assert.doesNotMatch(html, /<button|查看修正對話|查看討論結尾/);
});

test('all four condition histories share correction progress and wait for the backend focus to advance', async () => {
  const props = {
    task: errorElicitationTask,
    attempt: { status: 'submitted', response_payload: { answers: [{ question_id: 'q01', value: 'Original answer' }] },
      judgement_payload: { question_results: [{ question_id: 'q01', correctness: 'correct' }] } },
    learningFocus: { status: 'active', origin: 'learner', question_id: 'q01' },
    history: [{ id: 'saved-reply', speaker_type: 'persona', metadata: { target_question_id: 'q01', completion_status: 'resolved' } }],
  };
  for (const conditionKey of ['01', '02', '03', '04']) {
    const history = [{ ...props.history[0], speaker_type: ['03', '04'].includes(conditionKey) ? 'persona' : 'assistant',
      metadata: { ...props.history[0].metadata, condition_key: conditionKey } }];
    const active = await render('TaskAttemptReview', { ...props, history });
    assert.match(active, /目前討論/);
    assert.match(active, /第 1 題/);
    assert.match(active, /討論中/);
    assert.doesNotMatch(active, /已完成修正|查看修正對話/);

    const learningFocus = { status: 'active', origin: 'learner', question_id: 'q02' };
    const next = await render('TaskAttemptReview', { ...props, history, learningFocus });
    assert.match(next, /第 2 題/);
    assert.match(next, /Second statement\./);
    assert.doesNotMatch(next, /Original answer/);
    const notice = await render('TaskProgressNotice', { ...props, history, learningFocus });
    assert.match(notice, /第 1 題已完成修正 → 目前討論第 2 題/);
    assert.match(notice, /progress-notice-highlight/);
    assert.doesNotMatch(notice, /EBL|D0|D1|condition/);

    // Old records may have no focus, but confirmed completion is still valid in the full answer review.
    const legacy = await render('TaskAttemptReview', { ...props, history, learningFocus: null });
    assert.match(legacy, /Original answer/);
    assert.match(legacy, /已完成修正/);
    assert.doesNotMatch(legacy, /查看修正對話|查看討論結尾/);
    assert.doesNotMatch(legacy, /討論中/);
  }
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

test('split task workspace renders every authored question and counts filled answers without grading', async () => {
  const task = structuredClone(errorElicitationTask);
  task.evaluation_payload.questions = Array.from({ length: 8 }, (_, index) => ({
    id: `q${String(index * 2 + 1).padStart(2, '0')}`, type: 'true_false', required: true,
    correct_answer: true, reasoning_criteria: 'INTERNAL_CRITERIA',
  }));
  task.error_elicitation_task_full_text = 'Shared reading introduction.\n\n'
    + task.evaluation_payload.questions.map((question, index) => `Q${String(index + 1).padStart(2, '0')}｜Prompt ${index + 1}.\n{{blank:${question.id}}}`).join('\n\n')
    + '\nKeep this trailing instruction.';
  const answers = [
    { question_id: 'q01', value: false, rationale: 'A filled but ungraded reason.' },
    { question_id: 'q03', value: false, rationale: '' },
  ];
  const html = await render('TaskStudentWorkspace', { task, modelValue: answers, canSubmit: false, disabled: false,
    isSubmitting: false, error: null, judgement: null });
  assert.match(html, /已填寫 1／8 題/);
  assert.match(html, /第 2 題尚未填寫理由/);
  assert.match(html, /aria-label="第 8 題，待填寫"/);
  assert.match(html, /Keep this trailing instruction\./);
  assert.equal(html.split('Shared reading introduction.').length - 1, 1);
  assert.match(html, /id="task-reading-pane"/);
  assert.match(html, /id="task-questions-pane"/);
  for (const question of task.evaluation_payload.questions) {
    assert.equal(html.split(`aria-label="${question.id} 作答理由"`).length - 1, 1);
  }
  assert.doesNotMatch(html, /INTERNAL_CRITERIA|答對|答錯|已完成修正/);
  assert.match(html, /type="submit" disabled/);
  const closed = await render('TaskStudentWorkspace', { task, modelValue: answers, canSubmit: true, disabled: true,
    isSubmitting: false, error: null, judgement: null });
  assert.match(closed, /<fieldset disabled/);
  assert.match(closed, /type="submit" disabled/);
});
