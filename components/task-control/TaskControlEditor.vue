<template>
  <!-- Story-first task composer：研究員以故事文本為主，將單一題目插入文中。 -->
  <TaskControlShell>
    <template #actions>
      <button
        class="admin-button-secondary inline-flex items-center gap-1 px-3 py-2 text-xs font-bold"
        type="button"
        :disabled="!canUndo"
        title="回到上一步"
        @click="undoTaskEdit"
      >
        <Icon name="mdi:undo-variant" class="h-4 w-4" />
        上一步
      </button>
      <button
        class="admin-button-secondary inline-flex items-center gap-1 px-3 py-2 text-xs font-bold"
        type="button"
        :disabled="!canRedo"
        title="前往下一步"
        @click="redoTaskEdit"
      >
        <Icon name="mdi:redo-variant" class="h-4 w-4" />
        下一步
      </button>
      <button class="admin-button-primary px-3 py-2 text-xs font-bold" @click="$emit('save')">
        儲存任務
      </button>
    </template>

    <div class="space-y-4" @keydown.capture="handleEditorKeydown">
      <div class="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
        <section class="admin-editor-block p-4">
          <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <p class="admin-kicker">Authoring mode</p>
              <h4 class="admin-heading mt-1 text-lg font-bold">出題文本編輯</h4>
              <p class="admin-copy mt-1 text-xs font-semibold leading-5">
                選取文字或把游標放在句中，再插入一個填空、選擇或是非題。
              </p>
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
                <p class="admin-label">插入題目</p>
                <p class="admin-copy mt-1 text-xs font-semibold">{{ selectionSummary }}</p>
              </div>
              <div class="flex flex-wrap gap-2">
                <button class="admin-button-secondary px-3 py-2 text-xs font-bold" type="button" @click="insertInlineQuestion('cloze')">
                  插入填空
                </button>
                <button class="admin-button-secondary px-3 py-2 text-xs font-bold" type="button" @click="insertInlineQuestion('multiple_choice')">
                  插入選擇
                </button>
                <button class="admin-button-secondary px-3 py-2 text-xs font-bold" type="button" @click="insertInlineQuestion('true_false')">
                  插入是非
                </button>
              </div>
            </div>

            <section class="admin-subpanel p-3">
              <div class="flex items-center justify-between gap-3">
                <p class="admin-label">編輯模式</p>
                <span class="admin-code-badge">{{ inlineQuestionCount }} inline</span>
              </div>
              <TaskStoryComposer
                v-model="task.display_text"
                class="mt-2"
                :questions="questions"
                :selected-question-id="selectedQuestion?.id || null"
                @selection-change="captureStorySelection"
                @select-question="selectQuestion"
                @delete-question="deleteQuestion"
              />
            </section>
          </div>
        </section>

        <aside class="admin-editor-block p-4">
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="admin-kicker">Question list</p>
              <h4 class="admin-heading mt-1 text-lg font-bold">題目清單</h4>
            </div>
            <span class="admin-code-badge">{{ inlineQuestionCount }} inline</span>
          </div>

          <div class="mt-4 space-y-2">
            <article
              v-for="item in labeledQuestions"
              :key="item.question.id"
              :class="[
                'admin-question-row p-3',
                selectedQuestion?.id === item.question.id ? 'admin-question-row-active' : 'admin-question-row-idle'
              ]"
            >
              <button class="min-w-0 flex-1 rounded-[8px] bg-transparent text-left outline-none" type="button" @click="selectQuestion(item.question.id)">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="admin-caption text-xs font-bold">{{ item.label }} / {{ questionTypeLabel(item.question.type) }}</p>
                    <h5 class="admin-heading mt-1 truncate text-sm font-bold">{{ item.question.prompt || '尚未輸入題目文字' }}</h5>
                  </div>
                  <span :class="['admin-status-chip', questionInserted(item.question) ? 'admin-status-chip-ok' : 'admin-status-chip-warning']">
                    {{ questionStatusLabel(item.question) }}
                  </span>
                </div>
                <div class="mt-2 grid gap-2 text-xs md:grid-cols-2">
                  <div class="admin-answer-cell">
                    <span>答案</span>
                    <strong>{{ answerText(item.question) }}</strong>
                  </div>
                  <div class="admin-answer-cell">
                    <span>空格</span>
                    <strong>{{ item.question.blank_id || item.question.id }}</strong>
                  </div>
                </div>
              </button>
              <button class="admin-button-danger px-3 py-2 text-xs font-bold" type="button" @click.stop="deleteQuestion(item.question.id)">
                刪除
              </button>
            </article>

            <div v-if="!questions.length" class="admin-empty-state p-4">
              尚未建立題目。請在故事中選取文字後插入題目。
            </div>
          </div>

          <section v-if="selectedQuestion" class="admin-inspector-panel mt-4 p-3">
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
              @remove="deleteQuestion"
            />
          </section>
        </aside>
      </div>

      <div class="space-y-3">
        <TaskControlValidation :issues="validationIssues" />

        <TaskAnswerKeyPreview :task="task" :questions="questions" />

        <details class="admin-subpanel p-3">
          <summary class="admin-label cursor-pointer">進階：題目判斷 JSON</summary>
          <textarea
            :value="evaluationJson"
            rows="8"
            class="admin-textarea admin-code-editor mt-2 w-full px-3 py-2 font-mono text-xs leading-5"
            @input="updateEvaluationJson"
          />
        </details>

        <details class="admin-subpanel p-3">
          <summary class="admin-label cursor-pointer">進階：學生端互動預覽</summary>
          <TaskControlPreview class="mt-2" :task="task" :evaluation-json="evaluationJson" />
        </details>
      </div>
    </div>
  </TaskControlShell>
