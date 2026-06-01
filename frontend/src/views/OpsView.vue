<template>
  <section class="ops-wrap apple-layout">
    <PageHeader :title="t('ops.title')" :description="t('ops.desc')">
      <template #actions>
        <Button type="button" variant="secondary" size="sm" :disabled="loading" @click="reloadAll">{{ t('common.retry') }}</Button>
        <Button :as="RouterLink" to="/admin" size="sm" variant="ghost">{{ t('nav.adminNav') }}</Button>
      </template>
    </PageHeader>

    <div v-if="denied" class="card">
      <p class="error-msg">{{ t('ops.denied') }}</p>
    </div>

    <template v-else>
      <Tabs v-model="opsTab" default-value="clearing" class="ops-tabs">
        <TabList>
          <Tab value="clearing">{{ t('ops.tabClearing') }}</Tab>
          <Tab value="kyc">{{ t('ops.tabKyc') }}</Tab>
          <Tab value="audit">{{ t('ops.tabAudit') }}</Tab>
        </TabList>

        <TabPanel value="clearing">
          <div class="card card-content">
            <h3>{{ t('admin.clearingTitle') }}</h3>
            <p class="hint">{{ t('ops.clearingHint') }}</p>
            <input v-model="platformAdminKey" class="input" type="password" :placeholder="t('admin.clearingAdminKey')" />
            <div class="ops-actions">
              <Button size="sm" variant="secondary" :disabled="clearingLoading" @click="reloadClearing">{{ t('admin.clearingLoad') }}</Button>
              <Button size="sm" :disabled="clearingSaving" @click="saveClearing">{{ t('admin.clearingSave') }}</Button>
            </div>
            <p class="hint">{{ t('admin.clearingBalance') }}：<span class="mono">{{ clearingAccount?.balance ?? 0 }}</span></p>
            <p v-if="clearingError" class="error-msg">{{ clearingError }}</p>
            <ul v-if="clearingRecords.length" class="ops-records mono">
              <li v-for="r in clearingRecords" :key="r.id">
                {{ r.created_at || '-' }} · +{{ r.amount }} · task#{{ r.task_id ?? '-' }}
              </li>
            </ul>
            <p v-else class="hint">{{ t('admin.clearingNoRecords') }}</p>
          </div>
        </TabPanel>

        <TabPanel value="kyc">
          <div class="card card-content">
            <div class="ops-head">
              <h3>{{ t('admin.kycTitle') }}</h3>
              <div class="ops-actions">
                <Button size="sm" variant="secondary" :disabled="kycLoading" @click="reloadKyc">{{ t('common.retry') }}</Button>
                <Button size="sm" variant="secondary" :disabled="kycExporting" @click="exportKyc">{{ t('ops.kycExport') }}</Button>
              </div>
            </div>
            <div v-for="k in kycRecords" :key="k.id" class="ops-kyc-row">
              <span class="mono">#{{ k.id }} uid={{ k.user_id }}</span>
              <span>{{ k.legal_name }} · {{ k.kind }} · {{ k.status }}</span>
              <div v-if="k.status === 'pending'" class="ops-actions">
                <Button size="sm" @click="approveKyc(k.id)">{{ t('admin.kycApprove') }}</Button>
                <Button size="sm" variant="secondary" @click="rejectKyc(k.id)">{{ t('admin.kycReject') }}</Button>
              </div>
            </div>
            <p v-if="!kycRecords.length && !kycLoading" class="hint">{{ t('admin.kycEmpty') }}</p>
          </div>
        </TabPanel>

        <TabPanel value="audit">
          <div class="card card-content">
            <h3>{{ t('ops.auditTitle') }}</h3>
            <p class="hint">{{ t('ops.auditHint') }}</p>
            <div class="ops-actions">
              <input v-model="auditStart" class="input" type="date" />
              <input v-model="auditEnd" class="input" type="date" />
              <Button size="sm" :disabled="auditExporting" @click="exportAudit">{{ t('ops.auditExport') }}</Button>
            </div>
            <p v-if="auditError" class="error-msg">{{ auditError }}</p>
          </div>
        </TabPanel>
      </Tabs>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import PageHeader from '../components/PageHeader.vue'
import { Button } from '../components/ui/button'
import { Tabs, TabList, Tab, TabPanel } from '../components/ui/tabs'
import * as api from '../api'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()

const loading = ref(false)
const denied = ref(false)
const opsTab = ref('clearing')

