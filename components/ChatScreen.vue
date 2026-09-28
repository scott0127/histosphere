<template>
  <!--
    ChatScreen 是純 UI 元件：不直接呼叫 API，只透過 emit 把送出訊息交給 conversation route。
    它同時支援 generic chatbot 與 historical persona role-play，
    由 condition.roleplay_enabled 決定是否顯示事件固定人物。
  -->
  <div class="chat-workspace flex h-dvh min-h-0 flex-col bg-[var(--admin-page)] font-sans text-[var(--admin-text)]">
    <header class="chat-topbar shrink-0 border-b border-[var(--admin-border)] bg-[rgba(255,253,248,0.9)] backdrop-blur-xl">
      <div class="mx-auto flex max-w-[1600px] items-center justify-between gap-3 px-4 py-3">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2 text-xs font-semibold text-[var(--admin-soft)]">
            <span>{{ activityTitle }}</span>
          </div>
          <h1 class="mt-1 truncate text-xl font-semibold text-[var(--admin-text)] md:text-2xl">
            {{ event?.canonical_name || '載入中' }}
          </h1>
        </div>

        <button
          type="button"
          title="事件素材庫"
          class="chat-secondary-button inline-flex items-center justify-center gap-2 rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] px-3 py-2 text-sm font-semibold text-[var(--admin-coffee)] transition hover:bg-[var(--admin-coffee-soft)]"
          @click="showExitConfirmDialog = true"
        >
          <Icon name="mdi:library-outline" class="h-5 w-5" />
          <span class="sr-only md:not-sr-only">事件素材庫</span>
        </button>
      </div>
    </header>

    <main class="chat-main mx-auto flex min-h-0 w-full max-w-[1600px] flex-1 gap-4 px-3 py-3 md:px-4">
      <section class="flex min-h-0 min-w-0 flex-1 flex-col gap-3">
        <div class="chat-timer-shell shrink-0 overflow-hidden rounded-lg border border-[var(--admin-border)]">
        <SessionTimerBanner
          :session="session"
          flush
          @next-stage="$emit('next-stage')"
        />
        </div>
        <StudySplitView>
          <template #task>
            <TaskAttemptReview v-if="task && taskAttempt" :task="task" :attempt="taskAttempt" :history="history"
              :learning-focus="learningFocus" />
            <p v-else class="p-5 text-sm text-[var(--admin-soft)]">目前沒有作答紀錄。</p>
          </template>
        <div class="chat-conversation-heading flex shrink-0 items-center gap-3 border-b border-[var(--admin-border-soft)] px-3 py-2 md:px-5 md:py-4">
          <PersonaAvatar v-if="condition?.roleplay_enabled" :src="lockedPersona?.avatar_url"
            :alt="`${lockedPersona?.name || '歷史人物'} 肖像`" class="h-12 w-12 rounded-md md:h-16 md:w-16" />
          <span v-else class="chat-assistant-mark" aria-hidden="true"><Icon name="mdi:message-text" class="h-5 w-5" /></span>
          <div class="min-w-0">
            <h2 class="text-base font-semibold text-[var(--admin-text)]">{{ condition?.roleplay_enabled ? `與 ${lockedPersona?.name || '歷史人物'} 對話` : '與 AI 對話' }}</h2>
            <p v-if="condition?.roleplay_enabled && lockedPersona?.role" class="mt-1 break-words text-xs text-[var(--admin-soft)]">{{ lockedPersona.role }}</p>
          </div>
        </div>
        <TaskProgressNotice v-if="task" :task="task" :history="history" :learning-focus="learningFocus" />
        <div class="relative flex min-h-0 flex-1 flex-col">
        <div ref="chatContainerRef" class="chat-message-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pb-6 pt-7" @scroll.passive="onChatScroll">
          <div ref="chatContentRef" class="space-y-5">
          <!-- message.speaker_type 是新版 message contract 的核心欄位，用來區分 learner/persona/assistant。 -->
          <div
            v-for="(message, index) in history"
            :key="message.id || index"
            :data-message-id="message.id"
            tabindex="-1"
            :class="[
              'flex focus:outline-none',
              message.speaker_type === 'learner' ? 'justify-end' : 'justify-start'
            ]"
          >
            <div
              :class="[
                'chat-message max-w-[94%] min-w-0 break-words rounded-lg border px-4 py-4 shadow-sm md:max-w-[92%]',
                message.speaker_type === 'learner' ? 'chat-message-learner' : 'chat-message-assistant',
                highlightedMessageId === message.id ? 'ring-2 ring-[var(--admin-coffee)] ring-offset-2' : '',
                message.speaker_type === 'learner'
                  ? 'border-[var(--admin-coffee)] bg-[var(--admin-coffee)] text-[var(--admin-surface)]'
                  : 'border-[var(--admin-border)] bg-[var(--admin-surface)] text-[var(--admin-text)]'
              ]"
            >
              <div
                v-if="message.speaker_type !== 'learner'"
                class="chat-message-author mb-3 flex items-center gap-2 border-b border-[var(--admin-border-soft)] pb-3 text-xs font-semibold text-[var(--admin-soft)]"
              >
                <PersonaAvatar v-if="message.speaker_type === 'persona'" :src="messagePersona(message)?.avatar_url"
                  :alt="`${message.speaker_name} 肖像`" class="h-9 w-9 rounded-full" />
                <Icon
                  v-else
                  :name="message.metadata?.system_fallback ? 'mdi:information-outline' : (message.speaker_type === 'persona' ? 'mdi:account-voice' : 'mdi:school-outline')"
                  class="h-4 w-4"
                />
                {{ message.speaker_name }}
              </div>

              <div class="chat-message-copy text-sm leading-7 md:text-base">
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
                />
                <p v-else class="whitespace-pre-wrap">{{ message.content }}</p>
              </div>
              <button
                v-if="isFailedMessage(message) && retryRequestId(message)"
                type="button"
                class="chat-secondary-button mt-4 inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface-muted)] px-4 text-sm font-semibold text-[var(--admin-coffee)] transition hover:bg-[var(--admin-coffee-soft)] disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="isReplying"
                @click="$emit('retry-message', retryRequestId(message) || '')"
              >
                <Icon name="mdi:refresh" class="h-4 w-4" />
                重試這次回覆
              </button>
            </div>
          </div>
          </div>
        </div>
        <button v-if="!followingLatest" type="button" @click="scrollToLatest"
          :class="{ 'has-new-reply': hasNewReply }"
          class="chat-latest-button absolute bottom-3 left-1/2 inline-flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-full border border-[var(--admin-border)] bg-[var(--admin-surface)] px-4 py-2 text-sm font-semibold text-[var(--admin-coffee)] shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--admin-coffee)]">
          <Icon name="mdi:arrow-down" class="h-4 w-4" aria-hidden="true" />
          {{ hasNewReply ? '有新回覆 · 回到最新' : '回到最新回覆' }}
        </button>
        </div>

        <footer class="chat-composer shrink-0 border-t border-[var(--admin-border-soft)] p-3 md:p-5">
          <form v-if="!sessionClosed" class="chat-composer-form flex items-end gap-2" :aria-busy="isReplying" @submit.prevent="handleSendMessage">
            <textarea
              v-model="userInput"
              rows="1"
              aria-label="輸入訊息"
              :placeholder="inputPlaceholder"
              class="chat-input max-h-36 min-h-12 min-w-0 flex-1 resize-y rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] px-4 py-3 text-sm leading-6 text-[var(--admin-text)] outline-none transition focus:border-[var(--admin-coffee-muted)] focus:ring-4 focus:ring-[var(--admin-focus)]"
              :disabled="isReplying || sessionClosed"
            />
            <button
              type="submit"
              aria-label="送出訊息"
              :disabled="isReplying || sessionClosed || !userInput.trim()"
              class="chat-send-button inline-flex h-12 w-12 items-center justify-center rounded-lg bg-[var(--admin-coffee)] text-[var(--admin-surface)] transition hover:bg-[var(--admin-coffee-hover)] disabled:cursor-not-allowed disabled:bg-[var(--admin-border)]"
            >
              <Icon :name="isReplying ? 'mdi:loading' : 'mdi:send'" class="h-5 w-5" :class="{ 'animate-spin': isReplying }" />
            </button>
          </form>
          <p v-else class="text-center text-sm font-semibold text-[var(--admin-soft)]">
            本階段已結束，請使用上方按鈕進入下一階段。
          </p>
        </footer>
        </StudySplitView>
      </section>

    </main>

    <ConfirmActionModal
      class="chat-exit-overlay"
      :show="showExitConfirmDialog"
      title="離開對話"
      message="要返回事件素材庫嗎？"
      eyebrow="階段確認"
      icon="mdi:library-outline"
      confirm-label="返回素材庫"
      cancel-label="繼續對話"
      @confirm="confirmExitConversation"
      @cancel="showExitConfirmDialog = false"
    />
  </div>
