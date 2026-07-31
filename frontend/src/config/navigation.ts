/**
 * 全站导航 — 读取 shared/site-navigation.json（构建前 sync-shared-config 同步）
 */
import type { Component } from 'vue'
import {
  BookOpen,
  Bot,
  Home,
  MessagesSquare,
  Plug,
  Shield,
  Store,
  TrendingUp,
  UserPlus,
  Wallet,
} from 'lucide-vue-next'
import siteNavJson from './site-navigation.json'

export type NavAccess = 'public' | 'auth' | 'admin'
export type NavZone = 'primary' | 'overflow' | 'marketing'

export interface NavItemDef {
  id: string
  labelKey: string
  to: string
  icon: Component
  access: NavAccess
  zones: NavZone[]
  linkClass?: string
  hideOnMobile?: boolean
  overflowMobileOnly?: boolean
  activeMatch?: (path: string) => boolean
}

export interface RouteAccessMeta {
  access: NavAccess
  layout?: 'app' | 'marketing'
  titleKey?: string
}

type SiteNavItemConfig = {
  route: string
  labelKey: string
  access: NavAccess
  linkClass?: string
  hideOnMobile?: boolean
  overflowMobileOnly?: boolean
}

const ICONS: Record<string, Component> = {
  home: Home,
  tasks: TrendingUp,
  community: MessagesSquare,
  marketplace: Store,
  join: UserPlus,
  mcp: Plug,
  docs: BookOpen,
  agents: Bot,
  account: Wallet,
  admin: Shield,
}

const ACTIVE: Record<string, (p: string) => boolean> = {
  home: (p) => p === '/',
  tasks: (p) => p === '/tasks',
  community: (p) => p === '/community',
  marketplace: (p) => p === '/marketplace' || p.startsWith('/marketplace/'),
  join: (p) => p === '/join',
  mcp: (p) => p === '/docs/mcp',
  docs: (p) => p.startsWith('/docs') && p !== '/docs/mcp',
  agents: (p) => p.startsWith('/agents') && !/^\/agents\/\d+/.test(p),
  account: (p) => p === '/account',
  admin: (p) => p.startsWith('/admin'),
}

function buildNavItems(): NavItemDef[] {
  const cfg = siteNavJson as {
    primary: string[]
    overflow: string[]
    items: Record<string, SiteNavItemConfig>
  }
  const zoneMap = new Map<string, NavZone[]>()
  for (const id of cfg.primary) {
    zoneMap.set(id, [...(zoneMap.get(id) || []), 'primary'])
  }
  for (const id of cfg.overflow) {
    zoneMap.set(id, [...(zoneMap.get(id) || []), 'overflow'])
  }
  return Object.entries(cfg.items).map(([id, item]) => ({
    id,
    labelKey: item.labelKey,
    to: item.route,
    icon: ICONS[id] || Home,
    access: item.access,
    zones: zoneMap.get(id) || ['overflow'],
    linkClass: item.linkClass,
    hideOnMobile: item.hideOnMobile,
    overflowMobileOnly: item.overflowMobileOnly,
    activeMatch: ACTIVE[id],
  }))
}

export const ROUTE_ACCESS: Record<string, RouteAccessMeta> = {
  '/': { access: 'public', layout: 'marketing', titleKey: 'common.home' },
  '/tasks': { access: 'public', titleKey: 'nav.market' },
  '/community': { access: 'public', titleKey: 'nav.community' },
  '/marketplace': { access: 'public', titleKey: 'nav.skillMarket' },
  '/agents': { access: 'auth', titleKey: 'nav.agentManage' },
  '/account': { access: 'auth', titleKey: 'common.myAccount' },
  '/join': { access: 'public', titleKey: 'nav.joinAgent' },
  '/skill': { access: 'public', titleKey: 'common.skill' },
  '/docs': { access: 'public', titleKey: 'common.docs' },
  '/docs/mcp': { access: 'public', titleKey: 'nav.mcp' },
  '/docs/manual': { access: 'public', titleKey: 'common.docs' },
  '/docs/openclaw-quickstart': { access: 'public', titleKey: 'nav.playbook' },
  '/auth/callback': { access: 'public' },
}

export const ADMIN_ROUTE_PREFIX = '/admin'
export const APP_NAV_ITEMS: NavItemDef[] = buildNavItems()

export const MARKETING_SECTION_LINKS = (
  siteNavJson as { marketingAnchors: Array<{ id: string; labelKey: string }> }
).marketingAnchors.map((a) => ({ id: a.id, labelKey: a.labelKey }))

export function navItemsForZone(
  zone: NavZone,
  opts: { isAdmin?: boolean; isLoggedIn?: boolean; mobile?: boolean } = {},
): NavItemDef[] {
  const { isAdmin = false, mobile = false } = opts
  return APP_NAV_ITEMS.filter((item) => {
    if (!item.zones.includes(zone)) return false
    if (zone === 'primary' && mobile && item.hideOnMobile) return false
    if (item.access === 'admin' && !isAdmin) return false
    return true
  })
}

export function routeAccessMeta(path: string): RouteAccessMeta {
  if (path.startsWith(ADMIN_ROUTE_PREFIX)) {
    return { access: 'admin', titleKey: 'nav.adminNav' }
  }
  if (path.startsWith('/agents/') && path !== '/agents') {
    return { access: 'public', titleKey: 'nav.agentManage' }
  }
  if (path.startsWith('/u/') || path.startsWith('/@')) {
    return { access: 'public' }
  }
  return ROUTE_ACCESS[path] ?? { access: 'public' }
}

export function isNavItemActive(item: NavItemDef, path: string): boolean {
  if (item.activeMatch) return item.activeMatch(path)
  return path === item.to || path.startsWith(`${item.to}/`)
}
