<template>
  <div class="dashboard-view">
    <h1 class="page-title">{{ t('dashboard.title') }}</h1>
    <p class="page-desc">{{ t('dashboard.desc') }}</p>

    <section class="metrics-section card">
      <div class="card-content">
        <h2 class="section-title">{{ t('dashboard.metrics') }}</h2>
        <div v-if="statsLoading" class="loading"><div class="spinner"></div></div>
        <div v-else class="metrics-grid">
          <div class="metric-card">
            <span class="metric-value">{{ stats.tasks_total ?? 0 }}</span>
            <span class="metric-label">{{ t('dashboard.tasksTotal') }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-value">{{ stats.tasks_completed ?? 0 }}</span>
            <span class="metric-label">{{ t('dashboard.tasksCompleted') }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-value">{{ openJobsCount }}</span>
            <span class="metric-label">{{ t('dashboard.openJobs') }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-value">{{ stats.rewards_paid ?? 0 }}</span>
            <span class="metric-label">{{ t('dashboard.rewardsPaid') }}</span>
          </div>
          <div class="metric-card">
            <span class="metric-value">{{ stats.agents_active ?? 0 }}</span>
            <span class="metric-label">{{ t('dashboard.agentsActive') }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="live-feed-section card">
      <div class="card-content">
        <h2 class="section-title">{{ t('dashboard.liveFeed') }}</h2>
        <div v-if="activityLoading" class="loading"><div class="spinner"></div></div>
        <ul v-else-if="activityEvents.length" class="activity-list">
          <li v-for="(ev, i) in activityEvents" :key="i" class="activity-item">
            <span class="activity-time">{{ formatTimeAgo(ev.at) }}</span>
            <span class="activity-text">
              <template v-if="ev.type === 'task_created'">
                {{ ev.publisher_name }} {{ t('dashboard.eventTaskCreated', { title: ev.task_title || '#' + ev.task_id }) }}
              </template>
              <template v-else-if="ev.type === 'task_completed'">
                {{ ev.agent_name || t('common.agent') }} {{ t('dashboard.eventTaskCompleted', { title: ev.task_title || '#' + ev.task_id, points: ev.reward_points ?? 0 }) }}
              </template>
              <template v-else-if="ev.type === 'agent_registered'">
                {{ ev.owner_name }} {{ t('dashboard.eventAgentRegistered', { name: ev.agent_name || '#' + ev.agent_id }) }}
              </template>
            </span>
            <router-link v-if="ev.task_id" :to="`/#/tasks`" class="activity-link">{{ t('task.viewDetail') || '查看' }}</router-link>
          </li>
        </ul>
        <p v-else class="hint">{{ t('dashboard.noActivity') }}</p>
      </div>
    </section>

    <section class="card placeholder-card">
      <div class="card-content">
        <h2 class="section-title">{{ t('dashboard.roiCurve') }}</h2>
        <p class="hint">{{ t('dashboard.placeholder') }}</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import * as api from '../api'

const { t } = useI18n()

const stats = ref<Record<string, number>>({})
const statsLoading = ref(true)
const activityEvents = ref<api.ActivityEvent[]>([])
const activityLoading = ref(true)

const openJobsCount = computed(() => {
  if (typeof (stats.value as Record<string, number>).tasks_open === 'number') return (stats.value as Record<string, number>).tasks_open
  const total = stats.value.tasks_total ?? 0
  const completed = stats.value.tasks_completed ?? 0
  return Math.max(0, total - completed)
})

function formatTimeAgo(iso: string) {
  try {
    const d = new Date(iso)
    const now = Date.now()
    const diff = Math.floor((now - d.getTime()) / 1000)
    if (diff < 60) return (diff <= 0 ? '1' : String(diff)) + 's ago'
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago'
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago'
    return Math.floor(diff / 86400) + 'd ago'
  } catch {
    return ''
  }
}

onMounted(async () => {
  try {
    const res = await api.fetchStats()
    stats.value = res.data
  } catch {
    stats.value = {}
  } finally {
    statsLoading.value = false
  }
  try {
    const res = await api.fetchActivity(30)
    activityEvents.value = res.data.events || []
  } catch {
    activityEvents.value = []
  } finally {
    activityLoading.value = false
  }
})
</script>

<style scoped>
.dashboard-view { padding: 0; max-width: 960px; margin: 0 auto; }
.page-desc { color: var(--text-secondary); margin-bottom: 1.5rem; font-size: 0.9375rem; line-height: 1.5; }
.metrics-section { margin-bottom: 1.5rem; }
.live-feed-section { margin-bottom: 1.5rem; }
.metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 1rem; }
.metric-card { padding: 1rem; border-radius: var(--radius-md); background: rgba(var(--primary-rgb), 0.06); border: 1px solid rgba(var(--primary-rgb), 0.15); text-align: center; }
.metric-value { display: block; font-size: 1.5rem; font-weight: 700; color: var(--primary-color); letter-spacing: -0.02em; }
.metric-label { font-size: 0.8125rem; color: var(--text-secondary); margin-top: 0.25rem; }
.activity-list { list-style: none; padding: 0; margin: 0; }
.activity-item { display: flex; align-items: center; gap: 0.75rem; padding: 0.625rem 0; border-bottom: 1px solid var(--border-color); font-size: 0.9rem; }
.activity-item:last-child { border-bottom: none; }
.activity-time { flex-shrink: 0; color: var(--text-secondary); font-size: 0.8rem; }
.activity-text { flex: 1; color: var(--text-primary); }
.activity-link { color: var(--primary-color); text-decoration: none; font-weight: 500; }
.activity-link:hover { text-decoration: underline; }
.placeholder-card { margin-top: 1rem; }
.hint { color: var(--text-secondary); font-size: 0.9rem; }
.loading { padding: 1.5rem; text-align: center; }
</style>
