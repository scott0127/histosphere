<template>
  <!-- 左側登入卡只處理使用者身分；事件建立入口移到素材庫列表。 -->
  <section class="flex h-full justify-center">
    <article class="relative w-full max-w-[430px] rounded-xl border border-[var(--admin-border)] bg-[rgba(255,253,248,0.95)] p-1.5 shadow-xl lg:h-full">
      <div class="h-full rounded-[10px] border border-[var(--admin-border-soft)] px-6 py-9 text-center lg:flex lg:flex-col lg:justify-center">
        <div class="relative mx-auto flex h-20 w-20 items-center justify-center">
          <div class="pointer-events-none absolute inset-0">
            <div class="absolute bottom-0 left-1/2 top-0 w-[1px] -translate-x-1/2 border-b-2 border-t-2 border-[var(--admin-border)]"></div>
            <div class="absolute left-0 right-0 top-1/2 h-[1px] -translate-y-1/2 border-l-2 border-r-2 border-[var(--admin-border)]"></div>
            <div class="absolute inset-[3px] rounded-full border border-dashed border-[var(--admin-border)]"></div>
          </div>
          <div class="relative flex h-14 w-14 items-center justify-center rounded-full border border-[var(--admin-border)] bg-[var(--admin-surface)] text-[var(--admin-coffee)] shadow-sm">
            <Icon name="mdi:account-circle-outline" class="h-7 w-7 text-[var(--admin-coffee)]" />
          </div>
        </div>

        <h1 class="mt-5 font-serif text-3xl font-bold uppercase leading-[1.15] tracking-[0.14em] text-[var(--admin-text)]">
          USER<br>LOGIN
        </h1>
        <div class="my-4 flex items-center justify-center gap-2">
          <span class="h-[1px] w-8 bg-[var(--admin-border)]"></span>
          <span class="text-[8px] text-[var(--admin-coffee)]">◆</span>
          <span class="h-[1px] w-8 bg-[var(--admin-border)]"></span>
        </div>
        <p class="text-xs font-semibold tracking-[0.08em] text-[var(--admin-copy)]">
          登入後管理你的歷史學習紀錄
        </p>

        <div v-if="isAuthenticated" class="mt-7 rounded-[10px] border border-[var(--admin-border-soft)] bg-[var(--admin-surface-muted)] p-5 text-left shadow-inner">
          <div class="flex items-center gap-3">
            <span class="flex h-11 w-11 items-center justify-center rounded-full border border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] text-[var(--admin-coffee)]">
              <Icon name="mdi:account" class="h-5 w-5" />
            </span>
            <div class="min-w-0">
              <p class="text-xs font-bold uppercase tracking-[0.16em] text-[var(--admin-coffee)]">目前使用者</p>
              <p class="truncate text-base font-black text-[var(--admin-text)]">{{ displayName || user?.email }}</p>
            </div>
          </div>
          <button
            type="button"
            class="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-[8px] border border-[var(--admin-border)] bg-[var(--admin-surface)] py-3 text-sm font-bold text-[var(--admin-coffee)] transition hover:bg-[var(--admin-coffee-soft)]"
            @click="handleSignOut"
          >
            <Icon name="mdi:logout" class="h-4 w-4" />
            登出
          </button>
        </div>

        <form v-else class="mt-7 space-y-4 text-left" @submit.prevent="handleSignIn">
          <div>
            <label for="loginEmail" class="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-[0.16em] text-[var(--admin-coffee)]">
              <Icon name="mdi:email-outline" class="h-4 w-4" />
              Email
            </label>
            <input
              id="loginEmail"
              v-model="email"
              type="email"
              autocomplete="email"
              class="w-full rounded-[8px] border border-[var(--admin-border)] bg-[var(--admin-surface)] px-4 py-3 text-sm font-semibold text-[var(--admin-text)] shadow-inner outline-none transition placeholder:text-[var(--admin-soft)] focus:bg-[var(--admin-surface)] focus:ring-2 focus:ring-[var(--admin-focus)]"
              placeholder="your@email.com"
            />
          </div>

          <div>
            <label for="loginPassword" class="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-[0.16em] text-[var(--admin-coffee)]">
              <Icon name="mdi:lock-outline" class="h-4 w-4" />
              密碼
            </label>
            <div class="relative">
              <input
                id="loginPassword"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                class="w-full rounded-[8px] border border-[var(--admin-border)] bg-[var(--admin-surface)] py-3 pl-4 pr-11 text-sm font-semibold text-[var(--admin-text)] shadow-inner outline-none transition placeholder:text-[var(--admin-soft)] focus:bg-[var(--admin-surface)] focus:ring-2 focus:ring-[var(--admin-focus)]"
                placeholder="輸入密碼"
              />
              <button
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--admin-soft)] transition hover:text-[var(--admin-coffee)]"
                :title="showPassword ? '隱藏密碼' : '顯示密碼'"
                @click="showPassword = !showPassword"
              >
                <Icon :name="showPassword ? 'mdi:eye-off' : 'mdi:eye'" class="h-5 w-5" />
              </button>
            </div>
          </div>

          <button
            type="submit"
            :disabled="authLoading || !email.trim() || !password.trim()"
            class="inline-flex w-full items-center justify-center gap-2 rounded-[8px] border border-[var(--admin-coffee)] bg-[var(--admin-coffee)] py-3 text-base font-bold text-[var(--admin-surface)] shadow-md transition-all duration-300 hover:bg-[var(--admin-coffee-hover)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
          >
            <Icon v-if="authLoading" name="mdi:loading" class="h-5 w-5 animate-spin" />
            <span v-else class="flex items-center gap-2">
              登入
              <Icon name="mdi:login" class="h-5 w-5" />
            </span>
          </button>

          <p v-if="loginError" class="rounded-[8px] border border-red-300 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
            {{ loginError }}
          </p>

          <div class="flex items-center justify-center text-sm font-semibold text-[var(--admin-copy)]">
            <NuxtLink to="/auth/forgot-password" class="hover:text-[var(--admin-text)] hover:underline">
              忘記密碼
            </NuxtLink>
          </div>
        </form>
      </div>
      <img src="/images/vintage_book_quill.png" alt="" class="pointer-events-none absolute bottom-4 left-1/2 w-48 -translate-x-1/2 select-none opacity-[0.07] mix-blend-multiply" />
    </article>
  </section>
</template>

<script setup lang="ts">
// EventCreatePanel 專注於首頁左側登入表單；事件建立由 EventLibraryList 觸發。
import { onMounted, ref } from 'vue';

const { user, displayName, isAuthenticated, loading: authLoading, initialize, signIn, signOut } = useAuth();

const email = ref('');
const password = ref('');
const showPassword = ref(false);
const loginError = ref<string | null>(null);

onMounted(async () => {
  await initialize();
});

const handleSignIn = async () => {
  loginError.value = null;
  const result = await signIn(email.value.trim(), password.value);
  if (!result.success) {
    loginError.value = translateAuthError(result.error || '登入失敗，請稍後再試。');
    return;
  }
  password.value = '';
};

const handleSignOut = async () => {
  await signOut();
};

const translateAuthError = (message: string) => {
  const map: Record<string, string> = {
    'Supabase 未設定': '尚未設定 Supabase Auth，請先設定 VITE_SUPABASE_URL 與 VITE_SUPABASE_ANON_KEY。',
    'Invalid login credentials': '電子郵件或密碼錯誤。',
    'Email not confirmed': '電子郵件尚未驗證，請先完成信箱驗證。',
  };
  return map[message] || message;
};
</script>
