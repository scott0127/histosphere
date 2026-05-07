<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-history-paper bg-paper-pattern py-12 px-4">
    <!-- 背景紋理遮罩 -->
    <div class="absolute inset-0 bg-gradient-to-br from-history-brown/5 to-history-accent/5 pointer-events-none"></div>
    
    <!-- 個人資料卡片 -->
    <div class="relative z-10 w-full max-w-lg p-8 bg-white/90 backdrop-blur-sm rounded-2xl shadow-2xl border border-history-brown/20">
      <!-- Header -->
      <div class="flex items-center justify-between mb-8">
        <div class="flex items-center gap-4">
          <!-- Avatar -->
          <div class="w-16 h-16 rounded-full bg-history-accent/10 flex items-center justify-center">
            <Icon name="mdi:account-circle-outline" class="w-10 h-10 text-history-accent" />
          </div>
          <div>
            <h1 class="text-2xl font-bold text-history-dark tracking-wide">個人資料</h1>
            <p class="text-history-brown/70 text-sm">{{ user?.email }}</p>
          </div>
        </div>
        <!-- Back Button -->
        <NuxtLink 
          to="/" 
          class="p-2 rounded-full text-history-brown/50 hover:bg-history-brown/10 hover:text-history-dark transition-all"
        >
          <Icon name="mdi:close" class="w-6 h-6" />
        </NuxtLink>
      </div>

      <!-- Success Message -->
      <div v-if="successMessage" class="mb-6 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700 text-sm flex items-center gap-2">
        <Icon name="mdi:check-circle" class="w-5 h-5" />
        {{ successMessage }}
      </div>

      <!-- Profile Form -->
      <form @submit.prevent="handleUpdateProfile" class="space-y-6">
        <div class="border-b border-history-brown/10 pb-6">
          <h2 class="text-lg font-bold text-history-dark mb-4 flex items-center gap-2">
            <Icon name="mdi:account-edit-outline" class="w-5 h-5 text-history-accent" />
            基本資料
          </h2>
          
          <!-- Display Name -->
          <div>
            <label class="block text-sm font-medium text-history-dark mb-1.5">顯示名稱</label>
            <div class="relative">
              <Icon name="mdi:badge-account-outline" class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-history-brown/50" />
              <input
                v-model="displayNameInput"
                type="text"
                required
                placeholder="您的顯示名稱"
                class="w-full pl-10 pr-4 py-3 rounded-lg border border-history-brown/30 focus:border-history-accent focus:ring-2 focus:ring-history-accent/20 outline-none transition-all bg-white/80"
              />
            </div>
            <p class="text-history-brown/50 text-xs mt-1.5">此名稱將顯示在系統中</p>
          </div>
        </div>

        <!-- Error Message -->
        <div v-if="profileError" class="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
          {{ profileError }}
        </div>

        <!-- Save Button -->
        <button
          type="submit"
          :disabled="isUpdatingProfile || displayNameInput === displayName"
          class="w-full py-3 px-4 bg-history-accent hover:bg-history-accent/90 text-white font-medium rounded-lg transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Icon v-if="isUpdatingProfile" name="mdi:loading" class="w-5 h-5 animate-spin" />
          <span>{{ isUpdatingProfile ? '儲存中...' : '儲存變更' }}</span>
        </button>
      </form>

      <!-- Password Section -->
      <div class="mt-8 pt-6 border-t border-history-brown/10">
        <h2 class="text-lg font-bold text-history-dark mb-4 flex items-center gap-2">
          <Icon name="mdi:lock-outline" class="w-5 h-5 text-history-accent" />
          變更密碼
        </h2>
        
        <form @submit.prevent="handleUpdatePassword" class="space-y-4">
          <!-- New Password -->
          <div>
            <label class="block text-sm font-medium text-history-dark mb-1.5">新密碼</label>
            <div class="relative">
              <Icon name="mdi:lock-outline" class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-history-brown/50" />
              <input
                v-model="newPassword"
                :type="showNewPassword ? 'text' : 'password'"
                minlength="6"
                placeholder="至少 6 個字元"
                class="w-full pl-10 pr-12 py-3 rounded-lg border border-history-brown/30 focus:border-history-accent focus:ring-2 focus:ring-history-accent/20 outline-none transition-all bg-white/80"
              />
              <button 
                type="button" 
                @click="showNewPassword = !showNewPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-history-brown/50 hover:text-history-accent transition-colors"
              >
                <Icon :name="showNewPassword ? 'mdi:eye-off' : 'mdi:eye'" class="w-5 h-5" />
              </button>
            </div>
          </div>

          <!-- Confirm Password -->
          <div>
            <label class="block text-sm font-medium text-history-dark mb-1.5">確認密碼</label>
            <div class="relative">
              <Icon name="mdi:lock-check-outline" class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-history-brown/50" />
              <input
                v-model="confirmNewPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                minlength="6"
                placeholder="再次輸入新密碼"
                class="w-full pl-10 pr-12 py-3 rounded-lg border border-history-brown/30 focus:border-history-accent focus:ring-2 focus:ring-history-accent/20 outline-none transition-all bg-white/80"
                :class="{ 'border-red-300 focus:border-red-400': confirmNewPassword && newPassword !== confirmNewPassword }"
              />
              <button 
                type="button" 
                @click="showConfirmPassword = !showConfirmPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-history-brown/50 hover:text-history-accent transition-colors"
              >
                <Icon :name="showConfirmPassword ? 'mdi:eye-off' : 'mdi:eye'" class="w-5 h-5" />
              </button>
            </div>
            <p v-if="confirmNewPassword && newPassword !== confirmNewPassword" class="text-red-500 text-sm mt-1">
              密碼不一致
            </p>
          </div>

          <!-- Password Error -->
          <div v-if="passwordError" class="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
            {{ passwordError }}
          </div>

          <!-- Update Password Button -->
          <button
            type="submit"
            :disabled="isUpdatingPassword || !newPassword || newPassword !== confirmNewPassword"
            class="w-full py-3 px-4 border border-history-brown/30 text-history-brown hover:bg-history-brown/5 font-medium rounded-lg transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Icon v-if="isUpdatingPassword" name="mdi:loading" class="w-5 h-5 animate-spin" />
            <span>{{ isUpdatingPassword ? '更新中...' : '更新密碼' }}</span>
          </button>
        </form>
      </div>

      <!-- Logout Section -->
      <div class="mt-8 pt-6 border-t border-history-brown/10">
        <button
          @click="handleSignOut"
          class="w-full py-3 px-4 text-red-600 hover:bg-red-50 font-medium rounded-lg transition-all duration-200 flex items-center justify-center gap-2"
        >
          <Icon name="mdi:logout" class="w-5 h-5" />
          登出帳號
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const router = useRouter()
const { user, displayName, updateProfile, updatePassword, signOut, initialize } = useAuth()

