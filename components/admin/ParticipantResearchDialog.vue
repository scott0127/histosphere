<template>
  <Transition
    enter-active-class="transition-opacity duration-150"
    leave-active-class="transition-opacity duration-150"
    enter-from-class="opacity-0"
    leave-to-class="opacity-0"
  >
    <div
      v-if="research"
      class="research-overlay fixed inset-0 z-[70] flex items-center justify-center p-2 sm:p-5"
      @click.self="$emit('close')"
    >
      <section ref="dialog" role="dialog" aria-modal="true" aria-labelledby="research-title" tabindex="-1" class="research-dialog flex max-h-[calc(100dvh-1rem)] w-full max-w-6xl flex-col overflow-hidden rounded-[12px] border border-[var(--admin-border)] bg-[var(--admin-surface)] sm:max-h-[calc(100dvh-2.5rem)]" @keydown="handleDialogKey">
        <header class="flex shrink-0 items-start justify-between gap-4 border-b border-[var(--admin-border)] px-4 py-4 sm:px-6 sm:py-5">
          <div class="min-w-0 flex-1">
            <p class="admin-kicker">Session research record</p>
            <h2 id="research-title" class="admin-heading mt-1 break-words font-serif text-lg font-bold sm:text-2xl">
              <span>{{ research.participant_code }}</span>
              <span class="inline-block">· {{ research.event.canonical_name }}</span>
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
              aria-label="關閉研究紀錄"
              @click="$emit('close')"
            >
              <Icon name="mdi:close" class="h-5 w-5" />
            </button>
          </div>
        </header>
        <nav aria-label="研究紀錄分區" class="research-tabs flex shrink-0 gap-2 overflow-x-auto border-b border-[var(--admin-border)] px-3 sm:px-6">
          <button v-for="tab in tabs" :key="tab.id" type="button" :aria-pressed="activeTab === tab.id" class="research-tab min-h-12 shrink-0 px-3 text-xs sm:text-sm" @click="activeTab = tab.id">{{ tab.label }}</button>
        </nav>
        <div ref="scrollBody" class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-5 sm:px-6">
          <AdminConversationMetrics v-if="activeTab === 'overview' || activeTab === 'timing'" :stats="research.stats" :view="activeTab" />
          <template v-if="activeTab === 'technical'">
          <h3 class="admin-heading text-lg font-black">模型用量與研究素材</h3>
          <p class="admin-caption mt-2 text-xs font-semibold">
            共 {{ research.stats.llm_calls_total }} 次 LLM 呼叫（含 Task judge、開場、聊天、答案審查與修正）；Token 覆蓋
            {{ formatPercent(research.stats.token_usage_coverage) }}。快取輸入
            {{ research.stats.cached_prompt_tokens.toLocaleString() }}；推理 Token
            {{ research.stats.reasoning_tokens.toLocaleString() }}（已包含於輸出 Token）。
            <template v-if="research.stats.cost_usage_complete && research.stats.estimated_cost_usd != null">
              估計成本 {{ formatEstimatedTwd(research.stats.estimated_cost_usd, rate) }}（{{ formatUsd(research.stats.estimated_cost_usd) }}）。
            </template>
            <template v-else>成本資料不完整；下表保留已知費用，不代表完整總額。</template>
          </p>

          <section class="mt-5 border-y border-[var(--admin-border)] py-4">
            <h3 class="admin-heading mb-3 text-base font-bold">本次活動分環節用量</h3>
            <AdminLlmUsageTable :rows="research.stats.usage_breakdown || []" />
          </section>
          </template>
            <section v-if="activeTab === 'transcript'">
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
                  <div class="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-current/20 pt-2 text-xs leading-5 opacity-90">
                    <span>{{ metricNumber(messageMetrics.get(message.id || '')?.characters) }} 字</span>
                    <span v-if="message.metadata?.system_fallback">系統備援訊息</span>
                    <template v-else-if="message.speaker_type !== 'learner'">
                      <span>生成 Token：{{ metricNumber(messageMetrics.get(message.id || '')?.total_tokens) }}{{ messageMetrics.get(message.id || '')?.total_tokens != null && !messageMetrics.get(message.id || '')?.token_usage_complete ? '（僅已知）' : '' }}</span>
                      <span>輸出 Token：{{ metricNumber(messageMetrics.get(message.id || '')?.completion_tokens) }}</span>
                    </template>
                    <template v-if="messageTurns.get(message.id || '')">
                      <span>第 {{ messageTurns.get(message.id || '')?.index }} 輪</span>
                      <span>回覆等待：{{ metricDuration(messageTurns.get(message.id || '')?.response_seconds) }}</span>
                    </template>
                  </div>
                  <AdminAnswerReviewDetails v-if="message.metadata?.answer_review || message.metadata?.answer_delivery" :review="message.metadata.answer_review" :delivery="message.metadata.answer_delivery" />
                </article>
              </div>
              <div v-else class="admin-empty-state p-5">此 Session 尚未建立對話。</div>
            </section>

            <aside v-if="activeTab === 'technical'" class="mt-5 space-y-4">
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
                  <dt class="admin-caption font-bold">倒數截止</dt>
                  <dd class="admin-copy font-semibold">{{ formatDate(research.session.timer_ends_at) }}</dd>
                  <dt class="admin-caption font-bold">實際完成</dt>
                  <dd class="admin-copy font-semibold">{{ formatDate(research.session.completed_at) }}</dd>
                  <dt class="admin-caption font-bold">訊息跨度</dt>
                  <dd class="admin-copy font-semibold">{{ formatDuration(research.stats.duration_seconds) }}</dd>
                </dl>
              </section>
            </aside>
        </div>
      </section>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import type { AdminSessionResearchResponse } from '~/types';
