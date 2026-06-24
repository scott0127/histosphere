<template>
  <!-- 首頁頂部導覽：只放品牌、重新整理與 admin 入口，避免混入事件流程邏輯。 -->
  <header class="relative z-20 border-b border-[var(--admin-border)] bg-[rgba(255,253,248,0.92)] shadow-sm backdrop-blur-sm">
    <div class="mx-auto flex max-w-7xl items-center justify-between px-5 py-3">
      <NuxtLink to="/" class="flex items-center gap-3">
        <span class="flex h-10 w-10 items-center justify-center rounded-full border-2 border-[var(--admin-line)] bg-[var(--admin-surface)] text-[var(--admin-coffee)] shadow-[0_3px_0_rgba(47,41,36,0.18)]">
          <Icon name="mdi:book-open-page-variant" class="h-5 w-5" />
        </span>
        <span>
          <span class="block font-serif text-lg font-bold tracking-[0.08em] text-[var(--admin-text)]">Histosphere</span>
          <span class="block text-xs font-semibold tracking-[0.08em] text-[var(--admin-copy)]">歷史對話學習實驗</span>
        </span>
      </NuxtLink>

      <div class="flex items-center gap-2">
        <AdminModeSwitch
          :is-authenticated="isAuthenticated"
          :is-admin-mode="isAdminMode"
          :view-mode="adminViewMode"
          :display-name="displayName"
          :admin-mode-pending="adminModePending"
          :admin-mode-error="adminModeError"
          @enter-admin-mode="$emit('enter-admin-mode', $event)"
          @exit-admin-mode="$emit('exit-admin-mode')"
          @update:view-mode="$emit('update:admin-view-mode', $event)"
        />
        <button
          type="button"
          class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[var(--admin-border)] bg-[var(--admin-surface-muted)] text-[var(--admin-coffee)] transition hover:bg-[var(--admin-coffee-soft)]"
          title="重新整理事件"
          @click="$emit('refresh')"
        >
          <Icon name="mdi:history" class="h-5 w-5" :class="{ 'animate-spin': isRefreshing }" />
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
// EventLibraryHeader 是純導覽元件；重新整理由 page 接收事件後執行。
import type { AdminViewMode } from '~/composables/useAdminMode';

defineProps<{
  isRefreshing: boolean;
  isAuthenticated: boolean;
  isAdminMode: boolean;
  adminViewMode: AdminViewMode;
  displayName: string | null;
  adminModePending: boolean;
  adminModeError: string | null;
}>();

defineEmits<{
  (event: 'refresh'): void;
  (event: 'enter-admin-mode', adminKey: string): void;
  (event: 'exit-admin-mode'): void;
  (event: 'update:admin-view-mode', value: AdminViewMode): void;
}>();
</script>