</template>

<script setup lang="ts">
// TaskControlEditor 是研究者/老師端 task 編輯入口。
// 它以 display_text 為主要編輯面，並同步維護 evaluation_payload.questions。
import { computed, nextTick, ref, watch } from 'vue';
import type { EventTask, TaskQuestion, TaskQuestionType } from '~/types';
import TaskAnswerKeyPreview from '~/components/task-control/TaskAnswerKeyPreview.vue';
import TaskControlItemEditor from '~/components/task-control/TaskControlItemEditor.vue';
import TaskControlPreview from '~/components/task-control/TaskControlPreview.vue';
import TaskControlShell from '~/components/task-control/TaskControlShell.vue';
import TaskControlValidation from '~/components/task-control/TaskControlValidation.vue';
import TaskStoryComposer from '~/components/task-control/TaskStoryComposer.vue';
import {
  blankIdsInDisplayText,
  createTaskQuestion,
  insertQuestionToken,
  nextTaskQuestionIndex,
  questionInsertedInStory,
  removeQuestionAndToken,
  renumberQuestionLabels,
  taskControlQuestions,
  updateTaskControlQuestion,
  validateTaskControlPayload,
} from '~/composables/useTaskControl';

const props = defineProps<{
  task: EventTask;
  evaluationJson: string;
}>();

const emit = defineEmits<{
  (event: 'update:evaluationJson', value: string): void;
  (event: 'save'): void;
}>();

const selectedQuestionId = ref<string | null>(null);
const storySelection = ref({
  start: props.task.display_text?.length || 0,
  end: props.task.display_text?.length || 0,
});
const isRestoringHistory = ref(false);
const historyIndex = ref(-1);

type TaskEditorHistoryEntry = {
  title: string;
  displayText: string;
  storyText: string;
  evaluationJson: string;
};

const historyEntries = ref<TaskEditorHistoryEntry[]>([]);

const questions = computed(() => taskControlQuestions(props.task, props.evaluationJson));
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
  const blankIds = blankIdsInDisplayText(props.task.display_text || '');
  return questions.value.filter((question) => blankIds.includes(question.blank_id || question.id)).length;
});
const selectedText = computed(() => {
  const text = props.task.display_text || '';
  return text.slice(storySelection.value.start, storySelection.value.end);
});
const selectionSummary = computed(() => {
  const text = selectedText.value.trim();
  if (!text) {
    return '目前會插入在游標位置。';
  }
  return `目前選取：「${text.slice(0, 32)}${text.length > 32 ? '...' : ''}」`;
});
const historySnapshotKey = computed(() => JSON.stringify(createHistoryEntry()));
const canUndo = computed(() => historyIndex.value > 0);
const canRedo = computed(() => historyIndex.value >= 0 && historyIndex.value < historyEntries.value.length - 1);

