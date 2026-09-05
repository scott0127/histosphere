<template>
  <div
    v-if="session?.timer_ends_at && !expired"
    :class="[
      'flex min-h-14 flex-wrap items-center justify-between gap-3 border text-sm font-bold',
      flush ? 'rounded-none border-x-0 border-t-0 px-5 py-4' : 'rounded-lg px-4 py-3',
      'border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] text-[var(--admin-coffee)]',
    ]"
    aria-live="polite"
  >
    <div class="flex min-w-0 items-center gap-3">
      <Icon
        v-if="!flush"
        name="mdi:timer-outline"
        class="h-5 w-5 shrink-0"
      />
      <p>本階段剩餘時間</p>
    </div>
    <span class="font-mono text-base tabular-nums">{{ formattedRemaining }}</span>
  </div>

  <SessionClosureDialog
    v-if="session?.timer_ends_at && expired"
    :key="session.timer_ends_at"
    :session-id="session.id"
    @next-stage="$emit('next-stage')"
  />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import SessionClosureDialog from '~/components/session/SessionClosureDialog.vue';
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
