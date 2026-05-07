// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: true },
  
  modules: ["@nuxtjs/tailwindcss", "@nuxt/icon"],

  icon: {
    serverBundle: {
      collections: ['mdi', 'uil', 'heroicons']
    },
    clientBundle: {
      scan: true,
      includeCustomCollections: true
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
      title: 'AI Persona Chat',
      htmlAttrs: {
        lang: 'zh-TW'
      },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: '一個沉浸式的互動 AI 聊天機器人' }
      ]
    }
  },

  compatibilityDate: '2024-12-02'
})