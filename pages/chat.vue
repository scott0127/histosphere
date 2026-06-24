<template>
  <!-- Legacy route kept for existing links: /chat?conversationId=... -->
  <div class="flex h-screen items-center justify-center bg-[var(--admin-page)] font-sans text-[var(--admin-copy)]">
    <div class="text-center">
      <Icon name="mdi:loading" class="mx-auto h-8 w-8 animate-spin" />
      <p class="mt-3">正在開啟對話...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: false,
  name: 'chat-legacy',
  validate: async (route) => typeof route.query.conversationId === 'string',
});

const route = useRoute();

onMounted(async () => {
  const conversationId = typeof route.query.conversationId === 'string'
    ? route.query.conversationId
    : '';
  if (!conversationId) {
    await navigateTo('/');
    return;
  }

  await navigateTo(`/conversations/${encodeURIComponent(conversationId)}`, { replace: true });
});
</script>
