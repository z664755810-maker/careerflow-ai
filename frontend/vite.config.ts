import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发服务器代理 /api 到后端（避免跨域），生产由 Vercel 重写或同源部署处理
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
