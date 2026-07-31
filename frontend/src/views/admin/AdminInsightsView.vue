<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { TableCell, TableHead, TableRow } from '../../components/ui/table'
import AdminMetricCard from '../../components/admin/AdminMetricCard.vue'
import AdminMetricGrid from '../../components/admin/AdminMetricGrid.vue'
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue'
import { Table } from '../../components/ui/table'
import * as api from '../../api'
import { safeT } from '../../i18n'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

const platformInsightsDays = ref(30)
const platformInsightsLoading = ref(false)
const platformInsights = ref<api.PlatformInsights | null>(null)

function reload() {
  platformInsightsLoading.value = true
  api.fetchPlatformInsights(platformInsightsDays.value)
    .then((res) => { platformInsights.value = res.data })
    .catch(() => { platformInsights.value = null })
    .finally(() => { platformInsightsLoading.value = false })
}

onMounted(reload)
</script>

<template>
  <div class="admin-page">
    <AdminPageHeader
      :title="t('admin.nav.insights') || '平台洞察'"
      :description="t('admin.platformInsightsTitle') || '平台洞察'"
    />

    <Card>
      <CardHeader>
        <div class="admin-panel__head">
          <CardTitle>{{ t('admin.platformInsightsTitle') || '平台洞察' }}</CardTitle>
          <div class="admin-logs-filters">
            <select v-model.number="platformInsightsDays" class="input select-input admin-filter" @change="reload">
              <option :value="7">7d</option>
              <option :value="30">30d</option>
              <option :value="90">90d</option>
            </select>
            <Button size="sm" variant="secondary" type="button" :disabled="platformInsightsLoading" @click="reload">{{ t('common.retry') || '刷新' }}</Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <AdminMetricGrid :loading="platformInsightsLoading && !platformInsights">
          <AdminMetricCard title="GMV" :value="platformInsights!.gmv" />
          <AdminMetricCard :title="t('admin.insightsRevenue') || '平台收入'" :value="platformInsights!.revenue" />
          <AdminMetricCard :title="t('admin.insightsPublished') || '发布'" :value="platformInsights!.funnel.published" variant="ops" />
          <AdminMetricCard :title="t('admin.insightsCompleted') || '完成'" :value="platformInsights!.funnel.completed" variant="ops" />
        </AdminMetricGrid>

        <div v-if="platformInsights" class="admin-insights-funnel">
          <div class="admin-insights-funnel-row">
            <span>{{ t('admin.insightsBidRate') || '出价率' }}</span>
            <span class="font-mono">{{ (platformInsights.funnel.bid_rate * 100).toFixed(1) }}%</span>
          </div>
          <div class="admin-insights-funnel-row">
            <span>{{ t('admin.insightsAssignRate') || '分配率' }}</span>
            <span class="font-mono">{{ (platformInsights.funnel.assign_rate * 100).toFixed(1) }}%</span>
          </div>
          <div class="admin-insights-funnel-row">
            <span>{{ t('admin.insightsCompletionRate') || '完成率' }}</span>
            <span class="font-mono">{{ (platformInsights.funnel.completion_rate * 100).toFixed(1) }}%</span>
          </div>
        </div>

        <div v-if="platformInsights?.daily?.length" class="admin-insights-daily">
          <h4 class="admin-cb-history__title">{{ t('admin.insightsDaily') || '日趋势（最近）' }}</h4>
          <Table>
            <thead>
              <TableRow>
                <TableHead>{{ t('admin.insightsColDate') || '日期' }}</TableHead>
                <TableHead>{{ t('admin.insightsPublished') || '发布' }}</TableHead>
                <TableHead>{{ t('admin.insightsCompleted') || '完成' }}</TableHead>
                <TableHead>GMV</TableHead>
              </TableRow>
            </thead>
            <tbody>
              <TableRow v-for="row in platformInsights.daily.slice(-14)" :key="row.date">
                <TableCell class="admin-log-time">{{ row.date }}</TableCell>
                <TableCell class="font-mono">{{ row.published }}</TableCell>
                <TableCell class="font-mono">{{ row.completed }}</TableCell>
                <TableCell class="font-mono">{{ row.gmv }}</TableCell>
              </TableRow>
            </tbody>
          </Table>
        </div>

        <p v-if="!platformInsights && !platformInsightsLoading" class="empty">{{ t('admin.platformInsightsEmpty') || '暂无洞察数据' }}</p>
      </CardContent>
    </Card>
  </div>
</template>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: var(--space-6); }
</style>
