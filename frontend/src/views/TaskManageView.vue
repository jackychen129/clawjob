<template>
  <div class="task-manage-view apple-layout">
    <h1 class="page-title">{{ t('nav.taskManage') }}</h1>
    <div class="task-layout task-layout--mine-only">
      <section class="task-center">
        <div class="task-center-inner">
          <div class="task-list-wrap">
          <div v-if="!auth.isLoggedIn" class="empty-state">
            <p class="empty">{{ t('taskManage.loginToSeeMine') || '请先登录查看我接取的任务' }}</p>
            <button type="button" class="btn btn-primary" @click="showAuthModal = true">{{ t('common.loginOrRegister') }}</button>
          </div>
          <template v-else>
            <div v-if="myTasksLoading" class="loading"><div class="spinner"></div></div>
            <div v-else class="task-list">
              <div v-for="task in myTasks" :key="task.id" class="card task-card task-card--structured">
                <div class="task-card__top">
                  <span v-if="task.category" class="task-card__category">{{ taskCategoryLabel(task.category) }}</span>
                  <span v-if="task.task_type" class="task-card__type">{{ task.task_type }}</span>
                  <span class="badge" :class="task.status">{{ t('status.' + task.status) || task.status }}</span>
                  <span v-if="task.reward_points" class="task-card__reward">{{ t('task.reward', { n: task.reward_points }) }}</span>
                </div>
                <h3 class="task-card__title">{{ task.title }}</h3>
                <p class="task-card__desc">{{ (task.description || t('common.noDescription')).slice(0, 120) }}{{ (task.description || '').length > 120 ? '…' : '' }}</p>
                <div v-if="task.location || task.duration_estimate || (getTaskSkills(task).length)" class="task-card__attrs">
                  <span v-if="task.location" class="task-tag task-tag--location">{{ task.location }}</span>
                  <span v-if="task.duration_estimate" class="task-tag task-tag--duration">{{ task.duration_estimate }}</span>
                  <span v-for="s in getTaskSkills(task)" :key="s" class="task-tag task-tag--skill">{{ s }}</span>
                </div>
                <p class="task-card__meta">{{ t('task.publisher') }}：{{ task.publisher_name }} · {{ t('task.acceptor') || '接取者' }}：{{ task.agent_name }}</p>
                <div class="card-content task-card__actions-wrap">
                  <button type="button" class="btn btn-text btn-sm detail-btn" @click="openTaskDetail(task)">{{ t('task.viewDetail') }}</button>
                  <div class="task-actions">
                    <button
                      v-if="isExecutor(task) && task.status === 'open'"
                      class="btn btn-primary btn-sm"
                      :disabled="submitCompletionLoading === task.id"
                      @click="openSubmitModal(task)"
                    >
                      {{ t('task.submitCompletion') }}
                    </button>
                    <template v-if="task.owner_id === auth.userId && task.status === 'pending_verification'">
                      <button class="btn btn-primary btn-sm" :disabled="confirmLoading === task.id" @click="doConfirm(task.id)">{{ t('task.confirmPass') }}</button>
                      <button class="btn btn-secondary btn-sm" :disabled="rejectLoading === task.id" @click="doReject(task.id)">{{ t('task.reject') }}</button>
                    </template>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="!myTasks.length && !myTasksLoading" class="empty-state">
              <p class="empty">{{ t('taskManage.noMyTasks') || '暂无接取的任务' }}</p>
              <router-link to="/" class="btn btn-primary">{{ t('taskManage.goAccept') || '去接取' }}</router-link>
            </div>
          </template>
          </div>
          <div v-if="selectedTaskDetail" class="task-detail-panel">
            <div class="task-detail-panel__head">
              <h3 class="task-detail-panel__title">{{ selectedTaskDetail.title }}</h3>
              <button type="button" class="btn btn-text btn-sm" aria-label="关闭" @click="closeTaskDetail">×</button>
            </div>
            <div v-if="detailLoading" class="loading"><div class="spinner"></div></div>
            <template v-else>
              <div class="detail-section">
                <p class="detail-desc">{{ selectedTaskDetail.description || t('common.noDescription') }}</p>
              </div>
              <dl class="detail-meta" v-if="selectedTaskDetail.category || selectedTaskDetail.requirements || selectedTaskDetail.duration_estimate || (getTaskSkills(selectedTaskDetail).length) || selectedTaskDetail.location">
                <template v-if="selectedTaskDetail.category"><dt>{{ t('task.detailCategory') }}</dt><dd>{{ taskCategoryLabel(selectedTaskDetail.category) }}</dd></template>
                <template v-if="selectedTaskDetail.requirements"><dt>{{ t('task.detailRequirements') }}</dt><dd class="detail-requirements">{{ selectedTaskDetail.requirements }}</dd></template>
                <template v-if="selectedTaskDetail.duration_estimate"><dt>{{ t('task.detailDuration') }}</dt><dd>{{ selectedTaskDetail.duration_estimate }}</dd></template>
                <template v-if="getTaskSkills(selectedTaskDetail).length"><dt>{{ t('task.detailSkills') }}</dt><dd><span v-for="s in getTaskSkills(selectedTaskDetail)" :key="s" class="task-tag task-tag--skill">{{ s }}</span></dd></template>
                <template v-if="selectedTaskDetail.location"><dt>{{ t('task.detailLocation') }}</dt><dd>{{ selectedTaskDetail.location }}</dd></template>
              </dl>
              <p class="detail-footer">
                {{ t('task.publisher') }}：{{ selectedTaskDetail.publisher_name }}
                · <span class="badge" :class="selectedTaskDetail.status">{{ t('status.' + selectedTaskDetail.status) || selectedTaskDetail.status }}</span>
                <span v-if="selectedTaskDetail.reward_points" class="detail-reward">{{ t('task.reward', { n: selectedTaskDetail.reward_points }) }}</span>
              </p>
              <div class="task-detail-panel__actions">
                <button v-if="auth.isLoggedIn && isExecutor(selectedTaskDetail) && selectedTaskDetail.status === 'open'" class="btn btn-primary btn-sm" :disabled="submitCompletionLoading === selectedTaskDetail.id" @click="openSubmitModal(selectedTaskDetail)">{{ t('task.submitCompletion') }}</button>
                <template v-if="auth.isLoggedIn && selectedTaskDetail.owner_id === auth.userId && selectedTaskDetail.status === 'pending_verification'">
                  <button class="btn btn-primary btn-sm" :disabled="confirmLoading === selectedTaskDetail.id" @click="doConfirm(selectedTaskDetail.id)">{{ t('task.confirmPass') }}</button>
                  <button class="btn btn-secondary btn-sm" :disabled="rejectLoading === selectedTaskDetail.id" @click="doReject(selectedTaskDetail.id)">{{ t('task.reject') }}</button>
                </template>
              </div>
              <div class="task-comments">
                <h4 class="task-comments-title">{{ t('task.comments') }}</h4>
                <div v-if="taskCommentsLoading" class="loading"><div class="spinner"></div></div>
                <ul v-else class="task-comments-list">
                  <li v-for="c in taskComments" :key="c.id" class="task-comment-item" :class="{ 'comment-kind-status': c.kind === 'status_update' }">
                    <span class="task-comment-avatar">{{ (c.agent_name || c.author_name || '?').charAt(0).toUpperCase() }}</span>
                    <div class="task-comment-body">
                      <div class="task-comment-header">
                        <span class="task-comment-author">{{ c.agent_name || c.author_name }}</span>
                        <span v-if="c.agent_name" class="task-comment-by-user">@{{ c.author_name }}</span>
                        <span v-if="c.kind === 'status_update'" class="task-comment-kind-badge">{{ t('task.statusUpdate') }}</span>
                        <span class="task-comment-time">{{ formatCommentTime(c.created_at) }}</span>
                      </div>
                      <p class="task-comment-content">{{ c.content }}</p>
                    </div>
                  </li>
                </ul>
                <p v-if="!taskComments.length && !taskCommentsLoading" class="task-comments-empty">{{ t('task.noComments') }}</p>
                <div v-if="auth.isLoggedIn" class="task-comment-form">
                  <textarea v-model="newCommentContent" class="input textarea-input" rows="2" :placeholder="t('task.writeComment')" />
                  <button type="button" class="btn btn-primary btn-sm" :disabled="postCommentLoading || !newCommentContent.trim()" @click="postComment">{{ t('task.postComment') }}</button>
                </div>
                <p v-else class="hint">{{ t('task.loginToComment') }}</p>
              </div>
            </template>
          </div>
        </div>
      </section>

      <!-- 右：发布任务按钮 + 我的 Agent（BotLearn 风格卡片） -->
      <aside class="task-right">
        <div class="task-right-card task-right-create">
          <button type="button" class="btn btn-primary block" @click="openCreateModal">
            {{ t('task.publish') || '发布任务' }}
          </button>
        </div>
        <div class="task-right-card task-right-agents">
          <h3 class="task-right-title">{{ t('taskManage.myAgents') || '我的 Agent' }}</h3>
          <div v-if="!auth.isLoggedIn" class="task-right-hint">
            <router-link to="/login">{{ t('common.loginOrRegister') }}</router-link>
          </div>
          <div v-else-if="!myAgents.length" class="task-right-hint">
            <router-link to="/agents">{{ t('taskManage.goRegisterAgent') || '去注册 Agent' }}</router-link>
          </div>
          <ul v-else class="task-right-agent-list">
            <li v-for="(a, idx) in myAgents" :key="a.id" class="task-right-agent-item">
              <router-link :to="'/agents#' + a.id" class="task-right-agent-link">
                <span class="task-right-agent-num">{{ idx + 1 }}</span>
                <span class="task-right-agent-name">{{ a.name }}</span>
              </router-link>
            </li>
          </ul>
          <router-link v-if="auth.isLoggedIn && myAgents.length" to="/agents" class="btn btn-text btn-sm task-right-more">{{ t('taskManage.manageAgents') || '管理 Agent' }}</router-link>
        </div>
      </aside>
    </div>

    <!-- 创建任务弹窗 -->
    <div v-if="showCreateModal" class="modal-mask" @click.self="closeCreateModal">
      <div class="modal modal--create">
        <h3 class="modal-title">{{ t('task.publish') }}</h3>
        <div v-if="!auth.isLoggedIn" class="card-content publish-gate">
          <p class="hint">{{ t('task.publishHint') }}</p>
          <button type="button" class="btn btn-primary" @click="showCreateModal = false; showAuthModal = true">{{ t('task.loginToPublish') }}</button>
          <button type="button" class="btn btn-secondary close-btn" @click="closeCreateModal">{{ t('common.cancel') }}</button>
        </div>
        <div v-else class="publish-form-in-modal">
          <div class="create-task-step create-task-step--identity">
            <span class="create-task-step-label">{{ t('taskManage.stepIdentity') || '1. 发布身份' }}</span>
            <div class="publish-identity-toggles">
              <button type="button" class="identity-toggle" :class="{ active: publishForm.creator_agent_id === publishAsSelfValue }" @click="publishForm.creator_agent_id = publishAsSelfValue">{{ t('task.publishAsSelf') || '我本人' }}</button>
              <button v-for="a in myAgents" :key="a.id" type="button" class="identity-toggle" :class="{ active: publishForm.creator_agent_id === a.id }" @click="publishForm.creator_agent_id = a.id">{{ t('task.publishAsAgent', { name: a.name }) || `Agent：${a.name}` }}</button>
            </div>
          </div>
          <div class="create-task-step">
            <span class="create-task-step-label">{{ t('taskManage.stepTaskInfo') || '2. 任务信息' }}</span>
          </div>
          <div class="form-group">
            <label class="form-label" for="publish-title">{{ t('agentGuide.fieldTitle') }} <span class="required">*</span></label>
            <input id="publish-title" v-model="publishForm.title" class="input" type="text" :placeholder="t('task.title')" minlength="2" />
            <p class="form-hint">{{ t('task.titleHint') }}</p>
          </div>
          <div class="form-group">
            <label class="form-label" for="publish-desc">{{ t('task.description') }}</label>
            <textarea id="publish-desc" v-model="publishForm.description" class="input textarea-input" rows="4" :placeholder="t('task.requirementsPlaceholder')" />
            <p class="form-hint">{{ t('task.descriptionHint') }}</p>
          </div>
          <div class="form-group">
            <label class="form-label" for="publish-category">{{ t('task.category') }}</label>
            <select id="publish-category" v-model="publishForm.category" class="input select-input">
              <option value="">{{ t('task.categoryPlaceholder') }}</option>
              <option value="development">{{ t('task.categoryDevelopment') }}</option>
              <option value="design">{{ t('task.categoryDesign') }}</option>
              <option value="research">{{ t('task.categoryResearch') }}</option>
              <option value="writing">{{ t('task.categoryWriting') }}</option>
              <option value="data">{{ t('task.categoryData') }}</option>
              <option value="other">{{ t('task.categoryOther') }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" for="publish-requirements">{{ t('task.requirements') }}</label>
            <textarea id="publish-requirements" v-model="publishForm.requirements" class="input textarea-input" rows="3" :placeholder="t('task.requirementsPlaceholder')" />
            <p class="form-hint">{{ t('task.requirementsHint') }}</p>
          </div>
          <div class="form-group form-row-2">
            <label class="form-label" for="publish-location">{{ t('task.location') || '地点' }}</label>
            <input id="publish-location" v-model="publishForm.location" class="input" type="text" :placeholder="t('task.locationPlaceholder') || '如：远程、北京'" />
            <label class="form-label" for="publish-duration">{{ t('task.durationEstimate') || '预计时长' }}</label>
            <input id="publish-duration" v-model="publishForm.duration_estimate" class="input" type="text" :placeholder="t('task.durationPlaceholder') || '如：~1h、~3h'" />
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('task.skills') || '技能标签' }}</label>
            <input v-model="publishForm.skills_text" class="input" type="text" :placeholder="t('task.skillsPlaceholder') || '逗号分隔'" />
          </div>
          <div class="create-task-step">
            <span class="create-task-step-label">{{ t('taskManage.stepReward') || '3. 奖励与回调' }}</span>
          </div>
          <div class="form-group form-inline">
            <label class="form-label" for="publish-reward">{{ t('agentGuide.fieldRewardPoints') }}</label>
            <input id="publish-reward" v-model.number="publishForm.reward_points" type="number" min="0" class="input input-num" />
          </div>
          <template v-if="publishForm.reward_points > 0">
            <div class="form-group">
              <label class="form-label" for="publish-webhook">{{ t('agentGuide.fieldWebhook') }}</label>
              <input id="publish-webhook" v-model="publishForm.completion_webhook_url" class="input full-width" type="url" :placeholder="t('task.webhookPlaceholder')" />
            </div>
          </template>
          <div class="form-group">
            <label class="form-label" for="publish-discord">{{ t('task.discordWebhookLabel') }}</label>
            <input id="publish-discord" v-model="publishForm.discord_webhook_url" class="input full-width" type="url" :placeholder="t('task.discordWebhookPlaceholder')" />
          </div>
          <p class="hint">{{ t('task.balanceHint', { n: accountCredits }) }}</p>
          <p v-if="publishError" class="error-msg" role="alert">{{ publishError }}</p>
          <div class="modal-actions">
            <button type="button" class="btn btn-primary" :disabled="publishLoading" @click="doPublishAndClose">{{ publishLoading ? t('task.publishBtnLoading') : t('task.publishBtn') }}</button>
            <button type="button" class="btn btn-secondary" @click="closeCreateModal">{{ t('common.cancel') }}</button>
          </div>
        </div>
      </div>
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
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { safeT } from '../i18n'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'
import type { TaskListItem, TaskCommentItem } from '../api'

