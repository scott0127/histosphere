import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { parse, compileScript, compileTemplate } from 'vue/compiler-sfc';

const taskControl = await globalThis.loadTsModule('composables/useTaskControl.ts');
const task = {
  id: 'task-1', event_id: 'event-1', title: '法國大革命',
  story_text: '內部來源，不是第二份題文。',
  error_elicitation_task_full_text: '共同背景。\n\n三級會議原先如何表決？{{blank:q01}}',
  evaluation_payload: {}, revision_state: 'manual',
};
const question = (id = 'q01', type = 'cloze') => ({
  ...taskControl.createTaskQuestion(type, '', Number(id.slice(1))),
  correct_answer: type === 'true_false' ? false : type === 'multiple_choice' ? 'A' : ['按等級', '每個等級一票'],
  reasoning_criteria: '理由須指出每個等級各有一票。',
});
const payload = (questions = [question()], extra = {}) => ({ contract_version: 'error_elicitation_v1', questions, ...extra });
const json = (questions, extra) => JSON.stringify(payload(questions, extra));
const issues = (value, fullText = task.error_elicitation_task_full_text) => taskControl.validateTaskControlPayload({ ...task, error_elicitation_task_full_text: fullText }, JSON.stringify(value));

test('task editor creates only supported question types without prompt or a copied answer', () => {
  for (const type of ['cloze', 'multiple_choice', 'true_false']) {
    const q = taskControl.createTaskQuestion(type, 'internal source', 12);
    assert.equal(q.id, 'q12');
    assert.equal(q.required, true);
    assert.equal(q.reasoning_criteria, '');
    assert.ok(Array.isArray(q.options));
    assert.equal(q.source_text, 'internal source');
    for (const field of ['prompt', 'placeholder', 'blank_id', 'explanation']) assert.equal(field in q, false);
    assert.notEqual(q.correct_answer, 'internal source');
  }
  assert.equal(taskControl.createTaskQuestion().type, 'cloze');
  assert.throws(() => taskControl.createTaskQuestion('short_answer'));
});

test('task editor inserts the answer marker after selected prose without deleting the question', () => {
  const fullText = '共同背景。\n\n三級會議如何表決？\n\n下一段。';
  const start = fullText.indexOf('三級');
  const end = fullText.indexOf('\n\n下一');
  const inserted = taskControl.insertQuestionToken(fullText, 'q01', start, end);
  assert.equal(inserted.fullText, '共同背景。\n\n三級會議如何表決？{{blank:q01}}\n\n下一段。');
  assert.equal(inserted.selectedText, '三級會議如何表決？');
  assert.equal(inserted.fullText.replace(inserted.token, ''), fullText);
  assert.equal(taskControl.insertQuestionToken(inserted.fullText, 'q01').fullText, inserted.fullText);
});

test('task editor clamps insertion positions and never splits an existing marker', () => {
  assert.equal(taskControl.insertQuestionToken('text', 'q01', -10).fullText, '{{blank:q01}}text');
  assert.equal(taskControl.insertQuestionToken('text', 'q01', 100).fullText, 'text{{blank:q01}}');
  assert.equal(taskControl.insertQuestionToken('text{{blank:q01}}', 'q02', 9).fullText, 'text{{blank:q01}}{{blank:q02}}');
});

test('task editor generates IDs above surviving questions and orphan tokens', () => {
  assert.equal(taskControl.nextTaskQuestionIndex(json([question('q01'), question('q03')])), 4);
  assert.equal(taskControl.nextTaskQuestionIndex(json([]), '{{blank:q15}}'), 16);
});

test('task editor reads prompt-free questions without learner fallback synthesis', () => {
  assert.deepEqual(taskControl.taskControlQuestions(task, json()), [question()]);
  assert.deepEqual(taskControl.taskControlQuestions(task, '{}'), []);
});

