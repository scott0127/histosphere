<template>
  <div class="h-full flex flex-col bg-history-paper border-l-4 border-history-brown/20 shadow-xl relative overflow-hidden">
    <!-- Header -->
    <div class="p-4 bg-history-brown/10 border-b border-history-brown/20 flex justify-between items-center shrink-0">
      <h3 class="font-bold text-history-dark text-lg flex items-center gap-2">
        <Icon name="mdi:account-group" class="w-6 h-6" />
        歷史人物名錄
      </h3>
      <div class="text-xs text-history-brown/60 italic">
        共 {{ personas.length }} 位人物
      </div>
    </div>

    <!-- Active Speaker Notification (Popup) -->
    <Transition name="slide-fade">
      <div 
        v-if="showActiveNotification && activePersona" 
        class="absolute top-16 left-4 right-4 z-20 bg-history-accent text-history-paper p-3 rounded-lg shadow-lg border-2 border-history-dark flex items-center gap-3 animate-pulse-subtle"
      >
        <div class="w-10 h-10 rounded-full border-2 border-history-paper overflow-hidden shrink-0 bg-history-cream">
           <img 
             v-if="activePersona.avatar_url" 
             :src="activePersona.avatar_url" 
             class="w-full h-full object-cover"
           />
           <Icon v-else name="mdi:account" class="w-full h-full text-history-brown p-1" />
        </div>
        <div>
          <p class="font-bold text-sm">正在發言</p>
          <p class="text-lg font-bold leading-none">{{ activePersona.name }} 登場！</p>
        </div>
        <button @click="showActiveNotification = false" class="ml-auto text-history-paper/80 hover:text-white">
          <Icon name="mdi:close" class="w-5 h-5" />
        </button>
      </div>
    </Transition>

    <!-- List -->
    <div class="flex-1 overflow-y-auto p-4 space-y-4">
      <div 
        v-for="persona in personas" 
        :key="persona.id"
        :class="[
          'relative group rounded-xl border-2 transition-all duration-300 p-3 flex gap-3 items-start',
          activePersonaId === persona.id 
            ? 'bg-history-cream border-history-accent shadow-md scale-[1.02]' 
            : 'bg-white/50 border-history-brown/10 hover:border-history-brown/40 hover:bg-white/80'
        ]"
      >
        <!-- Avatar Section -->
        <div class="relative shrink-0">
          <div class="w-16 h-16 rounded-full border-2 border-history-brown/20 overflow-hidden bg-history-paper shadow-inner group-hover:shadow-md transition-shadow">
            <img 
              v-if="persona.avatar_url" 
              :src="persona.avatar_url" 
              :alt="persona.name"
              class="w-full h-full object-cover"
              @error="(e) => (e.target as HTMLImageElement).src = '/images/fallback_avatar.png'" 
            />
            <div v-else class="w-full h-full flex items-center justify-center bg-history-brown/10 text-history-brown">
              <Icon name="mdi:account" class="w-8 h-8" />
            </div>
          </div>
          
          <!-- Regenerate Button (Hidden by default, shown on hover) -->
          <button 
            @click.stop="confirmRegenerate(persona)"
            class="absolute -bottom-1 -right-1 w-7 h-7 bg-history-light text-history-brown rounded-full border border-history-brown shadow-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-history-accent hover:text-white hover:scale-110 z-10"
            title="重新生成頭像"
          >
            <Icon name="mdi:refresh" class="w-4 h-4" />
          </button>
        </div>

        <!-- Info Section -->
        <div class="flex-1 min-w-0">
          <div class="flex justify-between items-start">
            <h4 class="font-bold text-history-dark truncate">{{ persona.name }}</h4>
            <span v-if="activePersonaId === persona.id" class="text-xs font-bold text-history-accent px-2 py-0.5 bg-history-accent/10 rounded-full">
              當前
            </span>
          </div>
          <p class="text-xs text-history-brown/80 font-medium mb-1">{{ persona.role }}</p>
          <div class="flex flex-wrap gap-1">
            <span 
              v-for="area in persona.expertise_areas.slice(0, 2)" 
              :key="area"
              class="text-[10px] px-1.5 py-0.5 bg-history-brown/5 text-history-brown rounded border border-history-brown/10"
            >
              {{ area }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirmation Modal -->
    <div v-if="showConfirmDialog" class="absolute inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-[2px] p-4 animate-fade-in">
      <div class="bg-history-paper border-2 border-history-brown rounded-lg shadow-2xl w-full max-w-sm p-6 relative">
        <h4 class="text-xl font-bold text-history-dark mb-2 flex items-center gap-2">
          <Icon name="mdi:alert-decagram" class="text-red-600" />
          確認重繪？
        </h4>
        <p class="text-sm text-history-brown mb-6 leading-relaxed">
          您即將為 <span class="font-bold text-history-dark">{{ pendingPersona?.name }}</span> 重新繪製肖像。<br>
          這將會覆蓋原本的畫像且無法復原。
        </p>
        
        <div class="flex gap-3 justify-end">
          <button 
            @click="showConfirmDialog = false" 
            class="px-4 py-2 text-sm font-bold text-history-brown hover:bg-history-brown/10 rounded transition-colors"
          >
            取消
          </button>
          <button 
            @click="executeRegenerate" 
            class="px-4 py-2 text-sm font-bold bg-history-dark text-history-paper rounded hover:bg-history-brown transition-colors flex items-center gap-2"
            :disabled="isRegenerating"
          >
            <Icon v-if="isRegenerating" name="mdi:loading" class="animate-spin" />
            {{ isRegenerating ? '繪製中...' : '確認重繪' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import type { Persona } from '~/types';

const props = defineProps<{
  personas: Persona[];
  activePersonaId?: string;
}>();

const emit = defineEmits<{
  (e: 'update-persona', persona: Persona): void;
}>();

// State
const showActiveNotification = ref(false);
const showConfirmDialog = ref(false);
const pendingPersona = ref<Persona | null>(null);
const isRegenerating = ref(false);

// Computed
const activePersona = computed(() => 
  props.personas.find(p => p.id === props.activePersonaId)
);

// Watch for active persona change to trigger notification
watch(() => props.activePersonaId, (newId, oldId) => {
  if (newId && newId !== oldId) {
    showActiveNotification.value = true;
    // Auto hide after 3 seconds
    setTimeout(() => {
      showActiveNotification.value = false;
    }, 3000);
  }
});

// Actions
const confirmRegenerate = (persona: Persona) => {
  pendingPersona.value = persona;
  showConfirmDialog.value = true;
};

const executeRegenerate = async () => {
  if (!pendingPersona.value) return;
  
  isRegenerating.value = true;
  try {
    const response = await $fetch<{ avatar_url: string; success: boolean }>(
      `/api/personas/${pendingPersona.value.id}/regenerate_avatar`,
      { method: 'POST' }
    );

    if (response.success && response.avatar_url) {
      // Emit update to parent to update the list locally
      const updatedPersona = { ...pendingPersona.value, avatar_url: response.avatar_url };
      emit('update-persona', updatedPersona);
    }
  } catch (e) {
    console.error('Failed to regenerate avatar:', e);
    alert('重繪失敗，請稍後再試。');
  } finally {
    isRegenerating.value = false;
    showConfirmDialog.value = false;
    pendingPersona.value = null;
  }
};
</script>

<style scoped>
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}
.slide-fade-leave-active {
  transition: all 0.3s cubic-bezier(1, 0.5, 0.8, 1);
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-20px);
  opacity: 0;
}

@keyframes pulse-subtle {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02); }
}
.animate-pulse-subtle {
  animation: pulse-subtle 2s infinite;
}

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(121, 85, 72, 0.2);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(121, 85, 72, 0.4);
}
</style>
