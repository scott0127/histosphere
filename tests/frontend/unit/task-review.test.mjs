import assert from 'node:assert/strict';
import { errorElicitationTask } from './student-task.test.mjs';

const review = await globalThis.loadTsModule('utils/taskReview.ts');
export const reviewSnapshot = () => ({
  participant_code: 'P001', session: { id: 's1', status: 'initialized' },
  event: { id: 'event-1', canonical_name: '事件' }, task: structuredClone(errorElicitationTask),
  stage: 'awaiting_review', messages: [], updated_at: '2026-09-28T02:00:00Z',
  attempt: {
    id: 'a1', status: 'awaiting_review', review_version: 0, review_payload: {}, judgement_payload: {},
    response_payload: { answers: [
      { question_id: 'q01', value: 'Original learner answer', rationale: 'Original reason' },
      { question_id: 'q03', value: false, rationale: 'Original false reason' },
    ] },
    ai_judgement_payload: {
      error_elicitation_task_full_text: 'Original {{blank:q01}}\nOriginal boolean {{blank:q03}}',
      materials: [{ id: 'original-material', text: 'Original source', title: '原始材料', image_url: 'https://example.com/original.png' }],
      question_results: [
        { question_id: 'q01', question_type: 'cloze', question_text: 'Original question', expected_answer: 'Original standard', reasoning_criteria: 'Original criteria', answer_correct: false, reasoning_correct: true, answer_feedback: 'Answer explanation', reasoning_feedback: 'Reason explanation' },
        { question_id: 'q03', question_type: 'true_false', question_text: 'Original boolean', expected_answer: false, reasoning_criteria: 'Original boolean criteria', answer_correct: true, reasoning_correct: true, reasoning_feedback: 'Supported' },
      ],
    },
  },
});

test('review uses the frozen questions, criteria and image while preserving original false answers', () => {
  const snapshot = reviewSnapshot();
  snapshot.task.error_elicitation_task_full_text = 'LATER CHANGED QUESTION';
  snapshot.task.evaluation_payload.materials[0].text = 'LATER CHANGED MATERIAL';
  const task = review.reviewTask(snapshot);
  const rows = review.reviewQuestionRows(snapshot);
  assert.equal(task.evaluation_payload.materials[0].text, 'Original source');
  assert.equal(task.evaluation_payload.materials[0].image_url, 'https://example.com/original.png');
  assert.equal(rows[0].question.reasoning_criteria, 'Original criteria');
  assert.equal(rows[0].answer, 'Original learner answer');
  assert.equal(rows[1].answer, false);
  assert.equal(review.formatReviewAnswer(rows[1].answer), '否');
});

test('review headings use the frozen task layout without repeating the reading introduction', () => {
  const snapshot = reviewSnapshot();
  snapshot.attempt.ai_judgement_payload.error_elicitation_task_full_text = 'READING INTRODUCTION\nQ01｜Actual first question? {{blank:q01}}\nQ03｜Actual second question? {{blank:q03}}';
  snapshot.attempt.ai_judgement_payload.question_results[0].question_text = 'READING INTRODUCTION\nQ01｜Actual first question?';
  const rows = review.reviewQuestionRows(snapshot);
  assert.equal(rows[0].text, 'Actual first question?');
  assert.equal(rows[1].text, 'Actual second question?');
  assert.equal(review.reviewTask(snapshot).evaluation_payload.materials[0].text, 'Original source');
  snapshot.attempt.ai_judgement_payload.error_elicitation_task_full_text = 'Legacy text without markers';
  assert.equal(review.reviewQuestionRows(snapshot)[0].text, 'READING INTRODUCTION\nQ01｜Actual first question?');
});

test('AI correct answers are still unreviewed until explicitly saved as reviewed', () => {
  const snapshot = reviewSnapshot();
  const drafts = review.initialReviewDrafts(snapshot);
  assert.deepEqual(drafts.map(draft => draft.reviewed), [false, false]);
  assert.equal(drafts[1].answer_correct, true);
  snapshot.attempt.review_payload.question_results = [{ ...drafts[1], reviewed: true }];
  assert.deepEqual(review.initialReviewDrafts(snapshot).map(draft => draft.reviewed), [false, true]);
});

test('changed labels need an override reason and every reviewed rationale needs usable feedback', () => {
  const snapshot = reviewSnapshot();
  const row = review.reviewQuestionRows(snapshot)[0];
  const draft = review.initialReviewDrafts(snapshot)[0];
  assert.equal(review.reviewQuestionError(row, draft), null);
  draft.answer_correct = true;
  assert.match(review.reviewQuestionError(row, draft), /改判原因/);
  draft.override_reason = 'The supplied synonym meets the original standard.';
  assert.match(review.reviewQuestionError(row, draft), /更新答案判定說明/);
  draft.answer_feedback = 'The synonym expresses the expected answer.';
  assert.equal(review.reviewQuestionError(row, draft), null);
  draft.answer_feedback = '  ';
  assert.match(review.reviewQuestionError(row, draft), /答案判定說明/);
  draft.reasoning_feedback = '';
  assert.match(review.reviewQuestionError(row, draft), /理由判定說明/);
});

test('an objective answer override also requires a revised explanation even when AI feedback was null', () => {
  const snapshot = reviewSnapshot();
  const row = review.reviewQuestionRows(snapshot)[1];
  const draft = review.initialReviewDrafts(snapshot)[1];
  draft.answer_correct = false;
  draft.override_reason = 'The original rule does not match the supplied answer.';
  assert.match(review.reviewQuestionError(row, draft), /更新答案判定說明/);
  draft.answer_feedback = 'The stated conclusion conflicts with the source.';
  assert.equal(review.reviewQuestionError(row, draft), null);
  draft.reasoning_correct = false;
  assert.match(review.reviewQuestionError(row, draft), /更新理由判定說明/);
});

test('monitor treats ready as waiting for the learner rather than a running interaction', () => {
  const snapshot = reviewSnapshot();
  snapshot.attempt.status = 'ready';
  snapshot.conversation = { id: 'prepared-conversation' };
  assert.equal(review.monitorPhase(snapshot).id, 'ready');
  assert.equal(review.monitorPhase(snapshot).step, 2);
  snapshot.attempt.status = 'submitted';
  snapshot.session.status = 'conversation_started';
  assert.equal(review.monitorPhase(snapshot).id, 'chat');
  snapshot.stage = 'posttest_completed';
  assert.equal(review.monitorPhase(snapshot).id, 'complete');
  assert.equal(review.monitorPhase(snapshot).step, 3);
});
