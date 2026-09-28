import assert from 'node:assert/strict';
import { sampleEvent } from '../fixtures/histosphereFixtures.mjs';

const dashboard = await globalThis.loadTsModule('utils/adminParticipantDashboard.ts');

const participant = {
  id: 'participant-1',
  code: 'P001',
  auth_user_id: 'auth-1',
  display_name: '受測者 01',
  cohort: 'test',
  condition_list: ['01', '04'],
  status: 'active',
  notes: null,
  metadata: {},
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const session = (overrides = {}) => ({
  id: 'session-current',
  condition_id: 'condition-1',
  condition_key_snapshot: 'ebl_roleplay',
  user_id: 'auth-1',
  event_id: sampleEvent.id,
  status: 'initialized',
  timer_started_at: null,
  timer_ends_at: null,
  completed_at: null,
  completion_reason: null,
  created_at: '2026-01-02T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
  ...overrides,
});

test('participant dashboard exposes only non-archived sessions for admin restart', () => {
  const rows = dashboard.buildParticipantDashboardRows({
    events: [sampleEvent],
    conditions: [],
    participants: [participant],
    sessions: [
      session(),
      session({
        id: 'session-archived',
        status: 'archived',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }),
    ],
    research_logs: [],
  }, [{
    id: 'auth-1',
    email: 'participant@example.test',
    bound_participant_id: participant.id,
    bound_participant_code: participant.code,
  }]);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].currentSessions.length, 1);
  assert.equal(rows[0].currentSessions[0].session.id, 'session-current');
  assert.equal(rows[0].currentSessions[0].eventName, '法國大革命');
  assert.equal(rows[0].currentSessions[0].conditionCode, '04');
  assert.equal(rows[0].sessionHistory.length, 2);
  assert.deepEqual(
    rows[0].sessionHistory.map((item) => item.session.id),
    ['session-current', 'session-archived'],
  );
});

test('participant dashboard marks a completed non-archived session as completed', () => {
  const rows = dashboard.buildParticipantDashboardRows({
    events: [sampleEvent],
    conditions: [],
    participants: [{ ...participant, condition_list: ['04'] }],
    sessions: [session({ status: 'completed' })],
    research_logs: [],
  }, []);

  assert.equal(rows[0].currentStage, 'completed');
  assert.equal(rows[0].currentSessions[0].session.status, 'completed');
});

test('participant dashboard preserves the admin-defined condition order', () => {
  const rows = dashboard.buildParticipantDashboardRows({
    events: [sampleEvent],
    conditions: [],
    participants: [{ ...participant, condition_list: ['04', '01', '04'] }],
    sessions: [],
    research_logs: [],
  }, []);

  assert.deepEqual(
    rows[0].assignedConditions.map((condition) => condition.code),
    ['04', '01'],
  );
});

test('participant dashboard hides archived participants until the admin requests them', () => {
  const activeRow = {
    participant,
  };
  const archivedRow = {
    participant: { ...participant, id: 'participant-2', code: 'P002', status: 'archived' },
  };

  assert.deepEqual(
    dashboard.filterParticipantDashboardRows([activeRow, archivedRow], false),
    [activeRow],
  );
  assert.deepEqual(
    dashboard.filterParticipantDashboardRows([activeRow, archivedRow], true),
    [activeRow, archivedRow],
  );
});

test('participant search finds codes, assigned events and historical session IDs while respecting archive visibility', () => {
  const rows = dashboard.buildParticipantDashboardRows({
    events: [sampleEvent, { ...sampleEvent, id: 'wushe', canonical_name: '霧社事件' }],
    conditions: [],
    participants: [
      { ...participant, condition_list: ['04'], metadata: { activity_assignments: [{ event_id: 'wushe', condition_code: '04' }] } },
      { ...participant, id: 'participant-2', code: 'P002', auth_user_id: 'auth-2', status: 'archived' },
    ],
    sessions: [
      session({ id: 'OLD-FRENCH-SESSION', status: 'archived' }),
      session({ id: 'archived-participant-session', user_id: 'auth-2' }),
    ],
    research_logs: [],
  }, []);
  const before = structuredClone(rows);
  assert.deepEqual(dashboard.filterParticipantDashboardRows(rows, false, '  p001  ').map((row) => row.participant.code), ['P001']);
  assert.deepEqual(dashboard.filterParticipantDashboardRows(rows, false, '霧社').map((row) => row.participant.code), ['P001']);
  assert.deepEqual(dashboard.filterParticipantDashboardRows(rows, false, '法國').map((row) => row.participant.code), ['P001']);
  assert.deepEqual(dashboard.filterParticipantDashboardRows(rows, false, 'old-french-session').map((row) => row.participant.code), ['P001']);
  assert.equal(dashboard.filterParticipantDashboardRows(rows, false, 'archived-participant-session').length, 0);
  assert.deepEqual(dashboard.filterParticipantDashboardRows(rows, true, 'archived-participant-session').map((row) => row.participant.code), ['P002']);
  assert.equal(dashboard.filterParticipantDashboardRows(rows, true, 'no matching record').length, 0);
  assert.equal(dashboard.filterParticipantDashboardRows(rows, true, '   ').length, 2);
  assert.deepEqual(rows, before);
});

