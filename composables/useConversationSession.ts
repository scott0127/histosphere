// useConversationSession 集中管理 conversation 頁的 API orchestration。
// Nuxt page 只負責 route binding，ChatScreen 只負責畫面與互動事件。
import type {
  ChatMessage,
  ChatOperationStatusResponse,
  ChatResponse,
  ChatStreamEvent,
  ConversationLoadResponse,
  ExperimentCondition,
  Persona,
  TaskSubmitResponse,
} from '~/types';
import type { ComputedRef, Ref } from 'vue';
import {
  fetchChatOperationStatus,
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

const CHAT_OPERATION_POLL_INTERVAL_MS = 2000;
const CHAT_OPERATION_MAX_POLLS = 90;

const waitForNextPoll = () => new Promise((resolve) => {
  globalThis.setTimeout(resolve, CHAT_OPERATION_POLL_INTERVAL_MS);
});

const messageRequestId = (message: ChatMessage): string | null => {
  if (message.client_request_id) return message.client_request_id;
  const metadataRequestId = message.metadata?.client_request_id;
  return typeof metadataRequestId === 'string' ? metadataRequestId : null;
};

export const resolvePendingAssistantIdentity = (
  condition: Pick<ExperimentCondition, 'roleplay_enabled'> | null | undefined,
  personas: Persona[],
  history: ChatMessage[],
) => {
  if (!condition?.roleplay_enabled) {
    return {
      speakerType: 'assistant' as const,
      speakerName: 'AI Assistant',
      personaId: undefined,
    };
  }

  const lockedPersonaId = history.find((message) => message.persona_id)?.persona_id;
  const targetPersona = personas.find((persona) => {
    return lockedPersonaId ? persona.id === lockedPersonaId : persona.active;
  }) || null;
  return {
    speakerType: 'persona' as const,
    speakerName: targetPersona?.name || '歷史人物',
    personaId: targetPersona?.id,
  };
};

export const useConversationSession = (conversationId: Ref<string> | ComputedRef<string>) => {
  const chatState = useState<ConversationState | null>('chatData', () => null);
  const history = ref<ChatMessage[]>([]);
  const dynamicContext = ref('Conversation ready.');
  const isLoading = ref(false);
  const isSending = ref(false);
  const loadError = ref<string | null>(null);
  const streamStatus = ref('');
  const pollingRequestId = ref<string | null>(null);

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
      ensureFailedOperationMessages();
      const activeOperation = [...data.messages]
        .reverse()
        .find((message) => {
          return message.speaker_type === 'learner'
            && ['pending', 'processing'].includes(message.operation_status || '');
        });
      const activeRequestId = activeOperation ? messageRequestId(activeOperation) : null;
      if (activeRequestId) void resumeOperation(activeRequestId);
    } catch (e: any) {
      loadError.value = e.data?.detail || e.data?.message || '無法載入對話。';
      throw e;
    } finally {
      isLoading.value = false;
    }
  };

  const createAssistantPlaceholder = (requestId: string): ChatMessage => {
    const identity = resolvePendingAssistantIdentity(
      chatState.value?.condition,
      chatState.value?.personas || [],
      history.value,
    );
    return {
      id: `local-${requestId}-assistant`,
      speaker_type: identity.speakerType,
      speaker_name: identity.speakerName,
      persona_id: identity.personaId,
      sequence_index: history.value.length,
      content: '',
      client_request_id: requestId,
      metadata: {
        client_request_id: requestId,
        generation_status: 'pending',
        delivery_mode: 'validated_stream',
      },
    };
  };

  const applyCompletedResponse = (
    requestId: string,
    response: ChatResponse,
    learnerMessage?: ChatMessage,
  ) => {
    const storedLearner = learnerMessage || history.value.find((message) => {
      return message.speaker_type === 'learner' && messageRequestId(message) === requestId;
    });
    history.value = history.value.filter((message) => messageRequestId(message) !== requestId);
    if (storedLearner) {
      history.value.push({
        ...storedLearner,
        client_request_id: requestId,
        operation_status: 'completed',
        metadata: {
          ...storedLearner.metadata,
          client_request_id: requestId,
          response_status: 'completed',
          response_message_id: response.message.id,
        },
      });
    }
    history.value.push(response.message);
    history.value.sort((left, right) => left.sequence_index - right.sequence_index);
    if (response.dynamic_context) dynamicContext.value = response.dynamic_context;
    streamStatus.value = '';
  };

  const markOperationFailed = (
    requestId: string,
    detail = 'AI 回覆產生失敗。你的訊息已保存，可安全重試這次回覆。',
  ) => {
    const learner = history.value.find((message) => {
      return message.speaker_type === 'learner' && messageRequestId(message) === requestId;
    });
    history.value = history.value.filter((message) => {
      return message.speaker_type === 'learner' || messageRequestId(message) !== requestId;
    });
    if (learner) {
      const learnerIndex = history.value.findIndex((message) => message.id === learner.id);
      history.value[learnerIndex] = {
        ...learner,
        operation_status: 'failed',
        metadata: {
          ...learner.metadata,
          client_request_id: requestId,
          response_status: 'failed',
        },
      };
    }
    const alreadyHasFailure = history.value.some((message) => {
      return message.speaker_name === 'System' && messageRequestId(message) === requestId;
    });
    if (!alreadyHasFailure) {
      history.value.push({
        id: `local-${requestId}-error`,
        speaker_type: 'assistant',
        speaker_name: 'System',
        sequence_index: (learner?.sequence_index || history.value.length) + 0.5,
        content: detail,
        client_request_id: requestId,
        metadata: {
          client_request_id: requestId,
          generation_status: 'failed',
          retryable: true,
        },
      });
    }
    history.value.sort((left, right) => left.sequence_index - right.sequence_index);
  };

  const ensureFailedOperationMessages = () => {
    const failedOperations = history.value.filter((message) => {
      return message.speaker_type === 'learner'
        && message.operation_status === 'failed'
        && Boolean(messageRequestId(message));
    });
    for (const operation of failedOperations) {
      const requestId = messageRequestId(operation);
      if (requestId) markOperationFailed(requestId);
    }
  };

  const pollOperation = async (
    currentConversationId: string,
    requestId: string,
  ): Promise<ChatOperationStatusResponse> => {
    let lastError: unknown = null;
    let notFoundCount = 0;
    for (let pollIndex = 0; pollIndex < CHAT_OPERATION_MAX_POLLS; pollIndex += 1) {
      try {
        const operation = await fetchChatOperationStatus(currentConversationId, requestId);
        if (operation.status === 'completed' || operation.status === 'failed') return operation;
        streamStatus.value = '後端仍在產生回覆，連線恢復後會自動顯示…';
        notFoundCount = 0;
      } catch (error: any) {
        lastError = error;
        const statusCode = error?.statusCode || error?.response?.status;
        if (statusCode === 404) {
          notFoundCount += 1;
          if (notFoundCount >= 3) throw error;
        }
      }
      await waitForNextPoll();
    }
    throw lastError || new Error('回覆仍在後端處理，請重新整理後繼續確認。');
  };

  const resumeOperation = async (requestId: string) => {
    const currentConversationId = conversationId.value;
    if (!currentConversationId || pollingRequestId.value === requestId) return;
    pollingRequestId.value = requestId;
    isSending.value = true;
    streamStatus.value = '正在確認先前的回覆狀態…';
    try {
      const operation = await pollOperation(currentConversationId, requestId);
      if (operation.status === 'completed' && operation.response) {
        applyCompletedResponse(requestId, operation.response, operation.learner_message);
      } else {
        history.value = history.value.map((message) => {
          return messageRequestId(message) === requestId && message.speaker_type === 'learner'
            ? operation.learner_message
            : message;
        });
        markOperationFailed(requestId);
      }
    } catch (error: any) {
      console.error('Failed to resume chat operation:', error);
      markOperationFailed(
        requestId,
        error?.message || '目前無法確認回覆狀態。你的訊息若已送達，重新整理後仍會保留。',
      );
    } finally {
      pollingRequestId.value = null;
      isSending.value = false;
      streamStatus.value = '';
    }
  };

  const runOperation = async (
    userInput: string,
    requestId: string,
    retryFailed: boolean,
  ) => {
    const currentConversationId = conversationId.value;
    if (!currentConversationId || !chatState.value) return;

    isSending.value = true;
    streamStatus.value = retryFailed ? '正在重試先前回覆…' : '訊息正在保存…';
    try {
      const response = await requestChatMessageStream({
        conversationId: currentConversationId,
        userMessage: userInput,
        history: history.value.filter((message) => messageRequestId(message) !== requestId),
        clientRequestId: requestId,
        retryFailed,
      }, async (event: ChatStreamEvent) => {
        if (event.type === 'user_message') {
          history.value = history.value.map((message) => {
            return message.speaker_type === 'learner' && messageRequestId(message) === requestId
              ? event.message
              : message;
          });
          streamStatus.value = '訊息已保存，正在產生回覆…';
          return;
        }
        if (event.type === 'status') {
          streamStatus.value = event.message;
          return;
        }
        if (event.type === 'delta') {
          const assistantIndex = history.value.findIndex((message) => {
            return message.speaker_type !== 'learner' && messageRequestId(message) === requestId;
          });
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
          applyCompletedResponse(requestId, event.response);
          return;
        }
        streamStatus.value = event.detail;
      });
      applyCompletedResponse(requestId, response);
    } catch (error: any) {
      console.error('Chat stream interrupted:', error);
      try {
        const operation = await pollOperation(currentConversationId, requestId);
        if (operation.status === 'completed' && operation.response) {
          applyCompletedResponse(requestId, operation.response, operation.learner_message);
        } else {
          history.value = history.value.map((message) => {
            return messageRequestId(message) === requestId && message.speaker_type === 'learner'
              ? operation.learner_message
              : message;
          });
          markOperationFailed(requestId, error?.message);
        }
      } catch (pollError: any) {
        markOperationFailed(
          requestId,
          pollError?.message || error?.message || '目前無法確認回覆狀態。',
        );
      }
    } finally {
      isSending.value = false;
      streamStatus.value = '';
    }
  };

  const sendMessage = async (userInput: string) => {
    const currentConversationId = conversationId.value;
    if (!currentConversationId || !chatState.value || isSending.value) return;

    const requestId = globalThis.crypto?.randomUUID?.() || `${Date.now()}`;
    history.value.push({
      id: `local-${requestId}-learner`,
      speaker_type: 'learner',
      speaker_name: 'learner',
      sequence_index: history.value.length,
      content: userInput,
      client_request_id: requestId,
      operation_status: 'pending',
      metadata: {
        client_request_id: requestId,
        response_status: 'pending',
      },
    });
    history.value.push(createAssistantPlaceholder(requestId));
    await runOperation(userInput, requestId, false);
  };

  const retryMessage = async (requestId: string) => {
    if (!chatState.value || isSending.value) return;
    const learner = history.value.find((message) => {
      return message.speaker_type === 'learner' && messageRequestId(message) === requestId;
    });
    if (!learner || learner.operation_status !== 'failed') return;

    history.value = history.value.filter((message) => {
      return message.speaker_type === 'learner' || messageRequestId(message) !== requestId;
    });
    const learnerIndex = history.value.findIndex((message) => message.id === learner.id);
    history.value[learnerIndex] = {
      ...learner,
      operation_status: 'processing',
      metadata: {
        ...learner.metadata,
        response_status: 'pending',
      },
    };
    history.value.push(createAssistantPlaceholder(requestId));
    history.value.sort((left, right) => left.sequence_index - right.sequence_index);
    await runOperation(learner.content, requestId, true);
  };

  const resetConversationState = () => {
    chatState.value = null;
    history.value = [];
    isSending.value = false;
    pollingRequestId.value = null;
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
    retryMessage,
    sendMessage,
    session,
    streamStatus,
    task,
    taskAttempt,
  };
};
