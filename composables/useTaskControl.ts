// useTaskControl 集中管理研究者/老師 task 編輯端的資料轉換。
// evaluation_payload 仍存在 JSON 欄位中，這裡提供結構化題目編輯與 JSON 相容層。
import type {
  EventTask,
  TaskEvaluationPayload,
  TaskQuestion,
  TaskQuestionOption,
  TaskQuestionType,
} from '~/types';
import { normalizeTaskQuestions } from '~/composables/useStudentTask';

type ParsedTaskPayload = {
  payload: TaskEvaluationPayload;
  error: string | null;
};

const defaultQuestionType: TaskQuestionType = 'short_answer';
const inlineQuestionTypes = new Set<TaskQuestionType>(['cloze', 'multiple_choice', 'true_false']);
const blankPattern = /\{\{\s*blank:([a-zA-Z0-9_-]+)\s*\}\}/g;

// 安全解析 task JSON；解析失敗時回傳錯誤，讓 UI 顯示給研究者。
export const parseTaskEvaluationJson = (jsonText: string): ParsedTaskPayload => {
  try {
    const payload = JSON.parse(jsonText || '{}') as TaskEvaluationPayload;
    return { payload, error: null };
  } catch {
    return { payload: {}, error: 'evaluation_payload 不是合法 JSON。' };
  }
};

// 將 payload 穩定格式化，避免儲存時產生難讀的一行 JSON。
export const stringifyTaskEvaluationPayload = (payload: TaskEvaluationPayload) => {
  return JSON.stringify(payload || {}, null, 2);
};

// 取得研究者可編輯題目；舊 task 沒有 questions 時會用學生端同一套 fallback。
export const taskControlQuestions = (task: EventTask, evaluationJson: string) => {
  const parsed = parseTaskEvaluationJson(evaluationJson);
  if (Array.isArray(parsed.payload.questions)) {
    return parsed.payload.questions
      .filter((question): question is TaskQuestion => Boolean(question && question.id && question.prompt !== undefined))
      .map((question) => ({
        ...question,
        blank_id: question.blank_id || question.id,
        required: question.required !== false,
        options: Array.isArray(question.options) ? question.options : [],
      }));
  }
  const taskWithPayload = {
    ...task,
    evaluation_payload: parsed.payload,
  };
  return normalizeTaskQuestions(taskWithPayload);
};

const payloadQuestions = (payload: TaskEvaluationPayload) => {
  return Array.isArray(payload.questions) ? payload.questions : [];
};

const questionIdFromIndex = (index: number) => `q${String(index).padStart(2, '0')}`;

export const nextTaskQuestionIndex = (evaluationJson: string) => {
  const { payload } = parseTaskEvaluationJson(evaluationJson);
  const usedIds = new Set(payloadQuestions(payload).map((question) => question.id));
  let index = 1;
  while (usedIds.has(questionIdFromIndex(index))) {
    index += 1;
  }
  return index;
};

export const createTaskQuestion = (
  type: TaskQuestionType = defaultQuestionType,
  selectedText = '',
  nextIndex = 1,
): TaskQuestion => {
  const cleanSelectedText = selectedText.trim();
  const id = questionIdFromIndex(nextIndex);
  const baseQuestion: TaskQuestion = {
    id,
    blank_id: id,
    type,
    prompt: cleanSelectedText ? `請回答與「${cleanSelectedText}」相關的題目。` : '請輸入題目文字。',
    placeholder: '請輸入答案',
    source_text: cleanSelectedText || null,
    required: true,
    options: [],
  };

  if (type === 'cloze') {
    return {
      ...baseQuestion,
      prompt: cleanSelectedText ? '請補上這個空格。' : '請輸入填空題題目。',
      correct_answer: cleanSelectedText || null,
    };
  }

  if (type === 'multiple_choice') {
    const firstOption = cleanSelectedText || '選項 A';
    const secondOption = cleanSelectedText ? '其他' : '選項 B';
    return {
      ...baseQuestion,
      prompt: cleanSelectedText ? `請選出符合「${cleanSelectedText}」的選項。` : '請輸入選擇題題目。',
      correct_answer: firstOption,
      options: [
        { id: 'opt-1', label: firstOption, value: firstOption },
        { id: 'opt-2', label: secondOption, value: secondOption },
      ],
    };
  }

  if (type === 'true_false') {
    return {
      ...baseQuestion,
      prompt: cleanSelectedText ? `這個敘述是否正確：${cleanSelectedText}` : '請輸入是非題敘述。',
      placeholder: null,
      correct_answer: true,
    };
  }

  return {
    ...baseQuestion,
    blank_id: null,
    prompt: cleanSelectedText ? `請說明：${cleanSelectedText}` : '請輸入簡答題題目。',
    correct_answer: cleanSelectedText || null,
  };
};

