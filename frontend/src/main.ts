import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './stores'
import { useAuthStore } from './stores/auth'
import { i18n } from './i18n'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/runpod-theme.css'

const app = createApp(App)

app.use(store)
app.use(router)
app.use(i18n)
app.use(ElementPlus)

// 恢复登录态
useAuthStore().initFromStorage()

app.mount('#app')