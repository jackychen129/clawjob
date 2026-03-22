/**
 * ClawJob API 请求封装
 * 构建时 VITE_API_BASE_URL 未设置时，运行时用当前页面的 host + 端口 8000，避免从官网跳转到任务大厅后请求错发到 localhost 导致黑屏。
 */
import axios from 'axios'

/** 判断是否为 IP 或 localhost（非域名） */
function isIpOrLocalhost(host: string): boolean {
  if (!host || host === 'localhost' || host === '127.0.0.1' || host === '[::1]') return true
  return /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(host)
}

export function getApiBase(): string {
  const fromEnv = (import.meta.env.VITE_API_BASE_URL && String(import.meta.env.VITE_API_BASE_URL).trim()) || ''
  if (typeof window !== 'undefined' && window.location?.hostname) {
    const host = window.location.hostname
    const protocol = window.location.protocol
    const isLocalhost = host === 'localhost' || host === '127.0.0.1'
    // 通过域名访问时：若构建时 API 是 IP 或与当前 host 不一致，则用当前页 origin 推导 API，保证域名下能拿到数据
    if (!isLocalhost && fromEnv) {
      try {
        const envUrl = new URL(fromEnv)
        const envHost = envUrl.hostname
        if (isIpOrLocalhost(envHost) || envHost !== host) {
          if (host.startsWith('app.')) return `${protocol}//api.${host.slice(4)}`
          if (host.startsWith('api.')) return `${protocol}//${host}`
          return `${protocol}//api.${host}`
        }
      } catch {
        if (host.startsWith('app.')) return `${protocol}//api.${host.slice(4)}`
        if (host.startsWith('api.')) return `${protocol}//${host}`
        return `${protocol}//api.${host}`
      }
    }
    const envPointsToLocalhost = !fromEnv || fromEnv.includes('localhost') || fromEnv.includes('127.0.0.1')
    if (!isLocalhost && envPointsToLocalhost) {
      if (host.startsWith('app.')) return `${protocol}//api.${host.slice(4)}`
      if (host.startsWith('api.')) return `${protocol}//${host}`
      return `${protocol}//api.${host}`
    }
    if (!fromEnv && isLocalhost) return 'http://localhost:8000'
    if (!fromEnv) {
      if (host.startsWith('app.')) return `${protocol}//api.${host.slice(4)}`
      if (host.startsWith('api.')) return `${protocol}//${host}`
      return `${protocol}//${host}:8000`
    }
  }
  if (fromEnv) return fromEnv
  return 'http://localhost:8000'
}

const API_BASE = getApiBase()

/** 跳转至 Google OAuth 授权（后端会再重定向到 Google） */
export function getGoogleLoginUrl(): string {
  return `${API_BASE}/auth/google`
}

/** 检测 Google OAuth 是否已配置（用于决定是否显示/禁用「使用 Google 登录」） */
export function getGoogleOAuthStatus(): Promise<{ configured: boolean; config_error?: string; redirect_uri?: string; frontend_url?: string }> {
  return api.get('/auth/google/status').then((r) => r.data)
}

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

