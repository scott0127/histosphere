<template>
  <div ref="container" class="study-split" :class="{ 'is-resizing': resizing }" :style="{ '--reading-share': share / 100 }">
    <section id="task-review-pane" class="reading-pane" aria-label="題目與作答">
      <slot name="task" />
    </section>
    <div
      role="separator"
      tabindex="0"
      aria-label="調整題目與對話區域大小"
      aria-controls="task-review-pane chat-pane"
      :aria-orientation="horizontal ? 'vertical' : 'horizontal'"
      :aria-valuenow="Math.round(share)"
      :aria-valuemin="25"
      :aria-valuemax="60"
      :aria-valuetext="`題目區域 ${Math.round(share)}%`"
      title="拖曳調整大小；雙擊還原"
      class="split-handle"
      @pointerdown="startResize"
      @pointermove="resize"
      @pointerup="stopResize"
      @pointercancel="stopResize"
      @lostpointercapture="resizing = false"
      @keydown="resizeWithKeyboard"
      @dblclick="share = 38"
    ><span aria-hidden="true" /></div>
    <section id="chat-pane" class="conversation-pane" aria-label="對話">
      <slot />
    </section>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';

const container = ref<HTMLElement | null>(null);
const share = ref(38);
const resizing = ref(false);
const horizontal = ref(true);
let media: MediaQueryList | undefined;
const updateDirection = () => { horizontal.value = Boolean(media?.matches); };
const clamp = (value: number) => Math.min(60, Math.max(25, value));

function startResize(event: PointerEvent) {
  if (event.button !== 0) return;
  event.preventDefault();
  (event.currentTarget as HTMLElement).focus();
  (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  resizing.value = true;
}
function resize(event: PointerEvent) {
  if (!resizing.value || !container.value) return;
  const bounds = container.value.getBoundingClientRect();
  // 分隔把手佔 16px，其餘空間才按比例分配，避免拖動時兩側寬高相加溢出。
  const size = (horizontal.value ? bounds.width : bounds.height) - 16;
  const position = horizontal.value ? event.clientX - bounds.left : event.clientY - bounds.top;
  if (size > 0) share.value = clamp((position - 8) / size * 100);
}
function stopResize(event: PointerEvent) {
  resizing.value = false;
  const handle = event.currentTarget as HTMLElement;
  if (handle.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId);
}
function resizeWithKeyboard(event: KeyboardEvent) {
  const decrease = horizontal.value ? 'ArrowLeft' : 'ArrowUp';
  const increase = horizontal.value ? 'ArrowRight' : 'ArrowDown';
  if (![decrease, increase, 'Home', 'End', 'Enter'].includes(event.key)) return;
  event.preventDefault();
  share.value = event.key === 'Home' ? 25 : event.key === 'End' ? 60 : event.key === 'Enter' ? 38
    : clamp(share.value + (event.key === increase ? 2 : -2));
}
onMounted(() => {
  media = window.matchMedia('(min-width: 768px)');
  updateDirection();
  media.addEventListener('change', updateDirection);
});
onBeforeUnmount(() => media?.removeEventListener('change', updateDirection));
</script>

<style scoped>
.study-split { display: flex; flex-direction: column; flex: 1; min-height: 0; min-width: 0; }
.reading-pane, .conversation-pane { display: flex; flex-direction: column; min-height: 0; min-width: 0; overflow: hidden; border: 1px solid var(--admin-border); border-radius: 8px; background: var(--admin-surface); }
.reading-pane { flex: 0 0 calc((100% - 16px) * var(--reading-share)); }
.conversation-pane { flex: 1; }
.split-handle { display: flex; align-items: center; justify-content: center; flex: 0 0 16px; touch-action: none; cursor: row-resize; border-radius: 4px; }
.split-handle span { height: 4px; width: 36px; border-radius: 2px; background: var(--admin-border); }
.split-handle:hover span, .split-handle:focus-visible span, .is-resizing .split-handle span { background: var(--admin-coffee); }
.split-handle:focus-visible { outline: 2px solid var(--admin-coffee); outline-offset: -2px; }
.is-resizing { user-select: none; }
@media (min-width: 768px) {
  .study-split { flex-direction: row; }
  .split-handle { cursor: col-resize; }
  .split-handle span { width: 4px; height: 36px; }
}
</style>
