<template>
  <div class="min-w-0 space-y-3">
    <div class="grid gap-3 sm:grid-cols-2">
      <label class="block">
        <span class="admin-label">題型</span>
        <select :value="draft.type" class="admin-field mt-1 w-full px-3 py-2 text-sm" @change="changeType">
          <option v-if="!supportedType" disabled :value="draft.type">不支援的舊版題型</option>
          <option value="cloze">填空題</option>
          <option value="multiple_choice">選擇題</option>
          <option value="true_false">是非題</option>
        </select>
      </label>
      <label class="block">
        <span class="admin-label">固定題目 ID</span>
        <input :value="draft.id" class="admin-field mt-1 w-full px-3 py-2 font-mono text-sm" readonly />
      </label>
    </div>

    <span class="admin-status-chip admin-status-chip-ok">答案與理由必填</span>

    <div v-if="draft.type === 'multiple_choice'" class="space-y-2">
      <div class="flex items-center justify-between gap-2">
        <p class="admin-label">選項</p>
        <button type="button" class="admin-button-secondary inline-flex items-center gap-1 px-2 py-1 text-xs" @click="addOption">
          <Icon name="mdi:plus" class="h-4 w-4" />新增選項
        </button>
      </div>
      <div v-for="(option, index) in draft.options" :key="option.id" class="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(64px,0.4fr)_32px] items-end gap-2">
        <label class="min-w-0">
          <span class="admin-label">選項 {{ index + 1 }}</span>
          <input v-model="option.label" class="admin-field mt-1 w-full px-2 py-2 text-sm" @blur="commit" />
        </label>
        <label class="min-w-0">
          <span class="admin-label">值</span>
          <input v-model="option.value" class="admin-field mt-1 w-full px-2 py-2 font-mono text-sm" @blur="commit" />
        </label>
        <button type="button" class="admin-button-danger flex h-9 w-8 items-center justify-center" :aria-label="`刪除選項 ${index + 1}`" title="刪除選項" @click="removeOption(index)">
          <Icon name="mdi:close" class="h-4 w-4" />
        </button>
      </div>
    </div>

    <label v-if="draft.type === 'true_false'" class="block">
      <span class="admin-label">參考答案</span>
      <select v-model="correctAnswerText" class="admin-field mt-1 w-full px-3 py-2 text-sm" @change="commit">
        <option value="true">是</option>
        <option value="false">否</option>
      </select>
    </label>
    <fieldset v-else-if="draft.type === 'multiple_choice'" class="space-y-2">
      <legend class="admin-label mb-1">可接受的正確選項</legend>
      <label v-for="option in draft.options" :key="option.id" class="admin-copy flex min-w-0 items-start gap-2 text-sm">
        <input type="checkbox" class="admin-check mt-1" :checked="acceptedOptions.includes(option.value)" @change="toggleAnswer(option.value, $event)" />
        <span class="break-words">{{ option.label || option.id }} <span class="font-mono">({{ option.value }})</span></span>
      </label>
    </fieldset>
    <label v-else class="block">
      <span class="admin-label">參考答案／可接受別名（每行一個）</span>
      <textarea v-model="correctAnswerText" rows="3" class="admin-textarea mt-1 w-full px-3 py-2 text-sm leading-6" @blur="commit" />
    </label>

    <label class="block">
      <span class="admin-label">理由通過標準 *</span>
      <textarea v-model="draft.reasoning_criteria" rows="4" required class="admin-textarea mt-1 w-full px-3 py-2 text-sm leading-6" @blur="commit" />
    </label>

    <details>
      <summary class="admin-label cursor-pointer">內部來源文字</summary>
      <textarea v-model="draft.source_text" aria-label="內部來源文字" rows="3" class="admin-textarea mt-2 w-full px-3 py-2 text-sm leading-6" @blur="commit" />
    </details>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { ErrorElicitationQuestionType, TaskQuestion } from '~/types';
import { answersFromText, changeTaskQuestionType } from '~/composables/useTaskControl';

const props = defineProps<{ question: TaskQuestion }>();
const emit = defineEmits<{ (event: 'update', question: TaskQuestion): void }>();
const cloneQuestion = (question: TaskQuestion) => ({ ...question, options: Array.isArray(question.options) ? question.options.filter(Boolean).map((option) => ({ ...option })) : [] });
const answerToText = (value: unknown) => Array.isArray(value) ? value.join('\n') : String(value ?? '');
const draft = ref(cloneQuestion(props.question));
const correctAnswerText = ref(answerToText(props.question.correct_answer));
const supportedType = computed(() => ['cloze', 'multiple_choice', 'true_false'].includes(draft.value.type));
const acceptedOptions = computed(() => correctAnswerText.value.split('\n').filter(Boolean));

watch(() => props.question, (question) => {
  draft.value = cloneQuestion(question);
  correctAnswerText.value = answerToText(question.correct_answer);
}, { deep: true });

const commit = () => {
  emit('update', {
    ...draft.value,
    required: true,
    correct_answer: draft.value.type === 'true_false' ? correctAnswerText.value === 'true' : answersFromText(correctAnswerText.value),
    options: draft.value.type === 'multiple_choice' ? draft.value.options : [],
  });
};

const changeType = (event: Event) => {
  const type = (event.target as HTMLSelectElement).value as ErrorElicitationQuestionType;
  draft.value = cloneQuestion(changeTaskQuestionType(draft.value, type));
  correctAnswerText.value = answerToText(draft.value.correct_answer);
  commit();
};

const addOption = () => {
  const ids = new Set(draft.value.options.map((option) => option.id));
  let next = draft.value.options.length + 1;
  while (ids.has(`opt-${next}`)) next += 1;
  draft.value.options.push({ id: `opt-${next}`, label: '', value: '' });
  commit();
};

const removeOption = (index: number) => {
  const removed = draft.value.options.splice(index, 1)[0];
  correctAnswerText.value = acceptedOptions.value.filter((answer) => answer !== removed?.value).join('\n');
  commit();
};

const toggleAnswer = (value: string, event: Event) => {
  const checked = (event.target as HTMLInputElement).checked;
  correctAnswerText.value = (checked ? [...new Set([...acceptedOptions.value, value])] : acceptedOptions.value.filter((answer) => answer !== value)).join('\n');
  commit();
};
</script>
