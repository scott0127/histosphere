<template>
  <div class="w-full h-full overflow-y-auto p-4 md:p-8 scrollbar-thin scrollbar-thumb-history-brown scrollbar-track-history-light">
    <div class="grid grid-cols-1 md:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-0 max-w-7xl mx-auto">
      <!-- 主容器 (Main Container) -->
      <div 
        v-for="event in events" 
        :key="event.id"
        class="group relative transition-all duration-300 hover:-translate-y-1 overflow-hidden cursor-pointer bg-[length:100%_100%] bg-center bg-no-repeat border-none aspect-[333/443]"
        :style="{ ...getCardStyle(event.id), containerType: 'inline-size' }"
        @click="toggleExpand(event.id)"
      >
          <!-- 1. Century Tag (Fixed) -->
          <div class="absolute" style="top: 13%; left: 13%;">
            <span class="px-[3cqw] py-[1cqw] bg-[#5D4037] text-[#D7CCC8] text-[3.5cqw] font-bold rounded-full shadow-sm border border-[#3E2723]">
              {{ event.century }} 世紀
            </span>
          </div>

          <!-- 2-4. Info Group (Year -> Title -> Location Flow) -->
          <div class="absolute flex flex-col items-start gap-[3.5cqw]" style="top: 21%; left: 13%; width: 75%;">
             <!-- Year -->
             <div class="font-serif italic text-[#3E2723] font-bold text-[3.5cqw] mix-blend-multiply">
                {{ event.time_period }}
             </div>
             <!-- Title (Max 2 lines) -->
             <div class="font-serif font-bold text-[#3E2723] leading-[1.1] text-[7.6cqw] line-clamp-2 py-[1cqw] mix-blend-multiply min-h-[16.8cqw]">
                {{ event.name }}
             </div>
             <!-- Location -->
             <div class="flex items-center gap-[1cqw] font-bold text-[#5D4037] text-[4cqw] mix-blend-multiply">
                <Icon name="mdi:map-marker" class="w-[5cqw] h-[5cqw]" />
                {{ event.geographic_location }}
             </div>
          </div>

          <!-- 5. Description (Fixed) -->
          <div class="absolute font-serif text-[#3E2723] font-medium leading-[1.4] line-clamp-5 text-[4.4cqw] mix-blend-multiply opacity-90"
             style="top: 53%; left: 13%; width: 70%;">
            {{ event.description || event.context }}
          </div>

          <!-- 6. Image (Icon Representation) -->
          <div class="absolute flex items-start justify-center opacity-80 mix-blend-multiply pointer-events-none"
             style="top: 28%; left: 64%; width: 35%;">
             <Icon 
               :name="event.type === 'legend' ? 'mdi:unicorn-variant' : 'mdi:feather'" 
               class="w-full h-auto text-[#3E2723]" 
             />
          </div>

          <!-- 7. Delete Button -->
          <button 
              @click.stop="$emit('delete-event', event.id)"
              class="absolute p-2 text-[#5D4037]/40 hover:text-red-600 transition-colors z-30 opacity-0 group-hover:opacity-100"
              style="top: 14%; left: 75%;"
              title="刪除"
            >
              <Icon name="mdi:trash-can-outline" class="w-[6cqw] h-[6cqw]" />
          </button>

          <!-- 8. Bottom Hint -->
          <div class="absolute w-full text-center" style="top: 78%; left: 0;">
             <span class="text-[#5D4037]/70 text-[4cqw] font-bold tracking-[0.2em] uppercase group-hover:text-[#5D4037] transition-colors">
               點擊查看詳情
             </span>
          </div>

          <!-- Expanded Content Overlay -->
          <Transition
            enter-active-class="transition ease-out duration-200"
            enter-from-class="opacity-0 translate-y-4"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition ease-in duration-150"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 translate-y-4"
          >
            <div 
              v-if="expandedId === event.id"
              class="absolute inset-0 z-50 bg-black/80 backdrop-blur-md p-6 flex flex-col text-gray-100 overflow-y-auto"
            >
               <div class="flex justify-between items-start mb-4">
                  <h3 class="text-xl font-bold text-amber-500">{{ event.name }}</h3>
                  <button @click.stop="toggleExpand(event.id)" class="text-gray-400 hover:text-white">
                    <Icon name="mdi:close" class="w-6 h-6" />
                  </button>
               </div>
               
               <div class="space-y-4">
                  <!-- Personas -->
                  <div>
                    <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">歷史人物</h4>
                    <div class="flex flex-wrap gap-2">
                       <div v-for="persona in event.personas" :key="persona.id" class="flex items-center gap-2 bg-white/10 px-2 py-1 rounded">
                          <Icon name="mdi:account" class="w-4 h-4" />
                          <span class="text-sm">{{ persona.name }}</span>
                       </div>
                    </div>
                  </div>

                  <!-- Sources -->
                  <div v-if="event.sources?.length">
                    <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">資料來源</h4>
                    <ul class="text-xs text-gray-300 space-y-1">
                      <li v-for="(source, idx) in event.sources" :key="idx" class="truncate">
                        {{ source.title }}
                      </li>
                    </ul>
                  </div>

                  <button 
                    @click.stop="enterStory(event)"
                    class="w-full py-3 bg-amber-700 hover:bg-amber-600 text-white font-bold rounded shadow-md mt-4 flex items-center justify-center gap-2"
                  >
                    <Icon name="mdi:book-open-page-variant" class="w-5 h-5" />
                    進入歷史故事
                  </button>
               </div>
            </div>
          </Transition>
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

// Glob import for dynamic loading
const cardBgAssets = import.meta.glob('~/assets/images/ui/card_bg_*.png', { eager: true, import: 'default' });

// Determine card background based on ID (deterministic)
const getCardStyle = (id: string) => {
  // Simple hash for consistency
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = id.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = (Math.abs(hash) % 6) + 1;
  
  // Resolve path from glob imports
  // Note: glob keys are absolute paths in dev, relative in build.
  // We match by filename suffix.
  const matchingKey = Object.keys(cardBgAssets).find(key => key.includes(`card_bg_${index}.png`));
  const bgUrl = matchingKey ? cardBgAssets[matchingKey] : '';

  return {
    backgroundImage: `url('${bgUrl}')`
  };
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
