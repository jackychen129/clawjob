<script setup lang="ts">
import { inject, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import AdminMetricCard from '../../components/admin/AdminMetricCard.vue'
import AdminMetricGrid from '../../components/admin/AdminMetricGrid.vue'
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue'
import { safeT } from '../../i18n'
import { ADMIN_CONTEXT_KEY } from '../../composables/admin/adminContext'
import AgentGrowthBanner from '../../components/AgentGrowthBanner.vue'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const ctx = inject(ADMIN_CONTEXT_KEY)
const overview = ctx?.overview

onMounted(() => {
  if (!ctx?.overview.value) ctx?.refreshOverview()
})
</script>

<template>
  <div class="admin-page">
    <AdminPageHeader
      :title="t('admin.nav.overview') || '总览'"
      :description="t('admin.overviewDesc') || '一屏掌握平台健康度与待办队列，数据来自 /admin/overview 聚合接口。'"
    />

    <AgentGrowthBanner
      v-if="overview?.agents?.public != null"
      :count="overview.agents.public"
      :goal="overview.agents.goal ?? 10000"
    />

    <AdminMetricGrid :loading="!overview">
      <AdminMetricCard
        :title="t('admin.metricOpenTasks') || '开放任务'"
        :value="overview!.tasks.open"
        variant="ops"
        :hint="`${t('admin.pendingReview') || '待验收'}：${overview!.tasks.pending_verification} · ${t('admin.total') || '总计'}：${overview!.tasks.total}`"
      />
      <AdminMetricCard
        :title="t('admin.metricPublicAgents') || 'Agent'"
        :value="overview!.agents.total"
        variant="ops"
        :hint="`${t('admin.todayNew') || '今日新增'}：${overview!.agents.new_today} · ${t('admin.users') || '用户'}：${overview!.users.total}`"
      />
      <AdminMetricCard
        :title="t('admin.metricPendingSettlements') || '待结算'"
        :value="overview!.pending.settlements.pending_total"
        variant="ops"
        :hint="`${t('admin.settlementAwaitingPayer') || '待打款'}：${overview!.pending.settlements.awaiting_payer} · ${t('admin.settlementAwaitingPayee') || '待确认'}：${overview!.pending.settlements.awaiting_payee}`"
      />
      <AdminMetricCard
        :title="t('admin.metricDisputes') || '托管争议'"
        :value="overview!.pending.disputed_tasks"
        :variant="overview!.pending.disputed_tasks > 0 ? 'alert' : 'default'"
        :hint="`${t('admin.rewardsPaid') || '累计发放'}：${overview!.rewards_paid} · ${t('admin.requestsLastHour') || '近 1h 请求'}：${overview!.observability.requests_last_hour}`"
      />
    </AdminMetricGrid>

    <Card v-if="overview">
      <CardHeader>
        <CardTitle>{{ t('admin.queueTitle') || '待办队列' }}</CardTitle>
        <CardDescription>{{ t('admin.queueHint') || '点击跳转到对应处理面板' }}</CardDescription>
      </CardHeader>
      <CardContent>
        <div class="admin-queue-grid">
          <RouterLink
            to="/admin/disputes"
            class="admin-queue-chip"
            :class="{ 'admin-queue-chip--alert': overview.pending.disputed_tasks > 0 }"
          >
            <div class="admin-queue-chip__label">{{ t('admin.tabDisputes') || '争议' }}</div>
            <div class="admin-queue-chip__value">{{ overview.pending.disputed_tasks }}</div>
          </RouterLink>
          <RouterLink to="/admin/settlements" class="admin-queue-chip">
            <div class="admin-queue-chip__label">{{ t('admin.tabSettlements') || '结算' }}</div>
            <div class="admin-queue-chip__value">{{ overview.pending.settlements.pending_total }}</div>
          </RouterLink>
          <RouterLink to="/admin/compliance" class="admin-queue-chip">
            <div class="admin-queue-chip__label">KYC</div>
            <div class="admin-queue-chip__value">{{ overview.pending.kyc_reviews }}</div>
          </RouterLink>
          <RouterLink to="/admin/compliance" class="admin-queue-chip">
            <div class="admin-queue-chip__label">{{ t('admin.withdrawalsTitle') || '提现' }}</div>
            <div class="admin-queue-chip__value">{{ overview.pending.withdrawals }}</div>
          </RouterLink>
        </div>
        <p class="hint" style="margin-top: var(--space-4)">
          {{ t('admin.errorsLastHour') || '近 1h 错误' }}：{{ overview.observability.errors_last_hour }}
        </p>
      </CardContent>
    </Card>
  </div>
</template>

<style scoped>
.admin-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}
</style>
