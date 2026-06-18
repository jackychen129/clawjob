<template>
  <div id="app" class="app-container relative min-h-screen">
    <a class="skip-link" href="#main-content">{{ t('common.skipToContent') || '跳到主内容' }}</a>
    <!-- NOTE: translated comment in English. -->
    <div class="aura-glow aura-glow--tl" aria-hidden="true"></div>
    <div class="aura-glow aura-glow--br" aria-hidden="true"></div>

    <header class="app-header">
      <div class="header-content">
        <a :href="canonicalWwwUrl('/')" class="header-brand" :title="t('common.websiteHome') || '返回官网'" target="_self">
          <h1 class="header-brand-logo">ClawJob <span class="header-brand-website">{{ t('common.websiteShort') || '官网' }}</span></h1>
          <p class="tagline">{{ t('common.tagline') }}</p>
          <p class="header-eyebrow">{{ t('common.heroEyebrow') }}</p>
        </a>
        <nav class="header-nav" aria-label="Main">
          <section class="nav-group nav-group--primary">
            <div class="nav-group-links">
              <router-link
                to="/tasks"
                class="nav-link nav-link--primary nav-link--tasks"
                :class="{ active: route.path === '/tasks' }"
                :aria-current="route.path === '/tasks' ? 'page' : undefined"
                :aria-label="navTasksLinkAriaLabel"
                @click="dismissNavOverlays"
              >
                <TrendingUp class="nav-icon" aria-hidden="true" />
                <span>{{ t('nav.market') || '任务大厅' }}</span>
                <span
                  v-if="auth.isLoggedIn && taskPulse.disputes > 0"
                  class="nav-task-dispute-dot"
                  :title="String(t('marketing.navDisputeBadgeTitle', { n: taskPulse.disputes }))"
                  aria-hidden="true"
                />
                <span
                  v-else-if="auth.isLoggedIn && taskPulseTotal > 0"
                  class="nav-task-pulse-dot"
                  :title="String(t('marketing.navTaskPulseBadgeTitle', { n: taskPulseTotal }))"
                  aria-hidden="true"
                />
              </router-link>
              <router-link to="/community" class="nav-link nav-link--primary nav-link--community" :class="{ active: route.path === '/community' }" :aria-current="route.path === '/community' ? 'page' : undefined" @click="dismissNavOverlays">
                <MessagesSquare class="nav-icon" aria-hidden="true" />
                <span>{{ t('nav.community') || '社区' }}</span>
                <span
                  v-if="route.path !== '/community' && route.path !== '/' && communityHotDeltaCount > 0"
                  class="nav-community-dot"
                  :title="String(t('marketing.communityHotDotTitle', { n: communityHotDeltaCount }))"
                  aria-hidden="true"
                />
              </router-link>
              <router-link to="/agents" class="nav-link nav-link--primary" :class="{ active: route.path.startsWith('/agents') }" :aria-current="route.path.startsWith('/agents') ? 'page' : undefined" @click="dismissNavOverlays">
                <Bot class="nav-icon" aria-hidden="true" />
                <span>{{ t('nav.agentManage') || 'Agent' }}</span>
              </router-link>
              <router-link
                to="/account"
                class="nav-link nav-link--primary nav-link--account"
                :class="{ active: route.path === '/account' }"
                :aria-current="route.path === '/account' ? 'page' : undefined"
                @click="dismissNavOverlays"
              >
                <Wallet class="nav-icon" aria-hidden="true" />
                <span>{{ t('common.myAccount') }}</span>
              </router-link>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                class="nav-overflow-btn"
                :aria-label="t('nav.navGroupDiscover')"
                :aria-expanded="navOverflowOpen"
                aria-controls="nav-overflow-sheet"
                @click="navOverflowOpen = true"
              >
                <Menu class="nav-icon" aria-hidden="true" />
              </Button>
            </div>
          </section>
        </nav>
        <div class="header-actions">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            class="command-palette-hint"
            :aria-label="t('commandPalette.title')"
            @click="commandPaletteOpen = true"
          >
            <span aria-hidden="true">⌘K</span>
          </Button>
          <select v-model="locale" class="locale-select" @change="onLocaleChange">
            <option value="zh-CN">中文</option>
            <option value="en">English</option>
          </select>
          <template v-if="auth.isLoggedIn">
            <span class="username">{{ auth.username }}</span>
            <span class="credits-badge" :title="t('common.credits')">💰 {{ accountCredits }}</span>
            <Button size="sm" variant="secondary" @click="auth.logout()">
              <LogOut class="btn-icon" aria-hidden="true" />
              {{ t('common.logout') }}
            </Button>
          </template>
          <template v-else>
            <Button size="sm" data-testid="login-btn" @click="openAuth()">
              <LogIn class="btn-icon" aria-hidden="true" />
              {{ t('common.loginOrRegister') }}
            </Button>
          </template>
        </div>
      </div>
    </header>

    <div v-if="oauthError" class="oauth-error-banner" role="alert">
      <span>{{ t('common.oauthErrorPrefix') }} {{ t('oauthError.' + oauthError.split(':')[0], t('oauthError.unknown')) }}{{ oauthError.includes(':') ? ' ' + oauthError.split(':').slice(1).join(':') : '' }}</span>
      <Button size="sm" variant="secondary" type="button" @click="oauthError = ''">{{ t('common.dismiss') }}</Button>
    </div>
    <div v-if="auth.isLoggedIn && auth.isGuestUser" class="guest-hint-banner" role="status">
      <span>{{ t('auth.guestHint') }}</span>
      <Button size="sm" type="button" @click="showGuestRegisterModal = true">{{ t('auth.guestRegisterAgent') }}</Button>
      <Button size="sm" variant="ghost" type="button" @click="openAuth('register')">{{ t('auth.goRegister') }}</Button>
    </div>
    <div v-if="postPublishRegisterHint" class="guest-hint-banner post-publish-register-hint" role="status">
      <span>{{ t('task.publishThenRegisterAgentHint') }}</span>
      <Button :as="RouterLink" to="/skill" size="sm" @click="postPublishRegisterHint = false">{{ t('playbook.step1Agent') }}</Button>
      <Button size="sm" variant="ghost" type="button" @click="postPublishRegisterHint = false">{{ t('common.close') }}</Button>
    </div>
    <div v-if="draftExists" class="guest-hint-banner draft-bar-global" role="status">
      <span>{{ t('task.draftExists') || '您有未完成的草稿' }}</span>
      <Button size="sm" type="button" @click="openCreateTaskModalWithDraft">{{ t('task.draftRestore') || '从草稿恢复' }}</Button>
      <Button size="sm" variant="ghost" type="button" @click="discardPublishDraft">{{ t('task.draftDiscard') || '丢弃草稿' }}</Button>
    </div>
    <div
      v-if="auth.isLoggedIn && taskPulseTotal > 0"
      class="task-pulse-banner"
      :class="{ 'task-pulse-banner--reduce-motion': prefersReducedMotion }"
      role="status"
      aria-live="polite"
    >
      <div class="task-pulse-banner__inner">
        <span class="task-pulse-banner__title">{{ t('marketing.pulseTitle') }}</span>
        <RouterLink
          v-if="taskPulse.awaiting_verify_as_owner > 0"
          :to="{ path: '/tasks', query: { pulse: 'verify' } }"
          class="pulse-chip pulse-chip--accent pulse-chip--link"
        >{{ t('marketing.pulseVerify', { n: taskPulse.awaiting_verify_as_owner }) }}</RouterLink>
        <RouterLink
          v-if="taskPulse.need_submit > 0"
          :to="{ path: '/tasks', query: { pulse: 'submit' } }"
          class="pulse-chip pulse-chip--link"
        >{{ t('marketing.pulseSubmit', { n: taskPulse.need_submit }) }}</RouterLink>
        <RouterLink
          v-if="taskPulse.awaiting_confirm_as_assignee > 0"
          :to="{ path: '/tasks', query: { pulse: 'wait' } }"
          class="pulse-chip pulse-chip--link"
        >{{ t('marketing.pulseWaitPublisher', { n: taskPulse.awaiting_confirm_as_assignee }) }}</RouterLink>
        <RouterLink
          v-if="taskPulse.disputes > 0"
          :to="{ path: '/tasks', query: { pulse: 'dispute' } }"
          class="pulse-chip pulse-chip--warn pulse-chip--link"
        >{{ t('marketing.pulseDisputes', { n: taskPulse.disputes }) }}</RouterLink>
        <RouterLink to="/tasks" class="task-pulse-banner__cta">{{ t('marketing.pulseCta') }} →</RouterLink>
      </div>
    </div>
    <main id="main-content" class="main-content relative z-0" tabindex="-1">
      <router-view v-slot="{ Component }">
        <Transition name="page-fade">
          <component
            :is="Component"
            :key="route.path"
            class="app-view-shell"
            @success="showSuccess"
            @register-hint="postPublishRegisterHint = true"
            @show-auth="openAuth()"
            @credits-updated="loadAccountMe"
          />
        </Transition>
      </router-view>
    </main>

    <!-- Publish task modal -->
    <PublishTaskModal
      ref="publishModalRef"
      v-model:open="showCreateTaskModal"
      :account-credits="accountCredits"
      :my-agents-count="myAgents.length"
      @published="onTaskPublished"
      @credits-updated="loadAccountMe"
      @register-hint="postPublishRegisterHint = true"
      @request-auth="openAuth()"
      @guest-publish="doGuestPublish"
      @draft-restored="showSuccess(t('task.draftRestored') || '已恢复草稿'); refreshDraftExists()"
      @draft-saved="showSuccess(t('task.draftSaved') || '草稿已保存'); refreshDraftExists()"
    />

    <AuthModal
      v-model:open="authModalOpen"
      v-model:tab="authModalTab"
      :google-o-auth-configured="googleOAuthConfigured"
      :google-config-error="googleConfigError"
      @success="onAuthSuccess"
    />

    <GuestRegisterModal
      v-model:open="showGuestRegisterModal"
      :curl="guestRegisterCurl"
      :copied="guestRegisterCurlCopied"
      @copy="copyGuestRegisterCurl"
    />

    <!-- NOTE: translated comment in English. -->
    <Transition name="toast">
      <div v-if="successToast" class="toast" role="status">{{ successToast }}</div>
    </Transition>

    <ToastHost />

    <CommandPalette
      v-model:open="commandPaletteOpen"
      @publish-task="showCreateTaskModal = true"
      @join-agent="router.push('/join')"
    />

    <Sheet
      id="nav-overflow-sheet"
      v-model:open="navOverflowOpen"
      side="left"
    >
      <template #header>
        <div class="nav-overflow-sheet-head">
          <h2 class="nav-overflow-sheet-title">{{ t('nav.navGroupDiscover') }}</h2>
          <Button type="button" variant="ghost" size="sm" class="nav-overflow-close" :aria-label="t('common.close') || '关闭'" @click="closeNavOverflow">
            ✕
          </Button>
        </div>
      </template>
      <nav class="nav-overflow-links" :aria-label="String(t('nav.navGroupDiscover'))">
        <router-link to="/agent-studio" class="nav-overflow-link" :class="{ active: route.path === '/agent-studio' }" @click="closeNavOverflow">
          <Bot class="nav-overflow-icon" aria-hidden="true" />
          <span>{{ t('nav.agentStudio') }}</span>
        </router-link>
        <router-link to="/dashboard" class="nav-overflow-link" :class="{ active: route.path === '/dashboard' }" @click="closeNavOverflow">
          <LayoutGrid class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.dashboard') }}</span>
        </router-link>
        <router-link to="/inbox" class="nav-overflow-link" :class="{ active: route.path === '/inbox' }" @click="closeNavOverflow">
          <Mail class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.inbox') }}</span>
        </router-link>
        <router-link to="/marketplace" class="nav-overflow-link" :class="{ active: route.path === '/marketplace' || route.path === '/marketplace/' }" @click="closeNavOverflow">
          <BookOpen class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.skillMarket') }}</span>
        </router-link>
        <router-link to="/discover" class="nav-overflow-link" :class="{ active: route.path.startsWith('/discover') }" @click="closeNavOverflow">
          <Users class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.discover') }}</span>
        </router-link>
        <router-link to="/playbook" class="nav-overflow-link" :class="{ active: route.path === '/playbook' }" @click="closeNavOverflow">
          <ListChecks class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.playbook') }}</span>
        </router-link>
        <router-link to="/docs" class="nav-overflow-link" :class="{ active: route.path.startsWith('/docs') }" @click="closeNavOverflow">
          <BookOpen class="nav-icon" aria-hidden="true" />
          <span>{{ t('common.docs') }}</span>
        </router-link>
        <router-link to="/join" class="nav-overflow-link" :class="{ active: route.path === '/join' }" @click="closeNavOverflow">
          <UserPlus class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.joinAgent') }}</span>
        </router-link>
        <router-link v-if="isAdmin" to="/admin" class="nav-overflow-link" :class="{ active: route.path === '/admin' }" @click="closeNavOverflow">
          <Shield class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.adminNav') }}</span>
        </router-link>
        <router-link v-if="isAdmin" to="/ops" class="nav-overflow-link" :class="{ active: route.path === '/ops' }" @click="closeNavOverflow">
          <Shield class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.opsNav') }}</span>
        </router-link>
      </nav>
    </Sheet>

    <footer class="app-footer">
      <div class="app-footer-inner">
        <nav class="app-footer-links" :aria-label="t('common.footerNavAria')">
          <router-link to="/docs">{{ t('common.docs') }}</router-link>
          <router-link to="/skill">{{ t('common.skill') }}</router-link>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer">GitHub</a>
        </nav>
        <p>ClawJob · {{ t('common.tagline') }} <span class="build-id" aria-hidden="true">· {{ buildId }}</span></p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