import { useAdminCostEstimate } from '~/composables/useAdminCostEstimate';
import { useBodyScrollLock } from '~/composables/useBodyScrollLock';
import { formatCallCost, formatEstimatedTwd } from '~/utils/adminLlmUsage';
import { experimentConditionCodes, experimentConditionCodeByKey, experimentConditionLabels } from '~/utils/experimentConditions';
import { metricDate, metricDuration, metricNumber } from '~/utils/adminConversationMetrics';

const props = defineProps<{ research: AdminSessionResearchResponse | null }>();
const { rate } = useAdminCostEstimate();
const emit = defineEmits<{ (event: 'close'): void; (event: 'refresh', sessionId: string): void }>();
type ResearchTab = 'overview' | 'timing' | 'transcript' | 'technical';
const activeTab = ref<ResearchTab>('overview');
const tabs: Array<{ id: ResearchTab; label: string }> = [
  { id: 'overview', label: '量化摘要' }, { id: 'timing', label: '逐輪與逐題時間' },
  { id: 'transcript', label: '完整對話' }, { id: 'technical', label: '模型與素材' },
];
const dialog = ref<HTMLElement | null>(null);
const scrollBody = ref<HTMLElement | null>(null);
let previousFocus: HTMLElement | null = null;
let focusRequest = 0;
useBodyScrollLock(() => Boolean(props.research));
const restoreDialog = () => {
  focusRequest += 1;
  if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
  previousFocus = null;
};
onMounted(() => {
  watch(() => props.research?.session.id, async (id, oldId) => {
    if (!id) {
      restoreDialog();
      return;
    }
    const request = ++focusRequest;
    activeTab.value = 'overview';
    if (!oldId) previousFocus = document.activeElement as HTMLElement;
    await nextTick();
    if (request === focusRequest) dialog.value?.focus({ preventScroll: true });
  }, { immediate: true });
});
onBeforeUnmount(restoreDialog);
watch(activeTab, () => { scrollBody.value?.scrollTo({ top: 0 }); }, { flush: 'post' });
const handleDialogKey = (event: KeyboardEvent) => {
  if (event.key === 'Escape') { event.preventDefault(); emit('close'); }
  if (event.key !== 'Tab' || !dialog.value) return;
  const items = [...dialog.value.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input, summary, [tabindex="0"]')].filter((item) => item.getClientRects().length);
  const first = items[0]; const last = items[items.length - 1];
  if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.value)) { event.preventDefault(); last?.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
};
const messageMetrics = computed(() => new Map((props.research?.stats.message_metrics || []).map((item) => [item.message_id, item])));
const messageTurns = computed(() => new Map((props.research?.stats.round_trips || []).flatMap((turn) => [
  [turn.learner_message_id, turn] as const,
  ...(turn.assistant_message_id ? [[turn.assistant_message_id, turn] as const] : []),
])));

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

const taskPayload = computed(() => JSON.stringify({
  response: props.research?.attempt?.response_payload || {},
  judgement: props.research?.attempt?.judgement_payload || {},
}, null, 2));

const shortId = (id: string) => `${id.slice(0, 8)}...${id.slice(-4)}`;
const formatPercent = (value: number) => `${Math.round(value * 100)}%`;
const formatUsd = (value: number) => `US$${value.toFixed(6)}`;
const formatDate = metricDate;
const formatDuration = metricDuration;
const promptStageLabel = (stage: string) => stage === 'conversation_opening' ? '開場回覆' : '對話回覆';
const llmLabel = (llmCall?: Record<string, unknown> | null) => {
  if (!llmCall) return '未記錄模型用量';
  const total = llmCall.total_tokens == null ? 'Token 未回報' : `${llmCall.total_tokens} tokens`;
  return `${llmCall.provider || 'unknown'} / ${llmCall.model || 'unknown'} · ${total} · ${formatCallCost(llmCall, rate.value)}`;
};
</script>
