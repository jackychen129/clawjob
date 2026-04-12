/**
 * 任务流程时间线：相对时间与事件类型展示（与 task.justNow / timelineEventType 文案配套）
 */
export function formatTaskRelativeTime(
  t: (key: string, values?: Record<string, unknown>) => string,
  iso: string | null | undefined,
): string {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 60000
  if (diff < 1) return t('task.justNow')
  if (diff < 60) return t('task.minutesAgo', { n: Math.floor(diff) })
  if (diff < 1440) return t('task.hoursAgo', { n: Math.floor(diff / 60) })
  return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

export function timelineEventTypeLabel(
  t: (key: string) => string,
  type: string,
): string {
  const key = `task.timelineEventType.${type}`
  const msg = t(key)
  return msg === key ? type : String(msg)
}
