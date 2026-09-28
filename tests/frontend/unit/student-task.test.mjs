import assert from 'node:assert/strict';

const taskLogic = await globalThis.loadTsModule('composables/useStudentTask.ts');

export const errorElicitationTask = {
  id: 'task-error-elicitation',
  title: 'Historical evidence',
  error_elicitation_task_full_text: 'First statement. {{blank:q01}}\nSecond statement. {{blank:q02}}\nThird statement. {{blank:q03}}',
  evaluation_payload: {
    contract_version: 'error_elicitation_v1',
    questions: [
      { id: 'q01', type: 'cloze', required: true, correct_answer: 'INTERNAL_KEY', reasoning_criteria: 'INTERNAL_CRITERIA' },
      { id: 'q02', type: 'multiple_choice', required: true, options: [
        { id: 'a', value: 'a', label: 'First option' },
        { id: 'b', value: 'b', label: 'Second option' },
      ], correct_answer: 'b', reasoning_criteria: 'INTERNAL_CRITERIA' },
      { id: 'q03', type: 'true_false', required: true, correct_answer: false, reasoning_criteria: 'INTERNAL_CRITERIA' },
    ],
    materials: [{ id: 'm01', title: 'A source', text: 'Source text', image_url: 'https://example.com/source.png', source_url: 'https://example.com/source', attribution: 'Source archive' }],
  },
};

const legacyTask = {
  ...errorElicitationTask,
  error_elicitation_task_full_text: 'Legacy {{blank:q01}}',
  evaluation_payload: { questions: [{ id: 'q01', type: 'cloze', prompt: 'Legacy question', required: true }] },
};

const completeAnswers = [
  { question_id: 'q01', value: 'Learner answer', rationale: 'Evidence in source one.' },
  { question_id: 'q02', value: 'b', rationale: 'The second option matches the source.' },
  { question_id: 'q03', value: false, rationale: 'The statement overstates the evidence.' },
];

test('new-format questions do not require or expose per-question prompts and internal grading fields', () => {
  const questions = taskLogic.normalizeTaskQuestions(errorElicitationTask);
  assert.equal(questions.length, 3);
  assert.deepEqual(questions.map((question) => question.id), ['q01', 'q02', 'q03']);
  assert.ok(questions.every((question) => question.required === true));
  assert.ok(questions.every((question) => !('prompt' in question) && !('correct_answer' in question) && !('reasoning_criteria' in question)));
  assert.equal(taskLogic.taskConfigurationError(errorElicitationTask), null);
});

test('explicit legacy questions remain usable without a fabricated short-answer fallback', () => {
  assert.equal(taskLogic.normalizeTaskQuestions(legacyTask)[0].prompt, 'Legacy question');
  assert.deepEqual(taskLogic.normalizeTaskQuestions({ ...legacyTask, evaluation_payload: {} }), []);
  assert.equal(taskLogic.isTaskAnswerComplete([], []), false);
  const task = { ...errorElicitationTask, evaluation_payload: { ...errorElicitationTask.evaluation_payload, questions: [{ id: 'q01', type: 'short_answer', prompt: 'Not allowed' }] } };
  assert.deepEqual(taskLogic.normalizeTaskQuestions(task), []);
  assert.ok(taskLogic.taskConfigurationError(task));
});

test('full text renders exactly one answer block per marker with no question wording duplication', () => {
  const task = structuredClone(errorElicitationTask);
  task.evaluation_payload.questions[0].prompt = 'MUST_NOT_APPEAR';
  task.evaluation_payload.questions[0].blank_id = 'legacy-alias';
  const segments = taskLogic.buildTaskStorySegments(task);
  assert.deepEqual(segments.filter((segment) => segment.type === 'blank').map((segment) => segment.question.id), ['q01', 'q02', 'q03']);
  assert.equal(segments.filter((segment) => segment.type === 'text').map((segment) => segment.text).join(''), 'First statement. \nSecond statement. \nThird statement. ');
  assert.doesNotMatch(JSON.stringify(segments), /MUST_NOT_APPEAR|INTERNAL_KEY|INTERNAL_CRITERIA/);
});

