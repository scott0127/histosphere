<template>
  <!--
    ChatScreen 是純 UI 元件：不直接呼叫 API，只透過 emit 把送出訊息交給 conversation route。
    它同時支援 generic chatbot 與 historical persona role-play，
    由 condition.roleplay_enabled 決定是否顯示事件固定人物與人物側欄。
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
      <section class="flex min-h-0 flex-col overflow-hidden rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] shadow-[var(--admin-shadow-soft)]">
        <SessionTimerBanner
          :session="session"
          flush
          @next-stage="$emit('next-stage')"
        />
        <TaskAttemptReview
          v-if="task && taskAttempt"
          :task="task"
          :attempt="taskAttempt"
        />
        <div ref="chatContainerRef" class="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 pb-6 pt-7">
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
                'max-w-[88%] rounded-lg border px-5 py-4 shadow-sm',
                message.speaker_type === 'learner'
                  ? 'border-[var(--admin-coffee)] bg-[var(--admin-coffee)] text-[var(--admin-surface)]'
                  : 'border-[var(--admin-border)] bg-[var(--admin-surface)] text-[var(--admin-text)]'
              ]"
            >
              <div
                v-if="message.speaker_type !== 'learner'"
                class="mb-3 flex items-center gap-2 border-b border-[var(--admin-border-soft)] pb-3 text-xs font-semibold text-[var(--admin-soft)]"
              >
                <span
                  v-if="message.speaker_type === 'persona' && messagePersona(message)?.avatar_url"
                  class="h-7 w-7 shrink-0 overflow-hidden rounded-full border border-[var(--admin-border)]"
                >
                  <img
                    :src="messagePersona(message)?.avatar_url || ''"
                    :alt="`${message.speaker_name} 肖像`"
                    :class="[
                      'h-full w-full object-cover',
                      isMonaPortrait(messagePersona(message)) ? 'origin-[50%_22%] scale-[2.15]' : ''
                    ]"
                  />
                </span>
                <Icon
                  v-else
                  :name="message.speaker_type === 'persona' ? 'mdi:account-voice' : 'mdi:school-outline'"
                  class="h-4 w-4"
                />
                {{ message.speaker_name }}
              </div>

              <div class="text-sm leading-7 md:text-base">
                <div
                  v-if="isPendingMessage(message)"
                  class="flex items-center gap-2 text-[var(--admin-soft)]"
                  role="status"
                  aria-live="polite"
                >
                  <Icon name="mdi:loading" class="h-5 w-5 animate-spin" />
                  {{ replyStatus || '正在回應…' }}
                </div>
                <p
                  v-else-if="isStreamingMessage(message)"
                  class="whitespace-pre-wrap"
                >
                  {{ message.content }}<span aria-hidden="true" class="ml-1 inline-block h-4 w-0.5 animate-pulse bg-current align-middle" />
                </p>
                <Typewriter
                  v-else-if="
                    message.speaker_type !== 'learner'
                    && index === history.length - 1
                    && !wasValidatedStream(message)
                  "
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

        <footer class="shrink-0 border-t border-[var(--admin-border-soft)] p-5">
          <form v-if="!sessionClosed" class="flex items-end gap-2" @submit.prevent="handleSendMessage">
            <textarea
              v-model="userInput"
              rows="1"
              :placeholder="inputPlaceholder"
              class="max-h-36 min-h-12 flex-1 resize-y rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] px-4 py-3 text-sm leading-6 text-[var(--admin-text)] outline-none transition focus:border-[var(--admin-coffee-muted)] focus:ring-4 focus:ring-[var(--admin-focus)]"
              :disabled="isReplying || sessionClosed"
            />
            <button
              type="submit"
              :disabled="isReplying || sessionClosed || !userInput.trim()"
              class="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-[var(--admin-coffee)] text-[var(--admin-surface)] transition hover:bg-[var(--admin-coffee-hover)] disabled:cursor-not-allowed disabled:bg-[var(--admin-border)]"
            >
              <Icon name="mdi:send" class="h-5 w-5" />
            </button>
          </form>
          <p v-else class="text-center text-sm font-semibold text-[var(--admin-soft)]">
            本階段已結束，請使用上方按鈕進入下一階段。
          </p>
        </footer>
      </section>

      <aside class="hidden min-h-0 space-y-4 lg:block">
        <!-- role-play 僅呈現後端鎖定的人物，不提供受測者任何切換控制。 -->
        <div v-if="condition?.roleplay_enabled" class="rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] p-4 shadow-[var(--admin-shadow-soft)]">
          <h2 class="text-sm font-semibold text-[var(--admin-text)]">歷史人物</h2>
          <div v-if="lockedPersona" class="mt-3">
            <div class="overflow-hidden rounded-lg border border-[var(--admin-border-soft)] bg-[var(--admin-surface-muted)]">
              <img
                v-if="lockedPersona.avatar_url"
                :src="lockedPersona.avatar_url"
                :alt="`${lockedPersona.name} 肖像`"
                :class="[
                  'aspect-square w-full object-cover',
                  isMonaPortrait(lockedPersona) ? 'origin-[50%_22%] scale-[2.15]' : ''
                ]"
              />
              <div
                v-else
                class="flex aspect-square w-full items-center justify-center bg-[var(--admin-coffee-soft)] text-4xl font-semibold text-[var(--admin-coffee)]"
              >
                {{ lockedPersona.name.slice(0, 1) }}
              </div>
              <div class="p-3">
                <p class="font-semibold text-[var(--admin-text)]">{{ lockedPersona.name }}</p>
                <p class="mt-1 text-sm text-[var(--admin-soft)]">{{ lockedPersona.role || '角色資料待補' }}</p>
                <p class="mt-2 line-clamp-4 text-xs leading-5 text-[var(--admin-copy)]">{{ lockedPersona.biography }}</p>
              </div>
            </div>
          </div>
          <div v-else class="mt-3 rounded-lg border border-dashed border-[var(--admin-border)] p-3 text-sm text-[var(--admin-soft)]">
            此事件尚未設定可用人物。
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
// ChatScreen 只管理本地輸入框、固定人物呈現與畫面捲動。
// 對話 state、API error handling、history 替換都在 useConversationSession 處理。
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import type { ChatMessage, EventTask, ExperimentCondition, ExperimentSession, HistoricalEvent, Persona, TaskAttempt } from '~/types';
import Typewriter from './Typewriter.vue';
import AnnotatedText from './AnnotatedText.vue';
import ConfirmActionModal from '~/components/modals/ConfirmActionModal.vue';
import TaskAttemptReview from '~/components/task-student/TaskAttemptReview.vue';
import SessionTimerBanner from '~/components/session/SessionTimerBanner.vue';
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
  session?: ExperimentSession | null;
  isReplying: boolean;
  replyStatus?: string;
}>();

