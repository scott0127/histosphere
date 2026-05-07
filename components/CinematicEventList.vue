<template>
  <div class="absolute inset-0 z-40 bg-[#0a0908]/90 backdrop-blur-md pt-20 pb-10 px-4 md:px-8 overflow-y-auto scrollbar-thin scrollbar-thumb-amber-600/50 scrollbar-track-transparent animate-fade-in">
    
    <!-- Header Title for List View -->
    <div class="max-w-7xl mx-auto mb-8 flex justify-between items-end border-b border-white/10 pb-4">
      <div>
        <h2 class="text-3xl md:text-4xl text-amber-50 font-serif tracking-widest mb-2" style="font-family: 'Cormorant Garamond', serif;">
          ARCHIVES
        </h2>
        <p class="text-amber-400/60 text-sm tracking-wider uppercase">已記錄的歷史篇章</p>
      </div>
      <div class="text-white/30 text-xs font-mono">
        TOTAL: {{ events.length }}
      </div>
    </div>

    <!-- Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-7xl mx-auto pb-20">
      <div 
        v-for="event in events" 
        :key="event.id"
        class="group relative transition-all duration-500 hover:-translate-y-2 cursor-pointer rounded-xl overflow-hidden border border-white/10 hover:border-amber-500/50 hover:shadow-[0_0_30px_rgba(245,158,11,0.1)] bg-white/5"
        @click="toggleExpand(event.id)"
      >
        <!-- Background Overlay -->
        <div class="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

        <!-- Card Header -->
        <div class="p-6 relative z-10">
            <!-- Type Icon Watermark -->
            <div class="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity transform group-hover:scale-110 duration-700">
               <Icon 
                 :name="event.type === 'legend' ? 'mdi:unicorn-variant' : 'mdi:feather'" 
                 class="w-32 h-32 text-white" 
               />
            </div>
          
            <!-- Delete Button -->
            <button 
              @click.stop="$emit('delete-event', event.id)"
              class="absolute top-4 right-4 text-white/20 hover:text-red-400 rounded-full transition-all opacity-0 group-hover:opacity-100 z-20 transform hover:scale-110"
              title="刪除此歷史事件"
            >
              <Icon name="mdi:trash-can-outline" class="w-5 h-5" />
            </button>

            <!-- Tags -->
            <div class="flex flex-wrap gap-2 mb-4 relative z-10">
              <span class="px-3 py-1 bg-amber-900/40 border border-amber-500/30 text-amber-200 text-xs font-bold rounded-full uppercase tracking-wider backdrop-blur-sm">
                {{ event.century }} 世紀
              </span>
              <span 
                v-if="event.type === 'legend'"
                class="px-3 py-1 bg-purple-900/40 border border-purple-500/30 text-purple-200 text-xs font-bold rounded-full uppercase tracking-wider flex items-center gap-1 backdrop-blur-sm"
              >
                <Icon name="mdi:auto-fix" class="w-3 h-3" />
                非正史
              </span>
            </div>
            
            <p class="text-amber-400/40 text-xs font-serif italic mb-2 tracking-wide">
              {{ event.time_period }}
            </p>
          
            <h3 class="text-2xl font-light text-white mb-3 font-serif group-hover:text-amber-400 transition-colors tracking-wide leading-tight">
              {{ event.name }}
            </h3>
          
            <div class="flex items-center gap-2 text-white/40 text-sm mb-4">
              <Icon name="mdi:map-marker" class="w-4 h-4" />
              {{ event.geographic_location }}
            </div>
          
            <p class="text-white/60 text-sm line-clamp-3 font-serif leading-relaxed border-l-2 border-amber-500/20 pl-3">
              {{ event.description || event.context.substring(0, 100) + '...' }}
            </p>
        </div>

        <!-- Expanded Content -->
        <div 
          v-if="expandedId === event.id"
          class="bg-black/40 border-t border-white/10 p-6 animate-fade-in backdrop-blur-xl relative z-20"
        >
          <h4 class="text-xs font-bold text-amber-500/70 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
            <Icon name="mdi:account-group" /> Personas
          </h4>
          
          <div class="space-y-3 mb-6">
              <div 
                v-for="persona in event.personas" 
                :key="persona.id"
                class="flex items-center gap-4 p-2 rounded-lg hover:bg-white/5 transition-colors border border-transparent hover:border-white/5"
              >
                <div class="w-10 h-10 flex-shrink-0 rounded-full bg-amber-900/30 text-amber-500 border border-amber-500/30 flex items-center justify-center overflow-hidden">
                  <img 
                    v-if="persona.avatar_url" 
                    :src="persona.avatar_url" 
                    class="w-full h-full object-cover opacity-80"
                    @error="(e) => (e.target as HTMLImageElement).style.display = 'none'"
                  />
                  <Icon v-else name="mdi:account" class="w-5 h-5" />
                </div>
                <div class="min-w-0"> 
                    <p class="text-amber-100 text-sm font-serif tracking-wide truncate">{{ persona.name }}</p>
                    <p class="text-xs text-white/30 italic truncate">{{ persona.role }}</p>
                </div>
              </div>
          </div>

          <button 
            @click.stop="enterStory(event)"
            class="w-full py-4 bg-gradient-to-r from-amber-700/80 to-amber-900/80 hover:from-amber-600 hover:to-amber-800 text-white font-bold rounded-lg border border-amber-500/30 shadow-lg tracking-[0.2em] text-xs transition-all flex items-center justify-center gap-2 group/btn"
          >
            <span class="opacity-0 group-hover/btn:opacity-100 transition-opacity duration-300 mr-[-10px] group-hover/btn:mr-0">⚡</span>
            開始旅程
          </button>
        </div>

        <!-- Expand Hint -->
        <div 
          v-else 
          class="bg-black/20 py-3 text-center text-white/20 text-[10px] font-bold uppercase tracking-[0.3em] group-hover:bg-white/5 group-hover:text-amber-400/50 transition-colors border-t border-white/5"
        >
          View Details
        </div>
      </div>
    </div>
    
    <!-- Empty State -->
    <div v-if="events.length === 0" class="flex flex-col items-center justify-center h-[60vh] text-white/20">
         <Icon name="mdi:history" class="w-24 h-24 mb-4 opacity-20" />
         <p class="tracking-[0.2em] font-light">NO RECORDS FOUND</p>
    </div>

    <!-- Legend Confirmation (Cinematic Style) -->
    <div v-if="showConfirmation" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/90 backdrop-blur-lg" @click="closeConfirmation"></div>
        <div class="relative bg-[#1a1510] border border-amber-500/30 p-8 rounded-2xl max-w-md w-full text-center shadow-[0_0_50px_rgba(245,158,11,0.1)]">
            <div class="w-20 h-20 mx-auto bg-purple-900/20 rounded-full flex items-center justify-center mb-6 border border-purple-500/30 text-purple-400">
               <Icon name="mdi:unicorn-variant" class="w-10 h-10" />
            </div>
            <h3 class="text-2xl text-white font-serif mb-4 tracking-wide">非正史確認</h3>
            <p class="text-white/50 text-sm leading-relaxed mb-8">
               您選擇的<span class="text-purple-400 mx-1">「{{ pendingEvent?.name }}」</span>屬於民間傳說或文學作品。<br>歷史準確性可能有所偏差。
            </p>
            <div class="flex gap-4">
               <button @click="closeConfirmation" class="flex-1 py-3 px-4 border border-white/10 rounded-lg text-white/50 hover:bg-white/5 transition-colors text-sm tracking-wider">取消</button>
               <button @click="confirmEnterStory" class="flex-1 py-3 px-4 bg-purple-900/50 border border-purple-500/50 rounded-lg text-purple-100 hover:bg-purple-800/50 transition-colors text-sm tracking-wider shadow-[0_0_20px_rgba(168,85,247,0.2)]">進入傳說</button>
            </div>
        </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import type { HistoricalEvent, Persona } from '~/types';

