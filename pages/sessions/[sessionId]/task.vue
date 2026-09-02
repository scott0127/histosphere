<template>
  <!-- Session task route: /sessions/[sessionId]/task 是 Error-Elicitation Task 入口。 -->
  <TaskStudentGate
    v-model="answers"
    :task-data="taskData"
    :can-submit="canSubmit"
    :error="submitError"
    :is-loading="isLoading"
    :is-submitting="isSubmitting"
    :judgement="judgement"
    :session="session"
    :activity-mode="activityMode"
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
const authUserId = computed(() => {
  return typeof route.query.authUserId === 'string' && route.query.authUserId.trim()
    ? route.query.authUserId.trim()
    : null;
});

const { activityMode, initAdminMode } = useAdminMode();
onMounted(initAdminMode);

const {
  answers,
  canSubmit,
  isLoading,
  isSubmitting,
  judgement,
  session,
  submitError,
  submitTask,
  taskData,
} = useTaskGate(sessionId, authUserId);
</script>
