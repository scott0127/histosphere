import type {
  ErrorElicitationQuestionType,
  EventTask,
  TaskAllCorrectFallback,
  TaskEvaluationPayload,
  TaskMaterial,
  TaskQuestion,
} from '~/types';

export const taskContractVersion = 'error_elicitation_v1' as const;
const questionTypes = new Set(['cloze', 'multiple_choice', 'true_false']);
const blankPattern = /\{\{\s*blank:([a-zA-Z0-9_-]+)\s*\}\}/g;
const isObject = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === 'object' && !Array.isArray(value));
const hasText = (value: unknown): value is string => typeof value === 'string' && Boolean(value.trim());

export type TaskEditorHistoryEntry = {
  title: string;
  fullText: string;
  evaluationJson: string;
};

export const parseTaskEvaluationJson = (jsonText: string): { payload: TaskEvaluationPayload; error: string | null } => {
  try {
    const payload: unknown = JSON.parse(jsonText || '{}');
    if (!isObject(payload)) return { payload: {}, error: 'evaluation_payload 必須是 JSON 物件。' };
    return { payload: payload as TaskEvaluationPayload, error: null };
  } catch {
    return { payload: {}, error: 'evaluation_payload 不是合法 JSON。' };
  }
};

export const stringifyTaskEvaluationPayload = (payload: TaskEvaluationPayload) => JSON.stringify(payload, null, 2);

const editablePayload = (evaluationJson: string) => {
  const { payload, error } = parseTaskEvaluationJson(evaluationJson);
  if (error) throw new Error(error);
  return payload;
};

const payloadQuestions = (payload: TaskEvaluationPayload): TaskQuestion[] => {
  return Array.isArray(payload.questions) ? payload.questions.filter(isObject) as unknown as TaskQuestion[] : [];
};

// Admin authoring never invents learner fallback questions or duplicate question prose.
export const taskControlQuestions = (_task: EventTask, evaluationJson: string) => {
  return payloadQuestions(parseTaskEvaluationJson(evaluationJson).payload)
    .filter((question) => typeof question.id === 'string');
};

export const taskAllCorrectFallback = (evaluationJson: string): TaskAllCorrectFallback | null => {
  const fallback = parseTaskEvaluationJson(evaluationJson).payload.all_correct_fallback;
  return isObject(fallback) ? fallback as unknown as TaskAllCorrectFallback : null;
};

export const updateTaskAllCorrectFallback = (evaluationJson: string, fallback: TaskAllCorrectFallback | null) => {
  const payload = { ...editablePayload(evaluationJson), contract_version: taskContractVersion };
  if (fallback) {
    payload.all_correct_fallback = { ...fallback, id: fallback.id.trim() || 'all-correct-fallback', evidence_ids: fallback.evidence_ids || [] };
  } else {
    delete payload.all_correct_fallback;
  }
  return stringifyTaskEvaluationPayload(payload);
};

export const sameTaskHistoryEntry = (current: TaskEditorHistoryEntry | undefined, next: TaskEditorHistoryEntry) => {
  return Boolean(current && current.title === next.title && current.fullText === next.fullText && current.evaluationJson === next.evaluationJson);
};

export const appendTaskHistoryEntry = (entries: TaskEditorHistoryEntry[], currentIndex: number, next: TaskEditorHistoryEntry, limit = 80) => {
  if (sameTaskHistoryEntry(entries[currentIndex], next)) return { entries, index: currentIndex };
  const nextEntries = [...entries.slice(0, currentIndex + 1), next].slice(-limit);
  return { entries: nextEntries, index: nextEntries.length - 1 };
};

export const blankIdsInDisplayText = (fullText: string) => Array.from(fullText.matchAll(blankPattern), (match) => match[1]!);

export const nextTaskQuestionIndex = (evaluationJson: string, fullText = '') => {
  const ids = [...payloadQuestions(parseTaskEvaluationJson(evaluationJson).payload).map((question) => question.id), ...blankIdsInDisplayText(fullText)];
  // Do not renumber surviving questions or fill gaps left by deleted questions.
  return Math.max(0, ...ids.map((id) => /^q\d+$/.test(id) ? Number(id.slice(1)) : 0)) + 1;
};

export const createTaskQuestion = (type: ErrorElicitationQuestionType = 'cloze', sourceText = '', nextIndex = 1): TaskQuestion => {
  if (!questionTypes.has(type)) throw new Error('僅支援填空、選擇與是非題。');
  return {
    id: `q${String(nextIndex).padStart(2, '0')}`,
    type,
    options: type === 'multiple_choice' ? [
      { id: 'opt-1', label: '選項 A', value: 'A' },
      { id: 'opt-2', label: '選項 B', value: 'B' },
    ] : [],
    correct_answer: type === 'true_false' ? true : type === 'multiple_choice' ? 'A' : '',
    reasoning_criteria: '',
    required: true,
    ...(sourceText.trim() ? { source_text: sourceText.trim() } : {}),
  };
};

