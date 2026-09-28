<template>
  <section aria-labelledby="activity-guide-title" class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-6 shadow-sm sm:p-7">
    <p class="text-xs font-bold tracking-[0.15em] text-[var(--admin-coffee)]">活動指引</p>
    <h1 id="activity-guide-title" class="mt-3 text-lg font-semibold leading-8 text-[var(--admin-text)]">
      從<span class="hidden lg:inline">右側</span><span class="lg:hidden">下方</span>「我的活動」點選「開始活動」。
    </h1>
    <div v-if="allowSignOut" class="mt-5 flex items-center justify-between gap-3 border-t border-[var(--admin-border-soft)] pt-4">
      <span class="text-sm font-semibold text-[var(--admin-copy)]">{{ participantCode ? `受測者 ${participantCode}` : '已登入' }}</span>
      <button type="button" class="min-h-11 rounded-lg border border-[var(--admin-border)] px-4 text-sm font-bold text-[var(--admin-coffee)] transition hover:bg-[var(--admin-surface-muted)]" @click="$emit('sign-out')">登出</button>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{ participantCode?: string; allowSignOut?: boolean }>();
defineEmits<{ (event: 'sign-out'): void }>();

</script>