</template>

<script setup lang="ts">
// ChatScreen 只管理本地輸入框、固定人物呈現與畫面捲動。
// 對話 state、API error handling、history 替換都在 useConversationSession 處理。
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import type { ChatMessage, EventTask, ExperimentCondition, ExperimentSession, HistoricalEvent, LearningFocus, Persona, TaskAttempt } from '~/types';
import Typewriter from './Typewriter.vue';
import ConfirmActionModal from '~/components/modals/ConfirmActionModal.vue';
import TaskAttemptReview from '~/components/task-student/TaskAttemptReview.vue';
import TaskProgressNotice from '~/components/task-student/TaskProgressNotice.vue';
import StudySplitView from '~/components/chat/StudySplitView.vue';
import PersonaAvatar from '~/components/chat/PersonaAvatar.vue';
import SessionTimerBanner from '~/components/session/SessionTimerBanner.vue';
import { studentActivityTitle } from '~/composables/useStudentTask';
import { useChatScroll } from '~/composables/useChatScroll';

const props = defineProps<{
  event: HistoricalEvent | null;
  personas: Persona[];
  history: ChatMessage[];
  conversationId: string;
  condition?: ExperimentCondition | null;
  task?: EventTask | null;
  taskAttempt?: TaskAttempt | null;
  learningFocus?: LearningFocus | null;
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
  (event: 'retry-message', clientRequestId: string): void;
}>();

