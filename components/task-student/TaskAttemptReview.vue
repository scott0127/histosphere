<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <header class="flex shrink-0 items-center justify-between gap-4 border-b border-[var(--admin-border-soft)] px-5 py-3">
      <div>
        <p class="text-xs font-black text-[var(--admin-coffee)]">Error-Elicitation Task</p>
        <h2 class="mt-0.5 text-sm font-semibold text-[var(--admin-text)]">題目與作答</h2>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-xs font-semibold text-[var(--admin-soft)]">{{ reviews.length }} 題</span>
      </div>
    </header>
    <div class="flex shrink-0 border-b border-[var(--admin-border-soft)] px-3" role="tablist" aria-label="題組回顧">
      <button v-for="tab in tabs" :id="`review-tab-${tab.id}`" :key="tab.id" role="tab" type="button"
        :aria-selected="view === tab.id" :tabindex="view === tab.id ? 0 : -1" aria-controls="review-tab-content"
        class="inline-flex items-center gap-2 border-b-2 px-3 py-3 text-sm font-semibold"
        :class="view === tab.id ? 'border-[var(--admin-coffee)] text-[var(--admin-coffee)]' : 'border-transparent text-[var(--admin-soft)]'"
        @click="view = tab.id" @keydown="switchTab($event)">
        <Icon :name="tab.icon" class="h-4 w-4" />{{ tab.label }}
      </button>
    </div>

    <div id="review-tab-content" role="tabpanel" :aria-labelledby="`review-tab-${view}`" tabindex="0" class="min-h-0 flex-1 overflow-y-auto bg-[var(--admin-surface)] px-5 py-4">
      <template v-if="view === 'answers'">
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
      </template>
      <div v-else-if="task.evaluation_payload.materials?.length" class="space-y-6">
        <p v-if="readingLayout.introduction" class="whitespace-pre-wrap break-words text-base leading-8 text-[var(--admin-text)]">{{ readingLayout.introduction }}</p>
        <TaskStudentMaterials :materials="task.evaluation_payload.materials" />
      </div>
      <p v-else class="text-sm text-[var(--admin-soft)]">此題組沒有另外的閱讀材料。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue';
import type { EventTask, TaskAttempt } from '~/types';
import { buildTaskAnswerReviews, buildTaskReadingLayout } from '~/composables/useStudentTask';
import TaskAnswerReviewItem from './TaskAnswerReviewItem.vue';
import TaskStudentMaterials from './TaskStudentMaterials.vue';

const props = defineProps<{
  task: EventTask;
  attempt: TaskAttempt;
}>();

const tabs = [
  { id: 'answers', label: '作答', icon: 'mdi:clipboard-text-outline' },
  { id: 'materials', label: '閱讀材料', icon: 'mdi:book-open-page-variant-outline' },
];
const view = ref('answers');
async function switchTab(event: KeyboardEvent) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  view.value = event.key === 'Home' ? 'answers' : event.key === 'End' ? 'materials'
    : view.value === 'answers' ? 'materials' : 'answers';
  await nextTick();
  document.getElementById(`review-tab-${view.value}`)?.focus();
}

const reviews = computed(() => buildTaskAnswerReviews(props.task, props.attempt));
const readingLayout = computed(() => buildTaskReadingLayout(props.task));
const storySegments = computed(() => readingLayout.value.segments);
const reviewFor = (questionId: string) => reviews.value.find((review) => review.question.id === questionId);
const remainingReviews = computed(() => {
  const inlineIds = new Set(storySegments.value.flatMap((segment) => segment.type === 'blank' ? [segment.question.id] : []));
  return reviews.value.filter((review) => !inlineIds.has(review.question.id));
});
</script>
