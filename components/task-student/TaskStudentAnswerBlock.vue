<template>
  <fieldset class="my-5 min-w-0 border-y border-[var(--admin-border-soft)] py-4 text-base leading-7" :aria-label="`${question.id} 作答`">
    <legend class="px-1 font-mono text-sm font-bold text-[var(--admin-coffee)]">{{ question.id }}</legend>
    <div class="grid min-w-0 gap-4 md:grid-cols-2">
      <div class="min-w-0">
        <label v-if="question.type === 'cloze'" class="block text-sm font-bold text-[var(--admin-text)]">
          答案
          <input
            :value="typeof modelValue === 'string' ? modelValue : ''"
            :aria-label="`${question.id} 答案`"
            required
            class="mt-2 block w-full min-w-0 rounded-md border border-[var(--admin-border)] bg-[var(--admin-surface)] px-3 py-2 text-base font-normal text-[var(--admin-text)] outline-none focus:ring-2 focus:ring-[var(--admin-focus)]"
            @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <fieldset v-else class="min-w-0" :aria-label="`${question.id} 答案`">
          <legend class="text-sm font-bold text-[var(--admin-text)]">答案</legend>
          <div class="mt-2 grid gap-2" :class="question.type === 'true_false' ? 'grid-cols-2' : ''">
            <label
              v-for="option in options"
              :key="option.id"
              class="flex min-w-0 cursor-pointer items-start gap-3 rounded-md border border-[var(--admin-border)] px-3 py-2 text-base text-[var(--admin-text)] hover:bg-[var(--admin-surface-muted)]"
              :class="modelValue === option.value ? 'bg-[var(--admin-coffee-soft)]' : 'bg-[var(--admin-surface)]'"
            >
              <input
                type="radio"
                :name="`${question.id}-answer`"
                :value="String(option.value)"
                :checked="modelValue === option.value"
                required
                class="mt-1.5 h-4 w-4 shrink-0 accent-[var(--admin-coffee)]"
                @change="emit('update:modelValue', option.value)"
              />
              <span class="min-w-0 whitespace-pre-wrap break-words">{{ option.label }}</span>
            </label>
          </div>
        </fieldset>
      </div>
      <label class="block min-w-0 text-sm font-bold text-[var(--admin-text)]">
        作答理由
        <textarea
          :value="rationale"
          :aria-label="`${question.id} 作答理由`"
          required
          rows="3"
          class="mt-2 block min-h-28 w-full min-w-0 resize-y rounded-md border border-[var(--admin-border)] bg-[var(--admin-surface)] px-3 py-2 text-base font-normal leading-7 text-[var(--admin-text)] outline-none focus:ring-2 focus:ring-[var(--admin-focus)]"
          @input="emit('update:rationale', ($event.target as HTMLTextAreaElement).value)"
        />
      </label>
    </div>
  </fieldset>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { TaskAnswerValue, TaskQuestion } from '~/types';

const props = defineProps<{
  question: TaskQuestion;
  modelValue: TaskAnswerValue;
  rationale: string;
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: TaskAnswerValue): void;
  (event: 'update:rationale', value: string): void;
}>();

const options = computed(() => props.question.type === 'true_false'
  ? [{ id: 'true', label: '是', value: true }, { id: 'false', label: '否', value: false }]
  : props.question.options || []);
</script>
