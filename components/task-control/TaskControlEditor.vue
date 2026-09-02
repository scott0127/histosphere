<template>
  <TaskControlShell>
    <template #actions>
      <button
        class="admin-button-secondary inline-flex items-center gap-1 px-3 py-2 text-xs font-bold"
        type="button"
        :disabled="saving || !canUndo"
        title="回到上一步"
        aria-label="回到上一步"
        @click="undoTaskEdit"
      >
        <Icon name="mdi:undo-variant" class="h-4 w-4" />
      </button>
      <button
        class="admin-button-secondary inline-flex items-center gap-1 px-3 py-2 text-xs font-bold"
        type="button"
        :disabled="saving || !canRedo"
        title="前往下一步"
        aria-label="前往下一步"
        @click="redoTaskEdit"
      >
        <Icon name="mdi:redo-variant" class="h-4 w-4" />
      </button>
      <button
        class="admin-button-primary inline-flex min-w-28 items-center justify-center gap-2 px-3 py-2 text-xs font-bold"
        :disabled="saving || !dirty || validationIssues.length > 0"
        :title="validationIssues.length ? '請先修正下方檢查問題' : undefined"
        @click="$emit('save')"
      >
        <Icon
          :name="saving ? 'mdi:loading' : dirty ? 'mdi:content-save-outline' : 'mdi:check'"
          class="h-4 w-4"
          :class="{ 'animate-spin': saving }"
        />
        {{ saving ? '儲存中' : dirty ? '儲存任務' : '已儲存' }}
      </button>
    </template>

    <div class="space-y-4" @keydown.capture="handleEditorKeydown">
      <fieldset :disabled="saving || Boolean(payloadError)" class="min-w-0 space-y-4">
      <div class="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(340px,0.85fr)]">
        <section class="admin-editor-block min-w-0 p-4">
          <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <p class="admin-kicker">Authoring mode</p>
              <h4 class="admin-heading mt-1 text-lg font-bold">Error-Elicitation Task 完整題目內容</h4>
            </div>
            <span class="admin-badge">{{ questions.length }} 題</span>
          </div>

          <div class="mt-4 grid gap-3">
            <label class="block">
              <span class="admin-label">任務標題</span>
              <input v-model="task.title" class="admin-field mt-1 w-full px-3 py-2 text-sm font-semibold" />
            </label>

            <div class="admin-composer-toolbar p-3">
              <div>
                <p class="admin-label">新增題目作答區</p>
                <p class="admin-copy mt-1 text-xs font-semibold">{{ selectionSummary }}</p>
              </div>
              <div class="flex flex-wrap gap-2">
                <button class="admin-button-secondary px-3 py-2 text-xs font-bold" type="button" @click="insertInlineQuestion('cloze')">
                  <Icon name="mdi:plus" class="mr-1 h-4 w-4" />填空題
                </button>
                <button class="admin-button-secondary px-3 py-2 text-xs font-bold" type="button" @click="insertInlineQuestion('multiple_choice')">
                  <Icon name="mdi:plus" class="mr-1 h-4 w-4" />選擇題
                </button>
                <button class="admin-button-secondary px-3 py-2 text-xs font-bold" type="button" @click="insertInlineQuestion('true_false')">
                  <Icon name="mdi:plus" class="mr-1 h-4 w-4" />是非題
                </button>
              </div>
            </div>

            <div>
              <div class="flex items-center justify-between gap-3">
                <p class="admin-label">完整題文 *</p>
                <span class="admin-code-badge">{{ inlineQuestionCount }} 個作答標記</span>
              </div>
              <TaskStoryComposer
                v-model="task.error_elicitation_task_full_text"
                class="mt-2"
                :selected-question-id="selectedQuestion?.id || null"
                @selection-change="captureStorySelection"
                @select-question="selectQuestion"
              />
            </div>
          </div>
        </section>

        <aside class="admin-editor-block min-w-0 p-4">
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="admin-kicker">Question list</p>
              <h4 class="admin-heading mt-1 text-lg font-bold">題目清單</h4>
            </div>
            <span class="admin-code-badge">{{ questions.length }} 題</span>
          </div>

          <div class="mt-4 space-y-2">
            <article
              v-for="item in labeledQuestions"
              :key="item.question.id"
              :class="[
                'admin-question-row flex-wrap p-3',
                selectedQuestion?.id === item.question.id ? 'admin-question-row-active' : 'admin-question-row-idle'
              ]"
            >
              <button class="min-w-0 basis-full rounded-[8px] bg-transparent text-left outline-none" type="button" @click="selectQuestion(item.question.id)">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="admin-caption text-xs font-bold">{{ item.label }} / {{ questionTypeLabel(item.question.type) }}</p>
                    <h5 class="admin-heading mt-1 line-clamp-2 break-words text-sm font-bold">{{ taskQuestionExcerpt(task.error_elicitation_task_full_text, item.question.id) || '尚無對應題文' }}</h5>
                  </div>
                  <span :class="['admin-status-chip', questionInserted(item.question) ? 'admin-status-chip-ok' : 'admin-status-chip-warning']">
                    {{ questionStatusLabel(item.question) }}
                  </span>
                </div>
                <div class="mt-2 grid gap-2 text-xs md:grid-cols-2">
                  <div class="admin-answer-cell">
                    <span class="shrink-0">答案</span>
                    <strong class="line-clamp-2 min-w-0 break-words" :title="answerText(item.question)">{{ answerText(item.question) }}</strong>
                  </div>
                  <div class="admin-answer-cell">
                    <span>固定 ID</span>
                    <strong>{{ item.question.id }}</strong>
                  </div>
                </div>
              </button>
              <div class="flex shrink-0 gap-1">
                <button class="admin-button-secondary flex h-8 w-8 items-center justify-center" type="button" :disabled="!canMoveQuestion(item.question.id, -1)" title="上移題文段落與作答標記（題目須各自成段）" :aria-label="`上移 ${item.label}`" @click="moveQuestion(item.question.id, -1)"><Icon name="mdi:arrow-up" class="h-4 w-4" /></button>
                <button class="admin-button-secondary flex h-8 w-8 items-center justify-center" type="button" :disabled="!canMoveQuestion(item.question.id, 1)" title="下移題文段落與作答標記（題目須各自成段）" :aria-label="`下移 ${item.label}`" @click="moveQuestion(item.question.id, 1)"><Icon name="mdi:arrow-down" class="h-4 w-4" /></button>
                <button class="admin-button-danger flex h-8 w-8 items-center justify-center" type="button" title="刪除題目與標記，保留題文" :aria-label="`刪除 ${item.label}`" @click.stop="deleteQuestion(item.question.id)"><Icon name="mdi:trash-can-outline" class="h-4 w-4" /></button>
              </div>
            </article>

            <div v-if="!questions.length" class="admin-empty-state p-4">
              尚未建立題目。
            </div>
          </div>

          <section v-if="selectedQuestion" class="mt-4 border-t border-[var(--admin-border)] pt-4">
            <div class="mb-3 flex items-center justify-between gap-3">
              <div>
                <p class="admin-kicker">Inspector</p>
                <h5 class="admin-heading mt-1 text-base font-bold">{{ selectedQuestionLabel }}</h5>
              </div>
              <span class="admin-code-badge">{{ selectedQuestion.id }}</span>
            </div>
            <TaskControlItemEditor
              :question="selectedQuestion"
              @update="updateQuestion"
            />
            <button v-if="!questionInserted(selectedQuestion)" type="button" class="admin-button-secondary mt-3 px-3 py-2 text-xs font-bold" @click="insertExistingMarker(selectedQuestion.id)">補上作答標記</button>
          </section>
        </aside>
      </div>

      <div class="space-y-3">
        <TaskMaterialsEditor :model-value="materials" @update:model-value="updateMaterials" />
        <TaskAllCorrectFallbackEditor
          :model-value="allCorrectFallback"
          @update:model-value="updateAllCorrectFallback"
        />

        <TaskAnswerKeyPreview :task="task" :questions="questions" />
      </div>
      </fieldset>

      <TaskControlValidation :issues="validationIssues" />

        <details class="admin-subpanel p-3">
          <summary class="admin-label cursor-pointer">進階：題目判斷 JSON</summary>
          <textarea
            :value="evaluationJson"
            rows="8"
            class="admin-textarea admin-code-editor mt-2 w-full px-3 py-2 font-mono text-xs leading-5"
            :disabled="saving"
            @input="updateEvaluationJson"
          />
        </details>

        <details class="admin-subpanel p-3">
          <summary class="admin-label cursor-pointer">進階：學生端互動預覽</summary>
          <TaskControlPreview class="mt-2" :task="task" :evaluation-json="evaluationJson" />
        </details>
    </div>
  </TaskControlShell>
