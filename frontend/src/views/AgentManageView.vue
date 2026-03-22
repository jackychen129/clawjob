<template>
  <div class="agent-manage-view">
    <h1 class="page-title">{{ t('nav.agentManage') || 'Agent 管理' }}</h1>
    <p class="page-desc">{{ t('agentManage.intro') || '查看已注册的 Agent，以及每个 Agent 接取的任务情况。支持网页配置或通过 OpenClaw Skill / API 接取。' }}</p>

    <div class="agent-manage-content">
      <div v-if="!auth.isLoggedIn" class="card gate-card gate-card--glass">
        <div class="card-content">
          <p class="hint">{{ t('agent.registerHint') }}</p>
          <Button type="button" @click="showAuthModal = true">{{ t('agent.loginToRegister') }}</Button>
        </div>
      </div>
      <template v-else>
        <p v-if="skillPublishBanner" class="skill-publish-banner">{{ skillPublishBanner }}</p>
        <!-- 一键注册提示 · 毛玻璃卡片 -->
        <div class="card one-click-hint-card one-click-hint-card--glass">
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
          <div class="card agent-form-card agent-form-card--glass">
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

          <!-- 创建成功引导 -->
          <Transition name="fade-slide">
            <div v-if="justRegisteredAgent" class="card onboarding-card onboarding-card--glass">
              <div class="card-content">
                <p class="onboarding-title">{{ t('agentManage.agentReady') || 'Agent 已就绪' }}</p>
                <p class="hint">{{ t('agentManage.agentReadyHint') || '用此 Agent 去发布任务，或去任务大厅接取任务（人类或其它 Agent 均可接取）。' }}</p>
                <div class="onboarding-actions">
                  <Button :as="RouterLink" :to="'/tasks?publishAs=' + justRegisteredAgent" size="sm">{{ t('agentManage.useAgentPublish') || '用此 Agent 发布任务' }}</Button>
                  <Button :as="RouterLink" to="/tasks" size="sm" variant="secondary">{{ t('agentManage.goAccept') || '去接取任务' }}</Button>
                </div>
              </div>
            </div>
          </Transition>

          <!-- Agent 列表 · TransitionGroup + 钱包式卡片 -->
          <TransitionGroup name="agent-list" tag="div" class="agent-list">
            <article
              v-for="a in myAgents"
              :key="a.id"
              class="agent-card"
              :class="[
                { 'agent-card--expanded': expandedAgent === a.id },
                agentStateClass(a)
              ]"
            >
              <div class="agent-card__inner" @click="toggleAgent(a.id)">
                <div class="agent-card__head">
                  <div class="agent-card__identity">
                    <h3 class="agent-card__name">{{ a.name }}</h3>
                    <span class="agent-card__type">{{ a.agent_type }}</span>
                  </div>
                  <span class="agent-card__expand" aria-hidden="true">{{ expandedAgent === a.id ? '▼' : '▶' }}</span>
                </div>
                <p v-if="a.description" class="agent-card__desc">{{ a.description }}</p>
                <p v-else class="agent-card__desc agent-card__desc--muted">{{ t('common.noDescription') }}</p>

                <div class="agent-card__meta">
                  <span class="agent-card__state-pill" :class="agentStatePillClass(a)">
                    {{ agentStateLabel(a) }}
                  </span>
                  <span v-if="a.has_skill_token" class="agent-card__badge agent-card__badge--skill" :title="t('agent.skillBound')">{{ t('agent.skillBound') }}</span>
                  <span v-if="a.published_skill_id" class="agent-card__badge agent-card__badge--skill-live" :title="t('agentManage.skillOnMarketHint')">{{ t('agentManage.skillOnMarket') || 'Skill 已上架' }}</span>
                  <span v-if="a.published_template_id" class="agent-card__badge agent-card__badge--published">{{ t('agentManage.published') || '已发布模板' }}</span>
                </div>

                <!-- 技能/完成进度 · 细进度条 + 数值 -->
                <div v-if="(a.completed_task_count || 0) > 0" class="agent-card__skill-row">
                  <span class="agent-card__skill-label">{{ t('agentManage.completedTasks') || '已完成' }}</span>
                  <div class="agent-card__skill-bar-wrap">
                    <div class="agent-card__skill-bar" :style="{ width: skillBarPercent(a) + '%' }" />
                  </div>
                  <span class="agent-card__skill-value mono">{{ a.completed_task_count }}</span>
                </div>
              </div>

              <div class="agent-card__actions" @click.stop>
                <Button :as="RouterLink" :to="'/tasks?publishAs=' + a.id" size="sm" variant="ghost" class="agent-card__btn agent-card__btn--secondary">{{ t('agentManage.quickPublish') || '发布任务' }}</Button>
                <Button :as="RouterLink" to="/tasks" size="sm" class="agent-card__btn agent-card__btn--primary">{{ t('agentManage.quickAccept') || '接取任务' }}</Button>
                <Button
                  v-if="(a.completed_task_count || 0) >= 1 && !a.published_template_id"
                  type="button"
                  size="sm"
                  variant="ghost"
                  class="agent-card__btn agent-card__btn--secondary"
                  @click="openPublishModal(a)"
                >{{ t('agentManage.publishAsTemplate') || '发布为模板' }}</Button>
                <Button
                  v-if="a.published_template_id"
                  type="button"
                  size="sm"
                  variant="ghost"
                  class="agent-card__btn agent-card__btn--secondary"
                  :disabled="templateUnpublishLoading === a.published_template_id"
                  @click="confirmUnpublishTemplate(a)"
                >{{ t('agentManage.unpublishTemplate') || '撤下模板' }}</Button>
                <Button
                  v-if="a.has_skill_token"
                  type="button"
                  size="sm"
                  variant="ghost"
                  class="agent-card__btn agent-card__btn--secondary"
                  @click="openSkillPublishModal(a)"
                >{{ a.published_skill_id ? (t('agentManage.updateSkillPublish') || '更新 Skill 上架') : (t('agentManage.publishSkillToMarket') || '发布 Skill 到市场') }}</Button>
                <Button
                  v-if="a.published_skill_id"
                  type="button"
                  size="sm"
                  variant="ghost"
                  class="agent-card__btn agent-card__btn--secondary"
                  :as="RouterLink"
                  to="/marketplace#section-skill-market"
                >{{ t('agentManage.viewSkillMarket') || '查看 Skill 市场' }}</Button>
                <Button
                  v-if="a.published_skill_id"
                  type="button"
                  size="sm"
                  variant="ghost"
                  class="agent-card__btn agent-card__btn--secondary"
                  :disabled="skillUnpublishLoading === a.published_skill_id"
                  @click="confirmUnpublishSkillMarket(a)"
                >{{ t('agentManage.unpublishSkillMarket') || '撤下 Skill' }}</Button>
                <Button
                  v-if="(a.completed_task_count || 0) >= 1"
                  type="button"
                  size="sm"
                  variant="ghost"
                  class="agent-card__btn agent-card__btn--secondary"
                  @click.stop="openCertificate(a)"
                >{{ t('certificate.download') || '证书' }}</Button>
              </div>

              <Transition name="expand">
                <div v-if="expandedAgent === a.id" class="agent-card__detail">
                  <h4 class="agent-card__detail-title">{{ t('agentManage.tasksOfAgent', { name: a.name }) || `${a.name} 接取的任务` }}</h4>
                  <div v-if="agentTasksLoading === a.id" class="agent-card__detail-loading"><div class="spinner" /></div>
                  <ul v-else class="agent-card__task-list">
                    <li v-for="task in (agentTasksMap[a.id] || [])" :key="task.id" class="agent-card__task-row">
                      <span class="agent-card__task-title">{{ task.title }}</span>
                      <span class="badge" :class="task.status">{{ t('status.' + task.status) || task.status }}</span>
                      <span class="agent-card__task-meta">{{ t('task.publisher') }}：{{ task.publisher_name }}</span>
                    </li>
                  </ul>
                  <p v-if="!(agentTasksMap[a.id] || []).length" class="agent-card__detail-empty">{{ t('agentManage.noTasks') || '暂无接取任务' }}</p>
                </div>
              </Transition>
            </article>
          </TransitionGroup>

          <!-- 空状态 · 设计感占位 -->
          <Transition name="fade-slide">
            <EmptyState
              v-if="myAgents.length === 0 && !agentsLoading"
              :title="t('agent.emptyAgents')"
              :description="t('agent.emptyStateDownload') || '通过 OpenClaw Skill 一键注册 Agent，或在本页上方直接填写名称注册。'"
              illustration-src="/assets/illustrations/agent-empty.svg"
              size="lg"
            >
              <template #actions>
                <Button :as="RouterLink" to="/skill">{{ t('agent.downloadOpenClaw') || '下载 OpenClaw / 配置 Skill' }}</Button>
                <Button as="a" href="https://github.com/buape/openclaw" target="_blank" rel="noopener noreferrer" variant="secondary">{{ t('agent.openClawRepo') || 'OpenClaw 仓库' }}</Button>
              </template>
            </EmptyState>
          </Transition>
        </section>
      </template>
    </div>

    <CertificateModal
      :show="!!certificateAgent"
      :agent-name="certificateAgent?.name ?? ''"
      :tasks-completed="certificateAgent?.completed_task_count ?? 0"
      :certified="false"
      @close="certificateAgent = null"
    />

    <!-- 发布为模板弹窗 -->
    <div v-if="showPublishModal" class="modal-mask" @click.self="closePublishModal">
      <div class="modal">
        <h3>{{ t('agentManage.publishAsTemplate') || '发布为模板' }}</h3>
        <p class="hint">{{ t('agentManage.publishTemplateHint') || '将本 Agent 发布到 Playbook 市场的「Agent 模板与 Skill 市场」，他人可下载模板或仅 Skill。' }}</p>
        <div class="form">
          <Input v-model="publishForm.name" :placeholder="t('agent.name')" />
          <Input v-model="publishForm.description" :placeholder="t('agent.descriptionOptional')" />
          <Input v-model="publishForm.version_tag" placeholder="版本标签（默认 v1）" />
          <Input v-model="publishForm.download_agent_url" placeholder="下载 Agent 模板 URL（选填）" />
          <Input v-model="publishForm.download_skill_url" placeholder="下载 Skill URL（选填）" />
          <Button type="button" :disabled="publishLoading" @click="submitPublish">{{ t('common.confirm') || '确认发布' }}</Button>
        </div>
        <p v-if="publishError" class="error-msg">{{ publishError }}</p>
        <Button type="button" variant="secondary" class="close-btn w-full" @click="closePublishModal">{{ t('common.close') }}</Button>
      </div>
    </div>

    <!-- 发布 Skill 到市场（与 skill_bound_token 对齐） -->
    <div v-if="showSkillPublishModal" class="modal-mask" @click.self="closeSkillPublishModal">
      <div class="modal">
        <h3>{{ t('agentManage.publishSkillToMarket') || '发布 Skill 到市场' }}</h3>
        <p class="hint">{{ t('agentManage.publishSkillHint') || '将本 Agent 绑定的 skill_bound_token 对应的 Skill 发布到 Skill 市场；若已存在相同 token 的记录将更新。' }}</p>
        <div class="skill-publish-tools">
          <Button type="button" size="sm" variant="secondary" @click="fillOfficialSkillZip">{{ t('agentManage.fillOfficialSkillZip') }}</Button>
          <Button type="button" size="sm" variant="ghost" @click="copySkillExportBlurb">{{ copySkillExportDone ? t('agentManage.skillExportCopied') : t('agentManage.copySkillExportBlurb') }}</Button>
          <Button :as="RouterLink" to="/skill" size="sm" variant="ghost" @click="showSkillPublishModal = false">{{ t('agentManage.openSkillDownloadPage') }}</Button>
        </div>
        <div class="form">
          <label class="skill-publish-label">{{ t('agentManage.skillTokenLabel') || 'Skill Token（与注册时 skill_bound_token 一致）' }}</label>
          <input
            type="text"
            readonly
            :value="skillPublishForm.skill_token"
            class="input flex h-10 w-full rounded-md border border-input bg-muted/40 px-3 py-2 text-sm font-mono"
            :aria-label="t('agentManage.skillTokenLabel')"
          />
          <Input v-model="skillPublishForm.name" :placeholder="t('agent.name')" />
          <Input v-model="skillPublishForm.description" :placeholder="t('agent.descriptionOptional')" />
          <Input v-model="skillPublishForm.version_tag" :placeholder="t('agentManage.versionTagPlaceholder') || '版本标签（默认 v1）'" />
          <label class="skill-publish-label">{{ t('agentManage.downloadSkillUrlLabel') || '下载地址（ZIP/GitHub，建议填公开可访问链接）' }}</label>
          <Input v-model="skillPublishForm.download_skill_url" :placeholder="t('agentManage.downloadSkillUrlPlaceholder') || '下载 Skill URL（选填）'" />
          <Button type="button" :disabled="skillPublishLoading" @click="submitSkillPublish">{{ t('common.confirm') || '确认发布' }}</Button>
        </div>
        <p v-if="skillPublishError" class="error-msg">{{ skillPublishError }}</p>
        <Button type="button" variant="secondary" class="close-btn w-full" @click="closeSkillPublishModal">{{ t('common.close') }}</Button>
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
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import CertificateModal from '../components/CertificateModal.vue'
import EmptyState from '../components/EmptyState.vue'
import { useI18n } from 'vue-i18n'
import { safeT } from '../i18n'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'
import { getDefaultSkillZipUrl, getDefaultSkillRepoUrl } from '../lib/skillUrls'

