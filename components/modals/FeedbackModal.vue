<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
    <div class="relative bg-history-paper text-history-dark w-full max-w-md rounded-xl shadow-2xl p-6 border-2 border-history-brown/30">
      <button @click="$emit('close')" class="absolute top-4 right-4 text-history-brown/60 hover:text-history-dark">
        <Icon name="mdi:close" class="w-6 h-6" />
      </button>
      
      <div class="flex flex-col items-center text-center">
        <div class="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mb-4 text-emerald-600">
          <Icon name="mdi:message-draw" class="w-10 h-10" />
        </div>
        
        <h3 class="text-2xl font-bold font-serif mb-2 text-history-dark">意見回饋</h3>
        <p class="text-history-brown/80 mb-6">您的意見對我們非常重要！</p>
        
        <!-- Comment -->
        <div class="mb-4 w-full">
          <label class="block text-sm font-bold text-history-brown mb-2 text-left">您的意見</label>
          <textarea 
            v-model="comment"
            rows="4"
            class="w-full p-3 border-2 border-history-brown/20 rounded-lg focus:border-emerald-500 focus:outline-none resize-none"
            placeholder="請告訴我們您的使用體驗、建議或問題..."
          ></textarea>
        </div>
        
        <!-- Email (Optional) -->
        <div class="mb-6 w-full">
          <label class="block text-sm font-bold text-history-brown mb-2 text-left">聯繫方式 (選填)</label>
          <input 
            v-model="email"
            type="email"
            class="w-full p-3 border-2 border-history-brown/20 rounded-lg focus:border-emerald-500 focus:outline-none"
            placeholder="您的 Email (若希望我們回覆)"
          />
        </div>
        
        <!-- Submit -->
        <button 
          @click="submit"
          :disabled="isSubmitting"
          class="w-full py-3 bg-emerald-600 text-white rounded-lg font-bold shadow-md hover:bg-emerald-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <Icon v-if="isSubmitting" name="mdi:loading" class="w-5 h-5 animate-spin" />
          <Icon v-else name="mdi:send" class="w-5 h-5" />
          {{ isSubmitting ? '提交中...' : '送出回饋' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{
  show: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const comment = ref('');
const email = ref('');
const isSubmitting = ref(false);

const submit = async () => {
  if (!comment.value.trim()) {
    alert('請填寫您的意見');
    return;
  }
  
  isSubmitting.value = true;
  try {
    await $fetch('/api/feedback', {
      method: 'POST',
      body: {
        comment: comment.value,
        email: email.value
      }
    });
    
    alert('感謝您的寶貴意見！');
    emit('close');
    comment.value = '';
    email.value = '';
  } catch (e) {
    console.error('Failed to submit feedback:', e);
    alert('提交失敗，請稍後再試');
  } finally {
    isSubmitting.value = false;
  }
};
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
