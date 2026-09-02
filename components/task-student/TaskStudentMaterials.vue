<template>
  <section v-if="materials.length" class="space-y-7" aria-label="閱讀本文">
    <div v-for="material in materials" :key="material.id" class="min-w-0 space-y-4">
      <h3 v-if="material.title" class="break-words text-lg font-semibold leading-8 text-[var(--admin-text)]">{{ material.title }}</h3>
      <figure v-if="taskMaterialUrl(material.image_url)" class="space-y-3">
        <img :src="taskMaterialUrl(material.image_url)" :alt="material.caption || material.title" class="max-h-[32rem] w-full object-contain object-left" />
        <figcaption v-if="material.caption" class="whitespace-pre-wrap break-words text-sm leading-7 text-[var(--admin-copy)]">{{ material.caption }}</figcaption>
      </figure>
      <p v-else-if="material.caption" class="whitespace-pre-wrap break-words text-sm leading-7 text-[var(--admin-copy)]">{{ material.caption }}</p>
      <p v-if="material.text" class="whitespace-pre-wrap break-words text-lg leading-9 text-[var(--admin-text)]">{{ material.text }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { TaskMaterial } from '~/types';
import { taskMaterialUrl } from '~/composables/useStudentTask';

// 題組本文保留判斷所需的文字與圖說；研究用引用與連結不屬於受測者畫面。
defineProps<{ materials: TaskMaterial[] }>();
</script>
