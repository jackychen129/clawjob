import { createRouter, createWebHashHistory } from 'vue-router'
import { defineComponent, h } from 'vue'
import SkillPage from '../views/SkillPage.vue'
import DocsPage from '../views/DocsPage.vue'
import ManualPage from '../views/ManualPage.vue'
import TaskManageView from '../views/TaskManageView.vue'
import AgentManageView from '../views/AgentManageView.vue'
import AccountPage from '../views/AccountPage.vue'
import OpenClawQuickstartPage from '../views/OpenClawQuickstartPage.vue'
import DashboardView from '../views/DashboardView.vue'
import LeaderboardView from '../views/LeaderboardView.vue'
import PlaybookOnboardingView from '../views/PlaybookOnboardingView.vue'
import AgentRentalView from '../views/AgentRentalView.vue'

const Home = defineComponent({
  render: () => h('div', { class: 'home' }, 'Agent Arena'),
})

// 用于接收 Google OAuth 回调的占位页（实际逻辑在 App 里根据 hash 处理）
const AuthCallback = defineComponent({
  render: () => h('div', { class: 'auth-callback' }, '登录中…'),
})

const router = createRouter({
  history: createWebHashHistory(),
  scrollBehavior(to, _from, savedPosition) {
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    return savedPosition ?? { left: 0, top: 0 }
  },
  routes: [
    { path: '/', name: 'Home', component: Home },
    { path: '/dashboard', name: 'Dashboard', component: DashboardView },
    { path: '/leaderboard', name: 'Leaderboard', component: LeaderboardView },
    { path: '/playbook', name: 'PlaybookOnboarding', component: PlaybookOnboardingView },
    { path: '/rental', name: 'AgentRental', component: AgentRentalView },
    { path: '/tasks', name: 'TaskManage', component: TaskManageView },
    { path: '/agents', name: 'AgentManage', component: AgentManageView },
    { path: '/skill', name: 'Skill', component: SkillPage },
    // 更具体的路径放前面，避免 /docs 先于 /docs/manual 匹配
    { path: '/docs/manual', name: 'DocsManual', component: ManualPage },
    { path: '/docs/openclaw-quickstart', name: 'DocsOpenClawQuickstart', component: OpenClawQuickstartPage },
    { path: '/docs', name: 'Docs', component: DocsPage },
    // 用 name 重定向避免 path 解析时产生无限循环导致栈溢出
    { path: '/docs/', name: 'DocsSlash', redirect: { name: 'Docs' } },
    { path: '/account', name: 'Account', component: AccountPage },
    { path: '/auth/callback', name: 'AuthCallback', component: AuthCallback },
  ],
})

export default router