const PLATFORM_ADMIN_KEY_SESSION = 'clawjob_platform_admin_key'
const platformAdminKey = ref('')
const clearingLoading = ref(false)
const clearingSaving = ref(false)
const clearingError = ref('')
const clearingAccount = ref<api.PlatformClearingAccount | null>(null)
const clearingForm = ref({ alipay_account: '', alipay_name: '' })
const clearingRecords = ref<api.PlatformClearingRecord[]>([])

const kycLoading = ref(false)
const kycExporting = ref(false)
const kycRecords = ref<api.KycRecord[]>([])

const auditStart = ref('')
const auditEnd = ref('')
const auditExporting = ref(false)
const auditError = ref('')

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function isoDate(d: Date) {
  return d.toISOString().slice(0, 10)
}

onMounted(() => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 30)
  auditEnd.value = isoDate(end)
  auditStart.value = isoDate(start)
  try {
    platformAdminKey.value = sessionStorage.getItem(PLATFORM_ADMIN_KEY_SESSION) || ''
  } catch {
    platformAdminKey.value = ''
  }
  reloadAll()
})

function reloadAll() {
  loading.value = true
  denied.value = false
  api.getAdminMetrics()
    .then(() => {
      reloadKyc()
    })
    .catch(() => {
      denied.value = true
    })
    .finally(() => {
      loading.value = false
    })
}

function persistPlatformKey() {
  try {
    const k = platformAdminKey.value.trim()
    if (k) sessionStorage.setItem(PLATFORM_ADMIN_KEY_SESSION, k)
  } catch {}
}

function reloadClearing() {
  const k = platformAdminKey.value.trim()
  if (!k) {
    clearingError.value = t('admin.clearingNeedKey')
    return
  }
  persistPlatformKey()
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
    .finally(() => {
      clearingLoading.value = false
    })
}

function saveClearing() {
  const k = platformAdminKey.value.trim()
  if (!k) {
    clearingError.value = t('admin.clearingNeedKey')
    return
  }
  persistPlatformKey()
  clearingSaving.value = true
  api.patchPlatformClearingAccount(
    { alipay_account: clearingForm.value.alipay_account, alipay_name: clearingForm.value.alipay_name },
    k,
  )
    .then((res) => {
      clearingAccount.value = res.data
    })
    .catch((e: unknown) => {
      const ax = e as { response?: { data?: { detail?: string } } }
      clearingError.value = ax.response?.data?.detail || String(e)
    })
    .finally(() => {
      clearingSaving.value = false
    })
}

function reloadKyc() {
  kycLoading.value = true
  api.adminListKycRecords({ status: 'pending', limit: 50 })
    .then((res) => {
      kycRecords.value = res.data.items || []
    })
    .catch(() => {
      kycRecords.value = []
    })
    .finally(() => {
      kycLoading.value = false
    })
}

function approveKyc(id: number) {
  api.adminApproveKyc(id).then(() => reloadKyc())
}

function rejectKyc(id: number) {
  const reason = window.prompt(t('admin.kycRejectReason'), t('ops.kycRejectDefault')) || t('ops.kycRejectDefault')
  api.adminRejectKyc(id, reason).then(() => reloadKyc())
}

function exportKyc() {
  kycExporting.value = true
  api.adminExportKycCsv({ status: 'pending', limit: 5000 })
    .then((res) => {
      downloadBlob(res.data as Blob, `kyc_export_${Date.now()}.csv`)
    })
    .finally(() => {
      kycExporting.value = false
    })
}

function exportAudit() {
  auditError.value = ''
  if (!auditStart.value || !auditEnd.value) {
    auditError.value = t('ops.auditDatesRequired')
    return
  }
  auditExporting.value = true
  api.exportAuditLogs({
    start: `${auditStart.value}T00:00:00Z`,
    end: `${auditEnd.value}T23:59:59Z`,
    include: 'system_logs,credit_transactions,tasks',
  })
    .then((res) => {
      downloadBlob(res.data as Blob, `audit_${auditStart.value}_${auditEnd.value}.zip`)
    })
    .catch((e: unknown) => {
      const ax = e as { response?: { data?: { detail?: string } } }
      auditError.value = ax.response?.data?.detail || String(e)
    })
    .finally(() => {
      auditExporting.value = false
    })
}

void auth
</script>

<style scoped>
.ops-wrap {
  max-width: 960px;
  margin: 0 auto;
}
.ops-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: var(--space-3) 0;
}
.ops-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.ops-kyc-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border-subtle);
}
.ops-records {
  list-style: none;
  padding: 0;
  margin: var(--space-3) 0 0;
  font-size: var(--font-caption);
}
.ops-records li {
  padding: var(--space-1) 0;
}
</style>
