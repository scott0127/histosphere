<template>
  <div class="space-y-6 text-[var(--admin-text)]">
    <p class="text-sm leading-7 text-[var(--admin-copy)]">
      請逐題選擇最符合你想法的選項，每題選一個答案。
    </p>

    <fieldset
      v-for="question in questions"
      :id="question.id"
      :key="question.id"
      :disabled="disabled"
      class="min-w-0 rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] px-4 pb-5 pt-3 disabled:opacity-70 sm:px-6 sm:pb-6"
    >
      <legend class="px-2 text-base font-bold leading-7 sm:text-lg">
        {{ question.title }}
      </legend>

      <div class="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-5 sm:gap-3">
        <label
          v-for="option in options"
          :key="option.value"
          :for="`${question.id}_${option.value}`"
          class="flex min-h-12 items-center gap-3 rounded-lg border px-4 py-3 text-sm font-semibold transition-colors focus-within:ring-2 focus-within:ring-[var(--admin-coffee-muted)] focus-within:ring-offset-2 sm:min-h-24 sm:flex-col sm:justify-center sm:gap-2 sm:px-2 sm:text-center"
          :class="[
            modelValue[question.id] === option.value
              ? 'border-[var(--admin-coffee)] bg-[var(--admin-coffee-soft)] text-[var(--admin-text)]'
              : 'border-[var(--admin-border-soft)] bg-[var(--admin-surface-muted)] text-[var(--admin-copy)]',
            disabled ? 'cursor-not-allowed' : 'cursor-pointer hover:border-[var(--admin-coffee-muted)]',
          ]"
        >
          <input
            :id="`${question.id}_${option.value}`"
            type="radio"
            :name="question.id"
            :value="option.value"
            :checked="modelValue[question.id] === option.value"
            :disabled="disabled"
            class="h-4 w-4 shrink-0 accent-[var(--admin-coffee)]"
            @change="selectAnswer(question.id, option.value)"
          >
          <span class="leading-6">{{ option.label }}</span>
        </label>
      </div>
    </fieldset>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  modelValue: Record<string, number | null>;
  disabled: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, number | null>];
}>();

const questions = [
  { id: 'engagement_1', title: 'Pseudo 題 1' },
  { id: 'engagement_2', title: 'Pseudo 題 2' },
  { id: 'engagement_3', title: 'Pseudo 題 3' },
];

const options = [
  { value: 1, label: '非常不同意' },
  { value: 2, label: '不同意' },
  { value: 3, label: '普通' },
  { value: 4, label: '同意' },
  { value: 5, label: '非常同意' },
];

function selectAnswer(questionId: string, value: number) {
  if (props.disabled) return;
  emit('update:modelValue', { ...props.modelValue, [questionId]: value });
}
</script>
