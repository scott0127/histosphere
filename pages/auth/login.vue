<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-history-paper bg-paper-pattern">
    <!-- 背景紋理遮罩 -->
    <div class="absolute inset-0 bg-gradient-to-br from-history-brown/5 to-history-accent/5 pointer-events-none"></div>
    
    <!-- 登入卡片 -->
    <div class="relative z-10 w-full max-w-md mx-4 p-8 bg-white/90 backdrop-blur-sm rounded-2xl shadow-2xl border border-history-brown/20">
      <!-- Logo & 標題 -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-history-accent/10 mb-4">
          <Icon name="mdi:bank" class="w-8 h-8 text-history-accent" />
        </div>
        <h1 class="text-2xl font-bold text-history-dark tracking-wide">HISTOSPHERE</h1>
        <p class="text-history-brown/70 text-sm mt-1">探索歷史 · 對話古人</p>
      </div>

      <!-- 表單 -->
      <form @submit.prevent="handleLogin" class="space-y-5">
        <!-- Email -->
        <div>
          <label class="block text-sm font-medium text-history-dark mb-1.5">電子郵件</label>
          <div class="relative">
            <Icon name="mdi:email-outline" class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-history-brown/50" />
            <input
              v-model="email"
              type="email"
              required
              placeholder="your@email.com"
              class="w-full pl-10 pr-4 py-3 rounded-lg border border-history-brown/30 focus:border-history-accent focus:ring-2 focus:ring-history-accent/20 outline-none transition-all bg-white/80"
            />
          </div>
        </div>

        <!-- Password -->
        <div>
          <label class="block text-sm font-medium text-history-dark mb-1.5">密碼</label>
          <div class="relative">
            <Icon name="mdi:lock-outline" class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-history-brown/50" />
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              required
              minlength="6"
              placeholder="••••••••"
              class="w-full pl-10 pr-12 py-3 rounded-lg border border-history-brown/30 focus:border-history-accent focus:ring-2 focus:ring-history-accent/20 outline-none transition-all bg-white/80"
            />
            <button 
              type="button" 
              @click="showPassword = !showPassword"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-history-brown/50 hover:text-history-accent transition-colors"
            >
              <Icon :name="showPassword ? 'mdi:eye-off' : 'mdi:eye'" class="w-5 h-5" />
            </button>
          </div>
          <!-- 忘記密碼連結 -->
          <div class="flex justify-end mt-1.5">
            <NuxtLink to="/auth/forgot-password" class="text-sm text-history-accent hover:underline">
              忘記密碼？
            </NuxtLink>
          </div>
        </div>

        <!-- Error Message -->
        <div v-if="errorMessage" class="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
          {{ errorMessage }}
        </div>

        <!-- Submit Button -->
        <button
          type="submit"
          :disabled="isLoading"
          class="w-full py-3 px-4 bg-history-accent hover:bg-history-accent/90 text-white font-medium rounded-lg transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Icon v-if="isLoading" name="mdi:loading" class="w-5 h-5 animate-spin" />
          <span>{{ isLoading ? '登入中...' : '登入' }}</span>
        </button>
      </form>

      <!-- Divider -->
      <div class="relative my-6">
        <div class="absolute inset-0 flex items-center">
          <div class="w-full border-t border-history-brown/20"></div>
        </div>
        <div class="relative flex justify-center text-sm">
          <span class="px-3 bg-white/90 text-history-brown/60">或</span>
        </div>
      </div>

      <!-- 訪客繼續 -->
      <NuxtLink
        to="/"
        class="w-full py-3 px-4 border border-history-brown/30 text-history-brown hover:bg-history-brown/5 font-medium rounded-lg transition-all duration-200 flex items-center justify-center gap-2"
      >
        <Icon name="mdi:incognito" class="w-5 h-5" />
        <span>以訪客身份繼續</span>
      </NuxtLink>

      <p class="mt-6 text-center text-sm text-history-brown/70">
        研究帳號由研究團隊統一提供
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
const { signIn, error: authError, loading: authLoading } = useAuth()
const router = useRouter()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const isLoading = ref(false)
const errorMessage = ref('')

async function handleLogin() {
  errorMessage.value = ''
  isLoading.value = true

  const result = await signIn(email.value, password.value)

  if (result.success) {
    // 登入成功，跳轉回首頁
    router.push('/')
  } else {
    errorMessage.value = translateError(result.error || '登入失敗')
  }

  isLoading.value = false
}

function translateError(error: string): string {
  const errors: Record<string, string> = {
    'Invalid login credentials': '電子郵件或密碼錯誤',
    'Email not confirmed': '請先驗證您的電子郵件',
    'Too many requests': '請求過於頻繁，請稍後再試',
  }
  return errors[error] || error
}
</script>
