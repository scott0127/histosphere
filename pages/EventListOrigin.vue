<template>
  <div class="w-full h-full overflow-y-auto p-4 md:p-8 scrollbar-thin scrollbar-thumb-history-brown scrollbar-track-history-light">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-7xl mx-auto">
      <div 
        v-for="event in events" 
        :key="event.id"
        class="group relative transition-all duration-300 hover:-translate-y-1 overflow-hidden cursor-pointer bg-white/80 backdrop-blur-sm border border-history-brown/10 rounded-xl shadow-sm md:bg-history-cream md:border-2 md:border-history-brown md:shadow-lg md:hover:shadow-2xl"
        @click="toggleExpand(event.id)"
      >
        <!-- Card Header -->
        <div class="p-4 md:p-6 bg-paper-pattern relative" :class="{ 'bg-purple-50': event.type === 'legend' }">
          <div class="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity z-0">
            <Icon 
              :name="event.type === 'legend' ? 'mdi:unicorn-variant' : 'mdi:feather'" 
              class="w-24 h-24 text-history-dark" 
            />
          </div>
          
            <!-- Delete Button - Absolute positioned -->
            <button 
              @click.stop="$emit('delete-event', event.id)"
              class="absolute top-2 right-2 p-1 text-history-brown/40 hover:text-red-600 hover:bg-red-50 rounded-full transition-all opacity-0 group-hover:opacity-100 z-20"
              title="刪除此歷史事件"
            >
              <Icon name="mdi:trash-can-outline" class="w-5 h-5" />
            </button>

            <!-- Tags Row -->
            <div class="flex flex-wrap gap-2 mb-2 pr-8">
              <span class="px-3 py-1 bg-history-brown text-history-paper text-xs font-bold rounded-full uppercase tracking-wider flex-shrink-0 whitespace-nowrap">
                {{ event.century }} 世紀
              </span>
              <!-- Legend Badge -->
              <span 
                v-if="event.type === 'legend'"
                class="px-3 py-1 bg-purple-600 text-white text-xs font-bold rounded-full uppercase tracking-wider flex-shrink-0 flex items-center gap-1"
                title="此為民間傳說或文學作品，非嚴謹歷史事件"
              >
                <Icon name="mdi:auto-fix" class="w-3 h-3" />
                非正史
              </span>
            </div>
            
            <!-- Time Period - Separate row -->
            <p class="text-history-brown/60 text-xs font-serif italic leading-relaxed mb-2">
              {{ event.time_period }}
            </p>
          
          <h3 class="text-xl md:text-2xl font-bold text-history-dark mb-2 font-serif group-hover:text-history-accent transition-colors">
            {{ event.name }}
          </h3>
          
          <div class="flex items-center gap-2 text-history-brown text-sm mb-4">
            <Icon name="mdi:map-marker" class="w-4 h-4" />
            {{ event.geographic_location }}
          </div>
          
          <p class="text-history-dark/80 text-sm line-clamp-3 font-serif leading-relaxed">
            {{ event.description || event.context.substring(0, 100) + '...' }}
          </p>
        </div>

        <!-- Expanded Content (Personas) -->
        <div 
          v-if="expandedId === event.id"
          class="bg-history-light border-t-2 border-history-brown/20 p-6 animate-fade-in"
        >
          <h4 class="text-sm font-bold text-history-brown uppercase tracking-wider mb-4 flex items-center gap-2">
            <Icon name="mdi:account-group" />
            歷史人物
          </h4>
          
          <div 
            v-for="persona in event.personas" 
            :key="persona.id"
            class="flex items-center gap-3 p-2 rounded hover:bg-history-cream transition-colors"
          >
            <div class="w-12 h-12 flex-shrink-0 rounded-full bg-history-brown text-history-paper flex items-center justify-center border border-history-dark overflow-hidden relative">
              <img 
                v-if="persona.avatar_url" 
                :src="persona.avatar_url" 
                :alt="persona.name"
                class="w-full h-full object-cover"
                @error="(e) => (e.target as HTMLImageElement).style.display = 'none'"
              />
              <Icon v-else name="mdi:account" class="w-8 h-8 opacity-80" />
            </div>
            
            <div class="min-w-0"> <p class="font-bold text-history-dark text-sm truncate">{{ persona.name }}</p>
              <p class="text-xs text-history-brown/80 italic truncate">{{ persona.role }}</p>
            </div>
          </div>

          <!-- Data Sources -->
          <div v-if="event.sources && event.sources.length > 0" class="mb-6">
            <h4 class="text-sm font-bold text-history-brown uppercase tracking-wider mb-2 flex items-center gap-2">
              <Icon name="mdi:book-open-variant" />
              資料來源
            </h4>
            <ul class="space-y-1">
              <li v-for="(source, idx) in event.sources" :key="idx" class="text-xs text-history-dark/80">
                <a 
                  v-if="source.url" 
                  :href="source.url" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="hover:text-history-accent hover:underline flex items-start gap-1"
                >
                  <Icon name="mdi:link-variant" class="w-3 h-3 mt-0.5 flex-shrink-0" />
                  {{ source.title }}
                </a>
                <span v-else class="flex items-start gap-1">
                  <Icon name="mdi:file-document-outline" class="w-3 h-3 mt-0.5 flex-shrink-0" />
                  {{ source.title }}
                </span>
              </li>
            </ul>
          </div>

          <button 
            @click.stop="enterStory(event)"
            class="w-full py-3 bg-history-accent hover:bg-history-brown text-history-paper font-bold rounded-lg shadow-md transition-colors flex items-center justify-center gap-2 group/btn"
          >
            <Icon name="mdi:book-open-page-variant" class="w-5 h-5 group-hover/btn:scale-110 transition-transform" />
            進入歷史故事
          </button>
        </div>

        <!-- Expand Hint -->
        <div 
          v-else 
          class="bg-history-brown/5 p-2 text-center text-history-brown/60 text-xs font-bold uppercase tracking-widest group-hover:bg-history-brown/10 transition-colors"
        >
          點擊查看詳情
        </div>
      </div>
    </div>
  </div>


      <!-- Legend Confirmation Modal -->
      <div v-if="showConfirmation" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closeConfirmation"></div>
        
        <!-- Modal Content -->
        <div class="relative bg-history-paper text-history-dark w-full max-w-md rounded-xl shadow-2xl p-6 border-2 border-history-brown/30 animate-fade-in">
          <div class="flex flex-col items-center text-center">
            <div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4 text-purple-600">
              <Icon name="mdi:unicorn-variant" class="w-10 h-10" />
            </div>
            
            <h3 class="text-2xl font-bold font-serif mb-2 text-history-dark">確定進入傳說？</h3>
            
            <p class="text-history-brown/80 mb-6 leading-relaxed">
              您選擇的<span class="font-bold text-purple-700">「{{ pendingEvent?.name }}」</span>屬於民間傳說或文學作品，其中的人物與情節可能並非真實歷史記錄。
            </p>
            
            <div class="flex gap-4 w-full">
              <button 
                @click="closeConfirmation"
                class="flex-1 py-3 px-4 border-2 border-history-brown/20 rounded-lg text-history-brown font-bold hover:bg-history-brown/5 transition-colors"
              >
                再想想
              </button>
              <button 
                @click="confirmEnterStory"
                class="flex-1 py-3 px-4 bg-purple-600 text-white rounded-lg font-bold shadow-md hover:bg-purple-700 transition-colors flex items-center justify-center gap-2"
              >
                <Icon name="mdi:check" class="w-5 h-5" />
                了解並進入
              </button>
            </div>
          </div>
        </div>
      </div>

</template>

<script setup lang="ts">
import { ref } from 'vue';
import type { HistoricalEvent, Persona } from '~/types';

// Extend HistoricalEvent to include personas for the list view
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

// Confirmation Modal State
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
@keyframes fade-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fade-in 0.2s ease-out;
}
</style>
