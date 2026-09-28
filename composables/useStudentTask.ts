import type {
  EventTask,
  ExperimentCondition,
  TaskAnswerValue,
  TaskAttempt,
  TaskQuestion,
  TaskStudentAnswer,
} from '~/types';
import { ERROR_ELICITATION_CONTRACT_VERSION } from '~/types/index';
import { experimentConditionCode } from '~/utils/experimentConditions';

export type TaskStorySegment =
  | { type: 'text'; text: string }
  | { type: 'blank'; question: TaskQuestion };

const createBlankPattern = () => /\{\{\s*blank:([a-zA-Z0-9_-]+)\s*\}\}/g;
const objectiveTypes = new Set(['cloze', 'multiple_choice', 'true_false']);

export const isErrorElicitationTask = (task?: EventTask | null) => {
  return task?.evaluation_payload?.contract_version === ERROR_ELICITATION_CONTRACT_VERSION;
};

export const studentConditionCode = (condition: ExperimentCondition) => experimentConditionCode(condition);

export const studentActivityTitle = (condition: ExperimentCondition) => {
  const code = studentConditionCode(condition);
  return code ? `${code}模式` : '活動代號未設定';
};

export const normalizeTaskQuestions = (task: EventTask): TaskQuestion[] => {
  const questions = Array.isArray(task.evaluation_payload?.questions)
    ? task.evaluation_payload.questions
    : [];
  const newFormat = isErrorElicitationTask(task);

  return questions
    .filter((question) => question && typeof question.id === 'string' && question.id.trim()
      && (newFormat
        ? objectiveTypes.has(question.type)
        : (objectiveTypes.has(question.type) || question.type === 'short_answer')
          && typeof question.prompt === 'string' && question.prompt.trim()))
    .map((question) => newFormat ? {
      id: question.id,
      blank_id: question.id,
      type: question.type,
      required: true,
      options: Array.isArray(question.options) ? question.options : [],
    } : {
      ...question,
      blank_id: question.blank_id || question.id,
      required: question.required !== false,
      options: Array.isArray(question.options) ? question.options : [],
    });
};

export const hasInlineTaskBlanks = (task: EventTask) => {
  return createBlankPattern().test(task.error_elicitation_task_full_text || '');
};

export const taskConfigurationError = (task: EventTask): string | null => {
  const questions = normalizeTaskQuestions(task);
  if (!questions.length) return '任務尚未提供可作答的題目，請聯絡研究人員。';
  if (!isErrorElicitationTask(task)) return null;

  const markers = [...(task.error_elicitation_task_full_text || '').matchAll(createBlankPattern())]
    .map((match) => match[1]);
  const ids = questions.map((question) => question.id);
  const valid = questions.length === task.evaluation_payload.questions?.length
    && ids.every((id) => /^q\d{2,}$/.test(id))
    && new Set(ids).size === ids.length
    && markers.length === ids.length
    && ids.every((id) => markers.filter((marker) => marker === id).length === 1)
    && questions.every((question) => question.type !== 'multiple_choice' || Boolean(question.options?.length));
  return valid ? null : '任務題目與作答欄位不完整，請聯絡研究人員。';
};

export const buildTaskStorySegments = (task: EventTask): TaskStorySegment[] => {
  const fullText = task.error_elicitation_task_full_text || '';
  const questionByBlankId = new Map(
    normalizeTaskQuestions(task).map((question) => [question.blank_id || question.id, question]),
  );
  const segments: TaskStorySegment[] = [];
  const renderedIds = new Set<string>();
  let lastIndex = 0;

  fullText.replace(createBlankPattern(), (match, blankId: string, offset: number) => {
    if (offset > lastIndex) segments.push({ type: 'text', text: fullText.slice(lastIndex, offset) });
    const question = questionByBlankId.get(blankId);
    if (question && !renderedIds.has(question.id)) {
      segments.push({ type: 'blank', question });
      renderedIds.add(question.id);
    } else {
      segments.push({ type: 'text', text: '____' });
    }
    lastIndex = offset + match.length;
    return match;
  });

  if (lastIndex < fullText.length) segments.push({ type: 'text', text: fullText.slice(lastIndex) });
  return segments.length ? segments : [{ type: 'text', text: fullText }];
};

