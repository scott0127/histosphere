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
    :dynamic-context="dynamicContext"
    @reset="handleReset"
    @send-message="sendMessage"
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
  loadConversation,
  loadError,
  resetConversationState,
  sendMessage,
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
</script>
