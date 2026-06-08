<template>
  <div class="space-y-3">
    <article
      v-for="event in events"
      :key="event.id"
      class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-teal-300 hover:shadow-md"
    >
      <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="truncate font-sans text-base font-bold text-slate-950">
              {{ event.canonical_name }}
            </h3>
            <span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
              {{ formatYears(event) }}
            </span>
          </div>
          <p class="mt-2 line-clamp-2 text-sm leading-6 text-slate-600">
            {{ event.description || event.context || '此事件尚未補上描述。' }}
          </p>
          <div class="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
            <span class="inline-flex items-center gap-1">
              <Icon name="mdi:account-group" class="h-4 w-4" />
              {{ event.personas.length }} 位人物
            </span>
            <span class="inline-flex items-center gap-1">
              <Icon name="mdi:clipboard-text-outline" class="h-4 w-4" />
              {{ event.latest_task ? '已有 task' : '尚無 task' }}
            </span>
          </div>
        </div>

        <div class="flex shrink-0 items-center gap-2">
          <button
            class="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-teal-500 hover:text-teal-700"
            @click="$emit('enter-story', event)"
          >
            <Icon name="mdi:play-circle-outline" class="h-5 w-5" />
            使用
          </button>
          <button
            class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-400 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600"
            title="刪除此事件"
            @click="$emit('delete-event', event.id)"
          >
            <Icon name="mdi:trash-can-outline" class="h-5 w-5" />
          </button>
        </div>
      </div>
    </article>
  </div>
</template>

<script setup lang="ts">
import type { EventWithPersonas } from '~/types';

defineProps<{
  events: EventWithPersonas[];
}>();

defineEmits<{
  (event: 'enter-story', value: EventWithPersonas): void;
  (event: 'delete-event', eventId: string): void;
}>();

const formatYears = (event: EventWithPersonas) => {
  if (event.start_year && event.end_year) return `${event.start_year} - ${event.end_year}`;
  if (event.start_year) return `${event.start_year}`;
  if (event.century) return `${event.century} 世紀`;
  return '時間待補';
};
</script>