</template>

<script setup lang="ts">
// TaskControlEditor 是研究者/老師端 task 編輯入口。
// 它以 error_elicitation_task_full_text 為主要編輯面，並同步維護 evaluation_payload.questions。
import { computed, nextTick, ref, watch } from 'vue';
import type { EventTask, TaskAllCorrectFallback, TaskMaterial, TaskQuestion, TaskQuestionType } from '~/types';
import TaskAllCorrectFallbackEditor from '~/components/task-control/TaskAllCorrectFallbackEditor.vue';
import TaskAnswerKeyPreview from '~/components/task-control/TaskAnswerKeyPreview.vue';
import TaskControlItemEditor from '~/components/task-control/TaskControlItemEditor.vue';
import TaskControlPreview from '~/components/task-control/TaskControlPreview.vue';
import TaskControlShell from '~/components/task-control/TaskControlShell.vue';
import TaskControlValidation from '~/components/task-control/TaskControlValidation.vue';
import TaskStoryComposer from '~/components/task-control/TaskStoryComposer.vue';
import TaskMaterialsEditor from '~/components/task-control/TaskMaterialsEditor.vue';
import {
  appendTaskHistoryEntry,
  blankIdsInDisplayText,
  createTaskQuestion,
  insertQuestionToken,
  nextTaskQuestionIndex,
  moveTaskControlQuestion,
  parseTaskEvaluationJson,
  questionInsertedInStory,
  removeQuestionAndToken,
  renumberQuestionLabels,
  taskAllCorrectFallback,
  taskControlQuestions,
  taskControlMaterials,
  taskQuestionExcerpt,
  syncTaskQuestionOrder,
  updateTaskAllCorrectFallback,
  updateTaskControlQuestion,
  updateTaskMaterials,
  validateTaskControlPayload,
  type TaskEditorHistoryEntry,
} from '~/composables/useTaskControl';