export const insertQuestionToken = (
  displayText: string,
  questionId: string,
  selectionStart = displayText.length,
  selectionEnd = selectionStart,
) => {
  const start = Math.max(0, Math.min(selectionStart, displayText.length));
  const end = Math.max(start, Math.min(selectionEnd, displayText.length));
  const token = `{{blank:${questionId}}}`;
  const selectedText = displayText.slice(start, end);
  const nextDisplayText = `${displayText.slice(0, start)}${token}${displayText.slice(end)}`;
  return {
    displayText: nextDisplayText,
    selectedText,
    token,
    cursorPosition: start + token.length,
  };
};

export const blankIdsInDisplayText = (displayText: string) => {
  const ids: string[] = [];
  for (const match of displayText.matchAll(blankPattern)) {
    const blankId = match[1];
    if (blankId) ids.push(blankId);
  }
  return ids;
};

export const questionInsertedInStory = (displayText: string, question: TaskQuestion) => {
  const blankId = question.blank_id || question.id;
  return blankIdsInDisplayText(displayText).includes(blankId);
};

export const removeQuestionAndToken = (
  evaluationJson: string,
  displayText: string,
  questionId: string,
) => {
  const { payload } = parseTaskEvaluationJson(evaluationJson);
  const questions = payloadQuestions(payload);
  const target = questions.find((question) => question.id === questionId);
  const tokenIds = new Set([questionId, target?.blank_id].filter(Boolean));
  const nextDisplayText = displayText.replace(blankPattern, (match, blankId: string) => {
    return tokenIds.has(blankId) ? '' : match;
  });
  return {
    displayText: nextDisplayText,
    evaluationJson: stringifyTaskEvaluationPayload({
      ...payload,
      questions: questions.filter((question) => question.id !== questionId),
    }),
  };
};

export const renumberQuestionLabels = (questions: TaskQuestion[]) => {
  return questions.map((question, index) => ({
    question,
    label: `Q${String(index + 1).padStart(2, '0')}`,
  }));
};

// 新增一題，預設為簡答題，研究者可再改為填空、選擇或是非。
export const addTaskControlQuestion = (
  task: EventTask,
  evaluationJson: string,
  type: TaskQuestionType = defaultQuestionType,
  selectedText = '',
) => {
  const { payload } = parseTaskEvaluationJson(evaluationJson);
  const questions = payloadQuestions(payload);
  const question = createTaskQuestion(type, selectedText || task.display_text || '', nextTaskQuestionIndex(evaluationJson));
  return stringifyTaskEvaluationPayload({
    ...payload,
    questions: [...questions, question],
  });
};

// 更新單一題目並寫回 JSON 字串。
export const updateTaskControlQuestion = (
  _task: EventTask,
  evaluationJson: string,
  nextQuestion: TaskQuestion,
) => {
  const { payload } = parseTaskEvaluationJson(evaluationJson);
  const currentQuestions = payloadQuestions(payload);
  const nextQuestions = currentQuestions.map((question) =>
    question.id === nextQuestion.id ? sanitizeTaskQuestion(nextQuestion) : question,
  );

  if (!nextQuestions.some((question) => question.id === nextQuestion.id)) {
    nextQuestions.push(sanitizeTaskQuestion(nextQuestion));
  }

  return stringifyTaskEvaluationPayload({
    ...payload,
    questions: nextQuestions,
  });
};

