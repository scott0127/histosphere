import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { computed } from 'vue';
import ts from 'typescript';

const conditions = await globalThis.loadTsModule('utils/experimentConditions.ts');
globalThis.participantActivityTestUtils = await globalThis.loadTsModule('utils/participantActivities.ts');
const source = await readFile('composables/useExperimentSession.ts', 'utf8');
const apiNames = ['fetchAdminParticipantPreview', 'fetchParticipantMe', 'fetchUserProgress', 'initializeEventMaterial'];
const stubApiUrl = `data:text/javascript;base64,${Buffer.from(apiNames.map((name) =>
  `export const ${name} = (...args) => globalThis.participantPreviewTestApi.${name}(...args);`,
).join('\n')).toString('base64')}`;
const conditionUrl = `data:text/javascript;base64,${Buffer.from(
  `export const experimentConditionCodeByKey = ${JSON.stringify(conditions.experimentConditionCodeByKey)};`,
).toString('base64')}`;
const activityUrl = `data:text/javascript;base64,${Buffer.from(
  'export const { currentParticipantActivity, getParticipantActivities } = globalThis.participantActivityTestUtils;',
).toString('base64')}`;
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText
  .replaceAll("from 'vue'", `from '${import.meta.resolve('vue')}'`)
  .replaceAll("from '~/utils/histosphereApi'", `from '${stubApiUrl}'`)
  .replaceAll("from '~/utils/experimentConditions'", `from '${conditionUrl}'`)
  .replaceAll("from '~/utils/participantActivities'", `from '${activityUrl}'`);
const { useExperimentSession } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);

const participant = { id: 't001', code: 'T001', auth_user_id: 'real-user', status: 'active', condition_list: ['02', '04'] };
const response = (progress = []) => ({ participant: structuredClone(participant), test_user_id: 'isolated-user', progress });
const eblKey = Object.keys(conditions.experimentConditionCodeByKey).find((key) => conditions.experimentConditionCodeByKey[key] === '02');
const roleplayKey = Object.keys(conditions.experimentConditionCodeByKey).find((key) => conditions.experimentConditionCodeByKey[key] === '04');
const setup = (overrides = {}) => {
  const forbidden = async () => { throw new Error('Preview must not use regular participant/progress APIs'); };
  globalThis.participantPreviewTestApi = {
    fetchAdminParticipantPreview: async () => response(),
    fetchParticipantMe: forbidden,
    fetchUserProgress: forbidden,
    initializeEventMaterial: forbidden,
    ...overrides,
  };
  return useExperimentSession(computed(() => 'signed-in-admin'));
};

test('participant preview uses isolated progress and advances only after posttest completion', async () => {
  const flow = setup();
  await flow.loadAdminParticipantPreview('admin-key', 't001');
  assert.deepEqual(flow.assignedConditionCodes.value, ['02', '04']);
  assert.equal(flow.currentAssignedConditionCode.value, '02');
  const progress = [{ event_id: 'event-one', condition_key: eblKey, status: 'completed', posttest_stage: 'engagement', session_id: 'test-session', updated_at: '2026-09-23T00:00:00Z' }];
  globalThis.participantPreviewTestApi.fetchAdminParticipantPreview = async () => response(progress);
  await flow.loadProgressFromApi();
  assert.equal(flow.currentAssignedConditionCode.value, '02');
  progress[0].posttest_stage = 'completed';
  await flow.loadProgressFromApi();
  assert.equal(flow.currentAssignedConditionCode.value, '04');
});

test('preview initialization uses test identity, persists preview context, and refuses out-of-order starts', async () => {
  let request;
  const navigation = [];
  globalThis.navigateTo = async (destination) => navigation.push(destination);
  globalThis.useState = () => ({ value: null });
  const flow = setup({ initializeEventMaterial: async (input) => {
    request = input;
    return { event_id: 'event-one', session_id: 'test-session', task: { id: 'task-one' }, condition: { condition_key: eblKey } };
  } });
  await flow.loadAdminParticipantPreview('admin-key', 't001');
  const event = { id: 'event-one', canonical_name: 'Test event' };
  const options = { adminKey: 'admin-key', previewParticipantId: 't001', userId: 'real-user', reuseProgress: true };
  await flow.startCondition(event, { condition_key: roleplayKey }, options);
  assert.equal(request, undefined);
  assert.match(flow.initializeError.value, /分派順序/);
  await flow.startCondition(event, { condition_key: eblKey }, options);
  assert.equal(request.userId, 'isolated-user');
  assert.equal(request.previewParticipantId, 't001');
  assert.equal(navigation.at(-1).query.authUserId, 'isolated-user');
});

test('failed preview reload clears stale assignment and never falls back to formal progress', async () => {
  const flow = setup();
  await flow.loadAdminParticipantPreview('admin-key', 't001');
  globalThis.participantPreviewTestApi.fetchAdminParticipantPreview = async () => { throw new Error('offline'); };
  await flow.loadProgressFromApi();
  assert.equal(flow.participant.value, null);
  assert.equal(flow.previewTestUserId.value, null);
  assert.equal(flow.currentAssignedConditionCode.value, null);
  assert.deepEqual(flow.progressByEvent.value, {});
  assert.ok(flow.participantError.value);
});