const emit = defineEmits<{
  (event: 'reset'): void;
  (event: 'next-stage'): void;
  (event: 'session-expired'): void;
  (event: 'send-message', userInput: string): void;
}>();

const userInput = ref('');
const chatEndRef = ref<HTMLDivElement | null>(null);
const chatContainerRef = ref<HTMLDivElement | null>(null);
const showExitConfirmDialog = ref(false);
const now = ref(Date.now());
let sessionTimerId: ReturnType<typeof setInterval> | null = null;
const expirationReported = ref(false);
const sessionClosed = computed(() => {
  return props.session?.status === 'completed'
    || props.session?.status === 'archived'
    || Boolean(props.session?.timer_ends_at && Date.parse(props.session.timer_ends_at) <= now.value);
});

watch(
  () => props.session?.timer_ends_at,
  () => {
    expirationReported.value = false;
    now.value = Date.now();
  },
);

watch(
  sessionClosed,
  (closed) => {
    if (!closed) {
      expirationReported.value = false;
      return;
    }
    if (
      !expirationReported.value
      && props.session?.timer_ends_at
      && props.session.status !== 'completed'
      && props.session.status !== 'archived'
    ) {
      expirationReported.value = true;
      emit('session-expired');
    }
  },
  { immediate: true },
);

onMounted(() => { sessionTimerId = setInterval(() => { now.value = Date.now(); }, 1000); });
onBeforeUnmount(() => { if (sessionTimerId) clearInterval(sessionTimerId); });

const messageMetadata = (message: ChatMessage) => message.metadata || {};
const isPendingMessage = (message: ChatMessage) => {
  return messageMetadata(message).generation_status === 'pending' && !message.content;
};
const isStreamingMessage = (message: ChatMessage) => {
  return messageMetadata(message).generation_status === 'streaming';
};
const wasValidatedStream = (message: ChatMessage) => {
  return messageMetadata(message).delivery_mode === 'validated_stream';
};

// 學生端只顯示實驗代號，不揭露實際 treatment。
const activityTitle = computed(() => {
  if (!props.condition) return '載入中';
  return studentActivityTitle(props.condition);
});

const lockedPersona = computed(() => {
  const lockedPersonaId = props.history.find((message) => message.persona_id)?.persona_id;
  if (lockedPersonaId) {
    return props.personas.find((persona) => persona.id === lockedPersonaId) || null;
  }
  return props.personas.find((persona) => persona.active && !persona.archived_at)
    || props.personas[0]
    || null;
});

const messagePersona = (message: ChatMessage) => {
  if (!message.persona_id) return lockedPersona.value;
  return props.personas.find((persona) => persona.id === message.persona_id) || lockedPersona.value;
};

// 莫那・魯道的現存照片為三人合影；僅用 CSS 聚焦中央人物，不修改原始史料影像。
const isMonaPortrait = (persona: Persona | null | undefined) => {
  return Boolean(persona?.avatar_url?.includes('/mona-rudao.'));
};

// role-play 模式依事件固定人物調整 placeholder，不提供切換入口。
const inputPlaceholder = computed(() => {
  if (!props.condition?.roleplay_enabled) return '輸入你的問題...';
  return `向 ${lockedPersona.value?.name || '歷史人物'} 提問...`;
});

const handleSendMessage = () => {
  const trimmed = userInput.value.trim();
  if (!trimmed || props.isReplying) return;
  emit('send-message', trimmed);
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
