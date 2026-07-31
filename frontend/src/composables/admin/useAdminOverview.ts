import { computed, ref } from 'vue'
import * as api from '../../api'

export type AdminOverview = Awaited<ReturnType<typeof api.getAdminOverview>>['data']

export type AdminPendingCounts = {
  disputes: number
  settlements: number
  kyc: number
  withdrawals: number
  compliance: number
  total: number
}

export function useAdminOverview() {
  const loading = ref(false)
  const overview = ref<AdminOverview | null>(null)
  const error = ref('')

  const pendingCounts = computed(() => {
    const p = overview.value?.pending
    if (!p) {
      return {
        disputes: 0,
        settlements: 0,
        kyc: 0,
        withdrawals: 0,
        compliance: 0,
        total: 0,
      }
    }
    const settlements = p.settlements?.pending_total ?? 0
    const kyc = p.kyc_reviews ?? 0
    const withdrawals = p.withdrawals ?? 0
    const disputes = p.disputed_tasks ?? 0
    return {
      disputes,
      settlements,
      kyc,
      withdrawals,
      compliance: kyc + withdrawals,
      total: disputes + settlements + kyc + withdrawals,
    }
  })

  async function refresh() {
    loading.value = true
    error.value = ''
    try {
      const res = await api.getAdminOverview()
      overview.value = res.data
    } catch (e: unknown) {
      overview.value = null
      const ax = e as { response?: { data?: { detail?: string } }; message?: string }
      error.value = ax.response?.data?.detail || ax.message || String(e)
    } finally {
      loading.value = false
    }
  }

  return { loading, overview, error, pendingCounts, refresh }
}