test('missing, unknown, duplicate markers and invalid questions block submission', () => {
  for (const fullText of [
    'Missing {{blank:q01}}{{blank:q02}}',
    'Unknown {{blank:q01}}{{blank:q02}}{{blank:q99}}',
    'Duplicate {{blank:q01}}{{blank:q02}}{{blank:q03}}{{blank:q01}}',
  ]) {
    const task = { ...errorElicitationTask, error_elicitation_task_full_text: fullText };
    assert.ok(taskLogic.taskConfigurationError(task));
    assert.equal(taskLogic.isTaskAnswerComplete(taskLogic.normalizeTaskQuestions(task), completeAnswers, task), false);
  }
});

test('reading introduction moves before materials without losing question wording or answer bindings', () => {
  const task = { ...errorElicitationTask, error_elicitation_task_full_text: 'Reading context.\n\nQ01｜First question.\n{{blank:q01}}\nQ02｜Second.\n{{blank:q02}}\nQ03｜Third.\n{{blank:q03}}' };
  const layout = taskLogic.buildTaskReadingLayout(task);
  assert.equal(layout.introduction, 'Reading context.');
  assert.equal(layout.segments[0].text, 'Q01｜First question.\n');
  assert.deepEqual(layout.segments.filter((s) => s.type === 'blank').map((s) => s.question.id), ['q01', 'q02', 'q03']);
  assert.deepEqual(taskLogic.buildTaskReadingLayout(errorElicitationTask), { introduction: '', segments: taskLogic.buildTaskStorySegments(errorElicitationTask) });
  assert.deepEqual(taskLogic.buildTaskReadingLayout(legacyTask), { introduction: '', segments: taskLogic.buildTaskStorySegments(legacyTask) });
});

test('question layout supports five and eight questions in authored marker order without exposing grading data', () => {
  const ids = ['q42', 'q07', 'q90', 'q14', 'q101', 'q03', 'q25', 'q68'];
  for (const count of [5, 8]) {
    const authoredIds = ids.slice(0, count);
    const texts = authoredIds.map((id, index) => `Question for ${id}.\nEvidence paragraph ${index + 1}. Mention Q88｜inside the text.`);
    const task = {
      ...errorElicitationTask,
      error_elicitation_task_full_text: `Shared reading context.\n\n${authoredIds.map((id, index) => `${id.toUpperCase()}｜${texts[index]}\n{{blank:${id}}}`).join('\n\n')}\nClosing instructions.`,
      evaluation_payload: {
        ...errorElicitationTask.evaluation_payload,
        questions: [...authoredIds].reverse().map((id) => ({
          id, type: 'multiple_choice', correct_answer: 'INTERNAL_KEY',
          reasoning_criteria: 'INTERNAL_CRITERIA', explanation: 'INTERNAL_EXPLANATION',
          prompt: 'INTERNAL_UNUSED_PROMPT',
          options: [{ id: 'a', label: 'A visible option', value: 'a', grading_note: 'INTERNAL_OPTION_NOTE' }],
        })),
      },
    };
    const original = structuredClone(task);
    const layout = taskLogic.buildTaskQuestionLayout(task);
    assert.equal(layout.introduction, 'Shared reading context.');
    assert.equal(layout.questions.length, count);
    assert.deepEqual(layout.questions.map(({ question }) => question.id), authoredIds);
    assert.deepEqual(layout.questions.map(({ index }) => index), authoredIds.map((_, index) => index));
    assert.deepEqual(layout.questions.map(({ text }) => text), texts);
    assert.equal(layout.trailingText, 'Closing instructions.');
    assert.doesNotMatch(JSON.stringify(layout), /INTERNAL_|correct_answer|reasoning_criteria|grading_note/);
    assert.equal(taskLogic.taskConfigurationError(task), null);
    assert.deepEqual(task, original);
  }
});

