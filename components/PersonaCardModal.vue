<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
    <div class="bg-history-paper w-full max-w-4xl h-[85vh] rounded-xl shadow-2xl flex flex-col overflow-hidden border-4 border-history-dark relative">
      
      <!-- Close Button -->
      <button @click="$emit('close')" class="absolute top-4 right-4 z-20 text-history-dark hover:text-history-accent transition-colors bg-history-paper/80 rounded-full p-1">
        <Icon name="mdi:close-circle" class="w-8 h-8" />
      </button>

      <!-- Header -->
      <header class="bg-history-dark text-history-paper p-4 text-center shrink-0 border-b-4 border-history-accent">
        <h2 class="text-2xl font-bold tracking-widest flex items-center justify-center gap-3">
          <Icon name="mdi:card-account-details" />
          歷史人物誌
        </h2>
        <p class="text-history-light text-sm mt-1">{{ eventName }}</p>
      </header>

      <!-- Main Content -->
      <div class="flex-1 flex flex-col md:flex-row overflow-hidden">
        
        <!-- Left: Card Display -->
        <div class="flex-1 p-6 flex flex-col items-center bg-paper-pattern relative overflow-y-auto">
          
          <div v-if="currentPersona" class="w-full max-w-md flex flex-col gap-4">
            <!-- Top: Avatar Area -->
            <div class="relative aspect-[4/3] bg-history-dark rounded-lg overflow-hidden border-4 border-history-brown shadow-lg group">
              <!-- Locked Overlay -->
              <div v-if="!currentPersona.is_unlocked" class="absolute inset-0 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm z-10 text-history-paper">
                <Icon name="mdi:lock" class="w-16 h-16 mb-2 text-history-light" />
                <p class="font-bold tracking-wide text-lg">人物未解鎖</p>
              </div>
              
              <!-- Avatar Image / Video Player -->
              <div class="relative w-full h-full">
                <video 
                  ref="videoPlayer"
                  v-if="isPlayingVideo"
                  :src="videoUrl"
                  autoplay
                  @ended="handleVideoEnded"
                  class="w-full h-full object-cover"
                ></video>
                
                <img 
                  v-else-if="currentPersona.avatar_url" 
                  :src="currentPersona.avatar_url" 
                  class="w-full h-full object-contain transition-transform duration-700 group-hover:scale-105"
                  :class="{ 
                    'grayscale blur-sm': !currentPersona.is_unlocked,
                    'cursor-pointer hover:brightness-110': currentPersona.is_unlocked 
                  }"
                  @click="handleSpeak"
                />
                <div v-else class="w-full h-full flex items-center justify-center bg-history-brown text-history-paper">
                  <Icon name="mdi:account-question" class="w-24 h-24 opacity-50" />
                </div>

                <!-- Video Loading Overlay -->
                <div v-if="isGeneratingVideo" class="absolute inset-0 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm z-20 text-history-paper">
                  <Icon name="mdi:movie-open-star" class="w-12 h-12 mb-2 animate-pulse text-history-accent" />
                  <p class="font-bold tracking-wide text-sm">正在生成動態卡牌...</p>
                </div>
              </div>

              <!-- Name Tag -->
              <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-4 pt-12 text-center">
                <h3 class="text-2xl font-bold text-history-paper drop-shadow-md">{{ currentPersona.name }}</h3>
                <p class="text-history-accent text-sm font-bold uppercase tracking-wider">{{ currentPersona.role }}</p>
              </div>
            </div>

            <!-- Bottom: Story/Challenge Area -->
            <div class="flex-1 bg-history-cream border-2 border-history-brown rounded-lg p-6 shadow-inner overflow-y-auto relative min-h-[200px]">
              
              <!-- Loading State -->
              <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center bg-history-cream/80 z-20">
                <Icon name="mdi:loading" class="w-10 h-10 animate-spin text-history-brown" />
              </div>

              <!-- Unlocked: Story -->
              <div v-if="currentPersona.is_unlocked">
                <div class="flex items-start gap-3 mb-4">
                  <Icon name="mdi:format-quote-open" class="text-4xl text-history-accent opacity-40 shrink-0" />
                  <Typewriter :text="currentPersona.story || '（暫無故事內容）'" class="text-history-dark font-serif text-lg leading-relaxed" :speed="30" />
                </div>
              </div>

              <!-- Locked: Challenge -->
              <div v-else class="flex flex-col items-center justify-center h-full text-center">
                <!-- Step 1: Choose Challenge Type -->
                <div v-if="!selectedChallengeType && !activeChallenge && !isLoading">
                  <p class="text-history-brown mb-2 font-bold text-lg">你想從哪個角度了解我？</p>
                  <p class="text-history-brown/70 mb-6 text-sm">選擇一個你最感興趣的面向</p>
                  
                  <div class="space-y-3">
                    <button 
                      @click="selectChallengeType('關鍵決策')"
                      class="w-full px-6 py-4 bg-white hover:bg-history-light border-2 border-history-brown hover:border-history-accent rounded-lg transition-all text-left group"
                    >
                      <div class="flex items-center gap-3">
                        <Icon name="mdi:gavel" class="w-6 h-6 text-history-accent" />
                        <div>
                          <p class="font-bold text-history-dark group-hover:text-history-accent transition-colors">關鍵決策</p>
                          <p class="text-xs text-history-brown">測試對歷史轉折點的理解</p>
                        </div>
                      </div>
                    </button>
                    
                    <button 
                      @click="selectChallengeType('個人生平')"
                      class="w-full px-6 py-4 bg-white hover:bg-history-light border-2 border-history-brown hover:border-history-accent rounded-lg transition-all text-left group"
                    >
                      <div class="flex items-center gap-3">
                        <Icon name="mdi:account-heart" class="w-6 h-6 text-history-accent" />
                        <div>
                          <p class="font-bold text-history-dark group-hover:text-history-accent transition-colors">個人生平</p>
                          <p class="text-xs text-history-brown">測試對人物背景的了解</p>
                        </div>
                      </div>
                    </button>
                    
                    <button 
                      @click="selectChallengeType('時代背景')"
                      class="w-full px-6 py-4 bg-white hover:bg-history-light border-2 border-history-brown hover:border-history-accent rounded-lg transition-all text-left group"
                    >
                      <div class="flex items-center gap-3">
                        <Icon name="mdi:clock-outline" class="w-6 h-6 text-history-accent" />
                        <div>
                          <p class="font-bold text-history-dark group-hover:text-history-accent transition-colors">時代背景</p>
                          <p class="text-xs text-history-brown">測試對當時環境的認知</p>
                        </div>
                      </div>
                    </button>
                  </div>
                </div>

                <!-- Step 2: Loading State -->
                <div v-else-if="isLoading && !activeChallenge" class="flex flex-col items-center gap-4">
                  <div class="w-16 h-16 rounded-full bg-history-dark overflow-hidden border-4 border-history-accent shadow-lg animate-pulse">
                    <img v-if="currentPersona.avatar_url" :src="currentPersona.avatar_url" class="w-full h-full object-cover" />
                    <Icon v-else name="mdi:account" class="text-history-paper w-full h-full p-2" />
                  </div>
                  <div class="text-center">
                    <p class="text-history-brown font-bold text-lg mb-2">正在依 {{ currentPersona.name }} 的回憶生成題目...</p>
                    <div class="flex items-center justify-center gap-2">
                      <span class="w-2 h-2 bg-history-accent rounded-full animate-bounce"></span>
                      <span class="w-2 h-2 bg-history-accent rounded-full animate-bounce delay-100"></span>
                      <span class="w-2 h-2 bg-history-accent rounded-full animate-bounce delay-200"></span>
                    </div>
                  </div>
                </div>

                <!-- Step 3: Active Challenge -->
                <div v-else class="w-full text-left">
                  <div class="mb-4">
                    <span class="inline-block px-3 py-1 bg-history-brown text-history-paper text-xs rounded-full mb-2">歷史挑戰</span>
                    <p class="font-bold text-history-dark text-lg">{{ activeChallenge.question }}</p>
                  </div>
                  
                  <div class="space-y-3 mb-4">
                    <button 
                      v-for="(option, idx) in activeChallenge.options" 
                      :key="idx"
                      @click="submitAnswer(idx)"
                      class="w-full p-3 text-left rounded-lg border-2 transition-all relative overflow-hidden group"
                      :class="[
                        selectedOption === idx 
                          ? (isCorrect === true ? 'bg-green-100 border-green-600 text-green-900' : (isCorrect === false ? 'bg-red-100 border-red-600 text-red-900' : 'bg-history-light border-history-dark'))
                          : 'bg-white border-history-brown/30 hover:border-history-brown hover:bg-history-light'
                      ]"
                      :disabled="isCorrect !== null"
                    >
                      <span class="font-bold mr-2">{{ ['A', 'B', 'C', 'D'][idx] }}.</span>
                      {{ option }}
                      
                      <!-- Feedback Icon -->
                      <Icon v-if="selectedOption === idx && isCorrect === true" name="mdi:check-circle" class="absolute right-3 top-1/2 -translate-y-1/2 text-green-600 w-6 h-6" />
                      <Icon v-if="selectedOption === idx && isCorrect === false" name="mdi:close-circle" class="absolute right-3 top-1/2 -translate-y-1/2 text-red-600 w-6 h-6" />
                    </button>
                  </div>

                  <!-- Hint Section -->
                  <div class="flex flex-col gap-2 mt-4">
                    <div v-if="hasAnsweredWrong" class="flex items-center justify-between bg-red-50 border border-red-200 rounded-lg p-3">
                      <span class="text-red-600 font-bold text-sm flex items-center gap-2">
                        <Icon name="mdi:alert-circle" class="w-5 h-5" />
                        答案錯誤，請再試一次！
                      </span>
                      <button 
                        @click="requestHintFromChat"
                        :disabled="isHintLoading"
                        class="text-sm bg-history-accent hover:bg-history-brown text-history-paper px-4 py-2 rounded-full font-bold flex items-center gap-1 transition-colors disabled:opacity-50"
                      >
                        <Icon v-if="isHintLoading" name="mdi:loading" class="animate-spin" />
                        <Icon v-else name="mdi:chat-question" />
                        {{ isHintLoading ? '正在詢問...' : '請求提示' }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right/Bottom: Navigation -->
        <div class="bg-history-light border-t-4 md:border-t-0 md:border-l-4 border-history-brown p-4 flex md:flex-col gap-3 overflow-x-auto md:overflow-y-auto md:w-64 shrink-0">
          <h4 class="hidden md:block font-bold text-history-brown mb-2 uppercase tracking-wider text-sm">人物列表</h4>
          
          <button 
            v-for="(p, index) in personas" 
            :key="p.id"
            @click="selectPersona(index)"
            class="flex items-center gap-3 p-2 rounded-lg transition-all border-2 text-left min-w-[160px] md:min-w-0"
            :class="[
              currentIndex === index 
                ? 'bg-history-cream border-history-accent shadow-md' 
                : 'bg-history-paper border-transparent hover:bg-history-cream hover:border-history-brown/30'
            ]"
          >
            <div class="w-10 h-10 rounded-full bg-history-dark overflow-hidden shrink-0 border border-history-brown">
               <img v-if="p.avatar_url" :src="p.avatar_url" class="w-full h-full object-cover" />
               <Icon v-else name="mdi:account" class="text-history-paper w-full h-full p-1" />
            </div>
            <div class="min-w-0">
              <p class="font-bold text-history-dark truncate text-sm">{{ p.name }}</p>
              <div class="flex items-center gap-1">
                <Icon :name="p.is_unlocked ? 'mdi:lock-open-variant' : 'mdi:lock'" class="w-3 h-3" :class="p.is_unlocked ? 'text-green-600' : 'text-history-light'" />
                <span class="text-xs text-history-brown truncate">{{ p.is_unlocked ? '已解鎖' : '未解鎖' }}</span>
              </div>
            </div>
          </button>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import Typewriter from './Typewriter.vue';

