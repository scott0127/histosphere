import assert from 'node:assert/strict';

const createMemoryStorage = () => {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
  };
};

globalThis.window = {
  localStorage: createMemoryStorage(),
  sessionStorage: createMemoryStorage(),
};

const adminSession = await globalThis.loadTsModule('utils/adminSession.ts');

test('admin key is stored only for the current browser tab', () => {
  window.localStorage.setItem('histosphere_admin_key', 'legacy-key');
  adminSession.setAdminSessionKey('tab-key');

  assert.equal(window.sessionStorage.getItem('histosphere_admin_key'), 'tab-key');
  assert.equal(window.localStorage.getItem('histosphere_admin_key'), null);
  assert.equal(adminSession.getAdminSessionKey(), 'tab-key');
});

test('exiting admin mode clears key, view mode, and legacy values', () => {
  adminSession.setAdminSessionKey('tab-key');
  adminSession.setAdminViewMode('admin_testmode');
  window.localStorage.setItem('histosphere-admin-mode', 'true');

  adminSession.clearAdminSession();

  assert.equal(adminSession.getAdminSessionKey(), '');
  assert.equal(adminSession.getAdminViewMode(), null);
  assert.equal(window.localStorage.getItem('histosphere-admin-mode'), null);
});
