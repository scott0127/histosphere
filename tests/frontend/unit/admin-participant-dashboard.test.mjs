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
