/**
 * NOTE: translated comment in English.
 * NOTE: translated comment in English.
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
