
<template>
  <p class="whitespace-pre-wrap">
    <template v-for="(segment, index) in segments" :key="index">
      <span v-if="segment.isAnnotation" class="group relative mx-0.5 inline-block align-baseline">
        <span class="inline-block cursor-help rounded-md border border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] px-1.5 py-0.5 font-semibold leading-[1.4] text-[var(--admin-text)] transition-colors hover:border-[var(--admin-coffee-muted)] hover:bg-[var(--admin-surface-sunken)]">
          {{ segment.text }}
        </span>
        <span class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-xs bg-history-dark text-history-paper text-xs rounded-lg py-2 px-3 z-20 border border-history-brown shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
          {{ segment.explanation }}
          <div class="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-x-8 border-x-transparent border-t-8 border-t-history-dark"></div>
        </span>
      </span>
      <span v-else>{{ segment.text }}</span>
    </template>
  </p>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Annotation } from '~/types';

const props = defineProps<{
  content: string;
  annotations: Annotation[];
}>();

type TextSegment = {
  text: string;
  isAnnotation: boolean;
  explanation?: string;
};

const segments = computed<TextSegment[]>(() => {
  if (!props.annotations || props.annotations.length === 0) {
    return [{ text: props.content, isAnnotation: false }];
  }

  const sortedAnnotations = [...props.annotations].sort((a, b) => b.text.length - a.text.length);
  const regex = new RegExp(`(${sortedAnnotations.map(a => a.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'g');
  
  const parts = props.content.split(regex);
  
  return parts.map(part => {
    const annotation = sortedAnnotations.find(a => a.text === part);
    return {
      text: part,
      isAnnotation: !!annotation,
      explanation: annotation?.explanation
    };
  });
});
</script>
