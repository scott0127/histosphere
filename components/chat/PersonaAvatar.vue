<template>
  <span class="relative inline-flex shrink-0 items-center justify-center overflow-hidden border border-[var(--admin-border)] bg-[var(--admin-surface-muted)]"
    :role="unavailable ? 'img' : undefined" :aria-label="unavailable ? alt : undefined">
    <img v-if="!unavailable" :src="src || ''" :alt="alt"
      :class="isMona ? 'mona-portrait' : 'h-full w-full object-cover'" @error="failed = true" />
    <Icon v-else name="mdi:account-voice" class="h-1/2 w-1/2 text-[var(--admin-coffee)]" aria-hidden="true" />
  </span>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

const props = defineProps<{ src?: string | null; alt: string }>();
const failed = ref(false);
const unavailable = computed(() => !props.src || failed.value);
const isMona = computed(() => /\/mona-rudao\.(?:jpe?g|png|webp)(?:[?#]|$)/i.test(props.src || ''));
watch(() => props.src, () => { failed.value = false; });
</script>

<style scoped>
/* 600×858 合照中的中央人物：以原圖 (215,55) 起的 200×200 區域呈現頭肩。
   只調整顯示範圍，不改寫史料圖片；避免先置中裁切再縮放而切掉臉部。 */
.mona-portrait { position: absolute; width: 300%; max-width: none; height: auto; left: -107.5%; top: -27.5%; }
</style>
