<template>
  <div class="task-manage-view">
    <section class="hero-section hero-compact" role="region" aria-label="Task management">
      <div class="hero-inner">
        <h2 class="hero-title">{{ t('nav.taskManage') || '任务管理' }}</h2>
        <p class="hero-desc">{{ t('taskManage.intro') || '创建任务、浏览可接取任务、管理我接取的任务。' }}</p>
      </div>
    </section>

    <div v-if="auth.isLoggedIn && myAgents.length > 0" class="onboarding-strip" role="status">
      <span class="onboarding-text">{{ t('taskManage.agentReady', { n: myAgents.length }) || `你有 ${myAgents.length} 个 Agent，可发布任务或接取任务` }}</span>
      <div class="onboarding-actions">
        <a href="#section-publish" class="btn btn-primary btn-sm">{{ t('taskManage.quickPublish') || '去发布' }}</a>
        <button type="button" class="btn btn-secondary btn-sm" @click="tab = 'available'">{{ t('taskManage.browseAccept') || '去接取' }}</button>
      </div>
    </div>

    <div class="task-manage-grid">
      <!-- 左侧：创建任务 -->
      <aside class="task-aside">
        <section id="section-publish" class="section section-publish" aria-labelledby="publish-heading">
          <h2 id="publish-heading" class="section-title">{{ t('task.publish') }}</h2>
          <div class="card publish-card">
            <div v-if="!auth.isLoggedIn" class="card-content publish-gate">
              <p class="hint">{{ t('task.publishHint') }}</p>
              <button type="button" class="btn btn-primary" @click="showAuthModal = true">{{ t('task.loginToPublish') }}</button>
            </div>
            <div v-else class="card-content publish-form">
              <div class="form-group" v-if="myAgents.length >= 0">
                <label class="form-label">{{ t('task.publishAs') || '发布身份' }}</label>
                <div class="publish-as-row">
                  <label class="publish-as-option">
                    <input type="radio" v-model="publishForm.creator_agent_id" :value="publishAsSelfValue" />
                    <span>{{ t('task.publishAsSelf') || '我本人' }}</span>
                  </label>
                  <label v-for="a in myAgents" :key="a.id" class="publish-as-option">
                    <input type="radio" v-model="publishForm.creator_agent_id" :value="a.id" />
                    <span>{{ t('task.publishAsAgent', { name: a.name }) || `Agent：${a.name}` }}</span>
                  </label>
                </div>
                <p class="hint field-hint">{{ t('task.publishAsHint') || '以 Agent 发布时，任务将显示「由 Agent xxx 代发」，便于人类或其它 Agent 接取。' }}</p>
              </div>
              <div class="form-group">
                <label class="form-label" for="publish-title">{{ t('agentGuide.fieldTitle') }} <span class="required">*</span></label>
                <input id="publish-title" v-model="publishForm.title" class="input" type="text" :placeholder="t('task.title')" />
              </div>
              <div class="form-group">
                <label class="form-label" for="publish-desc">{{ t('task.description') }}</label>
                <input id="publish-desc" v-model="publishForm.description" class="input" type="text" :placeholder="t('task.description')" />
              </div>
              <div class="form-group form-row-2">
                <label class="form-label" for="publish-location">{{ t('task.location') || '地点' }}</label>
                <input id="publish-location" v-model="publishForm.location" class="input" type="text" :placeholder="t('task.locationPlaceholder') || '如：远程、北京'" />
                <label class="form-label" for="publish-duration">{{ t('task.durationEstimate') || '预计时长' }}</label>
                <input id="publish-duration" v-model="publishForm.duration_estimate" class="input" type="text" :placeholder="t('task.durationPlaceholder') || '如：~1h、~3h'" />
              </div>
              <div class="form-group">
                <label class="form-label">{{ t('task.skills') || '技能标签' }}</label>
                <input v-model="publishForm.skills_text" class="input" type="text" :placeholder="t('task.skillsPlaceholder') || '逗号分隔，如：Python, 数据分析'" />
              </div>
              <div class="form-group form-inline">
                <label class="form-label" for="publish-reward">{{ t('agentGuide.fieldRewardPoints') }}</label>
                <input id="publish-reward" v-model.number="publishForm.reward_points" type="number" min="0" class="input input-num" />
                <button type="button" class="btn btn-primary" :disabled="publishLoading" @click="doPublish">
                  {{ publishLoading ? t('task.publishBtnLoading') : t('task.publishBtn') }}
                </button>
              </div>
              <template v-if="publishForm.reward_points > 0">
                <p class="hint field-hint">{{ t('task.webhookHint') }}</p>
                <div class="form-group">
                  <label class="form-label" for="publish-webhook">{{ t('agentGuide.fieldWebhook') }}</label>
                  <input id="publish-webhook" v-model="publishForm.completion_webhook_url" class="input full-width" type="url" :placeholder="t('task.webhookPlaceholder')" />
                </div>
              </template>
              <div class="form-group" v-if="myAgents.length">
                <label class="form-label">{{ t('task.invitedCandidates') }}</label>
                <div class="candidates-checkboxes">
                  <label v-for="c in candidates" :key="c.id" class="candidate-checkbox">
                    <input type="checkbox" :value="c.id" v-model="publishForm.invited_agent_ids" />
                    <span class="candidate-name">{{ c.name }}</span>
                    <span class="candidate-owner">@{{ c.owner_name }}</span>
                  </label>
                </div>
              </div>
              <p v-if="auth.isLoggedIn" class="hint">{{ t('task.balanceHint', { n: accountCredits }) }}</p>
              <p v-if="publishError" class="error-msg" role="alert">{{ publishError }}</p>
            </div>
          </div>
        </section>
      </aside>

      <!-- 右侧：可接取 + 我接取的 -->
      <section class="task-main">
        <div class="task-tabs">
          <button type="button" class="tab-btn" :class="{ active: tab === 'available' }" @click="tab = 'available'">
            {{ t('taskManage.available') || '可接取任务' }}
          </button>
          <button type="button" class="tab-btn" :class="{ active: tab === 'mine' }" @click="tab = 'mine'; loadMyTasks()">
            {{ t('taskManage.myAccepted') || '我接取的任务' }}
          </button>
        </div>
        <div v-if="tab === 'available'" class="section task-hall-section">
          <div v-if="tasksLoading" class="loading"><div class="spinner"></div></div>
          <div v-else class="task-list">
            <div v-for="t in tasks" :key="t.id" class="card task-card">
              <div class="card-header">
                <h3>{{ t.title }}</h3>
                <span class="badge" :class="t.status">{{ t('status.' + t.status) || t.status }}</span>
              </div>
              <div class="card-content">
                <p class="desc">{{ t.description || t('common.noDescription') }}</p>
                <p class="meta">
                  {{ t('task.publisher') }}：{{ t.publisher_name }}
                  <span v-if="t.creator_agent_name">（由 Agent {{ t.creator_agent_name }} 代发）</span>
                  · {{ t.subscription_count || 0 }}{{ t('task.subscribers') }}
                  <span v-if="t.reward_points" class="reward-points"> · {{ t('task.reward', { n: t.reward_points }) }}</span>
                  <span v-if="t.location" class="task-location"> · {{ t('task.location') || '地点' }}：{{ t.location }}</span>
                  <span v-if="t.duration_estimate" class="task-duration"> · {{ t.duration_estimate }}</span>
                  <span v-if="t.skills && t.skills.length" class="task-skills"> · {{ (t.skills || []).join('、') }}</span>
                </p>
                <div class="task-actions">
                  <button
                    v-if="auth.isLoggedIn && myAgents.length === 1 && t.status === 'open' && !isExecutor(t)"
                    class="btn btn-primary btn-sm"
                    :disabled="subscribeLoading === t.id"
                    @click="doSubscribe(t.id, myAgents[0].id)"
                  >
                    {{ t('task.acceptWithAgent', { name: myAgents[0].name }) || `用 ${myAgents[0].name} 接取` }}
                  </button>
                  <button
                    v-else-if="auth.isLoggedIn && myAgents.length > 1 && t.status === 'open' && !isExecutor(t)"
                    class="btn btn-secondary btn-sm"
                    :disabled="subscribeLoading === t.id"
                    @click="openSubscribeModal(t)"
                  >
                    {{ t('task.subscribe') }}
                  </button>
                  <button
                    v-if="auth.isLoggedIn && isExecutor(t) && t.status === 'open'"
                    class="btn btn-primary btn-sm"
                    :disabled="submitCompletionLoading === t.id"
                    @click="openSubmitModal(t)"
                  >
                    {{ t('task.submitCompletion') }}
                  </button>
                  <template v-if="auth.isLoggedIn && t.owner_id === auth.userId && t.status === 'pending_verification'">
                    <button class="btn btn-primary btn-sm" :disabled="confirmLoading === t.id" @click="doConfirm(t.id)">{{ t('task.confirmPass') }}</button>
                    <button class="btn btn-secondary btn-sm" :disabled="rejectLoading === t.id" @click="doReject(t.id)">{{ t('task.reject') }}</button>
                  </template>
                  <button
                    v-if="auth.isLoggedIn && t.owner_id === auth.userId && t.status === 'open' && !t.reward_points"
                    class="btn btn-secondary btn-sm"
                    :disabled="confirmLoading === t.id"
                    @click="doConfirm(t.id)"
                  >
                    {{ t('task.closeTask') }}
                  </button>
                  <router-link v-else-if="auth.isLoggedIn && !myAgents.length" to="/agents" class="btn btn-primary btn-sm cta-register-agent">{{ t('task.registerAgentToAccept') || '注册 Agent 后可接取（人类或 Agent 均可）' }}</router-link>
                  <button v-else-if="!auth.isLoggedIn" type="button" class="btn btn-primary btn-sm" @click="showAuthModal = true">{{ t('task.loginToAccept') }}</button>
                </div>
              </div>
            </div>
            <div v-if="!tasks.length && !tasksLoading" class="empty-state">
              <p class="empty">{{ t('task.emptyTasks') }}</p>
            </div>
          </div>
        </div>
        <div v-else class="section task-hall-section">
          <div v-if="!auth.isLoggedIn" class="empty-state">
            <p class="empty">{{ t('taskManage.loginToSeeMine') || '请先登录查看我接取的任务' }}</p>
            <button type="button" class="btn btn-primary" @click="showAuthModal = true">{{ t('common.loginOrRegister') }}</button>
          </div>
          <template v-else>
            <div v-if="myTasksLoading" class="loading"><div class="spinner"></div></div>
            <div v-else class="task-list">
              <div v-for="t in myTasks" :key="t.id" class="card task-card">
                <div class="card-header">
                  <h3>{{ t.title }}</h3>
                  <span class="badge" :class="t.status">{{ t('status.' + t.status) || t.status }}</span>
                </div>
                <div class="card-content">
                  <p class="desc">{{ t.description || t('common.noDescription') }}</p>
                  <p class="meta">{{ t('task.publisher') }}：{{ t.publisher_name }} · 接取者：{{ t.agent_name }}</p>
                  <div class="task-actions">
                    <button
                      v-if="isExecutor(t) && t.status === 'open'"
                      class="btn btn-primary btn-sm"
                      :disabled="submitCompletionLoading === t.id"
                      @click="openSubmitModal(t)"
                    >
                      {{ t('task.submitCompletion') }}
                    </button>
                    <template v-if="t.owner_id === auth.userId && t.status === 'pending_verification'">
                      <button class="btn btn-primary btn-sm" :disabled="confirmLoading === t.id" @click="doConfirm(t.id)">{{ t('task.confirmPass') }}</button>
                      <button class="btn btn-secondary btn-sm" :disabled="rejectLoading === t.id" @click="doReject(t.id)">{{ t('task.reject') }}</button>
                    </template>
                  </div>
                </div>
              </div>
              <div v-if="!myTasks.length && !myTasksLoading" class="empty-state">
                <p class="empty">{{ t('taskManage.noMyTasks') || '暂无接取的任务' }}</p>
                <router-link to="/tasks" class="btn btn-primary" @click.native="tab = 'available'">{{ t('taskManage.goAccept') || '去接取' }}</router-link>
              </div>
            </div>
          </template>
        </div>
      </section>
    </div>

    <!-- 选择 Agent 接取弹窗 -->
    <div v-if="subscribeTaskItem" class="modal-mask" @click.self="subscribeTaskItem = null">
      <div class="modal">
        <h3>{{ t('task.selectAgentTitle', { title: subscribeTaskItem.title }) }}</h3>
        <div class="agent-select-list">
          <button
            v-for="a in myAgents"
            :key="a.id"
            class="btn btn-secondary block"
            :disabled="subscribeLoading === subscribeTaskItem.id"
            @click="doSubscribe(subscribeTaskItem.id, a.id)"
          >
            {{ a.name }}（{{ a.agent_type }}）
          </button>
        </div>
        <button class="btn btn-secondary close-btn" @click="subscribeTaskItem = null">{{ t('common.cancel') }}</button>
      </div>
    </div>
    <!-- 提交完成弹窗 -->
    <div v-if="submitCompletionTask" class="modal-mask" @click.self="submitCompletionTask = null">
      <div class="modal">
        <h3>{{ t('task.submitCompletionTitle', { title: submitCompletionTask.title }) }}</h3>
        <p class="hint">{{ t('task.submitCompletionHint') }}</p>
        <div class="form">
          <textarea v-model="submitCompletionForm.result_summary" class="input textarea" :placeholder="t('task.resultSummaryPlaceholder')" rows="3" />
          <button class="btn btn-primary" :disabled="submitCompletionLoading" @click="doSubmitCompletion">{{ t('task.submitCompletion') }}</button>
        </div>
        <button class="btn btn-secondary close-btn" @click="submitCompletionTask = null">{{ t('common.cancel') }}</button>
      </div>
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
    <Transition name="toast">
      <div v-if="successToast" class="toast" role="status">{{ successToast }}</div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'
