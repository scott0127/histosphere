<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-history-paper bg-paper-pattern">
    <!-- 背景紋理遮罩 -->
    <div class="absolute inset-0 bg-gradient-to-br from-history-brown/5 to-history-accent/5 pointer-events-none"></div>
    
    <!-- 重設密碼卡片 -->
    <div class="relative z-10 w-full max-w-md mx-4 p-8 bg-white/90 backdrop-blur-sm rounded-2xl shadow-2xl border border-history-brown/20">
      <!-- Logo & 標題 -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-history-accent/10 mb-4">
          <Icon name="mdi:lock-check-outline" class="w-8 h-8 text-history-accent" />
        </div>
        <h1 class="text-2xl font-bold text-history-dark tracking-wide">重設密碼</h1>
        <p class="text-history-brown/70 text-sm mt-1">請設定您的新密碼</p>
      </div>

      <!-- 成功訊息 -->
      <div v-if="isSuccess" class="text-center">
        <div class="inline-flex items-center justify-center w-20 h-20 rounded-full bg-emerald-100 mb-4">
          <Icon name="mdi:check-circle-outline" class="w-10 h-10 text-emerald-600" />
        </div>
        <h2 class="text-xl font-bold text-history-dark mb-2">密碼已更新！</h2>
        <p class="text-history-brown/70 mb-6">
          您的密碼已成功重設，現在可以使用新密碼登入。
        </p>
        <NuxtLink
          to="/auth/login"
          class="w-full py-3 px-4 bg-history-accent hover:bg-history-accent/90 text-white font-medium rounded-lg transition-all duration-200 inline-flex items-center justify-center gap-2"
        >
          <Icon name="mdi:login" class="w-5 h-5" />
          前往登入
        </NuxtLink>
      </div>

      <!-- 表單 -->
      <form v-else @submit.prevent="handleSubmit" class="space-y-5">
        <!-- New Password -->
        <div>
          <label class="block text-sm font-medium text-history-dark mb-1.5">新密碼</label>
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
              :type="showConfirmPassword ? 'text' : 'password'"
              required
              minlength="6"
              placeholder="再次輸入密碼"
              class="w-full pl-10 pr-12 py-3 rounded-lg border border-history-brown/30 focus:border-history-accent focus:ring-2 focus:ring-history-accent/20 outline-none transition-all bg-white/80"
              :class="{ 'border-red-300 focus:border-red-400': confirmPassword && password !== confirmPassword }"
            />
            <button 
              type="button" 
              @click="showConfirmPassword = !showConfirmPassword"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-history-brown/50 hover:text-history-accent transition-colors"
            >
              <Icon :name="showConfirmPassword ? 'mdi:eye-off' : 'mdi:eye'" class="w-5 h-5" />
            </button>
          </div>
          <p v-if="confirmPassword && password !== confirmPassword" class="text-red-500 text-sm mt-1">
            密碼不一致
          </p>
        </div>

        <!-- Error Message -->
        <div v-if="errorMessage" class="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
          {{ errorMessage }}
        </div>

        <!-- Submit Button -->
        <button
          type="submit"
          :disabled="isLoading || password !== confirmPassword"
          class="w-full py-3 px-4 bg-history-accent hover:bg-history-accent/90 text-white font-medium rounded-lg transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Icon v-if="isLoading" name="mdi:loading" class="w-5 h-5 animate-spin" />
          <span>{{ isLoading ? '更新中...' : '更新密碼' }}</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
const { updatePassword, initialize } = useAuth()

const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const isLoading = ref(false)
const isSuccess = ref(false)
const errorMessage = ref('')

// 頁面載入時初始化 auth 狀態 (處理從 email 連結進入的情況)
onMounted(async () => {
  await initialize()
})

async function handleSubmit() {
  if (password.value !== confirmPassword.value) {
    errorMessage.value = '密碼不一致'
    return
  }

  errorMessage.value = ''
  isLoading.value = true

  const result = await updatePassword(password.value)

  if (result.success) {
    isSuccess.value = true
  } else {
    errorMessage.value = translateError(result.error || '更新失敗')
  }

  isLoading.value = false
}

function translateError(error: string): string {
  const errors: Record<string, string> = {
    'New password should be different from the old password': '新密碼不能與舊密碼相同',
    'Password should be at least 6 characters': '密碼至少需要 6 個字元',
    'Auth session missing!': '認證已過期，請重新申請密碼重設',
  }
  return errors[error] || error
}
</script>