export const buildTaskReadingLayout = (task: EventTask) => {
  const segments = buildTaskStorySegments(task);
  const first = segments[0];
  // 題組沿用 QNN｜題幹格式；只把題前情境移到材料上方，不改題號或儲存內容。
  const heading = isErrorElicitationTask(task) && first?.type === 'text'
    ? /(?:^|\n)(Q\d{2,}[｜|])/i.exec(first.text) : null;
  if (!heading || first?.type !== 'text') return { introduction: '', segments };
  const offset = heading.index + heading[0].indexOf(heading[1]!);
  return {
    introduction: first.text.slice(0, offset).trim(),
    segments: [{ type: 'text' as const, text: first.text.slice(offset) }, ...segments.slice(1)],
  };
};

export const buildTaskQuestionLayout = (task: EventTask) => {
  const { introduction, segments } = buildTaskReadingLayout(task);
  const questions: { question: TaskQuestion; text: string; index: number }[] = [];
  let precedingText = '';

  for (const segment of segments) {
    if (segment.type === 'text') {
      precedingText += segment.text;
      continue;
    }
    const question = segment.question;
    questions.push({
      question: {
        id: question.id,
        blank_id: question.blank_id,
        type: question.type,
        required: question.required,
        options: question.options?.map(({ id, label, value }) => ({ id, label, value })),
        ...(question.prompt === undefined ? {} : { prompt: question.prompt }),
        ...(question.placeholder === undefined ? {} : { placeholder: question.placeholder }),
        ...(question.source_text === undefined ? {} : { source_text: question.source_text }),
      },
      // 顯示序號依本文順序；只移除開頭的題號，保留題目內其他文字。
      text: precedingText.replace(/^\s*Q\d{2,}[｜|]\s*/i, '').trim(),
      index: questions.length,
    });
    precedingText = '';
  }

  return { introduction, questions, trailingText: precedingText.trim() };
};

const hasTaskAnswerValue = (value: TaskAnswerValue) => {
  if (typeof value === 'string') return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  return typeof value === 'boolean';
};

export const isTaskAnswerComplete = (
  questions: TaskQuestion[],
  answers: TaskStudentAnswer[],
  task?: EventTask | null,
) => {
  if (!questions.length || (task && taskConfigurationError(task))) return false;
  const newFormat = isErrorElicitationTask(task);
  return questions.every((question) => {
    if (!newFormat && question.required === false) return true;
    const answer = answers.find((item) => item.question_id === question.id);
    if (!answer || !hasTaskAnswerValue(answer.value)) return false;
    if (!newFormat) return true;
    if (typeof answer.rationale !== 'string' || !answer.rationale.trim()) return false;
    if (question.type === 'true_false') return typeof answer.value === 'boolean';
    if (typeof answer.value !== 'string') return false;
    return question.type !== 'multiple_choice'
      || Boolean(question.options?.some((option) => option.value === answer.value));
  });
};

export const updateTaskAnswer = (
  answers: TaskStudentAnswer[],
  question: TaskQuestion,
  patch: Partial<Pick<TaskStudentAnswer, 'value' | 'rationale'>>,
): TaskStudentAnswer[] => {
  const existing = answers.find((answer) => answer.question_id === question.id);
  const next: TaskStudentAnswer = {
    question_id: question.id,
    blank_id: question.blank_id || question.id,
    type: question.type,
    prompt: question.prompt || '',
    value: existing?.value ?? null,
    rationale: existing?.rationale ?? '',
    ...patch,
  };
  return [...answers.filter((answer) => answer.question_id !== question.id), next];
};

export const restoreTaskAnswers = (
  task: EventTask,
  payload?: Record<string, unknown> | null,
): TaskStudentAnswer[] => {
  const rawAnswers = Array.isArray(payload?.answers) ? payload.answers : [];
  return normalizeTaskQuestions(task).flatMap((question) => {
    const answer = rawAnswers.find((item) => item && typeof item === 'object'
      && (item.question_id === question.id || (!isErrorElicitationTask(task)
        && item.blank_id === (question.blank_id || question.id))));
    if (!answer) return [];
    const value = typeof answer.value === 'string' || typeof answer.value === 'boolean'
      || (!isErrorElicitationTask(task) && Array.isArray(answer.value)) ? answer.value : null;
    return updateTaskAnswer([], question, {
      value,
      rationale: typeof answer.rationale === 'string' ? answer.rationale : '',
    });
  });
};

