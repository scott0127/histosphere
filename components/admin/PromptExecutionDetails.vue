<script setup lang="ts">
import type { AdminPromptDryRunResponse } from '~/types';

defineProps<{ result: AdminPromptDryRunResponse }>();

const pathLabels = {
  base: '基底提示詞',
  repair: '基底提示詞＋修正指令',
  constrained: '受限恢復引導',
  system_fallback: '系統固定提示',
};
</script>

<template>
  <section class="mt-4 border-t border-[var(--admin-border)] pt-3" aria-label="本次試跑提示詞">
    <p class="admin-label">
      本次回覆採用：{{ pathLabels[result.final_prompt_kind] }}<template v-if="result.schema_repair_count && result.final_prompt_kind !== 'system_fallback'">＋JSON 格式修復</template>
    </p>
    <p v-if="result.final_prompt_kind === 'system_fallback'" class="admin-copy mt-2 text-xs leading-5">
      本次顯示系統固定提示，沒有產生此回覆的 LLM 提示詞。下方基底模組僅供檢查首次組裝內容。
    </p>
    <p v-else-if="result.final_prompt_kind === 'constrained'" class="admin-copy mt-2 text-xs leading-5">
      最後採用受限恢復引導，只保留人物語氣、題文與學習者原話；完整 EBL 策略、答案與歷史材料未沿用。
    </p>
    <p v-else class="admin-copy mt-2 text-xs leading-5">
      {{ result.condition.roleplay_enabled ? '包含歷史人物設定' : '一般 AI，未使用人物設定' }}；
      {{ result.condition.ebl_enabled ? '包含 EBL 引導' : '未使用 EBL 引導' }}。
      <template v-if="result.final_prompt_kind === 'repair'">下方已包含最後一次生成使用的修正指令。</template>
    </p>
    <details v-if="result.final_messages.length && result.final_prompt_kind !== 'system_fallback'" class="mt-3" open>
      <summary class="admin-label cursor-pointer">最後實際送出的 LLM 訊息</summary>
      <p class="admin-caption mt-1 text-xs leading-5">
        這是產生本次回覆時實際交給 LiteLLM 的 messages，包含 system、JSON 輸出指令及 user 內容。
        <template v-if="result.schema_repair_count">已包含最後一次 JSON 格式修復指令與前次輸出。</template>
      </p>
      <div v-for="(message, index) in result.final_messages" :key="index" class="mt-2">
        <p class="admin-label">{{ message.role }}</p>
        <pre class="admin-code-editor mt-1 max-h-[360px] overflow-auto whitespace-pre-wrap break-words rounded-md border border-[var(--admin-border)] bg-[var(--admin-panel)] p-3 text-xs leading-5">{{ message.content }}</pre>
      </div>
    </details>
    <p v-else-if="result.final_prompt_kind !== 'system_fallback'" class="admin-caption mt-2 text-xs">此回覆沒有保留實際請求訊息，不能以基底預覽代替。</p>
    <details v-if="result.final_prompt" class="mt-3">
      <summary class="admin-label cursor-pointer">生成流程提示詞（Provider 加入外層指令前）</summary>
      <pre class="admin-code-editor mt-2 max-h-[240px] overflow-auto whitespace-pre-wrap break-words rounded-md border border-[var(--admin-border)] p-2 text-xs leading-5">{{ result.final_prompt }}</pre>
    </details>
    <details class="mt-3">
      <summary class="admin-label cursor-pointer">首次組裝的基底模組（供比對）</summary>
      <p class="admin-caption mt-1 text-xs leading-5">此清單描述最初組裝，不代表恢復引導沿用全部模組。</p>
      <details v-for="module in result.modules" :key="module.name" class="mt-2">
        <summary class="admin-copy cursor-pointer text-xs font-bold">{{ module.name }}</summary>
        <pre class="admin-code-editor mt-1 max-h-[240px] overflow-auto whitespace-pre-wrap break-words rounded-md border border-[var(--admin-border)] p-2 text-xs leading-5">{{ module.content }}</pre>
      </details>
    </details>
  </section>
</template>
