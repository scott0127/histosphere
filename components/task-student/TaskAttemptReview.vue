<template>
  <div class="task-review flex min-h-0 flex-1 flex-col">
    <header class="task-review-header flex shrink-0 items-center justify-between gap-3 border-b border-[var(--admin-border-soft)] bg-[var(--admin-surface-muted)] px-4 py-3 md:px-5 md:py-4">
      <div class="flex min-w-0 flex-wrap items-baseline gap-x-2 md:block" aria-live="polite" aria-atomic="true">
        <p class="text-xs font-semibold text-[var(--admin-soft)]">{{ learningFocus ? '目前討論' : '作答回顧' }}</p>
        <h2 class="break-words text-base font-semibold leading-7 text-[var(--admin-text)] md:mt-1 md:text-lg">{{ focusTitle }}</h2>
      </div>
      <span class="task-review-count shrink-0 text-xs tabular-nums text-[var(--admin-soft)]">共 {{ reviews.length }} 題</span>
    </header>
    <div class="task-review-tabs flex shrink-0 border-b border-[var(--admin-border-soft)] px-2" role="tablist" aria-label="題組回顧">
      <button v-for="tab in tabs" :id="`review-tab-${tab.id}`" :key="tab.id" ref="tabButtons" role="tab" type="button"
        :aria-selected="view === tab.id" :tabindex="view === tab.id ? 0 : -1" aria-controls="review-tab-content"
        class="task-review-tab inline-flex min-w-0 items-center justify-center gap-1.5 border-b-2 px-2.5 py-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--admin-coffee)]"
        :class="view === tab.id ? 'border-[var(--admin-coffee)] text-[var(--admin-coffee)]' : 'border-transparent text-[var(--admin-soft)] hover:text-[var(--admin-text)]'"
        @click="view = tab.id" @keydown="switchTab($event)">
        <Icon :name="tab.icon" class="h-4 w-4 shrink-0" /><span>{{ tab.label }}</span>
      </button>
    </div>
    <div id="review-tab-content" ref="scrollPane" role="tabpanel" :aria-labelledby="`review-tab-${view}`" tabindex="0" class="task-review-content min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5">
      <template v-if="view === 'current'">
        <TaskAnswerReviewItem v-if="currentReview" :review="currentReview" :discussion="discussionByQuestion.get(currentReview.question.id)" show-question />
        <div v-else-if="learningFocus?.status === 'active' && learningFocus.origin === 'third_party' && learningFocus.claim" class="space-y-4">
          <p class="text-xs font-semibold text-[var(--admin-soft)]">另一個人的說法</p>
          <blockquote class="task-review-claim border-l-2 border-[var(--admin-coffee)] pl-4 text-base leading-8">{{ learningFocus.claim }}</blockquote>
        </div>
        <p v-else class="text-sm leading-7 text-[var(--admin-copy)]">{{ focusEmptyText }}</p>
      </template>
      <template v-else-if="view === 'answers'">
        <section v-for="review in reviews" :key="review.question.id" class="task-review-answer border-b border-[var(--admin-border-soft)] py-4 first:pt-0 last:border-0">
          <TaskAnswerReviewItem :review="review" :discussion="discussionByQuestion.get(review.question.id)" show-question />
        </section>
      </template>
      <div v-else-if="materials.length" class="space-y-5">
        <TaskStudentMaterials :materials="materials" compact />
      </div>
      <p v-else class="text-sm text-[var(--admin-soft)]">此題組沒有另外的閱讀材料。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import type { ChatMessage, EventTask, LearningFocus, TaskAttempt } from '~/types';
import { buildTaskAnswerReviews } from '~/composables/useStudentTask';
import { getTaskDiscussionCompletions, type TaskDiscussionProgress } from '~/utils/taskDiscussionProgress';
import TaskAnswerReviewItem from './TaskAnswerReviewItem.vue';
import TaskStudentMaterials from './TaskStudentMaterials.vue';

const props = defineProps<{
  task: EventTask;
  attempt: TaskAttempt;
  learningFocus?: LearningFocus | null;
  history?: ChatMessage[];
}>();
const view = ref(props.learningFocus ? 'current' : 'answers');
const scrollPane = ref<HTMLElement | null>(null);
const tabButtons = ref<HTMLButtonElement[]>([]);
const reviews = computed(() => buildTaskAnswerReviews(props.task, props.attempt));
const discussionByQuestion = computed(() => {
  const progress = new Map<string, TaskDiscussionProgress>();
  for (const completion of getTaskDiscussionCompletions(props.task, props.history || [])) {
    progress.set(completion.questionId, completion);
  }
  const focus = props.learningFocus;
  if (focus?.status === 'active' && focus.origin === 'learner' && focus.question_id) {
    // 焦點與回覆尚未一起送達時，仍以目前後端焦點顯示討論中。
    progress.set(focus.question_id, { status: 'active', label: '討論中' });
  }
  return progress;
});
const currentReview = computed(() => props.learningFocus?.status === 'active' && props.learningFocus.origin === 'learner'
  ? reviews.value.find((review) => review.question.id === props.learningFocus?.question_id) : undefined);
