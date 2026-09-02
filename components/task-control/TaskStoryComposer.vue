<template>
  <div class="min-w-0">
    <textarea
      ref="textInput"
      :value="modelValue"
      aria-label="完整任務題文"
      rows="18"
      class="admin-textarea w-full resize-y px-3 py-3 text-sm leading-7"
      @input="updateText"
      @select="captureSelection"
      @click="captureSelection"
      @keyup="captureSelection"
      @focus="captureSelection"
    />
    <div v-if="markerIds.length" class="mt-2 flex flex-wrap gap-2">
      <button
        v-for="(id, index) in markerIds"
        :key="`${id}-${index}`"
        type="button"
        class="admin-button-secondary inline-flex items-center gap-1 px-2 py-1 font-mono text-xs"
        :aria-pressed="selectedQuestionId === id"
        :title="`定位作答標記 ${id}`"
        @click="locateQuestion(id)"
      >
        <Icon :name="selectedQuestionId === id ? 'mdi:tag' : 'mdi:tag-outline'" class="h-4 w-4" />
        {{ id }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { blankIdsInDisplayText } from '~/composables/useTaskControl';

const props = defineProps<{ modelValue: string; selectedQuestionId?: string | null }>();
const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void;
  (event: 'selection-change', selection: { start: number; end: number }): void;
  (event: 'select-question', questionId: string): void;
}>();
const textInput = ref<HTMLTextAreaElement | null>(null);
const markerIds = computed(() => blankIdsInDisplayText(props.modelValue || ''));
const captureSelection = () => {
  const input = textInput.value;
  if (input) emit('selection-change', { start: input.selectionStart, end: input.selectionEnd });
};
const updateText = (event: Event) => {
  emit('update:modelValue', (event.target as HTMLTextAreaElement).value);
  captureSelection();
};
const locateQuestion = (id: string) => {
  emit('select-question', id);
  const marker = Array.from(props.modelValue.matchAll(/\{\{\s*blank:([a-zA-Z0-9_-]+)\s*\}\}/g)).find((match) => match[1] === id);
  if (!marker || !textInput.value) return;
  textInput.value.focus();
  textInput.value.setSelectionRange(marker.index!, marker.index! + marker[0].length);
  captureSelection();
};
</script>
