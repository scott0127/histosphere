<template>
  <div class="flex flex-col items-center justify-center h-full text-history-dark p-4 text-center font-serif w-full">
    <div class="w-full max-w-md animate-card-appear bg-white/80 backdrop-blur-md border border-history-brown/10 shadow-xl shadow-history-brown/10 rounded-2xl p-6 md:p-8 md:bg-history-cream/90 md:border-2 md:border-history-dark md:ring-4 md:ring-history-paper md:shadow-[8px_8px_0px_0px_rgba(62,39,35,0.2)] md:rounded-xl">
      <!-- Icon -->
      <div class="flex justify-center mb-6">
        <div 
          @click="$emit('toggle-ui')"
          class="p-4 bg-history-paper rounded-full border border-history-brown/10 shadow-sm md:border-2 md:border-history-dark cursor-pointer hover:scale-110 hover:rotate-3 transition-transform duration-300"
          title="切換至書本模式"
        >
            <Icon name="mdi:book-open-page-variant" class="w-12 h-12 text-history-dark" />
        </div>
      </div>
      
      <!-- Title -->
      <h1 class="text-4xl font-bold mb-2 text-history-dark tracking-wider uppercase animate-title-fade">
        Echoes of Time
      </h1>
      <p class="text-history-brown mb-8 italic font-medium animate-subtitle-fade">輸入歷史事件，開啟時空對話</p>
      
      <form @submit.prevent="handleSubmit" class="space-y-6 animate-form-fade">
        <div class="relative group">
          <label for="event" class="sr-only">Historical Event</label>
          <input
            id="event"
            type="text"
            v-model="eventName"
            :placeholder="currentPlaceholder"
            class="w-full px-4 py-3 rounded-lg focus:outline-none transition-all font-sans text-lg shadow-inner bg-white/50 border border-history-brown/20 focus:bg-white focus:border-amber-400 focus:shadow-[0_0_15px_rgba(251,191,36,0.2)] placeholder-history-brown/40 text-history-dark md:bg-history-light md:border-2 md:border-history-brown md:focus:border-history-dark md:focus:ring-2 md:focus:ring-history-accent/30 md:placeholder-history-accent/70"
            :disabled="isLoading"
          />
          <!-- Glow effect on focus -->
          <div class="absolute inset-0 rounded-lg bg-history-accent/0 group-focus-within:bg-history-accent/5 transition-all pointer-events-none"></div>
        </div>
        <button
          type="submit"
          :disabled="isLoading || !eventName.trim()"
          class="w-full py-3 px-4 text-history-paper font-bold rounded-lg transition-all transform hover:-translate-y-1 hover:shadow-lg active:translate-y-0 flex items-center justify-center tracking-widest uppercase bg-gradient-to-r from-history-dark to-history-brown shadow-lg shadow-history-brown/20 md:bg-none md:bg-history-dark md:hover:bg-history-brown md:border-2 md:border-transparent md:hover:border-history-paper md:shadow-md disabled:bg-history-accent disabled:cursor-not-allowed disabled:bg-none"
        >
          <template v-if="isLoading">
            <Icon name="mdi:loading" class="animate-spin -ml-1 mr-3 h-5 w-5 text-history-paper" />
            翻閱史籍...
          </template>
          <template v-else>
            開始探索
          </template>
        </button>
      </form>
      <p v-if="error" class="mt-4 text-red-700 font-bold bg-red-100 px-2 py-1 rounded animate-shake">{{ error }}</p>
    </div>
    <footer class="absolute bottom-4 text-history-brown text-sm font-sans font-bold opacity-70">
      <div class="relative group cursor-help transition-all duration-300 hover:text-history-dark">
        <p>由 LKB 驅動</p>
        <span class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1 bg-history-dark/90 text-history-paper text-xs font-medium rounded shadow-lg opacity-0 group-hover:opacity-100 transition-all duration-300 transform translate-y-2 group-hover:translate-y-0 whitespace-nowrap pointer-events-none">
          404 Error Not Found 協助
          <!-- Little arrow -->
          <span class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-history-dark/90"></span>
        </span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

defineProps<{
  isLoading: boolean;
  error: string | null;
}>();

const emit = defineEmits<{
  (e: 'event-submit', eventName: string): void;
  (e: 'toggle-ui'): void;
}>();

const eventName = ref('');

// Rotating placeholder examples
const placeholders = [
  '例如：文藝復興...',
  '例如：法國大革命...',
  '例如：工業革命...',
  '例如：二戰諾曼第登陸...',
  '例如：唐朝安史之亂...',
];
const currentPlaceholderIndex = ref(0);
const currentPlaceholder = ref(placeholders[0]);
let placeholderInterval: ReturnType<typeof setInterval> | null = null;

const rotatePlaceholder = () => {
  currentPlaceholderIndex.value = (currentPlaceholderIndex.value + 1) % placeholders.length;
  currentPlaceholder.value = placeholders[currentPlaceholderIndex.value];
};

const handleSubmit = () => {
  if (eventName.value.trim()) {
    emit('event-submit', eventName.value.trim());
  }
};

// 監聽來自 index.vue 的填入事件
const handleFillEvent = (event: CustomEvent) => {
  eventName.value = event.detail;
  // 自動聚焦輸入框
  const inputElement = document.getElementById('event') as HTMLInputElement;
  if (inputElement) {
    inputElement.focus();
  }
};

onMounted(() => {
  window.addEventListener('fillEventName', handleFillEvent as EventListener);
  // Start rotating placeholders
  placeholderInterval = setInterval(rotatePlaceholder, 3000);
});

onUnmounted(() => {
  window.removeEventListener('fillEventName', handleFillEvent as EventListener);
  if (placeholderInterval) {
    clearInterval(placeholderInterval);
  }
});
</script>

<style scoped>
/* Card appear animation */
@keyframes card-appear {
  0% {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
.animate-card-appear {
  animation: card-appear 0.6s ease-out forwards;
}

/* Title fade in */
@keyframes title-fade {
  0% {
    opacity: 0;
    transform: translateY(-10px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}
.animate-title-fade {
  animation: title-fade 0.8s ease-out 0.2s both;
}

/* Subtitle fade in */
@keyframes subtitle-fade {
  0% {
    opacity: 0;
  }
  100% {
    opacity: 1;
  }
}
.animate-subtitle-fade {
  animation: subtitle-fade 0.8s ease-out 0.4s both;
}

/* Form fade in */
@keyframes form-fade {
  0% {
    opacity: 0;
    transform: translateY(10px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}
.animate-form-fade {
  animation: form-fade 0.8s ease-out 0.6s both;
}

/* Error shake animation */
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
  20%, 40%, 60%, 80% { transform: translateX(5px); }
}
.animate-shake {
  animation: shake 0.5s ease-in-out;
}
</style>
