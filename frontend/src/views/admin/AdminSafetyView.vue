<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { TableCell, TableHead, TableRow } from '../../components/ui/table'
import AdminDataTable from '../../components/admin/AdminDataTable.vue'
import AdminMetricCard from '../../components/admin/AdminMetricCard.vue'
import AdminMetricGrid from '../../components/admin/AdminMetricGrid.vue'
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue'
import * as api from '../../api'
import { safeT } from '../../i18n'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

const safetyDays = ref(30)
const safetyStatsLoading = ref(false)
const safetyStats = ref<Awaited<ReturnType<typeof api.fetchSafetyStats>>['data'] | null>(null)
const safetyEventsLoading = ref(false)
const safetyEvents = ref<api.SafetyEventItem[]>([])
const safetyEventsTotal = ref(0)
const safetyEventsSkip = ref(0)
const safetyEventsPageSize = 30
const safetyActionFilter = ref('')

function reloadSafety() {
  safetyStatsLoading.value = true
  api.fetchSafetyStats(safetyDays.value)
    .then((res) => { safetyStats.value = res.data })
    .catch(() => { safetyStats.value = null })
    .finally(() => { safetyStatsLoading.value = false })
}

function reloadSafetyEvents(reset = false) {
  if (reset) safetyEventsSkip.value = 0
  safetyEventsLoading.value = true
  api.listSafetyEvents({ offset: safetyEventsSkip.value, limit: safetyEventsPageSize, action: safetyActionFilter.value || undefined })
    .then((res) => { safetyEvents.value = res.data.items || []; safetyEventsTotal.value = res.data.total || 0 })
    .catch(() => { safetyEvents.value = []; safetyEventsTotal.value = 0 })
    .finally(() => { safetyEventsLoading.value = false })
}

onMounted(() => {
  reloadSafety()
  reloadSafetyEvents(true)
})
</script>

<template>
  <div class="admin-page">
    <AdminPageHeader
      :title="t('admin.nav.safety') || '内容安全'"
      :description="t('admin.safetyStatsTitle') || '内容安全统计与事件审计'"
    />

    <Card>
      <CardHeader>
        <div class="admin-panel__head">
          <CardTitle>{{ t('admin.safetyStatsTitle') || '内容安全统计' }}</CardTitle>
          <div class="admin-logs-filters">
            <select v-model.number="safetyDays" class="input select-input admin-filter" @change="reloadSafety">
              <option :value="7">7d</option>
              <option :value="30">30d</option>
              <option :value="90">90d</option>
            </select>
            <Button size="sm" variant="secondary" type="button" :disabled="safetyStatsLoading" @click="reloadSafety">{{ t('common.retry') || '刷新' }}</Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <AdminMetricGrid :loading="safetyStatsLoading && !safetyStats" :skeleton-count="1">
          <AdminMetricCard
            v-if="safetyStats"
            :title="t('admin.safetyTotal') || '事件总数'"
            :value="safetyStats.total"
            variant="ops"
          />
        </AdminMetricGrid>
        <div v-if="safetyStats" class="admin-safety-breakdown" style="margin-top: var(--space-4)">
          <div v-for="(cnt, act) in safetyStats.by_action" :key="'act-'+act" class="admin-safety-chip"><span class="mono">{{ act }}</span> · {{ cnt }}</div>
          <div v-for="(cnt, src) in safetyStats.by_source" :key="'src-'+src" class="admin-safety-chip admin-safety-chip--muted">{{ src }} · {{ cnt }}</div>
        </div>
      </CardContent>
    </Card>

    <AdminDataTable
      :title="t('admin.safetyEventsTitle') || '安全事件'"
      :loading="safetyEventsLoading"
      :is-empty="safetyEvents.length === 0"
      :empty-message="t('admin.safetyEventsEmpty') || '暂无安全事件'"
      :page-from="safetyEventsTotal ? safetyEventsSkip + 1 : 0"
      :page-to="Math.min(safetyEventsSkip + safetyEventsPageSize, safetyEventsTotal)"
      :page-total="safetyEventsTotal"
      :page-has-prev="safetyEventsSkip > 0"
      :page-has-next="safetyEventsSkip + safetyEventsPageSize < safetyEventsTotal"
      @refresh="reloadSafetyEvents(true)"
      @prev="safetyEventsSkip = Math.max(0, safetyEventsSkip - safetyEventsPageSize); reloadSafetyEvents()"
      @next="safetyEventsSkip += safetyEventsPageSize; reloadSafetyEvents()"
    >
      <template #actions>
        <select v-model="safetyActionFilter" class="input select-input admin-filter" @change="reloadSafetyEvents(true)">
          <option value="">{{ t('admin.allCategories') || '全部' }}</option>
          <option value="block">block</option>
          <option value="redact">redact</option>
        </select>
      </template>
      <template #head>
        <TableRow>
          <TableHead>{{ t('admin.safetyColTime') || '时间' }}</TableHead>
          <TableHead>{{ t('admin.safetyColAction') || '动作' }}</TableHead>
          <TableHead>{{ t('admin.safetyColSource') || '来源' }}</TableHead>
          <TableHead>{{ t('admin.safetyColSnippet') || '片段' }}</TableHead>
        </TableRow>
      </template>
      <TableRow v-for="ev in safetyEvents" :key="ev.id">
        <TableCell class="admin-log-time">{{ (ev.created_at || '').slice(0, 19).replace('T', ' ') }}</TableCell>
        <TableCell class="font-mono text-sm">{{ ev.action }}</TableCell>
        <TableCell class="font-mono text-sm">{{ ev.source }}</TableCell>
        <TableCell>
          <div>{{ ev.snippet || '-' }}</div>
          <div v-if="ev.reasons?.length" class="admin-log-msg-sub font-mono">{{ ev.reasons.join(', ') }}</div>
        </TableCell>
      </TableRow>
    </AdminDataTable>
  </div>
</template>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: var(--space-6); }
</style>
