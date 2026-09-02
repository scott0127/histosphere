<template>
  <!-- 僅呈現舊格式中明確提供的題目。 -->
  <section class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-5 shadow-md">
    <div class="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-xs font-bold uppercase tracking-[0.18em] text-[var(--admin-coffee)]">作答題目</p>
        <h2 class="mt-1 font-serif text-xl font-bold text-[var(--admin-text)]">補充回答</h2>
      </div>
      <span class="rounded-full border border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] px-3 py-1 text-xs font-bold text-[var(--admin-coffee)]">{{ questions.length }} 題</span>
    </div>

    <div class="grid gap-4 md:grid-cols-2 md:auto-rows-fr">
      <TaskStudentItem
        v-for="question in questions"
        :key="question.id"
        :question="question"
        :model-value="answerValue(question.id)"
        @update:model-value="updateAnswer(question, $event)"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
// TaskStudentRenderer 是學生作答端的題目轉接層：
// 它不判斷答案對錯，只把不同題型的輸入整理成 TaskStudentAnswer[]。
import { computed } from 'vue';
import type { EventTask, TaskAnswerValue, TaskQuestion, TaskStudentAnswer } from '~/types';
import { normalizeTaskQuestions, updateTaskAnswer } from '~/composables/useStudentTask';

const props = defineProps<{
  task: EventTask;
  modelValue: TaskStudentAnswer[];
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: TaskStudentAnswer[]): void;
}>();

const questions = computed(() => normalizeTaskQuestions(props.task));

// 取得目前題目的答案值，給子元件做 v-model 顯示。
const answerValue = (questionId: string) => {
  return props.modelValue.find((answer) => answer.question_id === questionId)?.value ?? null;
};

// 更新單題答案時保留其他題目，讓 submit payload 可以維持結構化。
const updateAnswer = (question: TaskQuestion, value: TaskAnswerValue) => {
  emit('update:modelValue', updateTaskAnswer(props.modelValue, question, { value }));
};
</script>
