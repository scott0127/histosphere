<template>
  <!-- Session task route: /sessions/[sessionId]/task 是正式前置任務入口。 -->
  <TaskStudentGate
    v-model="answers"
    :task-data="taskData"
    :can-submit="canSubmit"
    :error="submitError"
    :is-loading="isLoading"
    :is-submitting="isSubmitting"
    :judgement="judgement"
    @submit="submitTask"
  />
</template>

<script setup lang="ts">
definePageMeta({
  layout: false,
  name: 'session-task',
  validate: async (route) => typeof route.params.sessionId === 'string' && route.params.sessionId.length > 0,
});

const route = useRoute();
const sessionId = computed(() => route.params.sessionId as string);
const participantId = computed(() => {
  return typeof route.query.participantId === 'string' && route.query.participantId.trim()
    ? route.query.participantId.trim()
    : 'scott-test';
});
const authUserId = computed(() => {
  return typeof route.query.authUserId === 'string' && route.query.authUserId.trim()
    ? route.query.authUserId.trim()
    : null;
});

const {
  answers,
  canSubmit,
  isLoading,
  isSubmitting,
  judgement,
  submitError,
  submitTask,
  taskData,
} = useTaskGate(sessionId, participantId, authUserId);
</script>
