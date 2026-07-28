import assert from 'node:assert/strict';
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
  assert.notEqual(
    state.taskAuthoringSignature({ ...sampleTask, display_text: `${sampleTask.display_text}新增` }, evaluationJson),
    baseline,
  );
  assert.notEqual(
    state.taskAuthoringSignature(sampleTask, evaluationJson.replace('"questions"', '"questions_updated"')),
    baseline,
  );
});
