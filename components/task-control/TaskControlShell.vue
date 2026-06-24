<template>
  <!-- task-control 外框：標記這區是研究者/老師編輯端，不混入學生作答 UI。 -->
  <section class="admin-panel">
    <div class="admin-panel-inner admin-panel-muted p-4">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p class="admin-kicker">任務編輯</p>
          <h3 class="admin-heading mt-1 font-serif text-xl font-bold">歷史故事任務</h3>
        </div>
        <slot name="actions" />
      </div>
      <div class="mt-4">
        <slot />
      </div>
    </div>
  </section>
</template>