test('task editor preserves answer aliases and reasoning criteria in structured JSON', () => {
  const q = question();
  const updated = taskControl.updateTaskControlQuestion(task, '{"questions":[]}', q);
  assert.equal(JSON.parse(updated).contract_version, 'error_elicitation_v1');
  assert.deepEqual(taskControl.taskControlQuestions(task, updated), [q]);
  assert.deepEqual(taskControl.answersFromText('按等級\n每個等級一票\n按等級\n'), ['按等級', '每個等級一票']);
  assert.equal(taskControl.answersFromText('  按等級  '), '按等級');
});

test('task editor type changes preserve ID and criteria while resetting incompatible keys', () => {
  const q = { ...question(), source_text: 'internal' };
  const changed = taskControl.changeTaskQuestionType(q, 'true_false');
  assert.equal(changed.id, q.id);
  assert.equal(changed.reasoning_criteria, q.reasoning_criteria);
  assert.equal(changed.source_text, q.source_text);
  assert.equal(changed.correct_answer, true);
  assert.deepEqual(changed.options, []);
  assert.equal(taskControl.changeTaskQuestionType(changed, 'multiple_choice').correct_answer, 'A');
});

test('task editor removes only the matching question and markers, preserving all prose and other metadata', () => {
  const extra = { rubric: '保留其他設定', materials: [{ id: 'm01', title: '史料', text: '正文' }], all_correct_fallback: { id: 'fallback' } };
  const result = taskControl.removeQuestionAndToken(json([question(), question('q02')], extra), '甲{{blank:q01}}乙{{blank:q02}}丙{{blank:q01}}', 'q01');
  assert.equal(result.fullText, '甲乙{{blank:q02}}丙');
  assert.deepEqual(JSON.parse(result.evaluationJson), payload([question('q02')], extra));
});

test('task editor reorders complete question paragraphs with markers, not answer assignments', () => {
  const fullText = '共同背景。\n\n第一題？{{blank:q01}}\n\n第二題？{{blank:q02}}\n\n尾文。';
  const original = json([question(), question('q02', 'true_false')], { materials: [] });
  const moved = taskControl.moveTaskControlQuestion(original, fullText, 'q02', -1);
  assert.equal(moved.moved, true);
  assert.equal(moved.fullText, '共同背景。\n\n第二題？{{blank:q02}}\n\n第一題？{{blank:q01}}\n\n尾文。');
  assert.deepEqual(JSON.parse(moved.evaluationJson).questions, [question('q02', 'true_false'), question()]);
  const restored = taskControl.moveTaskControlQuestion(moved.evaluationJson, moved.fullText, 'q02', 1);
  assert.equal(restored.fullText, fullText);
  assert.deepEqual(JSON.parse(restored.evaluationJson), JSON.parse(original));
});

test('task editor refuses ambiguous paragraph moves without changing the task', () => {
  for (const fullText of ['第一題{{blank:q01}}第二題{{blank:q02}}', '第一題{{blank:q01}}\n\n第二題{{blank:q02}}仍有文字', '第一題{{blank:q01}}\n\n{{blank:q02}}']) {
    const original = json([question(), question('q02')]);
    assert.deepEqual(taskControl.moveTaskControlQuestion(original, fullText, 'q02', -1), { evaluationJson: original, fullText, moved: false });
  }
});

test('task editor synchronizes question list order with manually edited full text', () => {
  const original = json([question('q02'), question()]);
  const ordered = taskControl.syncTaskQuestionOrder(original, '第一題{{blank:q01}}第二題{{blank:q02}}');
  assert.deepEqual(JSON.parse(ordered).questions.map((q) => q.id), ['q01', 'q02']);
  assert.equal(taskControl.syncTaskQuestionOrder(ordered, '第一題{{blank:q01}}第二題{{blank:q02}}'), ordered);
  assert.equal(taskControl.taskQuestionExcerpt(task.error_elicitation_task_full_text, 'q01'), '三級會議原先如何表決？');
});

