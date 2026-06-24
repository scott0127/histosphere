<template>
  <!-- 事件詳情彈窗：呈現同一事件素材，並提供四種活動入口。 -->
  <Transition name="modal-fade">
    <div class="fixed inset-0 z-40 flex items-center justify-center bg-[rgba(47,41,36,0.58)] p-4 backdrop-blur-sm" @click.self="$emit('close')">
      <article class="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-[12px] border-2 border-[var(--admin-line)] bg-[var(--admin-page)] shadow-[0_30px_90px_rgba(47,41,36,0.34)]">
        <div class="sticky top-0 z-10 flex items-center justify-between border-b border-[var(--admin-border)] bg-[rgba(255,253,248,0.95)] px-5 py-3 backdrop-blur">
          <div>
            <p class="text-xs font-black uppercase tracking-[0.2em] text-[var(--admin-coffee)]">歷史事件</p>
            <h2 class="mt-1 font-serif text-2xl font-black text-[var(--admin-text)]">{{ event.canonical_name }}</h2>
          </div>
          <button
            type="button"
            class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[var(--admin-border)] bg-[var(--admin-surface)] text-[var(--admin-coffee)] transition hover:bg-[var(--admin-coffee-soft)]"
            title="關閉"
            @click="$emit('close')"
          >
            <Icon name="mdi:close" class="h-5 w-5" />
          </button>
        </div>

        <div class="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_300px]">
          <section class="rounded-[10px] border border-[var(--admin-border)] bg-[var(--admin-surface)] p-4 shadow-[var(--admin-shadow-soft)]">
            <div class="flex flex-wrap items-center gap-2">
              <span class="rounded-full bg-[var(--admin-coffee)] px-3 py-1 text-xs font-serif font-black text-[var(--admin-surface)]">
                {{ formatYears(event) }}
              </span>
              <span class="rounded-full border border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] px-3 py-1 text-xs font-serif font-bold text-[var(--admin-coffee)]">
                {{ eventMotif(event).label }}
              </span>
            </div>
            <h3 class="mt-4 font-serif text-2xl font-black text-[var(--admin-text)]">{{ event.canonical_name }}</h3>
            <p class="mt-3 line-clamp-3 text-sm font-medium leading-7 text-[var(--admin-copy)]">
              {{ event.description || event.context || '此事件尚未補上描述。' }}
            </p>

            <div class="mt-4 grid gap-3 sm:grid-cols-2">
              <div class="rounded-[9px] border border-[var(--admin-border-soft)] bg-[var(--admin-surface-muted)] p-3">
                <p class="text-xs font-black uppercase tracking-[0.18em] text-[var(--admin-coffee)]">核心歷史人物</p>
                <p class="mt-2 text-base font-black text-[var(--admin-text)]">{{ event.personas[0]?.name || '人物待補' }}</p>
                <p class="mt-1 text-sm font-medium leading-6 text-[var(--admin-copy)]">{{ event.personas[0]?.role || '尚未設定角色定位' }}</p>
              </div>
              <div class="rounded-[9px] border border-[var(--admin-border-soft)] bg-[var(--admin-surface-muted)] p-3">
                <p class="text-xs font-black uppercase tracking-[0.18em] text-[var(--admin-coffee)]">前置任務</p>
                <p class="mt-2 text-base font-black text-[var(--admin-text)]">{{ event.latest_task ? '已建立' : '尚未建立' }}</p>
              </div>
            </div>
          </section>

          <aside class="space-y-4">
            <label class="block rounded-[10px] border border-[var(--admin-border)] bg-[var(--admin-surface)] p-3 shadow-[var(--admin-shadow-soft)]">
              <span class="text-xs font-black uppercase tracking-[0.18em] text-[var(--admin-coffee)]">受測者</span>
              <input
                :value="participantId"
                class="mt-2 w-full rounded-[8px] border border-[var(--admin-border)] bg-[var(--admin-surface)] px-4 py-3 text-sm font-semibold text-[var(--admin-text)] outline-none transition focus:ring-4 focus:ring-[var(--admin-focus)]"
                @input="updateParticipantId"
                @change="$emit('participant-change')"
              />
            </label>

            <div v-if="activityMode === 'admin'" class="rounded-[10px] border border-[var(--admin-border)] bg-[var(--admin-surface)] p-3 shadow-[var(--admin-shadow-soft)]">
              <div class="flex items-center justify-between gap-3">
                <p class="text-sm font-black text-[var(--admin-text)]">管理</p>
                <button
                  type="button"
                  class="inline-flex h-9 w-9 items-center justify-center rounded-full border border-red-200 bg-red-50 text-red-600 transition hover:bg-red-100"
                  title="刪除此事件"
                  @click="$emit('delete', event.id)"
                >
                  <Icon name="mdi:trash-can-outline" class="h-4 w-4" />
                </button>
              </div>
              <NuxtLink to="/admin" class="mt-3 inline-flex w-full items-center justify-center rounded-[8px] border border-[var(--admin-border)] bg-[var(--admin-surface-muted)] px-4 py-3 text-sm font-black text-[var(--admin-coffee)] transition hover:bg-[var(--admin-coffee-soft)]">
                編輯活動素材
              </NuxtLink>
            </div>
          </aside>
        </div>

        <ActivityConditionGrid
          :conditions="conditions"
          :progress-by-condition="progressByCondition"
          :mode="activityMode"
          @start="$emit('start-condition', $event)"
        />
      </article>
    </div>
  </Transition>
</template>

<script setup lang="ts">
// EventDetailModal 是事件素材與活動入口的組合元件。
// 它不直接呼叫 API；刪除、受測者儲存、活動啟動都交回 page 控制。
import type { ConditionKey, EventWithPersonas, ExperimentCondition } from '~/types';
import ActivityConditionGrid from '~/components/event-library/ActivityConditionGrid.vue';
import { eventMotif, formatYears } from '~/utils/eventPresentation';

type LocalConditionProgress = {
  status: 'not_started' | 'task_started' | 'chat_started';
  sessionId?: string;
  taskId?: string;
  conversationId?: string;
  updatedAt: string;
};

defineProps<{
  event: EventWithPersonas;
  participantId: string;
  conditions: ExperimentCondition[];
  progressByCondition: Partial<Record<ConditionKey, LocalConditionProgress>>;
  activityMode: 'admin' | 'learner';
}>();

const emit = defineEmits<{
  (event: 'close'): void;
  (event: 'delete', eventId: string): void;
  (event: 'participant-change'): void;
  (event: 'start-condition', condition: ExperimentCondition): void;
  (event: 'update:participantId', value: string): void;
}>();

// 同步受測者代號給 page，讓 localStorage 與後端 UUID 邏輯維持單一來源。
const updateParticipantId = (event: Event) => {
  emit('update:participantId', (event.target as HTMLInputElement).value);
};
</script>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.18s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
