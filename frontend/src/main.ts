import { createApp, nextTick } from 'vue'
import App from './App.vue'
import router from './router'
import store from './stores'
import { useAuthStore } from './stores/auth'
import { i18n, applyLocaleToDocument } from './i18n'
import './assets/index.css'
import './styles/runpod-theme.css'

const app = createApp(App)

app.use(store)
app.use(router)
app.use(i18n)

// 恢复登录态
useAuthStore().initFromStorage()

try {
  app.mount('#app')
  nextTick(() => {
    applyLocaleToDocument(i18n.global.locale.value as 'zh-CN' | 'en')
  })
} catch (e) {
  const el = document.getElementById('app')
  if (el) {
    el.innerHTML = '<div style="padding:2rem;background:#1a1a1a;color:#e5e5e5;font-family:system-ui;max-width:600px;margin:2rem auto;"><h2>加载失败</h2><p>请刷新页面或检查网络。若持续出现，请打开浏览器控制台查看报错。</p><pre style="margin-top:1rem;font-size:0.85rem;overflow:auto;">' + String(e) + '</pre></div>'
  }
  throw e
}