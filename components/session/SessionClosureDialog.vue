<template>
  <dialog
    ref="dialog"
    aria-labelledby="closure-title"
    class="m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-2xl overflow-y-auto rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] p-6 text-[var(--admin-text)] shadow-2xl outline-none backdrop:bg-black/40 backdrop:backdrop-blur-sm sm:p-8"
    @cancel.prevent
  >
    <header class="flex items-start gap-4">
      <Icon name="mdi:timer-check-outline" class="mt-1 h-7 w-7 shrink-0 text-[var(--admin-coffee)]" />
      <div>
        <p class="text-sm font-bold text-[var(--admin-coffee)]">五分鐘對話已結束</p>
        <h2 id="closure-title" class="mt-2 text-2xl font-bold">{{ closure ? '整理這一題的想法' : '本階段已結束' }}</h2>
      </div>
    </header>
    <p v-if="loading" role="status" class="mt-6 text-[var(--admin-copy)]">正在載入收尾內容…</p>
    <p v-else-if="error" role="alert" class="mt-6 text-[var(--admin-coffee)]">{{ error }}</p>
    <section v-if="!loading && !error && finalExchange" class="mt-6 space-y-4 border-t border-[var(--admin-border)] pt-5" aria-label="最後一輪對話">
      <p class="text-sm font-bold text-[var(--admin-coffee)]">你最後送出的訊息</p>
      <p class="whitespace-pre-wrap rounded-md bg-[var(--admin-page)] p-4 text-base leading-7">{{ finalExchange.learner_message }}</p>
      <template v-if="finalExchange.assistant_message">
        <p class="text-sm font-bold text-[var(--admin-coffee)]">{{ finalExchange.assistant_name }}的最後回覆</p>
        <p class="whitespace-pre-wrap text-base leading-7">{{ finalExchange.assistant_message }}</p>
        <p v-if="finalExchange.delivered_after_deadline" class="text-sm text-[var(--admin-copy)]">這是倒數結束前送出訊息的回覆，保留在這裡供你整理想法。</p>
      </template>
      <p v-else-if="finalExchange.failed" role="status" class="text-sm text-[var(--admin-copy)]">最後一輪未能產生回覆，你送出的文字已保存。請依下方內容完成本階段。</p>
    </section>
    <p v-if="!loading && !error && pendingFinalResponse" role="status" class="mt-6 text-base leading-7 text-[var(--admin-copy)]">最後一輪回覆仍在處理，完成後會自動顯示。你不需要重新送出。</p>
    <template v-if="!loading && !error && !pendingFinalResponse && closure">
      <section class="mt-6 border-t border-[var(--admin-border)] pt-5">
        <p class="text-sm font-bold text-[var(--admin-coffee)]">剛才討論的問題</p>
        <p class="mt-2 whitespace-pre-wrap text-base leading-7">{{ closure.question }}</p>
        <dl class="mt-5 grid gap-2 border-l-2 border-[var(--admin-coffee)] pl-4">
          <dt class="text-sm font-bold text-[var(--admin-coffee)]">正確答案</dt>
          <dd class="break-words text-base font-bold leading-7">{{ closure.answer }}</dd>
          <dt class="mt-2 text-sm font-bold text-[var(--admin-coffee)]">理由</dt>
          <dd class="whitespace-pre-wrap text-base leading-7 text-[var(--admin-copy)]">{{ closure.explanation }}</dd>
        </dl>
      </section>
      <form class="mt-6" @submit.prevent="finish">
        <label for="closure-reflection" class="block text-base font-bold leading-7">看過說明後，請用自己的話，說明原先的答案或理由應如何修正。</label>
        <textarea
          id="closure-reflection"
          v-model="reflection"
          :readonly="Boolean(closure.completed_at)"
          :disabled="saving"
          rows="4"
          maxlength="6000"
          required
          class="mt-3 w-full resize-y rounded-md border border-[var(--admin-border)] bg-[var(--admin-surface)] p-3 text-base leading-7 outline-none focus:border-[var(--admin-coffee)] focus:ring-1 focus:ring-[var(--admin-coffee)]"
        />
        <p v-if="saveError" role="alert" class="mt-2 text-sm text-[var(--admin-coffee)]">{{ saveError }}</p>
        <p v-if="closure.completed_at" class="mt-2 text-sm text-[var(--admin-copy)]">你的重述已保存。</p>
        <div class="mt-5 flex justify-end">
          <button type="submit" :disabled="saving || !reflection.trim()" class="inline-flex min-h-12 items-center gap-2 rounded-md bg-[var(--admin-coffee)] px-5 py-3 font-bold text-white disabled:opacity-50">
            <Icon :name="saving ? 'mdi:loading' : 'mdi:arrow-right'" :class="['h-5 w-5', saving && 'animate-spin']" />
            {{ saving ? '儲存中' : '繼續：本輪後測' }}
          </button>
        </div>
      </form>
    </template>
    <p v-else-if="!loading && !error && !pendingFinalResponse" class="mt-6 text-base leading-7 text-[var(--admin-copy)]">本輪互動已結束，接下來請完成活動回饋與歷史思考後測。</p>
    <div v-if="!loading && (error || (!pendingFinalResponse && !closure))" class="mt-6 flex justify-end">
      <button type="button" class="inline-flex min-h-12 items-center gap-2 rounded-md bg-[var(--admin-coffee)] px-5 py-3 font-bold text-white" @click="error ? load() : $emit('next-stage')">
        <Icon :name="error ? 'mdi:refresh' : 'mdi:arrow-right'" class="h-5 w-5" />
        {{ error ? '重新載入' : '繼續：本輪後測' }}
      </button>
    </div>
  </dialog>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import type { SessionClosure, SessionFinalExchange } from '~/types';
