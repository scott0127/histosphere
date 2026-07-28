<template>
  <!-- 單題編輯器：研究者可調整題型、題目、placeholder、選項與參考答案。 -->
  <article class="admin-subpanel p-3">
    <div class="grid gap-3 md:grid-cols-[180px_minmax(0,1fr)_auto] md:items-end">
      <label class="block">
        <span class="admin-label">題型</span>
        <select v-model="draft.type" class="admin-field mt-1 w-full px-3 py-2 text-sm font-semibold" @change="changeType">
          <option value="short_answer">簡答題</option>
          <option value="cloze">填空題</option>
          <option value="multiple_choice">選擇題</option>
          <option value="true_false">是非題</option>
        </select>
      </label>
      <label class="block">
        <span class="admin-label">題目 ID</span>
        <input v-model="draft.id" class="admin-field mt-1 w-full px-3 py-2 font-mono text-sm" readonly />
      </label>
      <button class="admin-button-danger px-3 py-2 text-xs font-bold" @click="$emit('remove', question.id)">
        刪除題目
      </button>
    </div>

    <div class="mt-3 grid gap-3 md:grid-cols-[minmax(0,1fr)_220px]">
      <label class="block">
        <span class="admin-label">故事空格 ID</span>
        <input v-model="draft.blank_id" class="admin-field mt-1 w-full px-3 py-2 font-mono text-sm" readonly />
      </label>
      <div class="admin-token-reference rounded-[8px] px-3 py-2">
        <span class="admin-label">文中題目 chip</span>
        <span class="admin-story-token-chip admin-story-token-chip-static mt-1">
          <Icon name="mdi:tag-text-outline" class="h-4 w-4" />
          <strong>{{ draft.blank_id || draft.id }}</strong>
        </span>
      </div>
    </div>

    <label class="admin-label mt-3 block">題目文字</label>
    <textarea v-model="draft.prompt" rows="3" class="admin-textarea mt-1 w-full px-3 py-2 text-sm leading-6" @blur="commit" />

    <div class="mt-3 grid gap-3 md:grid-cols-2">
      <label class="block">
        <span class="admin-label">提示文字</span>
        <input v-model="draft.placeholder" class="admin-field mt-1 w-full px-3 py-2 text-sm" @blur="commit" />
      </label>
      <label class="block">
        <span class="admin-label">參考答案</span>
        <select v-if="draft.type === 'true_false'" v-model="correctAnswerText" class="admin-field mt-1 w-full px-3 py-2 text-sm" @change="commit">
          <option value="true">是</option>
          <option value="false">否</option>
        </select>
        <input v-else v-model="correctAnswerText" class="admin-field mt-1 w-full px-3 py-2 text-sm" @blur="commit" />
      </label>
    </div>

    <label class="admin-caption mt-3 flex items-center gap-2 text-xs font-bold">
      <input v-model="draft.required" type="checkbox" class="admin-check" @change="commit" />
      必填
    </label>

    <label v-if="draft.type === 'multiple_choice'" class="mt-3 block">
      <span class="admin-label">選項，每行一個</span>
      <textarea v-model="optionsText" rows="4" class="admin-textarea mt-1 w-full px-3 py-2 text-sm leading-6" @blur="commit" />
    </label>

    <label class="mt-3 block">
      <span class="admin-label">解析／研究者備註</span>
      <textarea
        v-model="draft.explanation"
        rows="3"
        class="admin-textarea mt-1 w-full px-3 py-2 text-sm leading-6"
        placeholder="記錄本題的判斷依據或後續討論重點"
        @blur="commit"
      />
    </label>
  </article>
</template>

<script setup lang="ts">
// TaskControlItemEditor 維護單題草稿；更新時 emit 完整 TaskQuestion 給父層寫回 JSON。
import { ref, watch } from 'vue';
import type { TaskQuestion } from '~/types';
import { optionsFromText } from '~/composables/useTaskControl';

const props = defineProps<{
  question: TaskQuestion;
}>();

const emit = defineEmits<{
  (event: 'update', question: TaskQuestion): void;
  (event: 'remove', questionId: string): void;
}>();

const answerToText = (value: unknown) => {
  if (typeof value === 'boolean') return String(value);
  return String(value ?? '');
};

const draft = ref<TaskQuestion>({ ...props.question });
const correctAnswerText = ref(answerToText(props.question.correct_answer));
const optionsText = ref((props.question.options || []).map((option) => option.label).join('\n'));

watch(
  () => props.question,
  (question) => {
    // 直接替換整筆草稿，避免切題時把上一題的選填欄位帶到下一題。
    draft.value = { ...question };
    correctAnswerText.value = answerToText(question.correct_answer);
    optionsText.value = (question.options || []).map((option) => option.label).join('\n');
  },
  { deep: true },
);

const answerFromText = () => {
  if (draft.value.type === 'true_false') {
    if (correctAnswerText.value === 'true') return true;
    if (correctAnswerText.value === 'false') return false;
    return null;
  }
  return correctAnswerText.value || null;
};

const changeType = () => {
  if (draft.value.type === 'true_false' && !['true', 'false'].includes(correctAnswerText.value)) {
    correctAnswerText.value = 'true';
  }
  if (draft.value.type === 'multiple_choice' && !optionsText.value.trim()) {
    optionsText.value = '選項 A\n選項 B';
    correctAnswerText.value = '選項 A';
  }
  commit();
};

// 將草稿轉回正式題目物件。
const commit = () => {
  emit('update', {
    ...draft.value,
    blank_id: draft.value.blank_id || draft.value.id,
    correct_answer: answerFromText(),
    options: draft.value.type === 'multiple_choice' ? optionsFromText(optionsText.value) : [],
  });
};
</script>
