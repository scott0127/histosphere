<template>
  <Transition
    enter-active-class="transition-opacity duration-150"
    leave-active-class="transition-opacity duration-150"
    enter-from-class="opacity-0"
    leave-to-class="opacity-0"
  >
    <div
      v-if="research"
      class="fixed inset-0 z-[70] flex items-center justify-center bg-[rgba(47,41,36,0.55)] p-5 backdrop-blur-sm"
      @click.self="$emit('close')"
    >
      <section class="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-[12px] border-2 border-[var(--admin-line)] bg-[var(--admin-page)] shadow-[0_30px_90px_rgba(47,41,36,0.32)]">
        <header class="flex items-start justify-between gap-4 border-b border-[var(--admin-border)] px-6 py-5">
          <div class="min-w-0 flex-1">
            <p class="admin-kicker">Session research record</p>
            <h2 class="admin-heading mt-1 break-words font-serif text-lg font-bold sm:text-2xl">
              {{ research.participant_code }} · {{ research.event.canonical_name }}
            </h2>
            <p class="admin-caption mt-2 text-sm font-semibold">
              {{ conditionLabel }} · {{ sessionStatusLabel }} · {{ shortId(research.session.id) }}
            </p>
          </div>
          <div class="flex shrink-0 gap-2">
            <button
              type="button"
              class="admin-button-secondary inline-flex h-10 w-10 items-center justify-center"
              title="重新載入紀錄與用量"
              aria-label="重新載入紀錄與用量"
              @click="$emit('refresh', research.session.id)"
            >
              <Icon name="mdi:refresh" class="h-5 w-5" />
            </button>
            <button
              type="button"
              class="admin-button-secondary inline-flex h-10 w-10 shrink-0 items-center justify-center"
              title="關閉"
              @click="$emit('close')"
            >
              <Icon name="mdi:close" class="h-5 w-5" />
            </button>
          </div>
        </header>

        <div class="overflow-y-auto px-6 py-5">
          <div class="grid gap-px overflow-hidden rounded-[8px] border border-[var(--admin-border)] bg-[var(--admin-border)] md:grid-cols-3 xl:grid-cols-6">
            <div v-for="item in summaryItems" :key="item.label" class="bg-[var(--admin-surface)] px-4 py-3">
              <p class="admin-caption text-xs font-bold">{{ item.label }}</p>
              <p class="admin-heading mt-1 text-xl font-black">{{ item.value }}</p>
            </div>
          </div>
          <p class="admin-caption mt-2 text-xs font-semibold">
            共 {{ research.stats.llm_calls_total }} 次 LLM 呼叫（含 Task judge、開場、聊天、答案審查與修正）；Token 覆蓋
            {{ formatPercent(research.stats.token_usage_coverage) }}。快取輸入
            {{ research.stats.cached_prompt_tokens.toLocaleString() }}；推理 Token
            {{ research.stats.reasoning_tokens.toLocaleString() }}（已包含於輸出 Token）。
            <template v-if="research.stats.cost_usage_complete && research.stats.estimated_cost_usd != null">
              估計成本 {{ formatUsd(research.stats.estimated_cost_usd) }}。
            </template>
            <template v-else>成本資料不完整，不顯示部分估計。</template>
          </p>

          <div class="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.65fr)_minmax(300px,0.75fr)]">
            <section>
              <div class="mb-3 flex items-center justify-between gap-3 border-b border-[var(--admin-border-soft)] pb-3">
                <div>
                  <p class="admin-kicker">Transcript</p>
                  <h3 class="admin-heading mt-1 text-lg font-black">完整對話紀錄</h3>
                </div>
                <span class="admin-badge">{{ research.messages.length }} 則</span>
              </div>

              <div v-if="research.messages.length" class="space-y-3">
                <article
                  v-for="message in research.messages"
                  :key="message.id || `${message.sequence_index}-${message.created_at}`"
                  class="border px-4 py-3"
                  :class="message.speaker_type === 'learner'
                    ? 'ml-4 rounded-[8px] border-[var(--admin-coffee)] bg-[var(--admin-coffee)] text-white sm:ml-12'
                    : 'mr-4 rounded-[8px] border-[var(--admin-border)] bg-[var(--admin-surface)] text-[var(--admin-copy-strong)] sm:mr-12'"
                >
                  <div class="flex items-center justify-between gap-3 text-xs font-bold opacity-75">
                    <span>{{ message.speaker_type === 'learner' ? '受測者' : message.speaker_name }}</span>
                    <span>{{ formatDate(message.created_at) }}</span>
                  </div>
                  <p class="mt-2 whitespace-pre-wrap break-words text-sm font-semibold leading-7">{{ message.content }}</p>
                  <AdminAnswerReviewDetails v-if="message.metadata?.answer_review || message.metadata?.answer_delivery" :review="message.metadata.answer_review" :delivery="message.metadata.answer_delivery" />
                </article>
              </div>
              <div v-else class="admin-empty-state p-5">此 Session 尚未建立對話。</div>
            </section>

            <aside class="space-y-4">
              <section class="border-b border-[var(--admin-border)] pb-4">
                <p class="admin-kicker">Reproducibility</p>
                <h3 class="admin-heading mt-1 text-lg font-black">重現性狀態</h3>
                <p class="admin-copy mt-3 text-sm font-semibold">
                  素材快照：{{ research.material_snapshot.status === 'captured' ? '已保存' : '舊 Session 未保存' }}
                </p>
                <p v-if="research.material_snapshot.material_hash" class="admin-caption mt-1 break-all font-mono text-xs">
                  {{ research.material_snapshot.material_hash }}
                </p>
                <p class="admin-copy mt-2 text-sm font-semibold">
                  Prompt 紀錄：{{ research.prompt_records.length }} 筆
                </p>
              </section>

              <details v-if="research.attempt" class="border-b border-[var(--admin-border)] pb-4">
                <summary class="cursor-pointer text-sm font-black text-[var(--admin-copy-strong)]">Task 作答與評分</summary>
                <pre class="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-[6px] bg-[var(--admin-surface-muted)] p-3 text-xs leading-6">{{ taskPayload }}</pre>
              </details>

              <details v-if="research.prompt_records.length" class="border-b border-[var(--admin-border)] pb-4">
                <summary class="cursor-pointer text-sm font-black text-[var(--admin-copy-strong)]">Prompt 雜湊與模型用量</summary>
                <div class="mt-3 space-y-3">
                  <div v-for="record in research.prompt_records" :key="`${record.created_at}-${record.message_id}`">
                    <p class="admin-copy text-xs font-black">{{ promptStageLabel(record.stage) }}</p>
                    <p class="admin-caption mt-1 break-all font-mono text-[11px]">{{ record.prompt_hash }}</p>
                    <p class="admin-caption mt-1 text-xs">{{ llmLabel(record.llm_call) }}</p>
                  </div>
                </div>
              </details>

              <section>
                <p class="admin-kicker">Timing</p>
                <dl class="mt-2 grid grid-cols-[100px_1fr] gap-y-2 text-sm">
                  <dt class="admin-caption font-bold">開始</dt>
                  <dd class="admin-copy font-semibold">{{ formatDate(research.session.timer_started_at) }}</dd>
                  <dt class="admin-caption font-bold">結束</dt>
                  <dd class="admin-copy font-semibold">{{ formatDate(research.session.timer_ends_at) }}</dd>
                  <dt class="admin-caption font-bold">訊息跨度</dt>
                  <dd class="admin-copy font-semibold">{{ formatDuration(research.stats.duration_seconds) }}</dd>
                </dl>
              </section>
            </aside>
          </div>
        </div>
      </section>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { AdminSessionResearchResponse } from '~/types';
