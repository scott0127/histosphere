<template>
  <details open class="group shrink-0 border-b border-[var(--admin-border-soft)] bg-[var(--admin-surface-muted)]">
    <summary class="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-3 [&::-webkit-details-marker]:hidden">
      <div>
        <p class="text-xs font-black uppercase tracking-[0.16em] text-[var(--admin-coffee)]">前置任務</p>
        <h2 class="mt-0.5 text-sm font-semibold text-[var(--admin-text)]">作答結果</h2>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-xs font-semibold text-[var(--admin-soft)]">{{ reviews.length }} 題</span>
        <Icon name="mdi:chevron-down" class="h-5 w-5 text-[var(--admin-coffee)] transition-transform group-open:rotate-180" />
      </div>
    </summary>

    <div class="max-h-64 overflow-y-auto border-t border-[var(--admin-border-soft)] bg-[var(--admin-surface)] px-5 py-4">
      <p class="whitespace-pre-wrap font-serif text-base leading-8 text-[var(--admin-text)]">
        <template v-for="(segment, index) in storySegments" :key="`${segment.type}-${index}`">
          <span v-if="segment.type === 'text'">{{ segment.text }}</span><span
            v-else
            :class="answerClass(reviewFor(segment.question.id)?.status)"
            :aria-label="`${reviewFor(segment.question.id)?.label || '題目'}，${statusLabel(reviewFor(segment.question.id)?.status)}`"
          >{{ reviewFor(segment.question.id)?.answerText || '未作答' }}</span>
        </template>
      </p>

      <div class="mt-4 flex flex-wrap gap-2 border-t border-[var(--admin-border-soft)] pt-3" aria-label="逐題作答結果">
        <span
          v-for="review in reviews"
          :key="review.question.id"
          :class="statusClass(review.status)"
        >
          <span class="font-mono">{{ review.label }}</span>
          <span>{{ statusLabel(review.status) }}</span>
        </span>
      </div>
    </div>
  </details>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { EventTask, TaskAttempt } from '~/types';
import {
  buildTaskAnswerReviews,
  buildTaskStorySegments,
  type TaskAnswerReviewStatus,
} from '~/composables/useStudentTask';

const props = defineProps<{
  task: EventTask;
  attempt: TaskAttempt;
}>();

const reviews = computed(() => buildTaskAnswerReviews(props.task, props.attempt));
const storySegments = computed(() => buildTaskStorySegments(props.task));
const reviewsByQuestionId = computed(() => new Map(
  reviews.value.map((review) => [review.question.id, review]),
));

const reviewFor = (questionId: string) => reviewsByQuestionId.value.get(questionId);

const statusLabel = (status?: TaskAnswerReviewStatus) => {
  if (status === 'correct') return '答對';
  if (status === 'incorrect') return '答錯';
  if (status === 'unanswered') return '未作答';
  return '待討論';
};

const answerClass = (status?: TaskAnswerReviewStatus) => [
  'border-b-2 px-0.5 font-semibold',
  status === 'incorrect'
    ? 'border-[var(--admin-danger)] text-[var(--admin-text)]'
    : status === 'correct'
      ? 'border-[var(--admin-success)] text-[var(--admin-text)]'
      : 'border-[var(--admin-coffee-muted)] text-[var(--admin-copy)]',
];

const statusClass = (status: TaskAnswerReviewStatus) => [
  'inline-flex h-7 items-center gap-1.5 rounded-md border px-2.5 text-xs font-semibold',
  status === 'correct'
    ? 'border-[var(--admin-success)] bg-[var(--admin-success-soft)] text-[var(--admin-success)]'
    : status === 'incorrect'
      ? 'border-[var(--admin-danger)] bg-[var(--admin-danger-soft)] text-[var(--admin-danger)]'
      : 'border-[var(--admin-border)] bg-[var(--admin-surface-muted)] text-[var(--admin-copy)]',
];
</script>
