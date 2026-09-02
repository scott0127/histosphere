<template>
  <section class="admin-answer-key-panel p-4">
    <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
      <div>
        <p class="admin-kicker">Answer key</p>
        <h4 class="admin-heading mt-1 text-lg font-bold">正解預覽</h4>
      </div>
      <span class="admin-code-badge">{{ questions.length }} 題</span>
    </div>

    <div class="admin-answer-key-story mt-4">
      <template v-for="segment in segments" :key="segment.key">
        <span v-if="segment.type === 'text'">{{ segment.text }}</span>
        <span
          v-else
          :class="[
            'admin-answer-key-control',
            !segment.question ? 'admin-answer-key-control-missing' : ''
          ]"
          :title="segment.question?.reasoning_criteria || '尚無理由通過標準'"
        >
          <span class="admin-answer-key-type">{{ segment.label }}</span>
          <strong>{{ answerText(segment.question) }}</strong>
          <span v-if="segment.question?.reasoning_criteria" class="mt-1 block max-w-full whitespace-pre-wrap break-words text-xs font-normal">{{ segment.question.reasoning_criteria }}</span>
        </span>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { EventTask, TaskQuestion } from '~/types';

type TextSegment = {
  type: 'text';
  key: string;
  text: string;
};

type AnswerSegment = {
  type: 'answer';
  key: string;
  blankId: string;
  label: string;
  question: TaskQuestion | null;
};

type PreviewSegment = TextSegment | AnswerSegment;

const props = defineProps<{
  task: EventTask;
  questions: TaskQuestion[];
}>();

const blankPattern = /\{\{\s*blank:([a-zA-Z0-9_-]+)\s*\}\}/g;

const questionTypeLabels: Record<TaskQuestion['type'], string> = {
  short_answer: '不支援的舊版題型',
  cloze: '填空題',
  multiple_choice: '選擇題',
  true_false: '是非題',
};

const questionByBlankId = computed(() => {
  const map = new Map<string, TaskQuestion>();
  for (const question of props.questions) {
    map.set(question.id, question);
  }
  return map;
});

const labelForQuestion = (question: TaskQuestion | null, blankId: string) => {
  if (!question) return '未連結題目';
  const index = props.questions.findIndex((item) => item.id === question.id || item.blank_id === blankId);
  return `${questionTypeLabels[question.type] || '題目'}${index >= 0 ? index + 1 : ''}`;
};

const answerText = (question: TaskQuestion | null) => {
  if (!question) return '未設定';
  const value = question.correct_answer;
  if (value === undefined || value === null || value === '') return '未設定';
  if (question.type === 'multiple_choice') {
    const values = Array.isArray(value) ? value : [value];
    return values.map((item) => question.options?.find((option) => option.value === item)?.label || String(item)).join(' / ');
  }
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (Array.isArray(value)) return value.join(' / ');
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};

const segments = computed<PreviewSegment[]>(() => {
  const displayText = props.task.error_elicitation_task_full_text || '';
  const parsed: PreviewSegment[] = [];
  let lastIndex = 0;
  let textIndex = 0;
  let answerIndex = 0;

  for (const match of displayText.matchAll(blankPattern)) {
    const token = match[0];
    const blankId = match[1];
    if (!blankId) continue;
    const offset = match.index ?? 0;
    if (offset > lastIndex) {
      parsed.push({
        type: 'text',
        key: `text-${textIndex}`,
        text: displayText.slice(lastIndex, offset),
      });
      textIndex += 1;
    }

    const question = questionByBlankId.value.get(blankId) || null;
    parsed.push({
      type: 'answer',
      key: `answer-${answerIndex}-${blankId}`,
      blankId,
      question,
      label: labelForQuestion(question, blankId),
    });
    answerIndex += 1;
    lastIndex = offset + token.length;
  }

  if (lastIndex < displayText.length || parsed.length === 0) {
    parsed.push({
      type: 'text',
      key: `text-${textIndex}`,
      text: displayText.slice(lastIndex),
    });
  }

  return parsed;
});
</script>

<style scoped>
.admin-answer-key-control {
  grid-auto-flow: row;
  grid-template-columns: minmax(0, 1fr);
  min-width: 0;
  max-width: 100%;
  margin: 0.5rem 0;
  padding: 0.75rem;
  white-space: normal;
  overflow-wrap: anywhere;
}

.admin-answer-key-control strong {
  line-height: 1.5;
}

.admin-answer-key-type {
  border-right: 0;
  padding-right: 0;
}
</style>
