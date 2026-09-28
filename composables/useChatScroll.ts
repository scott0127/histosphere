import { nextTick, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue';
import type { ChatMessage } from '~/types';

export function useChatScroll(
  container: Ref<HTMLElement | null>,
  content: Ref<HTMLElement | null>,
  history: () => ChatMessage[],
  conversationId: () => string,
) {
  const followingLatest = ref(true);
  const hasNewReply = ref(false);
  const highlightedMessageId = ref<string | null>(null);
  let resizeObserver: ResizeObserver | undefined;
  let highlightTimer: ReturnType<typeof setTimeout> | undefined;

  function onScroll() {
    const pane = container.value;
    if (!pane) return;
    followingLatest.value = pane.scrollHeight - pane.clientHeight - pane.scrollTop <= 64;
    if (followingLatest.value) hasNewReply.value = false;
  }

  function alignToLatest() {
    const pane = container.value;
    if (pane) pane.scrollTop = pane.scrollHeight;
  }

  function scrollToLatest() {
    followingLatest.value = true;
    hasNewReply.value = false;
    alignToLatest();
  }

  async function jumpToMessage(messageId: string) {
    await nextTick();
    const pane = container.value;
    const target = content.value?.querySelector<HTMLElement>(`[data-message-id="${CSS.escape(messageId)}"]`);
    if (!pane || !target) return;
    followingLatest.value = false;
    pane.scrollTop += target.getBoundingClientRect().top - pane.getBoundingClientRect().top - 12;
    target.focus({ preventScroll: true });
    highlightedMessageId.value = messageId;
    if (highlightTimer) clearTimeout(highlightTimer);
    highlightTimer = setTimeout(() => { highlightedMessageId.value = null; }, 2800);
  }

  // 讀者已往上回看時，保留位置；串流更新不以平滑捲動反覆搶回視線。
  watch(history, async () => {
    await nextTick();
    if (followingLatest.value) alignToLatest();
    else hasNewReply.value = true;
  }, { deep: true });

  watch(conversationId, async () => {
    followingLatest.value = true;
    hasNewReply.value = false;
    highlightedMessageId.value = null;
    await nextTick();
    alignToLatest();
  });

  onMounted(() => {
    alignToLatest();
    // 亦涵蓋打字機、圖片載入和分欄縮放造成的高度改變。
    resizeObserver = new ResizeObserver(() => {
      if (followingLatest.value) alignToLatest();
    });
    if (content.value) resizeObserver.observe(content.value);
    if (container.value) resizeObserver.observe(container.value);
  });
  onBeforeUnmount(() => {
    resizeObserver?.disconnect();
    if (highlightTimer) clearTimeout(highlightTimer);
  });

  return { followingLatest, hasNewReply, highlightedMessageId, onScroll, scrollToLatest, jumpToMessage };
}
