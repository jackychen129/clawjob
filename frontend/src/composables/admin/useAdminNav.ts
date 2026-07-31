import { computed, type ComputedRef } from 'vue'
import { useRoute } from 'vue-router'
import {
  Activity,
  FileSearch,
  Gavel,
  LayoutDashboard,
  Plug,
  Shield,
  Wallet,
  Zap,
  type LucideIcon,
} from 'lucide-vue-next'
import type { AdminPendingCounts } from './useAdminOverview'

export type AdminNavItem = {
  to: string
  name: string
  labelKey: string
  icon: LucideIcon
  badge?: () => number
}

export type AdminNavSection = {
  id: string
  labelKey: string
  items: AdminNavItem[]
}

export function useAdminNav(pendingCounts: ComputedRef<AdminPendingCounts>) {
  const route = useRoute()

  const sections = computed<AdminNavSection[]>(() => [
    {
      id: 'operations',
      labelKey: 'admin.nav.sectionOperations',
      items: [
        { to: '/admin', name: 'AdminOverview', labelKey: 'admin.nav.overview', icon: LayoutDashboard },
        {
          to: '/admin/disputes',
          name: 'AdminDisputes',
          labelKey: 'admin.nav.disputes',
          icon: Gavel,
          badge: () => pendingCounts.value.disputes,
        },
        {
          to: '/admin/settlements',
          name: 'AdminSettlements',
          labelKey: 'admin.nav.settlements',
          icon: Wallet,
          badge: () => pendingCounts.value.settlements,
        },
        {
          to: '/admin/compliance',
          name: 'AdminCompliance',
          labelKey: 'admin.nav.compliance',
          icon: Shield,
          badge: () => pendingCounts.value.compliance,
        },
      ],
    },
    {
      id: 'platform',
      labelKey: 'admin.nav.sectionPlatform',
      items: [
        { to: '/admin/runtime', name: 'AdminRuntime', labelKey: 'admin.nav.runtime', icon: Zap },
        { to: '/admin/mcp', name: 'AdminMcp', labelKey: 'admin.nav.mcp', icon: Plug },
        { to: '/admin/audit', name: 'AdminAudit', labelKey: 'admin.nav.audit', icon: FileSearch },
        { to: '/admin/safety', name: 'AdminSafety', labelKey: 'admin.nav.safety', icon: Activity },
      ],
    },
    {
      id: 'insights',
      labelKey: 'admin.nav.sectionInsights',
      items: [],
    },
  ])

  function isActive(item: AdminNavItem) {
    if (item.to === '/admin') return route.name === 'AdminOverview'
    return route.path === item.to || route.path.startsWith(item.to + '/')
  }

  return { sections, isActive }
}

export const ADMIN_ROUTE_LABELS: Record<string, string> = {
  AdminOverview: 'admin.nav.overview',
  AdminDisputes: 'admin.nav.disputes',
  AdminSettlements: 'admin.nav.settlements',
  AdminCompliance: 'admin.nav.compliance',
  AdminRuntime: 'admin.nav.runtime',
  AdminAudit: 'admin.nav.audit',
  AdminSafety: 'admin.nav.safety',
  AdminMcp: 'admin.nav.mcp',
}
