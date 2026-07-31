<script setup lang="ts">
import { inject, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '../../components/ui/button'
import { TableCell, TableHead, TableRow } from '../../components/ui/table'
import AdminDataTable from '../../components/admin/AdminDataTable.vue'
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue'
import KycRejectDialog from '../../components/admin/KycRejectDialog.vue'
import * as api from '../../api'
import { safeT } from '../../i18n'
import { ADMIN_CONTEXT_KEY } from '../../composables/admin/adminContext'
import { useAdminPaginatedList } from '../../composables/admin/useAdminPaginatedList'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const ctx = inject(ADMIN_CONTEXT_KEY)

const kycExporting = ref(false)
const kycDecideLoading = ref<number | null>(null)
const rejectOpen = ref(false)
const rejectKycId = ref<number | null>(null)
const withdrawDecideLoading = ref<number | null>(null)

const {
  loading: kycLoading,
  items: kycRecords,
  pageMeta: kycPageMeta,
  reload: reloadKyc,
  prevPage: kycPrev,
  nextPage: kycNext,
} = useAdminPaginatedList(async ({ skip, limit }) => {
  const res = await api.adminListKycRecords({ status: 'pending', skip, limit })
  return { items: res.data.items || [], total: res.data.total || 0 }
})

const {
  loading: withdrawalsLoading,
  items: withdrawals,
  pageMeta: withdrawPageMeta,
  reload: reloadWithdrawals,
  prevPage: withdrawPrev,
  nextPage: withdrawNext,
} = useAdminPaginatedList(async ({ skip, limit }) => {
  const res = await api.adminListWithdrawals({ status: 'pending', skip, limit })
  return { items: res.data.items || [], total: res.data.total || 0 }
})

function approveKyc(id: number) {
  kycDecideLoading.value = id
  api.adminApproveKyc(id)
    .then(async () => { await reloadKyc(); await ctx?.refreshOverview() })
    .finally(() => { kycDecideLoading.value = null })
}

function openReject(id: number) {
  rejectKycId.value = id
  rejectOpen.value = true
}

function onRejectConfirm(payload: { kycId: number; reason: string }) {
  kycDecideLoading.value = payload.kycId
  api.adminRejectKyc(payload.kycId, payload.reason)
    .then(async () => { rejectOpen.value = false; await reloadKyc(); await ctx?.refreshOverview() })
    .finally(() => { kycDecideLoading.value = null })
}

function exportKycCsv() {
  kycExporting.value = true
  api.adminExportKycCsv({ status: 'pending', limit: 5000 })
    .then((res) => {
      const url = URL.createObjectURL(res.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `kyc_export_${Date.now()}.csv`
      a.click()
      URL.revokeObjectURL(url)
    })
    .finally(() => { kycExporting.value = false })
}

function decideWithdraw(id: number, action: 'mark_paid' | 'reject') {
  withdrawDecideLoading.value = id
  const remark = action === 'mark_paid' ? '支付宝/银行已转账' : '账户信息不符'
  api.adminDecideWithdrawal(id, action, remark)
    .then(async () => { await reloadWithdrawals(); await ctx?.refreshOverview() })
    .finally(() => { withdrawDecideLoading.value = null })
}

onMounted(() => {
  reloadKyc(true)
  reloadWithdrawals(true)
})
</script>

<template>
  <div class="admin-page">
    <AdminPageHeader
      :title="t('admin.nav.compliance') || '合规审核'"
      :description="t('admin.withdrawalsHint') || '人工审核后标记已打款；驳回将退回冻结的任务点/佣金。'"
    />

    <AdminDataTable
      :title="t('admin.kycTitle') || 'KYC 审核'"
      :loading="kycLoading"
      :is-empty="kycRecords.length === 0"
      :empty-message="t('admin.kycEmpty') || '暂无待审 KYC'"
      :page-from="kycPageMeta.from"
      :page-to="kycPageMeta.to"
      :page-total="kycPageMeta.total"
      :page-has-prev="kycPageMeta.hasPrev"
      :page-has-next="kycPageMeta.hasNext"
      @refresh="reloadKyc()"
      @prev="kycPrev"
      @next="kycNext"
    >
      <template #actions>
        <Button size="sm" variant="secondary" type="button" :disabled="kycExporting" @click="exportKycCsv">
          {{ t('admin.kycExport') || '导出 CSV' }}
        </Button>
      </template>
      <template #head>
        <TableRow>
          <TableHead>ID</TableHead>
          <TableHead>{{ t('admin.kycColName') || '姓名' }}</TableHead>
          <TableHead>{{ t('admin.kycColKind') || '类型' }}</TableHead>
          <TableHead class="text-right">{{ t('admin.disputeColActions') || '操作' }}</TableHead>
        </TableRow>
      </template>
      <TableRow v-for="k in kycRecords" :key="k.id">
        <TableCell class="font-mono text-sm">#{{ k.id }} · uid={{ k.user_id }}</TableCell>
        <TableCell>
          {{ k.legal_name }}
          <div class="hint font-mono text-xs">{{ k.id_number_masked }}</div>
        </TableCell>
        <TableCell>{{ k.kind }} · {{ k.status }}</TableCell>
        <TableCell class="text-right">
          <div v-if="k.status === 'pending'" class="admin-dispute-actions justify-end">
            <Button size="sm" type="button" :disabled="kycDecideLoading === k.id" @click="approveKyc(k.id)">
              {{ t('admin.kycApprove') || '通过' }}
            </Button>
            <Button size="sm" variant="secondary" type="button" :disabled="kycDecideLoading === k.id" @click="openReject(k.id)">
              {{ t('admin.kycReject') || '驳回' }}
            </Button>
          </div>
        </TableCell>
      </TableRow>
    </AdminDataTable>

    <AdminDataTable
      :title="t('admin.withdrawalsTitle') || '提现审核队列'"
      :hint="t('admin.withdrawalsLegacyHint') || 'Agent 间直接结算为主路径；以下为 platform_credits 模式的 legacy 人工打款。'"
      :loading="withdrawalsLoading"
          :is-empty="withdrawals.length === 0"
          :empty-message="t('admin.withdrawalsEmpty') || '暂无待审提现'"
          :page-from="withdrawPageMeta.from"
          :page-to="withdrawPageMeta.to"
          :page-total="withdrawPageMeta.total"
          :page-has-prev="withdrawPageMeta.hasPrev"
          :page-has-next="withdrawPageMeta.hasNext"
          :show-refresh="true"
          @refresh="reloadWithdrawals()"
          @prev="withdrawPrev"
          @next="withdrawNext"
        >
          <template #head>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>{{ t('admin.withdrawColUser') || '用户' }}</TableHead>
              <TableHead>{{ t('admin.withdrawColAmount') || '金额' }}</TableHead>
              <TableHead>{{ t('admin.withdrawColAccount') || '收款账户' }}</TableHead>
              <TableHead class="text-right">{{ t('admin.disputeColActions') || '操作' }}</TableHead>
            </TableRow>
          </template>
          <TableRow v-for="w in withdrawals" :key="w.id">
            <TableCell class="font-mono text-sm">
              #{{ w.id }}
              <div class="admin-log-time">{{ (w.submitted_at || '').slice(0, 16).replace('T', ' ') }}</div>
            </TableCell>
            <TableCell class="font-mono">uid={{ w.user_id }}</TableCell>
            <TableCell>
              <strong>{{ w.amount }}</strong>
              <div class="admin-log-level text-xs">{{ w.status }}</div>
            </TableCell>
            <TableCell class="font-mono text-sm">{{ w.receiving_account_type }} {{ w.receiving_account_number }}</TableCell>
            <TableCell class="text-right">
              <div v-if="w.status === 'pending'" class="admin-dispute-actions justify-end">
                <Button size="sm" type="button" :disabled="withdrawDecideLoading === w.id" @click="decideWithdraw(w.id, 'mark_paid')">
                  {{ t('admin.withdrawMarkPaid') || '已打款' }}
                </Button>
                <Button size="sm" variant="secondary" type="button" :disabled="withdrawDecideLoading === w.id" @click="decideWithdraw(w.id, 'reject')">
                  {{ t('admin.withdrawReject') || '驳回' }}
                </Button>
              </div>
            </TableCell>
          </TableRow>
    </AdminDataTable>

    <KycRejectDialog
      v-model:open="rejectOpen"
      :kyc-id="rejectKycId"
      :loading="kycDecideLoading != null"
      @confirm="onRejectConfirm"
    />
  </div>
</template>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: var(--space-6); }
</style>
