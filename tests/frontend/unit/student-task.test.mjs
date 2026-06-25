import assert from 'node:assert/strict';
import { sampleTask } from '../fixtures/histosphereFixtures.mjs';

const taskLogic = await globalThis.loadTsModule('composables/useStudentTask.ts');

test('student task logic normalizes inline questions and fallback question', () => {
  const questions = taskLogic.normalizeTaskQuestions(sampleTask);

  assert.equal(questions.length, 2);
  assert.equal(questions[0].id, 'q01');
  assert.equal(questions[0].blank_id, 'q01');
  assert.equal(questions[0].required, true);
  assert.equal(questions[1].options.length, 2);

  const fallback = taskLogic.normalizeTaskQuestions({
    ...sampleTask,
    evaluation_payload: {},
    display_text: '請說明事件意義。',
  });

  assert.deepEqual(fallback[0], {
    id: 'main-answer',
    blank_id: 'main-answer',
    type: 'short_answer',
    prompt: '請說明事件意義。',
    placeholder: '請用自己的話補上你認為重要的缺口、理由或不確定之處...',
    required: true,
  });
});

test('student task logic builds story segments from display text tokens', () => {
  const segments = taskLogic.buildTaskStorySegments(sampleTask);

  assert.deepEqual(segments.map((segment) => segment.type), [
    'text',
    'blank',
    'text',
    'blank',
    'text',
  ]);
  assert.equal(segments[1].question.id, 'q01');
  assert.equal(segments[3].question.id, 'q02');
});

test('student task logic validates required answers and serializes response payload', () => {
  const questions = taskLogic.normalizeTaskQuestions(sampleTask);
  const incompleteAnswers = [
    {
      question_id: 'q01',
      blank_id: 'q01',
      type: 'cloze',
      prompt: '請填入舊制度危機。',
      value: '',
    },
  ];
  const completeAnswers = [
    {
      question_id: 'q01',
      blank_id: 'q01',
      type: 'cloze',
      prompt: '請填入舊制度危機。',
      value: '財政危機',
    },
    {
      question_id: 'q02',
      blank_id: 'q02',
      type: 'multiple_choice',
      prompt: '第三等級主張哪種表決方式？',
      value: '人數',
    },
  ];

  assert.equal(taskLogic.isTaskAnswerComplete(questions, incompleteAnswers), false);
  assert.equal(taskLogic.isTaskAnswerComplete(questions, completeAnswers), true);

  const payload = taskLogic.buildTaskResponsePayload(completeAnswers);
  assert.equal(payload.answers.length, 2);
  assert.match(payload.answer_text, /財政危機/);
  assert.match(payload.answer_text, /人數/);
});

test('student task logic keeps answer text and participant id deterministic', () => {
  assert.equal(taskLogic.taskAnswerValueToText(true), '是');
  assert.equal(taskLogic.taskAnswerValueToText(false), '否');
  assert.equal(taskLogic.taskAnswerValueToText(['A', 'B']), 'A, B');

  const first = taskLogic.participantUuid('scott-test');
  const second = taskLogic.participantUuid('scott-test');

  assert.equal(first, second);
  assert.match(first, /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
});
