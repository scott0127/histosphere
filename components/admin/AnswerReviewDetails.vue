<template>
  <details class="mt-3 border-t border-[var(--admin-border-soft)] pt-3 text-xs leading-6">
    <summary class="cursor-pointer font-bold">答案審查 · {{ deliveryData.mode ? outcomeLabel : statusLabel }}</summary>
    <template v-if="deliveryData.mode">
      <p class="admin-caption mt-2">先審查再顯示；以下草稿僅供管理員查閱，不是受測者的對話回合。</p>
      <p v-if="deliveryData.state_held">本回覆未推進錯誤修正進度。</p>
      <details v-for="(candidate, index) in candidates" :key="index" class="mt-3 border-l-2 border-[var(--admin-border)] pl-3">
        <summary class="cursor-pointer font-bold">{{ phaseLabel(candidate.phase) }} · {{ candidateLabel(candidate.status) }}</summary>
        <blockquote class="mt-2 whitespace-pre-wrap break-words">{{ candidate.response || '未取得完整回覆' }}</blockquote>
        <p v-if="candidate.failure_type">未完成原因：{{ candidate.failure_type }}</p>
        <p class="admin-caption mt-2">生成：{{ formatUsage(candidate.generation_call) }}</p>
        <p class="admin-caption">審查：{{ formatUsage(candidate.review_call) }}</p>
        <div v-for="(finding, n) in candidateFindings(candidate)" :key="n" class="mt-2">
          <p class="font-bold">{{ finding.severity === 'violation' ? '需要修正' : '疑慮' }} · {{ categoryLabel(finding.category) }}</p>
          <blockquote class="whitespace-pre-wrap break-words">「{{ finding.excerpt }}」</blockquote>
          <p class="admin-caption break-words">{{ finding.explanation }}</p>
        </div>
      </details>
    </template>
    <p v-else class="admin-caption mt-2">僅觀察，未攔截或改寫回覆。</p>
    <p class="admin-caption mt-2">沒有發現問題不代表保證無洩漏。</p>
    <p v-if="data.failure_type" class="mt-1">未完成原因：{{ data.failure_type }}</p>
    <div v-for="(finding, index) in findings" :key="index" class="mt-3 border-l-2 border-[var(--admin-coffee)] pl-3">
      <p class="font-bold">{{ finding.severity === 'violation' ? '觀察到問題' : '疑慮' }} · {{ categoryLabel(finding.category) }}</p>
      <blockquote class="mt-1 whitespace-pre-wrap break-words">「{{ finding.excerpt }}」</blockquote>
      <p class="admin-caption mt-1 break-words">{{ finding.explanation }}</p>
    </div>
    <p v-if="data.status === 'completed' && !findings.length" class="mt-2">本次未發現問題。</p>
    <p class="mt-2">{{ usageLabel }}</p>
    <dl class="admin-caption mt-2 space-y-1 break-all">
      <div><dt class="inline font-bold">政策：</dt><dd class="inline">{{ data.policy_version || '未記錄' }}</dd></div>
      <div><dt class="inline font-bold">回覆雜湊：</dt><dd class="inline font-mono">{{ data.response_sha256 || '未記錄' }}</dd></div>
      <div><dt class="inline font-bold">審查輸入雜湊：</dt><dd class="inline font-mono">{{ data.input_sha256 || '未記錄' }}</dd></div>
    </dl>
  </details>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ review?: unknown; delivery?: unknown }>();
const record = (value: unknown): Record<string, unknown> =>
  value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
const data = computed(() => record(props.review));
const deliveryData = computed(() => record(props.delivery));
const candidates = computed(() => Array.isArray(deliveryData.value.candidates) ? deliveryData.value.candidates.map(record) : []);
const candidateFindings = (candidate: Record<string, unknown>) => {
  const review = record(candidate.review);
  return Array.isArray(review.findings) ? review.findings.map(record) : [];
};
const outcomeLabel = computed(() => ({ accepted: '已送出審查後回覆', constrained: '已送出受限引導', system_fallback: '已使用系統提示' })[String(deliveryData.value.outcome)] || '處理中');
const phaseLabel = (value: unknown) => ({ initial: '首次草稿', repair: '修正草稿', constrained: '受限引導' })[String(value)] || String(value);
const candidateLabel = (value: unknown) => ({ accepted: '採用', rejected: '未顯示', unavailable: '無法完成', interrupted: '已中斷', review_pending: '審查未完成' })[String(value)] || String(value);
const findings = computed(() => Array.isArray(data.value.findings) ? data.value.findings.map(record) : []);
const statuses: Record<string, string> = { pending: '等待結果', completed: '已完成觀察', unavailable: '無法完成' };
const categories: Record<string, string> = {
  early_answer_exposure: '提前直接作答', next_answer_exposure: '提前提供下一題答案',
  corrective_feedback_missing: '收尾缺少必要修正',
};
const statusLabel = computed(() => statuses[String(data.value.status)] || '狀態未知');
const categoryLabel = (value: unknown) => categories[String(value)] || String(value);
const formatUsage = (value: unknown) => {
  const call = record(value);
  const tokens = call.total_tokens == null ? 'Token 尚未回報' : `${call.total_tokens} tokens`;
  const cost = typeof call.estimated_cost_usd === 'number' ? `US$${call.estimated_cost_usd.toFixed(6)}` : '費用未完整回報';
  const latency = typeof call.latency_ms === 'number' ? ` · ${(call.latency_ms / 1000).toFixed(1)} 秒` : '';
  return `${tokens} · ${cost}${latency}`;
};
const usageLabel = computed(() => formatUsage(data.value.llm_call));
</script>
