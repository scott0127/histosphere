<template>
  <form class="space-y-4" @submit.prevent="handleSubmit">
    <div>
      <label for="event" class="text-sm font-semibold text-slate-700">歷史事件</label>
      <input
        id="event"
        v-model="eventName"
        type="text"
        :placeholder="currentPlaceholder"
        class="mt-2 w-full rounded-lg border border-slate-300 bg-white px-4 py-3 font-sans text-base text-slate-950 shadow-sm outline-none transition focus:border-teal-600 focus:ring-4 focus:ring-teal-100 disabled:bg-slate-100"
        :disabled="isLoading"
      />
    </div>

    <button
      type="submit"
      :disabled="isLoading || !eventName.trim()"
      class="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 py-3 font-sans text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
    >
      <Icon v-if="isLoading" name="mdi:loading" class="h-5 w-5 animate-spin" />
      <Icon v-else name="mdi:arrow-right" class="h-5 w-5" />
      {{ isLoading ? '建立學習流程中' : '建立 task' }}
    </button>

    <p v-if="error" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
      {{ error }}
    </p>
  </form>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';

defineProps<{
  isLoading: boolean;
  error: string | null;
}>();

const emit = defineEmits<{
  (event: 'event-submit', eventName: string): void;
}>();

const eventName = ref('');
const placeholders = [
  '例如：諾曼第登陸',
  '例如：法國大革命',
  '例如：明治維新',
  '例如：安史之亂',
];
const currentPlaceholderIndex = ref(0);
const currentPlaceholder = ref(placeholders[0]);
let placeholderInterval: ReturnType<typeof setInterval> | null = null;

const rotatePlaceholder = () => {
  currentPlaceholderIndex.value = (currentPlaceholderIndex.value + 1) % placeholders.length;
  currentPlaceholder.value = placeholders[currentPlaceholderIndex.value];
};

const handleSubmit = () => {
  const trimmed = eventName.value.trim();
  if (trimmed) emit('event-submit', trimmed);
};

const handleFillEvent = (event: CustomEvent) => {
  eventName.value = event.detail;
  document.getElementById('event')?.focus();
};

onMounted(() => {
  window.addEventListener('fillEventName', handleFillEvent as EventListener);
  placeholderInterval = setInterval(rotatePlaceholder, 3000);
});

onUnmounted(() => {
  window.removeEventListener('fillEventName', handleFillEvent as EventListener);
  if (placeholderInterval) clearInterval(placeholderInterval);
});
</script>
