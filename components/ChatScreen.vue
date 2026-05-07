<template>
  <div class="flex h-full text-history-dark bg-history-paper font-serif">
    <!-- Main Chat Area -->
    <div :class="['flex flex-col flex-1 h-full min-w-0 relative border-l-2 border-history-brown bg-history-paper', backgroundUrl ? '' : 'bg-paper-pattern']">
      <!-- 歷史背景圖 - 覆蓋整個聊天區域 -->
      <div 
        v-if="backgroundUrl" 
        class="absolute inset-0 bg-cover bg-center bg-no-repeat pointer-events-none z-0"
        :style="{ 
          backgroundImage: `url(${backgroundUrl})`,
          opacity: 0.35
        }"
      ></div>
      <header class="bg-history-dark text-history-paper px-3 py-3 md:px-4 border-b-4 border-history-accent shadow-md shrink-0 z-20">
        <!-- 第一行：標題 + 按鈕 -->
        <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 sm:gap-0">
          <div class="flex items-center gap-3">
            <h2 class="text-lg md:text-2xl font-bold tracking-wide flex items-center gap-2 truncate">
              <Icon name="mdi:feather" class="flex-shrink-0" />
              <span class="truncate">{{ event?.name || '載入中...' }}</span>
            </h2>
            <!-- 動態情境描述 - 桌面版顯示在標題旁 -->
            <p class="hidden md:block text-sm italic opacity-80 border-l border-history-paper/30 pl-3">
              {{ dynamicContext }}
            </p>
          </div>
          
          <div class="flex gap-2 flex-shrink-0 self-end sm:self-auto">
            <button 
              v-if="event"
              @click="showPersonaCards = true" 
              class="px-2.5 py-1.5 md:px-3 bg-history-accent hover:bg-history-brown text-history-paper text-xs md:text-sm font-bold rounded border border-history-light/20 transition-colors shadow-sm flex items-center gap-1.5"
            >
              <Icon name="mdi:cards-playing-outline" class="w-4 h-4" />
              <span class="inline">卡牌</span>
            </button>
            <button 
              @click="$emit('reset')" 
              class="px-2.5 py-1.5 md:px-3 bg-history-brown hover:bg-history-accent text-history-paper text-xs md:text-sm font-bold rounded border border-history-light/20 transition-colors shadow-sm flex items-center gap-1.5"
            >
              <Icon name="mdi:plus" class="w-4 h-4" />
              <span>新事件</span>
            </button>
          </div>
        </div>
        
        <!-- 動態情境描述 - 手機版顯示在第二行 -->
        <p class="md:hidden text-xs md:text-sm italic opacity-80 mt-1.5 truncate">
          {{ dynamicContext }}
        </p>
        
        <!-- 關聯事件標籤 - 橫向佈局 -->
        <div v-if="relatedEvents.length > 0" class="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-history-paper/20">
          <span class="text-xs text-history-paper/60 mr-1 hidden sm:inline">相關事件：</span>
          
           <div class="flex overflow-x-auto gap-2 pb-1 w-full sm:w-auto no-scrollbar mask-gradient-right">
              <!-- 可探索的事件 - 強調「前往」動作 -->
              <button 
                v-for="event in explorableEvents" 
                :key="event.event_name"
                @click="switchToEvent(event)"
                class="group inline-flex items-center gap-1.5 text-xs bg-emerald-600/90 hover:bg-emerald-500 text-white rounded-full pl-2.5 pr-3 py-1 cursor-pointer transition-all hover:scale-105 shadow-sm whitespace-nowrap flex-shrink-0"
                :title="`前往「${event.event_name}」的對話`"
              >
                <Icon name="mdi:arrow-right-circle" class="w-4 h-4" />
                <span class="font-medium">前往</span>
                <span class="opacity-80">{{ event.event_year ? event.event_year + ' ' : '' }}{{ event.event_name }}</span>
              </button>
              
              <!-- 僅提及的事件 - 強調「探索」動作 -->
              <button 
                v-for="event in mentionedEvents" 
                :key="event.event_name"
                @click="exploreNewEvent(event)"
                class="group inline-flex items-center gap-1.5 text-xs bg-amber-500/80 hover:bg-amber-500 text-white rounded-full pl-2.5 pr-3 py-1 cursor-pointer transition-all hover:scale-105 shadow-sm whitespace-nowrap flex-shrink-0"
                :title="`探索「${event.event_name}」- 將創建新的歷史舞台`"
              >
                <Icon name="mdi:plus-circle" class="w-4 h-4" />
                <span class="font-medium">探索</span>
                <span class="opacity-80">{{ event.event_name }}</span>
              </button>
          </div>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto p-3 md:p-6 space-y-4 md:space-y-6 relative z-10" ref="chatContainerRef">
        <div v-for="(msg, index) in history" :key="index" :class="['flex items-start gap-2 md:gap-4', msg.role === 'user' ? 'justify-end' : 'justify-start']">
          <!-- Avatar -->
          <div v-if="msg.role === 'model'" :class="['flex-shrink-0', isThinkingAvatar(msg) ? 'relative w-12 h-12 md:w-14 md:h-14' : 'w-10 h-10 md:w-12 md:h-12 rounded-full flex items-center justify-center border-2 shadow-sm bg-history-cream border-history-dark overflow-hidden']">
             <!-- 思考中動畫 -->
             <template v-if="isThinkingAvatar(msg)">
               <!-- 指定人物: 單人登場動畫 -->
               <div v-if="msg.persona_id !== '__thinking__'" class="relative">
                 <div class="w-12 h-12 md:w-14 md:h-14 rounded-full border-3 border-history-accent shadow-lg overflow-hidden bg-history-cream animate-persona-entrance">
                   <img 
                     v-if="getPersonaAvatar(msg.persona_id)" 
                     :src="getPersonaAvatar(msg.persona_id)" 
                     :alt="msg.persona_name"
                     class="w-full h-full object-cover"
                   />
                   <Icon v-else name="mdi:account-circle" class="w-full h-full text-history-brown" />
                 </div>
                 <!-- 聚光燈光暈 -->
                 <div class="absolute -inset-1 bg-history-accent/30 rounded-full blur-md animate-spotlight-glow -z-10"></div>
               </div>
               <!-- 未指定: 多人思考中動畫 -->
               <div v-else class="absolute flex -space-x-3 left-0">
                 <div 
                   v-for="(persona, pIndex) in personas.slice(0, 3)" 
                   :key="persona.id"
                   :class="['w-8 h-8 md:w-10 md:h-10 rounded-full border-2 border-history-cream shadow-md overflow-hidden bg-history-cream animate-thinking-pulse', 
                     pIndex === 0 ? 'z-30' : pIndex === 1 ? 'z-20' : 'z-10']"
                   :style="{ animationDelay: `${pIndex * 150}ms` }"
                 >
                   <img 
                     v-if="persona.avatar_url" 
                     :src="persona.avatar_url" 
                     :alt="persona.name"
                     class="w-full h-full object-cover"
                   />
                   <Icon v-else name="mdi:account-circle" class="w-full h-full text-history-brown" />
                 </div>
               </div>
             </template>
             <!-- 一般頭像 -->
             <template v-else>
               <Icon v-if="msg.agent === 'tutor'" name="mdi:school" class="w-6 h-6 md:w-7 md:h-7 text-history-dark" />
               <template v-else>
                  <img 
                    v-if="getPersonaAvatar(msg.persona_id)" 
                    :src="getPersonaAvatar(msg.persona_id)" 
                    :alt="msg.persona_name"
                    class="w-full h-full object-cover"
                    @error="(e) => (e.target as HTMLImageElement).style.display = 'none'"
                  />
                  <Icon v-if="!getPersonaAvatar(msg.persona_id)" name="mdi:account-circle" class="w-6 h-6 md:w-7 md:h-7 text-history-brown" />
               </template>
             </template>
          </div>
          
          <!-- Message Bubble -->
          <div :class="['max-w-[80vw] md:max-w-2xl rounded-xl shadow-sm border-2 p-3 md:p-4 relative', 
            msg.role === 'user' 
                ? 'bg-history-dark text-history-paper border-history-dark rounded-br-none' 
                : 'bg-history-cream text-history-dark border-history-brown rounded-bl-none'
          ]">
             <div v-if="msg.role === 'model' && msg.persona_name" class="mb-1 md:mb-2 border-b border-history-brown/20 pb-1">
               <p class="text-xs text-history-accent font-bold tracking-wider uppercase">{{ msg.persona_name }}</p>
             </div>
             <div class="font-sans text-sm md:text-base leading-relaxed break-words">
               <!-- 多人思考中動畫 -->
               <div v-if="msg.role === 'model' && msg.content === '...'" class="py-1">
                 <p v-if="msg.persona_id === '__thinking__'" class="text-xs md:text-sm text-history-accent italic mb-1 animate-pulse">
                   {{ thinkingText }}
                 </p>
                 <div class="flex items-center space-x-1">
                   <span class="w-1.5 h-1.5 md:w-2 md:h-2 bg-history-brown rounded-full animate-bounce"></span>
                   <span class="w-1.5 h-1.5 md:w-2 md:h-2 bg-history-brown rounded-full animate-bounce" style="animation-delay: 100ms"></span>
                   <span class="w-1.5 h-1.5 md:w-2 md:h-2 bg-history-brown rounded-full animate-bounce" style="animation-delay: 200ms"></span>
                 </div>
               </div>
              <Typewriter v-else-if="msg.role === 'model' && index === history.length - 1" :text="msg.content" :annotations="msg.annotations" />
              <AnnotatedText v-else-if="msg.annotations && msg.annotations.length > 0"  :content="msg.content" :annotations="msg.annotations" />
              <p v-else class="whitespace-pre-wrap">{{ msg.content }}</p>
             </div>
             
             <!-- RAG 來源區塊 (可收合) -->
             <div v-if="msg.role === 'model' && msg.rag_sources && msg.rag_sources.length > 0 && msg.content !== '...'" class="mt-2 border-t border-history-brown/20 pt-2">
               <button 
                 @click="toggleSources(index)"
                 class="text-xs text-history-accent hover:text-history-brown flex items-center gap-1 transition-colors"
               >
                 <Icon :name="expandedSources[index] ? 'mdi:chevron-down' : 'mdi:chevron-right'" class="w-4 h-4" />
                 <span>📚 參考來源 ({{ msg.rag_sources.length }})</span>
               </button>
               <div v-if="expandedSources[index]" class="mt-2 space-y-2">
                 <div 
                   v-for="(src, sIdx) in msg.rag_sources" 
                   :key="sIdx"
                   class="p-2 bg-history-paper/60 rounded border border-history-brown/10 text-xs"
                 >
                   <p class="font-semibold text-history-accent">{{ src.section_title }}</p>
                   <p class="text-history-dark/80 mt-1 line-clamp-3">{{ src.content }}</p>
                   <p class="text-history-brown/60 text-[10px] mt-1 uppercase">來源: {{ formatSourceName(src.source) }}</p>
                 </div>
               </div>
             </div>
          </div>

          <div v-if="msg.role === 'user'" class="w-10 h-10 md:w-12 md:h-12 flex-shrink-0 bg-history-dark rounded-full flex items-center justify-center border-2 border-history-brown shadow-sm">
            <Icon name="mdi:account" class="w-6 h-6 md:w-7 md:h-7 text-history-paper" />
          </div>
        </div>
        <div ref="chatEndRef" />
      </main>

      <footer class="p-3 md:p-4 bg-history-light border-t-2 border-history-brown shrink-0 z-20 pb-safe">
        <!-- 人物選擇器 -->
        <div class="flex items-center gap-2 mb-2 overflow-x-auto no-scrollbar">
          <span class="text-xs text-history-brown/60 whitespace-nowrap">指定回應：</span>
          <button
            @click="selectedPersonaId = null"
            :class="['px-2 py-1 rounded-full text-xs transition-all whitespace-nowrap',
              selectedPersonaId === null 
                ? 'bg-history-dark text-history-paper' 
                : 'bg-history-cream text-history-brown hover:bg-history-brown/20']"
          >
            ✨ 自動
          </button>
          <button
            v-for="persona in personas"
            :key="persona.id"
            @click="selectedPersonaId = persona.id"
            :class="['flex items-center gap-1.5 px-2 py-1 rounded-full text-xs transition-all whitespace-nowrap',
              selectedPersonaId === persona.id 
                ? 'bg-history-accent text-history-paper ring-2 ring-history-dark' 
                : 'bg-history-cream text-history-brown hover:bg-history-brown/20']"
          >
            <img 
              v-if="persona.avatar_url" 
              :src="persona.avatar_url" 
              :alt="persona.name"
              class="w-5 h-5 rounded-full object-cover"
            />
            <Icon v-else name="mdi:account-circle" class="w-5 h-5" />
            <span>{{ persona.name }}</span>
          </button>
        </div>
        
        <form @submit.prevent="handleSendMessage" class="flex items-center gap-2 md:gap-3">
           <button 
            type="button" 
            @click="() => {}" 
            :disabled="isReplying"
            class="bg-history-accent hover:bg-history-brown disabled:bg-history-light disabled:text-history-brown/50 rounded-full p-2 md:p-3 text-history-paper transition-colors flex-shrink-0 disabled:cursor-not-allowed border-2 border-history-dark shadow-sm flex items-center justify-center"
            title="語音輸入（即將推出）"
          >
            <Icon name="mdi:microphone" class="w-5 h-5 md:w-6 md:h-6" />
          </button>

          <input
            type="text"
            v-model="userInput"
            :placeholder="selectedPersonaId ? `向 ${getPersonaName(selectedPersonaId)} 提問...` : '向歷史人物們提問...'"
            class="flex-1 w-full px-4 py-2 md:px-6 md:py-3 bg-history-cream border-2 border-history-brown rounded-full focus:outline-none focus:border-history-dark text-history-dark placeholder-history-brown/60 font-sans shadow-inner text-sm md:text-base"
            :disabled="isReplying"
          />
          <button type="submit" :disabled="isReplying || !userInput.trim()" class="bg-history-dark hover:bg-history-brown disabled:bg-history-light disabled:text-history-brown/50 rounded-full p-2 md:p-3 text-history-paper transition-colors border-2 border-history-dark shadow-sm flex items-center justify-center">
            <Icon name="mdi:send" class="w-5 h-5 md:w-6 md:h-6"/>
          </button>
        </form>
      </footer>
    </div>

    <!-- Historical Figures Sidebar -->
    <div class="w-80 border-l-2 border-history-brown shrink-0 hidden lg:block h-full">
      <HistoricalFiguresList 
        :personas="personas"
        :active-persona-id="activePersonaId"
        @update-persona="(p) => $emit('update-persona', p)"
      />
    </div>

    <!-- Persona Card Modal -->
    <PersonaCardModal 
      v-if="event && showPersonaCards"
      :event-id="event.id"
      :event-name="event.name"
      :conversation-id="conversationId"
      @close="showPersonaCards = false"
      @hint-requested="$emit('hint-requested')"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed, onUnmounted } from 'vue';
