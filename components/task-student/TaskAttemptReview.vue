<template>
  <details open class="group shrink-0 border-b border-[var(--admin-border-soft)] bg-[var(--admin-surface-muted)]">
    <summary class="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-3 [&::-webkit-details-marker]:hidden">
      <div>
        <p class="text-xs font-black text-[var(--admin-coffee)]">Error-Elicitation Task</p>
        <h2 class="mt-0.5 text-sm font-semibold text-[var(--admin-text)]">作答結果</h2>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-xs font-semibold text-[var(--admin-soft)]">{{ reviews.length }} 題</span>
        <Icon name="mdi:chevron-down" class="h-5 w-5 text-[var(--admin-coffee)] transition-transform group-open:rotate-180" />
      </div>
    </summary>

    <div class="max-h-80 overflow-y-auto border-t border-[var(--admin-border-soft)] bg-[var(--admin-surface)] px-5 py-4">
      <div class="min-w-0 break-words text-base leading-8 text-[var(--admin-text)]">
        <template v-for="(segment, index) in storySegments" :key="`${segment.type}-${index}`">
          <span v-if="segment.type === 'text'" class="whitespace-pre-wrap">{{ segment.text }}</span>
          <TaskAnswerReviewItem
            v-else-if="reviewFor(segment.question.id)"
            :review="reviewFor(segment.question.id)!"
          />
        </template>
      </div>
      <TaskAnswerReviewItem v-for="review in remainingReviews" :key="review.question.id" :review="review" show-question />
      <TaskStudentMaterials v-if="task.evaluation_payload.materials?.length" class="mt-6 border-t border-[var(--admin-border-soft)] pt-5" :materials="task.evaluation_payload.materials" />
    </div>
  </details>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { EventTask, TaskAttempt } from '~/types';
import { buildTaskAnswerReviews, buildTaskStorySegments } from '~/composables/useStudentTask';
import TaskAnswerReviewItem from './TaskAnswerReviewItem.vue';
import TaskStudentMaterials from './TaskStudentMaterials.vue';

const props = defineProps<{
  task: EventTask;
  attempt: TaskAttempt;
}>();

const reviews = computed(() => buildTaskAnswerReviews(props.task, props.attempt));
const storySegments = computed(() => buildTaskStorySegments(props.task));
const reviewFor = (questionId: string) => reviews.value.find((review) => review.question.id === questionId);
const remainingReviews = computed(() => {
  const inlineIds = new Set(storySegments.value.flatMap((segment) => segment.type === 'blank' ? [segment.question.id] : []));
  return reviews.value.filter((review) => !inlineIds.has(review.question.id));
});
</script>
