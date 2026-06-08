<template>
  <div class="min-h-screen bg-slate-50 font-sans text-slate-950">
    <header class="border-b border-slate-200 bg-white/90 backdrop-blur">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
        <NuxtLink to="/" class="flex items-center gap-3 font-bold">
          <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-950 text-white">
            <Icon name="mdi:history" class="h-5 w-5" />
          </span>
          <span>Histosphere</span>
        </NuxtLink>
        <nav class="flex items-center gap-2 text-sm">
          <NuxtLink class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100" to="/admin">
            Admin
          </NuxtLink>
          <NuxtLink class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100" to="/tutorial">
            Tutorial
          </NuxtLink>
        </nav>
      </div>
    </header>

    <main class="mx-auto grid max-w-6xl gap-6 px-5 py-8 lg:grid-cols-[minmax(0,1fr)_420px]">
      <section class="space-y-6">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-slate-950 md:text-4xl">
            建立 EBL × AI historical role-play 學習流程
          </h1>
          <p class="mt-3 max-w-2xl text-base leading-7 text-slate-600">
            輸入歷史事件後，系統會建立事件資料、可編輯 task 與 1-3 位相關歷史人物。學生完成 task 後才會進入對話。
          </p>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 class="text-sm font-bold uppercase tracking-wide text-slate-500">Experiment Condition</h2>
              <p class="mt-1 text-sm text-slate-600">第一版先手動選擇，後續可改為 admin 指派。</p>
            </div>
            <button
              class="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:border-teal-500 hover:text-teal-700"
              @click="fetchConditions"
            >
              <Icon name="mdi:refresh" class="h-4 w-4" />
              更新
            </button>
          </div>

          <div class="grid gap-3 md:grid-cols-2">
            <button
              v-for="condition in conditions"
              :key="condition.id"
              type="button"
              :class="[
                'rounded-lg border p-4 text-left transition',
                selectedConditionKey === condition.condition_key
                  ? 'border-teal-500 bg-teal-50 ring-4 ring-teal-100'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              ]"
              @click="selectedConditionKey = condition.condition_key"
            >
              <div class="flex items-center justify-between gap-3">
                <span class="text-sm font-bold text-slate-950">{{ compactConditionLabel(condition) }}</span>
                <Icon
                  :name="selectedConditionKey === condition.condition_key ? 'mdi:check-circle' : 'mdi:circle-outline'"
                  class="h-5 w-5 text-teal-600"
                />
              </div>
              <p class="mt-2 text-xs leading-5 text-slate-600">{{ condition.description }}</p>
            </button>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <PersonaInputForm :is-loading="isLoading" :error="error" @event-submit="handleEventSubmit" />
        </div>
      </section>

      <aside class="space-y-4">
        <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex items-center justify-between gap-3">
            <div>
              <h2 class="font-bold text-slate-950">已建立事件</h2>
              <p class="text-sm text-slate-500">可用目前選擇的 condition 重新開一輪 session。</p>
            </div>
            <button
              class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:border-teal-500 hover:text-teal-700"
              @click="refreshEvents"
            >
              <Icon name="mdi:refresh" class="h-5 w-5" :class="{ 'animate-spin': isRefreshing }" />
            </button>
          </div>
        </div>

        <div v-if="loadingEvents" class="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-500">
          <Icon name="mdi:loading" class="mx-auto h-6 w-6 animate-spin" />
        </div>
        <EventListClassic
          v-else-if="events.length > 0"
          :events="events"
          @enter-story="handleEnterStory"
          @delete-event="handleDeleteEvent"
        />
        <div v-else class="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
          尚未建立歷史事件
        </div>
      </aside>
    </main>

    <DeleteConfirmationModal
      :show="showDeleteConfirmDialog"
      @confirm="confirmDelete"
      @cancel="showDeleteConfirmDialog = false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';