import type { ChatMessage, HistoricalEvent, Persona, RelatedEvent, RagSource } from '../types';
import Typewriter from './Typewriter.vue';
import AnnotatedText from './AnnotatedText.vue';
import HistoricalFiguresList from './HistoricalFiguresList.vue';
import PersonaCardModal from './PersonaCardModal.vue';

const props = defineProps<{
  event: HistoricalEvent | null;
  personas: Persona[];
  history: ChatMessage[];
  conversationId: string;
  relatedEvents?: RelatedEvent[];
  dynamicContext: string;
  backgroundUrl?: string;
}>();

const emit = defineEmits<{
  (e: 'reset'): void;
  (e: 'send-message', userInput: string, targetPersonaId?: string): void;
  (e: 'hint-requested'): void;
  (e: 'update-persona', persona: Persona): void;
}>();

const userInput = ref('');
const chatEndRef = ref<HTMLDivElement | null>(null);
const showPersonaCards = ref(false);
const expandedSources = ref<Record<number, boolean>>({});
const selectedPersonaId = ref<string | null>(null);

// RAG 來源展開/收合
const toggleSources = (index: number) => {
  expandedSources.value[index] = !expandedSources.value[index];
};

// 格式化來源名稱
const formatSourceName = (source: string) => {
  const sourceMap: Record<string, string> = {
    'wikipedia_zh': '維基百科 (中文)',
    'wikipedia_en': 'Wikipedia (EN)',
    'unknown': '未知來源'
  };
  return sourceMap[source] || source;
};

