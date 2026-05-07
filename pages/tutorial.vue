<template>
  <div class="h-screen w-screen font-serif text-history-dark overflow-hidden relative">
    <!-- Global Background with Parallax Layers -->
    <div class="absolute inset-0 transition-all duration-1000"
      :class="currentStep <= 3 ? 'bg-history-dark' : 'bg-history-paper'"
    >
      <!-- Stars/Particles Layer -->
      <div class="absolute inset-0 overflow-hidden pointer-events-none opacity-50"
        :class="{ 'opacity-0': currentStep > 3 }"
      >
        <div v-for="i in 50" :key="'star-'+i" 
          class="absolute w-1 h-1 bg-history-accent/60 rounded-full"
          :class="i % 3 === 0 ? 'animate-twinkle' : 'animate-twinkle-delayed'"
          :style="{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
          }"
        ></div>
      </div>
      
      <!-- Light Rays Effect -->
      <div v-if="currentStep === 1" class="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div class="w-full h-full bg-gradient-radial from-history-accent/10 via-transparent to-transparent animate-pulse-slow"></div>
      </div>
    </div>

    <!-- Progress Bar -->
    <div class="absolute top-0 left-0 w-full h-1 bg-black/20 z-50 backdrop-blur">
      <div 
        class="h-full bg-gradient-to-r from-history-accent to-history-brown transition-all duration-700 ease-out"
        :style="{ width: `${(currentStep / totalSteps) * 100}%` }"
      ></div>
    </div>

    <!-- Skip Button -->
    <button 
      @click="skipTutorial"
      class="absolute top-4 right-4 z-50 px-4 py-2 text-sm transition-colors flex items-center gap-2 group backdrop-blur-sm rounded-full"
      :class="currentStep <= 3 ? 'text-history-paper/70 hover:text-history-paper bg-white/10' : 'text-history-brown hover:text-history-dark bg-black/5'"
    >
      跳過教學
      <Icon name="mdi:arrow-right" class="group-hover:translate-x-1 transition-transform" />
    </button>

    <!-- Step Counter -->
    <div class="absolute top-4 left-4 z-50 text-sm font-bold backdrop-blur-sm px-3 py-1 rounded-full"
      :class="currentStep <= 3 ? 'text-history-paper/70 bg-white/10' : 'text-history-brown bg-black/5'"
    >
      {{ currentStep }} / {{ totalSteps }}
    </div>

    <!-- ============ STEP 1: Cinematic Opening ============ -->
    <Transition name="cinematic-zoom-out">
      <div v-if="currentStep === 1" class="absolute inset-0 flex items-center justify-center overflow-hidden">
        <!-- Animated Portal Rings -->
        <div class="absolute inset-0 flex items-center justify-center">
          <div class="absolute w-[600px] h-[600px] rounded-full border border-history-accent/20 animate-portal-pulse"></div>
          <div class="absolute w-[500px] h-[500px] rounded-full border border-history-accent/30 animate-portal-pulse" style="animation-delay: 0.5s"></div>
          <div class="absolute w-[400px] h-[400px] rounded-full border-2 border-history-accent/40 animate-portal-spin-slow"></div>
          <div class="absolute w-[300px] h-[300px] rounded-full border-2 border-history-accent/50 animate-portal-spin-reverse"></div>
          <div class="absolute w-[200px] h-[200px] rounded-full bg-gradient-radial from-history-accent/30 to-transparent animate-breathe"></div>
        </div>
        
        <!-- Central Content with staggered reveal -->
        <div class="relative z-10 text-center text-history-paper max-w-xl px-8">
          <div class="overflow-hidden mb-6">
            <Icon name="mdi:clock-time-eight-outline" class="w-20 h-20 mx-auto text-history-accent animate-float-in" />
          </div>
          <div class="overflow-hidden">
            <h1 class="text-6xl font-bold tracking-widest animate-title-reveal">Echoes of Time</h1>
          </div>
          <div class="overflow-hidden mt-4">
            <p class="text-xl opacity-80 italic animate-subtitle-reveal">穿越時空，與歷史人物對話</p>
          </div>
          <div class="overflow-hidden mt-2">
            <p class="text-sm opacity-50 animate-subtitle-reveal" style="animation-delay: 0.3s">歡迎來到時空之門</p>
          </div>
          
          <div class="mt-12 animate-fade-in-up" style="animation-delay: 1s">
            <button 
              @click="nextStep" 
              class="relative px-10 py-5 bg-transparent text-history-paper font-bold text-lg rounded-full border-2 border-history-accent/50 overflow-hidden group hover:border-history-accent transition-all duration-500"
            >
              <span class="relative z-10 flex items-center gap-2">
                <Icon name="mdi:door-open" />
                踏入時空之門
              </span>
              <div class="absolute inset-0 bg-history-accent/20 scale-x-0 group-hover:scale-x-100 transition-transform duration-500 origin-left"></div>
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ============ STEP 2: Ancient Scroll Input ============ -->
    <Transition name="cinematic-slide-up">
      <div v-if="currentStep === 2" class="absolute inset-0 flex items-center justify-center p-8">
        <!-- Vignette effect -->
        <div class="absolute inset-0 bg-gradient-radial from-transparent via-transparent to-black/50 pointer-events-none"></div>
        
        <div class="w-full max-w-lg relative z-10">
          <!-- Floating ancient scroll -->
          <div class="relative animate-float-gentle">
            <!-- Scroll top roll -->
            <div class="h-8 bg-gradient-to-b from-history-brown to-history-brown/80 rounded-t-full shadow-lg"></div>
            
            <!-- Scroll content -->
            <div class="bg-history-paper p-8 shadow-2xl relative overflow-hidden">
              <!-- Paper texture overlay -->
              <div class="absolute inset-0 bg-[url('data:image/svg+xml,...')] opacity-10"></div>
              
              <div class="relative z-10">
                <h2 class="text-2xl font-bold text-history-dark mb-2 text-center">選擇您的歷史旅程</h2>
                <p class="text-history-brown mb-8 text-center">輸入一個歷史事件，開啟穿越之旅</p>
                
                <div class="relative mb-6 group">
                  <input
                    ref="inputField"
                    type="text"
                    v-model="typedText"
                    @keyup.enter="handleSearch"
                    class="w-full px-5 py-4 bg-history-light/50 border-2 border-history-brown/30 rounded-xl text-history-dark text-lg text-center focus:outline-none focus:border-history-accent focus:bg-white transition-all duration-300"
                    placeholder="文藝復興"
                  />
                  <div class="absolute inset-0 rounded-xl bg-history-accent/5 scale-105 opacity-0 group-focus-within:opacity-100 transition-opacity -z-10"></div>
                </div>
                
                <button 
                  @click="handleSearch"
                  class="w-full py-4 bg-gradient-to-r from-history-dark to-history-brown text-history-paper font-bold text-lg rounded-xl hover:shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group overflow-hidden relative"
                  :disabled="!typedText.trim()"
                >
                  <span class="relative z-10 flex items-center justify-center gap-2">
                    <Icon name="mdi:compass" class="group-hover:rotate-45 transition-transform duration-500" />
                    開始穿越
                  </span>
                  <div class="absolute inset-0 bg-gradient-to-r from-history-accent to-history-brown opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                </button>
              </div>
            </div>
            
            <!-- Scroll bottom roll -->
            <div class="h-8 bg-gradient-to-t from-history-brown to-history-brown/80 rounded-b-full shadow-lg"></div>
          </div>
          
          <p class="mt-8 text-history-paper/50 text-sm text-center animate-pulse" v-if="!typedText">
            試著輸入「文藝復興」或任何歷史事件
          </p>
        </div>
      </div>
    </Transition>

    <!-- ============ STEP 3: Discovery Sequence ============ -->
    <Transition name="cinematic-fade">
      <div v-if="currentStep === 3" class="absolute inset-0 flex flex-col items-center justify-center p-8 overflow-hidden">
        <!-- Dramatic spotlight effect -->
        <div class="absolute inset-0 bg-gradient-radial from-history-brown/30 via-transparent to-black/70 pointer-events-none"></div>
        
        <!-- Discovery Title with typewriter effect -->
        <div class="text-center text-history-paper mb-16 relative z-10">
          <h2 class="text-4xl font-bold mb-3 animate-text-glow">正在蒐集歷史資料</h2>
          <p class="text-history-accent text-xl font-bold">{{ typedText || '文藝復興' }}</p>
        </div>
        
        <!-- Cinematic Collection Sequence -->
        <div class="relative w-full max-w-4xl h-64 flex items-center justify-center">
          <!-- Central collection point -->
          <div class="absolute w-32 h-32 rounded-full border-2 border-history-accent/50 animate-pulse flex items-center justify-center">
            <div class="w-24 h-24 rounded-full bg-history-accent/20 animate-breathe"></div>
          </div>
          
          <!-- Flying items from different directions -->
          <Transition name="fly-left">
            <div v-if="discoveryPhase >= 1" class="absolute left-0 animate-fly-to-center-left">
              <div class="bg-history-cream rounded-xl p-4 shadow-2xl border-2 border-history-brown transform hover:scale-105 transition-transform">
                <Icon name="mdi:map-legend" class="w-10 h-10 text-history-dark mx-auto mb-2" />
                <p class="text-history-dark font-bold text-sm text-center">歷史背景</p>
                <p class="text-history-brown text-xs text-center">14-17世紀</p>
              </div>
            </div>
          </Transition>
          
          <Transition name="fly-top">
            <div v-if="discoveryPhase >= 2" class="absolute top-0 animate-fly-to-center-top">
              <div class="flex -space-x-3">
                <div v-for="(persona, idx) in collectedPersonas.slice(0, 3)" :key="persona.name"
                  class="w-14 h-14 rounded-full border-2 border-history-accent bg-history-cream overflow-hidden shadow-lg transform"
                  :style="{ animationDelay: `${idx * 0.1}s` }">
                  <img v-if="persona.avatar" :src="persona.avatar" :alt="persona.name" class="w-full h-full object-cover" />
                </div>
              </div>
            </div>
          </Transition>
          
          <Transition name="fly-right">
            <div v-if="discoveryPhase >= 3" class="absolute right-0 animate-fly-to-center-right">
              <div class="flex gap-2">
                <div v-for="obj in collectedObjects" :key="obj.name"
                  class="bg-history-cream rounded-lg p-3 shadow-lg border-2 border-history-brown">
                  <Icon :name="obj.icon" class="w-8 h-8 text-history-dark" />
                </div>
              </div>
            </div>
          </Transition>
        </div>
        
        <!-- Progress dots with labels -->
        <div class="mt-16 flex gap-8 relative z-10">
          <div v-for="(label, i) in ['背景', '人物', '文物']" :key="i" class="text-center">
            <div class="w-4 h-4 rounded-full mx-auto mb-2 transition-all duration-500"
              :class="discoveryPhase > i ? 'bg-history-accent scale-125 shadow-lg shadow-history-accent/50' : 'bg-history-paper/30'"
            ></div>
            <p class="text-history-paper/60 text-xs">{{ label }}</p>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ============ STEP 4: Epic Reveal ============ -->
    <Transition name="cinematic-zoom-in">
      <div v-if="currentStep === 4" class="absolute inset-0 overflow-y-auto bg-history-paper">
        <!-- Decorative top gradient -->
        <div class="absolute top-0 left-0 right-0 h-40 bg-gradient-to-b from-history-brown/20 to-transparent pointer-events-none"></div>
        
        <div class="min-h-full flex items-center py-12 px-8">
          <div class="w-full max-w-5xl mx-auto">
            <!-- Event Header with dramatic entrance -->
            <div class="text-center mb-12">
              <div class="inline-block mb-6 animate-bounce-in">
                <div class="w-20 h-20 rounded-full bg-history-accent/10 flex items-center justify-center mx-auto">
                  <Icon name="mdi:map-marker-radius" class="w-12 h-12 text-history-accent" />
                </div>
              </div>
              <h2 class="text-5xl font-bold text-history-dark mb-3 animate-title-reveal-dark">{{ demoEvent.name }}</h2>
              <p class="text-history-brown text-lg animate-fade-in-up" style="animation-delay: 0.3s">
                {{ demoEvent.time_period }} · {{ demoEvent.geographic_location }}
              </p>
            </div>
            
            <!-- Event Description with elegant card -->
            <div class="bg-gradient-to-br from-history-cream to-history-light rounded-2xl p-8 mb-12 shadow-xl border border-history-brown/20 animate-slide-up-fade" style="animation-delay: 0.5s">
              <p class="text-history-dark leading-relaxed text-lg">{{ demoEvent.description }}</p>
            </div>
            
            <!-- Personas with staggered cinematic entrance -->
            <h3 class="text-2xl font-bold text-history-dark mb-6 flex items-center gap-3">
              <Icon name="mdi:account-group" class="text-history-accent" />
              已召喚的歷史人物
            </h3>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12">
              <div 
                v-for="(persona, index) in demoPersonas" 
                :key="persona.name"
                class="group relative bg-white rounded-2xl p-5 shadow-lg border border-history-brown/10 opacity-0 animate-persona-entrance cursor-pointer overflow-hidden"
                :style="{ animationDelay: `${0.8 + index * 0.15}s` }"
              >
                <!-- Hover glow effect -->
                <div class="absolute inset-0 bg-gradient-to-br from-history-accent/0 to-history-accent/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                
                <div class="relative z-10">
                  <div class="w-24 h-24 mx-auto mb-4 rounded-full border-3 border-history-brown/30 overflow-hidden group-hover:border-history-accent group-hover:scale-105 transition-all duration-500 shadow-lg">
                    <img v-if="persona.avatar" :src="persona.avatar" :alt="persona.name" class="w-full h-full object-cover" />
                    <div v-else class="w-full h-full bg-history-cream flex items-center justify-center">
                      <Icon name="mdi:account" class="w-12 h-12 text-history-brown" />
                    </div>
                  </div>
                  <h5 class="font-bold text-center text-history-dark">{{ persona.name }}</h5>
                  <p class="text-sm text-center text-history-brown mt-1">{{ persona.role }}</p>
                </div>
              </div>
            </div>
            
            <!-- CTA Button with cinematic style -->
            <div class="text-center animate-fade-in-up" style="animation-delay: 1.5s">
              <button 
                @click="nextStep" 
                class="relative px-10 py-5 bg-history-dark text-history-paper font-bold text-lg rounded-full overflow-hidden group hover:shadow-2xl transition-all duration-500"
              >
                <span class="relative z-10 flex items-center gap-2">
                  <Icon name="mdi:message-text" />
                  開始與達文西對話
                </span>
                <div class="absolute inset-0 bg-gradient-to-r from-history-accent to-history-brown scale-x-0 group-hover:scale-x-100 transition-transform duration-500 origin-left"></div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ============ STEP 5: Immersive Chat ============ -->
    <Transition name="cinematic-slide-left">
      <div v-if="currentStep === 5" class="absolute inset-0 flex flex-col bg-gradient-to-b from-history-light to-history-paper">
        <!-- Elegant Header -->
        <header class="bg-history-dark text-history-paper p-5 flex justify-between items-center shadow-lg">
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 rounded-full border-3 border-history-accent overflow-hidden shadow-lg">
              <img :src="demoPersonas[0].avatar" :alt="demoPersonas[0].name" class="w-full h-full object-cover" />
            </div>
            <div>
              <h3 class="text-xl font-bold">{{ demoPersonas[0].name }}</h3>
              <p class="text-sm opacity-70 flex items-center gap-1">
                <span class="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
                正在對話中
              </p>
            </div>
          </div>
          <button class="px-4 py-2 bg-history-accent/20 rounded-full text-sm font-bold hover:bg-history-accent/40 transition-colors flex items-center gap-2">
            <Icon name="mdi:cards" />
            人物卡牌
          </button>
        </header>
        
        <!-- Chat Messages with elegant styling -->
        <main ref="chatMain" class="flex-1 overflow-y-auto p-6 space-y-6">
          <TransitionGroup name="message-cinematic">
            <div 
              v-for="(msg, index) in visibleMessages" 
              :key="index"
              :class="['flex items-end gap-4', msg.role === 'user' ? 'justify-end' : 'justify-start']"
            >
              <div v-if="msg.role === 'model'" class="w-12 h-12 rounded-full border-2 border-history-brown overflow-hidden flex-shrink-0 shadow-md">
                <img :src="demoPersonas[0].avatar" class="w-full h-full object-cover" />
              </div>
              
              <div :class="['max-w-lg rounded-2xl p-5 shadow-lg', 
                msg.role === 'user' 
                  ? 'bg-history-dark text-history-paper rounded-br-sm' 
                  : 'bg-white text-history-dark border border-history-brown/10 rounded-bl-sm']">
                <p v-if="msg.persona" class="text-xs text-history-accent font-bold mb-2 flex items-center gap-1">
                  <Icon name="mdi:feather" class="w-3 h-3" />
                  {{ msg.persona }}
                </p>
                <p class="leading-relaxed">{{ msg.content }}</p>
              </div>
              
              <div v-if="msg.role === 'user'" class="w-12 h-12 bg-history-dark rounded-full flex items-center justify-center border-2 border-history-brown flex-shrink-0 shadow-md">
                <Icon name="mdi:account" class="w-7 h-7 text-history-paper" />
              </div>
            </div>
          </TransitionGroup>
          
          <!-- Elegant typing indicator -->
          <div v-if="isAiTyping" class="flex items-end gap-4 justify-start">
            <div class="w-12 h-12 rounded-full border-2 border-history-brown overflow-hidden flex-shrink-0 shadow-md">
              <img :src="demoPersonas[0].avatar" class="w-full h-full object-cover" />
            </div>
            <div class="bg-white border border-history-brown/10 rounded-2xl rounded-bl-sm p-5 shadow-lg">
              <div class="flex gap-2">
                <span class="w-3 h-3 bg-history-accent rounded-full animate-typing-dot" style="animation-delay: 0s"></span>
                <span class="w-3 h-3 bg-history-accent rounded-full animate-typing-dot" style="animation-delay: 0.2s"></span>
                <span class="w-3 h-3 bg-history-accent rounded-full animate-typing-dot" style="animation-delay: 0.4s"></span>
              </div>
            </div>
          </div>
        </main>
        
        <!-- Elegant Input Area -->
        <footer class="p-6 bg-white/80 backdrop-blur border-t border-history-brown/10">
          <div class="flex items-center gap-4 max-w-3xl mx-auto">
            <div class="flex-1 relative">
              <input
                type="text"
                v-model="userMessage"
                @keyup.enter="sendMessage"
                :placeholder="hasInteracted ? '繼續對話...' : '試著問：您最自豪的作品是什麼？'"
                class="w-full px-6 py-4 bg-history-light/50 border-2 border-history-brown/20 rounded-full focus:outline-none focus:border-history-accent focus:bg-white transition-all duration-300 pr-14"
              />
            </div>
            <button 
              @click="sendMessage"
              class="p-4 bg-history-dark rounded-full text-history-paper hover:bg-history-accent transition-all duration-300 hover:scale-110 active:scale-95 disabled:opacity-50 shadow-lg"
              :disabled="!userMessage.trim()"
            >
              <Icon name="mdi:send" class="w-6 h-6" />
            </button>
          </div>
          <div v-if="!hasInteracted" class="text-center mt-4">
            <p class="text-history-brown text-sm">
              <Icon name="mdi:lightbulb-outline" class="inline animate-pulse" />
              在上方輸入框中輸入您的問題，與達文西展開對話
            </p>
          </div>
        </footer>
        
        <!-- Completion Button -->
        <Transition name="slide-up-bounce">
          <div v-if="allMessagesShown" class="absolute bottom-32 left-1/2 -translate-x-1/2 z-50">
            <button 
              @click="nextStep" 
              class="px-8 py-4 bg-history-accent text-history-paper font-bold rounded-full shadow-2xl hover:shadow-history-accent/50 transition-all duration-300 hover:-translate-y-1 animate-pulse-glow"
            >
              完成教學
              <Icon name="mdi:arrow-right" class="inline ml-2" />
            </button>
          </div>
        </Transition>
      </div>
    </Transition>

    <!-- ============ STEP 6: Grand Finale ============ -->
    <Transition name="cinematic-fade-zoom">
      <div v-if="currentStep === 6" class="absolute inset-0 flex items-center justify-center overflow-hidden bg-history-dark">
        <!-- Celebration effects -->
        <div class="absolute inset-0 pointer-events-none overflow-hidden">
          <!-- Radial light burst -->
          <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-gradient-radial from-history-accent/20 via-transparent to-transparent animate-pulse-slow"></div>
          
          <!-- Confetti particles -->
          <div v-for="i in 40" :key="'confetti-'+i" 
            class="absolute w-3 h-3 rounded-full animate-confetti-fall"
            :class="['bg-history-accent', 'bg-history-brown', 'bg-history-paper'][i % 3]"
            :style="{
              left: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 3}s`,
              animationDuration: `${3 + Math.random() * 2}s`
            }"
          ></div>
        </div>
        
        <div class="relative z-10 text-center text-history-paper max-w-lg px-8">
          <!-- Trophy with glow -->
          <div class="mb-8 animate-trophy-entrance">
            <div class="relative inline-block">
              <div class="absolute inset-0 w-28 h-28 rounded-full bg-history-accent/30 blur-xl animate-breathe"></div>
              <div class="relative w-28 h-28 mx-auto rounded-full bg-gradient-to-br from-history-accent to-history-brown flex items-center justify-center shadow-2xl">
                <Icon name="mdi:trophy" class="w-16 h-16 text-history-paper" />
              </div>
            </div>
          </div>
          
          <h2 class="text-5xl font-bold mb-4 animate-title-reveal">恭喜完成教學！</h2>
          <p class="text-xl mb-10 opacity-80 animate-fade-in-up" style="animation-delay: 0.5s">
            您已經準備好踏上歷史探索之旅<br />
            無數歷史人物正等待與您對話
          </p>
          
          <div class="space-y-4 animate-fade-in-up" style="animation-delay: 0.8s">
            <button 
              @click="startExploring"
              class="w-full px-8 py-5 bg-gradient-to-r from-history-accent to-history-brown text-history-paper font-bold text-lg rounded-full hover:shadow-2xl hover:shadow-history-accent/30 transition-all duration-500 hover:-translate-y-1"
            >
              <Icon name="mdi:compass" class="inline mr-2" />
              開始探索歷史
            </button>
            <button 
              @click="restartTutorial"
              class="w-full px-6 py-4 border-2 border-history-paper/30 text-history-paper font-bold rounded-full hover:bg-history-paper/10 hover:border-history-paper/50 transition-all duration-300"
            >
              <Icon name="mdi:refresh" class="inline mr-2" />
              重新體驗教學
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue';

definePageMeta({
  layout: false,
  name: 'tutorial'
});

// Tutorial state
const currentStep = ref(1);
const totalSteps = 6;

// Step 2: Input
const typedText = ref('');
const inputField = ref<HTMLInputElement | null>(null);

// Step 3: Discovery
const discoveryPhase = ref(0);
let discoveryInterval: ReturnType<typeof setInterval> | null = null;

const collectedPersonas = [
  { name: '達文西', avatar: '/static/avatars/Leonardo%20da%20Vinci_0e484316.png' },
  { name: '米開朗基羅', avatar: '/static/avatars/Michelangelo%20Buonarroti_5a356d58.png' },
  { name: '哥白尼', avatar: 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Nikolaus_Kopernikus_MOT.jpg/330px-Nikolaus_Kopernikus_MOT.jpg' },
];

const collectedObjects = [
  { name: '畫作', icon: 'mdi:palette' },
  { name: '書籍', icon: 'mdi:book-open-page-variant' },
  { name: '工具', icon: 'mdi:compass-rose' },
];

// Demo data
const demoEvent = {
  name: '文藝復興',
  description: '文藝復興是指約14世紀至17世紀初在歐洲發生的一場思想、文化與藝術運動。它以「復興」古希臘羅馬文化為核心，強調人文主義精神，對後世的藝術、科學、哲學乃至社會結構皆產生深遠影響。',
  time_period: '約14世紀至17世紀初',
  geographic_location: '歐洲，主要起源於義大利'
};

const demoPersonas = [
  { name: '李奧納多·達文西', role: '文藝復興全才', avatar: '/static/avatars/Leonardo%20da%20Vinci_0e484316.png' },
  { name: '米開朗基羅', role: '雕塑家、畫家', avatar: '/static/avatars/Michelangelo%20Buonarroti_5a356d58.png' },
  { name: '尼可拉斯·哥白尼', role: '天文學家', avatar: 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Nikolaus_Kopernikus_MOT.jpg/330px-Nikolaus_Kopernikus_MOT.jpg' },
  { name: '佩脫拉克', role: '人文主義之父', avatar: '/static/avatars/%E4%BD%A9%E8%84%AB%E6%8B%89%E5%85%8B_5fdfbe11.png' }
];

// Step 5: Chat
const visibleMessages = ref<any[]>([]);
const allMessagesShown = computed(() => visibleMessages.value.length >= 3);
const userMessage = ref('');
const isAiTyping = ref(false);
const hasInteracted = ref(false);
const chatMain = ref<HTMLElement | null>(null);

// Step handlers
const nextStep = () => {
  currentStep.value++;
  handleStepChange();
};

const handleStepChange = () => {
  cleanupIntervals();
  
  if (currentStep.value === 2) {
    setTimeout(() => inputField.value?.focus(), 500);
  } else if (currentStep.value === 3) {
    startDiscoveryAnimation();
  } else if (currentStep.value === 5) {
    visibleMessages.value = [
      { role: 'model', persona: '李奧納多·達文西', content: '歡迎來到文藝復興時代！我是李奧納多·達文西。在這個時代，我們相信人類有無限的潛能。請問您想了解什麼？' }
    ];
  }
};

const handleSearch = () => {
  if (!typedText.value.trim()) return;
  nextStep();
};

const startDiscoveryAnimation = () => {
  discoveryPhase.value = 0;
  let phase = 0;
  
  discoveryInterval = setInterval(() => {
    phase++;
    discoveryPhase.value = phase;
    
    if (phase >= 3) {
      if (discoveryInterval) clearInterval(discoveryInterval);
      setTimeout(() => nextStep(), 1200);
    }
  }, 1000);
};

const sendMessage = async () => {
  if (!userMessage.value.trim()) return;
  hasInteracted.value = true;
  
  visibleMessages.value.push({ role: 'user', content: userMessage.value });
  userMessage.value = '';
  await nextTick();
  scrollToBottom();
  
  isAiTyping.value = true;
  
  setTimeout(() => {
    isAiTyping.value = false;
    visibleMessages.value.push({
      role: 'model',
      persona: '李奧納多·達文西',
      content: '這是一個很有深度的問題！作為一名藝術家和科學家，我認為觀察是最重要的能力。無論是繪畫人體還是設計飛行器，都需要仔細觀察大自然的運作方式。藝術與科學在本質上是相通的。'
    });
    nextTick(() => scrollToBottom());
  }, 1500);
};

const scrollToBottom = () => {
  if (chatMain.value) {
    chatMain.value.scrollTop = chatMain.value.scrollHeight;
  }
};

const cleanupIntervals = () => {
  if (discoveryInterval) clearInterval(discoveryInterval);
};

const skipTutorial = () => navigateTo('/');
const startExploring = () => navigateTo('/');

const restartTutorial = () => {
  currentStep.value = 1;
  visibleMessages.value = [];
  typedText.value = '';
  hasInteracted.value = false;
  discoveryPhase.value = 0;
};

onUnmounted(() => cleanupIntervals());
</script>

<style scoped>
/* ===== CINEMATIC TRANSITIONS ===== */
.cinematic-zoom-out-leave-active {
  transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}
.cinematic-zoom-out-leave-to {
  opacity: 0;
  transform: scale(1.2);
  filter: blur(10px);
}

.cinematic-slide-up-enter-active {
  transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}
.cinematic-slide-up-enter-from {
  opacity: 0;
  transform: translateY(100px);
}
.cinematic-slide-up-leave-active {
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.cinematic-slide-up-leave-to {
  opacity: 0;
  transform: translateY(-50px) scale(0.95);
}

.cinematic-fade-enter-active,
.cinematic-fade-leave-active {
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.cinematic-fade-enter-from { opacity: 0; }
.cinematic-fade-leave-to { opacity: 0; transform: scale(0.98); }

.cinematic-zoom-in-enter-active {
  transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}
.cinematic-zoom-in-enter-from {
  opacity: 0;
  transform: scale(0.9);
}
.cinematic-zoom-in-leave-active {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
.cinematic-zoom-in-leave-to {
  opacity: 0;
  transform: scale(1.05);
}

.cinematic-slide-left-enter-active {
  transition: all 0.7s cubic-bezier(0.4, 0, 0.2, 1);
}
.cinematic-slide-left-enter-from {
  opacity: 0;
  transform: translateX(100px);
}
.cinematic-slide-left-leave-active {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
.cinematic-slide-left-leave-to {
  opacity: 0;
  transform: translateX(-50px);
}

.cinematic-fade-zoom-enter-active {
  transition: all 1s cubic-bezier(0.4, 0, 0.2, 1);
}
.cinematic-fade-zoom-enter-from {
  opacity: 0;
  transform: scale(0.8);
}

.slide-up-bounce-enter-active {
  transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.slide-up-bounce-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(30px);
}
.slide-up-bounce-leave-active {
  transition: all 0.3s ease;
}
.slide-up-bounce-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(10px);
}

.message-cinematic-enter-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.message-cinematic-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

/* ===== KEYFRAME ANIMATIONS ===== */
@keyframes twinkle {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.5); }
}
@keyframes twinkle-delayed {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 0.2; }
}

@keyframes portal-pulse {
  0%, 100% { transform: scale(1); opacity: 0.3; }
  50% { transform: scale(1.05); opacity: 0.5; }
}

@keyframes portal-spin-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes portal-spin-reverse {
  from { transform: rotate(360deg); }
  to { transform: rotate(0deg); }
}

@keyframes breathe {
  0%, 100% { transform: scale(1); opacity: 0.5; }
  50% { transform: scale(1.1); opacity: 0.8; }
}

@keyframes float-in {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes title-reveal {
  from { opacity: 0; letter-spacing: 0.3em; transform: translateY(20px); }
  to { opacity: 1; letter-spacing: 0.1em; transform: translateY(0); }
}

@keyframes title-reveal-dark {
  from { opacity: 0; letter-spacing: 0.2em; }
  to { opacity: 1; letter-spacing: 0.05em; }
}

@keyframes subtitle-reveal {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slide-up-fade {
  from { opacity: 0; transform: translateY(40px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes float-gentle {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

@keyframes text-glow {
  0%, 100% { text-shadow: 0 0 20px rgba(212, 163, 115, 0.5); }
  50% { text-shadow: 0 0 40px rgba(212, 163, 115, 0.8), 0 0 60px rgba(212, 163, 115, 0.4); }
}

@keyframes fly-to-center-left {
  from { transform: translateX(-100px) scale(0.8); opacity: 0; }
  to { transform: translateX(150px) scale(1); opacity: 1; }
}
@keyframes fly-to-center-top {
  from { transform: translateY(-80px) scale(0.8); opacity: 0; }
  to { transform: translateY(80px) scale(1); opacity: 1; }
}
@keyframes fly-to-center-right {
  from { transform: translateX(100px) scale(0.8); opacity: 0; }
  to { transform: translateX(-150px) scale(1); opacity: 1; }
}

@keyframes bounce-in {
  0% { transform: scale(0); opacity: 0; }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); opacity: 1; }
}

@keyframes persona-entrance {
  0% { opacity: 0; transform: translateY(50px) scale(0.8); }
  60% { transform: translateY(-10px) scale(1.02); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes typing-dot {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-8px); opacity: 1; }
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(212, 163, 115, 0.5); }
  50% { box-shadow: 0 0 30px 10px rgba(212, 163, 115, 0.3); }
}

@keyframes pulse-slow {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.05); }
}

@keyframes confetti-fall {
  0% { transform: translateY(-100vh) rotate(0deg); opacity: 1; }
  100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
}

@keyframes trophy-entrance {
  0% { transform: scale(0) rotate(-180deg); opacity: 0; }
  60% { transform: scale(1.2) rotate(10deg); }
  100% { transform: scale(1) rotate(0deg); opacity: 1; }
}

/* ===== ANIMATION CLASSES ===== */
.animate-twinkle { animation: twinkle 3s ease-in-out infinite; }
.animate-twinkle-delayed { animation: twinkle-delayed 4s ease-in-out infinite; animation-delay: 1s; }
.animate-portal-pulse { animation: portal-pulse 3s ease-in-out infinite; }
.animate-portal-spin-slow { animation: portal-spin-slow 20s linear infinite; }
.animate-portal-spin-reverse { animation: portal-spin-reverse 15s linear infinite; }
.animate-breathe { animation: breathe 4s ease-in-out infinite; }
.animate-float-in { animation: float-in 0.8s ease-out forwards; }
.animate-title-reveal { animation: title-reveal 1s ease-out forwards; }
.animate-title-reveal-dark { animation: title-reveal-dark 0.8s ease-out forwards; }
.animate-subtitle-reveal { animation: subtitle-reveal 0.8s ease-out forwards; animation-delay: 0.2s; opacity: 0; animation-fill-mode: forwards; }
.animate-fade-in-up { animation: fade-in-up 0.6s ease-out forwards; opacity: 0; animation-fill-mode: forwards; }
.animate-slide-up-fade { animation: slide-up-fade 0.7s ease-out forwards; opacity: 0; animation-fill-mode: forwards; }
.animate-float-gentle { animation: float-gentle 4s ease-in-out infinite; }
.animate-text-glow { animation: text-glow 3s ease-in-out infinite; }
.animate-fly-to-center-left { animation: fly-to-center-left 0.8s ease-out forwards; }
.animate-fly-to-center-top { animation: fly-to-center-top 0.8s ease-out forwards; }
.animate-fly-to-center-right { animation: fly-to-center-right 0.8s ease-out forwards; }
.animate-bounce-in { animation: bounce-in 0.6s ease-out forwards; }
.animate-persona-entrance { animation: persona-entrance 0.7s ease-out forwards; animation-fill-mode: forwards; }
.animate-typing-dot { animation: typing-dot 1.4s ease-in-out infinite; }
.animate-pulse-glow { animation: pulse-glow 2s ease-in-out infinite; }
.animate-pulse-slow { animation: pulse-slow 4s ease-in-out infinite; }
.animate-confetti-fall { animation: confetti-fall 4s ease-in-out forwards; }
.animate-trophy-entrance { animation: trophy-entrance 0.8s ease-out forwards; }

/* ===== UTILITIES ===== */
.bg-gradient-radial {
  background: radial-gradient(circle, var(--tw-gradient-from) 0%, var(--tw-gradient-to) 70%);
}
</style>