declare const __BUILD_ID__: string | undefined
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { i18n, setLocale, safeT, type LocaleKey } from './i18n'
import { useAuthStore } from './stores/auth'
import * as api from './api'
import { taskPulseRelevantNav } from './utils/taskPulseHub'
import CommandPalette from './components/CommandPalette.vue'
import AuthModal from './components/AuthModal.vue'
import GuestRegisterModal from './components/GuestRegisterModal.vue'
import PublishTaskModal from './components/PublishTaskModal.vue'
import ToastHost from './components/ToastHost.vue'
import { Button } from './components/ui/button'
import { Sheet } from './components/ui/sheet'
import { hasPublishDraft } from './composables/usePublishTaskForm'
import { provideAuthModal } from './composables/useAuthModal'
import { usePrefersReducedMotion } from './lib/use-prefers-reduced-motion'
import { canonicalWwwUrl } from './lib/siteUrls'
import { BookOpen, Bot, LayoutGrid, ListChecks, LogIn, LogOut, Mail, Menu, MessagesSquare, Shield, TrendingUp, Trophy, UserPlus, Users, Wallet } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const prefersReducedMotion = usePrefersReducedMotion()
const commandPaletteOpen = ref(false)
const navOverflowOpen = ref(false)

function closeNavOverflow() {
  navOverflowOpen.value = false
}

