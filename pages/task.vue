<template>
  <div class="min-h-screen bg-slate-50 font-sans text-slate-950">
    <header class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex max-w-4xl items-center justify-between px-5 py-4">
        <NuxtLink to="/" class="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-slate-950">
          <Icon name="mdi:arrow-left" class="h-5 w-5" />
          回首頁
        </NuxtLink>
        <span class="rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-700">
          Task before chat
        </span>
      </div>
    </header>

    <main class="mx-auto max-w-4xl px-5 py-8">
      <div v-if="!taskData" class="rounded-xl border border-amber-200 bg-amber-50 p-6 text-amber-900">
        找不到 task 狀態。請回首頁重新建立流程。
      </div>

      <section v-else class="space-y-6">
        <div>
          <p class="text-sm font-semibold uppercase tracking-wide text-slate-500">
            {{ taskData.condition.label }}
          </p>
          <h1 class="mt-2 text-3xl font-bold tracking-tight text-slate-950">
            {{ taskData.event.canonical_name }}
          </h1>
          <p class="mt-3 text-base leading-7 text-slate-600">
            先完成這個 task。你的回答會被用來判斷 learner misconceptions，並影響後續對話策略。
          </p>
        </div>

        <article class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <h2 class="text-xl font-bold text-slate-950">{{ taskData.task.title || '歷史故事挖洞' }}</h2>
              <p class="mt-2 text-sm text-slate-500">
                Revision: {{ revisionLabel(taskData.task.revision_state) }}
              </p>
            </div>
            <div class="flex flex-wrap gap-2 text-xs">
              <span class="rounded-full bg-slate-100 px-3 py-1 font-semibold text-slate-600">
                {{ taskData.condition.ebl_enabled ? 'EBL' : 'No EBL' }}
              </span>
              <span class="rounded-full bg-slate-100 px-3 py-1 font-semibold text-slate-600">
                {{ taskData.condition.roleplay_enabled ? 'Persona' : 'Generic' }}
              </span>
            </div>
          </div>

          <div class="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-5">
            <p class="whitespace-pre-wrap text-xl leading-10 text-slate-950">
              {{ taskData.task.display_text }}
            </p>
          </div>

          <details class="mt-4 rounded-lg border border-slate-200 bg-white p-4">
            <summary class="cursor-pointer text-sm font-semibold text-slate-700">查看原始故事文本</summary>
            <p class="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-600">
              {{ taskData.task.story_text }}
            </p>
          </details>
        </article>

        <form class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm" @submit.prevent="submitTask">
          <label for="answer" class="text-sm font-bold text-slate-700">你的回答</label>
          <textarea
            id="answer"
            v-model="answerText"
            rows="6"
            class="mt-2 w-full resize-y rounded-lg border border-slate-300 bg-white px-4 py-3 text-base leading-7 text-slate-950 outline-none transition focus:border-teal-600 focus:ring-4 focus:ring-teal-100"
            placeholder="請用自己的話補上你認為重要的缺口、理由或不確定之處..."
          />

          <div v-if="judgement" class="mt-4 rounded-lg border border-teal-200 bg-teal-50 p-4 text-sm text-teal-900">
            <p class="font-bold">LLM 初步判斷：{{ judgement.result || 'submitted' }}</p>
            <p class="mt-1 leading-6">{{ judgement.misconception_summary || judgement.feedback }}</p>
          </div>

          <p v-if="error" class="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
            {{ error }}
          </p>

          <div class="mt-5 flex justify-end">
            <button
              type="submit"
              :disabled="isSubmitting || !answerText.trim()"
              class="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              <Icon v-if="isSubmitting" name="mdi:loading" class="h-5 w-5 animate-spin" />
              <Icon v-else name="mdi:message-processing-outline" class="h-5 w-5" />
              {{ isSubmitting ? '送出並建立對話' : '送出 task，進入對話' }}
            </button>
          </div>
        </form>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import type { EventInitializeResponse, TaskSubmitResponse } from '~/types';

definePageMeta({
  layout: false,
  name: 'task-gate',
});

const taskData = useState<EventInitializeResponse | null>('taskData', () => null);
const answerText = ref('');
const isSubmitting = ref(false);
const error = ref<string | null>(null);
const judgement = ref<Record<string, any> | null>(null);

const revisionLabel = (state: string) => {
  const labels: Record<string, string> = {
    llm_generated: 'LLM generated',
    teacher_modified: 'Teacher modified',
    manual: 'Manual',
  };
  return labels[state] || state;
};

const submitTask = async () => {
  if (!taskData.value || !answerText.value.trim()) return;
  isSubmitting.value = true;
  error.value = null;
  try {
    const response = await $fetch<TaskSubmitResponse>(`/api/tasks/${taskData.value.task.id}/submit`, {
      method: 'POST',
      body: {
        session_id: taskData.value.session_id,
        response_payload: {
          answer_text: answerText.value.trim(),
        },
      },
    });
    judgement.value = response.judgement;

    const chatData = useState<TaskSubmitResponse | null>('chatData', () => null);
    chatData.value = response;
    await navigateTo({
      path: '/chat',
      query: {
        conversationId: response.conversation_id,
      },
    });
  } catch (e: any) {
    error.value = e.data?.detail || e.data?.message || '送出 task 失敗，請稍後再試。';
  } finally {
    isSubmitting.value = false;
  }
};
</script>
