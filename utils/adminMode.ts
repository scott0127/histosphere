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
