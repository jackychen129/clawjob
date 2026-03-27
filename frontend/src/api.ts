/**
 * NOTE: translated comment in English.
 * NOTE: translated comment in English.
 */
import axios from 'axios'

/* NOTE: translated comment in English. */
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
    // NOTE: translated comment in English.
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

/* NOTE: translated comment in English. */
export function getGoogleLoginUrl(): string {
  return `${API_BASE}/auth/google`
}

/* NOTE: translated comment in English. */
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

// NOTE: translated comment in English.
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

// NOTE: translated comment in English.
export function sendVerificationCode(data: { email: string }) {
  return api.post('/auth/send-verification-code', data)
}

export function register(data: { username: string; email: string; password: string; verification_code: string }) {
  return api.post('/auth/register', data)
}

export function login(data: { username: string; password: string }) {
  return api.post('/auth/login', data)
}

/* NOTE: translated comment in English. */
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

// NOTE: translated comment in English.
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

// NOTE: translated comment in English.
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

// NOTE: translated comment in English.
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

// NOTE: translated comment in English.
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

// NOTE: translated comment in English.
export function fetchMyCreatedTasks(params?: { skip?: number; limit?: number }) {
  return api.get<{ tasks: TaskListItem[]; total: number }>('/tasks/created-by-me', { params })
}

// NOTE: translated comment in English.
export function fetchMyAcceptedTasks(params?: { skip?: number; limit?: number }) {
  return api.get<{ tasks: TaskListItem[]; total: number }>('/tasks/mine', { params })
}

// NOTE: translated comment in English.
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
  related_skill?: {
    skill_id?: number
    skill_token: string
    skill_name?: string
    download_skill_url?: string
    verified?: boolean
    source?: 'manual' | 'creator_agent' | 'assigned_agent' | string
  } | null
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

// NOTE: translated comment in English.
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

// NOTE: translated comment in English.
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
  related_skill_token?: string
  discord_webhook_url?: string
  /* NOTE: translated comment in English. */
  escrow_milestones?: Array<{ title: string; weight: number; acceptance_criteria?: string }>
}) {
  return api.post('/tasks', data)
}

export function fetchSkillRelatedTasks(skillId: number, params?: { skip?: number; limit?: number }) {
  return api.get<{ items: TaskListItem[]; total: number; skill_id: number; skill_token: string }>(
    `/skills/${skillId}/tasks`,
    { params }
  )
}

// NOTE: translated comment in English.
export function getTaskDetail(taskId: number) {
  return api.get<TaskListItem>(`/tasks/${taskId}`)
}

// NOTE: translated comment in English.
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

// NOTE: translated comment in English.
export function a2aGetTask(taskId: number) {
  return api.get<Record<string, unknown>>(`/a2a/tasks/${taskId}`)
}
export function a2aPostMessage(taskId: number, data: { content: string; agent_id?: number; kind?: string }) {
  return api.post<{ id: number; task_id: number; agent_id?: number; agent_name?: string; kind: string; content: string; created_at: string | null }>(`/a2a/tasks/${taskId}/messages`, data)
}
export function a2aListMessages(taskId: number) {
  return api.get<{ messages: TaskCommentItem[] }>(`/a2a/tasks/${taskId}/messages`)
}

// NOTE: translated comment in English.
export function submitCompletion(taskId: number, data: { result_summary?: string; evidence?: Record<string, unknown> }) {
  return api.post(`/tasks/${taskId}/submit-completion`, data)
}

export function getTaskVerificationChain(taskId: number) {
  return api.get(`/tasks/${taskId}/verification-chain`)
}

export function getRuntimeCircuitBreakers() {
  return api.get<{ items: Array<{ host: string; state: string; consecutive_failures: number; open_until?: string | null }>; threshold: number; open_seconds: number }>(
    '/runtime/circuit-breakers'
  )
}

export function controlRuntimeCircuitBreaker(data: { host: string; action: 'reset' | 'open' | 'half_open' | 'close' }) {
  return api.post('/runtime/circuit-breakers/control', data)
}

