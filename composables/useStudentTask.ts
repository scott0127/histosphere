// useStudentTask 集中管理受測者 task 頁會用到的純前端邏輯。
// 這裡不直接操作 DOM；主要負責題目正規化、答案整理、活動名稱與本機進度紀錄。
import type {
  EventTask,
  ExperimentCondition,
  TaskAnswerValue,
  TaskAttempt,
  TaskQuestion,
  TaskStudentAnswer,
} from '~/types';
import { experimentConditionCode } from '~/utils/experimentConditions';

export type TaskStorySegment =
  | { type: 'text'; text: string }
  | { type: 'blank'; question: TaskQuestion };

const createBlankPattern = () => /\{\{\s*blank:([a-zA-Z0-9_-]+)\s*\}\}/g;

export const studentConditionCode = (condition: ExperimentCondition) => {
  return experimentConditionCode(condition);
};

// 學生端只顯示實驗代號，避免暴露實際 treatment。
export const studentActivityTitle = (condition: ExperimentCondition) => {
  const code = studentConditionCode(condition);
  return code ? `${code}模式` : '活動代號未設定';
};

// 從 event_tasks.evaluation_payload 取出正式題目；若舊資料還沒有 questions，就建立可作答的 fallback 題。
export const normalizeTaskQuestions = (task: EventTask): TaskQuestion[] => {
  const questions = Array.isArray(task.evaluation_payload?.questions)
    ? task.evaluation_payload.questions
    : [];

  const normalized = questions
    .filter((question): question is TaskQuestion => Boolean(question && question.id && question.prompt))
    .map((question) => ({
      ...question,
      blank_id: question.blank_id || question.id,
      required: question.required !== false,
      options: Array.isArray(question.options) ? question.options : [],
    }));

  if (normalized.length > 0) return normalized;

  return [
    {
      id: 'main-answer',
      blank_id: 'main-answer',
      type: 'short_answer',
      prompt: task.display_text || task.title || '請完成前置任務。',
      placeholder: '請用自己的話補上你認為重要的缺口、理由或不確定之處...',
      required: true,
    },
  ];
};

// 判斷這份 task 是否使用故事內嵌空格；有 blank token 時，學生會直接在故事中作答。
export const hasInlineTaskBlanks = (task: EventTask) => {
  return createBlankPattern().test(task.display_text || '');
};

// 將 display_text 切成文字與空格片段；空格 token 格式為 {{blank:question_id}}。
export const buildTaskStorySegments = (task: EventTask): TaskStorySegment[] => {
  const displayText = task.display_text || '';
  const blankPattern = createBlankPattern();
  const questions = normalizeTaskQuestions(task);
  const questionByBlankId = new Map(
    questions.map((question) => [question.blank_id || question.id, question]),
  );
  const segments: TaskStorySegment[] = [];
  let lastIndex = 0;

  displayText.replace(blankPattern, (match, blankId: string, offset: number) => {
    if (offset > lastIndex) {
      segments.push({ type: 'text', text: displayText.slice(lastIndex, offset) });
    }

    const question = questionByBlankId.get(blankId);
    if (question) {
      segments.push({ type: 'blank', question });
    } else {
      segments.push({ type: 'text', text: '____' });
    }

    lastIndex = offset + match.length;
    return match;
  });

  if (lastIndex < displayText.length) {
    segments.push({ type: 'text', text: displayText.slice(lastIndex) });
  }

  return segments.length > 0 ? segments : [{ type: 'text', text: displayText }];
};

// 檢查必填題是否都有答案，避免空白送出。
export const isTaskAnswerComplete = (questions: TaskQuestion[], answers: TaskStudentAnswer[]) => {
  return questions.every((question) => {
    if (question.required === false) return true;
    const answer = answers.find((item) => item.question_id === question.id);
    if (!answer) return false;
    if (typeof answer.value === 'string') return answer.value.trim().length > 0;
    if (Array.isArray(answer.value)) return answer.value.length > 0;
    return answer.value !== null && answer.value !== undefined;
  });
};