test('activity assignment editor preserves paired order and seeds legacy conditions without guessing events', () => {
  assert.deepEqual(dashboard.buildParticipantActivityDraft({ ...participant, condition_list: ['02', '04'] }), [
    { event_id: '', condition_code: '02' },
    { event_id: '', condition_code: '04' },
  ]);
  const configured = {
    ...participant,
    condition_list: ['04', '02'],
    metadata: { keep: 'research-notes', activity_assignments: [
      { event_id: 'event-2', condition_code: '04' },
      { event_id: sampleEvent.id, condition_code: '02' },
    ] },
  };
  const before = structuredClone(configured);
  const draft = dashboard.buildParticipantActivityDraft(configured);
  const input = dashboard.participantActivityAssignmentInput(draft, [sampleEvent, { ...sampleEvent, id: 'event-2' }]);
  assert.deepEqual(input.condition_list, ['04', '02']);
  assert.deepEqual(input.activity_assignments, configured.metadata.activity_assignments);
  assert.equal('metadata' in input, false);
  draft[0].event_id = 'changed-locally';
  assert.deepEqual(configured, before);
});

test('activity assignment validation rejects missing, duplicate and unavailable choices but allows unassigned participants', () => {
  const events = [sampleEvent, { ...sampleEvent, id: 'event-2' }, { ...sampleEvent, id: 'archived', archived_at: '2026-01-01' }];
  const valid = [{ event_id: sampleEvent.id, condition_code: '02' }, { event_id: 'event-2', condition_code: '04' }];
  assert.equal(dashboard.validateParticipantActivityDraft(valid, events), null);
  assert.deepEqual(dashboard.participantActivityAssignmentInput([], events), { activity_assignments: [], condition_list: [] });
  assert.match(dashboard.validateParticipantActivityDraft([{ event_id: '', condition_code: '02' }], events), /第 1.*歷史事件/);
  assert.match(dashboard.validateParticipantActivityDraft([{ event_id: sampleEvent.id, condition_code: '' }], events), /模式/);
  assert.match(dashboard.validateParticipantActivityDraft([valid[0], { ...valid[1], condition_code: '02' }], events), /模式只能/);
  assert.match(dashboard.validateParticipantActivityDraft([valid[0], { ...valid[1], event_id: sampleEvent.id }], events), /歷史事件只能/);
  assert.match(dashboard.validateParticipantActivityDraft([{ event_id: 'archived', condition_code: '02' }], events), /封存/);
  assert.match(dashboard.validateParticipantActivityDraft([{ event_id: 'unknown', condition_code: '02' }], events), /不存在/);
  assert.throws(() => dashboard.participantActivityAssignmentInput([{ event_id: '', condition_code: '02' }], events), /歷史事件/);
});

test('dashboard assignment chips name exact events and progress ignores old event, archived and admin test sessions', () => {
  const currentEvent = { ...sampleEvent, id: 'new-event', canonical_name: '霧社事件' };
  const [row] = dashboard.buildParticipantDashboardRows({
    events: [sampleEvent, currentEvent],
    conditions: [],
    participants: [{ ...participant, condition_list: ['04'], metadata: {
      activity_assignments: [{ event_id: currentEvent.id, condition_code: '04' }],
    } }],
    sessions: [
      session({ id: 'old-event', status: 'completed', updated_at: '2026-01-05T00:00:00Z' }),
      session({ id: 'archived', event_id: currentEvent.id, status: 'archived', updated_at: '2026-01-06T00:00:00Z' }),
      session({ id: 'test', event_id: currentEvent.id, is_admin_test: true, status: 'completed', updated_at: '2026-01-07T00:00:00Z' }),
      session({ id: 'current', event_id: currentEvent.id, status: 'initialized', updated_at: '2026-01-02T00:00:00Z' }),
    ],
    research_logs: [],
  }, []);
  assert.equal(row.assignedConditions[0].eventName, '霧社事件');
  assert.equal(row.assignedConditions[0].eventId, currentEvent.id);
  assert.equal(row.conditionProgress[0].sessionId, 'current');
  assert.equal(row.currentStage, 'task');
  assert.equal(row.sessionHistory.some((item) => item.session.id === 'test'), false);
});

