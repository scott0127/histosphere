<template>
  <div class="h-screen w-screen bg-history-dark font-serif relative overflow-hidden">
    <!-- 背景圖層 (帶過渡動畫) -->
    <div 
      class="absolute inset-0 bg-cover bg-center bg-no-repeat transition-opacity duration-1000 ease-in-out"
      :class="{ 'opacity-0': isTransitioningBg, 'opacity-100': !isTransitioningBg }"
      :style="backgroundStyle"
    ></div>
    
    <!-- 生成中遮罩 -->
    <Transition name="fade">
      <div 
        v-if="isRegeneratingBg" 
        class="absolute inset-0 bg-black/60 z-40 flex items-center justify-center"
      >
        <div class="text-white text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-4 border-white/30 border-t-white mx-auto mb-4"></div>
          <p class="text-lg font-medium">正在生成新背景...</p>
          <p class="text-sm text-white/60 mt-2">請稍候片刻</p>
        </div>
      </div>
    </Transition>

    <!-- 重新生成背景按鈕 -->
    <button
      v-if="chatData?.event && !isRegeneratingBg"
      @click="regenerateBackground"
      class="absolute bottom-4 right-4 z-50 bg-black/50 hover:bg-black/70 text-white px-3 py-2 rounded-lg 
             flex items-center gap-2 text-sm backdrop-blur-sm transition-all duration-300 hover:scale-105"
      title="點擊重新生成背景圖片"
    >
      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
      換背景
    </button>

    <div class="h-full w-full max-w-7xl mx-auto shadow-2xl relative z-10">
      <ChatScreen
        v-if="chatData"
        :event="chatData.event"
        :personas="chatData.personas"
        :history="history"
        :conversation-id="conversationId"
        :related-events="relatedEvents"
        :dynamic-context="dynamicContext"
        :background-url="chatData.event?.background_url"
        @reset="handleReset"
        @send-message="handleSendMessage"
        @hint-requested="refreshMessages"
        @update-persona="handleUpdatePersona"
      />
      <div v-else class="flex items-center justify-center h-full">
        <div class="text-white text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>載入對話...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage, HistoricalEvent, Persona, RelatedEvent, RagSource } from '~/types';

definePageMeta({
  layout: false,
  name: 'chat',
  validate: async (route) => {
    // 確保有 conversationId
    return typeof route.query.conversationId === 'string';
  }
});

const route = useRoute();
const conversationId = computed(() => route.query.conversationId as string);

// 從 useState 獲取初始資料
const chatData = useState<{
  event: HistoricalEvent;
  personas: Persona[];
  greeting: string;
  conversation_id: string;
  event_id: string;
  history?: ChatMessage[];
} | null>('chatData');

const history = ref<ChatMessage[]>([]);
const relatedEvents = ref<RelatedEvent[]>([]);
const dynamicContext = ref<string>('🌅 歷史的大門正在開啟...');
const isRegeneratingBg = ref<boolean>(false);
const isTransitioningBg = ref<boolean>(false);

// 背景樣式
const backgroundStyle = computed(() => {
  if (!chatData.value?.event?.background_url) return {};
  return { backgroundImage: `url(${chatData.value.event.background_url})` };
});

// 重新生成背景圖 (帶平滑過渡)
const regenerateBackground = async () => {
  if (!chatData.value?.event?.id || isRegeneratingBg.value) return;
  
  isRegeneratingBg.value = true;
  
  try {
    const response = await $fetch<{ background_url: string }>(`/api/event/${chatData.value.event.id}/regenerate-background`, {
      method: 'POST'
    });
    
    if (response.background_url && chatData.value) {
      // 淡出舊圖
      isTransitioningBg.value = true;
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // 更新圖片 URL (加時間戳強制刷新)
      const cacheBuster = `?t=${Date.now()}`;
      chatData.value.event.background_url = response.background_url + cacheBuster;
      
      // 等待圖片預載入後淡入
      const img = new Image();
      img.onload = () => {
        isTransitioningBg.value = false;
      };
      img.onerror = () => {
        isTransitioningBg.value = false;
      };
      img.src = response.background_url + cacheBuster;
    }
  } catch (e) {
    console.error('Failed to regenerate background:', e);
    alert('背景圖生成失敗，請稍後再試');
  } finally {
    isRegeneratingBg.value = false;
  }
};

// 初始化聊天歷史
// 單次更新訊息
const refreshMessages = async () => {
  if (!conversationId.value) return;
  
  try {
    const data = await $fetch<any>(`/api/conversations/${conversationId.value}`);
    history.value = data.messages;
  } catch (e) {
    console.error('Failed to refresh messages:', e);
  }
};

