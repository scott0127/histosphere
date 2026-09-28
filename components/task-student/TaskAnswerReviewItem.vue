<template>
  <div class="answer-review min-w-0 py-2 text-sm leading-7" :aria-label="`${review.label} 作答結果`">
    <h3 v-if="showQuestion && review.questionText" class="answer-review-question mb-4 whitespace-pre-wrap break-words text-base font-semibold leading-8 text-[var(--admin-text)]">{{ review.questionText }}</h3>
    <ol v-if="showQuestion && review.question.options?.length" class="answer-review-options mb-5 space-y-2" aria-label="題目選項">
      <li v-for="(option, index) in review.question.options" :key="option.id" class="answer-review-option flex gap-3 border-l-2 py-1 pl-3"
        :data-selected="option.value === review.value"
        :class="option.value === review.value ? 'border-[var(--admin-coffee)] bg-[var(--admin-surface-muted)]' : 'border-transparent'">
        <span class="answer-review-option-key shrink-0 font-mono font-semibold text-[var(--admin-coffee)]">{{ String.fromCharCode(65 + index) }}</span>
        <span class="min-w-0 break-words">{{ option.label }}</span>
      </li>
    </ol>
    <div class="answer-review-summary mb-2 flex flex-wrap items-center gap-3">
      <span class="answer-review-label font-mono font-bold text-[var(--admin-coffee)]">{{ review.label }}</span>
      <span class="text-xs text-[var(--admin-soft)]">原始作答</span>
      <span :class="review.status === 'correct' ? 'text-[var(--admin-success)]' : review.status === 'incorrect' ? 'text-[var(--admin-danger)]' : 'text-[var(--admin-copy)]'" class="font-semibold">
        {{ taskReviewStatusLabel(review.status) }}
      </span>
    </div>
    <dl class="answer-review-details grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2">
      <dt class="font-semibold text-[var(--admin-copy)]">答案</dt>
      <dd class="whitespace-pre-wrap break-words text-[var(--admin-text)]">{{ review.answerText }}</dd>
      <dt class="font-semibold text-[var(--admin-copy)]">作答理由</dt>
      <dd class="whitespace-pre-wrap break-words text-[var(--admin-text)]">{{ review.rationale || '未填寫' }}</dd>
    </dl>
    <div v-if="discussion" class="answer-review-discussion mt-4 flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-t border-[var(--admin-border-soft)] pt-3">
      <span class="answer-review-discussion-status inline-flex items-center gap-1.5 text-xs font-semibold"
        :class="discussion.status === 'corrected' ? 'text-[var(--admin-success)]' : discussion.status === 'active' ? 'text-[var(--admin-coffee)]' : 'text-[var(--admin-copy)]'">
        <Icon :name="discussion.status === 'corrected' ? 'mdi:check-circle-outline' : discussion.status === 'active' ? 'mdi:message-processing-outline' : 'mdi:check'" class="h-4 w-4" aria-hidden="true" />
        {{ discussion.label }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { taskReviewStatusLabel, type TaskAnswerReview } from '~/composables/useStudentTask';
import type { TaskDiscussionProgress } from '~/utils/taskDiscussionProgress';

defineProps<{ review: TaskAnswerReview; showQuestion?: boolean; discussion?: TaskDiscussionProgress }>();
</script>

<style scoped>
.chat-workspace .answer-review {
  padding: 0;
  font-size: 14px;
  line-height: 1.7;
}

.chat-workspace .answer-review-question {
  margin-bottom: 12px;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.7;
}

.chat-workspace .answer-review-options {
  margin-bottom: 14px;
}

.chat-workspace .answer-review-option + .answer-review-option {
  margin-top: 4px;
}

.chat-workspace .answer-review-option {
  align-items: flex-start;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid transparent;
  border-radius: 11px;
}

.chat-workspace .answer-review-option-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 7px;
  background: var(--chat-surface-muted, #f3f0e9);
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
}

.chat-workspace .answer-review-option[data-selected="true"] {
  border-color: #d9cabc;
  background: #f4ede4;
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 65%);
}

.chat-workspace .answer-review-option[data-selected="true"] .answer-review-option-key {
  color: #fffdf8;
  background: var(--admin-coffee);
}

.chat-workspace .answer-review-summary {
  gap: 8px;
  margin-bottom: 8px;
}

.chat-workspace .answer-review-label {
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--chat-surface-muted, #f3f0e9);
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
}

.chat-workspace .answer-review-details {
  column-gap: 12px;
  row-gap: 6px;
}

.chat-workspace .answer-review-details dt {
  padding-top: 2px;
  font-size: 13px;
  font-weight: 500;
}

.chat-workspace .answer-review-discussion {
  margin-top: 12px;
  padding-top: 10px;
}

.chat-workspace .answer-review-discussion-status {
  font-size: 13px;
}

</style>
