// useEventLibrary 管理首頁事件素材庫的讀取、重新整理與刪除。
// 首頁仍保留 modal/selection UI；這裡只處理資料狀態與 API 邊界。
import { ref } from 'vue';
import type { EventWithPersonas, ExperimentCondition } from '~/types';
import {
  deleteEventMaterial,
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

  const fetchEvents = async () => {
    loadingEvents.value = true;
    try {
      events.value = await requestEvents();
      listError.value = null;
    } catch (e) {
      console.error('Failed to fetch events:', e);
      listError.value = '讀取歷史事件失敗。';
    } finally {
      loadingEvents.value = false;
    }
  };

  const refreshEvents = async () => {
    isRefreshing.value = true;
    await fetchEvents();
    isRefreshing.value = false;
  };

  const deleteEvent = async (eventId: string) => {
    await deleteEventMaterial(eventId);
    await fetchEvents();
  };

  const findEvent = (eventId: string | null | undefined) => {
    if (!eventId) return null;
    return events.value.find((event) => event.id === eventId) || null;
  };

  const loadEventLibrary = async () => {
    await Promise.all([fetchConditions(), fetchEvents()]);
  };

  return {
    conditions,
    deleteEvent,
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
