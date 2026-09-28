import { buildTaskQuestionLayout } from '~/composables/useStudentTask';
import type { EventTask, TaskQuestion } from '~/types';
import type { AdminMonitorSnapshot, ReviewQuestionRow, TaskReviewQuestion } from '~/types/taskReview';

const records = (value: unknown): Record<string, any>[] => Array.isArray(value)
  ? value.filter(item => item && typeof item === 'object') : [];

/** Review the exact question/material snapshot used by the initial judge. */
export const reviewTask = (snapshot: AdminMonitorSnapshot): EventTask | null => {
  const task = snapshot.task;
  if (!task) return null;
  const ai = snapshot.attempt?.ai_judgement_payload;
  const questions = records(ai?.question_results);
  if (!questions.length) return task;
  return {
    ...task,
    error_elicitation_task_full_text: typeof ai?.error_elicitation_task_full_text === 'string'
      ? ai.error_elicitation_task_full_text : task.error_elicitation_task_full_text,
    evaluation_payload: {
      ...task.evaluation_payload,
      materials: Array.isArray(ai?.materials) ? ai.materials : task.evaluation_payload.materials,
      questions: questions.map(result => ({
        id: result.question_id, type: result.question_type, prompt: result.question_text,
        options: result.options || [], correct_answer: result.expected_answer,
        reasoning_criteria: result.reasoning_criteria, source_text: result.source_text,
      })),
    },
  };
};

export const reviewQuestionRows = (snapshot: AdminMonitorSnapshot): ReviewQuestionRow[] => {
  const task = reviewTask(snapshot);
  if (!task) return [];
  const textById = new Map(buildTaskQuestionLayout(task).questions.map(item => [item.question.id, item.text]));
  const answers = records(snapshot.attempt?.response_payload?.answers);
  const aiResults = records(snapshot.attempt?.ai_judgement_payload?.question_results);
  return (task.evaluation_payload.questions || []).map(question => {
    const answer = answers.find(item => item.question_id === question.id);
    const ai = aiResults.find(item => item.question_id === question.id) || {};
    return {
      question, text: textById.get(question.id)?.trim() || ai.question_text || question.prompt || question.id,
      answer: answer?.value ?? ai.learner_answer ?? null,
      rationale: answer?.rationale ?? ai.learner_rationale ?? '', ai,
    };
  });
};

export const initialReviewDrafts = (snapshot: AdminMonitorSnapshot): TaskReviewQuestion[] => {
  const saved = snapshot.attempt?.review_payload?.question_results || [];
  return reviewQuestionRows(snapshot).map(row => {
    const existing = saved.find(item => item.question_id === row.question.id);
    return {
      question_id: row.question.id, reviewed: existing?.reviewed === true,
      answer_correct: existing?.answer_correct ?? row.ai.answer_correct ?? false,
      reasoning_correct: existing?.reasoning_correct ?? row.ai.reasoning_correct ?? false,
      answer_feedback: existing?.answer_feedback ?? row.ai.answer_feedback ?? '',
      reasoning_feedback: existing?.reasoning_feedback ?? row.ai.reasoning_feedback ?? '',
      override_reason: existing?.override_reason ?? '',
    };
  });
};

export const reviewHasOverride = (row: ReviewQuestionRow, draft: TaskReviewQuestion) =>
  row.ai.answer_correct !== draft.answer_correct || row.ai.reasoning_correct !== draft.reasoning_correct;

export const reviewQuestionError = (row: ReviewQuestionRow, draft: TaskReviewQuestion): string | null => {
  if (!draft.reasoning_feedback.trim()) return '請填寫理由判定說明。';
  if (row.question.type === 'cloze' && !draft.answer_feedback.trim()) return '請填寫答案判定說明。';
  if (reviewHasOverride(row, draft) && !draft.override_reason.trim()) return '與初判不同時，請記錄改判原因。';
  if (row.ai.answer_correct !== draft.answer_correct
    && draft.answer_feedback.trim() === (row.ai.answer_feedback || '').trim()) return '答案已改判，請一併更新答案判定說明。';
  if (row.ai.reasoning_correct !== draft.reasoning_correct
    && draft.reasoning_feedback.trim() === (row.ai.reasoning_feedback || '').trim()) return '理由已改判，請一併更新理由判定說明。';
  return null;
};

export const formatReviewAnswer = (value: unknown, question?: TaskQuestion): string => {
  if (value === true) return '是';
  if (value === false) return '否';
  if (Array.isArray(value)) return value.map(item => formatReviewAnswer(item, question)).join('、');
  if (value === null || value === undefined || value === '') return '尚未填寫';
  const option = question?.options?.find(item => item.value === value);
  return option?.label || String(value);
};

export const monitorPhase = (snapshot: AdminMonitorSnapshot) => {
  if (snapshot.session.status === 'archived') return { id: 'archived', label: '已封存', step: -1 };
  const attempt = snapshot.attempt;
  if (attempt?.status === 'failed') return { id: 'failed', label: '處理失敗', step: attempt.review_payload?.approved_at ? 2 : 1 };
  if (attempt?.status === 'awaiting_review') return { id: 'review', label: '待人工核對', step: 1 };
  if (attempt?.status === 'processing') return { id: 'judging', label: '系統初判中', step: 1 };
  if (attempt?.status === 'preparing_chat') return { id: 'preparing', label: '準備 AI 互動', step: 2 };
  if (attempt?.status === 'ready') return { id: 'ready', label: '等待受測者銜接', step: 2 };
  if (snapshot.stage === 'posttest_completed' || snapshot.posttest?.stage === 'completed' || snapshot.posttest?.completed_at) return { id: 'complete', label: '施測完成', step: 3 };
  if (snapshot.stage?.startsWith('posttest_') || snapshot.posttest) return { id: 'posttest', label: '後續評量', step: 3 };
  if (snapshot.session.status === 'completed') return { id: 'posttest', label: 'AI 互動已結束', step: 3 };
  if (snapshot.session.status === 'conversation_started' || snapshot.conversation) return { id: 'chat', label: 'AI 互動中', step: 2 };
  return { id: 'task', label: '作答中', step: 0 };
};
