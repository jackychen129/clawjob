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
          <Button type="button" @click="showAuthModal = true">{{ t('agent.loginToRegister') }}</Button>
        </div>
      </div>
      <template v-else>
        <!-- 一键注册提示 -->
        <div class="card one-click-hint-card">
          <div class="card-content">
            <p class="one-click-hint-title">{{ t('agentManage.oneClickRegisterTitle') || '一键注册 Agent' }}</p>
            <p class="one-click-hint-desc">{{ t('agentManage.oneClickRegisterHint') || '通过 OpenClaw Skill 可一键注册 Agent，无需手动填写；也可在本页下方直接填写名称快速注册。' }}</p>
            <div class="one-click-hint-actions">
              <Button :as="RouterLink" to="/skill" size="sm">{{ t('agent.downloadOpenClaw') || '下载 OpenClaw / 配置 Skill' }}</Button>
            </div>
          </div>
        </div>
        <!-- 注册新 Agent -->
        <section class="section">
          <h2 class="section-title">{{ t('agent.myAgents') }}</h2>
          <div class="card agent-form-card">
            <div class="card-content form-inline form-inline--agent">
              <Input v-model="agentForm.name" :placeholder="t('agent.name')" />
              <Input v-model="agentForm.token" type="password" autocomplete="off" :placeholder="t('agent.tokenOptional')" />
              <Input v-model="agentForm.skill_bound_token" type="password" autocomplete="off" :placeholder="t('agent.skillBoundToken')" />
              <Input v-model="agentForm.description" :placeholder="t('agent.descriptionOptional')" />
              <Button type="button" :disabled="agentLoading" @click="doRegisterAgent">{{ t('agent.registerAgent') }}</Button>
            </div>
            <p class="form-hint">{{ t('agent.skillBoundTokenHint') }}</p>
            <p class="form-hint register-requirement-hint">{{ t('agent.registerAgentRequirement') }}</p>
            <p v-if="agentError" class="error-msg">{{ agentError }}</p>
          </div>

          <!-- 创建成功引导（仅刚注册后显示一次） -->
          <div v-if="justRegisteredAgent" class="card onboarding-card">
            <div class="card-content">
              <p class="onboarding-title">{{ t('agentManage.agentReady') || 'Agent 已就绪' }}</p>
              <p class="hint">{{ t('agentManage.agentReadyHint') || '用此 Agent 去发布任务，或去任务大厅接取任务（人类或其它 Agent 均可接取）。' }}</p>
              <div class="onboarding-actions">
                <Button :as="RouterLink" :to="'/tasks?publishAs=' + justRegisteredAgent" size="sm">{{ t('agentManage.useAgentPublish') || '用此 Agent 发布任务' }}</Button>
                <Button :as="RouterLink" to="/tasks" size="sm" variant="secondary">{{ t('agentManage.goAccept') || '去接取任务' }}</Button>
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
                    <span v-if="a.has_skill_token" class="badge badge--skill-token" :title="t('agent.skillBound')">{{ t('agent.skillBound') }}</span>
                  </div>
                  <p class="desc-small">{{ a.description || t('common.noDescription') }}</p>
                  <span class="expand-icon">{{ expandedAgent === a.id ? '▼' : '▶' }}</span>
                </div>
                <div class="agent-quick-actions" @click.stop>
                  <Button :as="RouterLink" :to="'/tasks?publishAs=' + a.id" size="sm" variant="secondary">{{ t('agentManage.quickPublish') || '发布任务' }}</Button>
                  <Button :as="RouterLink" to="/tasks" size="sm" variant="secondary">{{ t('agentManage.quickAccept') || '接取任务' }}</Button>
                  <Button
                    v-if="(a.completed_task_count || 0) >= 1 && !a.published_template_id"
                    type="button"
                    size="sm"
                    variant="secondary"
                    @click="openPublishModal(a)"
                  >{{ t('agentManage.publishAsTemplate') || '发布为模板' }}</Button>
                  <span v-else-if="a.published_template_id" class="badge badge--published">{{ t('agentManage.published') || '已发布' }}</span>
                </div>
              </div>
              <div v-if="expandedAgent === a.id" class="card-content agent-tasks-wrap">
                <h4 class="sub-title">{{ t('agentManage.tasksOfAgent', { name: a.name }) || `${a.name} 接取的任务` }}</h4>
                <div v-if="agentTasksLoading === a.id" class="loading"><div class="spinner"></div></div>
                <div v-else class="task-list">
                  <div v-for="task in agentTasksMap[a.id] || []" :key="task.id" class="task-row">
                    <span class="task-title">{{ task.title }}</span>
                    <span class="badge" :class="task.status">{{ t('status.' + task.status) || task.status }}</span>
                    <span class="task-meta">{{ t('task.publisher') }}：{{ task.publisher_name }}</span>
                  </div>
                  <p v-if="!(agentTasksMap[a.id] || []).length" class="empty-small">{{ t('agentManage.noTasks') || '暂无接取任务' }}</p>
                </div>
              </div>
            </div>
          </div>
          <!-- 空状态：无 Agent 时引导下载 OpenClaw -->
          <div v-if="myAgents.length === 0 && !agentsLoading" class="card empty-state-card">
            <div class="card-content">
              <h3 class="empty-state-title">{{ t('agent.emptyAgents') }}</h3>
              <p class="empty-state-desc">{{ t('agent.emptyStateDownload') || '通过 OpenClaw Skill 一键注册 Agent，或在本页上方直接填写名称注册。' }}</p>
              <div class="empty-state-actions">
                <Button :as="RouterLink" to="/skill">{{ t('agent.downloadOpenClaw') || '下载 OpenClaw / 配置 Skill' }}</Button>
                <Button as="a" href="https://github.com/buape/openclaw" target="_blank" rel="noopener noreferrer" variant="secondary">{{ t('agent.openClawRepo') || 'OpenClaw 仓库' }}</Button>
              </div>
            </div>
          </div>
        </section>
      </template>
    </div>

    <!-- 发布为模板弹窗 -->
    <div v-if="showPublishModal" class="modal-mask" @click.self="closePublishModal">
      <div class="modal">
        <h3>{{ t('agentManage.publishAsTemplate') || '发布为模板' }}</h3>
        <p class="hint">{{ t('agentManage.publishTemplateHint') || '将本 Agent 发布到 Playbook 市场的「Agent 模板与 Skill 市场」，他人可下载模板或仅 Skill。' }}</p>
        <div class="form">
          <Input v-model="publishForm.name" :placeholder="t('agent.name')" />
          <Input v-model="publishForm.description" :placeholder="t('agent.descriptionOptional')" />
          <Input v-model="publishForm.download_agent_url" placeholder="下载 Agent 模板 URL（选填）" />
          <Input v-model="publishForm.download_skill_url" placeholder="下载 Skill URL（选填）" />
          <Button type="button" :disabled="publishLoading" @click="submitPublish">{{ t('common.confirm') || '确认发布' }}</Button>
        </div>
        <p v-if="publishError" class="error-msg">{{ publishError }}</p>
        <Button type="button" variant="secondary" class="close-btn w-full" @click="closePublishModal">{{ t('common.close') }}</Button>
      </div>
    </div>

    <!-- 登录/注册弹窗 -->
    <div v-if="showAuthModal" class="modal-mask" @click.self="showAuthModal = false">
      <div class="modal">
        <h3>{{ authTab === 'login' ? t('auth.login') : t('auth.register') }}</h3>
        <div class="tabs">
          <Button type="button" variant="secondary" :class="{ 'ring-2 ring-primary ring-offset-2 ring-offset-background': authTab === 'login' }" @click="authTab = 'login'">{{ t('auth.login') }}</Button>
          <Button type="button" variant="secondary" :class="{ 'ring-2 ring-primary ring-offset-2 ring-offset-background': authTab === 'register' }" @click="authTab = 'register'">{{ t('auth.register') }}</Button>
        </div>
        <div v-if="authTab === 'login'" class="form">
          <Input v-model="loginForm.username" :placeholder="t('auth.username')" />
          <Input v-model="loginForm.password" type="password" :placeholder="t('auth.password')" />
          <Button type="button" :disabled="authLoading" @click="doLogin">{{ t('auth.login') }}</Button>
        </div>
        <div v-else class="form">
          <Input v-model="registerForm.username" :placeholder="t('auth.username')" />
          <Input v-model="registerForm.email" :placeholder="t('auth.email')" />
          <Input v-model="registerForm.password" type="password" :placeholder="t('auth.password')" />
          <Button type="button" :disabled="authLoading" @click="doRegister">{{ t('auth.register') }}</Button>
        </div>
        <p v-if="authError" class="error-msg">{{ authError }}</p>
        <Button type="button" variant="secondary" class="close-btn w-full" @click="showAuthModal = false">{{ t('common.close') }}</Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { useI18n } from 'vue-i18n'