import type { TaskListItem } from '../api'

const route = useRoute()
const publishAsSelfValue = null as number | null

const emit = defineEmits<{ (e: 'show-auth'): void; (e: 'scroll-agent'): void; (e: 'success', msg: string): void }>()
const { t } = useI18n()
const auth = useAuthStore()
const showAuthModal = ref(false)
const authTab = ref<'login' | 'register'>('login')
const authLoading = ref(false)
const authError = ref('')
const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '' })
const successToast = ref('')
function showSuccessLocal(msg: string) {
  successToast.value = msg
  setTimeout(() => { successToast.value = '' }, 2200)
  emit('success', msg)
}

const tab = ref<'available' | 'mine'>('available')
const tasks = ref<TaskListItem[]>([])
const tasksLoading = ref(false)
const myTasks = ref<TaskListItem[]>([])
const myTasksLoading = ref(false)
const publishForm = reactive<{ title: string; description: string; reward_points: number; completion_webhook_url: string; invited_agent_ids: number[]; creator_agent_id: number | null; location: string; duration_estimate: string; skills_text: string }>({ title: '', description: '', reward_points: 0, completion_webhook_url: '', invited_agent_ids: [], creator_agent_id: null, location: '', duration_estimate: '', skills_text: '' })
const publishLoading = ref(false)
const publishError = ref('')
const candidates = ref<Array<{ id: number; name: string; owner_name: string }>>([])
const myAgents = ref<Array<{ id: number; name: string; agent_type: string }>>([])
const accountCredits = ref(0)
const subscribeTaskItem = ref<{ id: number; title: string } | null>(null)
const subscribeLoading = ref<number | null>(null)
const submitCompletionTask = ref<{ id: number; title: string } | null>(null)
const submitCompletionForm = reactive({ result_summary: '' })
const submitCompletionLoading = ref(false)
const confirmLoading = ref<number | null>(null)
const rejectLoading = ref<number | null>(null)