export const changeTaskQuestionType = (question: TaskQuestion, type: ErrorElicitationQuestionType): TaskQuestion => {
  if (question.type === type) return question;
  const defaults = createTaskQuestion(type);
  return { ...question, type, options: defaults.options, correct_answer: defaults.correct_answer, required: true };
};

export const answersFromText = (text: string): string | string[] => {
  const answers = [...new Set(text.split('\n').map((line) => line.trim()).filter(Boolean))];
  return answers.length > 1 ? answers : answers[0] || '';
};

export const insertQuestionToken = (fullText: string, questionId: string, selectionStart = fullText.length, selectionEnd = selectionStart) => {
  const start = Math.max(0, Math.min(selectionStart, fullText.length));
  let end = Math.max(start, Math.min(selectionEnd, fullText.length));
  // A stale cursor inside a marker must not split that marker.
  for (const match of fullText.matchAll(blankPattern)) {
    if (end > match.index! && end < match.index! + match[0].length) end = match.index! + match[0].length;
  }
  const token = `{{blank:${questionId}}}`;
  const existing = Array.from(fullText.matchAll(blankPattern)).find((match) => match[1] === questionId);
  if (existing) return { fullText, selectedText: fullText.slice(start, end), token, cursorPosition: existing.index! + existing[0].length };
  return {
    fullText: `${fullText.slice(0, end)}${token}${fullText.slice(end)}`,
    selectedText: fullText.slice(start, end),
    token,
    cursorPosition: end + token.length,
  };
};

export const questionInsertedInStory = (fullText: string, question: TaskQuestion) => {
  return blankIdsInDisplayText(fullText).filter((id) => id === question.id).length === 1;
};

const orderQuestions = (questions: TaskQuestion[], fullText: string) => {
  const ids = blankIdsInDisplayText(fullText);
  return [...questions].sort((a, b) => {
    const position = (id: string) => ids.includes(id) ? ids.indexOf(id) : Number.MAX_SAFE_INTEGER;
    return position(a.id) - position(b.id);
  });
};

export const syncTaskQuestionOrder = (evaluationJson: string, fullText: string) => {
  const { payload, error } = parseTaskEvaluationJson(evaluationJson);
  if (error || !Array.isArray(payload.questions) || payload.questions.some((q) => !isObject(q))) return evaluationJson;
  const questions = orderQuestions(payload.questions, fullText);
  if (questions.every((question, index) => question === payload.questions![index])) return evaluationJson;
  return stringifyTaskEvaluationPayload({ ...payload, questions });
};

export const updateTaskControlQuestion = (task: EventTask, evaluationJson: string, nextQuestion: TaskQuestion) => {
  const payload = editablePayload(evaluationJson);
  const questions = payloadQuestions(payload);
  const next = { ...nextQuestion, required: true, options: nextQuestion.options || [], reasoning_criteria: nextQuestion.reasoning_criteria || '' };
  // Legacy prose remains intact until explicitly moved into the full text by the author.
  if (!next.prompt) delete next.prompt;
  if (!next.blank_id || next.blank_id === next.id) delete next.blank_id;
  const index = questions.findIndex((question) => question.id === next.id);
  if (index < 0) questions.push(next);
  else questions[index] = next;
  return stringifyTaskEvaluationPayload({ ...payload, contract_version: taskContractVersion, questions: orderQuestions(questions, task.error_elicitation_task_full_text || '') });
};

export const removeQuestionAndToken = (evaluationJson: string, fullText: string, questionId: string) => {
  const payload = editablePayload(evaluationJson);
  const questions = payloadQuestions(payload);
  const target = questions.find((question) => question.id === questionId);
  const tokenIds = new Set([questionId, target?.blank_id].filter(Boolean));
  return {
    fullText: fullText.replace(blankPattern, (match, id: string) => tokenIds.has(id) ? '' : match),
    evaluationJson: stringifyTaskEvaluationPayload({ ...payload, contract_version: taskContractVersion, questions: questions.filter((question) => question.id !== questionId) }),
  };
};

export const renumberQuestionLabels = (questions: TaskQuestion[]) => questions.map((question, index) => ({ question, label: `Q${String(index + 1).padStart(2, '0')}` }));

