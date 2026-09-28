<template>
  <!-- Conversation route: /conversations/[conversationId] 是正式對話入口。 -->
  <ChatScreen
    v-if="chatState"
    :event="chatState.event"
    :personas="chatState.personas"
    :history="history"
    :conversation-id="conversationId"
    :condition="chatState.condition"
    :task="task"
    :task-attempt="taskAttempt"
    :learning-focus="chatState.learning_focus"
    :dynamic-context="dynamicContext"
    :session="session"
    :is-replying="isSending"
    :reply-status="streamStatus"
    @next-stage="handleNextStage"
    @reset="handleReset"
    @session-expired="handleSessionExpired"
    @send-message="sendMessage"
    @retry-message="retryMessage"
  />
  <div v-else class="flex h-screen items-center justify-center bg-[var(--admin-page)] font-sans text-[var(--admin-copy)]">
    <div class="text-center">
      <Icon name="mdi:loading" class="mx-auto h-8 w-8 animate-spin" />
      <p class="mt-3">{{ loadError || '載入對話...' }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
// 此頁只做 route binding；conversation loading / send message 在 useConversationSession。
definePageMeta({
  layout: false,
  name: 'conversation-detail',
  validate: async (route) => typeof route.params.conversationId === 'string' && route.params.conversationId.length > 0,
});

const route = useRoute();
const conversationId = computed(() => route.params.conversationId as string);
const {
  chatState,
  dynamicContext,
  history,
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
} = useConversationSession(conversationId);

onMounted(async () => {
  try {
    await loadConversation();
  } catch (e) {
    console.error('Failed to load conversation:', e);
    alert('無法載入對話，將返回首頁');
    await navigateTo('/');
  }
});

const handleReset = async () => {
  resetConversationState();
  await navigateTo('/');
};

const handleSessionExpired = async () => {
  try {
    await loadConversation();
  } catch (e) {
    console.error('Failed to refresh the expired session:', e);
  }
};

const handleNextStage = async () => {
  const sessionId = session.value?.id;
  if (!sessionId) return;
  resetConversationState();
  await navigateTo(`/posttest/${sessionId}`);
};
</script>