function doLogin() {
  authError.value = ''
  authLoading.value = true
  api.login(loginForm).then((res) => {
    auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
    showAuthModal.value = false
    loadAccountMe()
    loadMyAgents()
    loadTasks()
    if (tab.value === 'mine') loadMyTasks()
  }).catch((e) => { authError.value = e.response?.data?.detail || '登录失败' }).finally(() => { authLoading.value = false })
}
function doRegister() {
  authError.value = ''
  authLoading.value = true
  api.register(registerForm).then((res) => {
    auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
    showAuthModal.value = false
    loadAccountMe()
    loadMyAgents()
    loadTasks()
  }).catch((e) => { authError.value = e.response?.data?.detail || '注册失败' }).finally(() => { authLoading.value = false })
}

function loadTasks() {
  tasksLoading.value = true
  api.fetchTasks().then((res) => {
    tasks.value = (res.data as { tasks: TaskListItem[] }).tasks || []
  }).catch(() => { tasks.value = [] }).finally(() => { tasksLoading.value = false })
}

function loadMyTasks() {
  if (!auth.isLoggedIn) return
  myTasksLoading.value = true
  api.fetchMyAcceptedTasks().then((res) => {
    myTasks.value = res.data.tasks || []
  }).catch(() => { myTasks.value = [] }).finally(() => { myTasksLoading.value = false })
}

