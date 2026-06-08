<template>
  <div class="flex h-screen min-h-0 flex-col bg-slate-50 font-sans text-slate-950">
    <header class="shrink-0 border-b border-slate-200 bg-white">
      <div class="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-4 md:flex-row md:items-center md:justify-between">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-500">
            <span>{{ condition?.label || 'Condition loading' }}</span>
            <span class="rounded-full bg-slate-100 px-2 py-0.5">
              {{ condition?.response_policy || 'direct' }}
            </span>
          </div>
          <h1 class="mt-1 truncate text-xl font-bold text-slate-950 md:text-2xl">
            {{ event?.canonical_name || '載入中' }}
          </h1>
        </div>

        <button
          class="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-teal-500 hover:text-teal-700"
          @click="$emit('reset')"
        >
          <Icon name="mdi:plus" class="h-5 w-5" />
          新事件
        </button>
      </div>
    </header>

    <main class="mx-auto grid min-h-0 w-full max-w-6xl flex-1 gap-4 px-5 py-4 lg:grid-cols-[minmax(0,1fr)_280px]">
      <section class="flex min-h-0 flex-col rounded-xl border border-slate-200 bg-white shadow-sm">
        <div class="border-b border-slate-200 px-4 py-3 text-sm text-slate-600">
          {{ policyDescription }}
        </div>

        <div ref="chatContainerRef" class="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
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
                'max-w-[86%] rounded-xl border px-4 py-3 shadow-sm',
                message.speaker_type === 'learner'
                  ? 'border-slate-900 bg-slate-950 text-white'
                  : 'border-slate-200 bg-slate-50 text-slate-950'
              ]"
            >
              <div
                v-if="message.speaker_type !== 'learner'"
                class="mb-2 flex items-center gap-2 border-b border-slate-200 pb-2 text-xs font-bold text-slate-500"
              >
                <Icon :name="message.speaker_type === 'persona' ? 'mdi:account-voice' : 'mdi:school-outline'" class="h-4 w-4" />
                {{ message.speaker_name }}
              </div>

              <div class="text-sm leading-7 md:text-base">
                <div v-if="message.content === '...'" class="flex items-center gap-2 text-slate-500">
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

        <footer class="shrink-0 border-t border-slate-200 p-4">
          <div v-if="condition?.roleplay_enabled" class="mb-3 flex gap-2 overflow-x-auto pb-1">
            <button
              type="button"
              :class="selectorClass(selectedPersonaId === null)"
              @click="selectedPersonaId = null"
            >
              自動
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
              class="max-h-36 min-h-12 flex-1 resize-y rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm leading-6 text-slate-950 outline-none transition focus:border-teal-600 focus:ring-4 focus:ring-teal-100"
              :disabled="isReplying"
            />
            <button
              type="submit"
              :disabled="isReplying || !userInput.trim()"
              class="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-slate-950 text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              <Icon name="mdi:send" class="h-5 w-5" />
            </button>
          </form>
        </footer>
      </section>

      <aside class="hidden min-h-0 space-y-4 lg:block">
        <div class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 class="text-sm font-bold text-slate-950">Task judgement</h2>
          <p class="mt-2 text-sm leading-6 text-slate-600">
            {{ taskAttempt?.judgement_payload?.misconception_summary || '尚無 task judgement。' }}
          </p>
        </div>

        <div v-if="condition?.roleplay_enabled" class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 class="text-sm font-bold text-slate-950">Personas</h2>
          <div class="mt-3 space-y-3">
            <div v-for="persona in personas" :key="persona.id" class="rounded-lg border border-slate-200 p-3">
              <p class="font-semibold text-slate-950">{{ persona.name }}</p>
              <p class="mt-1 text-sm text-slate-500">{{ persona.role || 'role 待補' }}</p>
              <p class="mt-2 line-clamp-3 text-xs leading-5 text-slate-600">{{ persona.biography }}</p>
            </div>
          </div>
        </div>

        <div v-else class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 class="text-sm font-bold text-slate-950">Generic chatbot</h2>
          <p class="mt-2 text-sm leading-6 text-slate-600">
            此條件不使用歷史 persona，因此對話會以一般 AI assistant / tutor 回應。
          </p>
        </div>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import type { ChatMessage, ExperimentCondition, HistoricalEvent, Persona, TaskAttempt } from '~/types';
import Typewriter from './Typewriter.vue';
import AnnotatedText from './AnnotatedText.vue';

const props = defineProps<{
  event: HistoricalEvent | null;
  personas: Persona[];
  history: ChatMessage[];
  conversationId: string;
  condition?: ExperimentCondition | null;
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

const isReplying = computed(() => {
  const lastMessage = props.history[props.history.length - 1];
  return lastMessage?.content === '...';
});

const policyDescription = computed(() => {
  if (!props.condition) return props.dynamicContext;
  if (props.condition.response_policy === 'scaffold') {
    return 'EBL scaffold：先引導 historical thinking、evidence-based argumentation 與 source interpretation，不先直接給答案。';
  }
  return 'Direct answer：以直接回答與情境解釋為主。';
});

const inputPlaceholder = computed(() => {
  if (!props.condition?.roleplay_enabled) return '向 AI assistant 提問...';
  if (!selectedPersonaId.value) return '向歷史人物們提問...';
  const persona = props.personas.find((item) => item.id === selectedPersonaId.value);
  return `向 ${persona?.name || '歷史人物'} 提問...`;
});

const selectorClass = (active: boolean) => [
  'whitespace-nowrap rounded-lg border px-3 py-2 text-xs font-semibold transition',
  active
    ? 'border-teal-500 bg-teal-50 text-teal-700'
    : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300',
];

const handleSendMessage = () => {
  const trimmed = userInput.value.trim();
  if (!trimmed || isReplying.value) return;
  emit('send-message', trimmed, selectedPersonaId.value || undefined);
  userInput.value = '';
};

watch(
  () => props.history,
  async () => {
    await nextTick();
    chatEndRef.value?.scrollIntoView({ behavior: 'smooth' });
  },
  { deep: true },
);
</script>