const focusTitle = computed(() => {
  if (!props.learningFocus) return '題目與作答';
  if (props.learningFocus?.status === 'completed') return '本輪題目已討論完畢';
  if (props.learningFocus?.status === 'none') return '自由討論';
  if (props.learningFocus?.origin === 'third_party') return '延伸討論';
  const index = reviews.value.findIndex((review) => review.question.id === props.learningFocus?.question_id);
  return index >= 0 && props.learningFocus?.status === 'active' ? `第 ${index + 1} 題` : '題目確認中';
});
const focusEmptyText = computed(() => props.learningFocus?.status === 'completed'
  ? '可以回看先前的作答與閱讀材料。'
  : props.learningFocus?.status === 'none' ? '目前沒有指定討論題目。' : '目前題目尚未載入，請稍候。');
const tabs = computed(() => [
  ...(props.learningFocus ? [{ id: 'current', label: '目前題目', icon: 'mdi:clipboard-text-outline' }] : []),
  { id: 'materials', label: '閱讀材料', icon: 'mdi:book-open-page-variant' },
  { id: 'answers', label: props.learningFocus ? '全部作答' : '題目與作答', icon: 'mdi:format-list-bulleted' },
]);
const materials = computed(() => props.task.evaluation_payload.materials || []);

// 只跟隨已保存的後端目標；離題聊天、載入舊訊息都不自行選題。
watch(() => [props.learningFocus?.question_id, props.learningFocus?.origin, props.learningFocus?.status], (value, previous) => {
  if (value.some((item, index) => item !== previous?.[index])) view.value = props.learningFocus ? 'current' : 'answers';
});
watch([view, () => props.learningFocus?.question_id], async () => {
  await nextTick();
  if (scrollPane.value) scrollPane.value.scrollTop = 0;
});
async function switchTab(event: KeyboardEvent) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  const currentIndex = tabs.value.findIndex((tab) => tab.id === view.value);
  const index = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.value.length - 1
    : (currentIndex + (event.key === 'ArrowRight' ? 1 : -1) + tabs.value.length) % tabs.value.length;
  view.value = tabs.value[index]!.id;
  await nextTick();
  tabButtons.value[index]?.focus();
}
</script>

<style scoped>
.chat-workspace .task-review-header {
  padding: 12px 18px;
  border-bottom: 0;
  background: transparent;
}

.chat-workspace .task-review-header > div {
  display: flex;
}

.chat-workspace .task-review-header h2 {
  margin-top: 0;
  font-size: 16px;
  line-height: 1.5;
  letter-spacing: 0;
}

.chat-workspace .task-review-header p {
  font-size: 12px;
  font-weight: 500;
}

.chat-workspace .task-review-count {
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--chat-surface-muted, #f3f0e9);
}

.chat-workspace .task-review-tabs {
  gap: 4px;
  margin: 0 14px 2px;
  padding: 4px;
  border: 1px solid var(--chat-border, #e0d9cf);
  border-radius: 13px;
  background: var(--chat-surface-muted, #f3f0e9);
  box-shadow: inset 0 1px 2px rgb(89 68 51 / 3%);
}

.chat-workspace .task-review-tab {
  flex: 1;
  min-height: 44px;
  padding: 8px 7px;
  border: 1px solid transparent;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  white-space: nowrap;
  transition: background-color 150ms ease, color 150ms ease, box-shadow 150ms ease;
}

.chat-workspace .task-review-tab:hover {
  color: var(--admin-coffee);
  background: rgb(255 253 248 / 65%);
}

.chat-workspace .task-review-tab[aria-selected="true"] {
  border-color: var(--chat-border, #e0d9cf);
  color: var(--admin-coffee);
  background: var(--chat-surface, #fffdf8);
  box-shadow: 0 2px 5px rgb(89 68 51 / 7%), inset 0 1px 0 rgb(255 255 255 / 90%);
  font-weight: 600;
}

.chat-workspace .task-review-tab:focus-visible,
.chat-workspace .task-review-content:focus-visible {
  outline: 2px solid var(--admin-coffee);
  outline-offset: 3px;
}

.chat-workspace .task-review-content {
  padding: 16px 18px;
  scrollbar-width: thin;
  scrollbar-color: #c9bfb1 transparent;
}

.chat-workspace .task-review-answer {
  padding-top: 16px;
  padding-bottom: 16px;
}

.chat-workspace .task-review-answer:first-child {
  padding-top: 0;
}

.chat-workspace .task-review-claim {
  padding: 12px 14px;
  border-left-width: 3px;
  border-radius: 0 12px 12px 0;
  background: var(--chat-surface-muted, #f3f0e9);
  font-size: 15px;
  line-height: 1.7;
}

@media (max-width: 767px) {
  .chat-workspace .task-review-header {
    padding: 10px 14px;
  }

  .chat-workspace .task-review-tabs {
    margin-right: 10px;
    margin-left: 10px;
  }

  .chat-workspace .task-review-content {
    padding: 14px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .chat-workspace .task-review-tab {
    transition: none;
  }
}
</style>
