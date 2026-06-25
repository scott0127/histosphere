// useConversationSession 集中管理 conversation 頁的 API orchestration。
// Nuxt page 只負責 route binding，ChatScreen 只負責畫面與互動事件。
import type {
  ChatMessage,
  ChatResponse,
  ConversationLoadResponse,
  TaskSubmitResponse,
} from '~/types';
import type { ComputedRef, Ref } from 'vue';
import {
  fetchConversation,
  sendChatMessage as requestChatMessage,
} from '~/utils/histosphereApi';

type ConversationState = (TaskSubmitResponse | ConversationLoadResponse) & {
  attempt?: TaskSubmitResponse['attempt'];
  task_attempt?: ConversationLoadResponse['task_attempt'];
};

const historyFromState = (state: ConversationState | null): ChatMessage[] => {
  if (!state) return [];
  if ('history' in state && Array.isArray(state.history)) return state.history;
  if ('messages' in state && Array.isArray(state.messages)) return state.messages;
  return [];
};

export const useConversationSession = (conversationId: Ref<string> | ComputedRef<string>) => {
  const chatState = useState<ConversationState | null>('chatData', () => null);
  const history = ref<ChatMessage[]>([]);
  const dynamicContext = ref('Conversation ready.');
  const isLoading = ref(false);
  const loadError = ref<string | null>(null);

  const taskAttempt = computed(() => chatState.value?.attempt || chatState.value?.task_attempt || null);

  const loadConversation = async () => {
    const currentConversationId = conversationId.value;
    if (!currentConversationId) return;

    const cachedHistory = chatState.value?.conversation_id === currentConversationId
      ? historyFromState(chatState.value)
      : [];
    if (cachedHistory.length > 0) {
      history.value = cachedHistory;
      return;
    }

    isLoading.value = true;
    loadError.value = null;
    try {
      const data: ConversationLoadResponse = await fetchConversation(currentConversationId);
      chatState.value = data as ConversationState;
      history.value = data.messages;
    } catch (e: any) {
      loadError.value = e.data?.detail || e.data?.message || '無法載入對話。';
      throw e;
    } finally {
      isLoading.value = false;
    }
  };

  const sendMessage = async (userInput: string, targetPersonaId?: string) => {
    const currentConversationId = conversationId.value;
    if (!currentConversationId || !chatState.value) return;

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
      const response: ChatResponse = await requestChatMessage({
        conversationId: currentConversationId,
        userMessage: userInput,
        history: history.value.slice(0, -1),
        targetPersonaId,
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

  const resetConversationState = () => {
    chatState.value = null;
    history.value = [];
  };

  return {
    chatState,
    dynamicContext,
    history,
    isLoading,
    loadConversation,
    loadError,
    resetConversationState,
    sendMessage,
    taskAttempt,
  };
};
