const { shouldShowEventIntroduction } = await loadTsModule('utils/eventVisibility.ts');

test('Admin 管理視角可以查看事件介紹', () => {
  assert.equal(shouldShowEventIntroduction('admin'), true);
});

test('Learner 與 Admin testmode 不顯示事件介紹', () => {
  assert.equal(shouldShowEventIntroduction('learner'), false);
});
