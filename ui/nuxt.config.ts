// https://nuxt.com/docs/api/configuration/nuxt-config

export default defineNuxtConfig({
  compatibilityDate: '2025-12-20',
  ssr: false,
  devtools: { enabled: true },
  devServer: {
    host: '0.0.0.0',
    port: 3000
  },
  modules: [
    '@pinia/nuxt'
  ],
  css: ['~/assets/css/main.css'],
  app: {
    head: {
      title: 'PyFlow | AI Driven Development',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' }
      ],
      link: [
        { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Outfit:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap' }
      ]
    }
  },
  nitro: {
    routeRules: {
      '/api/run': { proxy: (process.env.NUXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000') + '/run' },
      '/api/chat': { proxy: (process.env.NUXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000') + '/chat' },
      '/api/health': { proxy: (process.env.NUXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000') + '/health' }
    }
  }
})