export const buildTaskResponsePayload = (answers: TaskStudentAnswer[], task?: EventTask | null) => {
  if (task && isErrorElicitationTask(task)) {
    const orderedAnswers = normalizeTaskQuestions(task).flatMap((question) => {
      const answer = answers.find((item) => item.question_id === question.id);
      return answer ? [answer] : [];
    });
    return {
      contract_version: ERROR_ELICITATION_CONTRACT_VERSION,
      answers: orderedAnswers.map((answer) => ({
        question_id: answer.question_id,
        value: answer.value,
        rationale: answer.rationale ?? '',
      })),
    };
  }
  return {
    answer_text: answers.map((answer) => `${answer.prompt}\n${taskAnswerValueToText(answer.value)}`).join('\n\n'),
    answers: answers.map((answer) => ({
      question_id: answer.question_id,
      blank_id: answer.blank_id,
      type: answer.type,
      prompt: answer.prompt,
      value: answer.value,
      rationale: answer.rationale ?? '',
    })),
  };
};

export const taskAnswerValueToText = (value: TaskAnswerValue) => {
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'boolean') return value ? '是' : '否';
  return value || '';
};

export type TaskAnswerReviewStatus = 'correct' | 'incorrect' | 'unanswered' | 'pending' | 'failed';

export type TaskAnswerReview = {
  question: Pick<TaskQuestion, 'id' | 'type' | 'options'>;
  label: string;
  value: TaskAnswerValue;
  questionText: string;
  answerText: string;
  rationale: string;
  status: TaskAnswerReviewStatus;
};

export const buildTaskAnswerReviews = (task: EventTask, attempt: TaskAttempt): TaskAnswerReview[] => {
  const answers = restoreTaskAnswers(task, attempt.response_payload);
  const segments = buildTaskReadingLayout(task).segments;
  const rawResults = attempt.judgement_payload?.question_results;
  const judgementByQuestionId = new Map(
    (Array.isArray(rawResults) ? rawResults : [])
      .filter((item): item is Record<string, unknown> => Boolean(item && typeof item === 'object'))
      .map((item) => [String(item.question_id || ''), item]),
  );

  return normalizeTaskQuestions(task).map((question, index) => {
    const answer = answers.find((item) => item.question_id === question.id);
    const result = judgementByQuestionId.get(question.id);
    const learnerAnswer = result?.learner_answer;
    const value = typeof learnerAnswer === 'string' || typeof learnerAnswer === 'boolean' || Array.isArray(learnerAnswer)
      ? learnerAnswer as TaskAnswerValue : answer?.value ?? null;
    const backendStatus = result?.correctness;
    let status: TaskAnswerReviewStatus = 'pending';
    // A processing failure is never evidence of an incorrect learner answer.
    if (attempt.status === 'failed') status = 'failed';
    else if (!hasTaskAnswerValue(value)) status = 'unanswered';
    else if (attempt.status === 'submitted'
      && (backendStatus === 'correct' || backendStatus === 'incorrect')) status = backendStatus;

    const selectedOption = question.options?.find((option) => option.value === value);
    const segmentIndex = segments.findIndex((segment) => segment.type === 'blank' && segment.question.id === question.id);
    const preceding = segments[segmentIndex - 1];
    // 舊作答未保存題幹時，沿用本文的題號段落，不以答案或判定說明代替題目。
    const questionText = typeof result?.question_text === 'string' && result.question_text.trim()
      ? result.question_text
      : question.prompt || (preceding?.type === 'text' ? preceding.text.trim() : '');
    return {
      question: { id: question.id, type: question.type, options: question.options },
      label: isErrorElicitationTask(task) ? question.id : `Q${String(index + 1).padStart(2, '0')}`,
      value,
      questionText: questionText.match(/(?:^|\n)\s*Q\d{2,}[｜|]\s*([\s\S]*)$/i)?.[1] || questionText,
      answerText: selectedOption?.label || taskAnswerValueToText(value) || '未作答',
      rationale: typeof result?.learner_rationale === 'string' ? result.learner_rationale : answer?.rationale ?? '',
      status,
    };
  });
};

export const taskReviewStatusLabel = (status?: TaskAnswerReviewStatus) => {
  if (status === 'correct') return '答對';
  if (status === 'incorrect') return '答錯';
  if (status === 'failed') return '處理失敗';
  if (status === 'unanswered') return '未作答';
  return '尚未判定';
};

export const taskMaterialUrl = (url?: string | null) => {
  if (!url) return undefined;
  // 本機史料圖片不必依賴外站；只允許圖片目錄，不接受路徑跳脫或任意 API。
  if (/^\/images\/(?:[a-zA-Z0-9_-]+\/)*[a-zA-Z0-9_-]+\.(?:jpe?g|png|webp|gif)$/i.test(url)) return url;
  try {
    const parsed = new URL(url);
    return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : undefined;
  } catch {
    return undefined;
  }
};