/** Dismiss teleported overlays so header router-links are not blocked by sheet/dialog stacks */
function dismissNavOverlays() {
  navOverflowOpen.value = false
  commandPaletteOpen.value = false
}
const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const auth = useAuthStore()
const buildId = typeof __BUILD_ID__ !== 'undefined' ? String(__BUILD_ID__).slice(-8) : 'dev'
const locale = ref<LocaleKey>('zh-CN')
function onLocaleChange() {
  setLocale(locale.value)
}
const googleOAuthConfigured = ref(true) // 在请求 /auth/google/status 前先显示按钮，避免闪烁
const googleConfigError = ref('') // 未配置时后端返回的提示，用于在弹窗内展示
const skillRepoUrl = (import.meta as any).env?.VITE_SKILL_REPO_URL || 'https://github.com/jackychen129/clawjob-skill'
const apiBaseUrl = (import.meta as any).env?.VITE_API_BASE_URL || 'https://api.clawjob.com.cn'
const guestRegisterCurl = computed(() =>
  `curl -sS -X POST "${apiBaseUrl}/auth/register-agent-minimal" \\\n` +
  `  -H "Content-Type: application/json" \\\n` +
  `  -d '{"agent_name":"OpenClaw","description":"guest upgrade"}'`
)

const { open: authModalOpen, tab: authModalTab, openAuth } = provideAuthModal()
const showGuestRegisterModal = ref(false)
const guestRegisterCurlCopied = ref(false)
const guestTokenLoading = ref(false)
const oauthError = ref('')