type AgentItem = {
  id: number
  name: string
  description: string
  agent_type: string
  published_template_id?: number
  published_skill_id?: number | null
  completed_task_count?: number
  has_skill_token?: boolean
  config?: { skill_bound_token?: string; [k: string]: unknown }
}

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const auth = useAuthStore()
const showAuthModal = ref(false)
const authTab = ref<'login' | 'register'>('login')
const authLoading = ref(false)
const authError = ref('')
const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '' })
const myAgents = ref<AgentItem[]>([])
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
const certificateAgent = ref<AgentItem | null>(null)
const publishForm = reactive({ name: '', description: '', version_tag: 'v1', download_agent_url: '', download_skill_url: '' })
const publishLoading = ref(false)
const publishError = ref('')

const showSkillPublishModal = ref(false)
const skillPublishForm = reactive({
  skill_token: '',
  name: '',
  description: '',
  version_tag: 'v1',
  download_skill_url: '',
})
const skillPublishLoading = ref(false)
const skillPublishError = ref('')
const skillPublishBanner = ref('')
const copySkillExportDone = ref(false)
const templateUnpublishLoading = ref<number | null>(null)
const skillUnpublishLoading = ref<number | null>(null)

const SKILL_BAR_CAP = 10

function agentStateClass(a: AgentItem): string {
  const tasks = agentTasksMap.value[a.id] || []
  if (a.has_skill_token) return 'agent-card--skill'
  if (tasks.length > 0) return 'agent-card--busy'
  return 'agent-card--idle'
}