const questionTypeLabels: Record<TaskQuestion['type'], string> = {
  short_answer: '簡答題',
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
  { immediate: true },
);

watch(
  () => props.task.display_text,
  (displayText) => {
    storySelection.value = clampStorySelection(storySelection.value, displayText || '');
  },
);

const questionTypeLabel = (type: TaskQuestion['type']) => questionTypeLabels[type] || type;

function createHistoryEntry(): TaskEditorHistoryEntry {
  return {
    title: props.task.title || '',
    displayText: props.task.display_text || '',
    storyText: props.task.story_text || '',
    evaluationJson: props.evaluationJson || '',
  };
}

function sameHistoryEntry(a: TaskEditorHistoryEntry | undefined, b: TaskEditorHistoryEntry) {
  return !!a
    && a.title === b.title
    && a.displayText === b.displayText
    && a.storyText === b.storyText
    && a.evaluationJson === b.evaluationJson;
}

function pushHistoryEntry() {
  if (isRestoringHistory.value) return;
  const nextEntry = createHistoryEntry();
  if (sameHistoryEntry(historyEntries.value[historyIndex.value], nextEntry)) return;

  const nextHistory = historyEntries.value.slice(0, historyIndex.value + 1);
  nextHistory.push(nextEntry);

  if (nextHistory.length > 80) {
    nextHistory.shift();
  }

  historyEntries.value = nextHistory;
  historyIndex.value = nextHistory.length - 1;
}

const restoreHistoryEntry = async (entry: TaskEditorHistoryEntry) => {
  isRestoringHistory.value = true;
  props.task.title = entry.title;
  props.task.display_text = entry.displayText;
  props.task.story_text = entry.storyText;
  emit('update:evaluationJson', entry.evaluationJson);
  storySelection.value = { start: entry.displayText.length, end: entry.displayText.length };
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

const handleEditorKeydown = (event: KeyboardEvent) => {
  if (!event.ctrlKey && !event.metaKey) return;
  const key = event.key.toLowerCase();
  if (key === 'z' && !event.shiftKey) {
    event.preventDefault();
    void undoTaskEdit();
    return;
  }
  if (key === 'y' || (key === 'z' && event.shiftKey)) {
    event.preventDefault();
    void redoTaskEdit();
  }
};

const answerText = (question: TaskQuestion) => {
  const value = question.correct_answer;
  if (value === undefined || value === null || value === '') {
    return '尚未設定';
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

const clampStorySelection = (selection: StorySelection, displayText = props.task.display_text || '') => {
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
  return questionInsertedInStory(props.task.display_text || '', question);
};

const questionStatusLabel = (question: TaskQuestion) => {
  if (questionInserted(question)) return '文中';
  if (question.type === 'short_answer') return '文後';
  return '未插入';
};

const insertInlineQuestion = (type: Extract<TaskQuestionType, 'cloze' | 'multiple_choice' | 'true_false'>) => {
  const currentText = props.task.display_text || '';
  const selection = clampStorySelection(storySelection.value, currentText);
  const selected = currentText.slice(selection.start, selection.end);
  const question = createTaskQuestion(type, selected, nextTaskQuestionIndex(props.evaluationJson));
  const result = insertQuestionToken(currentText, question.id, selection.start, selection.end);
  props.task.display_text = result.displayText;
  emit('update:evaluationJson', updateTaskControlQuestion(props.task, props.evaluationJson, question));
  selectedQuestionId.value = question.id;
  storySelection.value = { start: result.cursorPosition, end: result.cursorPosition };
};

const updateQuestion = (question: TaskQuestion) => {
  emit('update:evaluationJson', updateTaskControlQuestion(props.task, props.evaluationJson, question));
  selectedQuestionId.value = question.id;
};

const deleteQuestion = (questionId: string) => {
  const result = removeQuestionAndToken(props.evaluationJson, props.task.display_text || '', questionId);
  props.task.display_text = result.displayText;
  emit('update:evaluationJson', result.evaluationJson);
  if (selectedQuestionId.value === questionId) {
    selectedQuestionId.value = questions.value.find((question) => question.id !== questionId)?.id || null;
  }
};

const updateEvaluationJson = (event: Event) => {
  emit('update:evaluationJson', (event.target as HTMLTextAreaElement).value);
};
</script>