// 判斷是否為思考中狀態的頭像
const isThinkingAvatar = (msg: ChatMessage) => {
  return msg.content === '...' && msg.role === 'model';
};

// 思考中文字輪播
const thinkingTexts = [
  '正在回顧歷史記憶...',
  '思考著如何回應...',
  '穿越時空的對話中...',
  '翻閱歷史的篇章...',
  '組織歷史的脈絡...'
];
const thinkingTextIndex = ref(0);

// 動態思考文字 (根據是否指定人物)
const thinkingText = computed(() => {
  const lastMsg = props.history[props.history.length - 1];
  if (lastMsg?.content === '...' && lastMsg?.persona_id && lastMsg.persona_id !== '__thinking__') {
    return `${lastMsg.persona_name} 正在組織回應...`;
  }
  return thinkingTexts[thinkingTextIndex.value];
});

// 思考文字輪播
let thinkingInterval: NodeJS.Timeout | null = null;

watch(() => props.history, (newHistory) => {
  const lastMsg = newHistory[newHistory.length - 1];
  const isThinking = lastMsg?.content === '...';
  
  if (isThinking && !thinkingInterval) {
    // 開始輪播
    thinkingTextIndex.value = 0;
    thinkingInterval = setInterval(() => {
      thinkingTextIndex.value = (thinkingTextIndex.value + 1) % thinkingTexts.length;
    }, 2000);
  } else if (!isThinking && thinkingInterval) {
    // 停止輪播
    clearInterval(thinkingInterval);
    thinkingInterval = null;
  }
}, { deep: true });

