// useEventLibrary 管理首頁事件素材庫的讀取、重新整理與封存。
// 首頁仍保留 modal/selection UI；這裡只處理資料狀態與 API 邊界。
import { ref } from 'vue';
import type { EventWithPersonas, ExperimentCondition } from '~/types';
import {
  archiveAdminEvent,
  fetchAdminSnapshot,
  fetchConditions as requestConditions,
  fetchEvents as requestEvents,
} from '~/utils/histosphereApi';

export const useEventLibrary = () => {
  const events = ref<EventWithPersonas[]>([]);
  const conditions = ref<ExperimentCondition[]>([]);
  const loadingEvents = ref(false);
  const isRefreshing = ref(false);
  const listError = ref<string | null>(null);

  const fetchConditions = async () => {
    try {
      conditions.value = await requestConditions();
    } catch (e) {
      console.error('Failed to fetch conditions:', e);
      listError.value = '讀取實驗條件失敗。';
    }
  };

  const fetchEvents = async (adminKey?: string | null) => {
    loadingEvents.value = true;
    try {
      if (adminKey) {
        const snapshot = await fetchAdminSnapshot(adminKey);
        events.value = snapshot.events.filter((event) => !event.archived_at);
      } else {
        events.value = await requestEvents();
      }
      listError.value = null;
    } catch (e) {
      console.error('Failed to fetch events:', e);
      listError.value = '讀取歷史事件失敗。';
    } finally {
      loadingEvents.value = false;
    }
  };

  const refreshEvents = async (adminKey?: string | null) => {
    isRefreshing.value = true;
    await fetchEvents(adminKey);
    isRefreshing.value = false;
  };

  const archiveEvent = async (adminKey: string, eventId: string) => {
    await archiveAdminEvent(adminKey, eventId);
    await fetchEvents(adminKey);
  };

  const findEvent = (eventId: string | null | undefined) => {
    if (!eventId) return null;
    return events.value.find((event) => event.id === eventId) || null;
  };

  const loadEventLibrary = async (adminKey?: string | null) => {
    await Promise.all([fetchConditions(), fetchEvents(adminKey)]);
  };

  return {
    conditions,
    archiveEvent,
    events,
    fetchConditions,
    fetchEvents,
    findEvent,
    isRefreshing,
    listError,
    loadEventLibrary,
    loadingEvents,
    refreshEvents,
  };
};
