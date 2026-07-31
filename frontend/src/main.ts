import { createApp, nextTick } from 'vue'
import App from './App.vue'
import router from './router'
import store from './stores'
import { useAuthStore } from './stores/auth'
import { i18n, applyLocaleToDocument } from './i18n'
import {
  clearOAuthFromUrl,
  parseOAuthFromLocation,
  stashOAuthError,
} from './lib/oauthCallback'
import '@fontsource-variable/geist'
import '@fontsource-variable/geist-mono'
import '@fontsource/noto-sans-sc/chinese-simplified-400.css'
import '@fontsource/noto-sans-sc/chinese-simplified-600.css'
import './assets/index.css'
import './styles/tokens.css'
import './styles/runpod-theme.css'
import './styles/apple-shell.css'
import './styles/admin.css'
import './styles/motion.css'

const app = createApp(App)

app.use(store)
app.use(router)
app.use(i18n)

useAuthStore().initFromStorage()

const auth = useAuthStore()
let oauthHandled = false

try {
  const oauthBootstrap = parseOAuthFromLocation()
  if (oauthBootstrap.error) {
    stashOAuthError(oauthBootstrap.error)
    oauthHandled = true
  } else if (oauthBootstrap.token) {
    auth.setUser(
      oauthBootstrap.token,
      oauthBootstrap.username || 'user',
      oauthBootstrap.userId,
    )
    oauthHandled = true
  }
} catch (e) {
  console.error('[oauth bootstrap]', e)
}

function showBootError(message: string) {
  const el = document.getElementById('app')
  if (el) {
    el.innerHTML =
      '<div style="padding:2rem;background:#1a1a1a;color:#e5e5e5;font-family:system-ui;max-width:600px;margin:2rem auto;">' +
      '<h2>加载失败</h2>' +
      `<p>${message}</p>` +
      '<p><button type="button" onclick="location.reload()" style="padding:8px 16px;border-radius:8px;border:0;background:#4f46e5;color:#fff;cursor:pointer;">刷新页面</button></p>' +
      '</div>'
  }
}

async function finishOAuthNavigation() {
  if (!oauthHandled) return
  if (auth.isLoggedIn) {
    await router.replace('/tasks')
  }
  clearOAuthFromUrl('#/tasks')
}

try {
  app.mount('#app')
  router.isReady().then(() => {
    finishOAuthNavigation().finally(() => {
      applyLocaleToDocument(i18n.global.locale.value as 'zh-CN' | 'en')
    })
  })
  nextTick(() => {
    applyLocaleToDocument(i18n.global.locale.value as 'zh-CN' | 'en')
  })
} catch (e) {
  showBootError('请刷新页面或检查网络。若持续出现，请打开浏览器控制台查看报错。')
  throw e
}