test('activity records separate exact event and mode pairs, preserve archived history and expose unstarted assignments', () => {
  const [row] = dashboard.buildParticipantDashboardRows({
    events: [sampleEvent, { ...sampleEvent, id: 'second-event', canonical_name: '霧社事件' }],
    conditions: [],
    participants: [{ ...participant, condition_list: ['04', '02'], metadata: { activity_assignments: [
      { event_id: sampleEvent.id, condition_code: '04' },
      { event_id: 'second-event', condition_code: '02' },
    ] } }],
    sessions: [
      session({ id: 'active-first', status: 'conversation_started' }),
      session({ id: 'archived-first', status: 'archived', updated_at: '2026-01-03T00:00:00Z' }),
      session({ id: 'other-event', event_id: 'second-event' }),
      session({ id: 'other-mode', condition_key_snapshot: 'no_ebl_no_roleplay' }),
    ],
    research_logs: [],
  }, []);
  assert.equal(row.activities.length, 4);
  const [first, unstarted, pastEvent, pastMode] = row.activities;
  assert.equal(first.eventId, sampleEvent.id);
  assert.equal(first.code, '04');
  assert.equal(first.stage, 'chat');
  assert.deepEqual(first.sessionHistory.map((item) => item.session.id), ['active-first', 'archived-first']);
  assert.equal(unstarted.isAssigned, true);
  assert.equal(unstarted.eventId, 'second-event');
  assert.equal(unstarted.code, '02');
  assert.equal(unstarted.stage, 'not_started');
  assert.deepEqual(unstarted.sessionHistory, []);
  assert.equal(pastEvent.isAssigned, false);
  assert.deepEqual(pastEvent.sessionHistory.map((item) => item.session.id), ['other-event']);
  assert.equal(pastMode.isAssigned, false);
  assert.equal(pastMode.code, '01');
  assert.deepEqual(pastMode.sessionHistory.map((item) => item.session.id), ['other-mode']);
  assert.equal(new Set(row.activities.map((activity) => activity.key)).size, 4);
});

test('stored participant identity survives account rebinding and auth removal without leaking another participant or admin tests', () => {
  const [original, rebound, unbound] = dashboard.buildParticipantDashboardRows({
    events: [sampleEvent], conditions: [], research_logs: [],
    participants: [
      { ...participant, auth_user_id: 'new-auth', condition_list: ['04'] },
      { ...participant, id: 'participant-2', code: 'P002', auth_user_id: 'auth-1', condition_list: ['04'] },
      { ...participant, id: 'participant-3', code: 'P003', auth_user_id: null, condition_list: ['04'], status: 'archived' },
    ],
    sessions: [
      session({ id: 'stored-original', participant_id: participant.id, status: 'completed' }),
      session({ id: 'legacy-rebound', participant_id: null }),
      session({ id: 'unbound-history', participant_id: 'participant-3', user_id: null, status: 'archived' }),
      session({ id: 'unbound-current', participant_id: 'participant-3', user_id: null, status: 'completed' }),
      session({ id: 'admin-test', participant_id: participant.id, is_admin_test: true }),
      session({ id: 'unrecognized-owner', participant_id: 'deleted-participant' }),
    ],
  }, []);
  assert.deepEqual(original.sessionHistory.map((item) => item.session.id), ['stored-original']);
  assert.equal(original.currentStage, 'completed');
  assert.deepEqual(rebound.sessionHistory.map((item) => item.session.id), ['legacy-rebound']);
  assert.deepEqual(unbound.sessionHistory.map((item) => item.session.id), ['unbound-history', 'unbound-current']);
  assert.deepEqual(unbound.currentSessions.map((item) => item.session.id), ['unbound-current']);
  assert.equal(unbound.currentStage, 'completed');
  assert.equal(unbound.isBound, false);
  assert.equal(unbound.updatedAt, '2026-01-02T00:00:00Z');
});
