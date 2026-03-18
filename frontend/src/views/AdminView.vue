<template>
  <section class="admin-wrap">
    <h1 class="page-title">{{ t('admin.title') || '管理后台' }}</h1>
    <div class="admin-head-actions">
      <Button type="button" variant="secondary" :disabled="loading" @click="reloadAll">
        {{ t('common.retry') || '刷新' }}
      </Button>
    </div>

    <div v-if="denied" class="card admin-card">
      <p class="error-msg">{{ t('admin.denied') || '无权限访问（需要管理员账号）' }}</p>
    </div>

    <template v-else>
      <div v-if="loading && !metrics" class="admin-metrics admin-metrics--skeleton">
        <div v-for="i in 4" :key="i" class="card tw-skeleton-card admin-metric-card">
          <div class="tw-skeleton admin-skel-line admin-skel-line--title"></div>
          <div class="tw-skeleton admin-skel-line admin-skel-line--value"></div>
          <div class="tw-skeleton admin-skel-line admin-skel-line--hint"></div>
        </div>
      </div>

      <div v-else class="admin-metrics">
        <div class="card admin-metric-card">
          <div class="admin-metric-title">{{ t('admin.tasks') || '任务' }}</div>
          <div class="admin-metric-value">{{ metrics?.tasks.total ?? 0 }}</div>
          <div class="admin-metric-hint">
            {{ t('admin.todayNew') || '今日新增' }}：{{ metrics?.tasks.today ?? 0 }} ·
            {{ t('admin.open') || '进行中' }}：{{ metrics?.tasks.open ?? 0 }} ·
            {{ t('admin.pendingReview') || '待验收' }}：{{ metrics?.tasks.pending_verification ?? 0 }}
          </div>
        </div>
        <div class="card admin-metric-card">
          <div class="admin-metric-title">{{ t('admin.users') || '用户' }}</div>
          <div class="admin-metric-value">{{ metrics?.users.total ?? 0 }}</div>
          <div class="admin-metric-hint">
            {{ t('admin.todayNew') || '今日新增' }}：{{ metrics?.users.new_today ?? 0 }} ·
            {{ t('admin.active') || '活跃' }}：{{ metrics?.users.active ?? 0 }}
          </div>
        </div>
        <div class="card admin-metric-card">
          <div class="admin-metric-title">{{ t('admin.agents') || 'Agent' }}</div>
          <div class="admin-metric-value">{{ metrics?.agents.total ?? 0 }}</div>
          <div class="admin-metric-hint">
            {{ t('admin.todayNew') || '今日新增' }}：{{ metrics?.agents.new_today ?? 0 }} ·
            {{ t('admin.active') || '活跃' }}：{{ metrics?.agents.active ?? 0 }}
          </div>
        </div>
        <div class="card admin-metric-card">
          <div class="admin-metric-title">{{ t('admin.rewardsPaid') || '累计发放' }}</div>
          <div class="admin-metric-value">{{ metrics?.rewards_paid ?? 0 }}</div>
          <div class="admin-metric-hint">{{ t('admin.generatedAt') || '更新时间' }}：{{ (metrics?.generated_at || '').slice(0, 19).replace('T', ' ') }}</div>
        </div>
      </div>

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
          <div v-for="i in 8" :key="i" class="tw-skeleton admin-log-skel-row"></div>
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
          <Button size="sm" variant="secondary" type="button" :disabled="skip <= 0 || logsLoading" @click="prevPage">
            {{ t('admin.prev') || '上一页' }}
          </Button>
          <span class="admin-page-meta">
            {{ skip + 1 }}-{{ skip + logs.length }} / {{ total }}
          </span>
          <Button size="sm" variant="secondary" type="button" :disabled="skip + pageSize >= total || logsLoading" @click="nextPage">
            {{ t('admin.next') || '下一页' }}
          </Button>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import { safeT } from '../i18n'
import * as api from '../api'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

const loading = ref(false)
const denied = ref(false)
const metrics = ref<Awaited<ReturnType<typeof api.getAdminMetrics>>['data'] | null>(null)

const logsLoading = ref(false)
const logs = ref<api.AdminLogItem[]>([])
const total = ref(0)
const skip = ref(0)
const pageSize = 50
const level = ref('')
const category = ref('')

function reloadAll() {
  denied.value = false
  loading.value = true
  api.getAdminMe().then(() => {
    return api.getAdminMetrics().then((res) => { metrics.value = res.data })
  }).catch(() => {
    denied.value = true
  }).finally(() => {
    loading.value = false
  })
  reloadLogs(true)
}

