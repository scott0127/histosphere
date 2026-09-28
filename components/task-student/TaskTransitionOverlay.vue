<template>
  <Transition enter-active-class="transition-opacity duration-300" leave-active-class="transition-opacity duration-200"
    enter-from-class="opacity-0" leave-to-class="opacity-0">
    <div v-if="show" class="task-waiting" role="status" aria-live="polite" aria-busy="true">
      <header class="task-waiting__header"><span>Histosphere</span><span>{{ eventName }}</span></header>
      <main class="task-waiting__main">
        <section class="task-waiting__card">
          <div class="task-waiting__mark" aria-hidden="true"><Icon name="mdi:check" /></div>
          <p class="task-waiting__eyebrow">TASK</p>
          <h1>{{ waitingState?.stage === 'sending' ? '正在送出作答' : '作答已送出' }}</h1>
          <p class="task-waiting__description">{{ message }}</p>
          <div class="task-waiting__connection">
            <span :class="['task-waiting__dot', { 'is-offline': waitingState && !waitingState.connected }]" aria-hidden="true"></span>
            <span>{{ waitingState && !waitingState.connected ? '正在重新連線，已保存的進度會保留' : '完成準備後，將自動進入互動' }}</span>
          </div>
          <p class="task-waiting__hint">請保持此頁開啟。等待期間不計入互動時間。</p>
        </section>
      </main>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { TaskWaitingState } from '~/utils/taskSubmissionWaiter';

const props = defineProps<{
  show: boolean;
  eventName: string;
  waitingState?: TaskWaitingState;
}>();
const message = computed(() => {
  if (props.waitingState?.stage === 'failed') return '作答已保存，請通知研究者協助繼續。';
  if (['preparing_chat', 'ready', 'submitted'].includes(props.waitingState?.stage || '')) return '正在準備接下來的互動，請稍候。';
  if (props.waitingState?.stage === 'sending') return '正在保存你的回答，請稍候。';
  return '請稍候，研究者正在確認你的作答。';
});
</script>

<style scoped>
.task-waiting { position: fixed; inset: 0; z-index: 100; overflow-y: auto; background: var(--admin-page); color: var(--admin-text); font-family: var(--font-sans, sans-serif); }
.task-waiting__header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1.2rem clamp(1.5rem, 5vw, 5rem); border-bottom: 1px solid var(--admin-border-soft); color: var(--admin-copy); font-size: .85rem; }
.task-waiting__header span:first-child { font-family: var(--font-serif, serif); color: var(--admin-text); font-size: 1.25rem; }
.task-waiting__main { min-height: calc(100dvh - 72px); display: grid; place-items: center; padding: 2rem 1.25rem; }
.task-waiting__card { width: min(100%, 560px); padding: clamp(2rem, 5vw, 3.5rem); text-align: center; background: var(--admin-surface); border: 1px solid var(--admin-border-soft); border-radius: 24px; box-shadow: 0 16px 56px rgba(74, 57, 43, .05), inset 0 1px 0 #ffffffa0; }
.task-waiting__mark { display: grid; place-items: center; width: 3rem; height: 3rem; margin: 0 auto 1.8rem; border: 1px solid #7d8b7530; border-radius: 50%; background: #7d8b750c; color: #68765e; font-size: 1.4rem; }
.task-waiting__eyebrow { font-size: .7rem; letter-spacing: .18em; color: var(--admin-coffee); }
h1 { margin: .8rem 0 1rem; font-size: clamp(1.5rem, 4vw, 1.85rem); font-weight: 600; letter-spacing: .025em; }
.task-waiting__description { color: var(--admin-copy); font-size: .95rem; line-height: 1.9; }
.task-waiting__connection { display: flex; justify-content: center; align-items: center; gap: .55rem; margin-top: 2.25rem; padding-top: 1.5rem; border-top: 1px solid var(--admin-border-soft); font-size: .8rem; color: var(--admin-copy); }
.task-waiting__dot { width: 6px; height: 6px; flex-shrink: 0; border-radius: 50%; background: #7d8b75; }
.task-waiting__dot.is-offline { background: var(--admin-coffee); }
.task-waiting__hint { margin-top: .85rem; font-size: .75rem; line-height: 1.8; color: var(--admin-copy); opacity: .8; }
</style>
