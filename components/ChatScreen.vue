<template>
  <!--
    ChatScreen 是純 UI 元件：不直接呼叫 API，只透過 emit 把送出訊息交給 conversation route。
    它同時支援 generic chatbot 與 historical persona role-play，
    由 condition.roleplay_enabled 決定是否顯示 persona selector 與人物側欄。
  -->
  <div class="flex h-screen min-h-0 flex-col bg-[var(--admin-page)] font-sans text-[var(--admin-text)]">
    <header class="shrink-0 border-b border-[var(--admin-border)] bg-[rgba(255,253,248,0.9)] backdrop-blur-xl">
      <div class="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2 text-xs font-semibold text-[var(--admin-soft)]">
            <span>{{ activityTitle }}</span>
          </div>
          <h1 class="mt-1 truncate text-xl font-semibold text-[var(--admin-text)] md:text-2xl">
            {{ event?.canonical_name || '載入中' }}
          </h1>
        </div>

        <button
          class="inline-flex items-center justify-center gap-2 rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] px-3 py-2 text-sm font-semibold text-[var(--admin-coffee)] transition hover:bg-[var(--admin-coffee-soft)]"
          @click="showExitConfirmDialog = true"
        >
          <Icon name="mdi:library-outline" class="h-5 w-5" />
          事件素材庫
        </button>
      </div>
    </header>

    <main class="mx-auto grid min-h-0 w-full max-w-6xl flex-1 gap-4 px-5 py-4 lg:grid-cols-[minmax(0,1fr)_280px]">
      <section class="flex min-h-0 flex-col rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] shadow-[var(--admin-shadow-soft)]">
        <TaskAttemptReview
          v-if="task && taskAttempt"
          :task="task"
          :attempt="taskAttempt"
        />
        <div ref="chatContainerRef" class="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
          <!-- message.speaker_type 是新版 message contract 的核心欄位，用來區分 learner/persona/assistant。 -->
          <div
            v-for="(message, index) in history"
            :key="message.id || index"
            :class="[
              'flex',
              message.speaker_type === 'learner' ? 'justify-end' : 'justify-start'
            ]"
          >
            <div
              :class="[
                'max-w-[86%] rounded-lg border px-4 py-3 shadow-sm',
                message.speaker_type === 'learner'
                  ? 'border-[var(--admin-coffee)] bg-[var(--admin-coffee)] text-[var(--admin-surface)]'
                  : 'border-[var(--admin-border)] bg-[var(--admin-surface)] text-[var(--admin-text)]'
              ]"
            >
              <div
                v-if="message.speaker_type !== 'learner'"
                class="mb-2 flex items-center gap-2 border-b border-[var(--admin-border-soft)] pb-2 text-xs font-semibold text-[var(--admin-soft)]"
              >
                <Icon :name="message.speaker_type === 'persona' ? 'mdi:account-voice' : 'mdi:school-outline'" class="h-4 w-4" />
                {{ message.speaker_name }}
              </div>

              <div class="text-sm leading-7 md:text-base">
                <div v-if="message.content === '...'" class="flex items-center gap-2 text-[var(--admin-soft)]">
                  <Icon name="mdi:loading" class="h-5 w-5 animate-spin" />
                  回應生成中
                </div>
                <Typewriter
                  v-else-if="message.speaker_type !== 'learner' && index === history.length - 1"
                  :text="message.content"
                  :annotations="message.annotations"
                />
                <AnnotatedText
                  v-else-if="message.annotations && message.annotations.length > 0"
                  :content="message.content"
                  :annotations="message.annotations"
                />
                <p v-else class="whitespace-pre-wrap">{{ message.content }}</p>
              </div>
            </div>
          </div>
          <div ref="chatEndRef" />
        </div>

        <footer class="shrink-0 border-t border-[var(--admin-border-soft)] p-4">
          <!-- role-play 條件才顯示人物選擇；非 role-play 條件維持一般 AI assistant 對話。 -->
          <div v-if="condition?.roleplay_enabled" class="mb-3 flex gap-2 overflow-x-auto pb-1">
            <button
              type="button"
              :class="selectorClass(selectedPersonaId === null)"
              @click="selectedPersonaId = null"
            >
              主要人物
            </button>
            <button
              v-for="persona in personas"
              :key="persona.id"
              type="button"
              :class="selectorClass(selectedPersonaId === persona.id)"
              @click="selectedPersonaId = persona.id"
            >
              {{ persona.name }}
            </button>
          </div>

          <form class="flex items-end gap-2" @submit.prevent="handleSendMessage">
            <textarea
              v-model="userInput"
              rows="1"
              :placeholder="inputPlaceholder"
              class="max-h-36 min-h-12 flex-1 resize-y rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] px-4 py-3 text-sm leading-6 text-[var(--admin-text)] outline-none transition focus:border-[var(--admin-coffee-muted)] focus:ring-4 focus:ring-[var(--admin-focus)]"
              :disabled="isReplying"
            />
            <button
              type="submit"
              :disabled="isReplying || !userInput.trim()"
              class="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-[var(--admin-coffee)] text-[var(--admin-surface)] transition hover:bg-[var(--admin-coffee-hover)] disabled:cursor-not-allowed disabled:bg-[var(--admin-border)]"
            >
              <Icon name="mdi:send" class="h-5 w-5" />
            </button>
          </form>
        </footer>
      </section>

      <aside class="hidden min-h-0 space-y-4 lg:block">
        <!-- persona 摘要只在 role-play 條件出現；作答結果統一顯示於聊天主區。 -->
        <div v-if="condition?.roleplay_enabled" class="rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] p-4 shadow-[var(--admin-shadow-soft)]">
          <h2 class="text-sm font-semibold text-[var(--admin-text)]">歷史人物</h2>
          <div class="mt-3 space-y-3">
            <div v-for="persona in personas" :key="persona.id" class="rounded-lg border border-[var(--admin-border-soft)] bg-[var(--admin-surface-muted)] p-3">
              <p class="font-semibold text-[var(--admin-text)]">{{ persona.name }}</p>
              <p class="mt-1 text-sm text-[var(--admin-soft)]">{{ persona.role || '角色資料待補' }}</p>
              <p class="mt-2 line-clamp-3 text-xs leading-5 text-[var(--admin-copy)]">{{ persona.biography }}</p>
            </div>
          </div>
        </div>

        <div v-else class="rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] p-4 shadow-[var(--admin-shadow-soft)]">
          <h2 class="text-sm font-semibold text-[var(--admin-text)]">對話夥伴</h2>
          <p class="mt-2 text-sm leading-6 text-[var(--admin-copy)]">
            你可以針對前置任務與歷史事件提出問題。
          </p>
        </div>
      </aside>
    </main>

    <ConfirmActionModal
      :show="showExitConfirmDialog"
      title="CHAT"
      message="點選「是」返回事件素材庫"
      eyebrow="階段確認"
      icon="mdi:library-outline"
      confirm-label="是"
      cancel-label="否"
      @confirm="confirmExitConversation"
      @cancel="showExitConfirmDialog = false"
    />
  </div>