const props = defineProps<{
  task: EventTask;
  evaluationJson: string;
  dirty?: boolean;
  saving?: boolean;
}>();

const emit = defineEmits<{
  (event: 'update:evaluationJson', value: string): void;
  (event: 'save'): void;
}>();

const selectedQuestionId = ref<string | null>(null);
const storySelection = ref({
  start: props.task.error_elicitation_task_full_text?.length || 0,
  end: props.task.error_elicitation_task_full_text?.length || 0,
});
const isRestoringHistory = ref(false);
const historyIndex = ref(-1);

const historyEntries = ref<TaskEditorHistoryEntry[]>([]);

const questions = computed(() => taskControlQuestions(props.task, props.evaluationJson));
const payloadError = computed(() => parseTaskEvaluationJson(props.evaluationJson).error);
const materials = computed(() => taskControlMaterials(props.evaluationJson));
const allCorrectFallback = computed(() => taskAllCorrectFallback(props.evaluationJson));
const labeledQuestions = computed(() => renumberQuestionLabels(questions.value));
const validationIssues = computed(() => validateTaskControlPayload(props.task, props.evaluationJson));
const selectedQuestion = computed(() => {
  return questions.value.find((question) => question.id === selectedQuestionId.value) || questions.value[0] || null;
});
const selectedQuestionLabel = computed(() => {
  const item = labeledQuestions.value.find((entry) => entry.question.id === selectedQuestion.value?.id);
  return item?.label || '未選取題目';
});
const inlineQuestionCount = computed(() => {
  const blankIds = blankIdsInDisplayText(props.task.error_elicitation_task_full_text || '');
  return questions.value.filter((question) => blankIds.filter((id) => id === question.id).length === 1).length;
});
const selectedText = computed(() => {
  const text = props.task.error_elicitation_task_full_text || '';
  return text.slice(storySelection.value.start, storySelection.value.end);
});
const selectionSummary = computed(() => {
  const text = selectedText.value.trim();
  if (!text) {
    return `游標位置：${storySelection.value.end}`;
  }
  return `選取末端：「${text.slice(0, 32)}${text.length > 32 ? '...' : ''}」`;
});
const historySnapshotKey = computed(() => JSON.stringify(createHistoryEntry()));
const canUndo = computed(() => historyIndex.value > 0);
const canRedo = computed(() => historyIndex.value >= 0 && historyIndex.value < historyEntries.value.length - 1);

