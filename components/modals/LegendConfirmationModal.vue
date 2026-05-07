<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
    <div class="relative bg-history-paper text-history-dark w-full max-w-md rounded-xl shadow-2xl p-6 border-2 border-history-brown/30 ring-4 ring-history-paper">
        <div class="flex flex-col items-center text-center">
          <div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4 text-purple-600">
            <Icon name="mdi:unicorn-variant" class="w-10 h-10" />
          </div>
          
          <h3 class="text-2xl font-bold font-serif mb-2 text-history-dark">確定進入傳說？</h3>
          
          <p class="text-history-brown/80 mb-6 leading-relaxed">
            您創建的<span class="font-bold text-purple-700">「{{ eventName }}」</span>被判定為民間傳說或文學作品，其中的人物與情節可能並非真實歷史記錄。
          </p>
          
          <div class="flex gap-4 w-full">
            <button 
              @click="$emit('cancel')"
              class="flex-1 py-3 px-4 border-2 border-history-brown/20 rounded-lg text-history-brown font-bold hover:bg-history-brown/5 transition-colors"
            >
              留在列表
            </button>
            <button 
              @click="$emit('confirm')"
              class="flex-1 py-3 px-4 bg-purple-600 text-white rounded-lg font-bold shadow-md hover:bg-purple-700 transition-colors flex items-center justify-center gap-2"
            >
              <Icon name="mdi:check" class="w-5 h-5" />
              了解並進入
            </button>
          </div>
        </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  show: boolean;
  eventName: string;
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