test('task editor accepts all three question types with exactly one marker per question', () => {
  const questions = [question(), question('q02', 'multiple_choice'), question('q03', 'true_false')];
  const fullText = '背景\n\n填空？{{blank:q01}}\n\n選擇？{{blank:q02}}\n\n敘述。{{blank:q03}}';
  assert.deepEqual(issues(payload(questions), fullText), []);
  questions[1].correct_answer = ['A', 'B'];
  assert.deepEqual(issues(payload(questions), fullText), []);
  delete questions[0].options;
  delete questions[2].options;
  assert.deepEqual(issues(payload(questions), fullText), []);
});

test('task editor rejects missing, duplicate, orphan and malformed markers for every type', () => {
  for (const type of ['cloze', 'multiple_choice', 'true_false']) {
    assert.match(issues(payload([question('q01', type)]), '題文').join('\n'), /恰好有一個/);
    assert.match(issues(payload([question('q01', type)]), '題文{{blank:q01}}{{blank:q01}}').join('\n'), /重複作答標記/);
  }
  assert.match(issues(payload(), '題文{{blank:q01}}{{blank:q02}}').join('\n'), /找不到對應/);
  assert.match(issues(payload(), '題文{{blank:q01}}{{blank:}}').join('\n'), /格式不正確/);
  assert.match(issues(payload([question(), question()])).join('\n'), /題目 ID q01 重複/);
  assert.match(issues(payload(), '{{blank:q01}}').join('\n'), /缺少題目敘述/);
});

test('task editor rejects legacy authoring, optional questions and missing criteria', () => {
  const q = { ...question(), prompt: '舊版題目', type: 'short_answer', required: false, reasoning_criteria: '  ' };
  const messages = issues(payload([q])).join('\n');
  for (const pattern of [/僅支援/, /prompt/, /必填/, /理由通過標準/]) assert.match(messages, pattern);
  assert.match(issues({ questions: [question()] }).join('\n'), /error_elicitation_v1/);
});

test('task editor does not silently discard legacy prose during structured edits', () => {
  const q = { ...question(), prompt: '這段舊版敘述尚未搬移。' };
  assert.equal(JSON.parse(taskControl.updateTaskControlQuestion(task, json([q]), q)).questions[0].prompt, q.prompt);
});

test('task editor validates answer types, empty aliases and option keys', () => {
  for (const answer of [null, 0, true, {}, [], ['valid', ' ']]) assert.ok(issues(payload([{ ...question(), correct_answer: answer }])).length);
  assert.ok(issues(payload([{ ...question('q01', 'true_false'), correct_answer: 'false' }])).length);
  assert.ok(issues(payload([{ ...question('q01', 'multiple_choice'), correct_answer: ['A', 'missing'] }])).length);
  const q = question('q01', 'multiple_choice');
  q.options[1].value = 'A';
  assert.match(issues(payload([q])).join('\n'), /不可重複/);
});

test('task editor rejects malformed JSON structures without crashing or replacing drafts', () => {
  for (const value of ['null', '[]', '42', '"text"', '{']) {
    assert.ok(taskControl.parseTaskEvaluationJson(value).error);
    assert.ok(taskControl.validateTaskControlPayload(task, value).length);
    assert.throws(() => taskControl.updateTaskControlQuestion(task, value, question()));
  }
  for (const questions of [null, {}, [null], [true], [{ id: 5 }]]) assert.ok(issues({ contract_version: 'error_elicitation_v1', questions }).length);
});

test('task editor materials round-trip text, image, source and attribution without changing questions', () => {
  const material = { ...taskControl.createTaskMaterial([]), title: '三級會議', text: '史料全文', image_url: 'https://example.org/image.png', source_url: 'https://example.org/source', attribution: '作者，CC BY' };
  const result = taskControl.updateTaskMaterials(json(), [material]);
  assert.deepEqual(taskControl.taskControlMaterials(result), [material]);
  assert.deepEqual(JSON.parse(result).questions, [question()]);
  assert.deepEqual(issues(JSON.parse(result)), []);
  assert.equal(taskControl.createTaskMaterial([material, { ...material, id: 'm03' }]).id, 'm04');
  assert.deepEqual(taskControl.taskControlMaterials(taskControl.updateTaskMaterials(result, [])), []);
});

