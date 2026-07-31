<script setup lang="ts">
import { inject, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../../components/ui/button'
import { TableCell, TableHead, TableRow } from '../../components/ui/table'
import AdminDataTable from '../../components/admin/AdminDataTable.vue'
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue'
import DisputeResolveDialog from '../../components/admin/DisputeResolveDialog.vue'
import * as api from '../../api'
import { safeT } from '../../i18n'
import { ADMIN_CONTEXT_KEY } from '../../composables/admin/adminContext'
import { useAdminPaginatedList } from '../../composables/admin/useAdminPaginatedList'

type DisputePrecheck = {
  summary?: string
  recommendation_zh?: string
  confidence?: number
  source?: string
}

type DisputeItem = {
  id: number
  title: string
  updated_at?: string
  dispute_reason?: string
  dispute_evidence?: { summary?: string; links?: string[] }
  dispute_ai_precheck?: DisputePrecheck
  current_index: number
  milestones_total: number
}

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const ctx = inject(ADMIN_CONTEXT_KEY)

const resolveLoading = ref<number | null>(null)
const dialogOpen = ref(false)
const dialogTaskId = ref<number | null>(null)
const dialogTaskTitle = ref('')
const dialogResolution = ref<'resume' | 'force_confirm' | null>(null)

const { loading, items: disputes, pageMeta, reload, prevPage, nextPage } = useAdminPaginatedList<DisputeItem>(
  async ({ skip, limit }) => {
    const res = await api.getAdminDisputedTasks({ skip, limit })
    return { items: res.data.items || [], total: res.data.total || 0 }
  },
)

function openResolve(taskId: number, title: string, type: 'resume' | 'force_confirm') {
  dialogTaskId.value = taskId
  dialogTaskTitle.value = title
  dialogResolution.value = type
  dialogOpen.value = true
}

async function onConfirm(payload: { taskId: number; resolutionType: 'resume' | 'force_confirm'; note: string }) {
  resolveLoading.value = payload.taskId
  try {
    await api.adminResolveEscrowDispute(payload.taskId, {
      resolution_type: payload.resolutionType,
      note: payload.note,
    })
    dialogOpen.value = false
    await reload()
    await ctx?.refreshOverview()
  } finally {
    resolveLoading.value = null
  }
}

function precheckConfidence(p: DisputePrecheck | undefined): string {
  if (p?.confidence == null) return ''
  return `${Math.round(Number(p.confidence) * 100)}%`
}

onMounted(() => reload(true))
</script>

<template>
  <div class="admin-page">
    <AdminPageHeader
      :title="t('admin.nav.disputes') || '争议处理'"
      :description="t('admin.disputesTitle') || '争议任务快速处理'"
    />

    <AdminDataTable
      :loading="loading"
      :is-empty="disputes.length === 0"
      :empty-message="t('admin.noDisputes') || '暂无争议任务'"
      :page-from="pageMeta.from"
      :page-to="pageMeta.to"
      :page-total="pageMeta.total"
      :page-has-prev="pageMeta.hasPrev"
      :page-has-next="pageMeta.hasNext"
      :show-refresh="true"
      @refresh="reload()"
      @prev="prevPage"
      @next="nextPage"
    >
      <template #head>
        <TableRow>
          <TableHead>{{ t('admin.disputeColTask') || '任务' }}</TableHead>
          <TableHead>{{ t('admin.disputeColProgress') || '进度' }}</TableHead>
          <TableHead>{{ t('admin.disputeColReason') || '争议原因' }}</TableHead>
          <TableHead>{{ t('admin.disputeColPrecheck') || 'AI 预检' }}</TableHead>
          <TableHead class="text-right">{{ t('admin.disputeColActions') || '操作' }}</TableHead>
        </TableRow>
      </template>
      <TableRow v-for="it in disputes" :key="it.id">
        <TableCell>
          <RouterLink :to="`/tasks?taskId=${it.id}`" class="admin-settlement-link font-medium">
            #{{ it.id }} {{ it.title }}
          </RouterLink>
          <div class="admin-log-time">{{ (it.updated_at || '').slice(0, 19).replace('T', ' ') }}</div>
        </TableCell>
        <TableCell class="font-mono text-sm">
          {{ Math.min(it.current_index + 1, Math.max(it.milestones_total, 1)) }} / {{ Math.max(it.milestones_total, 1) }}
        </TableCell>
        <TableCell class="admin-dispute-reason">
          <p class="admin-dispute-reason__text">{{ it.dispute_reason || '-' }}</p>
          <p v-if="it.dispute_evidence?.summary" class="admin-log-time">{{ it.dispute_evidence.summary }}</p>
          <ul v-if="it.dispute_evidence?.links?.length" class="admin-dispute-links">
            <li v-for="(link, li) in it.dispute_evidence.links.slice(0, 3)" :key="li">
              <a :href="link" target="_blank" rel="noopener" class="admin-settlement-link">{{ link }}</a>
            </li>
          </ul>
        </TableCell>
        <TableCell class="admin-dispute-precheck">
          <template v-if="it.dispute_ai_precheck">
            <p class="admin-dispute-precheck__badge">
              {{ t('admin.disputePrecheckLabel') || '预检' }}
              <span v-if="precheckConfidence(it.dispute_ai_precheck)"> · {{ precheckConfidence(it.dispute_ai_precheck) }}</span>
              <span v-if="it.dispute_ai_precheck.source" class="admin-log-time"> ({{ it.dispute_ai_precheck.source }})</span>
            </p>
            <p class="admin-dispute-precheck__summary">{{ it.dispute_ai_precheck.summary }}</p>
            <p v-if="it.dispute_ai_precheck.recommendation_zh" class="hint">{{ it.dispute_ai_precheck.recommendation_zh }}</p>
          </template>
          <span v-else class="hint">—</span>
        </TableCell>
        <TableCell class="text-right">
          <div class="admin-dispute-actions justify-end">
            <Button size="sm" type="button" variant="secondary" :disabled="resolveLoading === it.id" @click="openResolve(it.id, it.title, 'resume')">
              {{ t('admin.resumeExec') || '恢复执行' }}
            </Button>
            <Button size="sm" type="button" :disabled="resolveLoading === it.id" @click="openResolve(it.id, it.title, 'force_confirm')">
              {{ t('admin.forceConfirm') || '强制验收' }}
            </Button>
          </div>
        </TableCell>
      </TableRow>
    </AdminDataTable>

    <DisputeResolveDialog
      v-model:open="dialogOpen"
      :task-id="dialogTaskId"
      :task-title="dialogTaskTitle"
      :resolution-type="dialogResolution"
      :loading="resolveLoading != null"
      @confirm="onConfirm"
    />
  </div>
</template>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: var(--space-6); }
.admin-dispute-reason__text { margin: 0; line-height: 1.45; max-width: 22rem; }
.admin-dispute-links { margin: var(--space-1) 0 0; padding-left: 1rem; font-size: var(--font-caption); }
.admin-dispute-precheck { max-width: 20rem; }
.admin-dispute-precheck__badge { margin: 0 0 var(--space-1); font-size: var(--font-caption); font-weight: 600; color: var(--primary-color); }
.admin-dispute-precheck__summary { margin: 0; font-size: var(--font-caption); line-height: 1.45; color: var(--text-secondary); white-space: pre-wrap; }
</style>
