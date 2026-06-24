<template>
  <!-- 研究者預覽學生端會看到的作答元件。 -->
  <div class="admin-subpanel p-3">
    <div class="mb-3 flex items-center justify-between">
      <p class="admin-heading text-sm font-bold">學生端預覽</p>
      <span class="admin-badge">預覽</span>
    </div>
    <TaskStudentStory v-model="previewAnswers" :task="previewTask" />
    <TaskStudentRenderer v-if="!hasInlineTaskBlanks(previewTask)" v-model="previewAnswers" class="mt-3" :task="previewTask" />
  </div>
</template>

<script setup lang="ts">
// TaskControlPreview 使用學生端 renderer，確保編輯端看到的預覽與學生端一致。
import { computed, ref } from 'vue';
import type { EventTask, TaskEvaluationPayload, TaskStudentAnswer } from '~/types';
import { parseTaskEvaluationJson } from '~/composables/useTaskControl';
import { hasInlineTaskBlanks } from '~/composables/useStudentTask';

const props = defineProps<{
  task: EventTask;
  evaluationJson: string;
}>();

const previewAnswers = ref<TaskStudentAnswer[]>([]);

const previewTask = computed(() => {
  const { payload } = parseTaskEvaluationJson(props.evaluationJson);
  return {
    ...props.task,
    evaluation_payload: payload as TaskEvaluationPayload,
  };
});
</script>