test('task editor validates material IDs, content and safe source URLs', () => {
  const material = { id: 'm01', title: '圖像', text: '', image_url: 'https://example.org/image.png' };
  assert.deepEqual(issues(payload(undefined, { materials: [material] })), []);
  for (const url of ['javascript:alert(1)', 'data:image/png;base64,test', '/relative']) assert.ok(issues(payload(undefined, { materials: [{ ...material, image_url: url }] })).length);
  assert.ok(issues(payload(undefined, { materials: [material, material] })).length);
  assert.ok(issues(payload(undefined, { materials: [{ ...material, image_url: '' }] })).length);
  assert.ok(issues(payload(undefined, { materials: [null] })).length);
});

test('task editor preserves, validates and removes all-correct fallback independently of materials', () => {
  const fallback = { id: 'fallback-01', incorrect_claim: '三級會議原先採按人數表決。', correct_interpretation: '三級會議原先採按等級表決。', evidence_ids: ['E03'] };
  const updated = taskControl.updateTaskAllCorrectFallback(json(undefined, { materials: [] }), fallback);
  assert.deepEqual(taskControl.taskAllCorrectFallback(updated), fallback);
  assert.deepEqual(issues(JSON.parse(updated)), []);
  assert.equal(taskControl.taskAllCorrectFallback(taskControl.updateTaskAllCorrectFallback(updated, null)), null);
  assert.ok(issues(payload(undefined, { all_correct_fallback: { ...fallback, incorrect_claim: '' } })).length);
});

test('task editor history restores full text and JSON atomically, including aliases and materials', () => {
  const first = { title: task.title, fullText: task.error_elicitation_task_full_text, evaluationJson: json() };
  const second = { ...first, fullText: '另一題文{{blank:q01}}', evaluationJson: taskControl.updateTaskMaterials(first.evaluationJson, [{ id: 'm01', title: '史料', text: '正文' }]) };
  let result = taskControl.appendTaskHistoryEntry([], -1, first);
  result = taskControl.appendTaskHistoryEntry(result.entries, result.index, second);
  assert.deepEqual(result.entries[0], first);
  assert.deepEqual(result.entries[1], second);
  assert.equal(taskControl.sameTaskHistoryEntry(first, second), false);
  const unchanged = taskControl.appendTaskHistoryEntry(result.entries, result.index, second);
  assert.equal(unchanged.entries, result.entries);
  result = taskControl.appendTaskHistoryEntry(result.entries, 0, { ...first, title: 'branch' });
  assert.deepEqual(result.entries.map((entry) => entry.title), [task.title, 'branch']);
  for (const title of ['A', 'B', 'C']) result = taskControl.appendTaskHistoryEntry(result.entries, result.index, { ...first, title }, 2);
  assert.deepEqual(result.entries.map((entry) => entry.title), ['B', 'C']);
});

test('task editor Vue components compile and expose no per-question prompt or short-answer control', async () => {
  const root = 'components/task-control';
  for (const filename of (await readdir(root)).filter((name) => name.endsWith('.vue'))) {
    const source = await readFile(`${root}/${filename}`, 'utf8');
    const { descriptor, errors } = parse(source, { filename });
    assert.deepEqual(errors, [], filename);
    const script = descriptor.scriptSetup ? compileScript(descriptor, { id: filename }) : null;
    const compiled = compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script?.bindings } });
    assert.deepEqual(compiled.errors, [], filename);
  }
  const item = await readFile(`${root}/TaskControlItemEditor.vue`, 'utf8');
  assert.doesNotMatch(item, /v-model="draft\.(prompt|placeholder|required)"|value="short_answer"/);
  const preview = await readFile(`${root}/TaskControlPreview.vue`, 'utf8');
  assert.match(preview, /TaskStudentStory/);
  assert.match(preview, /TaskStudentRenderer/);
});