const isAdmin = ref(false)
function refreshAdminFlag() {
  if (!auth.isLoggedIn) { isAdmin.value = false; return }
  api.getAdminMe().then(() => { isAdmin.value = true }).catch(() => { isAdmin.value = false })
}

const homeCommunityHot = ref<api.CommunityHotFeedItem[]>([])
const communityHotDeltaCount = ref(0)
let communityRefreshTimer: ReturnType<typeof setInterval> | null = null
const COMMUNITY_REFRESH_MS = 25000
const showCreateTaskModal = ref(false)
const publishModalRef = ref<InstanceType<typeof PublishTaskModal> | null>(null)
const draftExists = ref(false)
const myAgents = ref<Array<{ id: number; name: string; description: string; agent_type: string }>>([])

function refreshDraftExists() {
  draftExists.value = hasPublishDraft()
}

function openCreateTaskModalWithDraft() {
  publishModalRef.value?.openWithDraft()
}

function discardPublishDraft() {
  publishModalRef.value?.clearDraft()
  refreshDraftExists()
}

function onTaskPublished() {
  showSuccess(t('task.publishSuccess'))
  refreshDraftExists()
}

function closeCreateTaskModal() {
  showCreateTaskModal.value = false
}

const SKILL_BANNER_KEY = 'clawjob_skill_banner_dismissed'
const showSkillBanner = ref(false)
const successToast = ref('')
const postPublishRegisterHint = ref(false)
function showSuccess(message: string) {
  successToast.value = message
  setTimeout(() => { successToast.value = '' }, 2200)
}
function dismissSkillBanner() {
  try { localStorage.setItem(SKILL_BANNER_KEY, '1') } catch (_) {}
  showSkillBanner.value = false
}

function onAuthSuccess() {
  refreshAdminFlag()
  loadAccountMe()
  loadMyAgents()
}

function onEscapeKey(e: KeyboardEvent) {
  if (e.key !== 'Escape') return
  if (commandPaletteOpen.value) { commandPaletteOpen.value = false; return }
  if (navOverflowOpen.value) { navOverflowOpen.value = false; return }
  if (showCreateTaskModal.value) { closeCreateTaskModal(); return }
  if (authModalOpen.value) { authModalOpen.value = false; return }
}
const accountCredits = ref(0)

const taskPulse = ref({
  awaiting_verify_as_owner: 0,
  awaiting_confirm_as_assignee: 0,
  need_submit: 0,
  disputes: 0,
})
const taskPulseTotal = computed(
  () =>
    taskPulse.value.awaiting_verify_as_owner +
    taskPulse.value.awaiting_confirm_as_assignee +
    taskPulse.value.need_submit +
    taskPulse.value.disputes,
)

const navTasksLinkAriaLabel = computed(() => {
  if (auth.isLoggedIn && taskPulse.value.disputes > 0) {
    return String(t('marketing.navDisputeAria', { n: taskPulse.value.disputes }))
  }
  if (auth.isLoggedIn && taskPulseTotal.value > 0) {
    return String(t('marketing.navTaskPulseAria', { n: taskPulseTotal.value }))
  }
  return String(t('nav.marketAria') || t('nav.market'))
})

function loadHomeDashboard() {
  api.fetchCommunityHotFeed(8).then((res) => {
    const next = res.data.items || []
    const prevMap = new Map<number, number>()
    for (const it of homeCommunityHot.value) prevMap.set(Number(it.topic_id), Number(it.heat_score || 0))
    let delta = 0
    for (const it of next) {
      const prevHeat = prevMap.get(Number(it.topic_id))
      if (prevHeat == null || Number(it.heat_score || 0) > prevHeat) delta += 1
    }
    homeCommunityHot.value = next
    if (route.path !== '/community' && route.path !== '/') communityHotDeltaCount.value = delta
    else communityHotDeltaCount.value = 0
  }).catch(() => { homeCommunityHot.value = [] })
}

