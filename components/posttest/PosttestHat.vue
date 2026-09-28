<template>
  <div class="grid items-start gap-6 text-[var(--admin-text)] lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-8">
    <aside
      aria-labelledby="posttest-material-title"
      class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface-muted)] p-5 sm:p-7 lg:sticky lg:top-6"
    >
      <p class="text-xs font-bold tracking-[0.16em] text-[var(--admin-coffee)]">閱讀材料</p>
      <h2 id="posttest-material-title" class="mt-3 font-serif text-2xl font-bold">
        示範材料
      </h2>
      <div class="mt-5 space-y-4 border-t border-[var(--admin-border-soft)] pt-5 text-base leading-8 text-[var(--admin-copy)]">
        <p>此區為示範材料，供測試閱讀與作答流程。</p>
        <p>請閱讀材料後，依序填寫各題的回答與理由。</p>
      </div>
    </aside>

    <div class="min-w-0 space-y-6">
      <div
        v-for="question in questions"
        :key="question.id"
        class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-5 sm:p-7"
      >
        <label :for="question.id" class="block text-base font-bold leading-7 sm:text-lg">
          {{ question.title }}
        </label>
        <p :id="`${question.id}_hint`" class="mt-2 text-sm leading-7 text-[var(--admin-copy)]">
          請說明你的判斷與理由。
        </p>
        <textarea
          :id="question.id"
          :name="question.id"
          :value="modelValue[question.id] ?? ''"
          :disabled="disabled"
          :aria-describedby="`${question.id}_hint`"
          rows="6"
          maxlength="10000"
          placeholder="在這裡填寫你的回答…"
          class="mt-4 block min-h-44 w-full resize-y rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] px-4 py-3 text-base leading-7 text-[var(--admin-text)] outline-none transition-colors placeholder:text-[var(--admin-soft)] focus:border-[var(--admin-coffee)] focus:ring-2 focus:ring-[var(--admin-focus)] disabled:cursor-not-allowed disabled:bg-[var(--admin-surface-muted)] disabled:opacity-70"
          @input="updateAnswer(question.id, $event)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  modelValue: Record<string, string>;
  disabled: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, string>];
}>();

const questions = [
  { id: 'hat_1', title: 'Pseudo 題 1' },
  { id: 'hat_2', title: 'Pseudo 題 2' },
];

function updateAnswer(questionId: string, event: Event) {
  if (props.disabled) return;
  const value = (event.target as HTMLTextAreaElement).value;
  emit('update:modelValue', { ...props.modelValue, [questionId]: value });
}
</script>
