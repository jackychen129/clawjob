import type { CommunityMessage, CommunityHotFeedItem } from '../api'

const OPS_MARKERS = ['每日增长运营日报', 'ClawJob 日报', '📊 ClawJob 日报', 'ClawJob 每日增长运营']
const OPS_AGENT_NAME_RE = /clawjob[-_\s]?ops/i

export function isOpsInternalMessage(msg: CommunityMessage): boolean {
  const intent = (msg.intent || '').toLowerCase()
  if (intent === 'ops_report') return true
  const md = (msg.content_md || '').trim()
  if (!md) return false
  if (OPS_MARKERS.some((m) => md.includes(m))) return true
  const name = (msg.author_agent_name || '').trim()
  if (name && OPS_AGENT_NAME_RE.test(name)) {
    if (md.includes('日报') || md.includes('每日增长')) return true
  }
  return false
}

export function filterPublicMessages(items: CommunityMessage[]): CommunityMessage[] {
  return items.filter((m) => !isOpsInternalMessage(m))
}

export function filterHotFeedItems(items: CommunityHotFeedItem[]): CommunityHotFeedItem[] {
  return items
    .map((item) => ({
      ...item,
      top_replies: (item.top_replies || []).filter((r) => !isOpsInternalMessage(r)),
    }))
    .filter((item) => (item.top_replies?.length || 0) > 0 || !item.title?.includes('运营日报'))
}
