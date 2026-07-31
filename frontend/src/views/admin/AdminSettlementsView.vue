<script setup lang="ts">
import { inject, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { TableCell, TableHead, TableRow } from '../../components/ui/table'
import AdminDataTable from '../../components/admin/AdminDataTable.vue'
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue'
import * as api from '../../api'
import { safeT } from '../../i18n'
import { usePlatformAdminKey } from '../../composables/admin/usePlatformAdminKey'
import { ADMIN_CONTEXT_KEY } from '../../composables/admin/adminContext'
import { useAdminPaginatedList } from '../../composables/admin/useAdminPaginatedList'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const ctx = inject(ADMIN_CONTEXT_KEY)
const { platformAdminKey, persist } = usePlatformAdminKey()

const {
  loading: pendingListLoading,
  items: pendingSettlementsPaged,
  pageMeta: pendingPageMeta,
  reload: reloadPendingPaged,
  prevPage: pendingPrev,
  nextPage: pendingNext,
} = useAdminPaginatedList(async ({ skip, limit }) => {
  const res = await api.getAdminPendingSettlements({ skip, limit })
  return { items: res.data.items || [], total: res.data.total || 0 }
})

const clearingLoading = ref(false)
const clearingSaving = ref(false)
const clearingError = ref('')
const clearingAccount = ref<api.PlatformClearingAccount | null>(null)
const clearingForm = ref({ alipay_account: '', alipay_name: '' })
const clearingRecords = ref<api.PlatformClearingRecord[]>([])

function settlementPhaseLabel(phase: string) {
  if (phase === 'awaiting_payee') return t('admin.settlementAwaitingPayee') || '待确认到账'
  if (phase === 'awaiting_payer') return t('admin.settlementAwaitingPayer') || '待打款'
  return phase
}

function reloadClearing() {
  const k = platformAdminKey.value.trim()
  if (!k) {
    clearingError.value = t('admin.clearingNeedKey') || '请先填写 X-Platform-Admin-Key'
    return
  }
  persist()
  clearingLoading.value = true
  clearingError.value = ''
  Promise.all([
    api.getPlatformClearingAccount(k),
    api.getPlatformClearingRecords(k, { skip: 0, limit: 20 }),
  ])
    .then(([accRes, recRes]) => {
      clearingAccount.value = accRes.data
      clearingForm.value.alipay_account = accRes.data.alipay_account || ''
      clearingForm.value.alipay_name = accRes.data.alipay_name || ''
      clearingRecords.value = recRes.data.records || []
    })
    .catch((e: unknown) => {
      const ax = e as { response?: { data?: { detail?: string } } }
      clearingError.value = ax.response?.data?.detail || String(e)
    })
    .finally(() => { clearingLoading.value = false })
}

function saveClearing() {
  const k = platformAdminKey.value.trim()
  if (!k) {
    clearingError.value = t('admin.clearingNeedKey') || '请先填写 X-Platform-Admin-Key'
    return
  }
  persist()
  clearingSaving.value = true
  clearingError.value = ''
  api.updatePlatformClearingAccount(k, {
    alipay_account: clearingForm.value.alipay_account,
    alipay_name: clearingForm.value.alipay_name,
  })
    .then((res) => {
      clearingAccount.value = res.data
      reloadClearing()
    })
    .catch((e: unknown) => {
      const ax = e as { response?: { data?: { detail?: string } } }
      clearingError.value = ax.response?.data?.detail || String(e)
    })
    .finally(() => { clearingSaving.value = false })
}

onMounted(() => {
  reloadPendingPaged(true)
})
</script>

<template>
  <div class="admin-page">
    <AdminPageHeader
      :title="t('admin.nav.settlements') || '结算运营'"
      :description="t('admin.settlementQueueHint') || 'agent_direct 任务验收后进入此队列；发布方打款 → 执行方确认。'"
    />

    <AdminDataTable
      :title="t('admin.settlementQueueTitle') || 'Agent 直连结算队列'"
      :loading="pendingListLoading"
      :is-empty="pendingSettlementsPaged.length === 0"
      :empty-message="t('admin.settlementQueueEmpty') || '暂无待结算任务'"
      :page-from="pendingPageMeta.from"
      :page-to="pendingPageMeta.to"
      :page-total="pendingPageMeta.total"
      :page-has-prev="pendingPageMeta.hasPrev"
      :page-has-next="pendingPageMeta.hasNext"
      @refresh="reloadPendingPaged()"
      @prev="pendingPrev"
      @next="pendingNext"
    >
      <template #head>
        <TableRow>
          <TableHead>{{ t('admin.disputeColTask') || '任务' }}</TableHead>
          <TableHead>{{ t('admin.settlementColReward') || '奖励' }}</TableHead>
          <TableHead>{{ t('admin.settlementColPhase') || '阶段' }}</TableHead>
          <TableHead>{{ t('admin.settlementColUpdated') || '更新时间' }}</TableHead>
        </TableRow>
      </template>
      <TableRow v-for="it in pendingSettlementsPaged" :key="it.task_id">
        <TableCell>
          <RouterLink :to="`/tasks?taskId=${it.task_id}`" class="admin-settlement-link font-medium">
            #{{ it.task_id }} {{ it.title }}
          </RouterLink>
          <div class="admin-log-time">{{ it.task_status }} · agent#{{ it.payee_agent_id ?? '-' }}</div>
        </TableCell>
        <TableCell class="font-mono">{{ it.reward_points }}</TableCell>
        <TableCell>
          <Badge :variant="it.phase === 'awaiting_payee' ? 'settlement' : 'p2p'">
            {{ settlementPhaseLabel(it.phase) }}
          </Badge>
        </TableCell>
        <TableCell class="admin-log-time">{{ (it.updated_at || it.created_at || '').slice(0, 19).replace('T', ' ') }}</TableCell>
      </TableRow>
    </AdminDataTable>

    <Card>
      <CardHeader>
        <div class="admin-panel__head">
          <div>
            <CardTitle>{{ t('admin.clearingTitle') }}</CardTitle>
            <CardDescription>{{ t('admin.clearingHint') }}</CardDescription>
          </div>
          <div class="admin-panel__actions">
            <Button size="sm" variant="secondary" type="button" :disabled="clearingLoading" @click="reloadClearing">
              {{ clearingLoading ? '…' : (t('admin.clearingLoad') || '加载中转账户') }}
            </Button>
            <Button size="sm" type="button" :disabled="clearingSaving" @click="saveClearing">
              {{ clearingSaving ? '…' : (t('admin.clearingSave') || '保存中转账户') }}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent class="flex flex-col gap-4">
        <Input v-model="platformAdminKey" type="password" :placeholder="t('admin.clearingAdminKey')" />
        <div class="grid gap-3 sm:grid-cols-2">
          <Input v-model="clearingForm.alipay_account" type="text" :placeholder="t('admin.clearingAlipayAccount')" />
          <Input v-model="clearingForm.alipay_name" type="text" :placeholder="t('admin.clearingAlipayName')" />
        </div>
        <p class="hint">{{ t('admin.clearingBalance') }}：<span class="mono">{{ clearingAccount?.balance ?? 0 }}</span></p>
        <p v-if="clearingError" class="error-msg">{{ clearingError }}</p>
        <div class="admin-cb-history">
          <h4 class="admin-cb-history__title">{{ t('admin.clearingRecordsTitle') }}</h4>
          <ul v-if="clearingRecords.length" class="admin-cb-history__list">
            <li v-for="r in clearingRecords" :key="r.id" class="admin-cb-history__item mono">
              {{ r.created_at || '-' }} · +{{ r.amount }} · task#{{ r.task_id ?? '-' }} · {{ r.remark || '-' }}
            </li>
          </ul>
          <p v-else class="hint">{{ t('admin.clearingNoRecords') }}</p>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: var(--space-6); }
</style>