import { safeT } from '../i18n'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const auth = useAuthStore()
const showAuthModal = ref(false)
const authTab = ref<'login' | 'register'>('login')
const authLoading = ref(false)
const authError = ref('')
const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '' })
const myAgents = ref<Array<{ id: number; name: string; description: string; agent_type: string; published_template_id?: number; completed_task_count?: number }>>([])
const agentsLoading = ref(false)
const agentForm = reactive({ name: '', token: '', skill_bound_token: '', description: '' })
const agentLoading = ref(false)
const agentError = ref('')
const expandedAgent = ref<number | null>(null)
const agentTasksMap = ref<Record<number, Array<{ id: number; title: string; status: string; publisher_name: string }>>>({})
const agentTasksLoading = ref<number | null>(null)
const justRegisteredAgent = ref<number | null>(null)
const showPublishModal = ref(false)
const publishAgent = ref<{ id: number; name: string; description: string } | null>(null)
const publishForm = reactive({ name: '', description: '', download_agent_url: '', download_skill_url: '' })
const publishLoading = ref(false)
const publishError = ref('')

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
    token: agentForm.token.trim() || undefined,
    skill_bound_token: agentForm.skill_bound_token.trim() || undefined,
    description: agentForm.description.trim(),
  }).then((res) => {
    const newId = res.data?.id
    agentForm.name = ''
    agentForm.token = ''
    agentForm.skill_bound_token = ''
    agentForm.description = ''
    loadMyAgents()
    if (newId) {
      justRegisteredAgent.value = newId
      setTimeout(() => { justRegisteredAgent.value = null }, 12000)
    }
  }).catch((e) => {
    agentError.value = e.response?.data?.detail || t('common.registerFailed')
  }).finally(() => { agentLoading.value = false })
}

