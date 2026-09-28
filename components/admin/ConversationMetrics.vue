<template>
  <div class="space-y-6">
    <template v-if="view === 'overview'">
      <section aria-label="對話量化摘要">
        <h3 class="admin-heading text-lg font-black">對話量化摘要</h3>
        <p class="admin-caption mt-1 text-xs leading-6">字數、完成來回與 AI 生成用量，皆以這次活動的對話為範圍。</p>
        <div class="research-metric-grid mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-[var(--admin-border)] bg-[var(--admin-border)] lg:grid-cols-3">
          <div v-for="item in cards" :key="item.label" class="bg-[var(--admin-surface)] p-4">
            <p class="admin-caption text-xs font-bold">{{ item.label }}</p>
            <p class="admin-heading mt-2 text-2xl font-black tabular-nums">{{ item.value }}</p>
            <p class="admin-caption mt-2 text-xs leading-5">{{ item.detail }}</p>
          </div>
        </div>
      </section>
      <section class="research-learning-summary rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] p-4" aria-label="學習時間摘要">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h3 class="admin-heading font-black">每題學習時間</h3>
          <span class="admin-badge">{{ learning?.is_complete ? '已結束' : '截至本次載入' }}</span>
        </div>
        <div class="mt-4 grid gap-4 sm:grid-cols-3">
          <div><p class="admin-caption text-xs font-bold">總學習時間</p><p class="admin-heading mt-2 text-xl font-black">{{ metricDuration(learning?.duration_seconds) }}</p></div>
          <div><p class="admin-caption text-xs font-bold">成功修正題數</p><p class="admin-heading mt-2 text-xl font-black">{{ learning?.applicable ? `${learning.corrected_questions} 題` : '不適用' }}</p></div>
          <div><p class="admin-caption text-xs font-bold">平均每題學習時間</p><p class="admin-heading mt-2 text-xl font-black">{{ learning?.applicable ? metricDuration(learning.average_seconds_per_question) : '不適用' }}</p></div>
        </div>
        <p v-if="learning?.applicable" class="admin-caption mt-4 text-xs leading-6">
          {{ metricDuration(learning.duration_seconds) }} ÷ {{ learning.denominator }} 題。{{ learning.corrected_questions === 0 ? '尚無修正成功題目，依規則以 1 題計算。' : '分母為成功修正的不同題目數。' }}
          時間包含閱讀、思考與 AI 等待；進行中的數值可按右上角重新載入更新。
        </p>
        <p v-else class="admin-caption mt-4 text-xs leading-6">此紀錄尚無可辨識的討論題目。</p>
        <p v-if="learning?.timing_source === 'message_timestamps'" class="mt-2 text-xs text-[var(--admin-coffee)]">舊紀錄缺少開始計時資料，學習時間依訊息時間推估。</p>
      </section>
      <details class="border-t border-[var(--admin-border)] pt-4">
        <summary class="admin-copy cursor-pointer text-sm font-bold">統計口徑與資料完整度</summary>
        <ul class="admin-caption mt-3 list-disc space-y-2 pl-5 text-xs leading-6">
          <li>字數按 Unicode 字元計算，包含標點、不含空白與換行。Token 是模型用量，與字數不同。</li>
          <li>一來回是一則學生訊息及其成功送出的 AI 回覆；AI 開場、失敗與尚未回覆不計入完成來回。</li>
          <li>平均 AI Token = 已回報的 AI 生成輸入＋輸出 Token ÷ 有回報用量的 AI 訊息數。包含開場；未送出的候選回覆與答案審查另計於 Session 用量，系統提示不算 AI 生成。</li>
          <li>AI 用量已回報 {{ stats.llm_messages_with_usage }} / {{ stats.llm_messages_total }} 則。{{ stats.assistant_token_usage_complete ? 'AI 訊息用量完整。' : '資料不完整，總量與平均僅代表已知部分；未回報不當作 0。' }}</li>
          <li>Session 用量另含作答評分、答案審查、修正與失敗呼叫。整體呼叫回報率 {{ Math.round(stats.token_usage_coverage * 100) }}%；完整明細位於「模型與素材」。</li>
          <li>逐輪「閱讀／思考」從上一則 AI 回覆到學生送出；「回覆等待」從學生送出到 AI 回覆，含重試等待；「整輪」為兩者總和。</li>
        </ul>
      </details>
    </template>

    <template v-else>
      <section aria-label="逐題學習時間">
        <h3 class="admin-heading text-lg font-black">逐題學習時間</h3>
        <p class="admin-caption mt-1 text-xs leading-6">依討論題目分段，累計閱讀、思考及回覆等待。此表顯示各題實際討論時間；摘要的平均值另依成功修正題數計算。</p>
        <div v-if="learning?.questions.length" class="mt-3 overflow-x-auto rounded-lg border border-[var(--admin-border)]">
          <table class="w-full min-w-[670px] text-left text-sm tabular-nums">
            <thead class="bg-[var(--admin-surface-muted)] text-[var(--admin-copy-strong)]"><tr><th class="p-3">題目</th><th class="p-3">結果</th><th class="p-3 text-right">完成來回</th><th class="p-3 text-right">學習時間</th><th class="p-3">開始／結束</th></tr></thead>
            <tbody class="bg-[var(--admin-surface)]">
              <tr v-for="question in learning.questions" :key="question.question_id" class="border-t border-[var(--admin-border-soft)]">
                <th scope="row" class="p-3 font-bold"><span>{{ question.question_id.toUpperCase() }}</span><span v-if="question.origin === 'third_party'" class="admin-caption mt-1 block text-xs font-normal">第三方錯誤</span></th>
                <td class="p-3">{{ questionOutcomeLabel(question.outcome) }}</td>
                <td class="p-3 text-right">{{ question.completed_exchanges }}</td>
                <td class="p-3 text-right font-bold">{{ metricDuration(question.duration_seconds) }}<span v-if="question.timing_source !== 'recorded'" class="admin-caption mt-1 block text-xs font-normal">{{ question.timing_source === 'unavailable' ? '時間不足' : '依舊紀錄推估' }}</span></td>
                <td class="admin-caption p-3 text-xs leading-6">{{ metricDate(question.started_at) }}<br>{{ question.outcome === 'in_progress' ? '截至 ' : '' }}{{ question.ended_at ? metricDate(question.ended_at) : '進行中' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="admin-empty-state mt-3 p-4 text-sm">尚無逐題討論紀錄。</p>
      </section>
      <section aria-label="逐輪對話時間">
        <h3 class="admin-heading text-lg font-black">逐輪對話時間</h3>
        <p class="admin-caption mt-1 text-xs leading-6">共 {{ stats.completed_exchanges }} 次完成來回；保留失敗或尚未完成的送出紀錄。時間不足時顯示「未記錄」。</p>
        <div v-if="stats.round_trips?.length" class="mt-3 overflow-x-auto rounded-lg border border-[var(--admin-border)]">
          <table class="w-full min-w-[800px] text-left text-xs tabular-nums">
            <thead class="bg-[var(--admin-surface-muted)] text-[var(--admin-copy-strong)]"><tr><th class="p-3">輪次／題目</th><th class="p-3">狀態</th><th class="p-3">送出時間</th><th class="p-3 text-right">閱讀／思考</th><th class="p-3 text-right">回覆等待</th><th class="p-3 text-right">整輪耗時</th><th class="p-3">時間來源</th></tr></thead>
            <tbody class="bg-[var(--admin-surface)]">
              <tr v-for="turn in stats.round_trips" :key="turn.learner_message_id" class="border-t border-[var(--admin-border-soft)]">
                <th scope="row" class="p-3">#{{ turn.index }}<span class="admin-caption mt-1 block font-normal">{{ turn.question_id?.toUpperCase() || '未指定題目' }}</span></th>
                <td class="p-3">{{ roundStatusLabel(turn.status) }}</td><td class="admin-caption p-3">{{ metricDate(turn.started_at) }}</td>
                <td class="p-3 text-right">{{ metricDuration(turn.thinking_seconds) }}</td><td class="p-3 text-right">{{ metricDuration(turn.response_seconds) }}</td><td class="p-3 text-right font-bold">{{ metricDuration(turn.elapsed_seconds) }}</td>
                <td class="admin-caption p-3">{{ turn.timing_source === 'recorded' ? '已記錄' : turn.timing_source === 'message_timestamps' ? '舊紀錄推估' : '未記錄' }}<span v-if="turn.generation_seconds != null" class="mt-1 block">本次處理 {{ metricDuration(turn.generation_seconds) }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="admin-empty-state mt-3 p-4 text-sm">尚無學生送出訊息。</p>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { AdminConversationStats } from '~/types';
import { metricDate, metricDuration, metricNumber, questionOutcomeLabel, roundStatusLabel } from '~/utils/adminConversationMetrics';
const props = defineProps<{ stats: AdminConversationStats; view: 'overview' | 'timing' }>();
const learning = computed(() => props.stats.learning);
const cards = computed(() => {
  const s = props.stats;
  const partial = s.assistant_token_usage_complete ? '' : '（僅已知）';
  return [
    { label: '對話總字數', value: metricNumber(s.total_characters), detail: `學生 ${metricNumber(s.learner_characters)} 字 · AI ${metricNumber(s.assistant_characters)} 字${s.system_characters ? ` · 系統 ${metricNumber(s.system_characters)} 字` : ''}` },
    { label: '完成來回次數', value: `${s.completed_exchanges} 次`, detail: `學生 ${s.learner_messages} 則 · AI ${s.assistant_messages} 則` },
    { label: `平均每則 AI Token${partial}`, value: metricNumber(s.assistant_average_tokens), detail: `${s.llm_messages_with_usage} 則有用量的 AI 訊息 · 含輸入與輸出` },
    { label: `AI 訊息總 Token${partial}`, value: metricNumber(s.assistant_total_tokens), detail: '包含開場與對話生成' },
    { label: `Session 總 Token${s.token_usage_complete ? '' : '（僅已知）'}`, value: s.llm_calls_with_usage ? metricNumber(s.total_tokens) : '未回報', detail: `含評分、審查與修正 · ${s.llm_calls_total} 次模型呼叫` },
    { label: '對話總訊息數', value: `${s.total_messages} 則`, detail: `首末訊息跨度 ${metricDuration(s.duration_seconds)}` },
  ];
});
</script>