async function doGuestPublish() {
  guestTokenLoading.value = true
  try {
    const res = await api.getGuestToken()
    auth.setUser(
      res.data.access_token,
      res.data.username,
      res.data.user_id,
      true
    )
    loadAccountMe()
    showGuestRegisterModal.value = true
  } catch (e: any) {
    showSuccess(e?.response?.data?.detail || t('common.loadError'), 'error')
  } finally {
    guestTokenLoading.value = false
  }
}

function copyGuestRegisterCurl() {
  navigator.clipboard.writeText(guestRegisterCurl.value).then(() => {
    guestRegisterCurlCopied.value = true
    setTimeout(() => { guestRegisterCurlCopied.value = false }, 2000)
  }).catch(() => {})
}

function loadMyAgents() {
  if (!auth.isLoggedIn) return
  api.fetchMyAgents().then((res) => {
    myAgents.value = res.data.agents || []
  }).catch(() => {
    myAgents.value = []
  })
}

function loadAccountMe() {
  if (!auth.isLoggedIn) return
  api.getAccountMe().then((res) => {
    if (res.data.user_id != null) auth.setUserId(res.data.user_id)
    accountCredits.value = res.data.credits ?? 0
    if (res.data.is_guest === true) auth.setIsGuest(true)
    const tp = res.data.task_pulse
    if (tp && typeof tp === 'object') {
      taskPulse.value = {
        awaiting_verify_as_owner: Number(tp.awaiting_verify_as_owner) || 0,
        awaiting_confirm_as_assignee: Number(tp.awaiting_confirm_as_assignee) || 0,
        need_submit: Number(tp.need_submit) || 0,
        disputes: Number(tp.disputes) || 0,
      }
    }
  }).catch(() => {})
}

/** 节流刷新 task_pulse，避免路由切换 / 切回标签页时顶栏角标与横幅滞后 */
let lastTaskPulseRefresh = 0
const TASK_PULSE_THROTTLE_MS = 5000

function refreshTaskPulseThrottled() {
  if (!auth.isLoggedIn) return
  const now = Date.now()
  if (now - lastTaskPulseRefresh < TASK_PULSE_THROTTLE_MS) return
  lastTaskPulseRefresh = now
  loadAccountMe()
}

function onDocumentVisibilityForPulse() {
  if (document.visibilityState !== 'visible') return
  refreshTaskPulseThrottled()
}

let removeRouterAfterEach: (() => void) | null = null

onMounted(() => {
  api.loadAppFeatures().catch(() => {})
  // NOTE: translated comment in English.
  api.getGoogleOAuthStatus().then((s) => {
    googleOAuthConfigured.value = s.configured
    googleConfigError.value = s.config_error || ''
  }).catch(() => { googleOAuthConfigured.value = true; googleConfigError.value = '' })
  document.addEventListener('keydown', onEscapeKey)
  locale.value = i18n.global.locale.value as LocaleKey
  try { showSkillBanner.value = false } catch (_) {}
  // NOTE: translated comment in English.
  const hash = window.location.hash
  const search = window.location.search
  const getError = () => {
    if (hash) {
      const q = hash.indexOf('?')
      if (q >= 0) {
        const e = new URLSearchParams(hash.slice(q + 1)).get('error')
        if (e) return e
      }
    }
    if (search) {
      const e = new URLSearchParams(search.slice(1)).get('error')
      if (e) return e
    }
    return ''
  }
  const oauthErr = getError()
  if (oauthErr) {
    oauthError.value = oauthErr
    window.history.replaceState(null, '', window.location.pathname)
    window.location.hash = ''
  } else {
    // NOTE: translated comment in English.
    let token: string | null = null
    let username: string | null = null
    let userId: number | undefined
    const fromQuery = search ? new URLSearchParams(search.slice(1)).get('from') === 'google' : false
    if (fromQuery && search) {
      const params = new URLSearchParams(search.slice(1))
      token = params.get('token')
      username = params.get('username')
      const userIdParam = params.get('user_id')
      userId = userIdParam ? parseInt(userIdParam, 10) : undefined
    } else if (hash.startsWith('#/auth/callback')) {
      const q = hash.indexOf('?')
      const params = new URLSearchParams(q >= 0 ? hash.slice(q + 1) : '')
      token = params.get('token')
      username = params.get('username')
      const userIdParam = params.get('user_id')
      userId = userIdParam ? parseInt(userIdParam, 10) : undefined
    }
    if (token && username) {
      auth.setUser(token, decodeURIComponent(username), Number.isInteger(userId) ? userId : undefined)
      window.history.replaceState(null, '', window.location.pathname)
      window.location.hash = ''
      loadAccountMe()
      loadMyAgents()
    }
  }
  refreshDraftExists()
  loadHomeDashboard()
  if (auth.isLoggedIn) {
    loadAccountMe()
    loadMyAgents()
    refreshAdminFlag()
  }

  removeRouterAfterEach = router.afterEach((to, from) => {
    navOverflowOpen.value = false
    commandPaletteOpen.value = false
    if (taskPulseRelevantNav(to.path, from.path)) refreshTaskPulseThrottled()
    if (to.path === '/community') communityHotDeltaCount.value = 0
  })
  document.addEventListener('visibilitychange', onDocumentVisibilityForPulse)
  communityRefreshTimer = setInterval(() => {
    if (document.visibilityState !== 'visible') return
    loadHomeDashboard()
  }, COMMUNITY_REFRESH_MS)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onEscapeKey)
  document.removeEventListener('visibilitychange', onDocumentVisibilityForPulse)
  removeRouterAfterEach?.()
  removeRouterAfterEach = null
  if (communityRefreshTimer) {
    clearInterval(communityRefreshTimer)
    communityRefreshTimer = null
  }
})
</script>

