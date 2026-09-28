<template>
  <div class="min-w-0 space-y-3">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <label class="flex flex-wrap items-center gap-2 text-xs font-semibold text-[var(--admin-copy)]">
        自訂估算匯率：1 USD =
        <input v-model.number="rate" type="number" min="0.0001" max="1000" step="0.01" aria-label="美元換台幣估算匯率"
          :aria-invalid="!validEstimateRate(rate)" class="admin-field w-24 px-2 py-2 text-right tabular-nums" />
        TWD
      </label>
      <p class="text-sm font-semibold text-[var(--admin-copy-strong)]">
        {{ total.cost_reported_requests === total.requests && total.requests ? '估計總額' : '已記錄費用' }}：
        {{ total.cost_reported_requests || total.estimated_known_cost_usd > 0 ? formatEstimatedTwd(total.estimated_known_cost_usd, rate) : '未能估算' }}
      </p>
    </div>
    <p v-if="!validEstimateRate(rate)" role="alert" class="admin-error px-3 py-2 text-sm">匯率需大於 0 且不超過 1000。</p>
    <p class="admin-caption text-xs leading-6">非即時匯率。費用依模型回報與價格表估算，未含匯差、稅費及手續費，不是帳戶實際扣款。請求次數包含重試，不等於對話來回數。</p>
    <div v-if="rows.length" class="max-h-[28rem] overflow-auto rounded border border-[var(--admin-border)]" tabindex="0" aria-label="分環節 LLM 用量">
      <table class="w-full min-w-[650px] border-collapse text-left text-xs tabular-nums">
        <thead class="sticky top-0 z-10 bg-[var(--admin-surface-muted)] text-[var(--admin-copy-strong)]">
          <tr><th class="px-3 py-3">環節／模型</th><th class="px-3 py-3 text-right">請求</th><th class="px-3 py-3 text-right">輸入 Token</th><th class="px-3 py-3 text-right">輸出 Token</th><th class="px-3 py-3 text-right">總 Token</th><th class="px-3 py-3 text-right">估計台幣</th></tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="`${row.stage}:${row.provider}:${row.model}`" class="border-t border-[var(--admin-border-soft)] bg-[var(--admin-surface)] align-top">
            <th scope="row" class="max-w-64 break-words px-3 py-3 font-semibold">
              {{ llmStageLabel(row.stage) }}
              <span class="admin-caption mt-1 block break-all text-[11px] font-normal">{{ row.provider }} · {{ row.model }}</span>
              <span v-if="row.token_reported_requests < row.requests" class="mt-1 block text-[var(--admin-coffee)]">{{ row.requests - row.token_reported_requests }} 次用量未完整回報</span>
            </th>
            <td class="px-3 py-3 text-right">{{ row.requests }}</td>
            <td class="px-3 py-3 text-right">{{ tokenText(row, 'prompt_tokens') }}</td>
            <td class="px-3 py-3 text-right">{{ tokenText(row, 'completion_tokens') }}</td>
            <td class="px-3 py-3 text-right">{{ tokenText(row, 'total_tokens') }}</td>
            <td class="px-3 py-3 text-right">
              <span class="whitespace-nowrap">{{ row.cost_reported_requests || row.estimated_known_cost_usd > 0 ? formatEstimatedTwd(row.estimated_known_cost_usd, rate) : '未回報' }}</span>
              <span v-if="row.cost_reported_requests || row.estimated_known_cost_usd > 0" class="admin-caption mt-1 block whitespace-nowrap">US${{ row.estimated_known_cost_usd.toFixed(6) }}</span>
              <span v-if="row.cost_reported_requests < row.requests" class="mt-1 block text-[var(--admin-coffee)]">未完整（{{ row.requests - row.cost_reported_requests }} 次）</span>
            </td>
          </tr>
        </tbody>
        <tfoot class="border-t border-[var(--admin-border)] bg-[var(--admin-surface-muted)] font-semibold">
          <tr><th class="px-3 py-3">已記錄合計</th><td class="px-3 py-3 text-right">{{ total.requests }}</td><td class="px-3 py-3 text-right">{{ tokenText(total, 'prompt_tokens') }}</td><td class="px-3 py-3 text-right">{{ tokenText(total, 'completion_tokens') }}</td><td class="px-3 py-3 text-right">{{ tokenText(total, 'total_tokens') }}</td><td class="px-3 py-3 text-right">{{ total.cost_reported_requests || total.estimated_known_cost_usd > 0 ? formatEstimatedTwd(total.estimated_known_cost_usd, rate) : '未回報' }}</td></tr>
        </tfoot>
      </table>
    </div>
    <p v-else class="admin-caption py-3 text-sm">尚無可顯示的 LLM 用量紀錄。</p>
    <p v-if="total.requests > total.cost_reported_requests || total.requests > total.token_reported_requests" role="status" class="text-xs leading-6 text-[var(--admin-coffee)]">合計僅含已記錄數值；未回報或舊版不完整紀錄的實際用量與費用仍未知，不能當成零。</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { AdminLLMUsageRow } from '~/types';
import { useAdminCostEstimate } from '~/composables/useAdminCostEstimate';
import { formatEstimatedTwd, llmStageLabel, sumUsageRows, validEstimateRate } from '~/utils/adminLlmUsage';
const props = defineProps<{ rows: AdminLLMUsageRow[] }>();
const { rate } = useAdminCostEstimate();
const total = computed(() => sumUsageRows(props.rows));
const tokenText = (row: AdminLLMUsageRow, field: 'prompt_tokens' | 'completion_tokens' | 'total_tokens') =>
  row.token_reported_requests || row.total_tokens > 0 ? row[field].toLocaleString() : '未回報';
</script>