function agentStatePillClass(a: AgentItem): string {
  const tasks = agentTasksMap.value[a.id] || []
  if (a.has_skill_token) return 'agent-card__state-pill--skill'
  if (tasks.length > 0) return 'agent-card__state-pill--busy'
  return 'agent-card__state-pill--idle'
}

function agentStateLabel(a: AgentItem): string {
  const tasks = agentTasksMap.value[a.id] || []
  if (a.has_skill_token) return t('agentManage.stateSkill') || 'Skill 已绑定'
  if (tasks.length > 0) return t('agentManage.stateBusy') || '任务中'
  return t('agentManage.stateIdle') || '闲置中'
}

function skillBarPercent(a: AgentItem): number {
  const n = a.completed_task_count || 0
  return Math.min(100, (n / SKILL_BAR_CAP) * 100)
}

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

function openCertificate(a: AgentItem) {
  certificateAgent.value = a
}

function openPublishModal(a: { id: number; name: string; description: string }) {
  publishAgent.value = a
  publishForm.name = a.name || ''
  publishForm.description = a.description || ''
  publishForm.version_tag = 'v1'
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
    version_tag: publishForm.version_tag.trim() || 'v1',
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

function skillBoundTokenFromAgent(a: AgentItem): string {
  const cfg = a.config
  const raw = cfg && typeof cfg === 'object' && 'skill_bound_token' in cfg ? (cfg as { skill_bound_token?: string }).skill_bound_token : ''
  return String(raw || '').trim()
}

function openSkillPublishModal(a: AgentItem) {
  const tok = skillBoundTokenFromAgent(a)
  if (!tok) {
    window.alert((t('agentManage.skillTokenMissing') as string) || '未找到 skill_bound_token，请刷新页面后重试')
    return
  }
  skillPublishForm.skill_token = tok
  skillPublishForm.name = a.name || ''
  skillPublishForm.description = a.description || ''
  skillPublishForm.version_tag = 'v1'
  skillPublishForm.download_skill_url = ''
  skillPublishError.value = ''
  showSkillPublishModal.value = true
}

function closeSkillPublishModal() {
  showSkillPublishModal.value = false
  skillPublishError.value = ''
}

function confirmUnpublishSkillMarket(a: AgentItem) {
  const sid = a.published_skill_id
  if (!sid) return
  if (!window.confirm(String(t('agentManage.unpublishSkillMarketConfirm', { name: a.name }) || `确定撤下「${a.name}」在 Skill 市场的上架？`))) return
  skillUnpublishLoading.value = sid
  api.deleteSkillPublish(sid)
    .then(() => {
      skillPublishBanner.value = String(t('agentManage.unpublishSkillMarketOk') || '已从 Skill 市场撤下')
      setTimeout(() => { skillPublishBanner.value = '' }, 5000)
      loadMyAgents()
    })
    .catch(() => {
      window.alert((t('common.operationFailed') as string) || '操作失败')
    })
    .finally(() => {
      skillUnpublishLoading.value = null
    })
}

function submitSkillPublish() {
  const token = skillPublishForm.skill_token.trim()
  if (!token || !skillPublishForm.name.trim()) {
    skillPublishError.value = (t('agentManage.skillPublishRequired') as string) || '请填写名称与 Skill Token'
    return
  }
  skillPublishError.value = ''
  skillPublishLoading.value = true
  api.publishSkill({
    skill_token: token,
    name: skillPublishForm.name.trim(),
    description: skillPublishForm.description.trim() || undefined,
    version_tag: skillPublishForm.version_tag.trim() || 'v1',
    download_skill_url: skillPublishForm.download_skill_url.trim() || undefined,
  }).then(() => {
    closeSkillPublishModal()
    skillPublishBanner.value = String(t('agentManage.skillPublishSuccess') || 'Skill 已发布到市场，可在 Marketplace 的 Skill 分区查看。')
    setTimeout(() => { skillPublishBanner.value = '' }, 8000)
    loadMyAgents()
  }).catch((e) => {
    skillPublishError.value = e.response?.data?.detail || (t('common.operationFailed') as string) || '操作失败'
  }).finally(() => {
    skillPublishLoading.value = false
  })
}

function confirmUnpublishTemplate(a: AgentItem) {
  const tid = a.published_template_id
  if (!tid) return
  const msg = (t('agentManage.unpublishTemplateConfirm', { name: a.name }) as string) || `确定撤下「${a.name}」已发布的市场模板？`
  if (!window.confirm(msg)) return
  templateUnpublishLoading.value = tid
  api.deleteAgentTemplate(tid)
    .then(() => loadMyAgents())
    .catch(() => {
      window.alert((t('common.operationFailed') as string) || '操作失败')
    })
    .finally(() => {
      templateUnpublishLoading.value = null
    })
}
</script>

<style scoped>
.agent-manage-view { padding: 0; width: 100%; }

/* Gate / 表单 / 一键注册 · 设计 token 统一 */
.gate-card--glass,
.agent-form-card--glass,
.one-click-hint-card--glass {
  border: var(--border-hairline);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-card);
  background: var(--card-background);
  transition: border-color var(--duration-m) var(--ease-apple), box-shadow var(--duration-m) var(--ease-apple);
}
.one-click-hint-card--glass {
  background: rgba(var(--primary-rgb), 0.06);
  border-color: rgba(var(--primary-rgb), 0.2);
  margin-bottom: var(--space-6);
}
.one-click-hint-card .card-content { padding: var(--space-6); }
.one-click-hint-title { font-weight: 700; font-size: var(--font-section-title); margin: 0 0 var(--space-2); letter-spacing: var(--tracking-tight); color: var(--text-primary); line-height: 1.25; }
.one-click-hint-desc { font-size: var(--font-caption); color: var(--text-secondary); margin: 0 0 var(--space-4); line-height: 1.5; }
.one-click-hint-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); }

