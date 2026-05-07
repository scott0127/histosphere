<template>
  <!-- 打字機效果進行中：顯示純文字 -->
  <p v-if="!isTypingComplete" class="text-history-dark whitespace-pre-wrap">{{ displayedText }}</p>
  
  <!-- 打字機效果完成：如果有 annotations 則使用 AnnotatedText，否則顯示純文字 -->
  <AnnotatedText 
    v-else-if="annotations && annotations.length > 0" 
    :content="text" 
    :annotations="annotations" 
  />
  <p v-else class="text-history-dark whitespace-pre-wrap">{{ text }}</p>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import type { Annotation } from '~/types';
import AnnotatedText from './AnnotatedText.vue';

const props = defineProps<{
  text: string;
  annotations?: Annotation[];
}>();

const displayedText = ref('');
const isTypingComplete = ref(false);
let intervalId: number | undefined;

const startTyping = () => {
  displayedText.value = '';
  isTypingComplete.value = false;
  
  if (props.text) {
    let i = 0;
    intervalId = window.setInterval(() => {
      if (i < props.text.length) {
        displayedText.value += props.text[i];
        i++;
      } else {
        clearInterval(intervalId);
        isTypingComplete.value = true;  // 打字完成
      }
    }, 20);
  }
};

watch(() => props.text, () => {
  if (intervalId) {
    clearInterval(intervalId);
  }
  startTyping();
});

onMounted(() => {
  startTyping();
});
</script>
