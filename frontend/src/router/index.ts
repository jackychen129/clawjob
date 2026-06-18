import { createRouter, createWebHashHistory } from 'vue-router'
import { defineComponent, h } from 'vue'
import { shouldRedirectIpToDomain } from '../lib/siteUrls'

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
    { path: '/', name: 'Home', redirect: '/tasks' },
    { path: '/community', name: 'Community', component: () => import('../views/CommunityChatView.vue') },
    { path: '/dashboard', name: 'Dashboard', component: () => import('../views/DashboardView.vue') },
    {
      path: '/discover',
      component: () => import('../views/DiscoverView.vue'),
      children: [
        { path: '', redirect: '/discover/agents' },
        {
          path: 'agents',
          name: 'DiscoverAgents',
          component: () => import('../views/CandidatesView.vue'),
          props: { embedded: true },
        },
        {
          path: 'ranks',
          name: 'DiscoverRanks',
          component: () => import('../views/LeaderboardView.vue'),
          props: { embedded: true },
        },
      ],
    },
    { path: '/leaderboard', redirect: '/discover/ranks' },
    { path: '/candidates', redirect: '/discover/agents' },
    { path: '/marketplace', name: 'Marketplace', component: () => import('../views/MarketplaceView.vue') },
    { path: '/playbook', name: 'Playbook', component: () => import('../views/PlaybookView.vue') },
    { path: '/rental', name: 'AgentRental', redirect: '/marketplace' },
    { path: '/tasks', name: 'TaskManage', component: () => import('../views/TaskManageView.vue') },
    { path: '/forum', redirect: '/tasks' },
    { path: '/agents', name: 'AgentManage', component: () => import('../views/AgentManageView.vue') },
    { path: '/agent-studio', name: 'AgentStudio', component: () => import('../views/AgentStudioView.vue') },
    { path: '/agents/:id', name: 'AgentProfile', component: () => import('../views/AgentProfileView.vue') },
    { path: '/u/:username', name: 'PublicUser', component: () => import('../views/PublicUserView.vue') },
    { path: '/@:username', name: 'PublicUserAt', component: () => import('../views/PublicUserView.vue') },
    { path: '/studio', redirect: '/agent-studio' },
    { path: '/skill', name: 'Skill', component: () => import('../views/SkillPage.vue') },
    { path: '/join', name: 'Join', component: () => import('../views/JoinView.vue') },
    { path: '/r/:code', name: 'ReferralJoin', redirect: (to) => ({ path: '/join', query: { ref: String(to.params.code || '') } }) },
    // NOTE: translated comment in English.
    { path: '/docs/manual', name: 'DocsManual', component: () => import('../views/ManualPage.vue') },
    { path: '/docs/openclaw-quickstart', name: 'DocsOpenClawQuickstart', component: () => import('../views/OpenClawQuickstartPage.vue') },
    { path: '/docs', name: 'Docs', component: () => import('../views/DocsPage.vue') },
    // NOTE: translated comment in English.
    { path: '/docs/', name: 'DocsSlash', redirect: { name: 'Docs' } },
    { path: '/inbox', name: 'Inbox', component: () => import('../views/InboxView.vue') },
    { path: '/account', name: 'Account', component: () => import('../views/AccountPage.vue') },
    { path: '/admin', name: 'Admin', component: () => import('../views/AdminView.vue') },
    { path: '/ops', name: 'Ops', component: () => import('../views/OpsView.vue') },
    { path: '/a2a', redirect: '/tasks' },
    { path: '/a2a-console', redirect: '/agents' },
    { path: '/agent-lab', redirect: '/agents' },
    { path: '/auth/callback', name: 'AuthCallback', component: AuthCallback },
  ],
})

router.beforeEach(() => {
  const target = shouldRedirectIpToDomain()
  if (target && typeof window !== 'undefined' && window.location.href !== target) {
    window.location.replace(target)
    return false
  }
})

export default router
