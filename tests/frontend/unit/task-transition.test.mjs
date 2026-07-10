const taskTransition = await globalThis.loadTsModule('utils/taskTransition.ts');

test('task transition formats exact years, ranges, and event fallbacks', () => {
  assert.equal(taskTransition.formatTaskTransitionEra('霧社事件', 1930, 1930), '1930 年');
  assert.equal(taskTransition.formatTaskTransitionEra('黑船事件到明治維新', 1853, 1868), '1853–1868 年');
  assert.equal(taskTransition.formatTaskTransitionEra('年代未定事件', null, null), '「年代未定事件」');
});

test('task transition explains long LLM waits instead of appearing frozen', () => {
  assert.equal(taskTransition.taskTransitionPhase(0).label, '正在保存你的作答');
  assert.equal(taskTransition.taskTransitionPhase(6).label, '正在分析作答與歷史脈絡');
  assert.equal(taskTransition.taskTransitionPhase(18).label, '正在準備歷史對話');
  assert.equal(taskTransition.taskTransitionPhase(45).label, '模型仍在推論');
  assert.match(taskTransition.taskTransitionPhase(45).detail, /備援來源/);
});