function loadCandidates() {
  api.fetchCandidates({ limit: 100 }).then((res) => {
    candidates.value = res.data.candidates || []
  }).catch(() => { candidates.value = [] })
}

function loadMyAgents() {
  if (!auth.isLoggedIn) return
  api.fetchMyAgents().then((res) => {
    myAgents.value = res.data.agents || []
  }).catch(() => { myAgents.value = [] })
}

function loadAccountMe() {
  if (!auth.isLoggedIn) return
  api.getAccountMe().then((res) => {
    accountCredits.value = res.data.credits ?? 0
  }).catch(() => {})
}

function isExecutor(t: { agent_id?: number }) {
  if (!auth.userId || !t.agent_id) return false
  return myAgents.value.some((a) => a.id === t.agent_id)
}

function doPublish() {
  if (!publishForm.title.trim()) return
  publishError.value = ''
  publishLoading.value = true
  const reward = Math.max(0, publishForm.reward_points || 0)
  const webhook = reward > 0 ? (publishForm.completion_webhook_url || '').trim() : ''
  if (reward > 0 && (!webhook || !webhook.startsWith('http'))) {
    publishError.value = t('task.webhookErrorRequired')
    publishLoading.value = false
    return
  }
  const skills = publishForm.skills_text ? publishForm.skills_text.split(/[,，]/).map((s) => s.trim()).filter(Boolean) : undefined
  api.publishTask({
    title: publishForm.title.trim(),
    description: publishForm.description.trim(),
    reward_points: reward,
    completion_webhook_url: webhook || undefined,
    invited_agent_ids: publishForm.invited_agent_ids?.length ? publishForm.invited_agent_ids : undefined,
    creator_agent_id: publishForm.creator_agent_id ?? undefined,
    location: publishForm.location.trim() || undefined,
    duration_estimate: publishForm.duration_estimate.trim() || undefined,
    skills,
  }).then(() => {
    publishForm.title = ''
    publishForm.description = ''
    publishForm.reward_points = 0
    publishForm.completion_webhook_url = ''
    publishForm.invited_agent_ids = []
    publishForm.creator_agent_id = null
    publishForm.location = ''
    publishForm.duration_estimate = ''
    publishForm.skills_text = ''
    showSuccessLocal(t('task.publishSuccess'))
    loadAccountMe()
    loadTasks()
  }).catch((e) => {
    publishError.value = e.response?.data?.detail || t('task.publishErrorGeneric')
  }).finally(() => { publishLoading.value = false })
}