const props = defineProps<{
  eventId: string;
  eventName: string;
  conversationId: string;
}>();

const emit = defineEmits(['close', 'hint-requested']);

interface PersonaCard {
  id: string;
  name: string;
  role: string;
  avatar_url?: string;
  is_unlocked: boolean;
  story?: string;
}

interface Challenge {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
}

const personas = ref<PersonaCard[]>([]);
const currentIndex = ref(0);
const isLoading = ref(false);
const selectedChallengeType = ref<string | null>(null);
const activeChallenge = ref<Challenge | null>(null);
const selectedOption = ref<number | null>(null);
const isCorrect = ref<boolean | null>(null);
const hasAnsweredWrong = ref(false);
const isHintLoading = ref(false);

// Talking Head State
const isPlayingVideo = ref(false);
const videoUrl = ref('');
const isGeneratingVideo = ref(false);

const currentPersona = computed(() => personas.value[currentIndex.value]);

onMounted(async () => {
  await fetchPersonas();
});

const fetchPersonas = async () => {
  isLoading.value = true;
  try {
    const data = await $fetch<PersonaCard[]>(`/api/personas/${props.eventId}/cards`);
    personas.value = data;
  } catch (e) {
    console.error('Failed to fetch persona cards:', e);
  } finally {
    isLoading.value = false;
  }
};