onUnmounted(() => {
  if (thinkingInterval) {
    clearInterval(thinkingInterval);
  }
});

const isReplying = computed(() => {
    const lastMsg = props.history[props.history.length - 1];
    return props.history.length > 0 && lastMsg?.content === '...';
});

const activePersonaId = computed(() => {
  // Find the last message from a persona
  for (let i = props.history.length - 1; i >= 0; i--) {
    const msg = props.history[i];
    if (msg.role === 'model' && msg.persona_id) {
      return msg.persona_id;
    }
  }
  return undefined;
});

// 關聯事件列表
const relatedEvents = computed(() => props.relatedEvents || []);

// 可探索的事件（資料庫有）
const explorableEvents = computed(() => 
  relatedEvents.value.filter(e => e.is_explorable)
);

// 僅提及的事件（資料庫沒有）
const mentionedEvents = computed(() => 
  relatedEvents.value.filter(e => !e.is_explorable)
);

// 切換到可探索的事件
const switchToEvent = async (event: RelatedEvent) => {
  if (!event.event_id) return;
  
  const confirmed = confirm(
    `確定要切換到「${event.event_name}」嗎？\n當前對話將會被保存。`
  );
  
  if (!confirmed) return;
  
  try {
    // 呼叫 API 創建新對話
    const response = await $fetch<any>('/api/conversations', {
      method: 'POST',
      body: {
        event_id: event.event_id
      }
    });
    
    // 更新 chatData state
    const chatData = useState('chatData');
    chatData.value = {
      event: response.event,
      personas: response.personas,
      greeting: response.greeting,
      knowledge_badges: response.knowledge_badges,
      conversation_id: response.conversation_id,
      event_id: response.event.id,
      history: []
    };
    
    // 導航到新對話
    await navigateTo(`/chat?conversationId=${response.conversation_id}`);
    
  } catch (error) {
    console.error('Failed to switch event:', error);
    alert('切換事件失敗，請稍後再試');
  }
};

