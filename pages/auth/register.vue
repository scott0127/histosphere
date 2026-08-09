<template>
  <main class="flex min-h-screen items-center justify-center bg-history-paper px-6">
    <section class="w-full max-w-md rounded-[8px] border border-history-brown/20 bg-white/90 p-8 text-center shadow-lg">
      <span class="mx-auto flex h-14 w-14 items-center justify-center rounded-full border border-history-brown/20 bg-history-accent/10 text-history-accent">
        <Icon name="mdi:account-lock-outline" class="h-7 w-7" />
      </span>
      <h1 class="mt-5 font-serif text-2xl font-bold text-history-dark">研究帳號由研究團隊建立</h1>
      <p class="mt-3 leading-7 text-history-brown/80">
        本系統不開放自行註冊。請使用研究團隊提供的帳號與密碼登入。
      </p>
      <NuxtLink
        to="/auth/login"
        class="mt-7 inline-flex w-full items-center justify-center gap-2 rounded-[8px] bg-history-accent px-4 py-3 font-bold text-white transition hover:bg-history-accent/90"
      >
        <Icon name="mdi:login" class="h-5 w-5" />
        返回登入
      </NuxtLink>
    </section>
  </main>
</template>
