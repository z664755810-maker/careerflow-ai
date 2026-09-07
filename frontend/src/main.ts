import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './styles/global.css'
import App from './App.vue'
import router from './router'

// Element Plus 已改为按需引入（见 vite.config.ts 的 AutoImport + Components 插件），
// 不再在此全量注册 app.use(ElementPlus)，也不再引入 element-plus/dist/index.css 全量样式。
const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
