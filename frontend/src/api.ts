/**
 * ClawJob API 请求封装
 */
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/** 跳转至 Google OAuth 授权（后端会再重定向到 Google） */
export function getGoogleLoginUrl(): string {
  return `${API_BASE}/auth/google`
}

/** 检测 Google OAuth 是否已配置（用于决定是否显示/禁用「使用 Google 登录」） */
export function getGoogleOAuthStatus(): Promise<{ configured: boolean; redirect_uri?: string; frontend_url?: string }> {
  return api.get('/auth/google/status').then((r) => r.data)
}

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

export function setAuthToken(token: string | null) {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common['Authorization']
  }
}

// 认证
export function register(data: { username: string; email: string; password: string }) {
  return api.post('/auth/register', data)
}

export function login(data: { username: string; password: string }) {
  return api.post('/auth/login', data)
}

// 任务大厅（公开）
export function fetchTasks(params?: { skip?: number; limit?: number; status_filter?: string }) {
  return api.get('/tasks', { params })
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
  invited_agent_ids?: number[]
  submitted_at?: string
  verification_deadline_at?: string
  created_at?: string
  location?: string
  duration_estimate?: string
  skills?: string[]
}

// 候选者列表（公开，供发布任务时选择指定接取者）
export function fetchCandidates(params?: { skip?: number; limit?: number }) {
  return api.get<{ candidates: Array<{ id: number; type: string; name: string; description: string; agent_type: string; owner_id: number; owner_name: string }>; total: number }>('/candidates', { params })
}

// 发布任务（需登录）；有奖励点时 completion_webhook_url 必填；invited_agent_ids 为可选指定接取者；creator_agent_id 为可选（由某 Agent 代发）
export function publishTask(data: {
  title: string
  description?: string
  task_type?: string
  priority?: string
  reward_points?: number
  completion_webhook_url?: string
  invited_agent_ids?: number[]
  creator_agent_id?: number
  location?: string
  duration_estimate?: string
  skills?: string[]
}) {
  return api.post('/tasks', data)
}

// 接取者提交完成（会 POST 到发布者的 webhook，任务进入待验收，6h 内未确认自动完成）
export function submitCompletion(taskId: number, data: { result_summary?: string; evidence?: Record<string, unknown> }) {
  return api.post(`/tasks/${taskId}/submit-completion`, data)
}

// 发布者验收通过（发放奖励）
export function confirmTask(taskId: number) {
  return api.post(`/tasks/${taskId}/confirm`)
}

// 发布者拒绝验收（接取者可重新提交）
export function rejectTask(taskId: number) {
  return api.post(`/tasks/${taskId}/reject`)
}

// 订阅任务（需登录）
export function subscribeTask(taskId: number, agentId: number) {
  return api.post(`/tasks/${taskId}/subscribe`, { agent_id: agentId })
}

// 我的 Agent（需登录）
export function registerAgent(data: { name: string; description?: string; agent_type?: string }) {
  return api.post('/agents/register', data)
}

export function fetchMyAgents() {
  return api.get('/agents/mine')
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
