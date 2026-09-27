import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 生产环境由后端 StaticFiles 挂载在 /pc 下，base 必须与之一致。
// 本地联调目标可用 VITE_API_TARGET 覆盖（如 SSH 隧道 http://127.0.0.1:18000）。
const apiTarget = process.env.VITE_API_TARGET || 'http://localhost:8000'
export default defineConfig({
  base: '/pc/',
  plugins: [vue()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        // 框架与运行时单独成块，发版时利于长缓存命中
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia'],
        },
      },
    },
  },
  server: {
    port: 5180,
    proxy: {
      '/api': { target: apiTarget, changeOrigin: true },
      '/uploads': { target: apiTarget, changeOrigin: true },
    },
  },
})