function reloadLogs(reset = false) {
  if (reset) skip.value = 0
  logsLoading.value = true
  api.getAdminLogs({ skip: skip.value, limit: pageSize, level: level.value || undefined, category: category.value || undefined })
    .then((res) => {
      logs.value = res.data.items || []
      total.value = res.data.total || 0
    })
    .catch(() => { logs.value = []; total.value = 0 })
    .finally(() => { logsLoading.value = false })
}

function nextPage() {
  if (skip.value + pageSize >= total.value) return
  skip.value += pageSize
  reloadLogs(false)
}
function prevPage() {
  if (skip.value <= 0) return
  skip.value = Math.max(0, skip.value - pageSize)
  reloadLogs(false)
}

onMounted(() => {
  reloadAll()
})
</script>

<style scoped>
.admin-wrap { display: flex; flex-direction: column; gap: var(--space-6); }
.admin-head-actions { display: flex; gap: var(--space-2); margin-bottom: var(--space-2); }
.admin-metrics { display: grid; grid-template-columns: 1fr; gap: var(--space-4); }
@media (min-width: 768px) { .admin-metrics { grid-template-columns: repeat(4, 1fr); } }
.admin-metric-card {
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  border: var(--border-hairline);
  background: var(--card-background);
  box-shadow: var(--shadow-card);
  transition: box-shadow var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple);
}
.admin-metric-card:hover { box-shadow: var(--shadow-card-hover); border-color: rgba(255,255,255,0.08); }
.admin-metric-title { color: var(--text-secondary); font-size: var(--font-caption); font-weight: 600; letter-spacing: var(--tracking-normal); }
.admin-metric-value { font-size: 1.75rem; font-weight: 700; margin-top: var(--space-2); letter-spacing: var(--tracking-tight); color: var(--text-primary); }
.admin-metric-hint { margin-top: var(--space-2); font-size: var(--font-caption); color: var(--text-secondary); line-height: 1.4; }

.admin-metrics--skeleton .admin-metric-card { display: flex; flex-direction: column; gap: 0.6rem; }
.admin-skel-line { height: 0.9rem; }
.admin-skel-line--title { width: 40%; }
.admin-skel-line--value { width: 65%; height: 1.6rem; }
.admin-skel-line--hint { width: 85%; }

.admin-card {
  padding: var(--space-6);
  border-radius: var(--radius-xl);
  border: var(--border-hairline);
  background: var(--card-background);
  box-shadow: var(--shadow-card);
}
.admin-logs { margin-top: 0; }
.admin-logs-head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); flex-wrap: wrap; margin-bottom: var(--space-4); }
.admin-logs-title { margin: 0; font-size: var(--font-section-title); font-weight: 650; letter-spacing: var(--tracking-normal); color: var(--text-primary); }
.admin-logs-filters { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.admin-filter { min-width: 10rem; }

.admin-log-table { width: 100%; }
.admin-log-row { display: grid; grid-template-columns: 11rem 5rem 7rem 1fr; gap: var(--space-3); padding: var(--space-3) 0; border-bottom: var(--border-hairline); }
.admin-log-row--head { color: var(--text-secondary); font-size: var(--font-caption); font-weight: 600; padding-top: 0; }
.admin-log-time { color: var(--text-secondary); font-size: var(--font-caption); }
.admin-log-level, .admin-log-cat { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: var(--font-caption); }
.admin-log-msg-main { font-size: var(--font-body); }
.admin-log-msg-sub { margin-top: var(--space-1); color: var(--text-secondary); font-size: var(--font-caption); display: flex; gap: var(--space-2); flex-wrap: wrap; }
.admin-log-row.lvl-error .admin-log-level { color: var(--danger-color); }
.admin-log-row.lvl-warning .admin-log-level { color: var(--warning-color); }
.admin-log-row.lvl-info .admin-log-level { color: var(--primary-color); }

.admin-logs-skeleton { display: flex; flex-direction: column; gap: var(--space-2); }
.admin-log-skel-row { height: 1rem; border-radius: var(--radius-sm); }

.admin-pagination { display: flex; justify-content: flex-end; align-items: center; gap: var(--space-3); margin-top: var(--space-4); }
.admin-page-meta { color: var(--text-secondary); font-size: var(--font-caption); }

@media (max-width: 900px) {
  .admin-log-row { grid-template-columns: 9rem 4.5rem 6rem 1fr; }
}
@media (max-width: 640px) {
  .admin-log-row { grid-template-columns: 1fr; }
  .admin-log-row--head { display: none; }
}
</style>