// 將結構化答案轉成後端既有 LLM judgement 可讀的 payload，同時保留 answer_text 相容舊 prompt。
export const buildTaskResponsePayload = (answers: TaskStudentAnswer[]) => {
  const answerText = answers
    .map((answer) => `${answer.prompt}\n${taskAnswerValueToText(answer.value)}`)
    .join('\n\n');

  return {
    answer_text: answerText,
    answers: answers.map((answer) => ({
      question_id: answer.question_id,
      blank_id: answer.blank_id,
      type: answer.type,
      prompt: answer.prompt,
      value: answer.value,
    })),
  };
};

// 將 UI 中不同型別的答案轉成給 LLM 閱讀的文字。
export const taskAnswerValueToText = (value: TaskAnswerValue) => {
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'boolean') return value ? '是' : '否';
  return value || '';
};

export type TaskAnswerReviewStatus = 'correct' | 'incorrect' | 'unanswered' | 'ungraded';

export type TaskAnswerReview = {
  question: TaskQuestion;
  label: string;
  value: TaskAnswerValue;
  answerText: string;
  status: TaskAnswerReviewStatus;
};

const hasTaskAnswerValue = (value: TaskAnswerValue) => {
  if (typeof value === 'string') return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  return value !== null && value !== undefined;
};

const normalizeComparableText = (value: unknown) => {
  return String(value ?? '')
    .normalize('NFKC')
    .trim()
    .replace(/\s+/g, ' ')
    .toLocaleLowerCase();
};

const taskAnswerMatches = (answer: TaskAnswerValue, expected: unknown) => {
  if (typeof expected === 'boolean') {
    if (typeof answer === 'boolean') return answer === expected;
    const normalized = normalizeComparableText(answer);
    return expected ? ['true', '是'].includes(normalized) : ['false', '否'].includes(normalized);
  }

  if (Array.isArray(expected)) {
    if (Array.isArray(answer)) {
      const actualValues = answer.map(normalizeComparableText).sort();
      const expectedValues = expected.map(normalizeComparableText).sort();
      return actualValues.length === expectedValues.length
        && actualValues.every((value, index) => value === expectedValues[index]);
    }
    return expected.some((value) => normalizeComparableText(value) === normalizeComparableText(answer));
  }

  return normalizeComparableText(answer) === normalizeComparableText(expected);
};

const taskAttemptAnswers = (attempt: TaskAttempt): TaskStudentAnswer[] => {
  const rawAnswers = attempt.response_payload?.answers;
  if (!Array.isArray(rawAnswers)) return [];

  return rawAnswers.flatMap((item) => {
    if (!item || typeof item !== 'object') return [];
    const answer = item as Partial<TaskStudentAnswer>;
    if (typeof answer.question_id !== 'string') return [];
    return [{
      question_id: answer.question_id,
      blank_id: typeof answer.blank_id === 'string' ? answer.blank_id : answer.question_id,
      type: answer.type || 'short_answer',
      prompt: typeof answer.prompt === 'string' ? answer.prompt : '',
      value: answer.value ?? null,
    }];
  });
};

// 將提交答案轉成逐題事實；只判斷正誤，不產生 misconception summary 或解析。
export const buildTaskAnswerReviews = (task: EventTask, attempt: TaskAttempt): TaskAnswerReview[] => {
  const answers = taskAttemptAnswers(attempt);
  const answerByQuestionId = new Map(answers.map((answer) => [answer.question_id, answer]));

  return normalizeTaskQuestions(task).map((question, index) => {
    const answer = answerByQuestionId.get(question.id)
      || answers.find((item) => item.blank_id === (question.blank_id || question.id));
    const value = answer?.value ?? null;
    let status: TaskAnswerReviewStatus = 'ungraded';

    if (!hasTaskAnswerValue(value)) {
      status = 'unanswered';
    } else if (question.correct_answer !== undefined && question.correct_answer !== null) {
      status = taskAnswerMatches(value, question.correct_answer) ? 'correct' : 'incorrect';
    }

    return {
      question,
      label: `Q${String(index + 1).padStart(2, '0')}`,
      value,
      answerText: taskAnswerValueToText(value) || '未作答',
      status,
    };
  });
};
