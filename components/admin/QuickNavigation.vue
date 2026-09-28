<template>
  <nav aria-label="管理員快速跳轉" class="admin-quick-navigation">
    <template v-for="(item, index) in items" :key="item.target">
      <span v-if="index" aria-hidden="true" class="admin-quick-connector" />
      <button type="button" class="admin-quick-link" :title="item.title" :aria-label="item.title" @click="$emit('jump', item.target)">
        <Icon :name="item.icon" class="admin-quick-icon" aria-hidden="true" />
        <span>{{ item.label }}</span>
      </button>
    </template>
  </nav>
</template>

<script setup lang="ts">
defineEmits<{ (event: 'jump', target: string): void }>();
const items = [
  { target: 'admin-top', label: '頂部', title: '回到管理頁頂部', icon: 'mdi:arrow-collapse-up' },
  { target: 'participant-research', label: '受測者', title: '跳到受測者與對話數據', icon: 'mdi:account-multiple-outline' },
  { target: 'model-usage', label: '用量', title: '跳到整體 Token 用量', icon: 'mdi:chart-box-outline' },
  { target: 'research-exports', label: '匯出', title: '跳到研究操作紀錄與匯出', icon: 'mdi:tray-arrow-down' },
  { target: 'admin-materials', label: '素材', title: '跳到歷史事件與素材管理', icon: 'mdi:view-grid-outline' },
  { target: 'admin-bottom', label: '底部', title: '跳到管理頁最下方', icon: 'mdi:arrow-collapse-down' },
];
</script>

<style scoped>
.admin-quick-navigation {
  position: fixed;
  z-index: 40;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 7px;
  border: 1px solid rgba(93, 73, 58, 0.1);
  border-radius: 48px;
  /* A restrained web material treatment inspired by iOS, not a native Apple material. */
  background: rgba(255, 253, 248, 0.97);
  -webkit-backdrop-filter: blur(12px) saturate(115%);
  backdrop-filter: blur(12px) saturate(115%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.94),
    0 2px 4px rgba(65, 55, 47, 0.025),
    0 12px 30px rgba(65, 55, 47, 0.07);
}
.admin-quick-link {
  display: flex;
  width: 48px;
  height: 48px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  flex-shrink: 0;
  border: 0;
  border-radius: 50%;
  color: var(--admin-coffee);
  background: transparent;
  font-family: inherit;
  cursor: pointer;
  transition: background-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
}
.admin-quick-icon { width: 21px; height: 21px; }
.admin-quick-link > span:last-child { font-family: inherit; font-size: 11px; font-weight: 500; }
.admin-quick-link:hover,
.admin-quick-link:focus-visible {
  background: var(--admin-coffee-soft);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8), 0 2px 5px rgba(65, 55, 47, 0.07);
}
.admin-quick-link:focus-visible { outline: 2px solid var(--admin-coffee); outline-offset: 3px; }
.admin-quick-link:active { transform: scale(0.96); box-shadow: inset 0 1px 2px rgba(65, 55, 47, 0.08); }
.admin-quick-connector { display: none; }
@media (max-width: 1023px), (max-height: 620px) {
  .admin-quick-navigation { top: auto; bottom: max(10px, env(safe-area-inset-bottom)); right: 50%; transform: translateX(50%); flex-direction: row; gap: 5px; padding: 7px; }
  .admin-quick-link { width: 46px; height: 46px; }
  .admin-quick-icon { width: 20px; height: 20px; }
  .admin-quick-connector { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .admin-quick-link { transition: none; }
  .admin-quick-link:active { transform: none; }
}
@media (prefers-reduced-transparency: reduce) {
  .admin-quick-navigation {
    background: var(--admin-surface);
    -webkit-backdrop-filter: none;
    backdrop-filter: none;
  }
}
</style>