const userInput = ref('');
const chatContainerRef = ref<HTMLDivElement | null>(null);
const chatContentRef = ref<HTMLDivElement | null>(null);
const { followingLatest, hasNewReply, highlightedMessageId, onScroll: onChatScroll, scrollToLatest } = useChatScroll(
  chatContainerRef, chatContentRef, () => props.history, () => props.conversationId,
);
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
const isFailedMessage = (message: ChatMessage) => {
  return messageMetadata(message).generation_status === 'failed';
};
const retryRequestId = (message: ChatMessage) => {
  if (message.client_request_id) return message.client_request_id;
  const requestId = messageMetadata(message).client_request_id;
  return typeof requestId === 'string' ? requestId : null;
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

// role-play 模式依事件固定人物調整 placeholder，不提供切換入口。
const inputPlaceholder = computed(() => {
  if (!props.condition?.roleplay_enabled) return '輸入你的問題...';
  return `向 ${lockedPersona.value?.name || '歷史人物'} 提問...`;
});

const handleSendMessage = () => {
  const trimmed = userInput.value.trim();
  if (!trimmed || props.isReplying) return;
  scrollToLatest();
  emit('send-message', trimmed);
  userInput.value = '';
};

const confirmExitConversation = () => {
  showExitConfirmDialog.value = false;
  emit('reset');
};

</script>

<style src="~/assets/css/chat-workspace.css"></style>
