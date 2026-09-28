<template>
  <!-- 送出區塊不顯示內部評分或理由回饋。 -->
  <div>
    <div v-if="judgement" class="rounded-[10px] border border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] p-4 text-sm text-[var(--admin-coffee)] shadow-[inset_0_1px_0_rgba(255,255,255,0.5)]">
      <p class="font-semibold">已送出</p>
      <p class="mt-1 leading-6">系統已保存你的回答。</p>
    </div>

    <p v-if="error" role="alert" class="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
      {{ error }}
    </p>

    <div class="flex justify-end" :class="compact ? '' : 'mt-5'">
      <button
        type="submit"
        :disabled="isSubmitting || !canSubmit"
        class="inline-flex items-center gap-2 rounded-[8px] border border-[var(--admin-coffee)] bg-[var(--admin-coffee)] px-5 py-3 text-sm font-bold text-[var(--admin-surface)] shadow-md transition hover:bg-[var(--admin-coffee-hover)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
      >
        <Icon v-if="isSubmitting" name="mdi:loading" class="h-5 w-5 animate-spin" />
        <Icon v-else name="mdi:message-processing-outline" class="h-5 w-5" />
        {{ isSubmitting ? '送出中' : '送出作答' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
// TaskStudentSubmitBar 不呼叫 API，只根據父層狀態顯示送出按鈕與回饋。
defineProps<{
  canSubmit: boolean;
  isSubmitting: boolean;
  error: string | null;
  judgement: Record<string, unknown> | null;
  compact?: boolean;
}>();

</script>
