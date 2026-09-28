import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { effectScope, nextTick, reactive } from 'vue';
import { compileScript, compileTemplate, parse } from 'vue/compiler-sfc';
import ts from 'typescript';
import { sampleEvent } from '../fixtures/histosphereFixtures.mjs';

const dashboard = await globalThis.loadTsModule('utils/adminParticipantDashboard.ts');
const file = 'components/admin/ParticipantDashboard.vue';
const { descriptor, errors } = parse(await readFile(file, 'utf8'), { filename: file });
assert.deepEqual(errors, []);
const script = compileScript(descriptor, { id: file });
const template = compileTemplate({ id: file, source: descriptor.template.content, filename: file, compilerOptions: { bindingMetadata: script.bindings } });
assert.deepEqual(template.errors, []);
globalThis.adminParticipantEditorTestUtilities = dashboard;
const utilityNames = ['conditionDisplayLabel', 'conditionName', 'buildParticipantActivityDraft', 'participantActivityAssignmentInput', 'validateParticipantActivityDraft', 'filterParticipantDashboardRows', 'participantConditionLabels', 'participantStageLabels'];
const utilityUrl = `data:text/javascript;base64,${Buffer.from(utilityNames.map((name) => `export const ${name} = globalThis.adminParticipantEditorTestUtilities.${name};`).join('\n')).toString('base64')}`;
const modalUrl = `data:text/javascript;base64,${Buffer.from('export default {};').toString('base64')}`;
const scrollLockUrl = `data:text/javascript;base64,${Buffer.from('export const useBodyScrollLock = () => {};').toString('base64')}`;
const compiled = ts.transpileModule(script.content, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText
  .replace(/from (['"])vue\1/g, `from '${import.meta.resolve('vue')}'`)
  .replace("from '~/utils/adminParticipantDashboard'", `from '${utilityUrl}'`)
  .replace("from '~/composables/useBodyScrollLock'", `from '${scrollLockUrl}'`)
  .replace("from '~/components/modals/ConfirmActionModal.vue'", `from '${modalUrl}'`);
const component = (await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)).default;

const setup = () => {
  const props = reactive({ rows: [], events: [sampleEvent, { ...sampleEvent, id: 'second-event' }], authUsers: [], creatingParticipant: false, changingParticipantStatusId: null, savingParticipantId: null, updatingTimerSessionId: null, restartingSessionId: null, operationError: null });
  const calls = [];
  const scope = effectScope();
  const state = scope.run(() => component.setup(props, { emit: (...args) => calls.push(args), expose: () => {} }));
  return { props, calls, state, stop: () => scope.stop() };
};

test('assignment editor blocks incomplete legacy rows and keeps event/condition pairs together when moved', () => {
  const { state, calls, stop } = setup();
  try {
    state.openEditor({ participant: { id: 'p-one', condition_list: ['02', '04'], metadata: {} } });
    state.saveEditor();
    assert.equal(calls.length, 0);
    state.draftActivities.value[0].event_id = sampleEvent.id;
    state.draftActivities.value[1].event_id = 'second-event';
    state.moveActivity(state.draftActivities.value, 1, -1);
    state.saveEditor();
    assert.deepEqual(calls[0][2].activity_assignments, [
      { event_id: 'second-event', condition_code: '04' },
      { event_id: sampleEvent.id, condition_code: '02' },
    ]);
    assert.deepEqual(calls[0][2].condition_list, ['04', '02']);
    assert.equal(state.editingRow.value.participant.id, 'p-one');
  } finally { stop(); }
});

test('assignment save failure keeps draft open and only a successful retry closes the editor', async () => {
  const { state, props, stop } = setup();
  try {
    state.openEditor({ participant: { id: 'p-one', condition_list: [], metadata: {} } });
    state.addActivity(state.draftActivities.value);
    state.draftActivities.value[0].event_id = sampleEvent.id;
    state.saveEditor();
    props.savingParticipantId = 'p-one';
    await nextTick();
    props.operationError = '已有進行中活動，無法重新分配。';
    props.savingParticipantId = null;
    await nextTick();
    assert.equal(state.editingRow.value.participant.id, 'p-one');
    assert.equal(state.draftActivities.value[0].event_id, sampleEvent.id);
    props.operationError = null;
    state.saveEditor();
    props.savingParticipantId = 'p-one';
    await nextTick();
    props.savingParticipantId = null;
    await nextTick();
    assert.equal(state.editingRow.value, null);
  } finally { stop(); }
});

test('selecting an activity isolates its records per participant and keeps archived entries out of the latest active label', () => {
  const { state, stop } = setup();
  const activities = [
    { key: 'first-event-04', sessionHistory: [{ session: { id: 'archived', status: 'archived' } }, { session: { id: 'current', status: 'completed' } }] },
    { key: 'second-event-02', sessionHistory: [] },
  ];
  const first = { participant: { id: 'p-one' }, activities };
  const second = { participant: { id: 'p-two' }, activities };
  try {
    assert.equal(state.selectedActivity(first), undefined);
    state.toggleActivity(first, activities[0].key);
    assert.equal(state.selectedActivity(first), activities[0]);
    assert.equal(state.latestActivitySessionId(first), 'current');
    assert.equal(state.selectedActivity(second), undefined);
    state.toggleActivity(first, activities[1].key);
    assert.equal(state.selectedActivity(first), activities[1]);
    assert.equal(state.latestActivitySessionId(first), undefined);
    state.toggleActivity(first, activities[1].key);
    assert.equal(state.selectedActivity(first), undefined);
  } finally { stop(); }
});

test('participant summary distinguishes one completed activity from the next unstarted activity', () => {
  const { state, stop } = setup();
  const [row] = dashboard.buildParticipantDashboardRows({
    events: [sampleEvent, { ...sampleEvent, id: 'second-event' }], conditions: [], research_logs: [],
    participants: [{ id: 'partial', code: 'PARTIAL', condition_list: ['02', '04'], metadata: { activity_assignments: [
      { event_id: sampleEvent.id, condition_code: '02' },
      { event_id: 'second-event', condition_code: '04' },
    ] } }],
    sessions: [{ id: 'completed-first', participant_id: 'partial', event_id: sampleEvent.id, condition_key_snapshot: 'ebl_no_roleplay', status: 'completed', updated_at: '2026-09-28T00:00:00Z' }],
  }, []);
  try {
    assert.equal(state.activityProgressLabel(row), '已完成 1 / 2 個分派活動');
    state.toggleActivity(row, row.activities[0].key);
    assert.equal(state.activityProgressLabel(row), '所選活動進度');
    assert.equal(state.selectedActivity(row).stage, 'completed');
    state.toggleActivity(row, row.activities[1].key);
    assert.equal(state.selectedActivity(row).stage, 'not_started');
    state.toggleActivity(row, row.activities[1].key);
    assert.equal(state.activityProgressLabel(row), '已完成 1 / 2 個分派活動');
  } finally { stop(); }
});
