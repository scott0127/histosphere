<template>
  <div class="my-3 min-w-0 border-y border-[var(--admin-border-soft)] py-3 text-sm leading-6" :aria-label="`${review.label} 作答結果`">
    <p v-if="showQuestion && review.questionText" class="mb-2 whitespace-pre-wrap break-words text-[var(--admin-text)]">{{ review.questionText }}</p>
    <div class="mb-2 flex flex-wrap items-center gap-3">
      <span class="font-mono font-bold text-[var(--admin-coffee)]">{{ review.label }}</span>
      <span :class="review.status === 'correct' ? 'text-[var(--admin-success)]' : review.status === 'incorrect' ? 'text-[var(--admin-danger)]' : 'text-[var(--admin-copy)]'" class="font-semibold">
        {{ taskReviewStatusLabel(review.status) }}
      </span>
    </div>
    <dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2">
      <dt class="font-semibold text-[var(--admin-copy)]">答案</dt>
      <dd class="whitespace-pre-wrap break-words text-[var(--admin-text)]">{{ review.answerText }}</dd>
      <dt class="font-semibold text-[var(--admin-copy)]">作答理由</dt>
      <dd class="whitespace-pre-wrap break-words text-[var(--admin-text)]">{{ review.rationale || '未填寫' }}</dd>
    </dl>
  </div>
</template>

<script setup lang="ts">
import { taskReviewStatusLabel, type TaskAnswerReview } from '~/composables/useStudentTask';

defineProps<{ review: TaskAnswerReview; showQuestion?: boolean }>();
</script>