const selectPersona = (index: number) => {
  currentIndex.value = index;
  // Reset challenge state when switching
  selectedChallengeType.value = null;
  activeChallenge.value = null;
  selectedOption.value = null;
  isCorrect.value = null;
  hasAnsweredWrong.value = false;
};

const selectChallengeType = async (type: string) => {
  if (!currentPersona.value) return;
  
  selectedChallengeType.value = type;
  isLoading.value = true;
  
  try {
    const data = await $fetch<Challenge>(`/api/personas/${currentPersona.value.id}/challenge?challenge_type=${encodeURIComponent(type)}`);
    activeChallenge.value = data;
  } catch (e) {
    console.error('Failed to start challenge:', e);
    alert('無法生成挑戰，請稍後再試。');
    selectedChallengeType.value = null;
  } finally {
    isLoading.value = false;
  }
};

const requestHintFromChat = async () => {
  if (!activeChallenge.value || !currentPersona.value) return;
  
  isHintLoading.value = true;
  try {
    await $fetch(`/api/personas/${currentPersona.value.id}/hint`, {
      method: 'POST',
      body: { 
        conversation_id: props.conversationId,
        question: activeChallenge.value.question,
        correct_answer: activeChallenge.value.options[activeChallenge.value.correct_index]
      }
    });
    
    // 關閉卡牌視窗
    emit('close');
    
    // 通知父元件更新訊息
    emit('hint-requested');
  } catch (e) {
    console.error('Failed to get hint:', e);
  } finally {
    isHintLoading.value = false;
  }
};

