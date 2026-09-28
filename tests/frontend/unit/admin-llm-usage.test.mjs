import assert from 'node:assert/strict';

const usage = await globalThis.loadTsModule('utils/adminLlmUsage.ts');

test('TWD estimate distinguishes zero, tiny, unknown and partial cost with editable rates', () => {
  assert.equal(usage.formatEstimatedTwd(0, 32), 'NT$0.00');
  assert.equal(usage.formatEstimatedTwd(0.5, 32), 'NT$16.00');
  assert.equal(usage.formatEstimatedTwd(0.5, 30), 'NT$15.00');
  assert.equal(usage.formatEstimatedTwd(0.000001, 32), '< NT$0.0001');
  for (const rate of ['', 0, -1, NaN, Infinity, 1001]) {
    assert.equal(usage.formatEstimatedTwd(0.5, rate), '未能估算');
  }
  assert.equal(usage.formatEstimatedTwd(null, 32), '未能估算');
  assert.match(usage.formatCallCost({ estimated_cost_usd: 0, attempt_count: 1 }, 32), /NT\$0.00/);
  assert.match(usage.formatCallCost({ estimated_known_cost_usd: 0.1, estimated_cost_usd: null, attempt_count: 2 }, 32), /僅已知費用/);
  assert.match(usage.formatCallCost({ estimated_cost_usd: 0.1, attempt_count: 2 }, 32), /僅已知費用/);
  assert.equal(usage.formatCallCost({}, 32), '費用未回報');
});

test('usage totals sum requests and known costs without filling missing coverage', () => {
  const row = { stage: 'review_answer', provider: 'test', model: 'test', requests: 2,
    token_reported_requests: 1, cost_reported_requests: 1, prompt_tokens: 10,
    completion_tokens: 5, total_tokens: 15, estimated_known_cost_usd: 0.001 };
  const total = usage.sumUsageRows([row, row]);
  assert.equal(total.requests, 4);
  assert.equal(total.cost_reported_requests, 2);
  assert.equal(total.total_tokens, 30);
  assert.equal(total.estimated_known_cost_usd, 0.002);
  assert.equal(usage.llmStageLabel('review_answer'), '答案審查');
  assert.match(usage.llmStageLabel('isolated_test'), /其他／測試/);
  assert.equal(usage.sumUsageRows([]).requests, 0);
});