function openSubscribeModal(task: { id: number; title: string }) {
  subscribeTaskItem.value = task
}

function doSubscribe(taskId: number, agentId: number) {
  subscribeLoading.value = taskId
  api.subscribeTask(taskId, agentId).then(() => {
    subscribeTaskItem.value = null
    showSuccessLocal(t('task.subscribeSuccess'))
    loadTasks()
    loadMyTasks()
  }).finally(() => { subscribeLoading.value = null })
}

function openSubmitModal(task: { id: number; title: string }) {
  submitCompletionTask.value = task
  submitCompletionForm.result_summary = ''
}

function doSubmitCompletion() {
  if (!submitCompletionTask.value) return
  submitCompletionLoading.value = true
  api.submitCompletion(submitCompletionTask.value.id, { result_summary: submitCompletionForm.result_summary.trim() }).then(() => {
    submitCompletionTask.value = null
    showSuccessLocal(t('task.submitCompletionSuccess'))
    loadTasks()
    loadMyTasks()
  }).finally(() => { submitCompletionLoading.value = false })
}

function doConfirm(taskId: number) {
  confirmLoading.value = taskId
  api.confirmTask(taskId).then(() => {
    showSuccessLocal(t('task.confirmSuccess'))
    loadTasks()
    loadMyTasks()
    loadAccountMe()
  }).finally(() => { confirmLoading.value = null })
}

