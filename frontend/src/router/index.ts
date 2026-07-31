import { createRouter, createWebHashHistory } from 'vue-router'
import { shouldRedirectIpToDomain } from '../lib/siteUrls'
import { routeAccessMeta } from '../config/navigation'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHashHistory(),
  scrollBehavior(to, _from, savedPosition) {
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    return savedPosition ?? { left: 0, top: 0 }
  },
  routes: [
    { path: '/', name: 'Landing', component: () => import('../views/LandingView.vue'), meta: { access: 'public', layout: 'marketing' } },
    { path: '/community', name: 'Community', component: () => import('../views/CommunityChatView.vue'), meta: { access: 'public' } },
    { path: '/dashboard', redirect: '/account' },
    { path: '/discover', redirect: '/marketplace' },
    { path: '/discover/agents', redirect: '/marketplace' },
    { path: '/discover/ranks', redirect: '/marketplace' },
    { path: '/leaderboard', redirect: '/marketplace' },
    { path: '/candidates', redirect: '/marketplace' },
    { path: '/marketplace', name: 'Marketplace', component: () => import('../views/MarketplaceView.vue'), meta: { access: 'public' } },
    { path: '/playbook', redirect: '/docs/openclaw-quickstart' },
    { path: '/rental', name: 'AgentRental', redirect: '/marketplace' },
    { path: '/tasks', name: 'TaskManage', component: () => import('../views/TaskManageView.vue'), meta: { access: 'public' } },
    { path: '/forum', redirect: '/tasks' },
    { path: '/agents', name: 'AgentManage', component: () => import('../views/AgentManageView.vue'), meta: { access: 'auth' } },
    { path: '/agent-studio', redirect: '/agents' },
    { path: '/agents/:id', name: 'AgentProfile', component: () => import('../views/AgentProfileView.vue') },
    { path: '/u/:username', name: 'PublicUser', component: () => import('../views/PublicUserView.vue') },
    { path: '/@:username', name: 'PublicUserAt', component: () => import('../views/PublicUserView.vue') },
    { path: '/studio', redirect: '/agent-studio' },
    { path: '/skill', name: 'Skill', component: () => import('../views/SkillPage.vue') },
    { path: '/join', name: 'Join', component: () => import('../views/JoinView.vue') },
    { path: '/r/:code', name: 'ReferralJoin', redirect: (to) => ({ path: '/join', query: { ref: String(to.params.code || '') } }) },
    { path: '/docs/manual', name: 'DocsManual', component: () => import('../views/ManualPage.vue') },
    { path: '/docs/openclaw-quickstart', name: 'DocsOpenClawQuickstart', component: () => import('../views/OpenClawQuickstartPage.vue') },
    { path: '/docs/mcp', name: 'DocsMcp', component: () => import('../views/McpDocsView.vue') },
    { path: '/docs', name: 'Docs', component: () => import('../views/DocsPage.vue') },
    { path: '/docs/', name: 'DocsSlash', redirect: { name: 'Docs' } },
    { path: '/inbox', redirect: '/tasks' },
    { path: '/account', name: 'Account', component: () => import('../views/AccountPage.vue'), meta: { access: 'auth' } },
    {
      path: '/admin',
      component: () => import('../layouts/AdminLayout.vue'),
      meta: { access: 'admin' },
      children: [
        { path: '', name: 'AdminOverview', component: () => import('../views/admin/AdminOverviewView.vue') },
        { path: 'disputes', name: 'AdminDisputes', component: () => import('../views/admin/AdminDisputesView.vue') },
        { path: 'settlements', name: 'AdminSettlements', component: () => import('../views/admin/AdminSettlementsView.vue') },
        { path: 'compliance', name: 'AdminCompliance', component: () => import('../views/admin/AdminComplianceView.vue') },
        { path: 'runtime', name: 'AdminRuntime', component: () => import('../views/admin/AdminRuntimeView.vue') },
        { path: 'audit', name: 'AdminAudit', component: () => import('../views/admin/AdminAuditView.vue') },
        { path: 'safety', name: 'AdminSafety', component: () => import('../views/admin/AdminSafetyView.vue') },
        { path: 'insights', redirect: { name: 'AdminOverview' } },
        { path: 'workspaces', redirect: { name: 'AdminOverview' } },
        { path: 'mcp', name: 'AdminMcp', component: () => import('../views/admin/AdminMcpView.vue') },
      ],
    },
    { path: '/ops', redirect: '/admin/settlements' },
    { path: '/a2a', redirect: '/tasks' },
    { path: '/a2a-console', redirect: '/agents' },
    { path: '/agent-lab', redirect: '/agents' },
    { path: '/auth/callback', name: 'AuthCallback', component: () => import('../views/AuthCallbackView.vue') },
  ],
})

router.beforeEach((to) => {
  const target = shouldRedirectIpToDomain()
  if (target && typeof window !== 'undefined' && window.location.href !== target) {
    window.location.replace(target)
    return false
  }

  const meta = routeAccessMeta(to.path)
  const auth = useAuthStore()

  if (meta.access === 'admin' && !auth.isLoggedIn) {
    return { path: '/tasks', query: { login: '1' } }
  }

  return true
})

export default router
