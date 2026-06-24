export type AdminViewMode = 'learner' | 'admin';

const isAdminMode = ref(false);
const adminViewMode = ref<AdminViewMode>('learner');

const adminViewStorageKey = 'histosphere-admin-view-mode';

export function useAdminMode() {
  const initAdminMode = () => {
    isAdminMode.value = false;
    if (!import.meta.client) return;
    const savedViewMode = localStorage.getItem(adminViewStorageKey);
    adminViewMode.value = savedViewMode === 'admin' ? 'admin' : 'learner';
  };

  const persistAdminMode = () => {
    if (!import.meta.client) return;
    localStorage.setItem(adminViewStorageKey, adminViewMode.value);
  };

  const enterAdminMode = () => {
    isAdminMode.value = true;
    adminViewMode.value = 'admin';
    persistAdminMode();
  };

  const exitAdminMode = () => {
    isAdminMode.value = false;
    adminViewMode.value = 'learner';
    persistAdminMode();
  };

  const setAdminViewMode = (mode: AdminViewMode) => {
    if (!isAdminMode.value) return;
    adminViewMode.value = mode;
    persistAdminMode();
  };

  const activityMode = computed(() => {
    return isAdminMode.value && adminViewMode.value === 'admin' ? 'admin' : 'learner';
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
