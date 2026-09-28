const { getTaskDiscussionCompletions } = await globalThis.loadTsModule('utils/taskDiscussionProgress.ts');

const task = { evaluation_payload: { questions: [{ id: 'q01' }, { id: 'q02' }, { id: 'q03' }] } };
const reply = (id, questionId, completionStatus, overrides = {}) => ({
  id, speaker_type: 'persona', content: 'Reply',
  metadata: { target_question_id: questionId, completion_status: completionStatus },
  ...overrides,
});

test('discussion review restores completion from saved records and links only to the explicitly paired learner message', () => {
  const confirmation = reply('confirmation', 'q01', 'resolved');
  const history = [
    { id: 'revision', speaker_type: 'learner', operation_status: 'completed', content: 'My revised reason', metadata: { response_message_id: 'confirmation' } },
    { id: 'unrelated', speaker_type: 'learner', operation_status: 'completed', content: 'An unrelated comment' },
    confirmation,
  ];
  const [completion] = getTaskDiscussionCompletions(task, history);
  assert.equal(completion.label, '已完成修正');
  assert.equal(completion.messageId, 'revision');
  assert.equal(completion.questionIndex, 0);
  assert.equal(getTaskDiscussionCompletions(task, history.slice(1))[0].messageId, 'confirmation');
  history[0].operation_status = 'failed';
  assert.equal(getTaskDiscussionCompletions(task, history)[0].messageId, 'confirmation');
});

test('pending, failed, held and learner-written completion claims do not become correction evidence', () => {
  const base = reply('saved', 'q01', 'resolved');
  const history = [
    { ...base, id: undefined },
    { ...base, id: 'local-placeholder' },
    { ...base, speaker_type: 'learner' },
    ...['pending', 'processing', 'failed'].map((operation_status) => ({ ...base, operation_status })),
    { ...base, metadata: { ...base.metadata, generation_status: 'pending' } },
    { ...base, metadata: { ...base.metadata, response_status: 'failed' } },
    { ...base, metadata: { ...base.metadata, answer_delivery: { state_held: true } } },
    reply('continued', 'q01', 'continue', { content: '你已完成修正' }),
    reply('other-task', 'unknown', 'resolved'),
  ];
  assert.deepEqual(getTaskDiscussionCompletions(task, history), []);
});

test('feedback correction and maximum-support closure keep distinct outcomes without changing original grading', () => {
  for (const status of ['resolved', 'feedback_completed', 'corrected_after_feedback']) {
    const [completion] = getTaskDiscussionCompletions(task, [reply('done', 'q01', status)]);
    assert.equal(completion.status, 'corrected');
    assert.equal(completion.label, '已完成修正');
  }
  for (const status of ['unresolved_after_max_support', 'complete']) {
    const [completion] = getTaskDiscussionCompletions(task, [reply('closed', 'q01', status)]);
    assert.equal(completion.status, 'closed');
    assert.equal(completion.label, '已結束討論');
    assert.equal(completion.linkLabel, '查看討論結尾');
  }
  assert.deepEqual(getTaskDiscussionCompletions(task, []), []);
});

test('completion review keeps each question latest saved outcome while ignoring incomplete retry updates', () => {
  const history = [
    reply('first-end', 'q01', 'unresolved_after_max_support'),
    reply('second-end', 'q02', 'resolved'),
    reply('revisited', 'q01', 'corrected_after_feedback'),
    reply('unfinished', 'q01', 'complete', { operation_status: 'processing' }),
  ];
  const completions = getTaskDiscussionCompletions(task, history);
  assert.deepEqual(completions.map((entry) => [entry.questionId, entry.messageId, entry.status]), [
    ['q01', 'revisited', 'corrected'], ['q02', 'second-end', 'corrected'],
  ]);
  assert.equal(history.length, 4);
});