interface EventWithPersonas extends HistoricalEvent {
  personas: Persona[];
}

const props = defineProps<{
  events: EventWithPersonas[];
}>();

const emit = defineEmits<{
  (e: 'enter-story', event: EventWithPersonas): void;
  (e: 'delete-event', eventId: string): void;
}>();

const expandedId = ref<string | null>(null);
const showConfirmation = ref(false);
const pendingEvent = ref<EventWithPersonas | null>(null);

const toggleExpand = (id: string) => {
  expandedId.value = expandedId.value === id ? null : id;
};

const enterStory = (event: EventWithPersonas) => {
  if (event.type === 'legend') {
    pendingEvent.value = event;
    showConfirmation.value = true;
  } else {
    emit('enter-story', event);
  }
};

const confirmEnterStory = () => {
  if (pendingEvent.value) {
    emit('enter-story', pendingEvent.value);
    closeConfirmation();
  }
};

const closeConfirmation = () => {
  showConfirmation.value = false;
  pendingEvent.value = null;
};
</script>

<style scoped>
.scrollbar-thin::-webkit-scrollbar { width: 6px; }
.scrollbar-thin::-webkit-scrollbar-track { background: transparent; }
.scrollbar-thin::-webkit-scrollbar-thumb { background: rgba(245, 158, 11, 0.2); border-radius: 10px; }
.scrollbar-thin::-webkit-scrollbar-thumb:hover { background: rgba(245, 158, 11, 0.4); }

@keyframes fade-in {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in { animation: fade-in 0.5s ease-out forwards; }
</style>
