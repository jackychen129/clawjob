/**
 * NOTE: translated comment in English.
 * NOTE: translated comment in English.
 */
import axios from 'axios'
import { canonicalApiUrl, getSiteDomain } from './lib/siteUrls'

/* NOTE: translated comment in English. */
function isIpOrLocalhost(host: string): boolean {
  if (!host || host === 'localhost' || host === '127.0.0.1' || host === '[::1]') return true
  return /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(host)
}

export function getApiBase(): string {
  const fromEnv = (import.meta.env.VITE_API_BASE_URL && String(import.meta.env.VITE_API_BASE_URL).trim()) || ''
  const siteDomain = getSiteDomain()
  if (typeof window !== 'undefined' && window.location?.hostname) {
    const host = window.location.hostname
    const protocol = window.location.protocol
    const isLocalhost = host === 'localhost' || host === '127.0.0.1'
    const hostIsIp = isIpOrLocalhost(host)
    // Production: never call API via raw IP when we know the public domain.
    if (hostIsIp && !isLocalhost && siteDomain && host !== siteDomain) {
      return canonicalApiUrl()
    }
    if (!isLocalhost && fromEnv) {
      try {
        const envUrl = new URL(fromEnv)
        const envHost = envUrl.hostname
        if (hostIsIp) {
          // Visiting via IP (no DNS) — `api.<ip>` is not resolvable. Trust env
          // if it points to the same IP; otherwise fall back to host:8000.
          if (envHost === host) return fromEnv
          return `${protocol}//${host}:8000`
        }
        if (envHost !== host && (isIpOrLocalhost(envHost) || !envHost.endsWith(host))) {
          if (host.startsWith('app.')) return `${protocol}//api.${host.slice(4)}`
          if (host.startsWith('api.')) return `${protocol}//${host}`
          return `${protocol}//api.${host}`
        }
        return fromEnv
      } catch {
        if (hostIsIp) return `${protocol}//${host}:8000`
        if (host.startsWith('app.')) return `${protocol}//api.${host.slice(4)}`
        if (host.startsWith('api.')) return `${protocol}//${host}`
        return `${protocol}//api.${host}`
      }
    }
    const envPointsToLocalhost = !fromEnv || fromEnv.includes('localhost') || fromEnv.includes('127.0.0.1')
    if (!isLocalhost && envPointsToLocalhost) {
      if (hostIsIp) return `${protocol}//${host}:8000`
      if (host.startsWith('app.')) return `${protocol}//api.${host.slice(4)}`
      if (host.startsWith('api.')) return `${protocol}//${host}`
      return `${protocol}//api.${host}`
    }
    if (!fromEnv && isLocalhost) return 'http://localhost:8000'
    if (!fromEnv) {
      if (hostIsIp) return `${protocol}//${host}:8000`
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

export interface AppHealthFeatures {
  enterprise_enabled?: boolean
  payout_enabled?: boolean
  community_enabled?: boolean
}

let _enterpriseEnabled: boolean | null = null

/** Cached from GET /health — subscription & workspace routes require enterprise; payout/KYC are core. */
export function isEnterpriseEnabled(): boolean {
  return _enterpriseEnabled === true
}

export function isPayoutEnabled(): boolean {
  return _payoutEnabled !== false
}

let _payoutEnabled: boolean | null = null

export async function loadAppFeatures(): Promise<AppHealthFeatures> {
  try {
    const r = await api.get<{ features?: AppHealthFeatures }>('/health')
    const features = r.data?.features ?? {}
    _enterpriseEnabled = !!features.enterprise_enabled
    _payoutEnabled = features.payout_enabled !== false
    return features
  } catch {
    _enterpriseEnabled = false
    _payoutEnabled = true
    return {}
  }
}

/** Shown when enterprise-only clients are unavailable (see fetchMyKyc / fetchMySubscription). */
export const ENTERPRISE_API_HINT =
  'Enterprise features (KYC, subscription, workspaces) require CLAWJOB_ENTERPRISE=1 on the server.'

// NOTE: translated comment in English.
export function sendVerificationCode(data: { email: string }) {
  return api.post('/auth/send-verification-code', data)
}

export function register(data: { username: string; email: string; password: string; verification_code: string; referral_code?: string }) {
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

export function fetchRecentAgentsStats() {
  return api.get<{ recent_agents_7d: number; period_days: number }>('/stats/recent-agents')
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
export function fetchLeaderboard(params?: { skip?: number; limit?: number; shadow?: 0 | 1 }) {
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
  category_completions?: number
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
  output_data?: {
    result_summary?: string
    evidence?: Record<string, unknown>
    rejection_reason?: string
    /** 接取方提交完成时，完成回调 POST 的重试与 HTTP 状态（有 completion_webhook_url 时） */
    webhook_delivery?: { attempts?: number; http_status?: number; ok?: boolean }
    /** 可选：POST /tasks/{id}/execute 自动重试元信息（服务端写入时） */
    last_execute?: { retried?: number; at?: string; ok?: boolean; error?: string }
  }
  verification_record?: {
    mode?: string
    note?: string
    verified_by_user_id?: number
    verified_at?: string
  }
  /** 发布方标记：适合多 Agent / 协作型任务（展示用） */
  collaborative?: boolean
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
  auction?: {
    enabled: boolean
    status?: string
    min_reward?: number
    max_reward?: number
    deadline?: string | null
    auto_pick?: string
    selected_bid_id?: number | null
    bids_count?: number
  }
  verification_hours?: number
  verification_extend_used?: number
  /** escrow / verified_payout — 平台差异化任务保障 */
  badges?: string[]
  timeline?: Array<{ at: string; type: string; summary: string }>
  rejection_history?: Array<{ at: string; reason: string }>
  payment_breakdown?: {
    reward_points: number
    commission_rate: number
    commission_points: number
    executor_net_points: number
    transactions: Array<{ amount: number; remark: string; created_at?: string | null }>
  }
  settlement_mode?: 'platform_credits' | 'agent_direct' | string
  settlement?: {
    status?: string
    payer_confirmed_at?: string | null
    payee_confirmed_at?: string | null
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
  verification_hours?: number
  collaborative?: boolean
  auction?: {
    enabled: boolean
    min_reward?: number
    max_reward?: number
    deadline?: string | null
    auto_pick?: 'none' | 'lowest_price'
  }
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

export interface ForumRecentPostItem {
  comment: TaskCommentItem
  task: { id: number; title: string; status: string }
}

export function fetchForumRecentPosts(params?: { skip?: number; limit?: number }) {
  return api.get<{ items: ForumRecentPostItem[]; total: number; skip: number; limit: number }>(
    '/forum/recent-posts',
    { params }
  )
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

export function getRuntimeCircuitBreakerConfig() {
  return api.get<{ ok: boolean; threshold: number; open_seconds: number }>('/runtime/circuit-breakers/config')
}

export function patchRuntimeCircuitBreakerConfig(data: { threshold?: number; open_seconds?: number }) {
  return api.patch<{ ok: boolean; threshold: number; open_seconds: number; snapshot?: unknown }>(
    '/runtime/circuit-breakers/config',
    data,
  )
}

export interface PlatformClearingAccount {
  balance: number
  alipay_account: string
  alipay_name: string
}

export interface PlatformClearingRecord {
  id: number
  amount: number
  task_id: number | null
  remark: string
  created_at: string | null
}

/** 平台中转账户：使用 X-Platform-Admin-Key 调用（与登录态独立）。 */
export function getPlatformClearingAccount(platformAdminKey: string) {
  return api.get<PlatformClearingAccount>('/platform/clearing-account', {
    headers: { 'X-Platform-Admin-Key': platformAdminKey },
  })
}

export function updatePlatformClearingAccount(
  platformAdminKey: string,
  body: { alipay_account?: string; alipay_name?: string },
) {
  return api.patch<PlatformClearingAccount>('/platform/clearing-account', body, {
    headers: { 'X-Platform-Admin-Key': platformAdminKey },
  })
}

export function getPlatformClearingRecords(
  platformAdminKey: string,
  params?: { skip?: number; limit?: number },
) {
  return api.get<{ records: PlatformClearingRecord[]; total: number }>(
    '/platform/clearing-account/records',
    {
      params,
      headers: { 'X-Platform-Admin-Key': platformAdminKey },
    },
  )
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

export interface PaymentMethod {
  type: string
  label?: string
  account_masked?: string
  details_for_counterparty?: string
  webhook_url?: string | null
}

export interface TaskSettlementView {
  task_id: number
  task_status: string
  settlement_mode: string
  reward_points: number
  settlement: Record<string, unknown> | null
  payee_profile: { methods: PaymentMethod[] }
  viewer_role: 'publisher' | 'executor'
  instructions_zh?: string
}

export function fetchTaskSettlement(taskId: number) {
  return api.get<TaskSettlementView>(`/tasks/${taskId}/settlement`)
}

export function settlementPayerMarkPaid(taskId: number, data: { proof_links?: string[]; note?: string; method_used?: string }) {
  return api.post(`/tasks/${taskId}/settlement/payer-mark-paid`, data)
}

export function settlementPayeeConfirm(taskId: number) {
  return api.post(`/tasks/${taskId}/settlement/payee-confirm`)
}

export function fetchAgentPaymentProfile(agentId: number, taskId?: number) {
  const q = taskId != null ? `?task_id=${taskId}` : ''
  return api.get<{ agent_id: number; payment_profile: { methods: PaymentMethod[] } }>(`/agents/${agentId}/payment-profile${q}`)
}

export function updateAgentPaymentProfile(agentId: number, methods: PaymentMethod[]) {
  return api.put(`/agents/${agentId}/payment-profile`, { methods })
}

/* NOTE: translated comment in English. */
export function batchConfirmTasks(taskIds: number[]) {
  return api.post<{
    results: Array<{ task_id: number; ok: boolean; message?: string; reason?: string }>
    summary?: { total_reward_points: number; high_value_task_ids: number[]; warning?: string | null }
  }>('/tasks/batch-confirm', { task_ids: taskIds })
}

export function extendTaskVerification(taskId: number) {
  return api.post<{ message: string; task_id: number; verification_deadline_at: string | null }>(
    `/tasks/${taskId}/extend-verification`
  )
}

// NOTE: translated comment in English.
export function rejectTask(taskId: number, data: { rejection_reason: string }) {
  return api.post(`/tasks/${taskId}/reject`, data)
}

export interface CancelTaskResult {
  ok: boolean
  idempotent: boolean
  task_id: number
  status: string
  refunded_points: number
}

export function cancelTask(taskId: number) {
  return api.post<CancelTaskResult>(`/tasks/${taskId}/cancel`)
}

export interface AgentReputationCard {
  agent: {
    id: number
    name: string
    description: string
    agent_type: string
    category: string
    skill_token: string | null
    owner: { id: number | null; username: string | null; joined_at: string | null }
    is_active: boolean
    created_at: string | null
  }
  stats: {
    accepted_task_count: number
    completed_task_count: number
    rejection_count: number
    dispute_count: number
    rejection_rate: number
    dispute_rate: number
    first_pass_confirm_rate: number | null
    reward_points_total: number
    avg_completion_hours: number | null
    recent_30d_completed_count: number
    recent_90d_completed_count: number
    last_active_at: string | null
    top_skills: string[]
  }
  reputation_score: number
}

export function getAgentReputation(agentId: number) {
  return api.get<AgentReputationCard>(`/agents/${agentId}/reputation`)
}

export interface AgentTrustCard {
  agent_id: number
  agent_name: string
  completion_rate: number | null
  escrow_tasks_completed: number
  total_earned: number
  verified_skills: Array<{ skill_token: string; name: string; verified: boolean }>
  member_since: string | null
  badges: string[]
  reputation_score: number
  one_liner_zh: string
  one_liner_en: string
  urls: {
    trust_card: string
    reputation: string
    profile: string
    cases: string
  }
}

export function getAgentTrustCard(agentId: number) {
  return api.get<AgentTrustCard>(`/agents/${agentId}/trust-card`)
}

export interface RecommendedCandidate {
  agent: AgentReputationCard['agent']
  stats: AgentReputationCard['stats']
  reputation_score: number
  match: {
    total_score: number
    breakdown: { reputation: number; skill_token: number; skill_overlap: number; recent_activity: number; price_fit?: number }
  }
  suggested_price: number
  agent_median_price?: number | null
}

export interface RecommendCandidatesResponse {
  task_id: number
  task: { title: string; skill_token: string | null; category: string | null; reward_points: number; skills: string[] }
  candidates: RecommendedCandidate[]
  total_evaluated: number
}

export function getRecommendCandidates(taskId: number, k = 5) {
  return api.get<RecommendCandidatesResponse>(`/tasks/${taskId}/recommend-candidates`, {
    params: { k },
  })
}

export interface InviteAgentResponse {
  ok: boolean
  task_id: number
  invited_agent_ids: number[]
  visibility: string
}

export function inviteAgentToTask(taskId: number, agentId: number) {
  return api.post<InviteAgentResponse>(`/tasks/${taskId}/invite-agent`, { agent_id: agentId })
}

export interface TaskRadarItem {
  task: {
    id: number
    title: string
    description: string
    category: string | null
    skills: string[]
    skill_token: string | null
    reward_points: number
    created_at: string | null
    owner_id: number
    invited_for_me: boolean
    visibility: 'public' | 'invitees_only' | string
  }
  score: number
  breakdown: {
    skill_match: number
    reward_fit: number
    freshness: number
    history_affinity: number
  }
  reasons: string[]
  suggested_bid: number
}

export interface TaskRadarResponse {
  agent_id: number
  agent_name: string
  agent_reputation_score: number
  weights: {
    skill_match: number
    reward_fit: number
    freshness: number
    history_affinity: number
  }
  total_pool: number
  radar: TaskRadarItem[]
}

export interface TaskRadarQuery {
  k?: number
  w_skill?: number
  w_reward?: number
  w_fresh?: number
  w_history?: number
  reward_min?: number
  category?: string
}

export interface TaskEstimateResponse {
  input: {
    skill: string | null
    kind: string | null
    category: string | null
    difficulty: string | null
  }
  sample_size: number
  heuristic_used: boolean
  reward_points: {
    suggested: number
    p25: number
    p50: number
    p75: number
    p90: number
  }
  completion_hours: { p50: number | null; p75: number | null }
  accept_wait_hours: { p50: number | null; p75: number | null }
  confidence: 'low' | 'medium' | 'high' | string
  tips: string[]
}

export function getTaskEstimate(params: {
  skill?: string
  kind?: string
  category?: string
  difficulty?: string
}) {
  const qp: Record<string, string> = {}
  if (params.skill) qp.skill = params.skill
  if (params.kind) qp.kind = params.kind
  if (params.category) qp.category = params.category
  if (params.difficulty) qp.difficulty = params.difficulty
  return api.get<TaskEstimateResponse>('/tasks/estimate', { params: qp })
}

export interface IntentDraftResponse {
  title: string
  description: string
  acceptance_criteria: string[]
  skill: string | null
  category: string | null
  kind: string | null
  difficulty: 'easy' | 'normal' | 'hard' | 'expert' | string
  deadline_days: number | null
  reward_hint: number | null
  source: 'heuristic' | 'llm' | string
  raw_intent: string
  confidence: number
  draft_source: 'intent'
  user_id: number
}

export function draftTaskFromIntent(intent: string, opts: { use_llm?: boolean } = {}) {
  return api.post<IntentDraftResponse>('/tasks/draft-from-intent', {
    intent,
    use_llm: !!opts.use_llm,
  })
}

export function getAgentTaskRadar(agentId: number, params: TaskRadarQuery = {}) {
  const qp: Record<string, string | number> = {}
  if (params.k != null) qp.k = params.k
  if (params.w_skill != null) qp.w_skill = params.w_skill
  if (params.w_reward != null) qp.w_reward = params.w_reward
  if (params.w_fresh != null) qp.w_fresh = params.w_fresh
  if (params.w_history != null) qp.w_history = params.w_history
  if (params.reward_min != null) qp.reward_min = params.reward_min
  if (params.category) qp.category = params.category
  return api.get<TaskRadarResponse>(`/agents/${agentId}/task-radar`, { params: qp })
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

/** POST /agents/{id}/use-tool — 以 Agent 身份执行已注册工具（tool_name + params）。 */
export function postAgentUseTool(
  agentId: number | string,
  body: { tool_name: string; params?: Record<string, unknown> },
) {
  return api.post<{ success: boolean; data?: unknown; error?: string }>(`/agents/${agentId}/use-tool`, {
    tool_name: body.tool_name,
    params: body.params ?? {},
  })
}

export interface SkillNode {
  name: string
  xp: number
  level: number
  xp_current: number
  xp_next: number
  progress: number
}

export interface SkillDecayPolicy {
  idle_days?: number
  weekly_ratio?: number
  max_ratio?: number
}

export function fetchAgentSkills(agentId: number) {
  return api.get<{
    agent_id: number
    items: SkillNode[]
    decay?: { ratio?: number; last_active_at?: string | null; policy?: SkillDecayPolicy }
    viewer_is_owner?: boolean
  }>(`/agents/${agentId}/skills`)
}

export function fetchMySkillTree() {
  return api.get<{
    nodes: SkillNode[]
    total_skills: number
    decay?: { max_ratio?: number; last_active_at?: string | null; policy?: SkillDecayPolicy }
  }>('/account/skill-tree')
}

/* NOTE: translated comment in English. */
export function pingAgent(agentId: number) {
  return api.get(`/agents/${agentId}/ping`)
}

/* NOTE: translated comment in English. */
export function sendMessageToAgent(agentId: number, content: string) {
  return api.post(`/agents/${agentId}/send-message`, { content })
}

/** /account/me 含 task_pulse：与任务相关的待办计数 */
export interface AccountMeResponse {
  user_id: number
  username: string
  credits: number
  commission_balance?: number
  is_guest?: boolean
  task_pulse?: {
    awaiting_verify_as_owner: number
    awaiting_confirm_as_assignee: number
    need_submit: number
    disputes: number
    total_actionable: number
  }
}

// NOTE: translated comment in English.
export function getAccountMe() {
  return api.get<AccountMeResponse>('/account/me')
}

export function getBalance() {
  return api.get('/account/balance')
}

export interface PublishFeeEstimate {
  reward_points: number
  commission_rate: number
  commission_points: number
  executor_net_points: number
  max_reward_points: number
  publisher_credits: number
  publisher_credits_after: number
  sufficient: boolean
}

export function getPublishFeeEstimate(reward_points: number) {
  return api.get<PublishFeeEstimate>('/account/publish-fee-estimate', {
    params: { reward_points: Math.max(0, Math.floor(Number(reward_points) || 0)) },
  })
}

export function getTransactions(params?: { skip?: number; limit?: number }) {
  return api.get('/account/transactions', { params })
}

export function recharge(data: { amount: number; payment_method_id?: number }) {
  return api.post('/account/recharge', data)
}

export interface PaymentMethodSpec {
  key: string
  display_name: string
  kind: 'url' | 'qr' | 'crypto' | 'bank' | 'direct'
  currency: string
  min_amount: number
  max_amount: number
  fee_rate: number
  icon: string
  description: string
  tags: string[]
}

export function getRechargeMethods() {
  return api.get<{ methods: PaymentMethodSpec[] }>('/account/recharge/methods')
}

export interface RechargeOrderInstructions {
  method: string
  display_name: string
  kind: string
  amount: number
  url?: string
  qr_payload?: string
  note?: string
  bank?: {
    bank_name: string
    account_name: string
    account_number: string
    swift_code?: string
    memo: string
  }
  crypto?: {
    network?: string
    address?: string
    memo?: string
  }
}

export interface RechargeOrderResponse {
  order_id: number
  amount: number
  payment_method_type: string
  status: string
  payment_url: string | null
  payment_qr: string | null
  btc_address: string | null
  instructions: RechargeOrderInstructions
  message: string
}

export function createRechargeOrder(data: { amount: number; payment_method_type: string }) {
  return api.post<RechargeOrderResponse>('/account/recharge/orders', data)
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

/** @deprecated 请使用 submitWithdrawal；保留别名避免旧调用 404 */
export function withdraw(data: { amount: number }) {
  return submitWithdrawal(data.amount)
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
    agents: { total: number; new_today: number; active: number; public?: number }
    rewards_paid: number
    pending_settlements?: {
      pending_total: number
      awaiting_payer: number
      awaiting_payee: number
    }
    observability?: { requests_last_hour: number; errors_last_hour: number }
    generated_at: string
  }>('/admin/metrics')
}

export interface AdminPendingSettlementItem {
  task_id: number
  title: string
  task_status: string
  reward_points: number
  settlement_status: string | null
  phase: 'awaiting_payer' | 'awaiting_payee' | 'paid' | string
  payer_confirmed_at: string | null
  payee_confirmed_at: string | null
  created_at: string | null
  updated_at: string | null
  payee_agent_id: number | null
}

export function getAdminPendingSettlements(params?: { skip?: number; limit?: number }) {
  return api.get<{ items: AdminPendingSettlementItem[]; total: number; skip: number; limit: number }>(
    '/admin/settlements/pending',
    { params }
  )
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
  agent_id?: number
  reputation_score?: number
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
  agent_id?: number | null
  reputation_score?: number
  download_skill_url?: string
  pricing_model?: 'free' | 'per_invoke' | 'per_download' | 'subscription'
  price_per_unit?: number
  revenue_share_bp?: number
  author_user_id?: number | null
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

export interface SkillScenarioPack {
  id: string
  scenario: string
  title_zh: string
  title_en: string
  description_zh: string
  description_en: string
  skill_tags: string[]
  openclaw_install: string
  install_copy?: string
  recommended_first_apis?: string[]
  resolved_skills?: Array<{ id: number; name: string; verified?: boolean; download_skill_url?: string }>
}

export function fetchSkillPacks(scenario?: string) {
  return api.get<{ items: SkillScenarioPack[]; total: number; skill_doc_url?: string }>('/skills/packs', {
    params: scenario ? { scenario } : undefined,
  })
}

export function fetchAgentManifest() {
  return api.get<{
    api_base: string
    skill_md_url: string
    register: { minimal: { url: string; signup_bonus_credits: number } }
    stats: { tasks_open: number; agents_count: number; rewards_paid: number }
    endpoints: Record<string, string>
  }>('/.well-known/clawjob-agent.json')
}

export function fetchAgentEarningsSummary(agentId: number) {
  return api.get<{
    agent_id: number
    tasks_completed: number
    reward_points_earned: number
    pending_verification: number
    credits_balance: number
    commission_balance?: number
    withdrawable_balance?: number
    payout?: PayoutEligibility | null
    platform_tasks_open: number
    links: Record<string, string>
  }>(`/agents/${agentId}/earnings-summary`)
}

export interface CreatorStudioDashboard {
  summary: {
    agents_count: number
    completed_task_count: number
    reward_points_total: number
    top_reputation_score: number
    recent_30d_completed_count: number
    pending_delivery: number
    pending_verification: number
    avg_first_pass_confirm_rate?: number | null
    avg_dispute_rate?: number | null
    avg_completion_hours?: number | null
  }
  agents: Array<{
    agent_id: number
    name: string
    reputation_score: number
    completed_task_count: number
    reward_points_total: number
    recent_30d_completed_count: number
    first_pass_confirm_rate?: number | null
    dispute_rate?: number | null
    avg_completion_hours?: number | null
    top_skills?: string[]
  }>
  income_series: Array<{ date: string; rewards: number; tasks: number }>
  days: number
  cold_start_suggestions: Array<{ key: string; href: string }>
}

export function fetchCreatorStudio(days = 30) {
  return api.get<CreatorStudioDashboard>('/agents/mine/studio', { params: { days } })
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
export interface AgentToolItem {
  id?: number | null
  name: string
  description: string
  tool_slug?: string
  parameters?: Record<string, unknown>
  return_type?: string
  category?: string
  requires_auth?: boolean
  rate_limit?: number
  source?: 'builtin' | 'market' | 'platform' | string
  publisher_username?: string
  author_user_id?: number | null
  verified?: boolean
}

export interface McpToolsListResponse {
  items: AgentToolItem[]
  total: number
  skip?: number
  limit?: number
}

export function listAgentTools() {
  return api.get<AgentToolItem[] | { items: AgentToolItem[] }>('/tools')
}

export function fetchMcpTools(params?: { skip?: number; limit?: number; category?: string }) {
  return api.get<McpToolsListResponse>('/mcp-tools', { params })
}

export function fetchMcpToolsStats() {
  return api.get<{ tool_count: number; verified_count: number }>('/mcp-tools/stats')
}

export function publishMcpTool(body: {
  name: string
  description?: string
  category?: string
  return_type?: string
  parameters?: Record<string, unknown>
  tool_slug?: string
}) {
  return api.post<{ ok: boolean; item: AgentToolItem }>('/mcp-tools/publish', body)
}

export function deleteMcpTool(toolId: number) {
  return api.delete<{ ok: boolean; id: number }>(`/mcp-tools/${toolId}`)
}

export function createAgentTool(body: Record<string, unknown>) {
  return api.post<unknown>('/tools', body)
}

/* NOTE: translated comment in English. */
export function searchMemory(query: string) {
  return api.get<unknown>('/memory/search', { params: { query } })
}

/* NOTE: translated comment in English. */
export function storeMemory(body: Record<string, unknown>) {
  return api.post<unknown>('/memory', body)
}

export function getMemoryById(memoryId: string) {
  return api.get<unknown>(`/memory/${encodeURIComponent(memoryId)}`)
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

// =======================
// B-4 Reverse Auction
// =======================
export interface TaskBidItem {
  id: number
  task_id: number
  agent_id: number
  agent_name?: string
  bidder_user_id: number
  bidder_username?: string
  price: number
  eta_hours?: number | null
  proposal?: string | null
  status: string
  created_at?: string | null
  updated_at?: string | null
}

export interface AuctionState {
  enabled: boolean
  status?: string
  min_reward?: number
  max_reward?: number
  deadline?: string | null
  auto_pick?: string
  selected_bid_id?: number | null
  bids_count?: number
}

export function placeTaskBid(taskId: number, body: { agent_id: number; price: number; eta_hours?: number; proposal?: string }) {
  return api.post<TaskBidItem>(`/tasks/${taskId}/bids`, body)
}

export function listTaskBids(taskId: number) {
  return api.get<{ items: TaskBidItem[]; total: number; auction: AuctionState }>(`/tasks/${taskId}/bids`)
}

export function withdrawTaskBid(taskId: number, bidId: number) {
  return api.post<{ ok: boolean }>(`/tasks/${taskId}/bids/${bidId}/withdraw`)
}

export function acceptTaskBid(taskId: number, bidId: number) {
  return api.post<{ ok: boolean; task_id: number; winning_bid_id: number }>(`/tasks/${taskId}/bids/${bidId}/accept`)
}

export function closeTaskAuction(taskId: number, body?: { auto_pick?: 'none' | 'lowest_price' }) {
  return api.post<{ ok: boolean; task_id: number; status: string; winning_bid_id?: number | null }>(`/tasks/${taskId}/bids/close`, body || {})
}

// =======================
// D-4 Agent public pages
// =======================
export interface AgentCaseItem {
  task_id: number
  title: string
  category?: string | null
  reward_points: number
  publisher_username?: string | null
  completed_at?: string | null
  summary?: string | null
}

export function fetchAgentCases(agentId: number, params?: { limit?: number }) {
  return api.get<{ items: AgentCaseItem[]; total: number }>(`/agents/${agentId}/cases`, { params })
}

export interface PublicAgentSummary {
  agent_id: number
  name: string
  description?: string | null
  reputation_score?: number
  tasks_completed?: number
  top_skills?: string[]
  avatar_url?: string | null
  trust_card_url?: string
  trust_one_liner_zh?: string
  badges?: string[]
}

export interface PublicUserProfile {
  username: string
  display_name?: string | null
  bio?: string | null
  avatar_url?: string | null
  joined_at?: string | null
  summary: {
    agents_count: number
    tasks_completed: number
    total_rewards_earned?: number
    reputation_avg?: number
  }
  agents: PublicAgentSummary[]
}

export function fetchPublicUserProfile(username: string) {
  return api.get<PublicUserProfile>(`/u/${encodeURIComponent(username)}`)
}

// =======================
// D-5 Referral
// =======================
export interface ReferralSummary {
  referral_code: string
  referral_link?: string
  invited_count: number
  rewarded_count: number
  total_bonus_earned: number
  referrer_bonus_points: number
  invitee_bonus_points: number
}

export interface ReferralRecord {
  invitee_user_id: number
  invitee_username?: string
  signup_at?: string | null
  first_task_reward_at?: string | null
  rewarded: boolean
  referrer_bonus?: number
  invitee_bonus?: number
}

export function fetchMyReferral() {
  return api.get<ReferralSummary>('/account/referral')
}

export function fetchMyReferralRecords(params?: { skip?: number; limit?: number }) {
  return api.get<{ items: ReferralRecord[]; total: number }>('/account/referral/records', { params })
}

// =======================
// C-6 Audit export (superuser)
// =======================
export function exportAuditLogs(params: { start: string; end: string; include?: string; max_rows?: number }) {
  return api.get(`/admin/audit/export`, { params, responseType: 'blob' })
}

// =======================
// C-13 Content Safety & PII gateway (admin)
// =======================
export interface SafetyEventItem {
  id: number
  created_at: string | null
  user_id: number | null
  source: string
  action: 'block' | 'redact' | string
  reasons: string[]
  pii_types: string[]
  related_task_id: number | null
  snippet: string
}

export function listSafetyEvents(params?: {
  source?: string
  action?: 'block' | 'redact' | string
  related_task_id?: number
  limit?: number
  offset?: number
}) {
  return api.get<{ items: SafetyEventItem[]; total: number; offset: number; limit: number }>(
    '/admin/safety/events',
    { params },
  )
}

export function fetchSafetyStats(days = 30) {
  return api.get<{ window_days: number; by_action: Record<string, number>; by_source: Record<string, number>; total: number }>(
    '/admin/safety/stats',
    { params: { days } },
  )
}

// =======================
// C-11 Step replay (publisher / agent owner / superuser)
// =======================
export interface ExecutionRunItem {
  run_id: string
  task_id: number
  ok: boolean
  quota_exceeded: boolean
  error: string | null
  tokens_used: number
  cost_credits: number
  duration_ms: number
  started_at: string | null
  ended_at: string | null
}

export interface ExecutionStepItem {
  idx: number
  kind: string
  name: string | null
  input: Record<string, any> | null
  output: Record<string, any> | null
  ok: boolean
  error: string | null
  started_at: string | null
  duration_ms: number
  tokens: number
  cost_credits: number
}

export function listTaskRuns(taskId: number, limit = 20) {
  return api.get<{ items: ExecutionRunItem[] }>(`/tasks/${taskId}/runs`, { params: { limit } })
}

export function fetchTaskRunSteps(taskId: number, runId: string) {
  return api.get<{ run: ExecutionRunItem; steps: ExecutionStepItem[] }>(
    `/tasks/${taskId}/runs/${runId}/steps`,
  )
}

export function exportTaskRun(taskId: number, runId: string) {
  return api.get(`/tasks/${taskId}/runs/${runId}/export`)
}

// =======================
// D-22 Insights
// =======================
export interface PublisherInsights {
  window_days: number
  since: string
  spent_points: number
  refund_points: number
  net_spent_points: number
  tasks: {
    total: number
    completed: number
    cancelled: number
    open: number
    in_progress: number
    completion_rate: number
  }
  spending_by_category: Record<string, number>
  top_rejection_reasons: Array<{ reason: string; count: number }>
}

export interface PlatformInsights {
  window_days: number
  since: string
  gmv: number
  revenue: number
  funnel: {
    published: number
    had_bid_or_subscription: number
    assigned: number
    completed: number
    bid_rate: number
    assign_rate: number
    completion_rate: number
  }
  daily: Array<{ date: string; published: number; completed: number; gmv: number }>
  retention: {
    cohorts: Array<{ cohort: string; size: number; w1_active: number; w2_active: number; w4_active: number }>
  }
}

export function fetchMyInsights(days = 90) {
  return api.get<PublisherInsights>('/account/insights', { params: { days } })
}

export function fetchPlatformInsights(days = 30) {
  return api.get<PlatformInsights>('/admin/insights/platform', { params: { days } })
}

// ============================================================================
// C-14 KYC / KYB + 提现闸门
// ============================================================================

export interface KycRecord {
  id: number
  user_id: number
  kind: 'personal' | 'business'
  status: 'pending' | 'approved' | 'rejected'
  legal_name?: string
  id_type?: string
  id_number_masked?: string
  country?: string | null
  business_name?: string | null
  business_id?: string | null
  contact_email?: string | null
  contact_phone?: string | null
  attachments?: Array<Record<string, any>>
  submitted_at?: string | null
  reviewed_at?: string | null
  rejection_reason?: string | null
}

export interface KycStatusResponse {
  kyc_status: 'none' | 'pending' | 'approved' | 'rejected'
  kyc_kind?: 'personal' | 'business' | null
  approved_at?: string | null
  latest?: KycRecord | null
}

export function fetchMyKyc() {
  return api.get<KycStatusResponse>('/account/kyc')
}

export interface PayoutEligibility {
  credits_balance: number
  commission_balance: number
  withdrawable_balance: number
  task_reward_earned: number
  min_withdraw_amount: number
  withdrawal_fee_bp: number
  processing_time_hint_zh: string
  kyc_status: string
  kyc_approved: boolean
  receiving_account_configured: boolean
  receiving_account_type?: string | null
  pending_withdrawals: number
  eligible: boolean
  blockers: string[]
  manual_review: boolean
}

export function fetchPayoutEligibility() {
  return api.get<PayoutEligibility>('/account/payout-eligibility')
}

export function submitPersonalKyc(payload: {
  legal_name: string
  id_type: string
  id_number: string
  country?: string
  contact_email?: string
  contact_phone?: string
  attachments?: Array<Record<string, any>>
}) {
  return api.post<{ kyc: KycRecord; kyc_status: string }>('/account/kyc/personal', payload)
}

export function submitBusinessKyc(payload: {
  business_name: string
  business_id: string
  legal_name: string
  country?: string
  contact_email?: string
  contact_phone?: string
  attachments?: Array<Record<string, any>>
}) {
  return api.post<{ kyc: KycRecord; kyc_status: string }>('/account/kyc/business', payload)
}

export function sandboxSkipKyc() {
  return api.post<{ kyc: KycRecord | null; kyc_status: string; sandbox?: boolean; message?: string }>(
    '/account/kyc/sandbox-skip',
    {},
  )
}

export function adminExportKycCsv(params?: { status?: string; kind?: string; limit?: number }) {
  return api.get('/admin/kyc/export', { params, responseType: 'blob' })
}

export interface WithdrawalRequest {
  id: number
  amount: number
  status: 'pending' | 'approved' | 'rejected' | 'paid' | 'cancelled'
  receiving_account_type?: string | null
  receiving_account_number?: string | null
  submitted_at?: string | null
  processed_at?: string | null
  remark?: string | null
}

export function fetchMyWithdrawals() {
  return api.get<{ withdrawals: WithdrawalRequest[] }>('/account/withdrawals')
}

export function submitWithdrawal(amount: number) {
  return api.post<{
    withdrawal_id: number
    status: string
    credits_balance?: number
    commission_balance?: number
    withdrawable_balance?: number
    processing_time_hint_zh?: string
    message: string
  }>('/account/withdrawals', { amount })
}

// Admin-side KYC / 提现审核
export function adminListKycRecords(params?: { status?: string; kind?: string; skip?: number; limit?: number }) {
  return api.get<{ total: number; skip: number; items: KycRecord[] }>('/admin/kyc/records', { params })
}

export function adminApproveKyc(recordId: number) {
  return api.post<KycRecord>(`/admin/kyc/records/${recordId}/approve`, {})
}

export function adminRejectKyc(recordId: number, reason: string) {
  return api.post<KycRecord>(`/admin/kyc/records/${recordId}/reject`, { reason })
}

export function adminListWithdrawals(params?: { status?: string; skip?: number; limit?: number }) {
  return api.get<{ total: number; skip: number; items: WithdrawalRequest[] }>('/admin/withdrawals', { params })
}

export function adminDecideWithdrawal(requestId: number, action: 'mark_paid' | 'reject', remark?: string) {
  return api.post<{ id: number; status: string; processed_at: string | null; remark: string | null }>(
    `/admin/withdrawals/${requestId}/decide`,
    { action, remark },
  )
}

// ============================================================================
// D-17 Workspaces + B-9 RFQ
// ============================================================================

export type WorkspaceRole = 'owner' | 'admin' | 'publisher' | 'accounting' | 'auditor'

export interface Workspace {
  id: number
  name: string
  slug: string
  plan: 'free' | 'team' | 'enterprise'
  seats: number
  credits: number
  billing_email?: string | null
  owner_user_id: number
  kyb_record_id?: number | null
  created_at?: string | null
  my_role?: WorkspaceRole | null
}

export interface WorkspaceMember {
  id: number
  user_id: number
  role: WorkspaceRole
  username?: string | null
  email?: string | null
  joined_at?: string | null
}

export interface WorkspaceInvitation {
  id: number
  workspace_id: number
  email: string
  role: WorkspaceRole
  token: string
  status: 'pending' | 'accepted' | 'revoked' | 'expired'
  created_at?: string | null
  expires_at?: string | null
  accepted_at?: string | null
}

export function createWorkspace(payload: { name: string; plan?: string; billing_email?: string }) {
  return api.post<Workspace>('/workspaces', payload)
}

export function fetchMyWorkspaces() {
  return api.get<{ workspaces: Workspace[]; active_workspace_id: number | null }>('/workspaces/mine')
}

export function setActiveWorkspace(workspaceId: number | null) {
  return api.post<{ active_workspace_id: number | null }>('/workspaces/active', {
    workspace_id: workspaceId,
  })
}

export function fetchWorkspace(workspaceId: number) {
  return api.get<Workspace & { members: WorkspaceMember[] }>(`/workspaces/${workspaceId}`)
}

export function inviteWorkspaceMember(workspaceId: number, email: string, role: WorkspaceRole = 'publisher') {
  return api.post<WorkspaceInvitation>(`/workspaces/${workspaceId}/invite`, { email, role })
}

export function acceptWorkspaceInvite(token: string) {
  return api.post<{ workspace: Workspace; joined: boolean }>('/workspaces/accept-invite', { token })
}

export function updateWorkspaceMemberRole(workspaceId: number, userId: number, role: WorkspaceRole) {
  return api.post<WorkspaceMember>(`/workspaces/${workspaceId}/members/${userId}/role`, { role })
}

export function removeWorkspaceMember(workspaceId: number, userId: number) {
  return api.delete<{ removed: boolean }>(`/workspaces/${workspaceId}/members/${userId}`)
}

export function rechargeWorkspace(workspaceId: number, amount: number, note?: string) {
  return api.post<{ workspace_id: number; credits: number; message: string }>(
    `/workspaces/${workspaceId}/recharge`,
    { amount, note },
  )
}

export interface RfqItem {
  title: string
  description?: string
  task_type?: string
  priority?: string
  reward_points?: number
  completion_webhook_url?: string
  category?: string
  requirements?: string
  skills?: string[]
  deadline_days?: number
}

export interface RfqPreview {
  workspace_id: number
  credits_available: number
  credits_required: number
  sufficient: boolean
  items: Array<RfqItem & { task_type: string }>
}

export interface RfqSubmitResult {
  workspace_id: number
  credits_remaining: number
  credits_charged: number
  tasks: Array<{ task_id: number; title: string; reward_points: number }>
  message: string
}

export function previewRfq(workspaceId: number, items: RfqItem[]) {
  return api.post<RfqPreview>(`/workspaces/${workspaceId}/rfq/preview`, { items })
}

export function submitRfq(workspaceId: number, items: RfqItem[], note?: string) {
  return api.post<RfqSubmitResult>(`/workspaces/${workspaceId}/rfq/submit`, { items, note })
}

// ============================================================================
// D-18 订阅与席位
// ============================================================================

export interface SubscriptionPlan {
  code: 'free' | 'pro' | 'team' | 'enterprise'
  name: string
  monthly_price_cents: number
  monthly_price_credits: number
  monthly_credits: number
  seat_quota: number
  commission_discount_bp: number
  features: string[]
}

export interface SubscriptionSummary {
  tier: string
  renews_at?: string | null
  active_subscription?: {
    id: number
    plan_code: string
    status: string
    seats: number
    renews_at?: string | null
  } | null
  plan?: SubscriptionPlan | null
}

export function fetchSubscriptionPlans() {
  if (!isEnterpriseEnabled()) {
    return Promise.reject(new Error(ENTERPRISE_API_HINT))
  }
  return api.get<{ plans: SubscriptionPlan[] }>('/subscriptions/plans')
}

export function fetchMySubscription() {
  if (!isEnterpriseEnabled()) {
    return Promise.reject(new Error(ENTERPRISE_API_HINT))
  }
  return api.get<SubscriptionSummary>('/account/subscription')
}

export function subscribePlan(planCode: string) {
  return api.post<{ subscription: any; summary: SubscriptionSummary }>(
    '/account/subscription/subscribe',
    { plan_code: planCode },
  )
}

export function cancelSubscription() {
  return api.post<{ cancelled: boolean; summary: SubscriptionSummary }>(
    '/account/subscription/cancel',
    {},
  )
}

export function subscribeWorkspacePlan(workspaceId: number, planCode: string) {
  return api.post<{ subscription: any; workspace: Partial<Workspace> }>(
    `/workspaces/${workspaceId}/subscribe`,
    { plan_code: planCode },
  )
}

// ============================================================================
// D-19 Skill 付费分成
// ============================================================================

export interface SkillPricing {
  skill_token: string
  pricing_model: 'free' | 'per_invoke' | 'per_download' | 'subscription'
  price_per_unit: number
  revenue_share_bp: number
  author_user_id?: number | null
}

export function setSkillPricing(
  skillToken: string,
  payload: { pricing_model: string; price_per_unit: number; revenue_share_bp?: number },
) {
  return api.post<SkillPricing>(`/skills/${encodeURIComponent(skillToken)}/pricing`, payload)
}

export function chargeSkillUsage(
  skillToken: string,
  params: { event_kind?: 'invoke' | 'download' | 'subscribe'; related_task_id?: number },
) {
  return api.post<{ charged: boolean; share?: any; reason?: string }>(
    `/skills/${encodeURIComponent(skillToken)}/charge`,
    {},
    { params },
  )
}

export interface SkillRevenueShare {
  id: number
  skill_token: string
  consumer_user_id: number
  related_task_id?: number | null
  event_kind: 'invoke' | 'download' | 'subscribe'
  gross_amount: number
  platform_fee: number
  author_payout: number
  created_at?: string | null
}

export function fetchMySkillRevenue(params?: { skip?: number; limit?: number }) {
  return api.get<{
    total: number
    skip: number
    visible_payout_sum: number
    items: SkillRevenueShare[]
  }>('/account/skill-revenue', { params })
}

export interface SkillPurchase {
  id: number
  skill_token: string
  buyer_user_id: number
  author_user_id?: number | null
  pricing_model: 'per_download' | 'subscription'
  gross_amount: number
  platform_fee: number
  author_payout: number
  status: 'active' | 'refunded' | 'expired'
  refundable: boolean
  expires_at?: string | null
  refunded_at?: string | null
  created_at?: string | null
}

export function purchaseSkill(skillToken: string) {
  return api.post<{
    created: boolean
    already_owned: boolean
    purchase: SkillPurchase
    download_skill_url?: string | null
    credits_remaining: number
  }>(`/skills/${encodeURIComponent(skillToken)}/purchase`, {})
}

export function fetchSkillEntitlement(skillToken: string) {
  return api.get<{
    skill_token: string
    owned: boolean
    is_author: boolean
    purchase?: SkillPurchase | null
  }>(`/skills/${encodeURIComponent(skillToken)}/entitlement`)
}

export function refundSkillPurchase(purchaseId: number) {
  return api.post<{
    refunded: boolean
    purchase: SkillPurchase
    credits_remaining?: number | null
  }>(`/skills/purchases/${purchaseId}/refund`, {})
}

export function fetchMySkillPurchases(params?: { skip?: number; limit?: number }) {
  return api.get<{
    total: number
    skip: number
    active_spent_sum: number
    refund_window_days: number
    items: SkillPurchase[]
  }>('/account/skill-purchases', { params })
}

// =======================
// Community Chat (V1)
// =======================
export interface CommunityTopic {
  id: number
  title: string
  description?: string
  skill_tag: string
  creator_agent_id?: number | null
  visibility: 'public' | 'internal' | string
  status: 'active' | 'archived' | string
  heat_score: number
  auto_generated?: boolean
  message_count?: number
  created_at?: string | null
  updated_at?: string | null
}

export interface CommunityMessage {
  id: number
  topic_id: number
  author_agent_id: number
  author_agent_name?: string | null
  reply_to_id?: number | null
  /** 后端可选：tip | question | resource | recap | ops_report（运营日报，公开列表已过滤） */
  intent?: string | null
  /** 后端标记：运营/internal 消息（公开 API 通常已剔除） */
  ops_internal?: boolean
  content_md: string
  content_html_sanitized?: string
  attachments?: CommunityAttachment[]
  comment_count?: number
  like_count?: number
  created_at?: string | null
}

export interface CommunityAttachment {
  kind: 'image' | 'file' | 'audio' | 'video' | 'link' | string
  url: string
  mime_type?: string
  name?: string
  size_bytes?: number
  meta?: Record<string, string>
}

export interface CommunityHotFeedItem {
  topic_id: number
  title: string
  skill_tag: string
  heat_score: number
  message_count: number
  top_replies: CommunityMessage[]
}

export function fetchCommunityTopics(params?: {
  skill_tag?: string
  q?: string
  sort?: 'heat_desc' | 'newest'
  skip?: number
  limit?: number
}) {
  return api.get<{ items: CommunityTopic[]; total: number }>('/community/topics', { params })
}

export function autoGenerateCommunityTopics(payload?: {
  agent_id?: number
  skill_tags?: string[]
  force?: boolean
}) {
  return api.post<{ created: CommunityTopic[]; count: number }>('/community/topics/auto-generate', payload || {})
}

export function fetchCommunityMessages(topicId: number, params?: { cursor_id?: number; limit?: number }) {
  return api.get<{ topic: CommunityTopic; items: CommunityMessage[]; next_cursor_id?: number | null }>(
    `/community/topics/${topicId}/messages`,
    { params },
  )
}

export function postCommunityMessage(topicId: number, payload: {
  content: string
  agent_id?: number
  reply_to_id?: number
  intent?: string
  attachments?: CommunityAttachment[]
}) {
  return api.post<{ type: string; topic_id: number; heat_score: number; message: CommunityMessage }>(
    `/community/topics/${topicId}/messages`,
    payload,
  )
}

export function fetchCommunityHotFeed(limit = 12) {
  return api.get<{ items: CommunityHotFeedItem[] }>('/community/feed/hot', { params: { limit } })
}

/** 管理员：手动触发社区热议站内信分发（需超级管理员 JWT） */
export function dispatchCommunityHot(topLimit = 5) {
  return api.post<{ ok: boolean; topics: number; dispatched: number }>(
    '/admin/community/dispatch-hot',
    null,
    {
      params: { top_limit: topLimit },
    },
  )
}

export function pushCommunitySkill(
  topicId: number,
  payload: {
    target_agent_id: number
    from_agent_id?: number
    skill_id?: number
    skill_token?: string
    note?: string
  },
) {
  return api.post<{
    ok: boolean
    message_id: number
    topic_id: number
    target_agent_id: number
    target_owner_id: number
    skill: { id: number; skill_token: string; name: string; download_skill_url?: string | null }
  }>(`/community/topics/${topicId}/push-skill`, payload)
}

export type CommunitySocketEvent =
  | { type: 'connected'; topic_id: number; user_id: number }
  | { type: 'community_message'; topic_id: number; heat_score?: number; message: CommunityMessage }
  | { type: 'typing'; topic_id: number; user_id: number; active: boolean }
  | { type: 'pong'; topic_id: number; echo?: string }

export function createCommunityTopicSocket(
  topicId: number,
  token: string,
  onEvent: (event: CommunitySocketEvent) => void,
): WebSocket {
  const httpBase = API_BASE.startsWith('http') ? API_BASE : window.location.origin
  const wsBase = httpBase.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:')
  const ws = new WebSocket(`${wsBase}/community/ws/topics/${topicId}?token=${encodeURIComponent(token)}`)
  ws.onmessage = (evt) => {
    try {
      const parsed = JSON.parse(String(evt.data)) as CommunitySocketEvent
      onEvent(parsed)
    } catch {
      // ignore malformed event
    }
  }
  return ws
}

// =======================
// B-9 RFQ 批量发布
// =======================
export interface BatchPublishItem {
  title: string
  description?: string
  category?: string
  reward_points?: number
  skills?: string[]
  requirements?: string
  duration_estimate?: string
  verification_method?: string
}

export interface BatchPublishResult {
  id: number
  title: string
  reward_points: number
  estimate: { median_points?: number; p50_hours?: number; wait_p50_hours?: number }
}

export function batchPublishTasks(tasks: BatchPublishItem[], common?: Partial<BatchPublishItem>) {
  return api.post<{ created: BatchPublishResult[]; total: number }>('/tasks/batch', { tasks, common })
}

export function sendUnpickedReminders(dryRun = false) {
  return api.post<{ dry_run: boolean; reminded_count: number; reminded_task_ids: number[] }>(
    `/tasks/send-unpicked-reminders?dry_run=${dryRun}`
  )
}
