<template>
  <ChatScreen
    v-if="chatState"
    :event="chatState.event"
    :personas="chatState.personas"
    :history="history"
    :conversation-id="conversationId"
    :condition="chatState.condition"
    :task-attempt="chatState.attempt || chatState.task_attempt"
    :dynamic-context="dynamicContext"
    @reset="handleReset"
    @send-message="handleSendMessage"
  />
  <div v-else class="flex h-screen items-center justify-center bg-slate-50 font-sans text-slate-600">
    <div class="text-center">
      <Icon name="mdi:loading" class="mx-auto h-8 w-8 animate-spin" />
      <p class="mt-3">載入對話...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
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
};

const chatState = useState<ChatState | null>('chatData', () => null);
const history = ref<ChatMessage[]>([]);
const dynamicContext = ref('Conversation ready.');

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

const handleReset = async () => {
  chatState.value = null;
  await navigateTo('/');
};
</script>
