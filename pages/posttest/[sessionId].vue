<template>
  <div class="posttest-page min-h-screen bg-[var(--admin-page)] font-sans text-[var(--admin-text)]">
    <header class="border-b border-[var(--admin-border)] bg-[var(--admin-surface)]">
      <div class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4">
        <div class="flex items-center gap-3">
          <Icon name="mdi:book-open-page-variant" class="h-7 w-7 text-[var(--admin-coffee)]" />
          <span class="font-serif text-xl font-bold tracking-wide">Histosphere</span>
        </div>
        <span class="text-sm text-[var(--admin-copy)]">{{ state?.event_name || '本輪活動' }} · 後測</span>
      </div>
    </header>
    <main class="mx-auto max-w-6xl px-5 py-8 md:py-10">
      <div v-if="loading" class="py-20 text-center" role="status">
        <Icon name="mdi:loading" class="h-7 w-7 animate-spin" />
        <p class="mt-3">正在載入本輪後測…</p>
      </div>
      <section v-else-if="!state || !state.eligible" class="mx-auto max-w-xl rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-8">
        <h1 class="text-2xl font-bold">{{ state ? '尚未進入後測' : '暫時無法載入後測' }}</h1>
        <p class="my-5 leading-7" role="alert">{{ error || state?.blocked_reason || '請先完成本輪對話與收尾，再進入後測。' }}</p>
        <button v-if="!state" class="posttest-primary" @click="load()">重新載入</button>
        <NuxtLink v-else :to="state.conversation_id ? `/conversations/${state.conversation_id}` : '/'" class="posttest-primary">返回目前活動</NuxtLink>
      </section>
      <template v-else>
        <ol class="mx-auto mb-8 grid max-w-2xl grid-cols-3 gap-3" aria-label="本輪後測進度">
          <li v-for="(step, index) in steps" :key="step.id" :aria-current="stage === step.id ? 'step' : undefined" class="flex flex-col items-center gap-2 text-center text-sm"
            :class="index <= stepIndex ? 'font-bold text-[var(--admin-coffee)]' : 'text-[var(--admin-copy)]'">
            <span class="flex h-9 w-9 items-center justify-center rounded-full border"
              :class="index <= stepIndex ? 'border-[var(--admin-coffee)] bg-[var(--admin-coffee)] text-white' : 'border-[var(--admin-border)] bg-[var(--admin-surface)]'">
              <Icon v-if="index < stepIndex" name="mdi:check" class="h-5 w-5" /><template v-else>{{ index + 1 }}</template>
            </span>
            {{ step.label }}
          </li>
        </ol>
        <div class="mb-6 rounded-lg border border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] px-4 py-3 text-sm leading-6 text-[var(--admin-coffee)]">
          <strong>流程示範版</strong> · 以下為 Pseudo 題目，僅供操作測試，不是正式量表或 HAT 題本。
        </div>
        <section v-if="stage === 'completed'" class="rounded-2xl border border-[var(--admin-border)] bg-[var(--admin-surface)] px-6 py-14 text-center">
          <Icon name="mdi:check-circle-outline" class="h-14 w-14 text-[var(--admin-success)]" />
          <h1 ref="heading" tabindex="-1" class="mt-5 text-3xl font-bold focus:outline-none">本輪已完成</h1>
          <p class="mt-4 leading-8 text-[var(--admin-copy)]">活動回饋與歷史思考後測已成功提交。<br />請依研究人員指示休息或進行下一個活動。</p>
          <NuxtLink to="/" class="posttest-primary mt-8">返回活動列表</NuxtLink>
        </section>
        <form v-else @submit.prevent="continueStage">
          <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p class="mb-2 text-sm font-bold text-[var(--admin-coffee)]">{{ stage === 'engagement' ? '步驟 1 / 2' : '步驟 2 / 2' }}</p>
              <h1 ref="heading" tabindex="-1" class="text-3xl font-bold focus:outline-none">{{ stage === 'engagement' ? '活動回饋' : '歷史思考後測' }}</h1>
              <p class="mt-3 leading-7 text-[var(--admin-copy)]">{{ stage === 'engagement' ? '請回想剛剛與 AI 互動的經驗，選擇最符合感受的程度。' : '請閱讀本頁材料，再獨立填寫你的判斷與理由。' }}</p>
            </div>
            <p class="text-sm font-medium text-[var(--admin-copy)]">已填 {{ completedCount }} / {{ stage === 'engagement' ? 3 : 2 }} 題</p>
          </div>
          <PosttestEngagement v-if="stage === 'engagement'" :model-value="engagement" :disabled="submitting || conflict" @update:model-value="updateEngagement" />
          <PosttestHat v-else :model-value="hat" :disabled="submitting || conflict" @update:model-value="updateHat" />
          <div v-if="error" role="alert" class="mt-5 rounded-lg border border-[var(--admin-danger)] bg-[var(--admin-danger-soft)] p-4 text-sm leading-6 text-[var(--admin-danger)]">
            {{ error }}
            <button type="button" class="ml-2 font-bold underline" :disabled="saving || submitting" @click="conflict ? load(true) : save()">{{ conflict ? '載入伺服器作答' : '重試儲存' }}</button>
          </div>
          <footer class="mt-8 flex flex-col gap-5 border-t border-[var(--admin-border)] pt-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p role="status" class="text-sm font-medium text-[var(--admin-copy)]">{{ saving ? '正在儲存…' : error ? '尚未完成儲存' : dirty ? '等待儲存…' : '作答已儲存' }}</p>
              <p class="mt-1 text-xs leading-6 text-[var(--admin-copy)]">{{ stage === 'engagement' ? '完成全部題目後繼續；進入後測後，活動回饋將無法修改。' : '請確認作答內容；提交後將無法修改。' }}</p>
            </div>
            <button type="submit" class="posttest-primary" :disabled="!canContinue">
              <Icon v-if="submitting" name="mdi:loading" class="h-5 w-5 animate-spin" />
              {{ submitting ? '正在處理…' : stage === 'engagement' ? '繼續：歷史思考後測' : '提交並完成本輪' }}
              <Icon v-if="!submitting" name="mdi:arrow-right" class="h-4 w-4" />
            </button>
          </footer>
        </form>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import PosttestEngagement from '~/components/posttest/PosttestEngagement.vue';
