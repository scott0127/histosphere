<template>
  <!-- 歷史故事區塊：學生端直接在故事中的關鍵知識空格作答。 -->
  <article class="relative overflow-hidden rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface-muted)] p-4 shadow-[var(--admin-shadow-soft)] md:p-5">
    <div class="space-y-5">
      <div class="flex flex-col gap-3 rounded-[10px] border border-[var(--admin-border-soft)] bg-[var(--admin-surface)] px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.58)] md:flex-row md:items-end md:justify-between">
        <div>
          <p class="text-xs font-bold text-[var(--admin-coffee)]">Error-Elicitation Task</p>
          <h2 class="mt-2 break-words font-serif text-2xl font-bold text-[var(--admin-text)]">{{ task.title || 'Error-Elicitation Task' }}</h2>
        </div>
        <span class="rounded-full border border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] px-3 py-1 text-xs font-bold text-[var(--admin-coffee)]">
          {{ newFormat ? `${questions.length} 題` : '補上關鍵知識' }}
        </span>
      </div>

      <TaskStudentMaterials :materials="task.evaluation_payload.materials || []" />

      <div class="relative rounded-[10px] border border-[var(--admin-border-soft)] bg-[var(--admin-surface)] p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.66),0_10px_24px_rgba(47,41,36,0.04)] md:p-6">
        <div v-if="newFormat" class="min-w-0 break-words text-lg leading-9 text-[var(--admin-text)]">
          <template v-for="(segment, index) in storySegments" :key="index">
            <span v-if="segment.type === 'text'" class="whitespace-pre-wrap">{{ segment.text }}</span>
            <TaskStudentAnswerBlock
              v-else
              :question="segment.question"
              :model-value="answerValue(segment.question.id)"
              :rationale="answerRationale(segment.question.id)"
              @update:model-value="updateAnswer(segment.question, $event)"
              @update:rationale="updateRationale(segment.question, $event)"
            />
          </template>
        </div>
        <p v-else class="whitespace-pre-wrap text-xl font-medium leading-10 text-[var(--admin-text)] md:text-2xl md:leading-[2.35]">
          <template v-for="(segment, index) in storySegments" :key="index">
            <span v-if="segment.type === 'text'">{{ segment.text }}</span>
            <TaskStudentInlineBlank
              v-else
              :question="segment.question"
              :model-value="answerValue(segment.question.id)"
              @update:model-value="updateAnswer(segment.question, $event)"
            />
          </template>
        </p>
      </div>

      <div v-if="scenarioQuestions.length" class="grid gap-3">
        <article
          v-for="question in scenarioQuestions"
          :key="question.id"
          class="grid min-h-[124px] gap-4 rounded-[10px] border border-[var(--admin-border-soft)] bg-[var(--admin-surface)] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.45)] md:grid-cols-[minmax(0,1fr)_auto] md:items-center"
        >
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.16em] text-[var(--admin-coffee)]">故事後的情境判斷</p>
            <p class="mt-2 text-lg font-semibold leading-8 text-[var(--admin-text)]">
              {{ question.prompt }}
            </p>
          </div>
          <TaskStudentInlineBlank
            :question="question"
            :model-value="answerValue(question.id)"
            @update:model-value="updateAnswer(question, $event)"
          />
        </article>
      </div>

    </div>
  </article>
</template>

<script setup lang="ts">
// TaskStudentStory 呈現故事挖洞，並把內嵌空格答案整理成 TaskStudentAnswer[]。
import { computed } from 'vue';
import type { EventTask, TaskAnswerValue, TaskQuestion, TaskStudentAnswer } from '~/types';
import { buildTaskStorySegments, isErrorElicitationTask, normalizeTaskQuestions, updateTaskAnswer } from '~/composables/useStudentTask';
import TaskStudentAnswerBlock from './TaskStudentAnswerBlock.vue';
import TaskStudentMaterials from './TaskStudentMaterials.vue';

const props = defineProps<{
  task: EventTask;
  modelValue?: TaskStudentAnswer[];
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: TaskStudentAnswer[]): void;
}>();

const storySegments = computed(() => buildTaskStorySegments(props.task));
const newFormat = computed(() => isErrorElicitationTask(props.task));
const questions = computed(() => normalizeTaskQuestions(props.task));
const inlineQuestionIds = computed(() => {
  const ids = new Set<string>();
  for (const segment of storySegments.value) {
    if (segment.type === 'blank') ids.add(segment.question.id);
  }
  return ids;
});
const scenarioQuestions = computed(() => {
  if (newFormat.value) return [];
  return normalizeTaskQuestions(props.task).filter((question) => {
    return question.type === 'true_false' && !inlineQuestionIds.value.has(question.id);
  });
});

// 取得目前空格答案。
const answerValue = (questionId: string) => {
  return props.modelValue?.find((answer) => answer.question_id === questionId)?.value ?? null;
};

// 更新故事中單一空格答案，並維持答案陣列穩定。
const updateAnswer = (question: TaskQuestion, value: TaskAnswerValue) => {
  emit('update:modelValue', updateTaskAnswer(props.modelValue || [], question, { value }));
};

const answerRationale = (questionId: string) => {
  return props.modelValue?.find((answer) => answer.question_id === questionId)?.rationale ?? '';
};

const updateRationale = (question: TaskQuestion, rationale: string) => {
  emit('update:modelValue', updateTaskAnswer(props.modelValue || [], question, { rationale }));
};
</script>