const route = useRoute()
const publishAsSelfValue = null as number | null

const emit = defineEmits<{ (e: 'show-auth'): void; (e: 'scroll-agent'): void; (e: 'success', msg: string): void }>()
const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const auth = useAuthStore()
const showAuthModal = ref(false)
const showCreateModal = ref(false)
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
const publishForm = reactive<{ title: string; description: string; category: string; requirements: string; reward_points: number; completion_webhook_url: string; discord_webhook_url: string; invited_agent_ids: number[]; creator_agent_id: number | null; location: string; duration_estimate: string; skills_text: string }>({ title: '', description: '', category: '', requirements: '', reward_points: 0, completion_webhook_url: '', discord_webhook_url: '', invited_agent_ids: [], creator_agent_id: null, location: '', duration_estimate: '', skills_text: '' })
const publishLoading = ref(false)
const publishError = ref('')
const candidates = ref<Array<{ id: number; name: string; owner_name: string; points?: number }>>([])
const myAgents = ref<Array<{ id: number; name: string; agent_type: string }>>([])
const accountCredits = ref(0)
const subscribeTaskItem = ref<{ id: number; title: string } | null>(null)
const subscribeLoading = ref<number | null>(null)
const submitCompletionTask = ref<{ id: number; title: string } | null>(null)
const submitCompletionForm = reactive({ result_summary: '' })
const submitCompletionLoading = ref(false)
const confirmLoading = ref<number | null>(null)
const rejectLoading = ref<number | null>(null)
const categoryFilter = ref('')
const categoryFilterOptions = [
  { value: 'development', labelKey: 'task.categoryDevelopment' },
  { value: 'design', labelKey: 'task.categoryDesign' },
  { value: 'research', labelKey: 'task.categoryResearch' },
  { value: 'writing', labelKey: 'task.categoryWriting' },
  { value: 'data', labelKey: 'task.categoryData' },
  { value: 'other', labelKey: 'task.categoryOther' },
]
const filteredTasks = computed(() => {
  if (!categoryFilter.value) return tasks.value
  return tasks.value.filter((t) => t.category === categoryFilter.value)
})

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
  }).catch((e) => { authError.value = e.response?.data?.detail || t('common.loginFailed') }).finally(() => { authLoading.value = false })
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
  }).catch((e) => { authError.value = e.response?.data?.detail || t('common.registerFailed') }).finally(() => { authLoading.value = false })
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
function getTaskSkills(t: { skills?: string[] | string }): string[] {
  if (!t.skills) return []
  if (Array.isArray(t.skills)) return t.skills
  if (typeof t.skills === 'string') return t.skills.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
  return []
}
const categoryLabels: Record<string, string> = {
  development: 'task.categoryDevelopment',
  design: 'task.categoryDesign',
  research: 'task.categoryResearch',
  writing: 'task.categoryWriting',
  data: 'task.categoryData',
  other: 'task.categoryOther',
}
function taskCategoryLabel(cat: string) {
  return t(categoryLabels[cat] || cat)
}
const selectedTaskDetail = ref<TaskListItem | null>(null)
const detailLoading = ref(false)
const taskComments = ref<TaskCommentItem[]>([])
const taskCommentsLoading = ref(false)
const newCommentContent = ref('')
const postCommentLoading = ref(false)

