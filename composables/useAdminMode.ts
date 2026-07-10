export type AdminViewMode = 'learner' | 'admin';

const isAdminMode = ref(false);
const adminViewMode = ref<AdminViewMode>('learner');

const adminViewStorageKey = 'histosphere-admin-view-mode';

export function useAdminMode() {
  const initAdminMode = () => {
    if (!import.meta.client) return;
    // 已驗證的 key 在同一登入狀態內維持 admin access；退出或登出時會一併清除。
    isAdminMode.value = Boolean(localStorage.getItem('histosphere_admin_key')?.trim());
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
