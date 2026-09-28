import assert from 'node:assert/strict';

const { monitorCountdown } = await globalThis.loadTsModule('utils/monitorTiming.ts');
const start = '2026-09-28T02:00:00Z';
const at = seconds => Date.parse(start) + seconds * 1000;
const snapshot = () => ({ session: { status: 'initialized', created_at: start }, stage: 'task', messages: [] });

test('monitor task reference countdown survives reload and draft updates without altering the snapshot', () => {
  const data = snapshot();
  data.attempt = { status: 'in_progress', updated_at: start };
  assert.equal(monitorCountdown(data, at(60)).display, '04:00');
  data.attempt.updated_at = new Date(at(120)).toISOString();
  const reloaded = structuredClone(data);
  assert.equal(monitorCountdown(reloaded, at(120)).display, '03:00');
  assert.deepEqual(data, reloaded);
  assert.equal(monitorCountdown(data, at(600)).state, 'expired');
  assert.equal(monitorCountdown(data, at(600)).display, '00:00');
});

test('admin AI reference uses ten minutes while explicitly preserving the learner five-minute timer', () => {
  const data = snapshot();
  Object.assign(data.session, { status: 'conversation_started', timer_started_at: start, timer_ends_at: new Date(at(300)).toISOString() });
  const result = monitorCountdown(data, at(120));
  assert.equal(result.display, '08:00');
  assert.match(result.detail, /現行互動時限為 5 分鐘/);
  assert.equal(data.session.timer_ends_at, new Date(at(300)).toISOString());
  data.session.timer_started_at = null;
  assert.equal(monitorCountdown(data, at(120)).state, 'waiting');
});

test('posttest shares fifteen minutes across Engagement and HAT and waits for actual entry', () => {
  const data = snapshot();
  data.session.status = 'completed';
  assert.equal(monitorCountdown(data, at(60)).display, '尚未開始');
  data.posttest = { stage: 'engagement', started_at: start };
  assert.equal(monitorCountdown(data, at(60)).display, '14:00');
  data.posttest.stage = 'hat';
  data.posttest.updated_at = new Date(at(90)).toISOString();
  assert.equal(monitorCountdown(data, at(90)).display, '13:30');
  assert.match(monitorCountdown(data, at(90)).title, /HAT/);
  data.posttest.stage = 'completed';
  assert.equal(monitorCountdown(data, at(100)).state, 'complete');
});

test('human review has no budget and invalid or future timestamps do not render NaN or inflated time', () => {
  const data = snapshot();
  data.attempt = { status: 'awaiting_review' };
  assert.equal(monitorCountdown(data, at(30)).state, 'waiting');
  delete data.attempt;
  data.session.created_at = 'invalid';
  assert.equal(monitorCountdown(data, at(30)).state, 'unavailable');
  data.session.created_at = new Date(at(30)).toISOString();
  assert.equal(monitorCountdown(data, at(0)).display, '05:00');
  data.session.status = 'archived';
  assert.equal(monitorCountdown(data, at(0)).state, 'complete');
});
