<template>
  <!-- chat.vue 是容器頁，只處理資料載入與 API 呼叫；實際對話 UI 在 ChatScreen.vue。 -->
  <ChatScreen
    v-if="chatState"
    :event="chatState.event"
    :personas="chatState.personas"
    :history="history"
    :conversation-id="conversationId"
    :condition="chatState.condition"
    :task-attempt="taskAttempt"
    :dynamic-context="dynamicContext"
    @reset="handleReset"
    @send-message="handleSendMessage"
  />
  <div v-else class="flex h-screen items-center justify-center bg-[var(--admin-page)] font-sans text-[var(--admin-copy)]">
    <div class="text-center">
      <Icon name="mdi:loading" class="mx-auto h-8 w-8 animate-spin" />
      <p class="mt-3">載入對話...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
// 對話頁資料流：
// - 若從 task submit 導入，優先使用 useState('chatData')，避免剛建立 conversation 後再打一輪載入。
// - 若使用者重新整理或直接進入網址，改用 conversationId 從後端重新載入。
// - 傳送訊息時先做 optimistic UI，再用後端回傳的正式 message 替換。
import type {
  ChatMessage,
  ChatResponse,
  ConversationLoadResponse,
  TaskSubmitResponse,
} from '~/types';

definePageMeta({
  layout: false,
  name: 'chat',
  validate: async (route) => typeof route.query.conversationId === 'string',
});

const route = useRoute();
const conversationId = computed(() => route.query.conversationId as string);

type ChatState = (TaskSubmitResponse | ConversationLoadResponse) & {
  attempt?: TaskSubmitResponse['attempt'];
  task_attempt?: ConversationLoadResponse['task_attempt'];
};

const chatState = useState<ChatState | null>('chatData', () => null);
const history = ref<ChatMessage[]>([]);
const dynamicContext = ref('Conversation ready.');
const taskAttempt = computed(() => chatState.value?.attempt || chatState.value?.task_attempt || null);

onMounted(async () => {
  if (chatState.value && 'history' in chatState.value && chatState.value.history?.length) {
    history.value = chatState.value.history;
    return;
  }

  try {
    const data = await $fetch<ConversationLoadResponse>(`/api/conversations/${conversationId.value}`);
    chatState.value = data as ChatState;
    history.value = data.messages;
  } catch (e) {
    console.error('Failed to load conversation:', e);
    alert('無法載入對話，將返回首頁');
    await navigateTo('/');
  }
});

// 先把 learner 訊息與「...」暫存回覆放進 history，讓 UI 立即有回應感。
// 後端回傳後，最後一則 placeholder 會被正式 message 取代。
const handleSendMessage = async (userInput: string, targetPersonaId?: string) => {
  if (!conversationId.value || !chatState.value) return;

  const nextIndex = history.value.length;
  history.value.push({
    speaker_type: 'learner',
    speaker_name: 'learner',
    sequence_index: nextIndex,
    content: userInput,
  });

  const thinkingSpeaker = chatState.value.condition?.roleplay_enabled ? 'persona' : 'assistant';
  const targetPersona = targetPersonaId
    ? chatState.value.personas.find((persona) => persona.id === targetPersonaId)
    : null;
  history.value.push({
    speaker_type: thinkingSpeaker,
    speaker_name: targetPersona?.name || (thinkingSpeaker === 'persona' ? '歷史人物' : 'AI Assistant'),
    persona_id: targetPersona?.id,
    sequence_index: nextIndex + 1,
    content: '...',
  });

  try {
    const response = await $fetch<ChatResponse>('/api/chat', {
      method: 'POST',
      body: {
        conversation_id: conversationId.value,
        user_message: userInput,
        history: history.value.slice(0, -1),
        target_persona_id: targetPersonaId || null,
      },
    });

    history.value[history.value.length - 1] = response.message;
    if (response.dynamic_context) dynamicContext.value = response.dynamic_context;
  } catch (e) {
    console.error('Failed to send message:', e);
    history.value[history.value.length - 1] = {
      speaker_type: 'assistant',
      speaker_name: 'System',
      sequence_index: nextIndex + 1,
      content: '回應失敗，請稍後再試。',
    };
  }
};

// 回素材庫時清掉暫存 chatData，避免下一次進 chat 時混到舊 session。
const handleReset = async () => {
  chatState.value = null;
  await navigateTo('/');
};
</script>
