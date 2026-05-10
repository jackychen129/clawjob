import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    host: 'localhost',
    open: true
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('/vue-router') || id.includes('/pinia') || id.includes('/@vue/')) return 'vendor-vue'
          if (id.includes('/vue-i18n')) return 'vendor-i18n'
          if (id.includes('/axios')) return 'vendor-net'
          if (id.includes('/marked') || id.includes('/dompurify')) return 'vendor-markdown'
          if (id.includes('/@vueuse/')) return 'vendor-vueuse'
          if (id.includes('/lucide-vue-next')) return 'vendor-icons'
          return 'vendor-misc'
        },
      },
    }
  }
})