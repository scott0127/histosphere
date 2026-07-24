<template>
  <div class="flex flex-wrap items-center justify-end gap-2">
    <form
      v-if="!isAdminMode"
      class="admin-mode-key-form"
      @submit.prevent="submitAdminKey"
    >
      <button
        v-if="!isKeyPanelOpen"
        type="button"
        class="admin-mode-link"
        @click="isKeyPanelOpen = true"
      >
        <Icon name="mdi:shield-account-outline" class="h-4 w-4" />
        進入 admin mode
      </button>

      <template v-else>
        <label for="adminModeKey" class="sr-only">Admin key</label>
        <input
          id="adminModeKey"
          v-model="adminKey"
          type="password"
          autocomplete="off"
          class="admin-mode-key-input"
          placeholder="Admin key"
        />
        <button
          type="submit"
          class="admin-mode-icon-button"
          :disabled="adminModePending || !adminKey.trim()"
          title="驗證 admin key"
        >
          <Icon :name="adminModePending ? 'mdi:loading' : 'mdi:check'" class="h-4 w-4" :class="{ 'animate-spin': adminModePending }" />
        </button>
        <button
          type="button"
          class="admin-mode-icon-button"
          title="取消"
          @click="closeKeyPanel"
        >
          <Icon name="mdi:close" class="h-4 w-4" />
        </button>
        <span v-if="adminModeError" class="admin-mode-error">{{ adminModeError }}</span>
      </template>
    </form>

    <div v-else class="admin-mode-shell">
      <div class="hidden min-w-0 max-w-[9rem] truncate px-2 text-xs font-bold text-[var(--admin-copy)] sm:block">
        {{ displayName || 'admin' }}
      </div>

      <div class="admin-mode-segment" role="group" aria-label="Admin view mode">
        <button
          type="button"
          :class="segmentClass('admin_mode')"
          title="管理與編輯系統資料"
          @click="$emit('update:view-mode', 'admin_mode')"
        >
          管理模式
        </button>
        <button
          type="button"
          :class="segmentClass('admin_testmode')"
          title="以受測者視角測試全部流程"
          @click="$emit('update:view-mode', 'admin_testmode')"
        >
          受測者測試
        </button>
      </div>

      <NuxtLink
        v-if="viewMode === 'admin_mode'"
        to="/admin"
        class="admin-mode-icon-button"
        title="開啟後台"
      >
        <Icon name="mdi:cog-outline" class="h-4 w-4" />
      </NuxtLink>

      <button
        type="button"
        class="admin-mode-icon-button"
        title="退出 admin mode"
        @click="$emit('exit-admin-mode')"
      >
        <Icon name="mdi:logout" class="h-4 w-4" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import type { AdminViewMode } from '~/utils/adminMode';

const props = defineProps<{
  isAdminMode: boolean;
  viewMode: AdminViewMode;
  displayName: string | null;
  adminModePending: boolean;
  adminModeError: string | null;
}>();

const emit = defineEmits<{
  (event: 'enter-admin-mode', adminKey: string): void;
  (event: 'exit-admin-mode'): void;
  (event: 'update:view-mode', value: AdminViewMode): void;
}>();

const adminKey = ref('');
const isKeyPanelOpen = ref(false);

const segmentClass = (mode: AdminViewMode) => [
  'admin-mode-segment-button',
  props.viewMode === mode ? 'admin-mode-segment-button-active' : 'admin-mode-segment-button-idle',
];

const submitAdminKey = () => {
  const trimmed = adminKey.value.trim();
  if (!trimmed || props.adminModePending) return;
  emit('enter-admin-mode', trimmed);
};

const closeKeyPanel = () => {
  adminKey.value = '';
  isKeyPanelOpen.value = false;
};

watch(
  () => props.isAdminMode,
  (enabled) => {
    if (enabled) {
      closeKeyPanel();
    }
  },
);
</script>
