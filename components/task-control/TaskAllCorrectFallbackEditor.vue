<template>
  <section class="admin-editor-block p-4">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="admin-kicker">All-correct fallback</p>
        <h4 class="admin-heading mt-1 text-base font-bold">全部答對時的對話起點</h4>
        <p class="admin-copy mt-1 text-xs font-semibold leading-5">
          只有受測者沒有錯題時才使用。內容必須是研究者預先核定的第三方錯誤，不會假裝成受測者答錯。
        </p>
      </div>
      <button
        v-if="!modelValue"
        class="admin-button-secondary shrink-0 px-3 py-2 text-xs font-bold"
        type="button"
        @click="createFallback"
      >
        建立素材
      </button>
      <button
        v-else
        class="admin-button-danger shrink-0 px-3 py-2 text-xs font-bold"
        type="button"
        @click="$emit('update:modelValue', null)"
      >
        停用素材
      </button>
    </div>

    <div v-if="modelValue" class="mt-4 grid gap-3 lg:grid-cols-2">
      <label class="block lg:col-span-2">
        <span class="admin-label">第三方錯誤說法</span>
        <textarea
          :value="modelValue.incorrect_claim"
          rows="3"
          class="admin-textarea mt-1 w-full px-3 py-2 text-sm leading-6"
          @input="updateField('incorrect_claim', inputValue($event))"
        />
      </label>
      <label class="block lg:col-span-2">
        <span class="admin-label">核定正確解釋</span>
        <textarea
          :value="modelValue.correct_interpretation"
          rows="3"
          class="admin-textarea mt-1 w-full px-3 py-2 text-sm leading-6"
          @input="updateField('correct_interpretation', inputValue($event))"
        />
      </label>
      <label class="block">
        <span class="admin-label">固定 ID</span>
        <input
          :value="modelValue.id"
          class="admin-field mt-1 w-full px-3 py-2 text-sm"
          @input="updateField('id', inputValue($event))"
        />
      </label>
      <label class="block">
        <span class="admin-label">可用史料 ID</span>
        <input
          :value="(modelValue.evidence_ids || []).join(', ')"
          class="admin-field mt-1 w-full px-3 py-2 text-sm"
          placeholder="例如 E01, E03"
          @input="updateEvidenceIds(inputValue($event))"
        />
      </label>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { TaskAllCorrectFallback } from '~/types';

const props = defineProps<{
  modelValue: TaskAllCorrectFallback | null;
}>();

const emit = defineEmits<{
  (event: 'update:modelValue', value: TaskAllCorrectFallback | null): void;
}>();

const inputValue = (event: Event) => (event.target as HTMLInputElement | HTMLTextAreaElement).value;

const createFallback = () => {
  emit('update:modelValue', {
    id: 'all-correct-fallback',
    incorrect_claim: '',
    correct_interpretation: '',
    evidence_ids: [],
  });
};

const updateField = (
  field: 'id' | 'incorrect_claim' | 'correct_interpretation',
  value: string,
) => {
  if (!props.modelValue) return;
  emit('update:modelValue', { ...props.modelValue, [field]: value });
};

const updateEvidenceIds = (value: string) => {
  if (!props.modelValue) return;
  emit('update:modelValue', {
    ...props.modelValue,
    evidence_ids: value.split(',').map((item) => item.trim()).filter(Boolean),
  });
};
</script>