import { experimentConditionCodes, experimentConditionCodeByKey, experimentConditionLabels } from '~/utils/experimentConditions';

const props = defineProps<{ research: AdminSessionResearchResponse | null }>();
defineEmits<{ (event: 'close'): void; (event: 'refresh', sessionId: string): void }>();

const conditionLabel = computed(() => {
  if (!props.research) return '';
  const code = experimentConditionCodeByKey[props.research.session.condition_key_snapshot];
  return code && experimentConditionCodes.includes(code)
    ? `${code} ${experimentConditionLabels[code]}`
    : props.research.session.condition_key_snapshot;
});

const sessionStatusLabel = computed(() => {
  const status = props.research?.session.status;
  if (status === 'completed') return '已完成';
  if (status === 'archived') return '已封存';
  if (status === 'conversation_started') return 'Chat';
  return 'Task';
});

const summaryItems = computed(() => {
  const stats = props.research?.stats;
  if (!stats) return [];
  return [
    { label: '總訊息數', value: stats.total_messages },
    { label: '受測者 / AI', value: `${stats.learner_messages} / ${stats.assistant_messages}` },
    { label: '完成來回', value: stats.completed_exchanges },
    { label: '輸入 Token', value: stats.prompt_tokens.toLocaleString() },
    { label: '輸出 Token', value: stats.completion_tokens.toLocaleString() },
    { label: 'Session 總 Token', value: stats.total_tokens.toLocaleString() },
  ];
});

const taskPayload = computed(() => JSON.stringify({
  response: props.research?.attempt?.response_payload || {},
  judgement: props.research?.attempt?.judgement_payload || {},
}, null, 2));

const shortId = (id: string) => `${id.slice(0, 8)}...${id.slice(-4)}`;
const formatPercent = (value: number) => `${Math.round(value * 100)}%`;
const formatUsd = (value: number) => `US$${value.toFixed(6)}`;
const formatDate = (value?: string | null) => value
  ? new Intl.DateTimeFormat('zh-TW', { dateStyle: 'short', timeStyle: 'medium' }).format(new Date(value))
  : '未記錄';
const formatDuration = (value?: number | null) => value == null
  ? '未產生訊息'
  : `${Math.floor(value / 60)} 分 ${value % 60} 秒`;
const promptStageLabel = (stage: string) => stage === 'conversation_opening' ? '開場回覆' : '對話回覆';
const llmLabel = (llmCall?: Record<string, unknown> | null) => {
  if (!llmCall) return '未記錄模型用量';
  const total = llmCall.total_tokens == null ? 'Token 未回報' : `${llmCall.total_tokens} tokens`;
  const cost = typeof llmCall.estimated_cost_usd === 'number'
    ? ` · ${formatUsd(llmCall.estimated_cost_usd)}`
    : '';
  return `${llmCall.provider || 'unknown'} / ${llmCall.model || 'unknown'} · ${total}${cost}`;
};
</script>