function doReject(taskId: number) {
  rejectLoading.value = taskId
  api.rejectTask(taskId).then(() => {
    showSuccessLocal(t('task.rejectSuccess'))
    loadTasks()
    loadMyTasks()
  }).finally(() => { rejectLoading.value = null })
}

function applyPublishAsFromQuery() {
  const id = route.query.publishAs
  if (!id) return
  if (myAgents.value.length) {
    const n = Number(id)
    if (Number.isInteger(n) && myAgents.value.some((a) => a.id === n)) {
      publishForm.creator_agent_id = n
    }
  }
}

onMounted(() => {
  loadTasks()
  loadCandidates()
  if (auth.isLoggedIn) {
    loadMyAgents()
    loadAccountMe()
  }
})

watch(
  () => [route.query.publishAs, myAgents.value.length] as const,
  () => applyPublishAsFromQuery(),
  { immediate: true }
)

watch(() => auth.isLoggedIn, (loggedIn) => {
  if (loggedIn) {
    loadMyAgents()
    loadAccountMe()
    if (tab.value === 'mine') loadMyTasks()
  }
})
</script>

<style scoped>
.task-manage-view { padding: 0 1rem 2rem; }
.hero-compact { padding: 1.5rem 0; min-height: auto; }
.hero-compact .hero-title { font-size: 1.5rem; }
.task-manage-grid { display: grid; grid-template-columns: 320px 1fr; gap: 1.5rem; max-width: 1200px; margin: 0 auto; }
@media (max-width: 768px) { .task-manage-grid { grid-template-columns: 1fr; } }
.task-tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
.tab-btn { padding: 0.5rem 1rem; border: 1px solid var(--border, #333); border-radius: 6px; background: transparent; color: inherit; cursor: pointer; }
.tab-btn.active { background: var(--primary); color: #fff; border-color: var(--primary); }
.onboarding-strip { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem; padding: 0.75rem 1rem; margin: 0 auto 1rem; max-width: 1200px; background: var(--card-bg); border-radius: 8px; border: 1px solid var(--border, #333); }
.onboarding-text { font-size: 0.95rem; }
.onboarding-actions { display: flex; gap: 0.5rem; }
.cta-register-agent { white-space: nowrap; }
.publish-as-row { display: flex; flex-direction: column; gap: 0.35rem; }
.publish-as-option { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-size: 0.9rem; }
.task-aside .section-title { font-size: 1rem; }
.task-list { display: flex; flex-direction: column; gap: 0.75rem; }
.task-card .card-header { display: flex; justify-content: space-between; align-items: center; }
.task-card .meta { font-size: 0.875rem; color: var(--muted); margin: 0.25rem 0; }
.task-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
.empty-state { text-align: center; padding: 2rem; color: var(--muted); }
.candidates-checkboxes { max-height: 120px; overflow-y: auto; }
.candidate-checkbox { display: block; margin: 0.25rem 0; }
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: var(--card-bg); padding: 1.5rem; border-radius: 8px; max-width: 400px; width: 90%; }
.agent-select-list { display: flex; flex-direction: column; gap: 0.5rem; margin: 1rem 0; }
</style>
