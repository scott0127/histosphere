<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-history-paper bg-paper-pattern">
    <!-- 背景紋理遮罩 -->
    <div class="absolute inset-0 bg-gradient-to-br from-history-brown/5 to-history-accent/5 pointer-events-none"></div>
    
    <!-- 忘記密碼卡片 -->
    <div class="relative z-10 w-full max-w-md mx-4 p-8 bg-white/90 backdrop-blur-sm rounded-2xl shadow-2xl border border-history-brown/20">
      <!-- Logo & 標題 -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-history-accent/10 mb-4">
          <Icon name="mdi:lock-reset" class="w-8 h-8 text-history-accent" />
        </div>
        <h1 class="text-2xl font-bold text-history-dark tracking-wide">忘記密碼</h1>
        <p class="text-history-brown/70 text-sm mt-1">輸入您的電子郵件，我們將寄送重設連結</p>
      </div>

      <!-- 成功訊息 -->
      <div v-if="isSuccess" class="text-center">
        <div class="inline-flex items-center justify-center w-20 h-20 rounded-full bg-emerald-100 mb-4">
          <Icon name="mdi:email-check-outline" class="w-10 h-10 text-emerald-600" />
        </div>
        <h2 class="text-xl font-bold text-history-dark mb-2">郵件已發送！</h2>
        <p class="text-history-brown/70 mb-6">
          請檢查您的信箱 <span class="font-medium text-history-dark">{{ email }}</span>，
          點擊連結重設密碼。
        </p>
        <NuxtLink
          to="/auth/login"
          class="inline-flex items-center gap-2 text-history-accent hover:underline font-medium"
        >
          <Icon name="mdi:arrow-left" class="w-4 h-4" />
          返回登入
        </NuxtLink>
      </div>

      <!-- 表單 -->
      <form v-else @submit.prevent="handleSubmit" class="space-y-5">
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
          <span>{{ isLoading ? '發送中...' : '發送重設連結' }}</span>
        </button>

        <!-- 返回登入 -->
        <p class="text-center text-sm text-history-brown/70 mt-6">
          想起密碼了？
          <NuxtLink to="/auth/login" class="text-history-accent hover:underline font-medium">
            返回登入
          </NuxtLink>
        </p>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
const { resetPasswordForEmail } = useAuth()

const email = ref('')
const isLoading = ref(false)
const isSuccess = ref(false)
const errorMessage = ref('')

async function handleSubmit() {
  errorMessage.value = ''
  isLoading.value = true

  const result = await resetPasswordForEmail(email.value)

  if (result.success) {
    isSuccess.value = true
  } else {
    errorMessage.value = translateError(result.error || '發送失敗')
  }

  isLoading.value = false
}

function translateError(error: string): string {
  const errors: Record<string, string> = {
    'User not found': '找不到此電子郵件',
    'Too many requests': '請求過於頻繁，請稍後再試',
    'For security purposes, you can only request this once every 60 seconds': '請等待 60 秒後再試',
  }
  return errors[error] || error
}
</script>