function openTaskDetail(task: TaskListItem) {
  selectedTaskDetail.value = { ...task }
  detailLoading.value = true
  taskComments.value = []
  api.getTaskDetail(task.id).then((res) => {
    selectedTaskDetail.value = res.data as TaskListItem
  }).catch(() => {}).finally(() => { detailLoading.value = false })
  loadTaskComments(task.id)
}

function loadTaskComments(taskId: number) {
  taskCommentsLoading.value = true
  api.getTaskComments(taskId).then((res) => {
    taskComments.value = res.data.comments || []
  }).catch(() => { taskComments.value = [] }).finally(() => { taskCommentsLoading.value = false })
}

function formatCommentTime(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 60000
  if (diff < 1) return t('task.justNow')
  if (diff < 60) return t('task.minutesAgo', { n: Math.floor(diff) })
  if (diff < 1440) return t('task.hoursAgo', { n: Math.floor(diff / 60) })
  return iso.slice(0, 16).replace('T', ' ')
}

function postComment() {
  if (!selectedTaskDetail.value || !newCommentContent.value.trim()) return
  postCommentLoading.value = true
  api.postTaskComment(selectedTaskDetail.value.id, { content: newCommentContent.value.trim() }).then((res) => {
    taskComments.value = [...taskComments.value, res.data]
    newCommentContent.value = ''
    showSuccessLocal(t('task.commentPosted'))
  }).catch(() => {}).finally(() => { postCommentLoading.value = false })
}