const questionBlock = (fullText: string, questionId: string) => {
  const matches = Array.from(fullText.matchAll(blankPattern));
  const tokens = matches.filter((match) => match[1] === questionId);
  if (tokens.length !== 1) return null;
  const token = tokens[0]!;
  const end = token.index! + token[0].length;
  // A paragraph ending in one answer marker is the smallest unambiguous movable unit.
  const before = fullText.slice(0, token.index);
  const boundaries = Array.from(before.matchAll(/\r?\n[\t ]*\r?\n/g));
  const boundary = boundaries.at(-1);
  const start = boundary ? boundary.index! + boundary[0].length : 0;
  if (!fullText.slice(start, token.index).trim() || matches.some((match) => match.index! >= start && match.index! < token.index!)) return null;
  if (fullText.slice(end).split(/\r?\n[\t ]*\r?\n/, 1)[0]!.trim()) return null;
  return { start, end, text: fullText.slice(start, end) };
};

export const taskQuestionExcerpt = (fullText: string, questionId: string) => {
  const token = Array.from(fullText.matchAll(blankPattern)).find((match) => match[1] === questionId);
  if (!token) return '';
  const before = fullText.slice(0, token.index).split(blankPattern).at(-1) || '';
  return before.trim().split(/\r?\n[\t ]*\r?\n/).at(-1)?.trim() || '';
};

export const moveTaskControlQuestion = (evaluationJson: string, fullText: string, questionId: string, direction: -1 | 1) => {
  const payload = editablePayload(evaluationJson);
  const questions = orderQuestions(payloadQuestions(payload), fullText);
  const index = questions.findIndex((question) => question.id === questionId);
  const neighbor = questions[index + direction];
  const unchanged = { evaluationJson, fullText, moved: false };
  if (index < 0 || !neighbor) return unchanged;
  const a = questionBlock(fullText, questionId);
  const b = questionBlock(fullText, neighbor.id);
  if (!a || !b) return unchanged;
  const [first, second] = a.start < b.start ? [a, b] : [b, a];
  if (first.end > second.start) return unchanged;
  const nextText = fullText.slice(0, first.start) + second.text + fullText.slice(first.end, second.start) + first.text + fullText.slice(second.end);
  return {
    moved: true,
    fullText: nextText,
    evaluationJson: stringifyTaskEvaluationPayload({ ...payload, contract_version: taskContractVersion, questions: orderQuestions(questions, nextText) }),
  };
};

export const taskControlMaterials = (evaluationJson: string): TaskMaterial[] => {
  const materials = parseTaskEvaluationJson(evaluationJson).payload.materials;
  return Array.isArray(materials) ? materials.filter((material) => isObject(material) && typeof material.id === 'string') : [];
};

export const createTaskMaterial = (materials: TaskMaterial[]): TaskMaterial => {
  const next = Math.max(0, ...materials.map((material) => /^m\d+$/.test(material.id) ? Number(material.id.slice(1)) : 0)) + 1;
  return { id: `m${String(next).padStart(2, '0')}`, title: '', text: '' };
};

export const updateTaskMaterials = (evaluationJson: string, materials: TaskMaterial[]) => {
  return stringifyTaskEvaluationPayload({ ...editablePayload(evaluationJson), contract_version: taskContractVersion, materials });
};

export const isTaskMaterialUrl = (value: string) => {
  try { return ['http:', 'https:'].includes(new URL(value).protocol); } catch { return false; }
};

