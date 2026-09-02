<template>
  <section v-if="materials.length" class="space-y-5 border-t border-[var(--admin-border-soft)] pt-5" aria-label="參考史料">
    <h3 class="text-base font-bold text-[var(--admin-text)]">參考史料</h3>
    <figure v-for="material in materials" :key="material.id" class="min-w-0 space-y-3 border-b border-[var(--admin-border-soft)] pb-5 last:border-0">
      <figcaption class="text-base font-semibold text-[var(--admin-text)]">
        <span class="mr-2 font-mono text-sm text-[var(--admin-coffee)]">{{ material.id }}</span>{{ material.title }}
      </figcaption>
      <a v-if="taskMaterialUrl(material.image_url)" :href="taskMaterialUrl(material.image_url)" target="_blank" rel="noopener noreferrer" :aria-label="`開啟圖片：${material.title}`" class="block">
        <img :src="taskMaterialUrl(material.image_url)" :alt="material.title" loading="lazy" class="max-h-[32rem] w-full object-contain object-left" />
      </a>
      <p class="whitespace-pre-wrap break-words text-base leading-8 text-[var(--admin-copy)]">{{ material.text }}</p>
      <p v-if="material.attribution" class="whitespace-pre-wrap break-words text-sm leading-6 text-[var(--admin-soft)]">{{ material.attribution }}</p>
      <a v-if="taskMaterialUrl(material.source_url)" :href="taskMaterialUrl(material.source_url)" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 text-sm font-semibold text-[var(--admin-coffee)] underline underline-offset-4">
        原始來源
        <Icon name="mdi:link-variant" class="h-4 w-4 shrink-0" />
      </a>
    </figure>
  </section>
</template>

<script setup lang="ts">
import type { TaskMaterial } from '~/types';
import { taskMaterialUrl } from '~/composables/useStudentTask';

defineProps<{ materials: TaskMaterial[] }>();
</script>