import type { ConditionKey, EventInitializeResponse, EventWithPersonas, ExperimentCondition } from '~/types';
import EventListClassic from '~/components/EventListClassic.vue';
import DeleteConfirmationModal from '~/components/modals/DeleteConfirmationModal.vue';

definePageMeta({
  layout: false,
  name: 'event-selection',
});

const isLoading = ref(false);
const error = ref<string | null>(null);
const showDeleteConfirmDialog = ref(false);
const pendingDeleteEventId = ref<string | null>(null);
const events = ref<EventWithPersonas[]>([]);
const conditions = ref<ExperimentCondition[]>([]);
const selectedConditionKey = ref<ConditionKey>('ebl_roleplay');
const loadingEvents = ref(false);
const isRefreshing = ref(false);

const currentCondition = computed(() =>
  conditions.value.find((condition) => condition.condition_key === selectedConditionKey.value),
);

onMounted(async () => {
  await Promise.all([fetchConditions(), fetchEvents()]);

  const pendingEvent = localStorage.getItem('pendingEventSearch');
  if (pendingEvent) {
    nextTick(() => {
      window.dispatchEvent(new CustomEvent('fillEventName', { detail: pendingEvent }));
      localStorage.removeItem('pendingEventSearch');
    });
  }
});

const fetchConditions = async () => {
  try {
    const data = await $fetch<ExperimentCondition[]>('/api/conditions');
    conditions.value = data;
    if (!data.some((condition) => condition.condition_key === selectedConditionKey.value) && data[0]) {
      selectedConditionKey.value = data[0].condition_key;
    }
  } catch (e) {
    console.error('Failed to fetch conditions:', e);
  }
};

const fetchEvents = async () => {
  loadingEvents.value = true;
  try {
    events.value = await $fetch<EventWithPersonas[]>('/api/events');
  } catch (e) {
    console.error('Failed to fetch events:', e);
  } finally {
    loadingEvents.value = false;
  }
};

const refreshEvents = async () => {
  isRefreshing.value = true;
  await fetchEvents();
  isRefreshing.value = false;
};

const compactConditionLabel = (condition: ExperimentCondition) => {
  const ebl = condition.ebl_enabled ? 'With EBL' : 'Without EBL';
  const roleplay = condition.roleplay_enabled ? 'Role-play' : 'Generic chat';
  return `${ebl} / ${roleplay}`;
};

const handleEventSubmit = async (eventName: string) => {
  await initializeEvent(eventName, false);
};

const handleEnterStory = async (event: EventWithPersonas) => {
  await initializeEvent(event.canonical_name, false);
};

const initializeEvent = async (eventName: string, rebuild: boolean) => {
  isLoading.value = true;
  error.value = null;
  try {
    const response = await $fetch<EventInitializeResponse>('/api/event/initialize', {
      method: 'POST',
      body: {
        event_name: eventName,
        condition_key: selectedConditionKey.value,
        rebuild,
      },
    });

    const taskData = useState<EventInitializeResponse | null>('taskData', () => null);
    taskData.value = response;

    await navigateTo({
      path: '/task',
      query: {
        taskId: response.task.id,
        sessionId: response.session_id,
      },
    });
  } catch (e: any) {
    error.value = e.data?.detail || e.data?.message || '建立流程失敗，請稍後再試。';
  } finally {
    isLoading.value = false;
  }
};

const handleDeleteEvent = (eventId: string) => {
  pendingDeleteEventId.value = eventId;
  showDeleteConfirmDialog.value = true;
};

const confirmDelete = async () => {
  if (!pendingDeleteEventId.value) return;
  try {
    await $fetch(`/api/event/${pendingDeleteEventId.value}`, { method: 'DELETE' });
    await fetchEvents();
  } catch (e) {
    console.error('Failed to delete event:', e);
    alert('刪除失敗，請稍後再試');
  } finally {
    showDeleteConfirmDialog.value = false;
    pendingDeleteEventId.value = null;
  }
};
</script>
