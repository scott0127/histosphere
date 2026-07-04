<template>
  <Transition
    enter-active-class="transition-opacity duration-200 ease-out"
    leave-active-class="transition-opacity duration-150 ease-in"
    enter-from-class="opacity-0"
    leave-to-class="opacity-0"
  >
    <div
      v-if="show"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(47,41,36,0.52)] p-4 backdrop-blur-sm"
      @click.self="$emit('cancel')"
    >
      <section
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        class="w-full max-w-[520px] rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-7 text-left shadow-[0_24px_70px_rgba(47,41,36,0.24)]"
      >
        <div class="flex items-start gap-5">
          <div class="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] text-[var(--admin-coffee)]">
            <Icon :name="icon" class="h-5 w-5" />
          </div>
          <div class="min-w-0">
            <p class="text-xs font-black uppercase leading-none tracking-[0.18em] text-[var(--admin-coffee)]">{{ eyebrow }}</p>
            <h3 :id="titleId" class="mt-3 font-sans text-3xl font-black leading-none text-[var(--admin-text)] tabular-nums">
              {{ title }}
            </h3>
            <p class="mt-5 text-xl font-black leading-9 text-[var(--admin-copy)]">
              {{ message }}
            </p>
          </div>
        </div>

        <div class="mt-6 flex justify-end gap-3">
          <button
            type="button"
            class="inline-flex h-14 min-w-24 items-center justify-center rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] px-6 text-base font-black leading-none text-[var(--admin-copy)] transition hover:bg-[var(--admin-surface-muted)]"
            @click="$emit('cancel')"
          >
            {{ cancelLabel }}
          </button>
          <button
            type="button"
            class="inline-flex h-14 min-w-24 items-center justify-center rounded-lg bg-[var(--admin-coffee)] px-6 text-base font-black leading-none text-[var(--admin-surface)] transition hover:bg-[var(--admin-coffee-hover)]"
            @click="$emit('confirm')"
          >
            {{ confirmLabel }}
          </button>
        </div>
      </section>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  show: boolean;
  title: string;
  message: string;
  eyebrow?: string;
  icon?: string;
  confirmLabel?: string;
  cancelLabel?: string;
}>(), {
  eyebrow: '確認',
  icon: 'mdi:check-circle-outline',
  confirmLabel: '是',
  cancelLabel: '否',
});

defineEmits<{
  (event: 'confirm'): void;
  (event: 'cancel'): void;
}>();

const titleId = computed(() => `confirm-action-${props.title.replace(/\s+/g, '-').toLowerCase()}`);
</script>
