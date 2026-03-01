import { createRouter, createWebHashHistory } from 'vue-router'
import { defineComponent, h } from 'vue'
import SkillPage from '../views/SkillPage.vue'
import DocsPage from '../views/DocsPage.vue'
import TaskManageView from '../views/TaskManageView.vue'
import AgentManageView from '../views/AgentManageView.vue'

const Home = defineComponent({
  render: () => h('div', { class: 'home' }, 'Agent Arena'),
})

// 用于接收 Google OAuth 回调的占位页（实际逻辑在 App 里根据 hash 处理）
const AuthCallback = defineComponent({
  render: () => h('div', { class: 'auth-callback' }, '登录中…'),
})

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'Home', component: Home },
    { path: '/tasks', name: 'TaskManage', component: TaskManageView },
    { path: '/agents', name: 'AgentManage', component: AgentManageView },
    { path: '/skill', name: 'Skill', component: SkillPage },
    { path: '/docs', name: 'Docs', component: DocsPage },
    { path: '/auth/callback', name: 'AuthCallback', component: AuthCallback },
  ],
})

export default router