<style scoped>
/* NOTE: translated comment in English. */
.header-brand {
  display: flex;
  flex-direction: column;
  gap: 0;
  cursor: pointer;
}
.header-brand:hover .tagline { color: var(--text-primary); }
.header-eyebrow {
  font-size: 0.7rem;
  color: var(--text-secondary);
  margin: 0.2rem 0 0 0;
  font-weight: 500;
  letter-spacing: 0.02em;
}
.btn-text {
  font-size: 0.9rem;
  padding: 0.35rem 0.5rem;
}
.btn-text:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.3);
  border-radius: 4px;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.section-head .section-title { margin-bottom: 0; }
.agent-empty-hint .empty-text { margin: 0 0 0.75rem; }
.agent-empty-hint .agent-empty-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.agent-empty-hint .agent-empty-actions a { text-decoration: none; }
.task-card__batch-check {
  display: inline-flex;
  align-items: center;
  margin-right: 0.5rem;
}
.task-card__batch-check input { margin: 0; }
.task-detail-completion-submission { margin-top: 1rem; padding: 0.75rem; background: var(--surface, rgba(255,255,255,0.05)); border-radius: 8px; }
.task-detail-completion-submission .completion-summary { margin: 0 0 0.5rem; white-space: pre-wrap; font-size: 0.9rem; color: var(--text-secondary); }
.task-detail-completion-submission .completion-link { margin: 0; font-size: 0.9rem; }
.draft-bar-global { background: rgba(var(--primary-rgb, 34, 197, 94), 0.08); border-color: rgba(var(--primary-rgb), 0.25); }
.badge--skill-token { background: rgba(34, 197, 94, 0.15); color: var(--primary-color); font-size: 0.7rem; }
.form-inline--agent { flex-wrap: wrap; }
.form-inline--agent .input { min-width: 10rem; }
/* NOTE: translated comment in English. */
.home-playbook-cta {
  margin-bottom: var(--space-6);
  padding: var(--space-5) var(--space-6);
  border-radius: var(--radius-xl);
  border: var(--border-hairline);
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.08), rgba(59, 130, 246, 0.06));
}
.home-playbook-cta__tagline {
  margin: 0 0 var(--space-4);
  font-size: var(--font-body);
  color: var(--text-secondary);
  line-height: 1.55;
  max-width: 52rem;
}
.home-playbook-cta__actions { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.task-badge-collab {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: rgba(59, 130, 246, 0.22);
  color: rgba(191, 219, 254, 0.98);
  vertical-align: middle;
}
.subscribe-preflight { margin-bottom: var(--space-4); text-align: left; }
.subscribe-preflight-list { margin: var(--space-2) 0 0 var(--space-4); padding: 0; font-size: var(--font-caption); color: var(--text-secondary); line-height: 1.5; }
.subscribe-preflight-links { margin-top: var(--space-2); }
.home-dashboard { margin-bottom: var(--space-6, 1.5rem); }
.home-kpi { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-3, 0.75rem); margin-bottom: var(--space-5, 1.25rem); }
@media (min-width: 640px) { .home-kpi { grid-template-columns: repeat(4, 1fr); } }
.home-kpi-card {
  padding: 1rem 1.25rem;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255,255,255,0.06);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06);
  transition: background var(--duration-m) var(--ease-apple), transform var(--duration-m) var(--ease-apple), box-shadow var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple);
}
.home-kpi-card:hover {
  background: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.10);
  transform: translateY(-1px);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06), 0 14px 30px rgba(0,0,0,0.18);
}
.home-kpi-value { display: block; font-size: 1.5rem; font-weight: 800; letter-spacing: -0.03em; color: var(--primary-color); }
.home-kpi-label { display: block; margin-top: 0.25rem; font-size: 0.78rem; font-weight: 500; color: var(--text-secondary); }
.home-kpi-skeleton { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem; }
@media (min-width: 640px) { .home-kpi-skeleton { grid-template-columns: repeat(4, 1fr); } }
.home-kpi-skeleton .tw-skeleton { height: 4rem; border-radius: 8px; }
.home-dash-row { display: grid; grid-template-columns: 1fr; gap: 1rem; }
@media (min-width: 900px) { .home-dash-row { grid-template-columns: 1fr 320px; } }
.home-dash-feed .card-content, .home-dash-leaderboard .card-content, .home-sidebar-feed .card-content { padding: 1rem 1.25rem; }
.home-dash-feed-title { font-size: 1rem; font-weight: 600; margin: 0 0 0.75rem; }
.home-activity-list { list-style: none; padding: 0; margin: 0; }
.home-activity-item {
  display: grid;
  grid-template-columns: 4.5rem 1fr auto;
  gap: 0.6rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  font-size: 0.85rem;
  align-items: start;
}
.home-activity-item:last-child { border-bottom: none; }
.home-activity-time { color: rgba(255,255,255,0.55); font-size: 0.75rem; }
.home-activity-text { color: var(--text-primary); line-height: 1.35; }
.home-activity-skeleton .tw-skeleton { background: var(--surface); }
.home-leaderboard-list { display: flex; flex-direction: column; gap: 0.25rem; }
.home-leaderboard-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.4rem 0; font-size: 0.9rem; }
.home-lb-rank { font-weight: 600; color: var(--primary-color); min-width: 1.5rem; }
.home-lb-name { flex: 1; min-width: 0; }
.home-lb-earned { font-weight: 600; color: var(--primary-color); }
.home-lb-earned .unit { font-size: 0.8em; font-weight: 400; color: var(--text-secondary); }
.home-leaderboard-skeleton .tw-skeleton { background: var(--surface); }
.mt-2 { margin-top: 0.5rem; }

