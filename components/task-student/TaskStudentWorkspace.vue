<template>
  <form class="flex min-h-0 flex-1 flex-col gap-3" @submit.prevent="emit('submit')">
    <div class="flex shrink-0 gap-2 lg:hidden" aria-label="切換閱讀與作答區域">
      <button v-for="view in views" :key="view.id" type="button" :aria-pressed="mobileView === view.id"
        :aria-controls="`task-${view.id}-pane`" @click="switchView(view.id)"
        class="min-h-10 flex-1 rounded-md border px-3 py-2 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--admin-coffee)]"
        :class="mobileView === view.id ? 'border-[var(--admin-coffee)] bg-[var(--admin-coffee-soft)] text-[var(--admin-coffee)]' : 'border-[var(--admin-border)] bg-[var(--admin-surface)]'">
        {{ view.label }}<span v-if="view.id === 'questions'" class="ml-2 text-xs">{{ completedCount }}／{{ layout.questions.length }}</span>
      </button>
    </div>

    <div class="grid min-h-0 flex-1 gap-4 lg:grid-cols-2">
      <section id="task-reading-pane" aria-labelledby="task-reading-heading"
        class="min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)]"
        :class="mobileView === 'reading' ? 'flex' : 'hidden lg:flex'">
        <div class="shrink-0 border-b border-[var(--admin-border-soft)] px-5 py-3">
          <h2 id="task-reading-heading" class="text-base font-semibold">閱讀材料</h2>
        </div>
        <div ref="readingPane" tabindex="0" aria-label="閱讀材料內容" @scroll.passive="rememberScroll('reading', $event)"
          class="min-h-0 flex-1 space-y-6 overflow-y-auto overscroll-contain p-5 leading-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--admin-coffee)] md:p-6">
          <h3 class="font-serif text-xl font-bold">{{ task.title || '閱讀材料' }}</h3>
          <p v-if="eventDescription" class="whitespace-pre-wrap border-b border-[var(--admin-border-soft)] pb-5 text-[var(--admin-copy)]">{{ eventDescription }}</p>
          <p v-if="layout.introduction" class="whitespace-pre-wrap">{{ layout.introduction }}</p>
          <TaskStudentMaterials :materials="task.evaluation_payload.materials || []" />
          <p v-if="!layout.introduction && !task.evaluation_payload.materials?.length" class="text-sm text-[var(--admin-soft)]">請依右側各題提供的內容作答。</p>
        </div>
      </section>

      <section id="task-questions-pane" aria-labelledby="task-questions-heading"
        class="min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)]"
        :class="mobileView === 'questions' ? 'flex' : 'hidden lg:flex'">
        <div class="shrink-0 space-y-3 border-b border-[var(--admin-border-soft)] px-4 py-3 md:px-5">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h2 id="task-questions-heading" class="text-base font-semibold">題目與作答</h2>
            <p class="text-xs text-[var(--admin-copy)]" role="status" aria-live="polite" aria-atomic="true">已填寫 {{ completedCount }}／{{ layout.questions.length }} 題</p>
          </div>
          <nav aria-label="題目導覽" class="flex gap-2 overflow-x-auto py-1 lg:max-h-24 lg:flex-wrap lg:overflow-y-auto">
            <button v-for="item in layout.questions" :key="item.question.id" type="button" @click="jumpToQuestion(item.question.id)"
              :aria-label="`第 ${item.index + 1} 題，${completedIds.has(item.question.id) ? '已填寫' : '待填寫'}`"
              class="inline-flex min-h-9 min-w-9 shrink-0 items-center justify-center gap-1 rounded-md border px-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--admin-coffee)]"
              :class="completedIds.has(item.question.id) ? 'border-[var(--admin-coffee-muted)] bg-[var(--admin-coffee-soft)] text-[var(--admin-coffee)]' : 'border-[var(--admin-border)] bg-[var(--admin-surface)]'">
              {{ item.index + 1 }}<Icon v-if="completedIds.has(item.question.id)" name="mdi:check" class="h-3 w-3" />
            </button>
          </nav>
        </div>

        <div ref="questionsPane" tabindex="0" aria-label="題目作答內容" @scroll.passive="rememberScroll('questions', $event)"
          class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--admin-coffee)] md:px-5">
          <fieldset :disabled="disabled" class="min-w-0 space-y-7 disabled:opacity-70">
            <article v-for="item in layout.questions" :key="item.question.id" :data-question-id="item.question.id" tabindex="-1"
              class="min-w-0 scroll-mt-4 focus:outline-none focus-visible:rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--admin-coffee)]">
              <h3 class="mb-2 text-sm font-bold text-[var(--admin-coffee)]">第 {{ item.index + 1 }} 題</h3>
              <p class="whitespace-pre-wrap break-words text-base leading-8">{{ item.text }}</p>
              <TaskStudentAnswerBlock :question="item.question" :model-value="answerFor(item.question.id)?.value ?? null"
                :rationale="answerFor(item.question.id)?.rationale || ''" stacked hide-legend show-option-labels
                @update:model-value="updateAnswer(item.question, { value: $event })"
                @update:rationale="updateAnswer(item.question, { rationale: $event })" />
            </article>
            <p v-if="layout.trailingText" class="whitespace-pre-wrap text-base leading-8">{{ layout.trailingText }}</p>
          </fieldset>
        </div>

        <div class="max-h-[35%] shrink-0 space-y-3 overflow-y-auto border-t border-[var(--admin-border-soft)] px-4 py-3 md:px-5">
          <button v-if="firstIncomplete && !disabled" type="button" @click="jumpToQuestion(firstIncomplete.question.id)"
            class="text-left text-xs leading-5 text-[var(--admin-copy)] underline decoration-[var(--admin-border)] underline-offset-4 hover:text-[var(--admin-coffee)]">
            第 {{ firstIncomplete.index + 1 }} 題{{ missingParts(firstIncomplete.question.id) }}，點此前往填寫
          </button>
          <TaskStudentSubmitBar :can-submit="canSubmit && !disabled" :is-submitting="isSubmitting" :error="error" :judgement="judgement" compact />
        </div>
      </section>
    </div>
  </form>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import type { EventTask, TaskQuestion, TaskStudentAnswer } from '~/types';