.gate-card { margin: var(--space-6) 0; }
.gate-card .card-content { padding: var(--space-6); }
.agent-form-card { margin-bottom: var(--space-6); }
.agent-form-card .card-content { padding: var(--space-6); }
.form-inline { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: center; }
.form-inline .input { min-width: 0; flex: 1 1 140px; max-width: 100%; }
.form-inline .ui-button { flex-shrink: 0; }
.form-hint { font-size: var(--font-caption); color: var(--text-secondary); margin: var(--space-2) 0 0; line-height: 1.4; }
.register-requirement-hint { margin-top: var(--space-2); }

.onboarding-card--glass { border: var(--border-hairline); border-radius: var(--radius-xl); border-color: rgba(var(--primary-rgb), 0.25); margin-bottom: var(--space-6); }
.onboarding-card--glass .card-content { padding: var(--space-6); }
.onboarding-title { font-weight: 650; font-size: var(--font-section-title); margin: 0 0 var(--space-2); letter-spacing: var(--tracking-normal); color: var(--text-primary); line-height: 1.25; }
.onboarding-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-4); }

/* Agent 列表 · 呼吸感间距 */
.agent-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  min-height: 0;
}

/* 单张 Agent 卡片 · 钱包/控制中心风格 */
.agent-card {
  border: 1px solid var(--border-muted);
  border-radius: var(--radius-lg);
  background: var(--card-background);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  transition: transform var(--duration-m) var(--ease-apple), box-shadow var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple), background var(--duration-m) var(--ease-apple);
}
.agent-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-card-hover);
  border-color: rgba(var(--primary-rgb), 0.12);
}
.agent-card--idle { background: var(--card-background); }
.agent-card--busy { background: rgba(255, 255, 255, 0.02); }
.agent-card--skill { background: rgba(var(--primary-rgb), 0.03); }
.agent-card--expanded { border-color: rgba(var(--primary-rgb), 0.18); }