function closeTaskDetail() {
  selectedTaskDetail.value = null
  taskComments.value = []
}

function openCreateModal() {
  if (!auth.isLoggedIn) {
    showAuthModal.value = true
    return
  }
  publishError.value = ''
  showCreateModal.value = true
}
function closeCreateModal() {
  showCreateModal.value = false
  publishError.value = ''
}
function doPublishAndClose() {
  doPublish()
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
    category: publishForm.category.trim() || undefined,
    requirements: publishForm.requirements.trim() || undefined,
    invited_agent_ids: publishForm.invited_agent_ids?.length ? publishForm.invited_agent_ids : undefined,
    creator_agent_id: publishForm.creator_agent_id ?? undefined,
    location: publishForm.location.trim() || undefined,
    duration_estimate: publishForm.duration_estimate.trim() || undefined,
    skills,
    discord_webhook_url: publishForm.discord_webhook_url.trim() || undefined,
  }).then(() => {
    publishForm.title = ''
    publishForm.description = ''
    publishForm.category = ''
    publishForm.requirements = ''
    publishForm.reward_points = 0
    publishForm.completion_webhook_url = ''
    publishForm.discord_webhook_url = ''
    publishForm.invited_agent_ids = []
    publishForm.creator_agent_id = null
    publishForm.location = ''
    publishForm.duration_estimate = ''
    publishForm.skills_text = ''
    showSuccessLocal(t('task.publishSuccess'))
    showCreateModal.value = false
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
.task-manage-view { width: 100%; }
.task-layout { display: grid; grid-template-columns: 160px 1fr 200px; gap: 1rem 1.5rem; min-height: 60vh; }
.task-left { padding-top: 0.25rem; }
.task-categories { display: flex; flex-direction: column; gap: 0.25rem; }
.category-item {
  padding: 0.5rem 0.75rem; border-radius: 8px; border: 1px solid var(--border, #333); background: transparent; color: var(--text-secondary);
  font-size: 0.9rem; text-align: left; cursor: pointer; transition: border-color 0.2s, background 0.2s, color 0.2s;
}
.category-item:hover { border-color: var(--primary-color); color: var(--text-primary); }
.category-item.active { background: rgba(var(--primary-rgb, 34, 197, 94), 0.12); border-color: var(--primary-color); color: var(--primary-color); }
.category-item--mine { margin-top: 0.5rem; font-weight: 500; }
.task-center { display: flex; flex-direction: column; min-width: 0; }
.task-center-inner { display: flex; gap: 1rem; flex: 1; min-height: 0; }
.task-center-inner--mine { display: block; }
.task-list-wrap { flex: 0 1 50%; min-width: 0; overflow-y: auto; }
.task-detail-panel {
  flex: 0 1 50%; min-width: 0; overflow-y: auto; border-radius: 12px; border: 1px solid var(--border, #333);
  background: var(--card-bg); padding: 1rem 1.25rem;
}
.task-detail-panel__head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem; }
.task-detail-panel__title { font-size: 1.05rem; margin: 0; font-weight: 600; line-height: 1.3; }
.task-detail-panel__actions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.75rem; }
.task-comments { margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid var(--border-color); }
.task-comments-title { font-size: 0.95rem; font-weight: 600; margin: 0 0 0.75rem; color: var(--text-primary); }
.task-comments-list { list-style: none; padding: 0; margin: 0 0 1rem; }
.task-comment-item { display: flex; gap: 0.75rem; padding: 0.75rem 0; border-bottom: 1px solid var(--border-color); align-items: flex-start; }
.task-comment-item:last-child { border-bottom: none; }
.task-comment-item.comment-kind-status { border-left: 3px solid var(--secondary-color); padding-left: 0.5rem; margin-left: -0.5rem; }
.task-comment-avatar { flex-shrink: 0; width: 2rem; height: 2rem; border-radius: 50%; background: var(--surface); color: var(--primary-color); font-size: 0.75rem; font-weight: 600; display: flex; align-items: center; justify-content: center; }
.task-comment-body { flex: 1; min-width: 0; }
.task-comment-header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.35rem 0.5rem; margin-bottom: 0.25rem; }
.task-comment-author { font-weight: 600; font-size: 0.9rem; color: var(--text-primary); }
.task-comment-by-user { font-size: 0.8rem; color: var(--text-secondary); }
.task-comment-kind-badge { font-size: 0.7rem; padding: 0.1rem 0.35rem; border-radius: 4px; background: rgba(139, 92, 246, 0.15); color: var(--secondary-color); }
.task-comment-time { font-size: 0.75rem; color: var(--muted); }
.task-comment-content { margin: 0; font-size: 0.9rem; line-height: 1.5; white-space: pre-wrap; word-break: break-word; color: var(--text-secondary); }
.task-comments-empty { font-size: 0.9rem; color: var(--muted); margin: 0 0 0.75rem; }
.task-comment-form { margin-top: 1rem; }
.task-comment-form .textarea-input { min-height: 3.5rem; margin-bottom: 0.5rem; width: 100%; border-radius: var(--radius-sm); padding: 0.6rem 0.75rem; }
.task-layout--mine-only { grid-template-columns: 1fr 200px; }
.task-layout--mine-only .task-center { min-width: 0; }
.task-right { display: flex; flex-direction: column; gap: 1rem; }
.task-right-card {
  border-radius: 12px;
  border: 1px solid var(--border-color, rgba(255,255,255,0.1));
  background: var(--card-background, var(--card-bg));
  padding: 1rem 1.25rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.task-right-create .btn { width: 100%; }
.task-right-title { font-size: 0.95rem; font-weight: 600; margin: 0 0 0.75rem; color: var(--text-primary); letter-spacing: 0.01em; }
.task-right-hint { font-size: 0.85rem; color: var(--text-secondary); line-height: 1.4; }
.task-right-agent-list { list-style: none; padding: 0; margin: 0 0 0.75rem; }
.task-right-agent-item { margin-bottom: 0.25rem; }
.task-right-agent-link {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.9rem; color: var(--primary-color); text-decoration: none;
  padding: 0.4rem 0.5rem; border-radius: 8px;
  transition: background 0.2s, color 0.2s;
}
.task-right-agent-link:hover { background: rgba(var(--primary-rgb, 34, 197, 94), 0.1); color: var(--primary-color); text-decoration: none; }
.task-right-agent-num {
  flex-shrink: 0; width: 1.25rem; height: 1.25rem; border-radius: 6px;
  background: var(--surface, rgba(255,255,255,0.06)); color: var(--text-secondary);
  font-size: 0.75rem; font-weight: 600; display: inline-flex; align-items: center; justify-content: center;
}
.task-right-agent-link:hover .task-right-agent-num { background: rgba(var(--primary-rgb, 34, 197, 94), 0.2); color: var(--primary-color); }
.task-right-agent-name { flex: 1; min-width: 0; }
.task-right-more { padding: 0.25rem 0; margin-top: 0.25rem; }
@media (max-width: 1024px) {
  .task-layout { grid-template-columns: 1fr 200px; }
  .task-left { order: 1; grid-column: 1 / -1; }
  .task-categories { flex-direction: row; flex-wrap: wrap; }
  .task-center-inner { flex-direction: column; }
  .task-list-wrap { flex: 1 1 auto; max-height: 40vh; }
  .task-detail-panel { flex: 1 1 auto; }
}
@media (max-width: 768px) {
  .task-layout { grid-template-columns: 1fr; gap: 1rem; }
  .task-right { order: -1; flex-direction: row; flex-wrap: wrap; align-items: center; gap: 0.75rem; }
  .task-right-create { flex: 1; min-width: 120px; }
  .task-right-agents { flex: 1 1 100%; }
}
.modal--create { max-width: 520px; width: 95%; max-height: 90vh; overflow-y: auto; }
.publish-form-in-modal .form-group { margin-bottom: 1rem; }
.publish-form-in-modal .create-task-step { margin-bottom: 0.75rem; }
.publish-form-in-modal .create-task-step-label { display: block; font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.5rem; }
.publish-form-in-modal .modal-actions { display: flex; gap: 0.5rem; margin-top: 1rem; }
.publish-form-in-modal .form-group.form-inline { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.publish-form-in-modal .form-group.form-inline .form-label { margin-bottom: 0; margin-right: 0.25rem; }
.publish-form-in-modal .form-group.form-inline .input-num { width: 6rem; }
.publish-form-in-modal .form-hint { font-size: 0.8rem; color: var(--text-secondary); margin: 0.35rem 0 0; line-height: 1.4; }
.create-task-step { margin-bottom: 1rem; }
.create-task-step-label { display: block; font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.03em; }
.create-task-step--identity { margin-bottom: 1.25rem; }
.publish-identity-toggles { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.35rem; }
.identity-toggle { padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid var(--border-color); background: var(--background-dark); color: var(--text-secondary); font-size: 0.9rem; cursor: pointer; transition: border-color 0.2s, background 0.2s, color 0.2s; }
.identity-toggle:hover { border-color: var(--primary-color); color: var(--primary-color); }
.identity-toggle.active { background: rgba(var(--primary-rgb, 34, 197, 94), 0.15); border-color: var(--primary-color); color: var(--primary-color); }
.form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem 1rem; }
.form-row-2 .form-group { margin-bottom: 0; }
@media (max-width: 480px) { .form-row-2 { grid-template-columns: 1fr; } }
.task-list { display: flex; flex-direction: column; gap: 1rem; }
.task-card .card-header { display: flex; justify-content: space-between; align-items: center; }
.task-card .meta { font-size: 0.875rem; color: var(--muted); margin: 0.25rem 0; }

/* 结构化任务卡片（BotLearn 风格：圆角、阴影、hover） */
.task-card--structured {
  padding: 1.25rem 1.5rem;
  border-radius: 12px;
  border: 1px solid var(--border-color, rgba(255,255,255,0.08));
  background: var(--card-background, var(--card-bg));
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  transition: box-shadow 0.2s, border-color 0.2s;
}
.task-card--structured:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  border-color: var(--border-color, rgba(255,255,255,0.12));
}
.task-card--structured .task-card__top { display: flex; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.4rem; }
.task-card--structured .task-card__type { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.02em; }
.task-card--structured .task-card__reward { margin-left: auto; font-size: 0.95rem; font-weight: 600; color: var(--primary, #6366f1); }
.task-card--structured .task-card__title { font-size: 1.05rem; margin: 0 0 0.4rem; font-weight: 600; line-height: 1.3; }
.task-card--structured .task-card__desc { font-size: 0.9rem; color: var(--muted); margin: 0 0 0.5rem; line-height: 1.45; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.task-card--structured .task-card__tags,
.task-card--structured .task-card__attrs { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.5rem; }
.task-tag { display: inline-block; font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 999px; background: var(--surface, rgba(255,255,255,0.06)); color: var(--text-secondary, #94a3b8); border: 1px solid var(--border, rgba(255,255,255,0.1)); }
.task-tag--location { border-color: rgba(34, 197, 94, 0.4); color: #86efac; }
.task-tag--duration { border-color: rgba(59, 130, 246, 0.4); color: #93c5fd; }
.task-card__category { font-size: 0.75rem; padding: 0.25rem 0.5rem; background: var(--surface-700, #333); border-radius: 6px; margin-right: 0.35rem; font-weight: 500; }
.select-input { max-width: 100%; }
.textarea-input { min-height: 4rem; resize: vertical; }
.modal--detail { max-width: 28rem; }
.detail-section { margin-bottom: 1rem; }
.detail-desc { white-space: pre-wrap; word-break: break-word; color: var(--text-secondary); }
.detail-meta { margin: 0 0 1rem; font-size: 0.9rem; }
.detail-meta dt { font-weight: 600; color: var(--text-secondary); margin-top: 0.5rem; margin-bottom: 0.2rem; }
.detail-meta dd { margin: 0; }
.detail-requirements { white-space: pre-wrap; word-break: break-word; }
.detail-footer { font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.75rem; }
.detail-reward { margin-left: 0.5rem; }
.detail-btn { margin-right: auto; }
.task-card__requirements-snippet { font-size: 0.8rem; color: var(--text-secondary); margin: 0 0 0.4rem; padding-left: 0.5rem; border-left: 2px solid var(--surface-700); line-height: 1.35; }
.task-card__priority { font-size: 0.7rem; padding: 0.15rem 0.4rem; border-radius: 4px; text-transform: uppercase; }
.task-card__priority.priority--high { background: rgba(234, 179, 8, 0.2); color: #eab308; }
.task-card__priority.priority--critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.task-card__priority.priority--low { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
.task-tag--skill { border-color: rgba(168, 85, 247, 0.4); color: #e9d5ff; }
.task-card--structured .task-card__meta { font-size: 0.8rem; color: var(--muted); margin: 0 0 0.5rem; }
.task-card--structured .task-card__actions-wrap { padding: 0; margin-top: 0.25rem; border: none; }

.task-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
.empty-state { text-align: center; padding: 2rem; color: var(--muted); }
.agent-select-list { display: flex; flex-direction: column; gap: 0.5rem; margin: 1rem 0; }
.modal--create { max-width: 520px; padding: var(--space-6, 1.5rem); }
.modal--create .form-group { margin-bottom: var(--space-4, 1rem); }
.modal--create .modal-actions { margin-top: var(--space-5, 1.25rem); }
</style>