// 暴露 refreshMessages 給子元件使用
defineExpose({
  refreshMessages
});

onMounted(async () => {
  if (chatData.value) {
    if (chatData.value.history && chatData.value.history.length > 0) {
      // 如果有歷史紀錄，直接使用
      history.value = chatData.value.history;
    } else {
      // 否則使用 greeting
      history.value = [{ 
        role: 'model', 
        agent: 'persona',
        persona_id: chatData.value.personas[0]?.id,
        persona_name: chatData.value.personas[0]?.name,
        content: chatData.value.greeting 
      }];
    }
  } else if (conversationId.value) {
    // 如果沒有 chatData (例如重新整理)，嘗試從 API 獲取
    try {
      const data = await $fetch<any>(`/api/conversations/${conversationId.value}`);
      
      // 更新 chatData
      chatData.value = {
        event: data.event,
        personas: data.personas,
        greeting: '', // 載入現有對話時，greeting 已在歷史訊息中
        conversation_id: data.conversation_id,
        event_id: data.event.id,
        history: data.messages
      };
      
      history.value = data.messages;
      
      // 設定關聯事件（如果有）
      if (data.related_events) {
        relatedEvents.value = data.related_events;
      }
      
    } catch (e) {
      console.error('Failed to load conversation:', e);
      alert('無法載入對話，將返回首頁');
      navigateTo('/');
    }
  }
});

const handleSendMessage = async (userInput: string, targetPersonaId?: string) => {
  if (!conversationId.value) return;

  // 找出目標人物名稱 (如果有指定)
  const targetPersona = targetPersonaId 
    ? chatData.value?.personas.find(p => p.id === targetPersonaId)
    : null;

  const userMessage: ChatMessage = { 
    role: 'user', 
    agent: 'user',
    content: userInput 
  };
  history.value.push(userMessage);

  const tempBotMessage: ChatMessage = { 
    role: 'model', 
    agent: 'persona',
    persona_id: targetPersonaId || '__thinking__',  // 如果有指定人物，顯示該人物
    persona_name: targetPersona?.name || '歷史人物們',
    content: '...' 
  };
  history.value.push(tempBotMessage);

  try {
    const response = await $fetch<{ 
      response: string; 
      annotations: any[];
      selected_persona: Persona;
      related_events?: RelatedEvent[];
      dynamic_context?: string;
      rag_sources?: RagSource[];
    }>('/api/chat', {
      method: 'POST',
      body: {
        conversation_id: conversationId.value,
        user_message: userInput,
        history: history.value.slice(0, -1),
        target_persona_id: targetPersonaId || null,
      },
    });

    history.value[history.value.length - 1] = { 
      role: 'model',
      agent: 'persona',
      persona_id: response.selected_persona.id,
      persona_name: response.selected_persona.name,
      content: response.response,
      annotations: response.annotations,
      rag_sources: response.rag_sources
    };
    
    // 更新關聯事件
    if (response.related_events) {
      relatedEvents.value = response.related_events;
    }
    
    // 更新動態情境
    if (response.dynamic_context) {
      dynamicContext.value = response.dynamic_context;
    }

    // 更新 chatData 中的 personas 列表，以防有新的 persona 資訊 (例如頭像更新)
    // 雖然目前後端不會動態更新頭像，但這是一個好習慣
    // 這裡我們假設 response.selected_persona 包含了完整的 persona 資訊
    // 但 ChatResponse 的 selected_persona 是 PersonaResponse，包含 avatar_url
    if (chatData.value) {
      const pIndex = chatData.value.personas.findIndex(p => p.id === response.selected_persona.id);
      if (pIndex !== -1) {
        // 更新現有 persona
        chatData.value.personas[pIndex] = {
          ...chatData.value.personas[pIndex],
          ...response.selected_persona
        };
      } else {
        // 如果是新 persona (理論上不會發生，除非動態新增)，加入列表
        chatData.value.personas.push(response.selected_persona);
      }
    }

  } catch (e: any) {
    const errorMessage: ChatMessage = { 
      role: 'model', 
      agent: 'persona',
      content: '我似乎無法回應。請稍後再試。' 
    };
    history.value[history.value.length - 1] = errorMessage;
  }
};

const handleReset = async () => {
  // 清除 state
  useState('chatData', () => null);
  
  // 導航回首頁
  await navigateTo('/');
};

const handleUpdatePersona = (updatedPersona: Persona) => {
  if (!chatData.value) return;
  
  const index = chatData.value.personas.findIndex(p => p.id === updatedPersona.id);
  if (index !== -1) {
    chatData.value.personas[index] = updatedPersona;
  }
};
</script>

<style scoped>
/* 淡入淡出動畫 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
