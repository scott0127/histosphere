import {
  activityModeForAdminView,
  normalizeAdminViewMode,
  type AdminViewMode,
} from '~/utils/adminMode';
import {
  clearAdminSession,
  getAdminSessionKey,
  getAdminViewMode,
  setAdminViewMode as persistAdminViewMode,
} from '~/utils/adminSession';

const isAdminMode = ref(false);
const adminViewMode = ref<AdminViewMode>('admin_mode');

export function useAdminMode() {
  const initAdminMode = () => {
    if (!import.meta.client) return;
    isAdminMode.value = Boolean(getAdminSessionKey());
    const savedViewMode = getAdminViewMode();
    adminViewMode.value = normalizeAdminViewMode(savedViewMode);
  };

  const persistAdminMode = () => {
    if (!import.meta.client) return;
    persistAdminViewMode(adminViewMode.value);
  };

  const enterAdminMode = () => {
    isAdminMode.value = true;
    adminViewMode.value = 'admin_mode';
    persistAdminMode();
  };

  const exitAdminMode = () => {
    isAdminMode.value = false;
    adminViewMode.value = 'admin_mode';
    clearAdminSession();
  };

  const setAdminViewMode = (mode: AdminViewMode) => {
    if (!isAdminMode.value) return;
    adminViewMode.value = mode;
    persistAdminMode();
  };

  const activityMode = computed(() => {
    return isAdminMode.value
      ? activityModeForAdminView(adminViewMode.value)
      : 'learner';
  });

  return {
    isAdminMode: readonly(isAdminMode),
    adminViewMode: readonly(adminViewMode),
    activityMode,
    initAdminMode,
    enterAdminMode,
    exitAdminMode,
    setAdminViewMode,
  };
}