// 刪除一題；若刪完沒有題目，保留空陣列讓研究者明確知道目前沒有正式題目。
export const removeTaskControlQuestion = (evaluationJson: string, questionId: string) => {
  const { payload } = parseTaskEvaluationJson(evaluationJson);
  const questions = payloadQuestions(payload);
  return stringifyTaskEvaluationPayload({
    ...payload,
    questions: questions.filter((question) => question.id !== questionId),
  });
};

// 基本驗證只檢查前端能判定的格式；正式評分規則仍由後端/LLM judgement 處理。
export const validateTaskControlPayload = (task: EventTask, evaluationJson: string) => {
  const { error } = parseTaskEvaluationJson(evaluationJson);
  if (error) return [error];

  const questions = taskControlQuestions(task, evaluationJson);
  const blankIds = blankIdsInDisplayText(task.display_text || '');
  const blankIdSet = new Set<string>();
  const questionBlankIds = new Set(questions.map((question) => question.blank_id || question.id));
  const issues: string[] = [];
  if (questions.length === 0) issues.push('至少需要一題 task 題目。');
  for (const blankId of blankIds) {
    if (blankIdSet.has(blankId)) {
      issues.push(`故事文本中有重複空格 ID：${blankId}。`);
    }
    blankIdSet.add(blankId);
    if (!questionBlankIds.has(blankId)) {
      issues.push(`故事文本中的空格 ${blankId} 找不到對應題目。`);
    }
  }
  for (const question of questions) {
    if (!question.prompt.trim()) issues.push(`題目 ${question.id} 缺少題目文字。`);
    const blankId = question.blank_id || question.id;
    const duplicateQuestionBlankIds = questions.filter((item) => (item.blank_id || item.id) === blankId);
    if (duplicateQuestionBlankIds.length > 1) {
      issues.push(`題目 ${question.id} 的空格 ID ${blankId} 與其他題目重複。`);
    }
    if (inlineQuestionTypes.has(question.type) && !blankIds.includes(blankId)) {
      issues.push(`題目 ${question.id} 尚未放進故事文本。`);
    }
    if (question.type === 'multiple_choice' && (!question.options || question.options.length < 2)) {
      issues.push(`題目 ${question.id} 是選擇題，至少需要兩個選項。`);
    }
    if (question.type === 'multiple_choice' && question.options?.length) {
      const optionValues = question.options.map((option) => option.value);
      if (!optionValues.includes(String(question.correct_answer ?? ''))) {
        issues.push(`題目 ${question.id} 的參考答案必須是選項之一。`);
      }
    }
    if (question.type === 'true_false' && typeof question.correct_answer !== 'boolean') {
      issues.push(`題目 ${question.id} 是是非題，參考答案必須是「是」或「否」。`);
    }
    if (question.type === 'cloze' && !String(question.correct_answer ?? '').trim()) {
      issues.push(`題目 ${question.id} 是填空題，請設定參考答案。`);
    }
  }
  return issues;
};

// 將多行選項文字轉成 options 結構，給 TaskControlItemEditor 使用。
export const optionsFromText = (text: string): TaskQuestionOption[] => {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => ({
      id: `opt-${index + 1}`,
      label: line,
      value: line,
    }));
};

// 清理題目物件，避免把不適用的欄位寫入太多雜訊。
const sanitizeTaskQuestion = (question: TaskQuestion): TaskQuestion => {
  const next: TaskQuestion = {
    ...question,
    blank_id: question.blank_id || question.id,
    prompt: String(question.prompt || '').trim(),
    required: question.required !== false,
  };
  if (next.type === 'true_false') {
    if (next.correct_answer === 'true') next.correct_answer = true;
    if (next.correct_answer === 'false') next.correct_answer = false;
    next.options = [];
    return next;
  }
  if (next.type !== 'multiple_choice') {
    next.options = [];
  }
  return next;
};