</template>

<script setup lang="ts">
// ChatScreen 只管理本地輸入框、persona selector 與畫面捲動。
// 對話 state、API error handling、history 替換都在 useConversationSession 處理。
import { computed, nextTick, ref, watch } from 'vue';
import type { ChatMessage, EventTask, ExperimentCondition, HistoricalEvent, Persona, TaskAttempt } from '~/types';
import Typewriter from './Typewriter.vue';
import AnnotatedText from './AnnotatedText.vue';
import ConfirmActionModal from '~/components/modals/ConfirmActionModal.vue';
import TaskAttemptReview from '~/components/task-student/TaskAttemptReview.vue';
import { studentActivityTitle } from '~/composables/useStudentTask';

const props = defineProps<{
  event: HistoricalEvent | null;
  personas: Persona[];
  history: ChatMessage[];
  conversationId: string;
  condition?: ExperimentCondition | null;
  task?: EventTask | null;
  taskAttempt?: TaskAttempt | null;
  dynamicContext: string;
}>();

const emit = defineEmits<{
  (event: 'reset'): void;
  (event: 'send-message', userInput: string, targetPersonaId?: string): void;
}>();

const userInput = ref('');
const selectedPersonaId = ref<string | null>(null);
const chatEndRef = ref<HTMLDivElement | null>(null);
const chatContainerRef = ref<HTMLDivElement | null>(null);
const showExitConfirmDialog = ref(false);

// 最後一則內容為 "..." 時代表後端正在生成回覆，避免連續送出造成 history index 混亂。
const isReplying = computed(() => {
  const lastMessage = props.history[props.history.length - 1];
  return lastMessage?.content === '...';
});

// 學生端只顯示實驗代號，不揭露實際 treatment。
const activityTitle = computed(() => {
  if (!props.condition) return '載入中';
  return studentActivityTitle(props.condition);
});

// role-play 模式會依選定 persona 改變 placeholder，幫助使用者知道目前對話目標。
const inputPlaceholder = computed(() => {
  if (!props.condition?.roleplay_enabled) return '輸入你的問題...';
  if (!selectedPersonaId.value) return '向歷史人物提問...';
  const persona = props.personas.find((item) => item.id === selectedPersonaId.value);
  return `向 ${persona?.name || '歷史人物'} 提問...`;
});

// persona selector 使用同一組 class，避免 active/inactive 視覺規則散在 template 裡。
const selectorClass = (active: boolean) => [
  'whitespace-nowrap rounded-lg border px-3 py-2 text-xs font-semibold transition',
  active
    ? 'border-[var(--admin-coffee-muted)] bg-[var(--admin-coffee-soft)] text-[var(--admin-coffee)]'
    : 'border-[var(--admin-border)] bg-[var(--admin-surface)] text-[var(--admin-copy)] hover:border-[var(--admin-coffee-muted)]',
];

const handleSendMessage = () => {
  const trimmed = userInput.value.trim();
  if (!trimmed || isReplying.value) return;
  emit('send-message', trimmed, selectedPersonaId.value || undefined);
  userInput.value = '';
};

const confirmExitConversation = () => {
  showExitConfirmDialog.value = false;
  emit('reset');
};

// history 改變後自動捲到底，保留聊天室連續閱讀體驗。
watch(
  () => props.history,
  async () => {
    await nextTick();
    chatEndRef.value?.scrollIntoView({ behavior: 'smooth' });
  },
  { deep: true },
);
</script>
