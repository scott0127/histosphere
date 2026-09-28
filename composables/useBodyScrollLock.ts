import { onMounted, onScopeDispose, watch } from 'vue';

const locks = new WeakMap<HTMLElement, { count: number; overflow: string; priority: string }>();

// Each overlay owns one lock, so closing or unmounting it cannot unlock another.
export const useBodyScrollLock = (isOpen: () => boolean) => {
  let release: (() => void) | undefined;
  let stop: (() => void) | undefined;

  onMounted(() => {
    stop = watch(isOpen, (open) => {
      if (!open) {
        release?.();
        release = undefined;
        return;
      }
      if (release) return;

      const body = document.body;
      let lock = locks.get(body);
      if (!lock) {
        lock = {
          count: 0,
          overflow: body.style.getPropertyValue('overflow'),
          priority: body.style.getPropertyPriority('overflow'),
        };
        locks.set(body, lock);
        body.style.setProperty('overflow', 'hidden');
      }
      lock.count += 1;
      const ownedLock = lock;
      release = () => {
        ownedLock.count -= 1;
        if (ownedLock.count) return;
        if (ownedLock.overflow) body.style.setProperty('overflow', ownedLock.overflow, ownedLock.priority);
        else body.style.removeProperty('overflow');
        locks.delete(body);
      };
    }, { immediate: true, flush: 'sync' });
  });

  onScopeDispose(() => {
    stop?.();
    release?.();
    release = undefined;
  });
};