const handleSpeak = async () => {
  if (!currentPersona.value || !currentPersona.value.is_unlocked || isGeneratingVideo.value || isPlayingVideo.value) return;

  isGeneratingVideo.value = true;
  try {
    const res = await $fetch<{ video_url: string; status: string }>(`/api/personas/${currentPersona.value.id}/speak`, {
      method: 'POST',
      body: {} // Use default story
    });
    
    if (res.video_url) {
      videoUrl.value = res.video_url;
      isPlayingVideo.value = true;
    } else {
      // Handle case where video_url is empty but no error thrown
      alert('無法生成語音影片，請稍後再試。');
    }
  } catch (e) {
    console.error('Failed to generate speech video:', e);
    alert('無法生成語音影片，請稍後再試。');
  } finally {
    isGeneratingVideo.value = false;
  }
};

const videoPlayer = ref<HTMLVideoElement | null>(null);

const handleVideoEnded = () => {
  if (!videoPlayer.value) return;
  // Reverse playback
  videoPlayer.value.playbackRate = -1;
  videoPlayer.value.play();
};

// Monitor time update to detect when reverse playback reaches the start
const checkReverseEnd = () => {
  if (videoPlayer.value && videoPlayer.value.playbackRate < 0 && videoPlayer.value.currentTime <= 0.1) {
    videoPlayer.value.playbackRate = 1;
    videoPlayer.value.play();
  }
  if (isPlayingVideo.value) {
    requestAnimationFrame(checkReverseEnd);
  }
};

// Start monitoring when video starts
watch(isPlayingVideo, (newVal) => {
  if (newVal) {
    requestAnimationFrame(checkReverseEnd);
  }
});

const onVideoEnded = () => {
  // Legacy handler, removed
};

const submitAnswer = async (index: number) => {
  if (!activeChallenge.value || !currentPersona.value) return;
  
  selectedOption.value = index;
  
  if (index === activeChallenge.value.correct_index) {
    isCorrect.value = true;
    hasAnsweredWrong.value = false;
    // Call API to unlock
    try {
      const res = await $fetch<{ is_correct: boolean; story: string }>(`/api/personas/${currentPersona.value.id}/unlock`, {
        method: 'POST',
        body: { answer_index: index }
      });
      
      // Wait a bit for visual feedback
      setTimeout(() => {
        // Update local state
        const p = personas.value[currentIndex.value];
        p.is_unlocked = true;
        p.story = res.story;
        activeChallenge.value = null;
        isCorrect.value = null;
        selectedOption.value = null;
        hasAnsweredWrong.value = false;
      }, 1500);
      
    } catch (e) {
      console.error('Unlock failed:', e);
    }
  } else {
    isCorrect.value = false;
    hasAnsweredWrong.value = true;
    // Allow retry after delay
    setTimeout(() => {
      selectedOption.value = null;
      isCorrect.value = null;
    }, 1000);
  }
};
</script>

<style scoped>
.animate-shake {
  animation: shake 0.5s cubic-bezier(.36,.07,.19,.97) both;
}

@keyframes shake {
  10%, 90% { transform: translate3d(-1px, 0, 0); }
  20%, 80% { transform: translate3d(2px, 0, 0); }
  30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
  40%, 60% { transform: translate3d(4px, 0, 0); }
}
</style>
