const adminMode = await globalThis.loadTsModule('utils/adminMode.ts');

test('admin view mode migrates legacy values to explicit modes', () => {
  assert.equal(adminMode.normalizeAdminViewMode('admin'), 'admin_mode');
  assert.equal(adminMode.normalizeAdminViewMode('learner'), 'admin_testmode');
  assert.equal(adminMode.normalizeAdminViewMode('admin_mode'), 'admin_mode');
  assert.equal(adminMode.normalizeAdminViewMode('admin_testmode'), 'admin_testmode');
  assert.equal(adminMode.normalizeAdminViewMode(null), 'admin_mode');
});

test('admin view mode maps management and participant previews independently', () => {
  assert.equal(adminMode.activityModeForAdminView('admin_mode'), 'admin');
  assert.equal(adminMode.activityModeForAdminView('admin_testmode'), 'learner');
});

test('admin access survives initial auth restore but exits on account changes', () => {
  assert.equal(adminMode.shouldExitAdminModeForAuthTransition('guest', 'auth-user-a'), false);
  assert.equal(adminMode.shouldExitAdminModeForAuthTransition('auth-user-a', 'auth-user-a'), false);
  assert.equal(adminMode.shouldExitAdminModeForAuthTransition('auth-user-a', 'auth-user-b'), true);
  assert.equal(adminMode.shouldExitAdminModeForAuthTransition('auth-user-a', 'guest'), true);
});

test('admin test mode uses an explicit deterministic UUID', () => {
  const first = adminMode.adminTestUserUuid('admin-test:local');
  const second = adminMode.adminTestUserUuid('admin-test:local');

  assert.equal(first, second);
  assert.match(first, /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
  assert.throws(() => adminMode.adminTestUserUuid(''), /seed is required/);
});
