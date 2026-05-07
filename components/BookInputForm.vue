<template>
  <div class="book-input-form relative" :style="containerStyle">
    <!-- Book Background Image -->
    <img 
      :src="bookImageUrl" 
      alt="Book background"
      class="w-full h-auto"
    />
    
    <!-- Logo Toggle Area (Invisible overlay) -->
    <div 
      class="absolute top-[13%] left-[38%] w-[24%] h-[14%] cursor-pointer z-20"
      title="返回經典模式"
      @click="$emit('toggle-ui')"
    ></div>
    
    <!-- Input Field (overlayed on parchment area) -->
    <input 
      id="event"
      v-model="eventName"
      type="text"
      :placeholder="currentPlaceholder"
      class="absolute input-field"
      :style="inputStyle"
      :disabled="isLoading"
      @keyup.enter="handleSubmit"
    />
    
    <!-- Submit Button (Visual Layer) -->
    <div 
      class="absolute pointer-events-none transition-transform duration-200"
      :class="{ 'opacity-70': isLoading }"
      :style="buttonStyle"
    >
      <img 
        :src="buttonImageUrl" 
        alt=""
        class="w-full h-auto"
      />
      <!-- Loading Indicator Overlay -->
      <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center">
        <Icon name="mdi:loading" class="animate-spin h-8 w-8 text-history-brown" />
      </div>
    </div>

    <!-- Submit Button (Click Interaction Layer) -->
    <div
        class="absolute cursor-pointer rounded-lg hover:scale-105 active:scale-95 transition-transform duration-200 z-20"
        :style="buttonHitAreaStyle"
        @click="!isLoading && handleSubmit()"
        title="開始探索"
    ></div>
    
    <!-- Error Message -->
    <div v-if="error" class="absolute -bottom-16 left-0 w-full text-center">
      <p class="inline-block px-3 py-1 bg-red-100 text-red-700 font-bold rounded shadow animate-shake text-sm">
        {{ error }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';

// Props
const props = withDefaults(defineProps<{
  isLoading?: boolean;
  error?: string | null;
  maxWidth?: string;
}>(), {
  isLoading: false,
  error: null,
  maxWidth: '500px'
});

// Emits
const emit = defineEmits<{
  (e: 'event-submit', eventName: string): void;
  (e: 'toggle-ui'): void;
}>();

// Internal State
const eventName = ref('');

// Rotating placeholder examples
const placeholders = [
  '例如：文藝復興...',
  '例如：法國大革命...',
  '例如：工業革命...',
  '例如：二戰諾曼第登陸...',
  '例如：唐朝安史之亂...',
];
const currentPlaceholderIndex = ref(0);
const currentPlaceholder = ref(placeholders[0]);
let placeholderInterval: ReturnType<typeof setInterval> | null = null;

const rotatePlaceholder = () => {
  currentPlaceholderIndex.value = (currentPlaceholderIndex.value + 1) % placeholders.length;
  currentPlaceholder.value = placeholders[currentPlaceholderIndex.value];
};

// Image URLs
import bookWithStaticItem from '~/assets/images/ui/book_with_static_item.png';
import bookButton from '~/assets/images/ui/book_button.png';

const bookImageUrl = bookWithStaticItem;
const buttonImageUrl = bookButton;

// Container style
const containerStyle = computed(() => ({
  maxWidth: props.maxWidth,
  width: '100%'
}));

// Input field positioning (user tested values)
const inputStyle = computed(() => ({
  top: '54.5%',
  left: '7.5%',
  width: '84%',
  height: '8%',
  background: 'transparent',
  border: 'none',
  outline: 'none',
  fontFamily: '"Noto Serif TC", serif',
  fontSize: 'clamp(0.9rem, 2.5vw, 1.2rem)',
  fontWeight: 'bold',
  color: '#5c4a32',
  padding: '0 15px',
  caretColor: '#5c4a32',
  zIndex: '10',
  opacity: props.isLoading ? '0.7' : '1'
}));

// Button positioning (visual layer)
const buttonStyle = computed(() => ({
  top: '-1.5%',
  left: '-0.5%',
  width: '101.5%'
}));

// Button hit area (interaction layer) - positioned over the actual button graphic
const buttonHitAreaStyle = computed(() => ({
  bottom: '12%',
  left: '15%',
  width: '70%',
  height: '12%'
}));

// Handle submit
const handleSubmit = () => {
  if (eventName.value.trim() && !props.isLoading) {
    emit('event-submit', eventName.value.trim());
  }
};

// Handle external fill event (from index.vue)
const handleFillEvent = (event: CustomEvent) => {
  eventName.value = event.detail;
  // Focus input
  const inputElement = document.getElementById('event') as HTMLInputElement;
  if (inputElement) {
    inputElement.focus();
  }
};

onMounted(() => {
  window.addEventListener('fillEventName', handleFillEvent as EventListener);
  placeholderInterval = setInterval(rotatePlaceholder, 3000);
});

onUnmounted(() => {
  window.removeEventListener('fillEventName', handleFillEvent as EventListener);
  if (placeholderInterval) {
    clearInterval(placeholderInterval);
  }
});
</script>

<style scoped>
.input-field::placeholder {
  color: #5c4a32;
  opacity: 0.8;
  font-style: italic;
}

.input-field:focus {
  outline: none;
}
</style>
