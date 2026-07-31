<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue'
import * as api from '../../api'
import { safeT } from '../../i18n'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

const communityDispatchLoading = ref(false)
const communityDispatchResult = ref('')
const communityDispatchError = ref('')

const logsLoading = ref(false)
const logs = ref<api.AdminLogItem[]>([])
const total = ref(0)
const skip = ref(0)
const pageSize = 50
const level = ref('')
const category = ref('')

const auditStart = ref('')
const auditEnd = ref('')
const auditExporting = ref(false)
const auditError = ref('')

function reloadLogs(reset = false) {
  if (reset) skip.value = 0
  logsLoading.value = true
  api.getAdminLogs({ skip: skip.value, limit: pageSize, level: level.value || undefined, category: category.value || undefined })
    .then((res) => { logs.value = res.data.items || []; total.value = res.data.total || 0 })
    .catch(() => { logs.value = []; total.value = 0 })
    .finally(() => { logsLoading.value = false })
}

function runCommunityDispatch() {
  communityDispatchLoading.value = true
  communityDispatchError.value = ''
  communityDispatchResult.value = ''
  api.dispatchCommunityHot(5)
    .then((res) => { communityDispatchResult.value = `topics=${res.data.topics} dispatched=${res.data.dispatched}` })
    .catch((e: unknown) => {
      const ax = e as { response?: { data?: { detail?: string } }; message?: string }
      communityDispatchError.value = typeof ax.response?.data?.detail === 'string' ? ax.response.data.detail : ax.message || String(e)
    })
    .finally(() => { communityDispatchLoading.value = false })
}

function exportAudit() {
  if (!auditStart.value || !auditEnd.value) {
    auditError.value = t('ops.auditDatesRequired') || '请选择日期范围'
    return
  }
  auditExporting.value = true
  auditError.value = ''
  api.exportAuditLogs({ start: auditStart.value, end: auditEnd.value })
    .then((res) => {
      const url = URL.createObjectURL(res.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit_${auditStart.value}_${auditEnd.value}.zip`
      a.click()
      URL.revokeObjectURL(url)
    })
    .catch((e: unknown) => {
      const ax = e as { response?: { data?: { detail?: string } } }
      auditError.value = ax.response?.data?.detail || String(e)
    })
    .finally(() => { auditExporting.value = false })
}

onMounted(() => reloadLogs(true))
</script>

<template>
  <div class="admin-page">
    <AdminPageHeader
      :title="t('admin.nav.audit') || '审计与日志'"
      :description="t('admin.logs') || '系统日志与审计导出'"
    />

    <Card>
      <CardHeader>
        <div class="admin-panel__head">
          <CardTitle>{{ t('admin.communityOpsTitle') }}</CardTitle>
          <Button size="sm" type="button" variant="secondary" :disabled="communityDispatchLoading" @click="runCommunityDispatch">
            {{ communityDispatchLoading ? '…' : t('admin.communityDispatchBtn') }}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <p class="hint">{{ t('admin.communityDispatchHint') }}</p>
        <p v-if="communityDispatchResult" class="mono">{{ communityDispatchResult }}</p>
        <p v-if="communityDispatchError" class="error-msg">{{ communityDispatchError }}</p>
      </CardContent>
    </Card>

    <Card>
      <CardHeader><CardTitle>{{ t('ops.auditTitle') || '审计导出' }}</CardTitle></CardHeader>
      <CardContent>
        <p class="hint">{{ t('ops.auditHint') }}</p>
        <div class="admin-cb-actions">
          <input v-model="auditStart" class="input" type="date" />
          <input v-model="auditEnd" class="input" type="date" />
          <Button size="sm" :disabled="auditExporting" @click="exportAudit">{{ t('ops.auditExport') }}</Button>
        </div>
        <p v-if="auditError" class="error-msg">{{ auditError }}</p>
      </CardContent>
    </Card>

    <div class="card admin-card admin-logs">
      <div class="admin-logs-head">
        <h3 class="admin-logs-title">{{ t('admin.logs') || '系统日志' }}</h3>
        <div class="admin-logs-filters">
          <select v-model="level" class="input select-input admin-filter" @change="reloadLogs(true)">
            <option value="">{{ t('admin.allLevels') || '全部级别' }}</option>
            <option value="info">info</option>
            <option value="warning">warning</option>
            <option value="error">error</option>
          </select>
          <select v-model="category" class="input select-input admin-filter" @change="reloadLogs(true)">
            <option value="">{{ t('admin.allCategories') || '全部分类' }}</option>
            <option value="request">request</option>
            <option value="auth">auth</option>
            <option value="task">task</option>
            <option value="agent">agent</option>
            <option value="system">system</option>
          </select>
        </div>
      </div>
      <div v-if="logsLoading && logs.length === 0" class="admin-logs-skeleton">
        <div v-for="i in 8" :key="i" class="tw-skeleton admin-log-skel-row" />
      </div>
      <div v-else class="admin-log-table">
        <div class="admin-log-row admin-log-row--head">
          <div>{{ t('admin.time') || '时间' }}</div>
          <div>{{ t('admin.level') || '级别' }}</div>
          <div>{{ t('admin.category') || '分类' }}</div>
          <div>{{ t('admin.message') || '消息' }}</div>
        </div>
        <div v-for="it in logs" :key="it.id" class="admin-log-row" :class="'lvl-' + it.level">
          <div class="admin-log-time">{{ (it.created_at || '').slice(0, 19).replace('T', ' ') }}</div>
          <div class="admin-log-level">{{ it.level }}</div>
          <div class="admin-log-cat">{{ it.category }}</div>
          <div class="admin-log-msg">
            <div class="admin-log-msg-main">{{ it.message }}</div>
            <div v-if="it.method || it.path || it.status_code" class="admin-log-msg-sub">
              <span v-if="it.method">{{ it.method }}</span>
              <span v-if="it.path">{{ it.path }}</span>
              <span v-if="it.status_code">· {{ it.status_code }}</span>
              <span v-if="it.user_id">· uid={{ it.user_id }}</span>
            </div>
          </div>
        </div>
        <p v-if="!logs.length && !logsLoading" class="empty">{{ t('admin.noLogs') || '暂无日志' }}</p>
      </div>
      <div class="admin-pagination">
        <Button size="sm" variant="secondary" type="button" :disabled="skip <= 0 || logsLoading" @click="skip = Math.max(0, skip - pageSize); reloadLogs()">{{ t('admin.prev') || '上一页' }}</Button>
        <span class="admin-page-meta">{{ skip + 1 }}-{{ skip + logs.length }} / {{ total }}</span>
        <Button size="sm" variant="secondary" type="button" :disabled="skip + pageSize >= total || logsLoading" @click="skip += pageSize; reloadLogs()">{{ t('admin.next') || '下一页' }}</Button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: var(--space-6); }
</style>