import PosttestHat from '~/components/posttest/PosttestHat.vue';

definePageMeta({ layout: false, key: route => route.fullPath });
const route = useRoute();
const sessionId = String(route.params.sessionId);
const { state, engagement, hat, loading, saving, submitting, error, conflict, dirty, stage, completedCount,
  canContinue, updateEngagement, updateHat, load, save, continueStage } = usePosttest(sessionId);
const heading = ref<HTMLElement | null>(null);
const steps = [{ id: 'engagement', label: '活動回饋' }, { id: 'hat', label: '歷史思考後測' }, { id: 'completed', label: '本輪完成' }];
const stepIndex = computed(() => steps.findIndex(step => step.id === stage.value));
watch(stage, async () => {
  await nextTick();
  heading.value?.focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: 'instant' });
});
onBeforeRouteLeave(async () => {
  if (submitting.value) return false;
  if (dirty.value) return await save();
});
</script>

<style scoped>
.posttest-primary {
  display: inline-flex; align-items: center; justify-content: center; gap: .65rem;
  min-height: 3rem; padding: .8rem 1.4rem; border-radius: .65rem;
  background: var(--admin-coffee); color: #fff; font-weight: 700;
}
.posttest-primary:hover:not(:disabled) { background: var(--admin-coffee-hover); }
.posttest-primary:focus-visible { outline: 3px solid var(--admin-coffee-muted); outline-offset: 3px; }
.posttest-primary:disabled { opacity: .45; cursor: not-allowed; }
</style>
