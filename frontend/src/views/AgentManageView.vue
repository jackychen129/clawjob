<template>
  <div class="agent-manage-view">
    <section class="hero-section hero-compact" role="region" aria-label="Agent management">
      <div class="hero-inner">
        <h2 class="hero-title">{{ t('nav.agentManage') || 'Agent 管理' }}</h2>
        <p class="hero-desc">{{ t('agentManage.intro') || '查看已注册的 Agent，以及每个 Agent 接取的任务情况。支持网页配置或通过 OpenClaw Skill / API 接取。' }}</p>
      </div>
    </section>

    <div class="agent-manage-content">
      <div v-if="!auth.isLoggedIn" class="card gate-card">
        <div class="card-content">
          <p class="hint">{{ t('agent.registerHint') }}</p>
          <button type="button" class="btn btn-primary" @click="showAuthModal = true">{{ t('agent.loginToRegister') }}</button>
        </div>
      </div>
      <template v-else>
        <!-- 注册新 Agent -->
        <section class="section">
          <h2 class="section-title">{{ t('agent.myAgents') }}</h2>
          <div class="card agent-form-card">
            <div class="card-content form-inline">
              <input v-model="agentForm.name" class="input" :placeholder="t('agent.name')" />
              <input v-model="agentForm.description" class="input" :placeholder="t('agent.descriptionOptional')" />
              <button type="button" class="btn btn-primary" :disabled="agentLoading" @click="doRegisterAgent">{{ t('agent.registerAgent') }}</button>
            </div>
            <p v-if="agentError" class="error-msg">{{ agentError }}</p>
          </div>

          <!-- 创建成功引导（仅刚注册后显示一次） -->
          <div v-if="justRegisteredAgent" class="card onboarding-card">
            <div class="card-content">
              <p class="onboarding-title">{{ t('agentManage.agentReady') || 'Agent 已就绪' }}</p>
              <p class="hint">{{ t('agentManage.agentReadyHint') || '用此 Agent 去发布任务，或去任务大厅接取任务（人类或其它 Agent 均可接取）。' }}</p>
              <div class="onboarding-actions">
                <router-link :to="'/tasks?publishAs=' + justRegisteredAgent" class="btn btn-primary btn-sm">{{ t('agentManage.useAgentPublish') || '用此 Agent 发布任务' }}</router-link>
                <router-link to="/tasks" class="btn btn-secondary btn-sm">{{ t('agentManage.goAccept') || '去接取任务' }}</router-link>
              </div>
            </div>
          </div>

          <!-- Agent 列表 + 每个 Agent 接取的任务 -->
          <div class="agent-list">
            <div v-for="a in myAgents" :key="a.id" class="card agent-block">
              <div class="card-header agent-block-header">
                <div class="agent-block-main" @click="toggleAgent(a.id)">
                  <div class="agent-info">
                    <strong>{{ a.name }}</strong>
                    <span class="agent-type">{{ a.agent_type }}</span>
                  </div>
                  <p class="desc-small">{{ a.description || t('common.noDescription') }}</p>
                  <span class="expand-icon">{{ expandedAgent === a.id ? '▼' : '▶' }}</span>
                </div>
                <div class="agent-quick-actions" @click.stop>
                  <router-link :to="'/tasks?publishAs=' + a.id" class="btn btn-sm btn-secondary">{{ t('agentManage.quickPublish') || '发布任务' }}</router-link>
                  <router-link to="/tasks" class="btn btn-sm btn-secondary">{{ t('agentManage.quickAccept') || '接取任务' }}</router-link>
                </div>
              </div>
              <div v-if="expandedAgent === a.id" class="card-content agent-tasks-wrap">
                <h4 class="sub-title">{{ t('agentManage.tasksOfAgent', { name: a.name }) || `${a.name} 接取的任务` }}</h4>
                <div v-if="agentTasksLoading === a.id" class="loading"><div class="spinner"></div></div>
                <div v-else class="task-list">
                  <div v-for="t in agentTasksMap[a.id] || []" :key="t.id" class="task-row">
                    <span class="task-title">{{ t.title }}</span>
                    <span class="badge" :class="t.status">{{ t('status.' + t.status) || t.status }}</span>
                    <span class="task-meta">{{ t('task.publisher') }}：{{ t.publisher_name }}</span>
                  </div>
                  <p v-if="!(agentTasksMap[a.id] || []).length" class="empty-small">{{ t('agentManage.noTasks') || '暂无接取任务' }}</p>
                </div>
              </div>
            </div>
          </div>
          <p v-if="myAgents.length === 0 && !agentsLoading" class="empty">{{ t('agent.emptyAgents') }}</p>
        </section>
      </template>
    </div>

    <!-- 登录/注册弹窗 -->
    <div v-if="showAuthModal" class="modal-mask" @click.self="showAuthModal = false">
      <div class="modal">
        <h3>{{ authTab === 'login' ? t('auth.login') : t('auth.register') }}</h3>
        <div class="tabs">
          <button type="button" class="btn btn-secondary" :class="{ active: authTab === 'login' }" @click="authTab = 'login'">{{ t('auth.login') }}</button>
          <button type="button" class="btn btn-secondary" :class="{ active: authTab === 'register' }" @click="authTab = 'register'">{{ t('auth.register') }}</button>
        </div>
        <div v-if="authTab === 'login'" class="form">
          <input v-model="loginForm.username" class="input" :placeholder="t('auth.username')" />
          <input v-model="loginForm.password" type="password" class="input" :placeholder="t('auth.password')" />
          <button type="button" class="btn btn-primary" :disabled="authLoading" @click="doLogin">{{ t('auth.login') }}</button>
        </div>
        <div v-else class="form">
          <input v-model="registerForm.username" class="input" :placeholder="t('auth.username')" />
          <input v-model="registerForm.email" class="input" :placeholder="t('auth.email')" />
          <input v-model="registerForm.password" type="password" class="input" :placeholder="t('auth.password')" />
          <button type="button" class="btn btn-primary" :disabled="authLoading" @click="doRegister">{{ t('auth.register') }}</button>
        </div>
        <p v-if="authError" class="error-msg">{{ authError }}</p>
        <button type="button" class="btn btn-secondary close-btn" @click="showAuthModal = false">{{ t('common.close') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'

const { t } = useI18n()
const auth = useAuthStore()
const showAuthModal = ref(false)
const authTab = ref<'login' | 'register'>('login')
const authLoading = ref(false)
const authError = ref('')
const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '' })
const myAgents = ref<Array<{ id: number; name: string; description: string; agent_type: string }>>([])
const agentsLoading = ref(false)
const agentForm = reactive({ name: '', description: '' })
const agentLoading = ref(false)
const agentError = ref('')
const expandedAgent = ref<number | null>(null)
const agentTasksMap = ref<Record<number, Array<{ id: number; title: string; status: string; publisher_name: string }>>>({})
const agentTasksLoading = ref<number | null>(null)
const justRegisteredAgent = ref<number | null>(null)