test('switching preview participant ignores an older pending response', async () => {
  let resolveOld;
  const flow = setup({ fetchAdminParticipantPreview: async (_key, id) => id === 't001'
    ? await new Promise((resolve) => { resolveOld = resolve; })
    : { participant: { ...participant, id: 't002', code: 'T002', condition_list: ['01', '03'] }, test_user_id: 'isolated-two', progress: [] },
  });
  const oldLoad = flow.loadAdminParticipantPreview('admin-key', 't001');
  await flow.resetForAuthScope();
  await flow.loadAdminParticipantPreview('admin-key', 't002');
  resolveOld(response());
  await oldLoad;
  assert.equal(flow.participant.value.id, 't002');
  assert.equal(flow.previewTestUserId.value, 'isolated-two');
  assert.equal(flow.currentAssignedConditionCode.value, '01');
});

test('paired activities count only the specified event and retain the assigned order until posttest ends', async () => {
  const assignments = [{ event_id: 'event-b', condition_code: '02' }, { event_id: 'event-a', condition_code: '04' }];
  const progress = [{ event_id: 'old-event', condition_key: eblKey, status: 'completed', posttest_stage: 'completed', session_id: 'old-session', updated_at: '2026-09-23T00:00:00Z' }];
  const pairedResponse = () => ({ ...response(progress), participant: { ...participant, metadata: { activity_assignments: assignments } } });
  const flow = setup({ fetchAdminParticipantPreview: async () => pairedResponse() });
  await flow.loadAdminParticipantPreview('admin-key', 't001');
  assert.deepEqual(flow.assignedActivities.value, assignments);
  assert.equal(flow.currentAssignedActivity.value.event_id, 'event-b');
  progress.push({ event_id: 'event-b', condition_key: eblKey, status: 'completed', posttest_stage: 'hat', session_id: 'current-session', updated_at: '2026-09-23T01:00:00Z' });
  await flow.loadProgressFromApi();
  assert.equal(flow.currentAssignedActivity.value.event_id, 'event-b');
  progress[1].posttest_stage = 'completed';
  await flow.loadProgressFromApi();
  assert.deepEqual(flow.currentAssignedActivity.value, assignments[1]);
});

test('paired preview rejects wrong event before using a cached session or calling initialization', async () => {
  let navigated = false;
  globalThis.navigateTo = async () => { navigated = true; };
  const progress = [{ event_id: 'wrong-event', condition_key: eblKey, status: 'task_started', session_id: 'stale-session', task_id: 'old-task', updated_at: '2026-09-23T00:00:00Z' }];
  const flow = setup({ fetchAdminParticipantPreview: async () => ({ ...response(progress), participant: { ...participant, metadata: { activity_assignments: [{ event_id: 'assigned-event', condition_code: '02' }] } } }) });
  await flow.loadAdminParticipantPreview('admin-key', 't001');
  await flow.startCondition({ id: 'wrong-event', canonical_name: 'Wrong event' }, { condition_key: eblKey }, { adminKey: 'admin-key', previewParticipantId: 't001' });
  assert.equal(navigated, false);
  assert.match(flow.initializeError.value, /指定歷史事件/);
});

test('explicitly empty or invalid activity assignments do not reopen legacy conditions', async () => {
  for (const assignments of [[], [{ event_id: 'event-a', condition_code: '99' }]]) {
    const flow = setup({ fetchAdminParticipantPreview: async () => ({ ...response(), participant: { ...participant, metadata: { activity_assignments: assignments } } }) });
    await flow.loadAdminParticipantPreview('admin-key', 't001');
    assert.deepEqual(flow.assignedConditionCodes.value, []);
    assert.equal(flow.currentAssignedActivity.value, null);
    assert.equal(flow.currentAssignedConditionCode.value, null);
  }
});

test('archived progress neither hides an active session nor resumes an archived conversation', async () => {
  const archived = { event_id: 'event-one', condition_key: eblKey, status: 'archived', session_id: 'archived-session', conversation_id: 'archived-chat', updated_at: '2026-09-23T02:00:00Z' };
  const active = { ...archived, status: 'task_started', session_id: 'active-session', conversation_id: null, updated_at: '2026-09-23T01:00:00Z' };
  const flow = setup({ fetchAdminParticipantPreview: async () => response([active, archived]) });
  await flow.loadAdminParticipantPreview('admin-key', 't001');
  assert.equal(flow.progressByEvent.value['event-one'][eblKey].sessionId, 'active-session');
  globalThis.participantPreviewTestApi.fetchAdminParticipantPreview = async () => response([archived]);
  await flow.loadProgressFromApi();
  assert.deepEqual(flow.progressByEvent.value, {});
  assert.equal(flow.currentAssignedConditionCode.value, '02');
});