// Form state
const displayNameInput = ref('')
const newPassword = ref('')
const confirmNewPassword = ref('')
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)

// Loading states
const isUpdatingProfile = ref(false)
const isUpdatingPassword = ref(false)

// Message states
const successMessage = ref('')
const profileError = ref('')
const passwordError = ref('')

// 初始化
onMounted(async () => {
  await initialize()
  
  // 如果未登入，導向登入頁
  if (!user.value) {
    router.push('/auth/login')
    return
  }
  
  // 設定初始值
  displayNameInput.value = displayName.value || ''
})

// 監聽 displayName 變化
watch(displayName, (newName) => {
  if (newName && !displayNameInput.value) {
    displayNameInput.value = newName
  }
})

async function handleUpdateProfile() {
  profileError.value = ''
  successMessage.value = ''
  isUpdatingProfile.value = true

  const result = await updateProfile(displayNameInput.value)

  if (result.success) {
    successMessage.value = '資料已更新'
    setTimeout(() => { successMessage.value = '' }, 3000)
  } else {
    profileError.value = result.error || '更新失敗'
  }

  isUpdatingProfile.value = false
}

async function handleUpdatePassword() {
  if (newPassword.value !== confirmNewPassword.value) {
    passwordError.value = '密碼不一致'
    return
  }

  passwordError.value = ''
  successMessage.value = ''
  isUpdatingPassword.value = true

  const result = await updatePassword(newPassword.value)

  if (result.success) {
    successMessage.value = '密碼已更新'
    newPassword.value = ''
    confirmNewPassword.value = ''
    setTimeout(() => { successMessage.value = '' }, 3000)
  } else {
    passwordError.value = result.error || '更新失敗'
  }

  isUpdatingPassword.value = false
}

async function handleSignOut() {
  await signOut()
  router.push('/')
}
</script>