export function planWorkflow(data: { nodes: number[]; edges: Array<{ from: number; to: number }> }) {
  return api.post('/workflows/plan', data)
}

export function attachTaskWorkflow(taskId: number, data: { nodes: number[]; edges: Array<{ from: number; to: number }> }) {
  return api.post(`/tasks/${taskId}/workflow`, data)
}

export function getTaskWorkflow(taskId: number) {
  return api.get(`/tasks/${taskId}/workflow`)
}

// NOTE: translated comment in English.
export function confirmTask(taskId: number, data?: { verification_mode?: string; verification_note?: string }) {
  return api.post(`/tasks/${taskId}/confirm`, data ?? {})
}

/* NOTE: translated comment in English. */
export function batchConfirmTasks(taskIds: number[]) {
  return api.post<{ results: Array<{ task_id: number; ok: boolean; message?: string; reason?: string }> }>('/tasks/batch-confirm', { task_ids: taskIds })
}

// NOTE: translated comment in English.
export function rejectTask(taskId: number, data: { rejection_reason: string }) {
  return api.post(`/tasks/${taskId}/reject`, data)
}

// NOTE: translated comment in English.
export function escrowDispute(taskId: number, data: { reason: string; evidence?: Record<string, unknown> }) {
  return api.post(`/tasks/${taskId}/escrow/dispute`, {
    reason: data.reason,
    evidence: data.evidence ?? {},
  })
}

// NOTE: translated comment in English.
export function adminResolveEscrowDispute(taskId: number, data: { note?: string; resolution_type?: string }) {
  return api.post(`/admin/tasks/${taskId}/escrow/dispute/resolve`, {
    note: data.note ?? '',
    resolution_type: data.resolution_type ?? 'resume',
  })
}

// NOTE: translated comment in English.
export function subscribeTask(taskId: number, agentId: number) {
  return api.post(`/tasks/${taskId}/subscribe`, { agent_id: agentId })
}

// NOTE: translated comment in English.
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

/* NOTE: translated comment in English. */
export function pingAgent(agentId: number) {
  return api.get(`/agents/${agentId}/ping`)
}

/* NOTE: translated comment in English. */
export function sendMessageToAgent(agentId: number, content: string) {
  return api.post(`/agents/${agentId}/send-message`, { content })
}

// NOTE: translated comment in English.
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

// NOTE: translated comment in English.
export function getReceivingAccount() {
  return api.get('/account/receiving-account')
}

export function updateReceivingAccount(data: { account_type: string; account_name: string; account_number: string }) {
  return api.patch('/account/receiving-account', data)
}

// NOTE: translated comment in English.
export function getCommission() {
  return api.get('/account/commission')
}

// NOTE: translated comment in English.
export function updateProfile(data: { username?: string; avatar_url?: string }) {
  return api.patch('/account/profile', data)
}

// NOTE: translated comment in English.
export function changePassword(data: { current_password: string; new_password: string }) {
  return api.post('/account/change-password', data)
}

// NOTE: translated comment in English.
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

// NOTE: translated comment in English.
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

// NOTE: translated comment in English.
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

/* NOTE: translated comment in English. */
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
  contract_schema?: Record<string, unknown>
  failure_semantics?: Record<string, unknown>
  idempotency_hint?: string
}) {
  return api.post<SkillMarketItem>('/skills/publish', body)
}

export function validateSkillContract(body: {
  contract_schema: Record<string, unknown>
  failure_semantics?: Record<string, unknown>
  sample_payload?: Record<string, unknown>
}) {
  return api.post<{
    ok: boolean
    contract_ok: boolean
    contract_errors: string[]
    payload_ok: boolean
    payload_errors: string[]
  }>('/skills/contract/validate', body)
}

export function deleteSkillPublish(skillId: number) {
  return api.delete<{ ok: boolean; id: number }>(`/skills/${skillId}`)
}

/* NOTE: translated comment in English. */
export function listAgentTools() {
  return api.get<unknown>('/tools')
}

/* NOTE: translated comment in English. */
export function searchMemory(query: string) {
  return api.get<unknown>('/memory/search', { params: { query } })
}

/* NOTE: translated comment in English. */
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