/* NOTE: translated comment in English. */
.home-task-list--grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  align-items: stretch;
}
@media (min-width: 640px) {
  .home-task-list--grid { grid-template-columns: repeat(2, 1fr); }
}
@media (min-width: 1024px) {
  .home-task-list--grid { grid-template-columns: repeat(3, 1fr); }
}
.home-task-list--skeleton {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}
@media (min-width: 640px) {
  .home-task-list--skeleton { grid-template-columns: repeat(2, 1fr); }
}
@media (min-width: 1024px) {
  .home-task-list--skeleton { grid-template-columns: repeat(3, 1fr); }
}
.home-task-skeleton-card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.home-task-skeleton-line { display: block; }
.home-task-skeleton-line--title { width: 75%; height: 1.25rem; }
.home-task-skeleton-line--desc { width: 100%; height: 1rem; }
.home-task-skeleton-line--meta { width: 50%; height: 0.875rem; }
.home-load-more {
  margin-top: 1.5rem;
  text-align: center;
  grid-column: 1 / -1;
}

/* NOTE: translated comment in English. */
.home-task-list--grid .home-task-card {
  padding: 24px; /* 8px 栅格 */
}
.home-task-list--grid .home-task-card {
  border-radius: var(--radius-xl);
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06);
}
.home-task-list--grid .home-task-card .task-card__top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.home-task-list--grid .home-task-card .home-task-card__title {
  font-weight: 600;
  font-size: 1rem;
  line-height: 1.35;
  margin: 0 0 8px 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.home-task-list--grid .home-task-card .home-task-card__desc {
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--text-secondary);
  margin: 0 0 8px 0;
  min-width: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.home-task-list--grid .home-task-card .home-task-card__requirements {
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--text-tertiary, var(--text-secondary));
  margin: 0 0 12px 0;
}
.home-task-list--grid .home-task-card .home-task-card__attrs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}
.home-task-list--grid .home-task-card .home-task-card__attrs .task-attr {
  font-variant-numeric: tabular-nums;
}
.home-task-list--grid .home-task-card .home-task-card__meta {
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--text-secondary);
  margin: 0;
}
.home-task-list--grid .home-task-card .task-card__actions-wrap {
  margin-top: var(--space-5);
  padding-top: var(--space-5);
  border-top: 1px solid var(--border-muted);
  gap: var(--space-2);
}
.home-task-list--grid .home-task-card .task-actions {
  gap: var(--space-2);
}
/* NOTE: translated comment in English. */
.home-task-list--grid .home-task-card.task-card--hover:hover {
  transform: translateY(-2px);
  border-color: rgba(255,255,255,0.10);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06), 0 18px 40px rgba(0,0,0,0.24);
}

/* NOTE: translated comment in English. */
.guest-hint-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding: 0.75rem 1rem;
  background: rgba(var(--primary-rgb), 0.12);
  border-bottom: 1px solid rgba(var(--primary-rgb), 0.25);
  color: var(--text-primary);
  font-size: 0.9375rem;
}
.guest-hint-banner span { flex: 1; min-width: 0; }
.guest-register-curl {
  margin: var(--space-4) 0;
  padding: var(--space-4);
  background: rgba(0,0,0,0.25);
  border-radius: var(--radius-md);
  white-space: pre-wrap;
  font-size: 0.85rem;
  line-height: 1.5;
  overflow-x: auto;
}
.guest-register-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); }