test('question layout keeps all preceding prose when there is no standard heading and preserves trailing prose', () => {
  const task = {
    ...errorElicitationTask,
    error_elicitation_task_full_text: 'Opening context belongs with the first question.\nFirst question. {{blank:q01}}\nSecond question.\nAn extra paragraph. {{blank:q02}}\nThird question. {{blank:q03}}\nClosing paragraph one.\nClosing paragraph two.',
  };
  const layout = taskLogic.buildTaskQuestionLayout(task);
  assert.equal(layout.introduction, '');
  assert.deepEqual(layout.questions.map(({ text }) => text), [
    'Opening context belongs with the first question.\nFirst question.',
    'Second question.\nAn extra paragraph.',
    'Third question.',
  ]);
  assert.equal(layout.trailingText, 'Closing paragraph one.\nClosing paragraph two.');
  assert.deepEqual(taskLogic.buildTaskQuestionLayout({ ...task, error_elicitation_task_full_text: 'Unbound reading prose.' }), {
    introduction: '', questions: [], trailingText: 'Unbound reading prose.',
  });
});

test('question layout preserves arbitrary legacy IDs and aliases while stripping only leading display labels', () => {
  const task = {
    ...legacyTask,
    error_elicitation_task_full_text: 'Opening prose.\nQ99｜Keep this non-leading label. {{blank:source-one}}\nQ21|Second prompt. {{blank:q_recheck}}\nQ88｜Keep the closing label.',
    evaluation_payload: { questions: [
      { id: 'q_recheck', type: 'true_false', prompt: 'Second legacy prompt', correct_answer: false },
      { id: 'custom-source', blank_id: 'source-one', type: 'cloze', prompt: 'First legacy prompt', reasoning_criteria: 'INTERNAL_CRITERIA' },
    ] },
  };
  const layout = taskLogic.buildTaskQuestionLayout(task);
  assert.equal(layout.introduction, '');
  assert.deepEqual(layout.questions.map(({ question }) => question.id), ['custom-source', 'q_recheck']);
  assert.equal(layout.questions[0].question.blank_id, 'source-one');
  assert.equal(layout.questions[0].question.prompt, 'First legacy prompt');
  assert.equal(layout.questions[0].text, 'Opening prose.\nQ99｜Keep this non-leading label.');
  assert.equal(layout.questions[1].text, 'Second prompt.');
  assert.equal(layout.trailingText, 'Q88｜Keep the closing label.');
  assert.doesNotMatch(JSON.stringify(layout), /correct_answer|reasoning_criteria|INTERNAL_/);
});

test('eight-question completion includes every answer and treats false as an answered value', () => {
  const questions = Array.from({ length: 8 }, (_, index) => ({ id: `q${String(index + 1).padStart(2, '0')}`, type: 'true_false' }));
  const task = {
    ...errorElicitationTask,
    error_elicitation_task_full_text: questions.map(({ id }) => `Question ${id}. {{blank:${id}}}`).join('\n'),
    evaluation_payload: { ...errorElicitationTask.evaluation_payload, questions },
  };
  const answers = questions.map(({ id }) => ({ question_id: id, value: false, rationale: 'The source does not support this claim.' }));
  const normalizedQuestions = taskLogic.normalizeTaskQuestions(task);
  assert.equal(taskLogic.isTaskAnswerComplete(normalizedQuestions, answers, task), true);
  assert.equal(taskLogic.isTaskAnswerComplete(normalizedQuestions, answers.slice(0, 7), task), false);
  assert.equal(taskLogic.isTaskAnswerComplete(normalizedQuestions, answers.map((answer, index) => index === 7 ? { ...answer, rationale: '' } : answer), task), false);
});

test('new-format submission requires every answer and nonblank rationale, while false is valid', () => {
  const questions = taskLogic.normalizeTaskQuestions(errorElicitationTask);
  assert.equal(taskLogic.isTaskAnswerComplete(questions, completeAnswers, errorElicitationTask), true);
  for (const patch of [
    { value: null }, { value: '' }, { value: '   ' }, { rationale: '' }, { rationale: ' \n\t' }, { rationale: undefined },
  ]) {
    const answers = completeAnswers.map((answer, index) => index === 0 ? { ...answer, ...patch } : answer);
    assert.equal(taskLogic.isTaskAnswerComplete(questions, answers, errorElicitationTask), false);
  }
  for (const [questionIndex, value] of [[1, 'unknown-option'], [1, ['b']], [2, 'false']]) {
    const answers = completeAnswers.map((answer, index) => index === questionIndex ? { ...answer, value } : answer);
    assert.equal(taskLogic.isTaskAnswerComplete(questions, answers, errorElicitationTask), false);
  }
});

