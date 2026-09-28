<template>
  <article class="monitor-question" :aria-labelledby="`review-heading-${row.question.id}`">
    <header class="monitor-question-heading">
      <p class="monitor-eyebrow">第 {{ index + 1 }} 題 <span>{{ row.question.id }}</span></p>
      <span class="monitor-small-status" :class="{ 'is-checked': draft.reviewed }">{{ draft.reviewed ? '已核對' : '待核對' }}</span>
    </header>
    <h2 :id="`review-heading-${row.question.id}`" class="monitor-question-text">{{ row.text }}</h2>
    <ul v-if="row.question.options?.length" class="monitor-options" aria-label="題目選項">
      <li v-for="(option, optionIndex) in row.question.options" :key="option.id || option.value"><span class="monitor-option-letter">{{ String.fromCharCode(65 + optionIndex) }}.</span><span>{{ option.label }}</span></li>
    </ul>

    <section class="monitor-answer" aria-label="受測者原始作答">
      <h3>受測者作答</h3>
      <dl>
        <dt>答案</dt><dd>{{ formatReviewAnswer(row.answer, row.question) }}</dd>
        <dt>理由</dt><dd>{{ row.rationale || '尚未填寫' }}</dd>
      </dl>
    </section>

    <details class="monitor-ai-details">
      <summary>
        <span>系統初判</span>
        <span>答案{{ judgementLabel(row.ai.answer_correct) }} · 理由{{ judgementLabel(row.ai.reasoning_correct) }}</span>
      </summary>
      <dl>
        <template v-if="row.ai.answer_feedback"><dt>答案說明</dt><dd>{{ row.ai.answer_feedback }}</dd></template>
        <dt>理由說明</dt><dd>{{ row.ai.reasoning_feedback || '未提供' }}</dd>
      </dl>
    </details>

    <fieldset :disabled="disabled || readonly" class="monitor-decision">
      <legend>{{ readonly ? '人工最終判定' : '研究者判定' }}</legend>
      <div class="monitor-decision-grid">
        <div v-for="field in decisionFields" :key="field.key" class="monitor-decision-field">
          <span :id="`${row.question.id}-${field.key}-label`">{{ field.label }}</span>
          <div class="monitor-segment" role="group" :aria-labelledby="`${row.question.id}-${field.key}-label`">
            <button v-for="choice in choices" :key="String(choice.value)" type="button"
              :aria-pressed="draft[field.key] === choice.value"
              :class="{ 'is-selected': draft[field.key] === choice.value }"
              @click="emit('update', { [field.key]: choice.value })">{{ choice.label }}</button>
          </div>
        </div>
      </div>
      <label v-if="row.question.type === 'cloze' || draft.answer_feedback || row.ai.answer_correct !== draft.answer_correct" class="monitor-field-label">
        答案判定說明
        <textarea :value="draft.answer_feedback" rows="2" class="admin-textarea"
          :aria-label="`${row.question.id} 答案判定說明`" @input="updateText('answer_feedback', $event)" />
      </label>
      <label class="monitor-field-label">
        理由判定說明
        <span v-if="!readonly" class="monitor-field-hint">由 AI 初判預填，可由研究者修訂。</span>
        <textarea :value="draft.reasoning_feedback" rows="3" class="admin-textarea"
          :aria-label="`${row.question.id} 理由判定說明`" @input="updateText('reasoning_feedback', $event)" />
      </label>
      <label v-if="hasOverride || draft.override_reason" class="monitor-field-label monitor-override">
        改判原因
        <textarea :value="draft.override_reason" rows="2" class="admin-textarea"
          :aria-label="`${row.question.id} 改判原因`" placeholder="說明原作答如何符合或不符合判準"
          @input="updateText('override_reason', $event)" />
      </label>
      <p class="monitor-decision-summary">整題判定：<strong>{{ draft.answer_correct && draft.reasoning_correct ? '通過' : '需進一步討論' }}</strong></p>
      <div v-if="!readonly" class="monitor-question-actions">
        <button type="button" class="monitor-text-button" @click="emit('save', false)">保存草稿</button>
        <button type="button" class="admin-button-secondary monitor-button" :disabled="draft.reviewed"
          @click="emit('save', true)"><Icon name="mdi:check" class="h-4 w-4" />{{ draft.reviewed ? '此題已核對' : '確認此題' }}</button>
      </div>
    </fieldset>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ReviewQuestionRow, TaskReviewQuestion } from '~/types/taskReview';
import { formatReviewAnswer, reviewHasOverride } from '~/utils/taskReview';
const props = defineProps<{ row: ReviewQuestionRow; draft: TaskReviewQuestion; index: number; disabled?: boolean; readonly?: boolean }>();
const emit = defineEmits<{
  (event: 'update', patch: Partial<TaskReviewQuestion>): void;
  (event: 'save', confirm: boolean): void;
}>();
const choices = [{ value: true, label: '正確' }, { value: false, label: '不符合' }];
const decisionFields = [{ key: 'answer_correct', label: '答案' }, { key: 'reasoning_correct', label: '理由' }] as const;
const hasOverride = computed(() => reviewHasOverride(props.row, props.draft));
const judgementLabel = (value?: boolean) => typeof value !== 'boolean' ? '未判定' : value ? '正確' : '不符合';
const updateText = (field: 'answer_feedback' | 'reasoning_feedback' | 'override_reason', event: Event) =>
  emit('update', { [field]: (event.target as HTMLTextAreaElement).value });
</script>
