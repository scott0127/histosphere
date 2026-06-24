<template>
  <!-- 故事內嵌空格：依題型在句子中呈現輸入、選擇或是非控制。 -->
  <span class="inline-flex align-middle">
    <input
      v-if="question.type === 'short_answer' || question.type === 'cloze'"
      :value="stringValue"
      :aria-label="question.prompt"
      :title="question.prompt"
      class="mx-1 inline-block h-10 min-w-[7.5rem] max-w-[14rem] rounded-[6px] border border-[rgba(123,93,75,0.48)] bg-transparent px-2.5 text-center text-[0.95em] font-black text-[#a62f2a] shadow-[inset_0_-1px_0_rgba(74,49,39,0.24)] outline-none transition placeholder:text-[#a62f2a]/50 hover:border-[var(--admin-coffee)] focus:border-[var(--admin-line)] focus:bg-[var(--admin-surface-muted)] focus:ring-4 focus:ring-[var(--admin-focus)]"
      :placeholder="question.placeholder || '？'"
      @input="emitString"
    />

    <span
      v-else-if="question.type === 'multiple_choice'"
      class="relative mx-1 inline-flex h-11 min-w-[8rem] align-middle"
      @keydown.escape="isChoiceOpen = false"
    >
      <button
        type="button"
        :aria-label="question.prompt"
        :title="question.prompt"
        class="inline-flex h-10 w-full min-w-[8rem] items-center justify-between gap-2 rounded-[6px] border px-3 text-center text-[0.95em] font-black text-[#a62f2a] outline-none transition focus:ring-4 focus:ring-[#a62f2a]/10"
        :class="isChoiceOpen ? 'border-[var(--admin-line)] bg-[var(--admin-surface-muted)] shadow-[0_8px_18px_rgba(47,41,36,0.12),inset_0_-1px_0_rgba(47,41,36,0.18)]' : 'border-[rgba(123,93,75,0.48)] bg-transparent shadow-[inset_0_-1px_0_rgba(47,41,36,0.2)] hover:border-[var(--admin-coffee)] focus:border-[var(--admin-line)] focus:bg-[var(--admin-surface-muted)]'"
        @click="isChoiceOpen = !isChoiceOpen"
      >
        <span class="min-w-0 flex-1 truncate">{{ selectedChoiceLabel }}</span>
        <Icon name="mdi:chevron-down" class="h-4 w-4 shrink-0 transition" :class="isChoiceOpen ? 'rotate-180' : ''" />
      </button>
      <span
        v-if="isChoiceOpen"
        class="absolute left-1/2 top-[calc(100%+0.45rem)] z-40 grid min-w-[11rem] -translate-x-1/2 overflow-hidden rounded-[10px] border border-[var(--admin-border)] bg-[var(--admin-surface)] p-1 text-left shadow-[0_18px_36px_rgba(47,41,36,0.16),inset_0_1px_0_rgba(255,255,255,0.68)]"
      >
        <button
          v-for="option in choiceOptions"
          :key="option.id"
          type="button"
          class="group flex min-h-11 items-center justify-between gap-3 whitespace-nowrap rounded-[7px] px-3.5 py-2 text-left text-base font-black transition focus:outline-none"
          :class="isChoiceSelected(option.value) ? 'bg-[var(--admin-coffee-soft)] text-[#7f2b27] shadow-[inset_0_0_0_1px_rgba(127,43,39,0.08)]' : 'text-[#a62f2a] hover:bg-[var(--admin-surface-muted)] hover:text-[#7f2b27] focus:bg-[var(--admin-surface-muted)]'"
          @click="emitChoice(option.value)"
        >
          <span>{{ option.label }}</span>
          <Icon
            name="mdi:check"
            class="h-4 w-4 transition"
            :class="isChoiceSelected(option.value) ? 'opacity-100' : 'opacity-0 group-hover:opacity-35'"
          />
        </button>
      </span>
    </span>

    <span v-else class="mx-1 inline-flex h-10 overflow-hidden rounded-[6px] border border-[rgba(123,93,75,0.48)] bg-transparent align-middle shadow-[inset_0_-1px_0_rgba(47,41,36,0.2)] transition hover:border-[var(--admin-coffee)]">
      <button
        type="button"
        class="min-w-14 px-3 text-sm font-black transition"
        :class="modelValue === true ? 'bg-[#a62f2a] text-white' : 'text-[#a62f2a] hover:bg-[#a62f2a]/10'"
        :aria-label="`${question.prompt}：是`"
        @click="$emit('update:modelValue', true)"
      >
        是
      </button>
      <button
        type="button"
        class="min-w-14 border-l border-[#9f3d33]/20 px-3 text-sm font-black transition"
        :class="modelValue === false ? 'bg-[#a62f2a] text-white' : 'text-[#a62f2a] hover:bg-[#a62f2a]/10'"
        :aria-label="`${question.prompt}：否`"
        @click="$emit('update:modelValue', false)"
      >
        否
      </button>
    </span>
  </span>
</template>

<script setup lang="ts">
// TaskStudentInlineBlank 是故事挖洞的最小互動單位。
// 它只負責單個空格的輸入狀態，答案整理交給父層 TaskStudentStory。
import { computed, ref } from 'vue';
import type { TaskAnswerValue, TaskQuestion } from '~/types';

const props = defineProps<{
  question: TaskQuestion;
  modelValue: TaskAnswerValue;
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: TaskAnswerValue): void;
}>();

const stringValue = computed(() => typeof props.modelValue === 'string' ? props.modelValue : '');
const isChoiceOpen = ref(false);
const choiceOptions = computed(() => props.question.options || []);
const selectedChoiceLabel = computed(() => {
  if (typeof props.modelValue !== 'string' || !props.modelValue) return '？';
  return choiceOptions.value.find((option) => option.value === props.modelValue)?.label || props.modelValue;
});

// 下拉選單用選中狀態提升可讀性，避免學生重新打開時不知道已選哪個答案。
const isChoiceSelected = (value: string) => props.modelValue === value;

// input 與 select 共用字串更新邏輯。
const emitString = (event: Event) => {
  emit('update:modelValue', (event.target as HTMLInputElement).value);
};

// 自訂選單避免瀏覽器原生 select 樣式破壞歷史紙感介面。
const emitChoice = (value: string) => {
  emit('update:modelValue', value);
  isChoiceOpen.value = false;
};
</script>
