import { readFileSync } from 'node:fs';

// This handler must run before Nuxt's module entry, including when that entry cannot load.
const clientStartupScript = readFileSync(new URL('./scripts/client-startup.js', import.meta.url), 'utf8');

// https://nuxt.com/docs/api/configuration/nuxt-config
const mdiClientIcons = [
  'mdi:account',
  'mdi:account-circle-outline',
  'mdi:account-edit-outline',
  'mdi:account-group',
  'mdi:account-group-outline',
  'mdi:account-multiple-outline',
  'mdi:account-outline',
  'mdi:account-plus',
  'mdi:account-plus-outline',
  'mdi:account-voice',
  'mdi:archive-arrow-down-outline',
  'mdi:arrow-collapse-down',
  'mdi:arrow-collapse-up',
  'mdi:arrow-down',
  'mdi:arrow-left',
  'mdi:arrow-right',
  'mdi:arrow-up',
  'mdi:badge-account-outline',
  'mdi:bank',
  'mdi:book-open-blank-variant',
  'mdi:book-open-page-variant',
  'mdi:chart-box-outline',
  'mdi:check',
  'mdi:check-circle',
  'mdi:check-circle-outline',
  'mdi:chevron-down',
  'mdi:chevron-up',
  'mdi:clipboard-text-outline',
  'mdi:clock-time-eight-outline',
  'mdi:close',
  'mdi:cog-outline',
  'mdi:compass',
  'mdi:compass-rose',
  'mdi:content-save-outline',
  'mdi:database-search',
  'mdi:door-open',
  'mdi:download-outline',
  'mdi:email-check-outline',
  'mdi:email-outline',
  'mdi:eye',
  'mdi:eye-outline',
  'mdi:eye-off',
  'mdi:feather',
  'mdi:file-document-outline',
  'mdi:format-list-bulleted',
  'mdi:history',
  'mdi:incognito',
  'mdi:information-outline',
  'mdi:library-outline',
  'mdi:lightbulb-outline',
  'mdi:link-variant',
  'mdi:link-variant-plus',
  'mdi:loading',
  'mdi:lock-check-outline',
  'mdi:lock-outline',
  'mdi:lock-reset',
  'mdi:login',
  'mdi:logout',
  'mdi:magnify',
  'mdi:magnify-plus-outline',
  'mdi:map-legend',
  'mdi:map-marker-radius',
  'mdi:message-processing-outline',
  'mdi:message-text',
  'mdi:palette',
  'mdi:pencil-outline',
  'mdi:pillar',
  'mdi:play-circle-outline',
  'mdi:plus',
  'mdi:refresh',
  'mdi:restart',
  'mdi:restart-alert',
  'mdi:school-outline',
  'mdi:send',
  'mdi:send-check-outline',
  'mdi:shield-account-outline',
  'mdi:tag-text-outline',
  'mdi:tag',
  'mdi:tag-outline',
  'mdi:timer-check-outline',
  'mdi:timer-outline',
  'mdi:timer-refresh-outline',
  'mdi:tray-arrow-down',
  'mdi:trash-can-outline',
  'mdi:trophy',
  'mdi:unicorn-variant',
  'mdi:undo-variant',
  'mdi:redo-variant',
  'mdi:view-grid-outline',
];

export default defineNuxtConfig({
  // DevTools 會增加本地 dev 啟動與 runtime 負擔；需要時用 NUXT_DEVTOOLS=true 開啟。
  devtools: { enabled: process.env.NUXT_DEVTOOLS === 'true' },

  css: ['~/assets/css/admin-theme.css'],
  
  modules: ["@nuxtjs/tailwindcss", "@nuxt/icon"],

  tailwindcss: {
    // Tailwind Viewer 會在 dev 額外註冊路由與產物；目前不需要，關閉可降低啟動面積。
    viewer: false,
  },

  vite: {
    ssr: {
      // Windows dev SSR can emit externalized imports like "C:/..." which Node ESM rejects.
      // Keep dependencies bundled in dev so generated server imports stay portable.
      noExternal: process.platform === 'win32' && process.env.NODE_ENV !== 'production' ? true : undefined,
    },
  },

  icon: {
    // 專案 icon 名稱目前可枚舉，直接打進 client bundle。
    // 這可避免 dev 時掃描檔案，也避免 Nitro 建立 /api/_nuxt_icon server bundle。
    provider: 'none',
    serverBundle: false,
    clientBundle: {
      icons: mdiClientIcons,
      scan: false,
      includeCustomCollections: false
    }
  },

  nitro: {
    routeRules: {
      // 排除 Nuxt Icon 的 API 路徑，不進行代理
      '/api/_nuxt_icon/**': { headers: { 'cache-control': 's-maxage=3600' } },
      // 其他 API 請求代理到後端
      '/api/**': { proxy: process.env.NUXT_API_URL ? `${process.env.NUXT_API_URL}/api/**` : (process.env.NUXT_API_HOST ? `https://${process.env.NUXT_API_HOST}/api/**` : 'http://127.0.0.1:8000/api/**') },
      // 靜態檔案（頭像圖片等）代理到後端
      '/static/**': { proxy: process.env.NUXT_API_URL ? `${process.env.NUXT_API_URL}/static/**` : (process.env.NUXT_API_HOST ? `https://${process.env.NUXT_API_HOST}/static/**` : 'http://127.0.0.1:8000/static/**') }
    }
  },

  app: {
    head: {
      title: 'Histosphere',
      htmlAttrs: {
        lang: 'zh-TW'
      },
      script: [
        {
          key: 'client-startup-recovery',
          innerHTML: clientStartupScript,
          tagPosition: 'head',
          tagPriority: 'critical'
        }
      ],
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400;1,600;1,700&display=swap' }
      ],
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'EBL-integrated AI historical persona role-play learning prototype' }
      ]
    }
  },

  compatibilityDate: '2024-12-02'
})
