export const ADMIN_KEY_STORAGE_KEY = 'histosphere_admin_key';
export const ADMIN_VIEW_STORAGE_KEY = 'histosphere-admin-view-mode';

const hasBrowserStorage = () => typeof window !== 'undefined';

export const getAdminSessionKey = () => {
  if (!hasBrowserStorage()) return '';
  return window.sessionStorage.getItem(ADMIN_KEY_STORAGE_KEY)?.trim() || '';
};

export const setAdminSessionKey = (adminKey: string) => {
  if (!hasBrowserStorage()) return;
  window.sessionStorage.setItem(ADMIN_KEY_STORAGE_KEY, adminKey.trim());
  window.localStorage.removeItem(ADMIN_KEY_STORAGE_KEY);
};

export const clearAdminSessionKey = () => {
  if (!hasBrowserStorage()) return;
  window.sessionStorage.removeItem(ADMIN_KEY_STORAGE_KEY);
  window.localStorage.removeItem(ADMIN_KEY_STORAGE_KEY);
};

export const getAdminViewMode = () => {
  if (!hasBrowserStorage()) return null;
  return window.sessionStorage.getItem(ADMIN_VIEW_STORAGE_KEY);
};

export const setAdminViewMode = (viewMode: string) => {
  if (!hasBrowserStorage()) return;
  window.sessionStorage.setItem(ADMIN_VIEW_STORAGE_KEY, viewMode);
  window.localStorage.removeItem(ADMIN_VIEW_STORAGE_KEY);
};

export const clearAdminSession = () => {
  if (!hasBrowserStorage()) return;
  clearAdminSessionKey();
  window.sessionStorage.removeItem(ADMIN_VIEW_STORAGE_KEY);
  window.localStorage.removeItem(ADMIN_VIEW_STORAGE_KEY);
  window.localStorage.removeItem('histosphere-admin-mode');
};
