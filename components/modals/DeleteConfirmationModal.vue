<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
    <div class="bg-history-cream border-2 border-history-dark p-8 rounded-xl shadow-2xl max-w-md w-full mx-4 text-center relative ring-4 ring-history-paper">
      <div class="absolute -top-6 left-1/2 transform -translate-x-1/2 bg-red-600 text-history-paper p-3 rounded-full border-4 border-history-cream shadow-lg">
          <Icon name="mdi:trash-can-outline" class="w-8 h-8" />
      </div>
      <h3 class="text-2xl font-bold text-history-dark mt-6 mb-2 tracking-wide">確認刪除？</h3>
      <p class="text-history-brown mb-8 font-medium leading-relaxed">
        您確定要刪除此歷史事件嗎？<br>
        此操作將無法復原，所有相關的對話記錄也將一併消失。
      </p>
      <div class="flex gap-4 justify-center">
        <button 
          @click="$emit('cancel')" 
          class="px-6 py-3 bg-history-light text-history-brown font-bold rounded-lg hover:bg-history-brown/20 transition-colors border-2 border-history-brown/20 shadow-sm"
        >
          取消
        </button>
        <button 
          @click="$emit('confirm')" 
          class="px-6 py-3 bg-red-600 text-white font-bold rounded-lg hover:bg-red-700 transition-colors border-2 border-red-800 shadow-md hover:-translate-y-0.5 active:translate-y-0"
        >
          確認刪除
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  show: boolean;
}>();

defineEmits<{
  (e: 'confirm'): void;
  (e: 'cancel'): void;
}>();
</script>

<style scoped>
@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
.animate-fade-in {
  animation: fade-in 0.2s ease-out;
}
</style>