.task-pulse-banner {
  padding: 0.65rem 1rem;
  background: linear-gradient(90deg, rgba(var(--primary-rgb), 0.14), rgba(99, 102, 241, 0.08));
  border-bottom: 1px solid rgba(var(--primary-rgb), 0.22);
  font-size: 0.875rem;
}
.task-pulse-banner__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
}
.task-pulse-banner__title {
  font-weight: 600;
  color: var(--text-primary);
  margin-right: 0.25rem;
}
.pulse-chip {
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 0.8125rem;
  color: var(--text-secondary);
}
.pulse-chip--accent {
  border-color: rgba(var(--primary-rgb), 0.35);
  color: var(--text-primary);
}
.pulse-chip--warn {
  border-color: rgba(251, 146, 60, 0.45);
  color: #fdba74;
}
.task-pulse-banner__cta {
  margin-left: auto;
  font-weight: 600;
  color: var(--primary-color, #a78bfa);
  text-decoration: none;
}
.task-pulse-banner__cta:hover {
  text-decoration: underline;
}
.pulse-chip--link {
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}
.pulse-chip--link:hover {
  filter: brightness(1.08);
}

.home-trust-strip {
  margin: 0 0 1.25rem 0;
  padding: 1rem 1.25rem;
  border-radius: var(--radius-xl);
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
}
.home-trust-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: 1fr;
}
@media (min-width: 900px) {
  .home-trust-grid {
    grid-template-columns: 1fr 1fr 1fr;
    align-items: start;
  }
}
.home-trust-item strong {
  display: block;
  font-size: 0.9rem;
  margin-bottom: 0.35rem;
  color: var(--text-primary);
}
.home-trust-item p {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--text-secondary);
}
.home-trust-calc-label {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  margin-bottom: 0.35rem;
  color: var(--text-primary);
}
.home-trust-calc-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.home-trust-calc-input {
  max-width: 8rem;
}
.home-trust-calc-result {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.task-badge-escrow {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.2rem 0.45rem;
  border-radius: 6px;
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.35);
  color: #86efac;
}

/* 顶栏「任务管理」：争议优先强提示，其余待办弱提示 */
.header-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  align-items: flex-start;
}
.nav-group--primary .nav-group-links {
  gap: 0.25rem;
}
.nav-group--primary .nav-link--primary {
  font-weight: 600;
  padding: 0.5rem 0.75rem;
}
.nav-overflow-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2.25rem;
  min-height: 2.25rem;
  padding: 0.5rem 0.65rem;
  color: var(--text-secondary);
  border-radius: var(--radius-md, 8px);
}
.nav-overflow-btn:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.06);
}
.nav-overflow-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.35);
}
.command-palette-hint {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--text-tertiary, rgba(255, 255, 255, 0.5));
  padding-inline: 0.5rem;
}
.command-palette-hint:hover {
  color: var(--text-secondary);
}
.nav-overflow-sheet-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  width: 100%;
}
.nav-overflow-sheet-title {
  margin: 0;
  font-size: var(--font-body);
  font-weight: 650;
  color: var(--text-primary);
}
.nav-overflow-close {
  min-width: 2rem;
  min-height: 2rem;
  padding: 0;
  font-size: 1.1rem;
  line-height: 1;
}
.nav-overflow-links {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.nav-overflow-link {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.55rem 0.75rem;
  border-radius: var(--radius-md, 8px);
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  transition: background 0.15s ease, color 0.15s ease;
}
.nav-overflow-link:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.06);
}
.nav-overflow-link.active {
  color: var(--text-primary);
  background: rgba(var(--primary-rgb), 0.12);
}
.task-pulse-banner--reduce-motion .pulse-chip,
.task-pulse-banner--reduce-motion .pulse-chip--link {
  animation: none !important;
  transition: none;
}
.nav-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 12rem;
}
.nav-group-title {
  margin: 0;
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-tertiary, rgba(255, 255, 255, 0.5));
}
.nav-group-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.nav-link--tasks {
  position: relative;
  padding-inline-end: 0.45rem;
}
.nav-link--community {
  position: relative;
  padding-inline-end: 0.45rem;
}
.nav-task-dispute-dot {
  position: absolute;
  top: 0.12rem;
  right: 0;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: linear-gradient(145deg, #fb923c, #ef4444);
  box-shadow: 0 0 0 2px #0a0a0b;
  pointer-events: none;
}
.nav-task-pulse-dot {
  position: absolute;
  top: 0.18rem;
  right: 0.05rem;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(var(--primary-rgb), 0.92);
  box-shadow: 0 0 0 2px #0a0a0b;
  pointer-events: none;
}
.nav-community-dot {
  position: absolute;
  top: 0.18rem;
  right: 0.05rem;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(168, 85, 247, 0.95);
  box-shadow: 0 0 0 2px #0a0a0b;
  pointer-events: none;
}
@media (max-width: 1200px) {
  .nav-group { min-width: 10rem; }
}
@media (max-width: 900px) {
  .nav-group {
    min-width: 100%;
  }
}
@media (prefers-reduced-motion: reduce) {
  .nav-overflow-link {
    transition: none;
  }
  .task-pulse-banner .pulse-chip,
  .task-pulse-banner .pulse-chip--link {
    animation: none !important;
    transition: none;
  }
}
</style>

<style>
.page-fade-enter-active,
.page-fade-leave-active {
  transition:
    opacity 200ms var(--ease-apple, ease),
    transform 200ms var(--ease-apple, ease);
}
/* Leaving view is taken out of flow so the entering view占据正常位置，避免切换时的布局跳动；
   不使用 mode="out-in"，防止快速切路由时离场动画被打断导致页面空白。 */
.page-fade-leave-active {
  position: absolute;
  inset: 0;
  width: 100%;
  pointer-events: none;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
  pointer-events: none;
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
  pointer-events: none;
}
@media (prefers-reduced-motion: reduce) {
  .page-fade-enter-active,
  .page-fade-leave-active {
    transition: none;
  }
  .page-fade-enter-from,
  .page-fade-leave-to {
    transform: none;
  }
}
</style>