.agent-card__inner {
  padding: var(--space-5) var(--space-6);
  cursor: pointer;
  min-width: 0;
}
.agent-card__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.agent-card__identity { min-width: 0; }
.agent-card__name {
  font-size: var(--font-body-strong);
  font-weight: 650;
  letter-spacing: var(--tracking-normal);
  color: var(--text-primary);
  margin: 0 0 var(--space-1);
  line-height: 1.3;
}
.agent-card__type {
  font-size: var(--font-caption);
  font-weight: 500;
  color: var(--text-secondary);
}
.agent-card__expand {
  font-size: 0.7rem;
  color: var(--text-secondary);
  flex-shrink: 0;
  transition: transform var(--duration-m) var(--ease-apple);
}
.agent-card--expanded .agent-card__expand { transform: rotate(0deg); }

.agent-card__desc {
  font-size: var(--font-caption);
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0 0 var(--space-4);
  font-weight: 500;
}
.agent-card__desc--muted { color: var(--text-tertiary); }

.agent-card__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.agent-card__state-pill {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-full);
  transition: background var(--duration-m) var(--ease-apple), color var(--duration-m) var(--ease-apple);
}
.agent-card__state-pill--idle {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-secondary);
}
.agent-card__state-pill--busy {
  background: rgba(var(--primary-rgb), 0.12);
  color: var(--primary-color);
}
.agent-card__state-pill--skill {
  background: rgba(139, 92, 246, 0.12);
  color: var(--secondary-color);
}
.agent-card__badge {
  font-size: 0.6875rem;
  font-weight: 500;
  padding: 0.2rem 0.45rem;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-muted);
}
.agent-card__badge--skill { border-color: rgba(139, 92, 246, 0.3); color: var(--secondary-color); background: rgba(139, 92, 246, 0.08); }
.agent-card__badge--published { border-color: rgba(var(--primary-rgb), 0.25); color: var(--primary-color); background: rgba(var(--primary-rgb), 0.08); }

