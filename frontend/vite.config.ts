import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// 开发服务器代理 /api 到后端（避免跨域），生产由 Vercel 重写或同源部署处理
export default defineConfig({
  plugins: [
    vue(),
    // 按需自动导入 Element Plus 的 API（ElMessage / ElMessageBox 等），
    // 不再需要手写 import；dts 生成类型声明供 vue-tsc 识别。
    AutoImport({
      resolvers: [ElementPlusResolver()],
      dts: true,
    }),
    // 按需自动注册模板中实际用到的 el-* 组件，并注入对应样式，
    // 取代原来 main.ts 里的全量 app.use(ElementPlus)。
    Components({
      resolvers: [ElementPlusResolver()],
      dts: true,
    }),
  ],
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