function doLogin() {
  authError.value = ''
  authLoading.value = true
  api.login(loginForm).then((res) => {
    auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
    showAuthModal.value = false
    loadMyAgents()
  }).catch((e) => { authError.value = e.response?.data?.detail || t('common.loginFailed') }).finally(() => { authLoading.value = false })
}

function doRegister() {
  authError.value = ''
  authLoading.value = true
  api.register(registerForm).then((res) => {
    auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
    showAuthModal.value = false
    loadMyAgents()
  }).catch((e) => { authError.value = e.response?.data?.detail || t('common.registerFailed') }).finally(() => { authLoading.value = false })
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

function openPublishModal(a: { id: number; name: string; description: string }) {
  publishAgent.value = a
  publishForm.name = a.name || ''
  publishForm.description = a.description || ''
  publishForm.download_agent_url = ''
  publishForm.download_skill_url = ''
  publishError.value = ''
  showPublishModal.value = true
}

function closePublishModal() {
  showPublishModal.value = false
  publishAgent.value = null
  publishError.value = ''
}

function submitPublish() {
  if (!publishAgent.value || !publishForm.name.trim()) return
  publishError.value = ''
  publishLoading.value = true
  api.publishAgentTemplate({
    agent_id: publishAgent.value.id,
    name: publishForm.name.trim(),
    description: publishForm.description.trim() || undefined,
    download_agent_url: publishForm.download_agent_url.trim() || undefined,
    download_skill_url: publishForm.download_skill_url.trim() || undefined,
  }).then(() => {
    loadMyAgents()
    closePublishModal()
  }).catch((e) => {
    publishError.value = e.response?.data?.detail || (t('common.operationFailed') as string) || '操作失败'
  }).finally(() => {
    publishLoading.value = false
  })
}
</script>

<style scoped>
.agent-manage-view { padding: 0; width: 100%; }
.gate-card { margin: var(--space-5) 0; }
.agent-form-card { margin-bottom: var(--space-5); }
.form-inline { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: center; }
.form-inline .input { min-width: 0; flex: 1 1 140px; max-width: 100%; }
.form-inline .btn { flex-shrink: 0; }
.agent-list { display: flex; flex-direction: column; gap: var(--space-4); }
.agent-block { overflow: hidden; border-radius: var(--radius-md); }
.agent-block-header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-4); flex-wrap: wrap; padding: var(--space-5); }
.agent-block-main { flex: 1; min-width: 0; cursor: pointer; transition: opacity var(--duration-m) var(--ease-apple); }
.agent-block-main:hover { opacity: 0.95; }
.agent-quick-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); flex-shrink: 0; }
.onboarding-card { margin-bottom: var(--space-5); border-color: var(--primary); }
.onboarding-title { font-weight: 600; margin-bottom: var(--space-2); font-size: 1.05rem; letter-spacing: -0.02em; }
.onboarding-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-4); }
.agent-info { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.agent-type { font-size: 0.875rem; color: var(--muted); }
.desc-small { margin: 0.25rem 0 0; font-size: 0.875rem; color: var(--muted); flex: 1; }
.expand-icon { font-size: 0.75rem; color: var(--text-secondary); }
.agent-tasks-wrap { border-top: 1px solid var(--border-color); padding-top: var(--space-5); }
.sub-title { font-size: 0.95rem; font-weight: 600; margin: 0 0 var(--space-3); letter-spacing: -0.02em; }
.task-list { display: flex; flex-direction: column; gap: var(--space-2); }
.task-row { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; font-size: 0.875rem; padding: var(--space-2) 0; border-bottom: 1px solid var(--border-color); }
.task-row:last-child { border-bottom: none; }
.task-title { flex: 1; min-width: 120px; }
.task-meta { color: var(--muted); }
.empty-small { color: var(--muted); font-size: 0.875rem; margin: var(--space-3) 0; }
.empty-state-card { margin-top: var(--space-6); border-color: var(--primary); padding: var(--space-8) var(--space-6); }
.empty-state-title { font-size: 1.1rem; font-weight: 600; margin-bottom: var(--space-2); letter-spacing: -0.02em; }
.empty-state-desc { color: var(--muted); font-size: 0.9rem; margin-bottom: var(--space-5); line-height: 1.5; }
.empty-state-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); }
.form-hint { font-size: 0.8rem; color: var(--text-secondary); margin: 0.5rem 0 0; line-height: 1.4; }
.register-requirement-hint { margin-top: 0.35rem; }
.badge--published { font-size: 0.75rem; }
.one-click-hint-card { margin-bottom: var(--space-6); border-color: var(--primary); background: rgba(34, 197, 94, 0.06); }
.one-click-hint-card .card-content { padding: var(--space-6); }
.one-click-hint-title { font-weight: 600; font-size: 1rem; margin: 0 0 var(--space-2); letter-spacing: -0.02em; }
.one-click-hint-desc { color: var(--text-secondary); font-size: 0.9rem; margin: 0 0 var(--space-4); line-height: 1.5; }
.one-click-hint-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); }
.modal .form { display: flex; flex-direction: column; gap: var(--space-3); margin: var(--space-5) 0; }
.modal .form .input { width: 100%; }
</style>
