export type AdminViewMode = 'admin_mode' | 'admin_testmode';

export const normalizeAdminViewMode = (value: string | null | undefined): AdminViewMode => {
  if (value === 'admin_mode' || value === 'admin') return 'admin_mode';
  if (value === 'admin_testmode' || value === 'learner') return 'admin_testmode';
  return 'admin_mode';
};

export const activityModeForAdminView = (mode: AdminViewMode): 'admin' | 'learner' => {
  return mode === 'admin_mode' ? 'admin' : 'learner';
};

export const shouldExitAdminModeForAuthTransition = (
  previousScope: string | null | undefined,
  nextScope: string | null | undefined,
) => {
  if (!previousScope || previousScope === 'guest') return false;
  return nextScope === 'guest' || previousScope !== nextScope;
};

// Admin test mode 需要可寫入 UUID 欄位的明確測試身分，但不能成為 learner 的預設身分。
export const adminTestUserUuid = (value: string) => {
  const seed = value.trim();
  if (!seed) throw new Error('Admin test user seed is required');

  let hash = 2166136261;
  for (const char of seed) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  const hex = Math.abs(hash).toString(16).padStart(8, '0');
  return `${hex}${hex}${hex}${hex}`.replace(
    /^(.{8})(.{4})(.{4})(.{4})(.{12}).*$/,
    '$1-$2-$3-$4-$5',
  );
};
