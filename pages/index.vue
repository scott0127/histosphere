<template>
  <div class="min-h-screen w-full lg:h-screen lg:w-screen bg-history-paper bg-paper-pattern font-serif text-history-dark relative flex flex-col lg:overflow-hidden">
    
    <!-- Immersive Loading Screen -->
    <Transition name="fade">
      <ImmersiveLoading 
        v-if="isLoading" 
        :event-name="pendingEventName || '歷史事件'" 
        :is-loading="isLoading"
      />
    </Transition>

    <!-- Top Navigation / Mode Switcher -->
    <header class="fixed top-0 left-0 w-full z-50 lg:p-4 lg:py-3 flex flex-col pointer-events-none lg:absolute">
      <!-- Desktop Header -->
      <div class="hidden lg:flex w-full justify-between items-center">
        <!-- Left: Tutorial + Feedback -->
        <div class="pointer-events-auto flex gap-2">
          <!-- Tutorial Button -->
          <NuxtLink 
            to="/tutorial"
            class="px-4 py-2 bg-history-accent/90 backdrop-blur-sm text-history-paper text-sm font-bold rounded-full border-2 border-history-dark shadow-lg hover:bg-history-accent transition-all flex items-center gap-2"
          >
            <Icon name="mdi:school" class="w-4 h-4" />
            教學導覽
          </NuxtLink>
          <!-- Feedback Button -->
          <button
            @click="showFeedbackModal = true"
            class="px-4 py-2 bg-emerald-600/90 backdrop-blur-sm text-white text-sm font-bold rounded-full border-2 border-emerald-800 shadow-lg hover:bg-emerald-700 transition-all flex items-center gap-2"
          >
            <Icon name="mdi:message-draw" class="w-4 h-4" />
            意見回饋
          </button>
        </div>
        
        <!-- Right: Placeholder (Auth button now in absolute position) -->
        <div></div>
      </div>
      
      

      <!-- Mobile Header (Modern & Clean) -->
      <div class="flex lg:hidden w-full justify-between items-center pointer-events-auto bg-history-paper/90 backdrop-blur-md px-4 py-3 shadow-sm border-b border-history-brown/10 relative">
        <!-- Left: Menu -->
        <button @click="showMobileMenu = !showMobileMenu" class="p-2 -ml-2 text-history-dark hover:bg-history-dark/5 rounded-full transition-colors">
          <Icon :name="showMobileMenu ? 'mdi:close' : 'mdi:menu'" class="w-6 h-6" />
        </button>

        <!-- Center: Mode Switcher (Segmented Control) -->
        <div class="flex bg-history-brown/10 rounded-lg p-1 gap-1">
          <button 
            @click="currentMode = 'input'" 
            :class="['px-4 py-1.5 rounded-md text-xs font-bold transition-all', currentMode === 'input' ? 'bg-white text-history-dark shadow-sm' : 'text-history-brown/60']"
          >
            書寫
          </button>
          <button 
            @click="currentMode = 'map'" 
            :class="['px-4 py-1.5 rounded-md text-xs font-bold transition-all', currentMode === 'map' ? 'bg-white text-history-dark shadow-sm' : 'text-history-brown/60']"
          >
            地圖
          </button>
        </div>

        <!-- Right: Brand -->
        <div class="w-10 h-10 flex items-center justify-end">
           <Icon name="mdi:feather" class="w-6 h-6 text-history-accent" />
        </div>

        <!-- Mobile Menu Dropdown -->
        <div v-show="showMobileMenu" class="absolute top-full left-0 w-full bg-history-paper/95 backdrop-blur-xl border-b border-history-brown/10 shadow-xl p-4 flex flex-col gap-3 animate-fade-in origin-top z-50">
           <NuxtLink 
            to="/tutorial"
            class="flex items-center gap-3 p-3 rounded-lg bg-history-cream hover:bg-white border border-history-brown/10 transition-all active:scale-95"
            @click="showMobileMenu = false"
           >
             <div class="w-8 h-8 rounded-full bg-history-accent/10 flex items-center justify-center text-history-accent">
               <Icon name="mdi:school" class="w-4 h-4" />
             </div>
             <span class="font-bold text-history-dark">教學導覽</span>
           </NuxtLink>
           
           <button 
            @click="showFeedbackModal = true; showMobileMenu = false"
            class="flex items-center gap-3 p-3 rounded-lg bg-emerald-50 hover:bg-white border border-emerald-100 transition-all active:scale-95 text-left w-full"
           >
             <div class="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">
               <Icon name="mdi:message-draw" class="w-4 h-4" />
             </div>
             <span class="font-bold text-emerald-800">意見回饋</span>
           </button>
        </div>
      </div>
    </header>

    <!-- Mode 1: Input & List View -->
    <div v-if="currentMode === 'input'" class="flex-1 flex flex-col h-full relative animate-fade-in">
      <!-- Background Image with Gradient Overlay -->
      <div class="absolute inset-0 pointer-events-none fixed lg:absolute">
         <img src="~/assets/images/landing-bg.png" alt="" class="w-full h-full object-cover" />
         <!-- Classic Mode Gradients -->
         <div v-if="!useBookUI" class="absolute inset-0 bg-gradient-to-br from-history-paper/80 via-transparent to-history-brown/30"></div>
         <div v-if="!useBookUI" class="absolute inset-0 bg-gradient-to-t from-history-paper/60 via-transparent to-transparent"></div>
      </div>
      
      <!-- Animated Particles -->
      <div v-if="useBookUI" class="absolute inset-0 pointer-events-none overflow-hidden fixed lg:absolute">
        <div v-for="i in 20" :key="i" class="particle" :style="getParticleStyle(i)"></div>
      </div>

      <!-- Split View: Input Form (Top/Left) & Event List (Bottom/Right) -->
      <!-- Responsive: Stack columns on mobile, row on desktop -->
      <div class="flex-1 flex flex-col lg:flex-row lg:overflow-hidden relative z-10">
        <!-- Left: Input Form -->
        <div class="w-full lg:w-1/2 min-h-[500px] lg:min-h-0 lg:h-full flex items-center justify-center p-4 relative pt-20 lg:pt-4">
          <Transition name="fade" mode="out-in">
            <BookInputForm 
              v-if="useBookUI"
              :is-loading="isLoading" 
              :error="error" 
              @event-submit="handleEventSubmit"
              @toggle-ui="useBookUI = !useBookUI"
              class="z-10 animate-fade-in mt-12 md:mt-20"
            />
            <PersonaInputForm 
              v-else
              :is-loading="isLoading" 
              :error="error" 
              @event-submit="handleEventSubmit"
              @toggle-ui="useBookUI = !useBookUI" 
            />
          </Transition>
        </div>

        <!-- Right: Event List -->
        <div class="w-full lg:w-1/2 min-h-[500px] lg:min-h-0 lg:h-full bg-[url('')] bg-cover bg-center bg-no-repeat border-t-2 lg:border-t-0 lg:border-l-2 border-history-brown/70 relative">
          <!-- Leather Mode Overlay (Only for Book Mode) -->
          <div :class="['w-full h-full flex flex-col', useBookUI ? 'bg-black/60' : 'bg-history-paper/30']">
            <div class="lg:h-14"></div> <!-- Spacer for desktop header alignment -->
            
            <!-- Leather Header (New) -->
            <div v-if="useBookUI" class="sticky top-0 lg:absolute lg:top-0 left-0 w-full px-6 py-6 border-b border-history-brown/20 z-10 bg-center bg-cover bg-no-repeat shadow-md" :style="{ backgroundImage: `url(${topAreaImage})` }">
              <div class="flex justify-between items-center relative z-10">
                <!-- Title with decorative elements -->
                <div class="flex items-center gap-3">
                  <!-- Decorative icon with subtle animation -->
                  <div class="relative">
                    <Icon name="mdi:book-open-page-variant" class="w-6 h-6 text-history-dark" />
                    <div class="absolute -bottom-1 -right-1 w-2 h-2 bg-history-brown/50 rounded-full"></div>
                  </div>
                  <!-- Title with refined typography -->
                  <div class="flex flex-col">
                    <h3 class="font-bold text-history-dark tracking-wide text-lg">
                      已記錄的歷史篇章
                    </h3>
                    <div class="flex items-center gap-2 mt-0.5">
                      <div class="h-px w-8 bg-gradient-to-r from-history-brown to-transparent"></div>
                      <span class="text-xs text-history-dark/80 italic font-bold">Recorded Chronicles</span>
                      <div class="h-px w-8 bg-gradient-to-l from-history-brown to-transparent"></div>
                    </div>
                  </div>
                </div>
                <!-- Mode Toggle + Refresh Button -->
                <div class="flex items-center gap-2">
                  <!-- Mode Toggle (fixed in header) -->
                  <div class="hidden lg:flex p-1 rounded-full border-2 border-history-brown/30 shadow-sm gap-0.5" style="background-color: #dbc29a;">
                    <button 
                      @click="currentMode = 'input'"
                      :class="['px-3 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5', 
                        currentMode === 'input' ? 'bg-history-dark text-history-paper shadow-sm' : 'text-history-brown hover:bg-history-brown/10']"
                    >
                      <Icon name="mdi:feather" class="w-3.5 h-3.5" />
                      歷史書寫
                    </button>
                    <button 
                      @click="currentMode = 'map'"
                      :class="['px-3 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5', 
                        currentMode === 'map' ? 'bg-history-dark text-history-paper shadow-sm' : 'text-history-brown hover:bg-history-brown/10']"
                    >
                      <Icon name="mdi:map-legend" class="w-3.5 h-3.5" />
                      時空地圖
                    </button>
                  </div>
                  <!-- Auth Button Component -->
                  <AuthButton @signed-out="fetchEvents" />
                  <!-- Refresh button -->
                  <button 
                    @click="refreshEvents" 
                    class="p-2 rounded-full text-history-brown/60 hover:text-history-accent hover:bg-history-brown/10 transition-all duration-300" 
                    title="重新整理"
                  >
                    <Icon name="mdi:refresh" class="w-5 h-5" :class="{ 'animate-spin': isRefreshing }" />
                  </button>
                </div>
              </div>
            </div>

            <!-- Classic Header (Restored) -->
            <div v-else class="sticky top-0 lg:absolute lg:top-0 left-0 w-full px-6 py-4 border-b border-history-brown/10 z-10 bg-[#F5E6D3]/90 backdrop-blur-sm flex justify-between items-center shadow-sm">
                <!-- Left: Simple Title -->
                <div class="flex items-center gap-2 text-history-dark">
                    <Icon name="mdi:diamond-stone" class="w-5 h-5 opacity-60" />
                    <h3 class="font-bold tracking-wider text-base">已記錄的歷史篇章</h3>
                </div>

                <!-- Right: Toggle & Refresh -->
                <div class="flex items-center gap-3">
                     <!-- Mode Toggle (Classic Pill) -->
                     <div class="hidden lg:flex bg-[#F5E6D3] border border-history-dark/20 rounded-full p-1 gap-1 shadow-inner">
                        <button 
                          @click="currentMode = 'input'" 
                          :class="['px-4 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5', currentMode === 'input' ? 'bg-history-dark text-history-paper shadow-md' : 'text-history-brown hover:bg-history-brown/5']"
                        >
                            <Icon name="mdi:feather" class="w-3.5 h-3.5" />
                            歷史書寫
                        </button>
                        <button 
                          @click="currentMode = 'map'" 
                          :class="['px-4 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5', currentMode === 'map' ? 'bg-history-dark text-history-paper shadow-md' : 'text-history-brown hover:bg-history-brown/5']"
                        >
                            <Icon name="mdi:map-legend" class="w-3.5 h-3.5" />
                            時空地圖
                        </button>
                     </div>
                     <!-- Auth Button Component -->
                     <AuthButton @signed-out="fetchEvents" />
                     <button @click="refreshEvents" class="p-2 text-history-brown hover:bg-history-brown/5 rounded-full transition-colors">
                        <Icon name="mdi:refresh" class="w-5 h-5" :class="{ 'animate-spin': isRefreshing }" />
                     </button>
                </div>
            </div>
            <div class="flex-1 overflow-y-auto pt-2 lg:pt-4 pb-4">
              <div v-if="loadingEvents" class="flex justify-center items-center h-full text-history-brown">
                 <Icon name="mdi:loading" class="animate-spin w-8 h-8" />
              </div>
              <div v-else-if="events.length > 0" class="h-full">
                <!-- Leather Style (New) -->
                <EventList 
                  v-if="useBookUI"
                  :events="events" 
                  @enter-story="handleEnterStory" 
                  @delete-event="handleDeleteEvent"
                />
                <!-- Classic Style (Old) -->
                <EventListClassic 
                  v-else
                  :events="events" 
                  @enter-story="handleEnterStory" 
                  @delete-event="handleDeleteEvent"
                />
              </div>
              <div v-else class="flex flex-col items-center justify-center h-full text-history-brown/50 italic py-20">
                <Icon name="mdi:book-open-blank-variant" class="w-16 h-16 mb-2" />
                <p>尚無歷史記錄，請開始書寫...</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Mode 2: Map View -->
    <div v-else class="flex-1 h-full relative animate-fade-in lg:h-full h-[calc(100vh-80px)] mt-20 lg:mt-0">
      <!-- Toggle overlay for map view -->
      <div class="absolute top-4 right-4 z-20 hidden lg:flex">
        <div class="bg-history-cream/90 backdrop-blur-sm p-1 rounded-full border-2 border-history-brown shadow-lg gap-0.5 flex">
          <button 
            @click="currentMode = 'input'"
            :class="['px-3 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5', 
              currentMode === 'input' ? 'bg-history-dark text-history-paper shadow-sm' : 'text-history-brown hover:bg-history-brown/10']"
          >
            <Icon name="mdi:feather" class="w-3.5 h-3.5" />
            歷史書寫
          </button>
          <button 
            @click="currentMode = 'map'"
            :class="['px-3 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5', 
              currentMode === 'map' ? 'bg-history-dark text-history-paper shadow-sm' : 'text-history-brown hover:bg-history-brown/10']"
          >
            <Icon name="mdi:map-legend" class="w-3.5 h-3.5" />
            時空地圖
          </button>
        </div>
      </div>
      <ClientOnly>
        <HistoricalMap :events="events" @enter-story="handleEnterStory" />
        <template #fallback>
          <div class="flex items-center justify-center h-full bg-history-paper text-history-brown">
            <div class="text-center">
              <Icon name="mdi:map-clock-outline" class="w-16 h-16 mb-4 animate-bounce" />
              <p class="font-bold">正在展開時空地圖...</p>
            </div>
          </div>
        </template>
      </ClientOnly>
    </div>

    <!-- Modals -->
    <DeleteConfirmationModal
      :show="showDeleteConfirmDialog"
      @confirm="confirmDelete"
      @cancel="showDeleteConfirmDialog = false"
    />

    <LegendConfirmationModal
      :show="showLegendConfirmDialog"
      :event-name="pendingChatData?.event.name || ''"
      @confirm="confirmEnterLegend"
      @cancel="cancelEnterLegend"
    />

    <FeedbackModal
      :show="showFeedbackModal"
      @close="showFeedbackModal = false"
    />

    <!-- Event Exists Confirmation Modal (Keep simple inline or extract if preferred, keeping inline for now as it's small) -->
    <div v-if="showConfirmDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in p-4">
      <div class="bg-history-cream border-2 border-history-dark p-8 rounded-xl shadow-2xl max-w-md w-full mx-4 text-center relative ring-4 ring-history-paper">
        <div class="absolute -top-6 left-1/2 transform -translate-x-1/2 bg-history-dark text-history-paper p-3 rounded-full border-4 border-history-cream shadow-lg">
            <Icon name="mdi:alert-circle-outline" class="w-8 h-8" />
        </div>
        <h3 class="text-2xl font-bold text-history-dark mt-6 mb-2 tracking-wide">歷史重演？</h3>
        <p class="text-history-brown mb-8 font-medium leading-relaxed">
          關於「{{ pendingEventName }}」的歷史舞台已經存在。<br>
          您想要重新搭建舞台，還是進入現有的歷史場景？
        </p>
        <div class="flex gap-4 justify-center">
          <button 
            @click="confirmRebuild" 
            class="px-6 py-3 bg-history-accent text-history-paper font-bold rounded-lg hover:bg-history-brown transition-colors border-2 border-history-dark shadow-md hover:-translate-y-0.5 active:translate-y-0"
          >
            重新搭建
          </button>
          <button 
            @click="confirmUseExisting" 
            class="px-6 py-3 bg-history-dark text-history-paper font-bold rounded-lg hover:bg-history-brown transition-colors border-2 border-history-dark shadow-md hover:-translate-y-0.5 active:translate-y-0"
          >
            進入現有
          </button>
        </div>
        <button @click="showConfirmDialog = false" class="absolute top-4 right-4 text-history-brown/60 hover:text-history-dark transition-colors">
            <Icon name="mdi:close" class="w-6 h-6" />
        </button>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import type { HistoricalEvent, Persona } from '~/types';
import EventList from '~/components/EventList.vue';
import EventListClassic from '~/components/EventListClassic.vue';
import HistoricalMap from '~/components/HistoricalMap.vue';
import ImmersiveLoading from '~/components/ImmersiveLoading.vue';
import DeleteConfirmationModal from '~/components/modals/DeleteConfirmationModal.vue';
import LegendConfirmationModal from '~/components/modals/LegendConfirmationModal.vue';
import FeedbackModal from '~/components/modals/FeedbackModal.vue';

// Assets
import topAreaImage from '~/assets/images/ui/TopArea.png';


definePageMeta({
  layout: false,
  name: 'event-selection'
});

// Types
interface EventWithPersonas extends HistoricalEvent {
  personas: Persona[];
}

// State
const currentMode = ref<'input' | 'map'>('input');
const useBookUI = ref(false); // Toggle for new Book UI
const isLoading = ref<boolean>(false);
const error = ref<string | null>(null);
const showConfirmDialog = ref(false);
const showDeleteConfirmDialog = ref(false);
const showLegendConfirmDialog = ref(false);
const showFeedbackModal = ref(false);
const showMobileMenu = ref(false); // Mobile menu state
const pendingEventName = ref('');
const pendingDeleteEventId = ref<string | null>(null);
const events = ref<EventWithPersonas[]>([]);
const loadingEvents = ref(false);
const isRefreshing = ref(false);
const pendingChatData = ref<any>(null); // Store data for delayed navigation

// Initialize on mount
onMounted(async () => {
  await fetchEvents();
  incrementViewCount(); // 紀錄瀏覽次數
  
  // 檢查是否有待探索的事件（從關聯事件點擊過來）
  const pendingEvent = localStorage.getItem('pendingEventSearch');
  
  if (pendingEvent) {
    nextTick(() => {
      const event = new CustomEvent('fillEventName', { detail: pendingEvent });
      window.dispatchEvent(event);
      localStorage.removeItem('pendingEventSearch');
      setTimeout(() => {
        alert(`已為您填入「${pendingEvent}」，請按 Enter 開始探索！`);
      }, 300);
    });
  }
});

// Particle effect for ambient dust/light
const getParticleStyle = (index: number) => {
  const size = Math.random() * 4 + 2;
  const left = Math.random() * 100;
  const delay = Math.random() * 15;
  const duration = Math.random() * 10 + 15;
  const opacity = Math.random() * 0.4 + 0.1;
  
  return {
    width: `${size}px`,
    height: `${size}px`,
    left: `${left}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`,
    opacity: opacity,
  };
};

// 增加瀏覽次數 (頁面載入時呼叫一次)
const incrementViewCount = async () => {
  try {
    await $fetch('/api/stats/view-count/increment', { method: 'POST' });
  } catch (e) {
    console.error('Failed to increment view count:', e);
  }
};

// Fetch events on mount
const fetchEvents = async () => {
  loadingEvents.value = true;
  try {
    const data = await $fetch<EventWithPersonas[]>('/api/events');
    events.value = data;
  } catch (e) {
    console.error('Failed to fetch events:', e);
  } finally {
    loadingEvents.value = false;
  }
};

const refreshEvents = async () => {
  isRefreshing.value = true;
  await fetchEvents();
  isRefreshing.value = false;
};

const handleDeleteEvent = (eventId: string) => {
  pendingDeleteEventId.value = eventId;
  showDeleteConfirmDialog.value = true;
};

const confirmDelete = async () => {
  if (!pendingDeleteEventId.value) return;
  
  try {
    await $fetch(`/api/event/${pendingDeleteEventId.value}`, {
      method: 'DELETE'
    });
    // Refresh list
    await fetchEvents();
  } catch (e) {
    console.error('Failed to delete event:', e);
    alert('刪除失敗，請稍後再試');
  } finally {
    showDeleteConfirmDialog.value = false;
    pendingDeleteEventId.value = null;
  }
};



const handleEnterStory = async (event: EventWithPersonas) => {
  // Reuse the initialize logic but with rebuild=false since we know it exists
  pendingEventName.value = event.name;
  await initializeEvent(event.name, false);
};

const handleEventSubmit = async (eventName: string) => {
  isLoading.value = true;
  error.value = null;
  pendingEventName.value = eventName;
  
  try {
    // 1. 檢查事件是否存在
    const checkResponse = await $fetch<{ exists: boolean }>('/api/event/check', {
      method: 'POST',
      body: { event_name: eventName }
    });

    if (checkResponse.exists) {
      showConfirmDialog.value = true;
      isLoading.value = false;
      return;
    }

    // 2. 如果不存在，直接創建
    await initializeEvent(eventName, false);

  } catch (e: any) {
    if (e.statusCode === 400 || e.status === 400) {
      error.value = e.data?.detail || '您輸入的內容似乎與歷史無關。請輸入歷史事件名稱。';
    } else {
      error.value = e.data?.message || '檢查事件時發生錯誤。';
    }
    isLoading.value = false;
  }
};

const confirmRebuild = async () => {
  showConfirmDialog.value = false;
  await initializeEvent(pendingEventName.value, true);
};

const confirmUseExisting = async () => {
  showConfirmDialog.value = false;
  await initializeEvent(pendingEventName.value, false);
};

const confirmEnterLegend = async () => {
  if (pendingChatData.value) {
    showLegendConfirmDialog.value = false;
    await proceedToChat(pendingChatData.value);
  }
};

const cancelEnterLegend = async () => {
  showLegendConfirmDialog.value = false;
  pendingChatData.value = null;
  // Refresh list to show the newly created event
  await fetchEvents();
};

const proceedToChat = async (data: any) => {
    // 使用 useState 儲存資料供聊天頁面使用
    const chatData = useState('chatData', () => null);
    chatData.value = {
      event: data.event,
      personas: data.personas,
      greeting: data.greeting,
      conversation_id: data.conversation_id,
      event_id: data.event_id,
      history: data.history || []
    };

    // 導航到聊天頁面，傳遞所有必要資料
    await navigateTo({
      path: '/chat',
      query: {
        conversationId: data.conversation_id,
        eventId: data.event_id
      }
    });
};

const initializeEvent = async (eventName: string, rebuild: boolean) => {
  isLoading.value = true;
  try {
    const response = await $fetch<{
      event_id: string;
      conversation_id: string;
      event: HistoricalEvent;
      personas: Persona[];
      greeting: string;
      history?: any[];
    }>('/api/event/initialize', {
      method: 'POST',
      body: { 
        event_name: eventName,
        rebuild: rebuild
      },
    });
    
    // Check if it's a legend and needs confirmation
    if (response.event.type === 'legend') {
        pendingChatData.value = response;
        showLegendConfirmDialog.value = true;
        // Do NOT navigate yet
        return;
    }

    await proceedToChat(response);

  } catch (e: any) {
    if (e.statusCode === 400 || e.status === 400) {
      error.value = e.data?.detail || '您輸入的內容似乎與歷史無關。請輸入歷史事件名稱。';
    } else {
      error.value = e.data?.message || '發生未知錯誤。';
    }
  } finally {
    isLoading.value = false;
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

/* Floating particles animation */
@keyframes float-up {
  0% {
    transform: translateY(100vh) rotate(0deg);
    opacity: 0;
  }
  10% {
    opacity: var(--particle-opacity, 0.3);
  }
  90% {
    opacity: var(--particle-opacity, 0.3);
  }
  100% {
    transform: translateY(-100px) rotate(360deg);
    opacity: 0;
  }
}

.particle {
  position: absolute;
  background: radial-gradient(circle, rgba(139, 109, 76, 0.6) 0%, rgba(139, 109, 76, 0) 70%);
  border-radius: 50%;
  animation: float-up linear infinite;
  --particle-opacity: 0.3;
}
</style>
