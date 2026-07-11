<template>
  <ConfirmActionModal
    :show="show"
    title="封存歷史事件"
    message="封存後 Learner 不會再看到這個事件，但所有 task、session、對話與研究紀錄都會完整保留。"
    eyebrow="素材管理"
    icon="mdi:archive-arrow-down-outline"
    confirm-label="封存"
    cancel-label="取消"
    @confirm="$emit('confirm')"
    @cancel="$emit('cancel')"
  />
</template>

<script setup lang="ts">
import ConfirmActionModal from '~/components/modals/ConfirmActionModal.vue';

defineProps<{ show: boolean }>();

defineEmits<{
  (event: 'confirm'): void;
  (event: 'cancel'): void;
}>();
</script>