import { fetchSessionState, submitSessionClosure } from '~/utils/histosphereApi';

const props = defineProps<{ sessionId: string }>();
const emit = defineEmits<{ (event: 'next-stage'): void }>();
const dialog = ref<HTMLDialogElement | null>(null);
const closure = ref<SessionClosure | null>(null);
const finalExchange = ref<SessionFinalExchange | null>(null);
const pendingFinalResponse = ref(false);
const reflection = ref('');
const loading = ref(true);
const saving = ref(false);
const error = ref('');
const saveError = ref('');
let refreshTimer: ReturnType<typeof setTimeout> | undefined;
let disposed = false;

async function load(background = false) {
  if (refreshTimer) clearTimeout(refreshTimer);
  if (!background) loading.value = true;
  error.value = '';
  try {
    const state = await fetchSessionState(props.sessionId);
    if (disposed) return;
    // 以伺服器確認到期，不能靠調快瀏覽器時鐘提前領取正解或跳過收尾。
    if (!['completed', 'archived'].includes(state.session.status)) throw new Error('伺服器尚未確認本階段結束，請稍候重新載入。');
    closure.value = state.closure || null;
    finalExchange.value = state.final_exchange || null;
    pendingFinalResponse.value = Boolean(state.pending_final_response);
    reflection.value = state.closure?.reflection || '';
    if (pendingFinalResponse.value) refreshTimer = setTimeout(() => { void load(true); }, 2000);
  } catch (cause: any) {
    error.value = cause.data?.detail || cause.message || '無法載入收尾內容，請重試。';
  } finally {
    loading.value = false;
  }
}

async function finish() {
  if (!closure.value || !reflection.value.trim() || saving.value) return;
  saving.value = true;
  saveError.value = '';
  try {
    // 重連後仍送後端確認；不可僅憑舊畫面略過管理員可能已重置的倒數。
    closure.value = await submitSessionClosure(props.sessionId, closure.value.closure_id, reflection.value);
    emit('next-stage');
  } catch (cause: any) {
    saveError.value = cause.data?.detail || '尚未保存，請重試；你的文字仍在這裡。';
  } finally {
    saving.value = false;
  }
}

onMounted(() => { dialog.value?.showModal(); void load(); });
onBeforeUnmount(() => {
  disposed = true;
  if (refreshTimer) clearTimeout(refreshTimer);
  dialog.value?.close();
});
</script>
