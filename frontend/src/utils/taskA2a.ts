/**
 * A2A：发布方或当前用户名下 Agent 为任务接取 Agent 时可访问 /a2a/*。
 * 与后端 `_a2a_can_access_task` 对齐。
 */
export type CanA2aParams = {
  isLoggedIn: boolean
  userId: number | null
  taskOwnerId: number
  taskAgentId?: number | null
  myAgentIds: readonly number[]
}

export function canA2aTaskParams(p: CanA2aParams): boolean {
  if (!p.isLoggedIn || p.userId == null) return false
  if (p.taskOwnerId === p.userId) return true
  if (!p.taskAgentId) return false
  return p.myAgentIds.includes(p.taskAgentId)
}
