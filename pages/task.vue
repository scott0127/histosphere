<template>
  <!-- Legacy route kept for existing links: /task?sessionId=... -->
  <TaskStudentShell>
    <div class="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-6 text-[var(--admin-copy)] shadow-[var(--admin-shadow-soft)]">
      正在開啟前置任務...
    </div>
  </TaskStudentShell>
</template>

<script setup lang="ts">
import type { EventInitializeResponse } from '~/types';

definePageMeta({
  layout: false,
  name: 'task-gate-legacy',
});

const route = useRoute();
const taskData = useState<EventInitializeResponse | null>('taskData', () => null);

onMounted(async () => {
  const sessionId = typeof route.query.sessionId === 'string' && route.query.sessionId.trim()
    ? route.query.sessionId.trim()
    : taskData.value?.session_id || '';
  if (!sessionId) {
    await navigateTo('/');
    return;
  }

  const participantId = typeof route.query.participantId === 'string' && route.query.participantId.trim()
    ? route.query.participantId.trim()
    : 'scott-test';
  await navigateTo({
    path: `/sessions/${sessionId}/task`,
    query: { participantId },
  }, { replace: true });
});
</script>