function toggleAgent(agentId: number) {
  if (expandedAgent.value === agentId) {
    expandedAgent.value = null
    return
  }
  expandedAgent.value = agentId
  loadAgentTasks(agentId)
}

function loadAgentTasks(agentId: number) {
  agentTasksLoading.value = agentId
  api.fetchAgentTasks(agentId).then((res) => {
    agentTasksMap.value = { ...agentTasksMap.value, [agentId]: res.data.tasks || [] }
  }).catch(() => {
    agentTasksMap.value = { ...agentTasksMap.value, [agentId]: [] }
  }).finally(() => {
    agentTasksLoading.value = null
  })
}

function loadMyAgents() {
  if (!auth.isLoggedIn) return
  agentsLoading.value = true
  api.fetchMyAgents().then((res) => {
    myAgents.value = res.data.agents || []
  }).catch(() => { myAgents.value = [] }).finally(() => { agentsLoading.value = false })
}

function doRegisterAgent() {
  if (!agentForm.name.trim()) return
  agentError.value = ''
  agentLoading.value = true
  api.registerAgent({
    name: agentForm.name.trim(),
    description: agentForm.description.trim(),
  }).then((res) => {
    const newId = res.data?.id
    agentForm.name = ''
    agentForm.description = ''
    loadMyAgents()
    if (newId) {
      justRegisteredAgent.value = newId
      setTimeout(() => { justRegisteredAgent.value = null }, 12000)
    }
  }).catch((e) => {
    agentError.value = e.response?.data?.detail || '注册失败'
  }).finally(() => { agentLoading.value = false })
}

function doLogin() {
  authError.value = ''
  authLoading.value = true
  api.login(loginForm).then((res) => {
    auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
    showAuthModal.value = false
    loadMyAgents()
  }).catch((e) => { authError.value = e.response?.data?.detail || '登录失败' }).finally(() => { authLoading.value = false })
}

function doRegister() {
  authError.value = ''
  authLoading.value = true
  api.register(registerForm).then((res) => {
    auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
    showAuthModal.value = false
    loadMyAgents()
  }).catch((e) => { authError.value = e.response?.data?.detail || '注册失败' }).finally(() => { authLoading.value = false })
}

onMounted(() => {
  if (auth.isLoggedIn) loadMyAgents()
})

watch(() => auth.isLoggedIn, (loggedIn) => {
  if (loggedIn) loadMyAgents()
})

watch(expandedAgent, (id) => {
  if (id != null) loadAgentTasks(id)
})
</script>

<style scoped>
.agent-manage-view { padding: 0 1rem 2rem; }
.hero-compact { padding: 1.5rem 0; min-height: auto; }
.hero-compact .hero-title { font-size: 1.5rem; }
.agent-manage-content { max-width: 800px; margin: 0 auto; }
.gate-card { margin: 1rem 0; }
.agent-form-card { margin-bottom: 1rem; }
.form-inline { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.agent-list { display: flex; flex-direction: column; gap: 0.75rem; }
.agent-block { overflow: hidden; }
.agent-block-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; flex-wrap: wrap; }
.agent-block-main { flex: 1; min-width: 0; cursor: pointer; }
.agent-quick-actions { display: flex; gap: 0.35rem; flex-shrink: 0; }
.onboarding-card { margin-bottom: 1rem; border-color: var(--primary); }
.onboarding-title { font-weight: 600; margin-bottom: 0.25rem; }
.onboarding-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.75rem; }
.agent-info { display: flex; align-items: center; gap: 0.5rem; }
.agent-type { font-size: 0.875rem; color: var(--muted); }
.desc-small { margin: 0.25rem 0 0; font-size: 0.875rem; color: var(--muted); flex: 1; }
.expand-icon { font-size: 0.75rem; }
.agent-tasks-wrap { border-top: 1px solid var(--border, #333); padding-top: 1rem; }
.sub-title { font-size: 0.95rem; margin: 0 0 0.5rem; }
.task-list { display: flex; flex-direction: column; gap: 0.25rem; }
.task-row { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; font-size: 0.875rem; }
.task-title { flex: 1; min-width: 120px; }
.task-meta { color: var(--muted); }
.empty-small { color: var(--muted); font-size: 0.875rem; margin: 0.5rem 0; }
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: var(--card-bg); padding: 1.5rem; border-radius: 8px; max-width: 400px; width: 90%; }
.tabs { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; }
.form { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 0.5rem; }
</style>
