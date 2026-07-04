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
        class="w-full max-w-md rounded-xl border border-[var(--admin-border)] bg-[var(--admin-surface)] p-6 text-left shadow-[0_24px_70px_rgba(47,41,36,0.24)]"
      >
        <div class="flex items-start gap-4">
          <div class="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] text-[var(--admin-coffee)]">
            <Icon :name="icon" class="h-5 w-5" />
          </div>
          <div class="min-w-0">
            <p class="text-xs font-black uppercase tracking-[0.18em] text-[var(--admin-coffee)]">{{ eyebrow }}</p>
            <h3 :id="titleId" class="mt-1 font-serif text-2xl font-black text-[var(--admin-text)]">
              {{ title }}
            </h3>
            <p class="mt-3 text-sm font-medium leading-7 text-[var(--admin-copy)]">
              {{ message }}
            </p>
          </div>
        </div>

        <div class="mt-6 flex justify-end gap-3">
          <button
            type="button"
            class="inline-flex min-h-11 items-center justify-center rounded-lg border border-[var(--admin-border)] bg-[var(--admin-surface)] px-5 text-sm font-black text-[var(--admin-copy)] transition hover:bg-[var(--admin-surface-muted)]"
            @click="$emit('cancel')"
          >
            {{ cancelLabel }}
          </button>
          <button
            type="button"
            class="inline-flex min-h-11 items-center justify-center rounded-lg bg-[var(--admin-coffee)] px-5 text-sm font-black text-[var(--admin-surface)] transition hover:bg-[var(--admin-coffee-hover)]"
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

const titleId = `confirm-action-${props.title.replace(/\s+/g, '-').toLowerCase()}`;
</script>
