<template>
  <p v-if="notice" :key="notice" role="status" aria-live="polite" aria-atomic="true"
    :class="{ 'progress-notice-highlight': notice.includes(' → ') }"
    class="task-progress-notice flex shrink-0 items-start gap-2 border-b border-[var(--admin-border-soft)] bg-[var(--admin-coffee-soft)] px-5 py-3 text-sm font-semibold leading-6 text-[var(--admin-coffee)]">
    <Icon name="mdi:check-circle-outline" class="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
    <span>{{ notice }}</span>
  </p>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ChatMessage, EventTask, LearningFocus } from '~/types';
import { getTaskDiscussionCompletions } from '~/utils/taskDiscussionProgress';

const props = defineProps<{
  task: EventTask;
  history: ChatMessage[];
  learningFocus?: LearningFocus | null;
}>();

const notice = computed(() => {
  const focus = props.learningFocus;
  if (!focus || focus.status === 'none') return '';
  const questions = props.task.evaluation_payload.questions || [];
  const currentIndex = questions.findIndex((question) => question.id === focus.question_id);
  const current = focus.status === 'completed' ? '本輪題目已討論完畢'
    : focus.origin === 'third_party' ? '目前進行延伸討論'
    : currentIndex >= 0 ? `目前討論第 ${currentIndex + 1} 題` : '';
  if (!current || focus.origin === 'third_party') return current;

  const completion = getTaskDiscussionCompletions(props.task, props.history)[0];
  if (completion) {
    // 回覆與焦點尚未同步時，保留目前題目，不搶先宣告轉題。
    if (focus.status === 'active' && completion.questionIndex === currentIndex) return current;
    return `第 ${completion.questionIndex + 1} 題${completion.label} → ${current}`;
  }
  return current;
});
</script>

<style scoped>
.progress-notice-highlight {
  animation: progress-notice-pulse 1.2s ease-in-out 2;
}

.chat-workspace .task-progress-notice {
  gap: 10px;
  padding: 12px 20px;
  border-color: var(--chat-border-soft, var(--admin-border-soft));
  background: var(--chat-sage, #eef2e9);
  color: #52604a;
  box-shadow: var(--chat-edge, inset 0 1px 0 rgb(255 255 255 / 88%));
  font-size: 13px;
  font-weight: 500;
  line-height: 1.75;
}

.chat-workspace .progress-notice-highlight {
  animation-name: chat-progress-notice-pulse;
}

@keyframes chat-progress-notice-pulse {
  0%, 100% {
    background-color: var(--chat-sage, #eef2e9);
    box-shadow: inset 3px 0 0 transparent;
  }
  35%, 65% {
    background-color: #e3eadc;
    box-shadow: inset 3px 0 0 #7d8b70;
  }
}

@keyframes progress-notice-pulse {
  0%, 100% {
    background-color: var(--admin-coffee-soft);
    box-shadow: inset 0 0 0 0 transparent;
  }
  35%, 65% {
    background-color: #f5ce86;
    box-shadow: inset 4px 0 0 var(--admin-coffee), inset 0 0 0 1px #c08a3b;
  }
}

@media (max-width: 767px) {
  .chat-workspace .task-progress-notice { padding-inline: 16px; }
}

@media (prefers-reduced-motion: reduce) {
  .progress-notice-highlight {
    animation: none;
    box-shadow: inset 4px 0 0 var(--admin-coffee);
  }
  .chat-workspace .progress-notice-highlight {
    animation: none;
    box-shadow: inset 3px 0 0 #7d8b70;
  }
}
</style>