test('new response payload is only contract version and question id/value/rationale', () => {
  const answers = completeAnswers.map((answer) => ({ ...answer, blank_id: answer.question_id, type: 'cloze', prompt: 'DUPLICATE_PROMPT', expected_answer: 'INTERNAL_KEY' }));
  const payload = taskLogic.buildTaskResponsePayload(answers, errorElicitationTask);
  assert.deepEqual(payload, { contract_version: 'error_elicitation_v1', answers: completeAnswers });
  assert.doesNotMatch(JSON.stringify(payload), /answer_text|prompt|blank_id|expected_answer/);
});

test('partial drafts and false answers preserve rationale through serialized payload resume', () => {
  const questions = taskLogic.normalizeTaskQuestions(errorElicitationTask);
  let answers = taskLogic.updateTaskAnswer([], questions[0], { rationale: 'Unfinished reasoning\nwith a second line' });
  answers = taskLogic.updateTaskAnswer(answers, questions[2], { value: false, rationale: 'Original reason' });
  answers = taskLogic.updateTaskAnswer(answers, questions[2], { value: true });
  assert.equal(answers.find((answer) => answer.question_id === 'q03').rationale, 'Original reason');
  answers = taskLogic.updateTaskAnswer(answers, questions[2], { value: false });
  const payload = taskLogic.buildTaskResponsePayload(answers, errorElicitationTask);
  const resumed = taskLogic.restoreTaskAnswers(errorElicitationTask, JSON.parse(JSON.stringify(payload)));
  assert.equal(resumed[0].value, null);
  assert.equal(resumed[0].rationale, 'Unfinished reasoning\nwith a second line');
  assert.equal(resumed[1].value, false);
  assert.equal(resumed[1].rationale, 'Original reason');
  assert.equal(taskLogic.isTaskAnswerComplete(questions, resumed, errorElicitationTask), false);
  assert.deepEqual(taskLogic.buildTaskResponsePayload(resumed, errorElicitationTask), payload);
});

test('resume derives question metadata from the task without requiring a payload type or prompt', () => {
  const answers = taskLogic.restoreTaskAnswers(errorElicitationTask, { answers: [...completeAnswers, { question_id: 'unknown', value: 'ignored' }, null] });
  assert.equal(answers.length, 3);
  assert.deepEqual(answers.map((answer) => answer.type), ['cloze', 'multiple_choice', 'true_false']);
  assert.ok(answers.every((answer) => answer.prompt === ''));
  assert.deepEqual(taskLogic.restoreTaskAnswers(errorElicitationTask, { answers: 'invalid' }), []);
});

test('legacy response serialization and optional rationale remain compatible', () => {
  const questions = taskLogic.normalizeTaskQuestions(legacyTask);
  const answers = taskLogic.updateTaskAnswer([], questions[0], { value: 'Legacy answer' });
  assert.equal(taskLogic.isTaskAnswerComplete(questions, answers, legacyTask), true);
  const payload = taskLogic.buildTaskResponsePayload(answers, legacyTask);
  assert.equal(payload.answer_text, 'Legacy question\nLegacy answer');
  assert.equal(payload.answers[0].value, 'Legacy answer');
});