const questionTypeLabels: Record<TaskQuestion['type'], string> = {
  short_answer: '不支援的舊版題型',
  cloze: '填空題',
  multiple_choice: '選擇題',
  true_false: '是非題',
};

watch(
  questions,
  (nextQuestions) => {
    if (!nextQuestions.length) {
      selectedQuestionId.value = null;
      return;
    }
    if (!selectedQuestionId.value || !nextQuestions.some((question) => question.id === selectedQuestionId.value)) {
      selectedQuestionId.value = nextQuestions[0]?.id || null;
    }
  },
  { immediate: true },
);

watch(
  historySnapshotKey,
  () => {
    pushHistoryEntry();
  },
  { immediate: true, flush: 'post' },
);

watch(
  () => props.task.error_elicitation_task_full_text,
  (fullText) => {
    storySelection.value = clampStorySelection(storySelection.value, fullText || '');
    const ordered = syncTaskQuestionOrder(props.evaluationJson, fullText || '');
    if (ordered !== props.evaluationJson) emit('update:evaluationJson', ordered);
  },
);

watch(
  () => props.task.id,
  () => {
    selectedQuestionId.value = null;
    historyEntries.value = [];
    historyIndex.value = -1;
    storySelection.value = { start: props.task.error_elicitation_task_full_text?.length || 0, end: props.task.error_elicitation_task_full_text?.length || 0 };
    pushHistoryEntry();
  },
);

const questionTypeLabel = (type: TaskQuestion['type']) => questionTypeLabels[type] || type;

function createHistoryEntry(): TaskEditorHistoryEntry {
  return {
    title: props.task.title || '',
    fullText: props.task.error_elicitation_task_full_text || '',
    evaluationJson: props.evaluationJson || '',
  };
}

function pushHistoryEntry() {
  if (isRestoringHistory.value) return;
  const result = appendTaskHistoryEntry(
    historyEntries.value,
    historyIndex.value,
    createHistoryEntry(),
  );
  historyEntries.value = result.entries;
  historyIndex.value = result.index;
}

const restoreHistoryEntry = async (entry: TaskEditorHistoryEntry) => {
  isRestoringHistory.value = true;
  props.task.title = entry.title;
  props.task.error_elicitation_task_full_text = entry.fullText;
  emit('update:evaluationJson', entry.evaluationJson);
  storySelection.value = { start: entry.fullText.length, end: entry.fullText.length };
  await nextTick();
  isRestoringHistory.value = false;
};

const undoTaskEdit = async () => {
  if (!canUndo.value) return;
  historyIndex.value -= 1;
  const entry = historyEntries.value[historyIndex.value];
  if (!entry) return;
  await restoreHistoryEntry(entry);
};

const redoTaskEdit = async () => {
  if (!canRedo.value) return;
  historyIndex.value += 1;
  const entry = historyEntries.value[historyIndex.value];
  if (!entry) return;
  await restoreHistoryEntry(entry);
};

const handleEditorKeydown = async (event: KeyboardEvent) => {
  if (!event.ctrlKey && !event.metaKey) return;
  const key = event.key.toLowerCase();
  if (props.saving || !['z', 'y'].includes(key)) return;
  // Commit an inspector draft before applying the shared task history.
  event.preventDefault();
  const target = event.target as HTMLElement;
  target.blur();
  await nextTick();
  if (key === 'z' && !event.shiftKey) {
    await undoTaskEdit();
    target.focus();
    return;
  }
  if (key === 'y' || (key === 'z' && event.shiftKey)) {
    await redoTaskEdit();
    target.focus();
  }
};

