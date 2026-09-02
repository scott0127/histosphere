<template>
  <section class="admin-editor-block min-w-0 p-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <p class="admin-kicker">Reading passage</p>
        <h4 class="admin-heading mt-1 text-base font-bold">閱讀本文與圖片</h4>
      </div>
      <button type="button" class="admin-button-secondary inline-flex items-center gap-1 px-3 py-2 text-xs font-bold" @click="addMaterial">
        <Icon name="mdi:plus" class="h-4 w-4" />新增材料
      </button>
    </div>
    <p v-if="!modelValue.length" class="admin-copy mt-4 text-sm">尚無學習材料</p>
    <div v-for="(material, index) in modelValue" :key="material.id" class="mt-4 min-w-0 space-y-3 border-t border-[var(--admin-border)] pt-4">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <span class="admin-code-badge">{{ material.id }}</span>
        <div class="flex gap-1">
          <button type="button" class="admin-button-secondary flex h-8 w-8 items-center justify-center" :disabled="index === 0" title="上移材料" aria-label="上移材料" @click="moveMaterial(index, -1)"><Icon name="mdi:arrow-up" class="h-4 w-4" /></button>
          <button type="button" class="admin-button-secondary flex h-8 w-8 items-center justify-center" :disabled="index === modelValue.length - 1" title="下移材料" aria-label="下移材料" @click="moveMaterial(index, 1)"><Icon name="mdi:arrow-down" class="h-4 w-4" /></button>
          <button type="button" class="admin-button-danger flex h-8 w-8 items-center justify-center" title="刪除材料" aria-label="刪除材料" @click="removeMaterial(index)"><Icon name="mdi:trash-can-outline" class="h-4 w-4" /></button>
        </div>
      </div>
      <label class="block">
        <span class="admin-label">閱讀段落標題 *</span>
        <input :value="material.title" class="admin-field mt-1 w-full px-3 py-2 text-sm" @input="updateField(index, 'title', $event)" />
      </label>
      <label class="block">
        <span class="admin-label">閱讀本文</span>
        <textarea :value="material.text" rows="4" class="admin-textarea mt-1 w-full px-3 py-2 text-sm leading-6" @input="updateField(index, 'text', $event)" />
      </label>
      <label class="block">
        <span class="admin-label">作者／年代／圖說（受測者可見）</span>
        <textarea :value="material.caption" rows="2" class="admin-textarea mt-1 w-full px-3 py-2 text-sm leading-6" @input="updateField(index, 'caption', $event)" />
      </label>
      <div class="grid gap-3 lg:grid-cols-2">
        <label class="block min-w-0">
          <span class="admin-label">圖片 URL</span>
          <input :value="material.image_url" type="url" class="admin-field mt-1 w-full px-3 py-2 text-sm" @input="updateField(index, 'image_url', $event)" />
        </label>
        <label class="block min-w-0">
          <span class="admin-label">來源 URL（僅 Admin）</span>
          <input :value="material.source_url" type="url" class="admin-field mt-1 w-full px-3 py-2 text-sm" @input="updateField(index, 'source_url', $event)" />
        </label>
      </div>
      <label class="block">
        <span class="admin-label">研究引用／授權紀錄（僅 Admin）</span>
        <input :value="material.attribution" class="admin-field mt-1 w-full px-3 py-2 text-sm" @input="updateField(index, 'attribution', $event)" />
      </label>
      <template v-if="material.image_url && isTaskMaterialUrl(material.image_url)">
        <p v-if="failedImages[material.id] === material.image_url" role="status" class="admin-copy text-sm">圖片無法載入</p>
        <img v-else :src="material.image_url" :alt="material.title || '學習材料圖片'" class="max-h-64 max-w-full object-contain" loading="lazy" referrerpolicy="no-referrer" @error="failedImages[material.id] = material.image_url" />
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive } from 'vue';
import type { TaskMaterial } from '~/types';
import { createTaskMaterial, isTaskMaterialUrl } from '~/composables/useTaskControl';

const props = defineProps<{ modelValue: TaskMaterial[] }>();
const emit = defineEmits<{ (event: 'update:modelValue', value: TaskMaterial[]): void }>();
const failedImages = reactive<Record<string, string>>({});
const addMaterial = () => emit('update:modelValue', [...props.modelValue, createTaskMaterial(props.modelValue)]);
const removeMaterial = (index: number) => emit('update:modelValue', props.modelValue.filter((_, position) => position !== index));
const updateField = (index: number, field: Exclude<keyof TaskMaterial, 'id'>, event: Event) => {
  const value = (event.target as HTMLInputElement).value;
  emit('update:modelValue', props.modelValue.map((material, position) => position === index ? { ...material, [field]: value } : material));
};
const moveMaterial = (index: number, direction: number) => {
  const next = [...props.modelValue];
  const target = index + direction;
  if (target < 0 || target >= next.length) return;
  [next[index], next[target]] = [next[target]!, next[index]!];
  emit('update:modelValue', next);
};
</script>
