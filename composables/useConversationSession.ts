// useConversationSession 集中管理 conversation 頁的 API orchestration。
// Nuxt page 只負責 route binding，ChatScreen 只負責畫面與互動事件。
import type {
  ChatMessage,
  ChatStreamEvent,
  ConversationLoadResponse,
  TaskSubmitResponse,
} from '~/types';
import type { ComputedRef, Ref } from 'vue';
import {
  fetchConversation,
  sendChatMessageStream as requestChatMessageStream,
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
  const isSending = ref(false);
  const loadError = ref<string | null>(null);
  const streamStatus = ref('');

  const taskAttempt = computed(() => chatState.value?.attempt || chatState.value?.task_attempt || null);
  const task = computed(() => chatState.value?.task || null);
  const session = computed(() => {
    return chatState.value && 'session' in chatState.value ? chatState.value.session || null : null;
  });

  const loadConversation = async () => {
    const currentConversationId = conversationId.value;
    if (!currentConversationId) return;

    const cachedHistory = chatState.value?.conversation_id === currentConversationId
      ? historyFromState(chatState.value)
      : [];
    if (cachedHistory.length > 0) {
      history.value = cachedHistory;
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
    if (!currentConversationId || !chatState.value || isSending.value) return;

    const learnerIndex = history.value.length;
    const assistantIndex = learnerIndex + 1;
    const localRequestId = globalThis.crypto?.randomUUID?.() || `${Date.now()}`;
    history.value.push({
      id: `local-${localRequestId}-learner`,
      speaker_type: 'learner',
      speaker_name: 'learner',
      sequence_index: learnerIndex,
      content: userInput,
      metadata: { response_status: 'pending' },
    });

    const thinkingSpeaker = chatState.value.condition?.roleplay_enabled ? 'persona' : 'assistant';
    const targetPersona = targetPersonaId
      ? chatState.value.personas.find((persona) => persona.id === targetPersonaId)
      : null;
    history.value.push({
      id: `local-${localRequestId}-assistant`,
      speaker_type: thinkingSpeaker,
      speaker_name: targetPersona?.name || (thinkingSpeaker === 'persona' ? '歷史人物' : 'AI Assistant'),
      persona_id: targetPersona?.id,
      sequence_index: assistantIndex,
      content: '',
      metadata: { generation_status: 'pending', delivery_mode: 'validated_stream' },
    });

    isSending.value = true;
    streamStatus.value = '訊息正在保存…';
    try {
      const response = await requestChatMessageStream({
        conversationId: currentConversationId,
        userMessage: userInput,
        history: history.value.slice(0, learnerIndex),
        targetPersonaId,
      }, async (event: ChatStreamEvent) => {
        if (event.type === 'user_message') {
          history.value[learnerIndex] = event.message;
          streamStatus.value = '訊息已保存，正在產生回覆…';
          return;
        }
        if (event.type === 'status') {
          streamStatus.value = event.message;
          return;
        }
        if (event.type === 'delta') {
          const currentMessage = history.value[assistantIndex];
          if (!currentMessage) return;
          history.value[assistantIndex] = {
            ...currentMessage,
            content: `${currentMessage.content}${event.content}`,
            metadata: {
              ...currentMessage.metadata,
              generation_status: 'streaming',
              delivery_mode: 'validated_stream',
            },
          };
          return;
        }
        if (event.type === 'complete') {
          history.value[assistantIndex] = event.response.message;
          const currentLearnerMessage = history.value[learnerIndex];
          if (currentLearnerMessage) {
            history.value[learnerIndex] = {
              ...currentLearnerMessage,
              metadata: {
                ...currentLearnerMessage.metadata,
                response_status: 'completed',
                response_message_id: event.response.message.id,
              },
            };
          }
          if (event.response.dynamic_context) dynamicContext.value = event.response.dynamic_context;
          streamStatus.value = '';
          return;
        }
        streamStatus.value = event.detail;
      });

      history.value[assistantIndex] = response.message;
      if (response.dynamic_context) dynamicContext.value = response.dynamic_context;
    } catch (e: any) {
      console.error('Failed to send message:', e);
      const currentLearnerMessage = history.value[learnerIndex];
      if (currentLearnerMessage) {
        history.value[learnerIndex] = {
          ...currentLearnerMessage,
          metadata: {
            ...currentLearnerMessage.metadata,
            response_status: 'failed',
          },
        };
      }
      history.value[assistantIndex] = {
        id: `local-${localRequestId}-error`,
        speaker_type: 'assistant',
        speaker_name: 'System',
        sequence_index: assistantIndex,
        content: e?.message || '回應失敗。你的訊息若已送達後端，重新整理後仍會保留。',
        metadata: { generation_status: 'failed' },
      };
    } finally {
      isSending.value = false;
      streamStatus.value = '';
    }
  };

  const resetConversationState = () => {
    chatState.value = null;
    history.value = [];
    isSending.value = false;
    streamStatus.value = '';
  };

  return {
    chatState,
    dynamicContext,
    history,
    isLoading,
    isSending,
    loadConversation,
    loadError,
    resetConversationState,
    sendMessage,
    session,
    streamStatus,
    task,
    taskAttempt,
  };
};
