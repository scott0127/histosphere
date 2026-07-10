<template>
  <Transition
    enter-active-class="transition-opacity duration-300 ease-out"
    leave-active-class="transition-opacity duration-200 ease-in"
    enter-from-class="opacity-0"
    leave-to-class="opacity-0"
  >
    <div
      v-if="show"
      class="fixed inset-0 z-[100] overflow-y-auto bg-[var(--admin-page)] font-sans text-[var(--admin-text)]"
      role="status"
      aria-live="polite"
      aria-busy="true"
      :aria-label="`正在回到 ${eraLabel}的時代`"
    >
      <div class="pointer-events-none fixed inset-0">
        <img src="~/assets/images/landing-bg.png" alt="" class="h-full w-full object-cover opacity-[0.16]" />
        <div class="absolute inset-0 bg-[rgba(242,240,236,0.9)]"></div>
      </div>

      <header class="relative z-10 border-b border-[var(--admin-border)] bg-[rgba(255,253,248,0.82)]">
        <div class="mx-auto flex min-h-16 max-w-6xl items-center justify-between px-6">
          <div class="flex items-center gap-3">
            <span class="flex h-10 w-10 items-center justify-center rounded-full border-2 border-[var(--admin-line)] bg-[var(--admin-surface)] text-[var(--admin-coffee)] shadow-[0_3px_0_rgba(47,41,36,0.18)]">
              <Icon name="mdi:history" class="h-5 w-5" />
            </span>
            <span>
              <span class="block font-serif text-lg font-bold tracking-[0.08em]">Histosphere</span>
              <span class="block text-xs font-semibold tracking-[0.08em] text-[var(--admin-copy)]">時間轉場</span>
            </span>
          </div>
          <span class="font-mono text-sm font-semibold text-[var(--admin-copy)]">
            {{ elapsedSeconds }} 秒
          </span>
        </div>
      </header>

      <main class="relative z-10 mx-auto flex min-h-[calc(100vh-64px)] max-w-6xl items-center px-6 py-14">
        <section class="w-full max-w-5xl">
          <p class="text-xs font-black uppercase tracking-[0.22em] text-[var(--admin-coffee)]">Time transition</p>
          <h2 class="mt-5 max-w-5xl font-serif text-5xl font-bold leading-[1.12] text-[var(--admin-text)] md:text-7xl">
            正在回到
            <span class="my-2 block text-[var(--admin-coffee)]">{{ eraLabel }}</span>
            的時代
          </h2>
          <p class="mt-6 max-w-3xl text-xl font-semibold leading-9 text-[var(--admin-copy)] md:text-2xl">
            {{ eventName }}
          </p>

          <div class="mt-12 flex items-center gap-4" aria-hidden="true">
            <span class="h-3 w-3 shrink-0 rounded-full bg-[var(--admin-coffee)] animate-pulse"></span>
            <span class="h-px flex-1 bg-[var(--admin-border)]"></span>
            <Icon name="mdi:book-open-page-variant" class="h-6 w-6 shrink-0 text-[var(--admin-coffee)]" />
          </div>

          <div class="mt-8 flex max-w-4xl items-start gap-4 border-y border-[var(--admin-border)] py-5">
            <Icon name="mdi:loading" class="mt-1 h-6 w-6 shrink-0 animate-spin text-[var(--admin-coffee)]" />
            <div>
              <p class="text-lg font-bold text-[var(--admin-text)]">{{ phase.label }}</p>
              <p class="mt-1 text-sm font-semibold leading-7 text-[var(--admin-copy)]">{{ phase.detail }}</p>
            </div>
          </div>
        </section>
      </main>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { formatTaskTransitionEra, taskTransitionPhase } from '~/utils/taskTransition';

const props = defineProps<{
  show: boolean;
  eventName: string;
  startYear?: number | null;
  endYear?: number | null;
}>();

const elapsedSeconds = ref(0);
let timer: ReturnType<typeof setInterval> | null = null;

const eraLabel = computed(() => formatTaskTransitionEra(
  props.eventName,
  props.startYear,
  props.endYear,
));
const phase = computed(() => taskTransitionPhase(elapsedSeconds.value));

const stopTimer = () => {
  if (!timer) return;
  clearInterval(timer);
  timer = null;
};

watch(
  () => props.show,
  (show) => {
    stopTimer();
    elapsedSeconds.value = 0;
    if (!show || !import.meta.client) return;
    timer = setInterval(() => {
      elapsedSeconds.value += 1;
    }, 1000);
  },
  { immediate: true },
);

onBeforeUnmount(stopTimer);
</script>
