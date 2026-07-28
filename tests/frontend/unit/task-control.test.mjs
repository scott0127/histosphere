import assert from 'node:assert/strict';

const taskControl = await globalThis.loadTsModule('composables/useTaskControl.ts');

const task = {
  id: 'task-1',
  event_id: 'event-1',
  title: '法國大革命',
  story_text: '法國舊制度面臨財政危機。',
  display_text: '法國舊制度面臨財政危機。',
  evaluation_payload: { questions: [] },
  revision_state: 'manual',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

test('task editor inserts a selected phrase as one inline question', () => {
  const selectedText = '財政危機';
  const start = task.display_text.indexOf(selectedText);
  const question = taskControl.createTaskQuestion('cloze', selectedText, 1);
  const inserted = taskControl.insertQuestionToken(
    task.display_text,
    question.id,
    start,
    start + selectedText.length,
  );
  const evaluationJson = taskControl.updateTaskControlQuestion(task, '{"questions":[]}', question);

  assert.equal(inserted.displayText, '法國舊制度面臨{{blank:q01}}。');
  assert.equal(JSON.parse(evaluationJson).questions[0].correct_answer, selectedText);
});

test('task editor removes the matching question and story token together', () => {
  const evaluationJson = JSON.stringify({
    rubric: '保留其他設定',
    questions: [
      { id: 'q01', blank_id: 'q01', type: 'cloze', prompt: 'Q1' },
      { id: 'q02', blank_id: 'q02', type: 'cloze', prompt: 'Q2' },
    ],
  });
  const result = taskControl.removeQuestionAndToken(
    evaluationJson,
    '甲{{blank:q01}}乙{{blank:q02}}丙',
    'q01',
  );

  assert.equal(result.displayText, '甲乙{{blank:q02}}丙');
  assert.equal(JSON.parse(result.evaluationJson).rubric, '保留其他設定');
  assert.deepEqual(JSON.parse(result.evaluationJson).questions.map((item) => item.id), ['q02']);
});

test('task editor preserves the researcher explanation in structured JSON', () => {
  const question = {
    ...taskControl.createTaskQuestion('true_false', '革命後衝突完全消失', 1),
    explanation: '檢查受測者是否把革命理解成單線進步。',
  };
  const evaluationJson = taskControl.updateTaskControlQuestion(task, '{"questions":[]}', question);
  const roundTrip = taskControl.taskControlQuestions(task, evaluationJson)[0];

  assert.equal(roundTrip.explanation, question.explanation);
  assert.equal(roundTrip.correct_answer, true);
});

test('task editor history drops redo entries after a new edit', () => {
  const entry = (title) => ({
    title,
    displayText: title,
    storyText: title,
    evaluationJson: '{}',
  });
  let result = taskControl.appendTaskHistoryEntry([], -1, entry('A'));
  result = taskControl.appendTaskHistoryEntry(result.entries, result.index, entry('B'));
  result = taskControl.appendTaskHistoryEntry(result.entries, result.index, entry('C'));

  result = taskControl.appendTaskHistoryEntry(result.entries, 0, entry('D'));

  assert.deepEqual(result.entries.map((item) => item.title), ['A', 'D']);
  assert.equal(result.index, 1);
});

test('task editor history keeps only the configured maximum entries', () => {
  const entry = (title) => ({
    title,
    displayText: title,
    storyText: title,
    evaluationJson: '{}',
  });
  let result = { entries: [], index: -1 };
  for (const title of ['A', 'B', 'C']) {
    result = taskControl.appendTaskHistoryEntry(result.entries, result.index, entry(title), 2);
  }

  assert.deepEqual(result.entries.map((item) => item.title), ['B', 'C']);
  assert.equal(result.index, 1);
});
