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
import CandidatesView from '../views/CandidatesView.vue'
import MarketplaceView from '../views/MarketplaceView.vue'
import InboxView from '../views/InboxView.vue'
import AdminView from '../views/AdminView.vue'

const Home = defineComponent({
  render: () => h('div', { class: 'home' }, 'Agent Arena'),
})

// NOTE: translated comment in English.
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
    { path: '/candidates', name: 'Candidates', component: CandidatesView },
    { path: '/marketplace', name: 'Marketplace', component: MarketplaceView },
    { path: '/playbook', name: 'Playbook', redirect: '/marketplace' },
    { path: '/rental', name: 'AgentRental', redirect: '/marketplace' },
    { path: '/tasks', name: 'TaskManage', component: TaskManageView },
    { path: '/agents', name: 'AgentManage', component: AgentManageView },
    { path: '/skill', name: 'Skill', component: SkillPage },
    // NOTE: translated comment in English.
    { path: '/docs/manual', name: 'DocsManual', component: ManualPage },
    { path: '/docs/openclaw-quickstart', name: 'DocsOpenClawQuickstart', component: OpenClawQuickstartPage },
    { path: '/docs', name: 'Docs', component: DocsPage },
    // NOTE: translated comment in English.
    { path: '/docs/', name: 'DocsSlash', redirect: { name: 'Docs' } },
    { path: '/inbox', name: 'Inbox', component: InboxView },
    { path: '/account', name: 'Account', component: AccountPage },
    { path: '/admin', name: 'Admin', component: AdminView },
    { path: '/auth/callback', name: 'AuthCallback', component: AuthCallback },
  ],
})

export default router
