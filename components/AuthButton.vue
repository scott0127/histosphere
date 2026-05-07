<template>
  <!-- Auth Button - 依據 variant 調整外觀 -->
  <div :class="wrapperClass">
    <template v-if="isAuthenticated">
      <div class="relative group flex items-center gap-1">
        <!-- 個人資料按鈕 -->
        <NuxtLink
          to="/profile"
          :class="buttonClass"
        >
          <Icon name="mdi:account-circle-outline" class="w-3.5 h-3.5" />
          {{ displayName || '使用者' }}
        </NuxtLink>
        
        <!-- 登出按鈕 -->
        <button
          @click="handleSignOut"
          :class="buttonClass"
          title="登出"
        >
          <Icon name="mdi:logout" class="w-3.5 h-3.5" />
        </button>
        
        <!-- Email tooltip on hover -->
        <div class="absolute top-full right-0 mt-2 px-3 py-2 bg-history-dark text-history-paper text-xs rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
          {{ user?.email }}
        </div>
      </div>
    </template>
    <template v-else>
      <NuxtLink
        to="/auth/login"
        :class="buttonClass"
      >
        <Icon name="mdi:account" class="w-3.5 h-3.5" />
        登入
      </NuxtLink>
    </template>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  variant?: 'leather' | 'classic'
}>(), {
  variant: 'leather'
});

const { user, displayName, isAuthenticated, signOut, initialize: initAuth } = useAuth();

const emit = defineEmits<{
  signedOut: []
}>();

// 依據 variant 決定樣式
const wrapperClass = computed(() => {
  if (props.variant === 'leather') {
    // Book UI style - 深色皮革背景
    return 'hidden lg:flex p-1 rounded-full border-2 border-history-brown/30 shadow-sm gap-0.5';
  } else {
    // Classic UI style - 淺色紙張背景
    return 'hidden lg:flex bg-[#F5E6D3] border border-history-dark/20 rounded-full p-1 shadow-inner';
  }
});

const buttonClass = computed(() => {
  return 'px-3 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 text-history-brown hover:bg-history-brown/5';
});

// 初始化認證狀態
onMounted(async () => {
  await initAuth();
});

const handleSignOut = async () => {
  await signOut();
  emit('signedOut');
};
</script>
