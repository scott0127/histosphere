<template>
  <!-- 學生 task 頁的外框：只處理頁面層級排版，具體題目交給 renderer。 -->
  <div class="historical-task relative min-h-screen overflow-x-hidden bg-[var(--admin-page)] font-sans text-[var(--admin-text)] [&_.font-serif]:font-['Crimson_Text',Georgia,'Noto_Serif_TC','Times_New_Roman',serif]">
    <header class="relative z-20 border-b border-[var(--admin-border)] bg-[rgba(255,253,248,0.95)] shadow-sm">
      <div class="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-3">
        <NuxtLink to="/" class="flex items-center gap-3">
          <span class="flex h-10 w-10 items-center justify-center rounded-full border-2 border-[var(--admin-line)] bg-[var(--admin-surface)] text-[var(--admin-coffee)] shadow-[0_3px_0_rgba(47,41,36,0.18)]">
            <Icon name="mdi:book-open-page-variant" class="h-5 w-5" />
          </span>
          <span>
            <span class="block font-serif text-lg font-bold tracking-[0.08em] text-[var(--admin-text)]">Histosphere</span>
            <span class="block text-xs font-semibold tracking-[0.08em] text-[var(--admin-copy)]">歷史對話學習實驗</span>
          </span>
        </NuxtLink>
        <span class="rounded-full border border-[var(--admin-border)] bg-[var(--admin-coffee-soft)] px-4 py-2 text-sm font-bold text-[var(--admin-coffee)] shadow-sm">
          Error-Elicitation Task
        </span>
      </div>
    </header>

    <main class="relative z-10 mx-auto max-w-6xl px-5 py-10 md:py-12">
      <slot />
    </main>
  </div>
</template>