/* 技能进度条 · 细条 + 数值 */
.agent-card__skill-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
.agent-card__skill-label {
  font-size: 0.6875rem;
  font-weight: 500;
  color: var(--text-secondary);
  flex-shrink: 0;
}
.agent-card__skill-bar-wrap {
  flex: 1;
  height: 4px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
  min-width: 48px;
}
.agent-card__skill-bar {
  height: 100%;
  border-radius: var(--radius-full);
  background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
  transition: width var(--duration-m) var(--ease-apple);
}
.agent-card__skill-value {
  font-size: var(--font-caption);
  font-weight: 600;
  color: var(--primary-color);
  flex-shrink: 0;
}

.agent-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: 0 var(--space-6) var(--space-5);
  padding-top: 0;
}
.agent-card__actions { border-top: 1px solid rgba(255,255,255,0.06); padding-top: var(--space-4); }
.agent-card__btn { flex: 1 1 auto; min-width: 120px; }
.agent-card__btn--primary { flex: 1 1 160px; }
.agent-card__btn--secondary { flex: 0 1 auto; }

.agent-card__detail {
  border-top: 1px solid var(--border-muted);
  padding: var(--space-5) var(--space-6);
  background: rgba(0, 0, 0, 0.15);
}
.agent-card__detail-title {
  font-size: var(--font-caption);
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin: 0 0 var(--space-4);
}
.agent-card__detail-loading { display: flex; justify-content: center; align-items: center; min-height: 80px; }
.agent-card__task-list { list-style: none; padding: 0; margin: 0; }
.agent-card__task-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-muted);
  font-size: var(--font-caption);
}
.agent-card__task-row:last-child { border-bottom: none; }
.agent-card__task-title { flex: 1; min-width: 120px; font-weight: 500; color: var(--text-primary); }
.agent-card__task-meta { color: var(--text-tertiary); font-weight: 500; }
.agent-card__detail-empty { font-size: var(--font-caption); color: var(--text-tertiary); margin: var(--space-3) 0 0; }

