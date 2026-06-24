<template>
  <section class="admin-story-composer mt-1">
    <div class="admin-story-token-editor">
      <template v-for="segment in segments" :key="segment.key">
        <span
          v-if="segment.type === 'text'"
          :contenteditable="true"
          :data-placeholder="segmentPlaceholder(segment)"
          :class="[
            'admin-story-text-segment',
            !segment.text ? 'admin-story-text-segment-empty' : ''
          ]"
          @input="updateTextSegment(segment, $event)"
          @click="captureSelection(segment, $event)"
          @focus="captureSelection(segment, $event)"
          @keyup="captureSelection(segment, $event)"
          @mouseup="captureSelection(segment, $event)"
          @paste="pastePlainText(segment, $event)"
        >{{ segment.text }}</span>

        <span
          v-else
          :class="[
            'admin-story-token-wrap',
            tokenIsActive(segment.id) ? 'admin-story-token-wrap-active' : '',
            !questionForBlank(segment.id) ? 'admin-story-token-wrap-missing' : ''
          ]"
        >
          <button
            type="button"
            :class="[
              'admin-story-token-chip inline-flex h-12 min-w-32 items-center justify-center px-4 text-center leading-none',
              tokenIsActive(segment.id) ? 'admin-story-token-chip-active' : '',
              !questionForBlank(segment.id) ? 'admin-story-token-chip-missing' : ''
            ]"
            :title="tokenTitle(segment.id)"
            @click="$emit('select-question', questionIdForBlank(segment.id))"
          >
            <strong class="flex h-full w-full items-center justify-center text-center text-[0.95rem] font-extrabold leading-none text-[var(--admin-text)]">
              {{ tokenLabel(segment.id) }}
            </strong>
          </button>
          <button
            type="button"
            class="admin-story-token-remove"
            title="刪除此題與文中標記"
            @click="$emit('delete-question', questionIdForBlank(segment.id))"
          >
            <Icon name="mdi:close" class="h-3.5 w-3.5" />
          </button>
        </span>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { TaskQuestion } from '~/types';

type StorySelection = {
  start: number;
  end: number;
};

type TextSegment = {
  type: 'text';
  key: string;
  text: string;
  start: number;
  end: number;
  index: number;
};

type TokenSegment = {
  type: 'token';
  key: string;
  id: string;
  token: string;
  start: number;
  end: number;
  index: number;
};

type StorySegment = TextSegment | TokenSegment;

const props = defineProps<{
  modelValue: string;
  questions: TaskQuestion[];
  selectedQuestionId?: string | null;
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void;
  (event: 'selection-change', selection: StorySelection): void;
  (event: 'select-question', questionId: string): void;
  (event: 'delete-question', questionId: string): void;
}>();

const blankPattern = /\{\{\s*blank:([a-zA-Z0-9_-]+)\s*\}\}/g;

const segments = computed<StorySegment[]>(() => {
  const displayText = props.modelValue || '';
  const parsed: StorySegment[] = [];
  let lastIndex = 0;
  let textIndex = 0;
  let tokenIndex = 0;

  for (const match of displayText.matchAll(blankPattern)) {
    const token = match[0];
    const blankId = match[1];
    const offset = match.index ?? 0;
    parsed.push({
      type: 'text',
      key: `text-${textIndex}`,
      text: displayText.slice(lastIndex, offset),
      start: lastIndex,
      end: offset,
      index: textIndex,
    });
    textIndex += 1;
    parsed.push({
      type: 'token',
      key: `token-${tokenIndex}-${blankId}`,
      id: blankId,
      token,
      start: offset,
      end: offset + token.length,
      index: tokenIndex,
    });
    tokenIndex += 1;
    lastIndex = offset + token.length;
  }

  parsed.push({
    type: 'text',
    key: `text-${textIndex}`,
    text: displayText.slice(lastIndex),
    start: lastIndex,
    end: displayText.length,
    index: textIndex,
  });

  return parsed;
});

const questionsByBlankId = computed(() => {
  const map = new Map<string, TaskQuestion>();
  for (const question of props.questions) {
    map.set(question.blank_id || question.id, question);
    map.set(question.id, question);
  }
  return map;
});

const questionTypeLabels: Record<TaskQuestion['type'], string> = {
  short_answer: '簡答題',
  cloze: '填空題',
  multiple_choice: '選擇題',
  true_false: '是非題',
};

const questionForBlank = (blankId: string) => questionsByBlankId.value.get(blankId) || null;

const questionIdForBlank = (blankId: string) => questionForBlank(blankId)?.id || blankId;

const tokenIsActive = (blankId: string) => {
  const question = questionForBlank(blankId);
  return props.selectedQuestionId === blankId || props.selectedQuestionId === question?.id;
};

const tokenLabel = (blankId: string) => {
  const index = props.questions.findIndex((question) => question.id === blankId || question.blank_id === blankId);
  if (index < 0) return '未連結題目';
  const question = questionForBlank(blankId);
  return `${question ? questionTypeLabels[question.type] : '題目'}${index + 1}`;
};

const tokenTitle = (blankId: string) => {
  const question = questionForBlank(blankId);
  if (!question) return '找不到對應題目';
  return question.prompt || question.id;
};

const segmentPlaceholder = (segment: TextSegment) => {
  if (segments.value.length === 1) return '輸入學生會看到的故事文字';
  if (segment.index === 0) return '開頭文字';
  return '接續文字';
};

const emitSelection = (start: number, end = start, displayLength = (props.modelValue || '').length) => {
  const safeStart = Math.max(0, Math.min(start, displayLength));
  const safeEnd = Math.max(safeStart, Math.min(end, displayLength));
  emit('selection-change', { start: safeStart, end: safeEnd });
};

const selectionOffsets = (element: HTMLElement) => {
  if (typeof window === 'undefined') return { start: 0, end: 0 };
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) return { start: 0, end: 0 };

  const range = selection.getRangeAt(0);
  if (!element.contains(range.startContainer) || !element.contains(range.endContainer)) {
    return { start: element.textContent?.length || 0, end: element.textContent?.length || 0 };
  }

  const startRange = range.cloneRange();
  startRange.selectNodeContents(element);
  startRange.setEnd(range.startContainer, range.startOffset);

  const endRange = range.cloneRange();
  endRange.selectNodeContents(element);
  endRange.setEnd(range.endContainer, range.endOffset);

  return {
    start: startRange.toString().length,
    end: endRange.toString().length,
  };
};

const captureSelection = (segment: TextSegment, event: Event) => {
  const element = event.currentTarget as HTMLElement;
  const offsets = selectionOffsets(element);
  emitSelection(segment.start + offsets.start, segment.start + offsets.end);
};

const updateTextSegment = (segment: TextSegment, event: Event) => {
  const element = event.currentTarget as HTMLElement;
  const nextText = element.textContent || '';
  const currentText = props.modelValue || '';
  const nextModelValue = `${currentText.slice(0, segment.start)}${nextText}${currentText.slice(segment.end)}`;
  const offsets = selectionOffsets(element);
  emit('update:modelValue', nextModelValue);
  emitSelection(
    segment.start + offsets.start,
    segment.start + offsets.end,
    nextModelValue.length,
  );
};

const pastePlainText = (segment: TextSegment, event: ClipboardEvent) => {
  event.preventDefault();
  const text = event.clipboardData?.getData('text/plain') || '';
  if (typeof document !== 'undefined') {
    document.execCommand('insertText', false, text);
  }
  updateTextSegment(segment, event);
};
</script>
