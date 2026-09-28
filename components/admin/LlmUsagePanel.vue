<template>
  <section class="admin-panel">
    <button class="admin-accordion-header" type="button" :aria-expanded="open" @click="toggle">
      <span class="admin-section-heading">
        <span class="admin-section-icon" aria-hidden="true"><Icon name="mdi:tag-outline" /></span>
        <span><span class="admin-kicker">LLM usage</span><span class="admin-accordion-title">LLM 用量與估計費用</span></span>
      </span>
      <Icon :name="open ? 'mdi:chevron-down' : 'mdi:arrow-right'" class="h-5 w-5" />
    </button>
    <div v-if="open" class="admin-accordion-body space-y-4">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0 text-xs leading-6 text-[var(--admin-copy)]">
          <p>本機用量帳本，包含正式活動、Admin 測試、素材生成與開發測試。不是單一受測者費用，也不是 API 帳戶總帳。</p>
          <p v-if="data?.first_recorded_at">紀錄期間：{{ dateLabel(data.first_recorded_at) }} 至 {{ dateLabel(data.last_recorded_at) }}</p>
        </div>
        <button class="admin-button-secondary inline-flex h-10 w-10 shrink-0 items-center justify-center" :disabled="loading" type="button" title="更新用量" aria-label="更新用量" @click="load">
          <Icon name="mdi:refresh" class="h-5 w-5" :class="{ 'animate-spin': loading }" />
        </button>
      </div>
      <p v-if="loading" role="status" class="admin-caption text-sm">正在讀取用量紀錄…</p>
      <p v-if="error" role="alert" class="admin-error px-3 py-2 text-sm">{{ error }}</p>
      <template v-if="data">
        <p v-if="!data.log_available" class="text-sm text-[var(--admin-coffee)]">尚未建立本機帳本，無法回推更早的呼叫費用。</p>
        <p v-if="data.malformed_lines" class="text-sm text-[var(--admin-coffee)]">{{ data.malformed_lines }} 筆紀錄無法解析，以下合計可能不完整。</p>
        <AdminLlmUsageTable :rows="data.rows" />
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import type { AdminLLMUsageResponse } from '~/types';
import { fetchAdminLlmUsage } from '~/utils/histosphereApi';
const props = defineProps<{ adminKey: string }>();
const open = ref(false);
const loading = ref(false);
const error = ref('');
const data = ref<AdminLLMUsageResponse | null>(null);
let requestVersion = 0;
async function load() {
  const version = ++requestVersion;
  loading.value = true;
  error.value = '';
  try {
    const result = await fetchAdminLlmUsage(props.adminKey);
    if (version === requestVersion) data.value = result;
  } catch {
    if (version === requestVersion) { data.value = null; error.value = '無法載入用量紀錄，請確認管理權限或稍後重試。'; }
  } finally { if (version === requestVersion) loading.value = false; }
}
function toggle() { open.value = !open.value; if (open.value && !data.value) void load(); }
function expand() { open.value = true; if (!data.value && !loading.value) void load(); }
defineExpose({ expand });
watch(() => props.adminKey, () => { requestVersion++; data.value = null; error.value = ''; loading.value = false; open.value = false; });
const dateLabel = (value?: string | null) => value ? new Date(value).toLocaleString('zh-TW') : '未記錄';
</script>
