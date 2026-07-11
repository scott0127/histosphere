<template>
  <div
    v-if="session?.timer_ends_at"
    class="flex min-h-12 items-center justify-between gap-4 rounded-lg border px-4 py-3 text-sm font-bold"
    :class="expired ? 'border-red-300 bg-red-50 text-red-800' : 'border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] text-[var(--admin-coffee)]'"
    aria-live="polite"
  >
    <span class="inline-flex items-center gap-2">
      <Icon :name="expired ? 'mdi:timer-stop-outline' : 'mdi:timer-outline'" class="h-5 w-5" />
      {{ expired ? '本階段時間已結束' : '本階段剩餘時間' }}
    </span>
    <span class="font-mono text-base">{{ expired ? '00:00' : formattedRemaining }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import type { ExperimentSession } from '~/types';

const props = defineProps<{ session?: ExperimentSession | null }>();
const now = ref(Date.now());
let intervalId: ReturnType<typeof setInterval> | null = null;

const remainingSeconds = computed(() => {
  if (!props.session?.timer_ends_at) return 0;
  return Math.max(0, Math.ceil((Date.parse(props.session.timer_ends_at) - now.value) / 1000));
});
const expired = computed(() => {
  return props.session?.status === 'completed'
    || props.session?.status === 'archived'
    || Boolean(props.session?.timer_ends_at && remainingSeconds.value <= 0);
});
const formattedRemaining = computed(() => {
  const minutes = Math.floor(remainingSeconds.value / 60);
  const seconds = remainingSeconds.value % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
});

onMounted(() => {
  intervalId = setInterval(() => { now.value = Date.now(); }, 1000);
});
onBeforeUnmount(() => {
  if (intervalId) clearInterval(intervalId);
});
</script>
