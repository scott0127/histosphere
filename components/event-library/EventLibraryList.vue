<template>
  <!-- 右側素材庫列表：同一事件的 source、task、persona 會被四種活動共用。 -->
  <section class="min-w-0 pb-10 lg:pb-0">
    <div class="flex lg:h-full lg:flex-col">
      <div class="mb-6 flex flex-col gap-4 border-b border-[var(--admin-border)] pb-4 xl:flex-row xl:items-end xl:justify-between">
        <div class="flex flex-col">
          <div class="flex items-center gap-1.5 text-xs font-bold uppercase tracking-[0.2em] text-[var(--admin-coffee)]">
            <Icon name="mdi:pillar" class="h-4 w-4" />
            <span>歷史篇章</span>
          </div>
          <h2 class="mt-2 font-serif text-3xl font-bold tracking-[0.02em] text-[var(--admin-text)]">已記錄的歷史篇章</h2>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <span class="rounded-full border border-[var(--admin-border)] bg-[var(--admin-surface)] px-3.5 py-1 text-xs font-bold text-[var(--admin-coffee)] shadow-sm">
            {{ events.length }} 筆
          </span>
          <button
            v-if="canCreateEvent"
            type="button"
            class="inline-flex items-center justify-center gap-2 rounded-full border border-[var(--admin-coffee)] bg-[var(--admin-coffee)] px-4 py-2 text-sm font-bold text-[var(--admin-surface)] shadow-sm transition hover:bg-[var(--admin-coffee-hover)] hover:shadow-md"
            @click="showCreateForm = !showCreateForm"
          >
            <Icon name="mdi:book-open-page-variant" class="h-4 w-4" />
            新增歷史事件
          </button>
        </div>
      </div>

      <form
        v-if="canCreateEvent && showCreateForm"
        class="mb-6 rounded-[10px] border border-[var(--admin-border)] bg-[var(--admin-surface)] p-4 shadow-sm"
        @submit.prevent="$emit('create')"
      >
        <div class="flex flex-col gap-3 md:flex-row">
          <label for="libraryEventName" class="sr-only">歷史事件</label>
          <div class="relative min-w-0 flex-1">
            <input
              id="libraryEventName"
              :value="eventName"
              class="w-full rounded-[8px] border border-[var(--admin-border)] bg-[var(--admin-surface)] py-3 pl-4 pr-10 text-sm font-semibold text-[var(--admin-text)] shadow-inner outline-none transition placeholder:text-[var(--admin-soft)] focus:bg-[var(--admin-surface)] focus:ring-2 focus:ring-[var(--admin-focus)]"
              placeholder="例如：法國大革命"
              @input="updateEventName"
            />
            <Icon name="mdi:feather" class="absolute right-3 top-1/2 h-5 w-5 -translate-y-1/2 text-[var(--admin-soft)]" />
          </div>
          <button
            type="submit"
            :disabled="creatingEvent || !eventName.trim()"
            class="inline-flex items-center justify-center gap-2 rounded-[8px] border border-[var(--admin-coffee)] bg-[var(--admin-coffee)] px-5 py-3 text-sm font-bold text-[var(--admin-surface)] shadow-md transition hover:bg-[var(--admin-coffee-hover)] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
          >
            <Icon v-if="creatingEvent" name="mdi:loading" class="h-5 w-5 animate-spin" />
            <template v-else>
              建立事件
              <Icon name="mdi:arrow-right" class="h-4 w-4" />
            </template>
          </button>
        </div>
        <p v-if="createError" class="mt-3 rounded-[8px] border border-red-300 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
          {{ createError }}
        </p>
      </form>

      <div v-if="loadingEvents" class="rounded-[10px] border border-[var(--admin-border)] bg-[var(--admin-surface-muted)] p-10 text-center text-[var(--admin-copy)] shadow-sm">
        <Icon name="mdi:loading" class="mx-auto h-8 w-8 animate-spin" />
        <p class="mt-3 font-semibold">載入事件...</p>
      </div>

      <div
        v-else-if="events.length"
        class="grid gap-6 overflow-y-auto pr-2 md:grid-cols-2 lg:flex-1 lg:auto-rows-[minmax(240px,1fr)]"
      >
        <button
          v-for="event in events"
          :key="event.id"
          type="button"
          class="group relative overflow-hidden rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] bg-[linear-gradient(135deg,rgba(255,255,255,0.46),transparent_38%),radial-gradient(circle_at_82%_18%,rgba(168,141,123,0.14),transparent_28%)] p-1.5 text-left shadow-md transition-all duration-300 hover:-translate-y-1 hover:border-[var(--admin-line)] hover:bg-[var(--admin-surface-muted)] hover:shadow-lg"
          @click="$emit('open', event)"
        >
          <div
            :class="[
              'pointer-events-none absolute bottom-0 right-0 top-0 w-[45%] select-none overflow-hidden rounded-r-xl',
              showEventIntroduction ? 'opacity-[0.16]' : 'opacity-50',
            ]"
          >
            <img
              :src="getEventSketch(event)"
              class="h-full w-full object-cover object-right mix-blend-multiply contrast-[1.25] brightness-[1.08] [mask-image:linear-gradient(to_left,black_15%,transparent_95%)] [-webkit-mask-image:linear-gradient(to_left,black_15%,transparent_95%)]"
              alt=""
            />
          </div>

          <div class="relative flex h-full flex-col justify-between rounded-[8px] border border-[var(--admin-border-soft)] p-4">
            <div class="relative z-10">
              <div class="flex flex-wrap items-center gap-2.5">
                <span class="rounded-full bg-[var(--admin-coffee)] px-3.5 py-1 text-xs font-serif font-semibold text-[var(--admin-surface)] shadow-sm">
                  {{ formatYears(event) }}
                </span>
                <span class="rounded-full border border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] px-3 py-1 text-xs font-serif font-medium text-[var(--admin-coffee)]">
                  {{ eventMotif(event).label }}
                </span>
              </div>
              <h3 class="mt-5 font-serif text-3xl font-bold leading-tight text-[var(--admin-text)]">
                {{ event.canonical_name }}
              </h3>
              <p
                v-if="showEventIntroduction"
                class="mt-4 line-clamp-3 max-w-[85%] text-sm font-medium leading-relaxed text-[var(--admin-copy)]"
              >
                {{ event.description || event.context || '此事件尚未補上描述。' }}
              </p>
            </div>

            <div class="relative z-10 mt-6 flex items-center justify-between border-t border-[var(--admin-border-soft)] pt-4">
              <span class="inline-flex items-center gap-2 text-sm font-bold text-[var(--admin-coffee)] transition-all group-hover:text-[var(--admin-text)]">
                點擊查看詳情
                <Icon name="mdi:arrow-right" class="h-4 w-4 transition-transform group-hover:translate-x-1.5" />
              </span>
            </div>
          </div>
        </button>
      </div>

      <div v-else class="rounded-[10px] border border-dashed border-[var(--admin-border)] bg-[var(--admin-surface-muted)] p-10 text-center shadow-sm">
        <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-[var(--admin-coffee)] bg-[var(--admin-surface)] text-[var(--admin-coffee)]">
          <Icon name="mdi:book-open-blank-variant" class="h-8 w-8" />
        </div>
        <h3 class="mt-5 font-serif text-2xl font-black text-[var(--admin-text)]">尚未建立歷史篇章</h3>
        <p class="mt-2 text-sm font-semibold leading-7 text-[var(--admin-copy)]">
          {{ canCreateEvent ? '請點擊上方「新增歷史事件」，建立一組學習素材。' : '目前尚無可參與的歷史事件。' }}
        </p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// EventLibraryList 負責事件卡片呈現；點擊後把完整事件交回 page 開啟詳情。
import { ref } from 'vue';
import type { EventWithPersonas } from '~/types';
import { eventMotif, formatYears, getEventSketch } from '~/utils/eventPresentation';

defineProps<{
  eventName: string;
  events: EventWithPersonas[];
  loadingEvents: boolean;
  creatingEvent: boolean;
  createError: string | null;
  canCreateEvent: boolean;
  showEventIntroduction: boolean;
}>();

const emit = defineEmits<{
  (event: 'update:eventName', value: string): void;
  (event: 'create'): void;
  (event: 'open', value: EventWithPersonas): void;
}>();

const showCreateForm = ref(false);

const updateEventName = (event: Event) => {
  emit('update:eventName', (event.target as HTMLInputElement).value);
};
</script>
