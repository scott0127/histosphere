<template>
  <div class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-history-paper text-history-dark font-serif overflow-hidden">
    <!-- Background Texture & Effects -->
    <div class="absolute inset-0 pointer-events-none opacity-30 bg-paper-pattern mix-blend-multiply"></div>
    <div class="absolute inset-0 pointer-events-none bg-gradient-to-b from-history-brown/10 via-transparent to-history-brown/20"></div>
    
    <!-- Floating Particles (Simulated Dust/History) -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div v-for="n in 10" :key="n" 
           class="absolute rounded-full bg-history-brown/20 animate-float"
           :style="{
             width: Math.random() * 10 + 5 + 'px',
             height: Math.random() * 10 + 5 + 'px',
             top: Math.random() * 100 + '%',
             left: Math.random() * 100 + '%',
             animationDuration: Math.random() * 10 + 10 + 's',
             animationDelay: Math.random() * 5 + 's'
           }"
      ></div>
    </div>

    <!-- Main Content -->
    <div class="relative z-10 max-w-2xl w-full p-8 text-center flex flex-col items-center">
      
      <!-- Event Title -->
      <h2 class="text-3xl md:text-4xl font-bold mb-2 text-history-dark tracking-widest uppercase animate-fade-in-up">
        {{ eventName }}
      </h2>
      <div class="w-32 h-1 bg-history-accent mb-12 mx-auto rounded-full animate-expand-width"></div>

      <!-- Narrative Steps -->
      <div class="h-24 flex items-center justify-center mb-8 w-full">
        <Transition name="fade-slide" mode="out-in">
          <p :key="currentStepIndex" class="text-xl md:text-2xl font-medium text-history-brown italic">
            {{ currentStepText }}
          </p>
        </Transition>
      </div>

      <!-- Progress Bar (Ink Style) -->
      <div class="w-full max-w-md h-2 bg-history-brown/10 rounded-full overflow-hidden relative border border-history-brown/20">
        <div 
          class="absolute top-0 left-0 h-full bg-history-dark transition-all duration-300 ease-out"
          :style="{ width: `${progress}%` }"
        >
          <!-- Ink bleeding effect at the tip -->
          <div class="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 w-4 h-4 bg-history-dark rounded-full blur-[2px] opacity-80"></div>
        </div>
      </div>
      
      <!-- Percentage (Optional, maybe too digital?) -->
      <p class="mt-4 text-sm text-history-brown/60 font-mono">
        {{ Math.floor(progress) }}%
      </p>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';

const props = defineProps<{
  eventName: string;
  isLoading: boolean; // Parent controls when it's done
}>();

// Narrative Steps
const steps = [
  "正在翻閱塵封的檔案...",
  "正在定位歷史座標...",
  "正在召喚歷史人物...",
  "正在重構當時的場景...",
  "正在準備歷史舞台...",
  "即將進入歷史..."
];

const currentStepIndex = ref(0);
const progress = ref(0);
let progressInterval: NodeJS.Timeout | null = null;
let stepInterval: NodeJS.Timeout | null = null;

const currentStepText = computed(() => steps[currentStepIndex.value]);

onMounted(() => {
  startLoadingSequence();
});

onUnmounted(() => {
  if (progressInterval) clearInterval(progressInterval);
  if (stepInterval) clearInterval(stepInterval);
});

const startLoadingSequence = () => {
  // 1. Progress Bar Simulation (0% -> 90% over ~25s)
  // We leave the last 10% for the actual completion
  const totalDuration = 25000; 
  const updateInterval = 100;
  const increment = 90 / (totalDuration / updateInterval);

  progressInterval = setInterval(() => {
    if (progress.value < 90) {
      progress.value += increment + (Math.random() * 0.5 - 0.25); // Add some jitter
    }
  }, updateInterval);

  // 2. Step Rotation
  const stepDuration = totalDuration / (steps.length - 1);
  stepInterval = setInterval(() => {
    if (currentStepIndex.value < steps.length - 1) {
      currentStepIndex.value++;
    }
  }, stepDuration);
};

// Watch for isLoading to become false (completion)
watch(() => props.isLoading, (newVal) => {
  if (!newVal) {
    // Finish up quickly
    if (progressInterval) clearInterval(progressInterval);
    if (stepInterval) clearInterval(stepInterval);
    
    progress.value = 100;
    currentStepIndex.value = steps.length - 1;
  }
});
</script>

<style scoped>
/* Animations */
@keyframes float {
  0% { transform: translateY(0) rotate(0deg); opacity: 0; }
  20% { opacity: 0.5; }
  80% { opacity: 0.5; }
  100% { transform: translateY(-100px) rotate(360deg); opacity: 0; }
}
.animate-float {
  animation-name: float;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}

@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in-up {
  animation: fade-in-up 1s ease-out forwards;
}

@keyframes expand-width {
  from { width: 0; opacity: 0; }
  to { width: 8rem; opacity: 1; }
}
.animate-expand-width {
  animation: expand-width 1s ease-out 0.5s forwards;
  opacity: 0; /* Start hidden */
}

/* Transition for text */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.5s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
