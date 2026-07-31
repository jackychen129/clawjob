import type { InjectionKey, Ref } from 'vue'
import type { AdminOverview } from '../composables/admin/useAdminOverview'

export type AdminContext = {
  overview: Ref<AdminOverview | null>
  refreshOverview: () => Promise<void>
}

export const ADMIN_CONTEXT_KEY: InjectionKey<AdminContext> = Symbol('admin-context')
