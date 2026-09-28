import {
  activityModeForAdminView,
  normalizeAdminViewMode,
  type AdminViewMode,
} from '~/utils/adminMode';
import {
  clearAdminSession,
  getAdminSessionKey,
  getAdminViewMode,
  getAdminPreviewParticipantId,
  setAdminPreviewParticipantId as persistPreviewParticipantId,
  setAdminViewMode as persistAdminViewMode,
} from '~/utils/adminSession';

const isAdminMode = ref(false);
const adminViewMode = ref<AdminViewMode>('admin_mode');
const previewParticipantId = ref<string | null>(null);

export function useAdminMode() {
  const initAdminMode = () => {
    if (!import.meta.client) return;
    isAdminMode.value = Boolean(getAdminSessionKey());
    const savedViewMode = getAdminViewMode();
    adminViewMode.value = normalizeAdminViewMode(savedViewMode);
    previewParticipantId.value = isAdminMode.value ? getAdminPreviewParticipantId() : null;
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
    previewParticipantId.value = null;
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

  const setPreviewParticipantId = (participantId: string | null) => {
    if (!isAdminMode.value) return;
    previewParticipantId.value = participantId?.trim() || null;
    persistPreviewParticipantId(previewParticipantId.value);
  };

  return {
    isAdminMode: readonly(isAdminMode),
    adminViewMode: readonly(adminViewMode),
    previewParticipantId: readonly(previewParticipantId),
    setPreviewParticipantId,
    activityMode,
    initAdminMode,
    enterAdminMode,
    exitAdminMode,
    setAdminViewMode,
  };
}
