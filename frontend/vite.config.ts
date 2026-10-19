import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import path from 'node:path'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({ resolvers: [ElementPlusResolver()] }),
    Components({ resolvers: [ElementPlusResolver()] }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      'exceljs': path.resolve(__dirname, 'node_modules/exceljs'),
      'html2canvas': path.resolve(__dirname, 'node_modules/html2canvas'),
    },
    dedupe: ['vue', 'element-plus', '@element-plus/icons-vue'],
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8010', changeOrigin: true },
      '/static': { target: 'http://127.0.0.1:8010', changeOrigin: true },
    },
    fs: {
      allow: [
        '.',
        path.resolve(__dirname, '../chart-templates'),
      ],
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('echarts')) return 'echarts'
          if (id.includes('element-plus') || id.includes('@element-plus')) return 'element-plus'
          if (id.includes('exceljs')) return 'exceljs'
          if (id.includes('html2canvas')) return 'html2canvas'
          if (id.includes('vue') || id.includes('pinia') || id.includes('vue-router')) return 'vue-vendor'
          return 'vendor'
        },
      },
    },
    chunkSizeWarningLimit: 900,
  },
})