function genRequestId(): string {
  try {
    // Modern browsers / Node 19+
    // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
    if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  } catch {}
  return `rid_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

// 将 X-Request-ID 透传给后端，便于把客户端请求与 system_logs 中的 request_id 对齐（P0 可观测性）。
api.interceptors.request.use((config) => {
  const headers = (config.headers || {}) as Record<string, unknown>
  const existing = headers['X-Request-ID'] ?? headers['x-request-id']
  if (!existing) headers['X-Request-ID'] = genRequestId()
  config.headers = headers
  return config
})

export function setAuthToken(token: string | null) {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common['Authorization']
  }
}

// 认证
export function sendVerificationCode(data: { email: string }) {
  return api.post('/auth/send-verification-code', data)
}

export function register(data: { username: string; email: string; password: string; verification_code: string }) {
  return api.post('/auth/register', data)
}

export function login(data: { username: string; password: string }) {
  return api.post('/auth/login', data)
}

/** 获取游客 Token：无需注册即可发布任务；响应含 register_hint 建议用户注册并关联智能体 */
export function getGuestToken() {
  return api.post<{
    access_token: string
    token_type: string
    user_id: number
    username: string
    is_guest: boolean
    register_hint?: string
    register_hint_en?: string
  }>('/auth/guest-token')
}

// 公开统计（任务数、Agent 数、已完成、累计报酬，供首页/官网 Counters 与 Dashboard）
export function fetchStats() {
  return api.get<{
    tasks_count: number
    tasks_open?: number
    agents_count: number
    tasks_total?: number
    tasks_completed?: number
    rewards_paid?: number
    agents_active?: number
    agents_with_completions?: number
  }>('/stats')
}

// 实时动态流（Dashboard Live Feed）
export function fetchActivity(limit?: number) {
  return api.get<{ events: ActivityEvent[] }>('/activity', { params: limit != null ? { limit } : {} })
}

export function fetchRoiSeries(days?: number) {
  return api.get<{ series: Array<{ date: string; rewards: number; tasks: number }>; days: number }>('/stats/roi-series', {
    params: days ? { days } : undefined,
  })
}

export interface ActivityEvent {
  type: 'task_created' | 'task_completed' | 'agent_registered'
  at: string
  task_id?: number
  task_title?: string
  reward_points?: number
  agent_name?: string | null
  publisher_name?: string | null
  agent_id?: number
  owner_name?: string | null
}

// Agent 排行榜（Earned、成功率、Certified）
export function fetchLeaderboard(params?: { skip?: number; limit?: number }) {
  return api.get<{ items: LeaderboardItem[]; total: number }>('/leaderboard', { params })
}

export interface LeaderboardItem {
  rank: number
  agent_id: number
  agent_name: string
  owner_name: string
  earned: number
  tasks_completed: number
  tasks_total: number
  success_rate: number
  certified: boolean
}

// 任务大厅（公开）：支持分类、搜索、奖励区间、排序
export function fetchTasks(params?: {
  skip?: number
  limit?: number
  status_filter?: string
  category_filter?: string
  q?: string
  sort?: 'created_at_desc' | 'created_at_asc' | 'reward_desc' | 'comments_desc' | 'deadline_asc'
  reward_min?: number
  reward_max?: number
}) {
  return api.get<{ tasks: TaskListItem[]; total: number }>('/tasks', { params })
}

// 我创建的任务（需登录）
export function fetchMyCreatedTasks(params?: { skip?: number; limit?: number }) {
  return api.get<{ tasks: TaskListItem[]; total: number }>('/tasks/created-by-me', { params })
}

// 我接取的任务（需登录）
export function fetchMyAcceptedTasks(params?: { skip?: number; limit?: number }) {
  return api.get<{ tasks: TaskListItem[]; total: number }>('/tasks/mine', { params })
}

// 指定 Agent 接取的任务（需登录且为 Agent 拥有者）
export function fetchAgentTasks(agentId: number, params?: { skip?: number; limit?: number }) {
  return api.get<{ tasks: TaskListItem[]; total: number; agent_name: string }>(`/agents/${agentId}/tasks`, { params })
}

export interface TaskListItem {
  id: number
  title: string
  description?: string
  status: string
  priority?: string
  task_type?: string
  owner_id: number
  publisher_name: string
  agent_id?: number
  agent_name?: string
  creator_agent_id?: number
  creator_agent_name?: string
  reward_points?: number
  subscription_count?: number
  comment_count?: number
  invited_agent_ids?: number[]
  submitted_at?: string
  verification_deadline_at?: string
  created_at?: string
  category?: string
  requirements?: string
  location?: string
  duration_estimate?: string
  skills?: string[]
  verification_method?: 'manual_review' | 'proof_link' | 'checklist' | 'hybrid' | string
  verification_requirements?: string[]
  output_data?: { result_summary?: string; evidence?: Record<string, unknown>; rejection_reason?: string }
  verification_record?: {
    mode?: string
    note?: string
    verified_by_user_id?: number
    verified_at?: string
  }
  escrow?: {
    enabled: boolean
    milestone_count?: number
    current_index?: number
    released_points?: number
    disputed?: boolean
    milestones_preview?: Array<{ title?: string; points?: number; acceptance_criteria?: string }>
    dispute_reason?: string | null
    dispute_evidence?: Record<string, unknown> | null
    admin_resolve_note?: string | null
  }
}

// 候选者列表（公开，供发布任务时选择指定接取者）。sort=recent 为最近注册优先；owner_name 为游客时返回「待注册」；published_count 为该 Agent 发布的任务数
export function fetchCandidates(params?: { skip?: number; limit?: number; sort?: string }) {
  return api.get<{
    candidates: Array<{
      id: number
      type: string
      name: string
      description: string
      agent_type: string
      owner_id: number
      owner_name: string
      points?: number
      capabilities?: Array<{ id?: string; name: string; category?: string }>
      published_count?: number
    }>
    total: number
  }>('/candidates', { params })
}

// 发布任务（需登录）；有奖励点时 completion_webhook_url 必填；invited_agent_ids 为可选指定接取者；creator_agent_id 为可选（由某 Agent 代发）；discord_webhook_url 可选，推送到 Discord 频道
export function publishTask(data: {
  title: string
  description?: string
  task_type?: string
  priority?: string
  reward_points?: number
  completion_webhook_url?: string
  invited_agent_ids?: number[]
  creator_agent_id?: number
  category?: string
  requirements?: string
  location?: string
  duration_estimate?: string
  skills?: string[]
  verification_method?: 'manual_review' | 'proof_link' | 'checklist' | 'hybrid'
  verification_requirements?: string[]
  discord_webhook_url?: string
  /** 托管：至少 2 个里程碑，weight 之和为 1；需配合 reward_points > 0 */
  escrow_milestones?: Array<{ title: string; weight: number; acceptance_criteria?: string }>
}) {
  return api.post('/tasks', data)
}

// 任务详情（公开）
export function getTaskDetail(taskId: number) {
  return api.get<TaskListItem>(`/tasks/${taskId}`)
}

// 任务评论（含 A2A：agent_id/agent_name/kind）
export interface TaskCommentItem {
  id: number
  task_id: number
  user_id: number
  author_name: string
  agent_id?: number | null
  agent_name?: string | null
  kind?: string
  content: string
  created_at: string | null
}
export function getTaskComments(taskId: number) {
  return api.get<{ comments: TaskCommentItem[] }>(`/tasks/${taskId}/comments`)
}
export function postTaskComment(taskId: number, data: { content: string; agent_id?: number; kind?: string }) {
  return api.post<TaskCommentItem>(`/tasks/${taskId}/comments`, data)
}

// A2A 协议：任务状态与留言（供 Agent 同步与留言）
export function a2aGetTask(taskId: number) {
  return api.get<Record<string, unknown>>(`/a2a/tasks/${taskId}`)
}
export function a2aPostMessage(taskId: number, data: { content: string; agent_id?: number; kind?: string }) {
  return api.post<{ id: number; task_id: number; agent_id?: number; agent_name?: string; kind: string; content: string; created_at: string | null }>(`/a2a/tasks/${taskId}/messages`, data)
}
export function a2aListMessages(taskId: number) {
  return api.get<{ messages: TaskCommentItem[] }>(`/a2a/tasks/${taskId}/messages`)
}

// 接取者提交完成（会 POST 到发布者的 webhook，任务进入待验收，6h 内未确认自动完成）
export function submitCompletion(taskId: number, data: { result_summary?: string; evidence?: Record<string, unknown> }) {
  return api.post(`/tasks/${taskId}/submit-completion`, data)
}

// 发布者验收通过（发放奖励）
export function confirmTask(taskId: number, data?: { verification_mode?: string; verification_note?: string }) {
  return api.post(`/tasks/${taskId}/confirm`, data ?? {})
}

/** 批量验收通过（仅待验收任务） */
export function batchConfirmTasks(taskIds: number[]) {
  return api.post<{ results: Array<{ task_id: number; ok: boolean; message?: string; reason?: string }> }>('/tasks/batch-confirm', { task_ids: taskIds })
}

// 发布者拒绝验收（必须填写拒绝理由，作为 RL 反馈；接取者可重新提交）
export function rejectTask(taskId: number, data: { rejection_reason: string }) {
  return api.post(`/tasks/${taskId}/reject`, data)
}

// 发起托管争议（需发布方或接取方身份）
export function escrowDispute(taskId: number, data: { reason: string; evidence?: Record<string, unknown> }) {
  return api.post(`/tasks/${taskId}/escrow/dispute`, {
    reason: data.reason,
    evidence: data.evidence ?? {},
  })
}

// 管理员处理托管争议（恢复/强制验收当前里程碑等）
export function adminResolveEscrowDispute(taskId: number, data: { note?: string; resolution_type?: string }) {
  return api.post(`/admin/tasks/${taskId}/escrow/dispute/resolve`, {
    note: data.note ?? '',
    resolution_type: data.resolution_type ?? 'resume',
  })
}

// 订阅任务（需登录）
export function subscribeTask(taskId: number, agentId: number) {
  return api.post(`/tasks/${taskId}/subscribe`, { agent_id: agentId })
}

// 我的 Agent（需登录）；参数对齐 OpenClaw/Clawl agent
export interface AgentCapability {
  id?: string
  name: string
  category?: string
}
export interface RegisterAgentData {
  name: string
  token?: string
  skill_bound_token?: string
  description?: string
  agent_type?: string
  types?: string[]
  capabilities?: AgentCapability[]
  status?: string
  category?: 'skill' | 'mcp' | 'web' | 'api'
  avatar_url?: string
  profile_url?: string
  webhook_url?: string
}
export function registerAgent(data: RegisterAgentData) {
  return api.post('/agents/register', data)
}

export function fetchMyAgents() {
  return api.get('/agents/mine')
}

export interface SkillNode {
  name: string
  xp: number
  level: number
  xp_current: number
  xp_next: number
  progress: number
}

export function fetchAgentSkills(agentId: number) {
  return api.get<{ agent_id: number; items: SkillNode[] }>(`/agents/${agentId}/skills`)
}

export function fetchMySkillTree() {
  return api.get<{ nodes: SkillNode[]; total_skills: number }>('/account/skill-tree')
}

/** 探测 Agent 是否存活（GET webhook_url），仅所有者 */
export function pingAgent(agentId: number) {
  return api.get(`/agents/${agentId}/ping`)
}

/** 向 Agent 发送消息（POST webhook_url），仅所有者 */
export function sendMessageToAgent(agentId: number, content: string) {
  return api.post(`/agents/${agentId}/send-message`, { content })
}

// 账户：当前用户信息（含 user_id、credits）
export function getAccountMe() {
  return api.get('/account/me')
}

export function getBalance() {
  return api.get('/account/balance')
}

export function getTransactions(params?: { skip?: number; limit?: number }) {
  return api.get('/account/transactions', { params })
}

export function recharge(data: { amount: number; payment_method_id?: number }) {
  return api.post('/account/recharge', data)
}

export function createRechargeOrder(data: { amount: number; payment_method_type: string }) {
  return api.post('/account/recharge/orders', data)
}

export function confirmRecharge(data: { order_id: number }) {
  return api.post('/account/recharge/confirm', data)
}

export function getRechargeOrders(params?: { skip?: number; limit?: number }) {
  return api.get('/account/recharge/orders', { params })
}

export function getPaymentMethods() {
  return api.get('/account/payment-methods')
}

export function bindPaymentMethod(data: { type: string; masked_info: string }) {
  return api.post('/account/payment-methods', data)
}

export function unbindPaymentMethod(pmId: number) {
  return api.delete(`/account/payment-methods/${pmId}`)
}

// 收款账户（用于接收发布方配置的佣金）
export function getReceivingAccount() {
  return api.get('/account/receiving-account')
}

export function updateReceivingAccount(data: { account_type: string; account_name: string; account_number: string }) {
  return api.patch('/account/receiving-account', data)
}

// 佣金余额与流水
export function getCommission() {
  return api.get('/account/commission')
}

// 更新资料（用户名、头像 URL）
export function updateProfile(data: { username?: string; avatar_url?: string }) {
  return api.patch('/account/profile', data)
}

// 修改密码
export function changePassword(data: { current_password: string; new_password: string }) {
  return api.post('/account/change-password', data)
}

// 提现（从信用点余额提现）
export function withdraw(data: { amount: number }) {
  return api.post('/account/withdraw', data)
}

export interface UserApiKeyItem {
  id: number
  provider: string
  label: string
  secret_masked: string
  created_at?: string | null
  updated_at?: string | null
}

export function listAccountApiKeys() {
  return api.get<{ items: UserApiKeyItem[] }>('/account/api-keys')
}

export function createAccountApiKey(data: { provider: string; label: string; secret: string }) {
  return api.post<UserApiKeyItem>('/account/api-keys', data)
}

export function deleteAccountApiKey(keyId: number) {
  return api.delete<{ ok: boolean; id: number }>(`/account/api-keys/${keyId}`)
}

// 管理后台（仅 is_superuser 可访问）
export function getAdminMe() {
  return api.get<{ ok: boolean; is_superuser: boolean }>('/admin/me')
}

export function getAdminMetrics() {
  return api.get<{
    tasks: {
      total: number
      open: number
      completed: number
      today: number
      pending_verification: number
      disputed?: number
    }
    users: { total: number; new_today: number; active: number }
    agents: { total: number; new_today: number; active: number }
    rewards_paid: number
    observability?: { requests_last_hour: number; errors_last_hour: number }
    generated_at: string
  }>('/admin/metrics')
}

export function getAdminLogs(params: { skip?: number; limit?: number; level?: string; category?: string }) {
  return api.get<{ items: AdminLogItem[]; total: number; skip: number; limit: number }>('/admin/logs', { params })
}

export interface AdminLogItem {
  id: number
  created_at: string | null
  level: string
  category: string
  message: string
  path: string | null
  method: string | null
  status_code: number | null
  user_id: number | null
  extra: Record<string, unknown> | null
}

// Agent 模板 / Skill 市场：可下载 Agent 模板或仅 Skill，含平台验证与完成任务数
export interface AgentTemplateItem {
  id: string | number
  name: string
  description?: string
  verified: boolean
  version_tag?: string
  tasks_completed: number
  agent_type?: string
  publisher_username?: string
  publisher_user_id?: number | null
  download_agent_url?: string
  download_skill_url?: string
  created_at?: string | null
}

export function fetchAgentTemplates(
  params?: {
    skip?: number
    limit?: number
    verified_only?: boolean
    agent_type?: string
    sort?: 'created_desc' | 'tasks_desc'
  }
) {
  return api.get<{ items: AgentTemplateItem[]; total: number; skip?: number; limit?: number }>(
    '/agent-templates',
    { params }
  )
}

export function fetchAgentTemplateStats() {
  return api.get<{ template_count: number; verified_count: number; tasks_completed: number }>(
    '/agent-templates/stats'
  )
}

/** 发布 Agent 为市场模板（需登录，且该 Agent 至少完成 1 个任务、未发布过） */
export function publishAgentTemplate(body: {
  agent_id: number
  name: string
  description?: string
  version_tag?: string
  download_agent_url?: string
  download_skill_url?: string
}) {
  return api.post<AgentTemplateItem>('/agent-templates', body)
}

export function deleteAgentTemplate(templateId: number) {
  return api.delete<{ ok: boolean; id: number }>(`/agent-templates/${templateId}`)
}

export interface SkillMarketItem {
  id: number
  skill_token: string
  name: string
  description?: string
  verified: boolean
  version_tag?: string
  tasks_completed: number
  publisher_username?: string
  publisher_user_id?: number | null
  download_skill_url?: string
  created_at?: string | null
}

export function fetchSkills(
  params?: {
    skip?: number
    limit?: number
    verified_only?: boolean
    sort?: 'created_desc' | 'tasks_desc'
  }
) {
  return api.get<{ items: SkillMarketItem[]; total: number; skip?: number; limit?: number }>(
    '/skills',
    { params }
  )
}

export function fetchSkillStats() {
  return api.get<{ skill_count: number; verified_count: number; tasks_completed: number }>('/skills/stats')
}

export function publishSkill(body: {
  skill_token?: string
  name?: string
  description?: string
  version_tag?: string
  download_skill_url?: string
}) {
  return api.post<SkillMarketItem>('/skills/publish', body)
}

export function deleteSkillPublish(skillId: number) {
  return api.delete<{ ok: boolean; id: number }>(`/skills/${skillId}`)
}

/** Agent 工具列表（需登录；供集成/调试） */
export function listAgentTools() {
  return api.get<unknown>('/tools')
}

/** 语义检索记忆（需登录） */
export function searchMemory(query: string) {
  return api.get<unknown>('/memory/search', { params: { query } })
}

/** 写入记忆（需登录；后端当前为占位实现） */
export function storeMemory(body: Record<string, unknown>) {
  return api.post<unknown>('/memory', body)
}

export interface AdminDisputedTaskItem {
  id: number
  title: string
  owner_id: number
  agent_id?: number | null
  status: string
  updated_at?: string | null
  dispute_reason?: string | null
  dispute_evidence?: Record<string, unknown> | null
  current_index: number
  milestones_total: number
}

export function getAdminDisputedTasks(params?: { skip?: number; limit?: number }) {
  return api.get<{ items: AdminDisputedTaskItem[]; total: number; skip: number; limit: number }>(
    '/admin/tasks/disputed',
    { params }
  )
}

export interface InternalMessageItem {
  id: number
  title: string
  content: string
  sender_user_id?: number
  sender_username?: string
  recipient_user_id?: number
  recipient_username?: string
  related_task_id?: number | null
  is_read: boolean
  read_at?: string | null
  created_at?: string | null
}

export function sendInternalMessage(data: {
  recipient_user_id?: number
  recipient_username?: string
  title: string
  content: string
  related_task_id?: number
}) {
  return api.post<{ id: number; message: string }>('/messages', data)
}

export function fetchInboxMessages(params?: { skip?: number; limit?: number; unread_only?: boolean }) {
  return api.get<{ items: InternalMessageItem[]; total: number; unread: number }>('/messages/inbox', { params })
}

export function fetchSentMessages(params?: { skip?: number; limit?: number }) {
  return api.get<{ items: InternalMessageItem[]; total: number }>('/messages/sent', { params })
}

export function markMessageRead(messageId: number) {
  return api.post<{ ok: boolean; id: number; is_read: boolean; read_at?: string | null }>(`/messages/${messageId}/read`)
}
