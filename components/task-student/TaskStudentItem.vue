<template>
  <!-- 單題輸入元件：依題型切換輸入控制，避免學生端看到 JSON 或研究欄位。 -->
  <article class="flex h-full min-h-[190px] flex-col rounded-[10px] border border-[var(--admin-border-soft)] bg-[var(--admin-surface)] p-4">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p class="text-xs font-bold uppercase tracking-[0.12em] text-[var(--admin-coffee)]">{{ typeLabel }}</p>
        <h3 class="mt-1 whitespace-pre-wrap text-base font-bold leading-7 text-[var(--admin-text)]">
          {{ question.prompt }}
        </h3>
      </div>
      <span v-if="question.required !== false" class="shrink-0 rounded-full border border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] px-2.5 py-1 text-xs font-bold text-[var(--admin-coffee)]">
        必填
      </span>
    </div>

    <p v-if="question.source_text" class="mt-3 rounded-[8px] border border-[var(--admin-border-soft)] bg-[var(--admin-surface-muted)] px-3 py-2 text-sm leading-6 text-[var(--admin-copy)]">
      {{ question.source_text }}
    </p>

    <textarea
      v-if="question.type === 'short_answer'"
      :value="stringValue"
      rows="5"
      class="mt-3 min-h-[112px] w-full flex-1 resize-y rounded-[8px] border border-[var(--admin-border)] bg-[var(--admin-surface)] px-4 py-3 text-base leading-7 text-[var(--admin-text)] outline-none transition placeholder:text-[var(--admin-soft)] focus:bg-[var(--admin-surface)] focus:ring-2 focus:ring-[var(--admin-focus)]"
      :placeholder="question.placeholder || '請輸入你的回答...'"
      @input="emitString"
    />

    <input
      v-else-if="question.type === 'cloze'"
      :value="stringValue"
      class="mt-3 w-full rounded-[8px] border border-[var(--admin-border)] bg-[var(--admin-surface)] px-4 py-3 text-base text-[var(--admin-text)] outline-none transition placeholder:text-[var(--admin-soft)] focus:bg-[var(--admin-surface)] focus:ring-2 focus:ring-[var(--admin-focus)]"
      :placeholder="question.placeholder || '請填入答案...'"
      @input="emitString"
    />

    <div v-else-if="question.type === 'multiple_choice'" class="mt-3 grid gap-2">
      <label
        v-for="option in question.options"
        :key="option.id"
        class="flex cursor-pointer items-center gap-3 rounded-[8px] border border-[var(--admin-border-soft)] bg-[var(--admin-surface)] px-4 py-3 text-sm font-semibold text-[var(--admin-text)] transition hover:border-[var(--admin-coffee-muted)] hover:bg-[var(--admin-surface-muted)]"
      >
        <input
          type="radio"
          :name="question.id"
          :value="option.value"
          :checked="modelValue === option.value"
          class="h-4 w-4 accent-[var(--admin-coffee)]"
          @change="$emit('update:modelValue', option.value)"
        />
        {{ option.label }}
      </label>
    </div>

    <div v-else class="mt-3 grid gap-2 sm:grid-cols-2">
      <label class="flex cursor-pointer items-center gap-3 rounded-[8px] border border-[var(--admin-border-soft)] bg-[var(--admin-surface)] px-4 py-3 text-sm font-semibold text-[var(--admin-text)] transition hover:border-[var(--admin-coffee-muted)] hover:bg-[var(--admin-surface-muted)]">
        <input
          type="radio"
          :name="question.id"
          :checked="modelValue === true"
          class="h-4 w-4 accent-[var(--admin-coffee)]"
          @change="$emit('update:modelValue', true)"
        />
        是
      </label>
      <label class="flex cursor-pointer items-center gap-3 rounded-[8px] border border-[var(--admin-border-soft)] bg-[var(--admin-surface)] px-4 py-3 text-sm font-semibold text-[var(--admin-text)] transition hover:border-[var(--admin-coffee-muted)] hover:bg-[var(--admin-surface-muted)]">
        <input
          type="radio"
          :name="question.id"
          :checked="modelValue === false"
          class="h-4 w-4 accent-[var(--admin-coffee)]"
          @change="$emit('update:modelValue', false)"
        />
        否
      </label>
    </div>
  </article>
</template>

<script setup lang="ts">
// TaskStudentItem 負責單一題目的輸入 UI；答案值統一往上交給 TaskStudentRenderer。
import { computed } from 'vue';
import type { TaskAnswerValue, TaskQuestion } from '~/types';

const props = defineProps<{
  question: TaskQuestion;
  modelValue: TaskAnswerValue;
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: TaskAnswerValue): void;
}>();

const typeLabel = computed(() => {
  if (props.question.type === 'cloze') return '填空題';
  if (props.question.type === 'multiple_choice') return '選擇題';
  if (props.question.type === 'true_false') return '是非題';
  return '簡答題';
});

const stringValue = computed(() => typeof props.modelValue === 'string' ? props.modelValue : '');

// textarea/input 共用的字串答案更新。
const emitString = (event: Event) => {
  emit('update:modelValue', (event.target as HTMLInputElement | HTMLTextAreaElement).value);
};
</script>
