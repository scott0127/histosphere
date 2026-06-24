<template>
  <!-- 顯示研究者編輯 task 時的前端格式檢查結果。 -->
  <div
    class="border px-3 py-2 text-sm"
    :class="issues.length ? 'admin-validation-warning' : 'admin-validation-ok'"
  >
    <p class="font-semibold">{{ issues.length ? '需要確認' : '格式檢查通過' }}</p>
    <ul v-if="issues.length" class="mt-1 list-disc space-y-1 pl-5">
      <li v-for="issue in issues" :key="issue">{{ issue }}</li>
    </ul>
  </div>
</template>

<script setup lang="ts">
// TaskControlValidation 只做前端格式提示，不取代後端儲存與 LLM 評分檢查。
defineProps<{
  issues: string[];
}>();
</script>
