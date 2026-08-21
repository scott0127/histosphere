import assert from 'node:assert/strict';
import { sampleCondition } from '../fixtures/histosphereFixtures.mjs';

const conditions = await globalThis.loadTsModule('utils/experimentConditions.ts');
const dashboard = await globalThis.loadTsModule('utils/adminParticipantDashboard.ts');

const matrix = [
  {
    code: '01',
    key: 'no_ebl_no_roleplay',
    label: 'Baseline',
    ebl: false,
    roleplay: false,
    agentMode: 'generic',
    responsePolicy: 'direct',
  },
  {
    code: '02',
    key: 'ebl_no_roleplay',
    label: 'AI Error-based learning',
    ebl: true,
    roleplay: false,
    agentMode: 'generic',
    responsePolicy: 'scaffold',
  },
  {
    code: '03',
    key: 'no_ebl_roleplay',
    label: 'AI Role-play learning',
    ebl: false,
    roleplay: true,
    agentMode: 'persona',
    responsePolicy: 'direct',
  },
  {
    code: '04',
    key: 'ebl_roleplay',
    label: 'EBL AI Role-play',
    ebl: true,
    roleplay: true,
    agentMode: 'persona',
    responsePolicy: 'scaffold',
  },
];

test('condition codes map to the fixed 2x2 experiment matrix', () => {
  assert.deepEqual(conditions.experimentConditionCodes, matrix.map((item) => item.code));

  for (const item of matrix) {
    assert.equal(conditions.experimentConditionCodeByKey[item.key], item.code);
    assert.equal(conditions.experimentConditionLabels[item.code], item.label);
    assert.equal(conditions.experimentConditionCode(item.key), item.code);
    assert.equal(dashboard.conditionDisplayLabel(item.code), `${item.code} ${item.label}`);
  }
});

test('condition sorting is canonical and does not trust backend input order', () => {
  const unsorted = [...matrix].reverse().map((item) => ({
    ...sampleCondition,
    id: `condition-${item.code}`,
    condition_key: item.key,
    label: item.label,
    ebl_enabled: item.ebl,
    roleplay_enabled: item.roleplay,
    agent_mode: item.agentMode,
    response_policy: item.responsePolicy,
  }));

  const sorted = conditions.sortExperimentConditions(unsorted);
  assert.deepEqual(sorted.map((condition) => condition.condition_key), matrix.map((item) => item.key));
  assert.deepEqual(sorted.map((condition) => conditions.experimentConditionCode(condition)), ['01', '02', '03', '04']);
});

test('participant dashboard preserves assigned order and maps session stages by condition key', () => {
  const snapshot = {
    events: [],
    conditions: [],
    participants: [
      {
        id: 'participant-1',
        code: 'P001',
        auth_user_id: 'auth-1',
        condition_list: ['04', '02', '02', 'invalid'],
        status: 'active',
        metadata: {},
        created_at: '2026-07-11T00:00:00Z',
        updated_at: '2026-07-11T00:00:00Z',
      },
    ],
    sessions: [
      {
        id: 'session-02',
        condition_key_snapshot: 'ebl_no_roleplay',
        user_id: 'auth-1',
        event_id: 'event-1',
        status: 'conversation_started',
        created_at: '2026-07-11T00:00:00Z',
        updated_at: '2026-07-11T01:00:00Z',
      },
      {
        id: 'session-04',
        condition_key_snapshot: 'ebl_roleplay',
        user_id: 'auth-1',
        event_id: 'event-1',
        status: 'task_submitted',
        created_at: '2026-07-11T00:00:00Z',
        updated_at: '2026-07-11T00:30:00Z',
      },
    ],
    research_logs: [],
  };

  const [row] = dashboard.buildParticipantDashboardRows(snapshot, [{ id: 'auth-1' }]);
  assert.deepEqual(row.assignedConditions, [
    { code: '04', label: 'EBL AI Role-play' },
    { code: '02', label: 'AI Error-based learning' },
  ]);
  assert.deepEqual(row.conditionProgress.map((item) => [item.code, item.stage]), [
    ['04', 'task'],
    ['02', 'chat'],
  ]);
  assert.equal(row.currentStage, 'chat');
  assert.equal(row.latestActiveSession.id, 'session-02');
});
