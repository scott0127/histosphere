<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-history-paper bg-paper-pattern">
    <!-- 背景紋理遮罩 -->
    <div class="absolute inset-0 bg-gradient-to-br from-history-brown/5 to-history-accent/5 pointer-events-none"></div>
    
    <!-- 註冊卡片 -->
    <div class="relative z-10 w-full max-w-md mx-4 p-8 bg-white/90 backdrop-blur-sm rounded-2xl shadow-2xl border border-history-brown/20">
      <!-- Logo & 標題 -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-history-accent/10 mb-4">
          <Icon name="mdi:account-plus" class="w-8 h-8 text-history-accent" />
        </div>
        <h1 class="text-2xl font-bold text-history-dark tracking-wide">建立帳號</h1>
        <p class="text-history-brown/70 text-sm mt-1">開始你的歷史探索之旅</p>
      </div>

      <!-- 表單 -->
      <form @submit.prevent="handleRegister" class="space-y-5">
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
              placeholder="至少 6 個字元"
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
        </div>

        <!-- Confirm Password -->
        <div>
          <label class="block text-sm font-medium text-history-dark mb-1.5">確認密碼</label>
          <div class="relative">
            <Icon name="mdi:lock-check-outline" class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-history-brown/50" />
            <input
              v-model="confirmPassword"
              :type="showPassword ? 'text' : 'password'"
              required
              minlength="6"
              placeholder="再次輸入密碼"
              class="w-full pl-10 pr-4 py-3 rounded-lg border border-history-brown/30 focus:border-history-accent focus:ring-2 focus:ring-history-accent/20 outline-none transition-all bg-white/80"
            />
          </div>
          <p v-if="password && confirmPassword && password !== confirmPassword" class="text-red-500 text-xs mt-1">
            密碼不一致
          </p>
        </div>

        <!-- Error Message -->
        <div v-if="errorMessage" class="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
          {{ errorMessage }}
        </div>

        <!-- Success Message -->
        <div v-if="successMessage" class="p-3 bg-green-50 border border-green-200 rounded-lg text-green-600 text-sm">
          {{ successMessage }}
        </div>

        <!-- Submit Button -->
        <button
          type="submit"
          :disabled="isLoading || (password !== confirmPassword)"
          class="w-full py-3 px-4 bg-history-accent hover:bg-history-accent/90 text-white font-medium rounded-lg transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Icon v-if="isLoading" name="mdi:loading" class="w-5 h-5 animate-spin" />
          <span>{{ isLoading ? '註冊中...' : '建立帳號' }}</span>
        </button>
      </form>

      <!-- 登入連結 -->
      <p class="text-center text-sm text-history-brown/70 mt-6">
        已經有帳號？
        <NuxtLink to="/auth/login" class="text-history-accent hover:underline font-medium">
          立即登入
        </NuxtLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
const { signUp } = useAuth()
const router = useRouter()

const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

async function handleRegister() {
  errorMessage.value = ''
  successMessage.value = ''

  if (password.value !== confirmPassword.value) {
    errorMessage.value = '密碼不一致'
    return
  }

  isLoading.value = true

  const result = await signUp(email.value, password.value)

  if (result.success) {
    if (result.needsVerification) {
      successMessage.value = '註冊成功！請查收驗證郵件後再登入。'
    } else {
      // 自動登入成功，跳轉回首頁
      router.push('/')
    }
  } else {
    errorMessage.value = translateError(result.error || '註冊失敗')
  }

  isLoading.value = false
}

function translateError(error: string): string {
  const errors: Record<string, string> = {
    'User already registered': '此電子郵件已註冊',
    'Password should be at least 6 characters': '密碼至少需要 6 個字元',
    'Unable to validate email address: invalid format': '電子郵件格式無效',
  }
  return errors[error] || error
}
</script>