const answerText = (question: TaskQuestion) => {
  const value = question.correct_answer;
  if (value === undefined || value === null || value === '') {
    return '尚未設定';
  }
  if (question.type === 'multiple_choice') {
    const values = Array.isArray(value) ? value : [value];
    return values.map((item) => question.options?.find((option) => option.value === item)?.label || String(item)).join(' / ');
  }
  if (typeof value === 'boolean') {
    return value ? '是' : '否';
  }
  if (Array.isArray(value)) {
    return value.join(' / ');
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
};

type StorySelection = {
  start: number;
  end: number;
};

const clampStorySelection = (selection: StorySelection, displayText = props.task.error_elicitation_task_full_text || '') => {
  const length = displayText.length;
  const start = Math.max(0, Math.min(selection.start, length));
  const end = Math.max(start, Math.min(selection.end, length));
  return { start, end };
};

const captureStorySelection = (selection: StorySelection) => {
  storySelection.value = clampStorySelection(selection);
};

const selectQuestion = (questionId: string) => {
  selectedQuestionId.value = questionId;
};

const questionInserted = (question: TaskQuestion) => {
  return questionInsertedInStory(props.task.error_elicitation_task_full_text || '', question);
};

const questionStatusLabel = (question: TaskQuestion) => {
  if (questionInserted(question)) return '文中';
  return '未插入';
};

const insertInlineQuestion = (type: Extract<TaskQuestionType, 'cloze' | 'multiple_choice' | 'true_false'>) => {
  const currentText = props.task.error_elicitation_task_full_text || '';
  const selection = clampStorySelection(storySelection.value, currentText);
  const question = createTaskQuestion(type, '', nextTaskQuestionIndex(props.evaluationJson, currentText));
  const result = insertQuestionToken(currentText, question.id, selection.start, selection.end);
  props.task.error_elicitation_task_full_text = result.fullText;
  emit('update:evaluationJson', updateTaskControlQuestion(props.task, props.evaluationJson, question));
  selectedQuestionId.value = question.id;
  storySelection.value = { start: result.cursorPosition, end: result.cursorPosition };
};

const updateQuestion = (question: TaskQuestion) => {
  emit('update:evaluationJson', updateTaskControlQuestion(props.task, props.evaluationJson, question));
  selectedQuestionId.value = question.id;
};

const deleteQuestion = (questionId: string) => {
  const result = removeQuestionAndToken(props.evaluationJson, props.task.error_elicitation_task_full_text || '', questionId);
  props.task.error_elicitation_task_full_text = result.fullText;
  emit('update:evaluationJson', result.evaluationJson);
  if (selectedQuestionId.value === questionId) {
    selectedQuestionId.value = questions.value.find((question) => question.id !== questionId)?.id || null;
  }
};

const updateEvaluationJson = (event: Event) => {
  emit('update:evaluationJson', (event.target as HTMLTextAreaElement).value);
};

const updateAllCorrectFallback = (fallback: TaskAllCorrectFallback | null) => {
  emit('update:evaluationJson', updateTaskAllCorrectFallback(props.evaluationJson, fallback));
};

const updateMaterials = (value: TaskMaterial[]) => {
  emit('update:evaluationJson', updateTaskMaterials(props.evaluationJson, value));
};

const canMoveQuestion = (questionId: string, direction: -1 | 1) => {
  return !payloadError.value && moveTaskControlQuestion(props.evaluationJson, props.task.error_elicitation_task_full_text || '', questionId, direction).moved;
};

const moveQuestion = (questionId: string, direction: -1 | 1) => {
  const result = moveTaskControlQuestion(props.evaluationJson, props.task.error_elicitation_task_full_text || '', questionId, direction);
  if (!result.moved) return;
  props.task.error_elicitation_task_full_text = result.fullText;
  emit('update:evaluationJson', result.evaluationJson);
};

const insertExistingMarker = (questionId: string) => {
  const result = insertQuestionToken(props.task.error_elicitation_task_full_text || '', questionId, storySelection.value.start, storySelection.value.end);
  props.task.error_elicitation_task_full_text = result.fullText;
  storySelection.value = { start: result.cursorPosition, end: result.cursorPosition };
};
</script>
