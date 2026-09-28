<template>
  <div
    v-if="session?.timer_ends_at && !expired"
    :class="[
      'session-timer-banner flex min-h-14 flex-wrap items-center justify-between gap-3 border text-sm font-bold',
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
      <p class="session-timer-label">本階段剩餘時間</p>
    </div>
    <span class="session-timer-value font-mono text-base tabular-nums">{{ formattedRemaining }}</span>
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

<style scoped>
.chat-workspace .session-timer-banner {
  min-height: 58px;
  padding: 12px 20px;
  border-color: var(--chat-border-soft, var(--admin-border-soft));
  background: var(--chat-surface-muted, #f7f5f1);
  color: var(--chat-coffee, var(--admin-coffee));
  box-shadow: var(--chat-edge, inset 0 1px 0 rgb(255 255 255 / 88%));
}

.chat-workspace .session-timer-label {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
}

.chat-workspace .session-timer-value {
  min-width: 76px;
  padding: 4px 12px;
  border: 1px solid var(--chat-border, var(--admin-border));
  border-radius: 10px;
  background: var(--chat-surface, var(--admin-surface));
  box-shadow: var(--chat-edge, inset 0 1px 0 rgb(255 255 255 / 88%));
  font-family: inherit;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
  letter-spacing: 0.04em;
  text-align: center;
}

@media (max-width: 767px) {
  .chat-workspace .session-timer-banner { padding-inline: 16px; }
}
</style>
