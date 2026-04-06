/**
 * 与任务待办（task_pulse）可能变化相关的路由：进出这些页面时应节流刷新 /account/me。
 * 与 docs/API_UI_COVERAGE.md 中「任务相关 Hub」描述保持一致。
 */
export function isTaskPulseHubRoute(p: string): boolean {
  if (p === '/' || p === '/tasks') return true
  if (p === '/forum' || p.startsWith('/forum/')) return true
  if (p === '/inbox' || p.startsWith('/inbox/')) return true
  if (p === '/dashboard' || p.startsWith('/dashboard/')) return true
  if (p === '/account' || p.startsWith('/account/')) return true
  return false
}

/** 路由切换是否应触发 task_pulse 刷新（同路径不刷） */
export function taskPulseRelevantNav(toPath: string, fromPath: string): boolean {
  if (toPath === fromPath) return false
  return isTaskPulseHubRoute(toPath) || isTaskPulseHubRoute(fromPath)
}