// 探索新事件（帶入首頁）
const exploreNewEvent = async (event: RelatedEvent) => {
  // 將事件名稱存到 localStorage
  localStorage.setItem('pendingEventSearch', event.event_name);
  
  // 導航到首頁
  await navigateTo('/');
};

const getPersonaAvatar = (personaId?: string) => {
  if (!personaId) return null;
  const persona = props.personas.find(p => p.id === personaId);
  return persona?.avatar_url || null;
};

const getPersonaName = (personaId: string) => {
  const persona = props.personas.find(p => p.id === personaId);
  return persona?.name || '歷史人物';
};

watch(() => props.history, async () => {
  await nextTick();
  chatEndRef.value?.scrollIntoView({ behavior: 'smooth' });
}, { deep: true });

const handleSendMessage = () => {
  if (!userInput.value.trim() || isReplying.value) return;
  emit('send-message', userInput.value, selectedPersonaId.value || undefined);
  userInput.value = '';
};
</script>

<style scoped>
@keyframes fade-in {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fade-in 0.5s ease-out;
}

@keyframes thinking-pulse {
  0%, 100% { 
    transform: scale(1); 
    opacity: 1;
  }
  50% { 
    transform: scale(1.05); 
    opacity: 0.85;
  }
}
.animate-thinking-pulse {
  animation: thinking-pulse 1.5s ease-in-out infinite;
}

/* 人物登場動畫 */
@keyframes persona-entrance {
  0% { 
    transform: scale(0.8) translateY(10px); 
    opacity: 0;
  }
  50% { 
    transform: scale(1.1); 
    opacity: 1;
  }
  100% { 
    transform: scale(1) translateY(0); 
    opacity: 1;
  }
}
.animate-persona-entrance {
  animation: persona-entrance 0.6s ease-out forwards;
}

/* 聚光燈光暈 */
@keyframes spotlight-glow {
  0%, 100% { 
    opacity: 0.4;
    transform: scale(1);
  }
  50% { 
    opacity: 0.7;
    transform: scale(1.1);
  }
}
.animate-spotlight-glow {
  animation: spotlight-glow 2s ease-in-out infinite;
}

/* Hide scrollbar for Chrome, Safari and Opera */
.no-scrollbar::-webkit-scrollbar {
    display: none;
}
/* Hide scrollbar for IE, Edge and Firefox */
.no-scrollbar {
    -ms-overflow-style: none;  /* IE and Edge */
    scrollbar-width: none;  /* Firefox */
}
</style>