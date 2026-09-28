import assert from 'node:assert/strict';

const metrics = await globalThis.loadTsModule('utils/adminConversationMetrics.ts');

test('conversation metrics distinguish missing values from zero and preserve fractional time', () => {
  assert.equal(metrics.metricNumber(null), '未記錄');
  assert.equal(metrics.metricNumber(0), '0');
  assert.equal(metrics.metricNumber(1234.567), '1,234.6');
  assert.equal(metrics.metricDuration(undefined), '未記錄');
  assert.equal(metrics.metricDuration(-1), '未記錄');
  assert.equal(metrics.metricDuration(0), '0 秒');
  assert.equal(metrics.metricDuration(0.001), '< 0.1 秒');
  assert.equal(metrics.metricDuration(12.34), '12.3 秒');
  assert.equal(metrics.metricDuration(59.99), '1 分');
  assert.equal(metrics.metricDuration(61.5), '1 分 1.5 秒');
  assert.equal(metrics.metricDuration(3601), '1 小時 1 秒');
  assert.equal(metrics.metricDate('invalid date'), '未記錄');
});

test('question and round status labels never treat feedback-only or missing replies as corrected', () => {
  assert.equal(metrics.questionOutcomeLabel('feedback_completed'), '已提供回饋');
  assert.equal(metrics.questionOutcomeLabel('corrected'), '修正成功');
  assert.equal(metrics.questionOutcomeLabel('unresolved'), '未修正成功');
  assert.equal(metrics.roundStatusLabel('pending'), '尚未回覆');
  assert.equal(metrics.roundStatusLabel('failed'), '回覆失敗');
});