test('review exposes learner answer/rationale and backend binary correctness only', () => {
  const attempt = {
    status: 'submitted',
    response_payload: { contract_version: 'error_elicitation_v1', answers: completeAnswers },
    judgement_payload: { question_results: [
      { question_id: 'q01', correctness: 'correct', expected_answer: 'INTERNAL_KEY', reasoning_feedback: 'INTERNAL_FEEDBACK' },
      { question_id: 'q02', correctness: 'incorrect', reasoning_criteria: 'INTERNAL_CRITERIA' },
      { question_id: 'q03', correctness: 'correct' },
    ] },
  };
  const reviews = taskLogic.buildTaskAnswerReviews(errorElicitationTask, attempt);
  assert.deepEqual(reviews.map((review) => review.status), ['correct', 'incorrect', 'correct']);
  assert.deepEqual(reviews.map((review) => review.rationale), completeAnswers.map((answer) => answer.rationale));
  assert.deepEqual(reviews.map((review) => review.label), ['q01', 'q02', 'q03']);
  assert.equal(reviews[1].answerText, 'Second option');
  assert.equal(reviews[2].answerText, '否');
  assert.doesNotMatch(JSON.stringify(reviews), /INTERNAL_|expected_answer|reasoning_feedback|reasoning_criteria|correct_answer/);
});

test('review never grades from an internal key or translates missing/partial judgement into wrong', () => {
  for (const correctness of [undefined, 'partial', 'unanswered', true, false]) {
    const reviews = taskLogic.buildTaskAnswerReviews(errorElicitationTask, {
      status: 'submitted',
      response_payload: { answers: completeAnswers },
      judgement_payload: { question_results: [{ question_id: 'q03', correctness }] },
    });
    assert.ok(reviews.every((review) => review.status === 'pending'));
  }
});

test('review uses allowlisted backend question text, learner answer and rationale snapshots', () => {
  const [review] = taskLogic.buildTaskAnswerReviews(errorElicitationTask, {
    status: 'submitted',
    response_payload: { answers: [{ question_id: 'q01', value: 'Older answer', rationale: 'Older rationale' }] },
    judgement_payload: { question_results: [{
      question_id: 'q01', question_text: 'Authored question snapshot', learner_answer: 'Submitted answer',
      learner_rationale: 'Submitted rationale', correctness: 'incorrect',
      expected_answer: 'PRIVATE_KEY', reasoning_feedback: 'PRIVATE_FEEDBACK', criteria: 'PRIVATE_CRITERIA',
    }] },
  });
  assert.equal(review.questionText, 'Authored question snapshot');
  assert.equal(review.answerText, 'Submitted answer');
  assert.equal(review.rationale, 'Submitted rationale');
  assert.equal(review.status, 'incorrect');
  assert.doesNotMatch(JSON.stringify(review), /PRIVATE_|Older/);
});

test('processing failures and pending attempts override any stale binary judgement', () => {
  for (const [status, expected] of [['failed', 'failed'], ['processing', 'pending'], ['in_progress', 'pending'], [undefined, 'pending']]) {
    const reviews = taskLogic.buildTaskAnswerReviews(errorElicitationTask, {
      status,
      response_payload: { answers: completeAnswers },
      judgement_payload: { question_results: completeAnswers.map((answer) => ({ question_id: answer.question_id, correctness: 'incorrect' })) },
    });
    assert.ok(reviews.every((review) => review.status === expected));
    assert.notEqual(taskLogic.taskReviewStatusLabel(expected), '答錯');
  }
});

test('material references allow HTTP(S) and local images only; answer display preserves false', () => {
  assert.equal(taskLogic.taskMaterialUrl('https://archive.example/source?q=1'), 'https://archive.example/source?q=1');
  assert.equal(taskLogic.taskMaterialUrl('/images/materials/wushe-headquarters-1930.jpg'), '/images/materials/wushe-headquarters-1930.jpg');
  for (const url of ['javascript:alert(1)', 'data:text/html,test', 'not a url', '', null, '/api/events', '/images/../secret.png', '/images/%2e%2e/secret.png', '//example.com/a.png']) {
    assert.equal(taskLogic.taskMaterialUrl(url), undefined);
  }
  assert.equal(taskLogic.taskAnswerValueToText(false), '否');
  assert.equal(taskLogic.taskAnswerValueToText(true), '是');
  assert.equal(taskLogic.taskAnswerValueToText(['A', 'B']), 'A, B');
});