import { buildTaskQuestionLayout, isTaskAnswerComplete, updateTaskAnswer } from '~/composables/useStudentTask';
import TaskStudentMaterials from './TaskStudentMaterials.vue';
import TaskStudentAnswerBlock from './TaskStudentAnswerBlock.vue';
import TaskStudentSubmitBar from './TaskStudentSubmitBar.vue';

const props = defineProps<{
  task: EventTask;
  modelValue: TaskStudentAnswer[];
  canSubmit: boolean;
  disabled: boolean;
  isSubmitting: boolean;
  error: string | null;
  judgement: Record<string, unknown> | null;
  eventDescription?: string;
}>();
const emit = defineEmits<{
  (event: 'update:modelValue', value: TaskStudentAnswer[]): void;
  (event: 'submit'): void;
}>();
type View = 'reading' | 'questions';
const views: { id: View; label: string }[] = [{ id: 'reading', label: '閱讀材料' }, { id: 'questions', label: '題目與作答' }];
const mobileView = ref<View>('reading');
const readingPane = ref<HTMLElement | null>(null);
const questionsPane = ref<HTMLElement | null>(null);
const scrollPositions = { reading: 0, questions: 0 };
const layout = computed(() => buildTaskQuestionLayout(props.task));
const answerFor = (id: string) => props.modelValue.find(answer => answer.question_id === id);
// 使用既有完整性規則；僅表示答案與理由已填寫，不判定正確性。
const completedIds = computed(() => new Set(layout.value.questions
  .filter(item => isTaskAnswerComplete([item.question], props.modelValue, props.task))
  .map(item => item.question.id)));
const completedCount = computed(() => completedIds.value.size);
const firstIncomplete = computed(() => layout.value.questions.find(item => !completedIds.value.has(item.question.id)));
const updateAnswer = (question: TaskQuestion, patch: Partial<Pick<TaskStudentAnswer, 'value' | 'rationale'>>) => {
  emit('update:modelValue', updateTaskAnswer(props.modelValue, question, patch));
};
const missingParts = (id: string) => {
  const answer = answerFor(id);
  const hasAnswer = typeof answer?.value === 'boolean' || (typeof answer?.value === 'string' && Boolean(answer.value.trim()));
  const hasReason = Boolean(answer?.rationale?.trim());
  return !hasAnswer && !hasReason ? '尚未填寫答案與理由' : !hasAnswer ? '尚未填寫答案' : !hasReason ? '尚未填寫理由' : '的答案需重新選擇';
};
function rememberScroll(view: View, event: Event) {
  const pane = event.currentTarget as HTMLElement;
  if (pane.clientHeight > 0) scrollPositions[view] = pane.scrollTop;
}
async function switchView(view: View) {
  if (view === mobileView.value) return;
  const currentPane = mobileView.value === 'reading' ? readingPane.value : questionsPane.value;
  scrollPositions[mobileView.value] = currentPane?.scrollTop || 0;
  mobileView.value = view;
  await nextTick();
  const nextPane = view === 'reading' ? readingPane.value : questionsPane.value;
  if (nextPane) nextPane.scrollTop = scrollPositions[view];
}
async function jumpToQuestion(id: string) {
  await switchView('questions');
  await nextTick();
  const pane = questionsPane.value;
  const target = pane?.querySelector<HTMLElement>(`[data-question-id="${CSS.escape(id)}"]`);
  if (!pane || !target) return;
  pane.scrollTop += target.getBoundingClientRect().top - pane.getBoundingClientRect().top - 16;
  target.focus({ preventScroll: true });
}
watch(() => props.task, () => {
  scrollPositions.reading = 0;
  scrollPositions.questions = 0;
  mobileView.value = 'reading';
  if (readingPane.value) readingPane.value.scrollTop = 0;
  if (questionsPane.value) questionsPane.value.scrollTop = 0;
});
</script>