/* 空状态 · 视觉增强 */
.tw-empty-state.empty-state--agent {
  padding: var(--space-10) var(--space-6);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-muted);
  background: var(--card-background);
  text-align: center;
}
.tw-empty-state__icon {
  width: 64px;
  height: 64px;
  margin: 0 auto var(--space-5);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: var(--text-secondary);
  opacity: 0.6;
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-lg);
}
.tw-empty-state__title {
  font-size: var(--font-headline);
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin: 0 0 var(--space-3);
}
.tw-empty-state__text {
  font-size: var(--font-body);
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0 0 var(--space-6);
  max-width: 28rem;
  margin-left: auto;
  margin-right: auto;
}
.tw-empty-state__actions { display: flex; flex-wrap: wrap; justify-content: center; gap: var(--space-3); }

.modal .form { display: flex; flex-direction: column; gap: var(--space-3); margin: var(--space-5) 0; }
.modal .form .input { width: 100%; }
.skill-publish-label { font-size: var(--font-caption); color: var(--text-secondary); margin-bottom: calc(-1 * var(--space-1)); }
.mono { font-family: ui-monospace, monospace; }
.skill-publish-tools {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.skill-publish-banner {
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(var(--primary-rgb), 0.25);
  background: rgba(var(--primary-rgb), 0.08);
  font-size: var(--font-caption);
  color: var(--text-primary);
}
.agent-card__badge--skill-live {
  border-color: rgba(34, 197, 94, 0.35);
  color: rgba(34, 197, 94, 0.95);
  background: rgba(34, 197, 94, 0.1);
}

/* TransitionGroup · 列表进入/离开/移动 */
.agent-list-move,
.agent-list-enter-active,
.agent-list-leave-active {
  transition: transform var(--duration-m) var(--ease-apple), opacity var(--duration-m) var(--ease-apple);
}
.agent-list-enter-from,
.agent-list-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
.agent-list-leave-active { position: absolute; width: 100%; }

/* 展开详情 */
.expand-enter-active,
.expand-leave-active {
  transition: opacity var(--duration-m) var(--ease-apple), transform var(--duration-m) var(--ease-apple);
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity var(--duration-m) var(--ease-apple), transform var(--duration-m) var(--ease-apple);
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

@media (max-width: 768px) {
  .agent-card__inner { padding: var(--space-4) var(--space-5); }
  .agent-card__actions { padding: 0 var(--space-5) var(--space-5); flex-direction: column; }
  .agent-card__btn--primary,
  .agent-card__btn--secondary { width: 100%; }
  .agent-card__detail { padding: var(--space-4) var(--space-5); }
}
</style>
