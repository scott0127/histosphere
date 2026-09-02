import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
  sampleCondition,
  sampleEvent,
  samplePersona,
  sampleTask,
} from '../fixtures/histosphereFixtures.mjs';

const state = await globalThis.loadTsModule('utils/adminWorkspaceState.ts');

test('admin workspace state builds editable task and persona json maps', () => {
  const snapshot = {
    events: [
      {
        ...sampleEvent,
        personas: [samplePersona],
        latest_task: sampleTask,
      },
    ],
    conditions: [sampleCondition],
    sessions: [],
    research_logs: [],
  };

  const editable = state.buildAdminEditableJson(snapshot);

  assert.deepEqual(JSON.parse(editable.taskJson[sampleTask.id]), sampleTask.evaluation_payload);
  assert.deepEqual(JSON.parse(editable.personaJson[samplePersona.id]), samplePersona.prompt_profile);
});

test('admin workspace state sorts condition modes by research order', () => {
  const conditions = [
    { ...sampleCondition, id: 'c4', condition_key: 'ebl_roleplay' },
    { ...sampleCondition, id: 'c2', condition_key: 'ebl_no_roleplay' },
    { ...sampleCondition, id: 'c1', condition_key: 'no_ebl_no_roleplay' },
    { ...sampleCondition, id: 'c3', condition_key: 'no_ebl_roleplay' },
  ];

  const sorted = state.sortPromptConditions(conditions);

  assert.deepEqual(sorted.map((condition) => condition.condition_key), [
    'no_ebl_no_roleplay',
    'ebl_no_roleplay',
    'no_ebl_roleplay',
    'ebl_roleplay',
  ]);
  assert.equal(state.conditionOrdinal(sorted[0]), '01');
  assert.equal(state.conditionOrdinal(sorted[3]), '04');
  assert.match(state.conditionModeLabel(sorted[0]), /without EBL/);
});

test('admin workspace state formats event year ranges without custom ids', () => {
  assert.equal(state.eventYearRange({ ...sampleEvent, start_year: 1789, end_year: 1799 }), '1789 - 1799');
  assert.equal(state.eventYearRange({ ...sampleEvent, start_year: 1853, end_year: 1853 }), '1853');
  assert.equal(state.eventYearRange({ ...sampleEvent, start_year: null, end_year: null, century: 19 }), '19 世紀');
  assert.equal(state.eventYearRange({ ...sampleEvent, start_year: null, end_year: null, century: null }), '未設定');
});

test('task authoring signature changes only when editable task content changes', () => {
  const evaluationJson = JSON.stringify(sampleTask.evaluation_payload, null, 2);
  const baseline = state.taskAuthoringSignature(sampleTask, evaluationJson);

  assert.equal(state.taskAuthoringSignature({ ...sampleTask }, evaluationJson), baseline);
  assert.equal(state.taskAuthoringSignature({ ...sampleTask, story_text: 'server-side source changed' }, evaluationJson), baseline);
  assert.notEqual(
    state.taskAuthoringSignature({ ...sampleTask, error_elicitation_task_full_text: `${sampleTask.error_elicitation_task_full_text}新增` }, evaluationJson),
    baseline,
  );
  assert.notEqual(
    state.taskAuthoringSignature(sampleTask, evaluationJson.replace('"questions"', '"questions_updated"')),
    baseline,
  );
});

test('admin task patch uses only canonical authored fields and preserves keys, materials and fallback', () => {
  const payload = {
    contract_version: 'error_elicitation_v1',
    questions: [{ id: 'q01', type: 'cloze', options: [], correct_answer: ['A', 'Alias'], reasoning_criteria: 'Must cite the source.', required: true }],
    materials: [{ id: 'm01', title: 'Source', text: 'Source text', image_url: 'https://example.org/image.png', source_url: 'https://example.org/source', attribution: 'Author' }],
    all_correct_fallback: { id: 'fallback', incorrect_claim: 'Claim', correct_interpretation: 'Correction', evidence_ids: [] },
  };
  const task = { ...sampleTask, error_elicitation_task_full_text: 'Shared context.\n\nQuestion statement?{{blank:q01}}' };
  const patch = state.buildAdminTaskPatch(task, JSON.stringify(payload));
  assert.deepEqual(Object.keys(patch).sort(), ['title', 'error_elicitation_task_full_text', 'evaluation_payload', 'revision_state'].sort());
  assert.equal(patch.error_elicitation_task_full_text, task.error_elicitation_task_full_text);
  assert.deepEqual(patch.evaluation_payload, payload);
  assert.equal(patch.revision_state, 'teacher_modified');
  assert.equal('story_text' in patch, false);
  assert.equal('display_text' in patch, false);
  const signature = state.taskAuthoringSignature(task, JSON.stringify(payload));
  const changedMaterials = { ...payload, materials: [{ ...payload.materials[0], attribution: 'Another author' }] };
  assert.notEqual(signature, state.taskAuthoringSignature(task, JSON.stringify(changedMaterials)));
});

test('admin task patch refuses invalid full text and invalid contracts before API submission', () => {
  const q = { id: 'q01', type: 'true_false', options: [], correct_answer: false, required: true, reasoning_criteria: 'Criterion' };
  const payload = { contract_version: 'error_elicitation_v1', questions: [q] };
  assert.throws(() => state.buildAdminTaskPatch({ ...sampleTask, error_elicitation_task_full_text: 'No marker' }, JSON.stringify(payload)), /恰好有一個/);
  assert.throws(() => state.buildAdminTaskPatch(sampleTask, 'null'), /JSON 物件/);
  assert.throws(() => state.buildAdminTaskPatch(sampleTask, JSON.stringify({ questions: [q] })), /error_elicitation_v1/);
});

test('admin editor takes complete private task data from snapshot, never initialize', async () => {
  const privatePayload = {
    contract_version: 'error_elicitation_v1',
    questions: [{ id: 'q01', type: 'true_false', options: [], correct_answer: false, required: true, reasoning_criteria: 'Private criterion', source_text: 'Internal source' }],
    all_correct_fallback: { id: 'fallback', incorrect_claim: 'Claim', correct_interpretation: 'Correction' },
    materials: [{ id: 'm01', title: 'Source', text: 'Text' }],
  };
  const editable = state.buildAdminEditableJson({ events: [{ ...sampleEvent, personas: [], latest_task: { ...sampleTask, evaluation_payload: privatePayload } }] });
  assert.deepEqual(JSON.parse(editable.taskJson[sampleTask.id]), privatePayload);
  const workspace = await readFile('composables/useAdminWorkspace.ts', 'utf8');
  assert.match(workspace, /await fetchAdminSnapshot\(adminKey\.value\)/);
  assert.doesNotMatch(workspace, /initializeEventMaterial|\/event\/initialize/);
});
