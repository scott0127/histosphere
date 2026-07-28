<template>
  <div
    v-if="session?.timer_ends_at"
    :class="[
      'flex min-h-14 flex-wrap items-center justify-between gap-3 border text-sm font-bold',
      flush ? 'rounded-none border-x-0 border-t-0 px-5 py-4' : 'rounded-lg px-4 py-3',
      expired
        ? 'border-red-300 bg-red-50 text-red-800'
        : 'border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] text-[var(--admin-coffee)]',
    ]"
    aria-live="polite"
  >
    <div class="flex min-w-0 items-center gap-3">
      <Icon
        v-if="!flush"
        :name="expired ? 'mdi:timer-check-outline' : 'mdi:timer-outline'"
        class="h-5 w-5 shrink-0"
      />
      <div>
        <p>{{ expired ? '本階段已結束' : '本階段剩餘時間' }}</p>
        <p v-if="expired" class="mt-0.5 text-xs font-semibold text-red-700">
          對話已停止，請進入下一階段。
        </p>
      </div>
    </div>
    <button
      v-if="expired"
      type="button"
      class="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-red-800 px-4 text-sm font-bold text-white transition hover:bg-red-900"
      @click="$emit('next-stage')"
    >
      進入下一階段
      <Icon name="mdi:arrow-right" class="h-4 w-4" />
    </button>
    <span v-else class="font-mono text-base tabular-nums">{{ formattedRemaining }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import type { ExperimentSession } from '~/types';

const props = withDefaults(defineProps<{
  session?: ExperimentSession | null;
  flush?: boolean;
}>(), {
  flush: false,
});
defineEmits<{ (event: 'next-stage'): void }>();
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