export const validateTaskControlPayload = (task: EventTask, evaluationJson: string) => {
  const { payload, error } = parseTaskEvaluationJson(evaluationJson);
  if (error) return [error];
  const issues: string[] = [];
  if (payload.contract_version !== taskContractVersion) issues.push('任務必須使用 error_elicitation_v1 格式。');
  const fullText = task.error_elicitation_task_full_text || '';
  if (!fullText.trim()) issues.push('請填寫完整任務題文。');
  const ids = blankIdsInDisplayText(fullText);
  if (/\{\{\s*blank\s*:/.test(fullText.replace(blankPattern, ''))) issues.push('完整題文含有格式不正確的作答標記。');
  const rawQuestions: unknown[] = Array.isArray(payload.questions) ? payload.questions : [];
  if (!Array.isArray(payload.questions)) issues.push('questions 必須是陣列。');
  if (!rawQuestions.length) issues.push('至少需要一題任務題目。');
  const questions = rawQuestions.filter(isObject);
  if (questions.length !== rawQuestions.length) issues.push('每一題必須是 JSON 物件。');
  const questionIds = questions.map((question) => question.id);
  for (const id of new Set(ids)) {
    if (ids.filter((item) => item === id).length !== 1) issues.push(`完整題文中有重複作答標記：${id}。`);
    if (!questionIds.includes(id)) issues.push(`完整題文中的標記 ${id} 找不到對應題目。`);
  }
  for (const [index, question] of questions.entries()) {
    const label = typeof question.id === 'string' ? question.id : `#${index + 1}`;
    if (!hasText(question.id) || !/^[a-zA-Z0-9_-]+$/.test(String(question.id))) issues.push(`題目 ${label} 的固定 ID 格式不正確。`);
    if (questionIds.filter((id) => id === question.id).length > 1) issues.push(`題目 ID ${label} 重複。`);
    if (ids.filter((id) => id === question.id).length !== 1) issues.push(`題目 ${label} 必須在完整題文中恰好有一個作答標記。`);
    else if (!taskQuestionExcerpt(fullText, String(question.id))) issues.push(`題目 ${label} 的作答標記前缺少題目敘述。`);
    if (!questionTypes.has(String(question.type))) issues.push(`題目 ${label} 僅支援填空、選擇與是非題。`);
    if ('prompt' in question) issues.push(`題目 ${label} 的題目敘述須移入完整題文，並移除 JSON 中的 prompt。`);
    if (question.blank_id && question.blank_id !== question.id) issues.push(`題目 ${label} 的標記必須使用固定題目 ID。`);
    if (question.required !== true) issues.push(`題目 ${label} 的答案與理由必須設為必填。`);
    if (!hasText(question.reasoning_criteria)) issues.push(`題目 ${label} 缺少理由通過標準。`);
    if (question.source_text != null && typeof question.source_text !== 'string') issues.push(`題目 ${label} 的內部來源文字格式不正確。`);
    const answer = question.correct_answer;
    const answers = Array.isArray(answer) ? answer : [answer];
    if (question.type === 'true_false') {
      if (typeof answer !== 'boolean') issues.push(`題目 ${label} 的參考答案必須是「是」或「否」。`);
    } else if (!answers.length || !answers.every(hasText)) {
      issues.push(`題目 ${label} 請設定非空白的參考答案或可接受答案。`);
    }
    // 非選擇題可省略 options，與後端生成及驗證契約一致。
    const options = question.options === undefined && question.type !== 'multiple_choice' ? [] : question.options;
    if (!Array.isArray(options)) {
      issues.push(`題目 ${label} 的 options 必須是陣列。`);
    } else if (question.type === 'multiple_choice') {
      if (options.length < 2) issues.push(`題目 ${label} 至少需要兩個選項。`);
      if (options.some((option) => !isObject(option) || !hasText(option.id) || !hasText(option.label) || !hasText(option.value))) issues.push(`題目 ${label} 的每個選項都需要 ID、文字與值。`);
      const values = options.filter(isObject).map((option) => option.value);
      const optionIds = options.filter(isObject).map((option) => option.id);
      if (new Set(values).size !== values.length || new Set(optionIds).size !== optionIds.length) issues.push(`題目 ${label} 的選項 ID 與值不可重複。`);
      if (!answers.every((value) => values.includes(value))) issues.push(`題目 ${label} 的參考答案必須是選項值之一。`);
    } else if (options.length) {
      issues.push(`題目 ${label} 不是選擇題，options 必須為空陣列。`);
    }
  }
  if (payload.materials !== undefined) {
    if (!Array.isArray(payload.materials)) issues.push('materials 必須是陣列。');
    else {
      const seen = new Set<string>();
      for (const material of payload.materials) {
        if (!isObject(material) || !hasText(material.id) || !hasText(material.title) || typeof material.text !== 'string') {
          issues.push('每份學習材料都需要固定 ID、標題與文字欄位。');
          continue;
        }
        if (seen.has(material.id)) issues.push(`學習材料 ID ${material.id} 重複。`);
        seen.add(material.id);
        if (!material.text.trim() && !hasText(material.image_url)) issues.push(`學習材料 ${material.id} 至少需要文字或圖片 URL。`);
        for (const field of ['image_url', 'source_url'] as const) {
          const value = material[field];
          if (value != null && value !== '' && (typeof value !== 'string' || !isTaskMaterialUrl(value))) issues.push(`學習材料 ${material.id} 的 ${field} 必須是 HTTP(S) URL。`);
        }
        if (material.attribution != null && typeof material.attribution !== 'string') issues.push(`學習材料 ${material.id} 的來源署名必須是文字。`);
      }
    }
  }
  const fallback = payload.all_correct_fallback;
  if (fallback != null) {
    if (!isObject(fallback)) issues.push('全部答對時的對話素材格式不正確。');
    else {
      if (!hasText(fallback.id)) issues.push('全部答對時的對話素材缺少固定 ID。');
      if (!hasText(fallback.incorrect_claim)) issues.push('請填寫全部答對時使用的第三方錯誤說法。');
      if (!hasText(fallback.correct_interpretation)) issues.push('請填寫第三方錯誤說法的核定正確解釋。');
      if (fallback.evidence_ids !== undefined && (!Array.isArray(fallback.evidence_ids) || !fallback.evidence_ids.every(hasText))) issues.push('全部答對時的史料 ID 必須是文字陣列。');
    }
  }
  return issues;
};
