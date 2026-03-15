<template>
  <div class="dashboard-view">
    <div class="dash-head">
      <div>
        <h1 class="page-title">{{ t('dashboard.title') }}</h1>
        <p class="page-desc">{{ t('dashboard.desc') }}</p>
      </div>
      <div class="dash-head-actions">
        <Button size="sm" variant="secondary" type="button" @click="reloadAll">{{ t('common.retry') || '刷新' }}</Button>
      </div>
    </div>

    <div class="dash-bento">
      <!-- Metrics / KPI -->
      <Card class="bento bento--kpi">
        <CardHeader class="pb-2">
          <div class="bento-head">
            <CardTitle class="section-title text-base">{{ t('dashboard.metrics') }}</CardTitle>
            <span class="bento-sub mono">{{ new Date().toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) }}</span>
          </div>
        </CardHeader>
        <CardContent class="pt-0">
          <div v-if="statsLoading" class="kpi-grid kpi-grid--skeleton">
            <div v-for="i in 5" :key="i" class="kpi">
              <span class="tw-skeleton tw-skeleton-value"></span>
              <span class="tw-skeleton tw-skeleton-label"></span>
            </div>
          </div>
          <div v-else class="kpi-grid">
            <div class="kpi">
              <span class="kpi-value mono">{{ stats.tasks_total ?? 0 }}</span>
              <span class="kpi-label">{{ t('dashboard.tasksTotal') }}</span>
            </div>
            <div class="kpi">
              <span class="kpi-value mono">{{ stats.tasks_completed ?? 0 }}</span>
              <span class="kpi-label">{{ t('dashboard.tasksCompleted') }}</span>
            </div>
            <div class="kpi">
              <span class="kpi-value mono">{{ openJobsCount }}</span>
              <span class="kpi-label">{{ t('dashboard.openJobs') }}</span>
            </div>
            <div class="kpi">
              <span class="kpi-value mono">{{ stats.rewards_paid ?? 0 }}</span>
              <span class="kpi-label">{{ t('dashboard.rewardsPaid') }}</span>
            </div>
            <div class="kpi">
              <span class="kpi-value mono">{{ stats.agents_active ?? 0 }}</span>
              <span class="kpi-label">{{ t('dashboard.agentsActive') }}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- ROI placeholder -->
      <section class="card bento bento--roi">
        <div class="card-content">
          <div class="bento-head">
            <h2 class="section-title">{{ t('dashboard.roiCurve') }}</h2>
            <span class="bento-sub">{{ t('dashboard.placeholder') }}</span>
          </div>
          <div class="roi-chart-placeholder" aria-hidden="true">
            <div class="roi-chart-axis">
              <span class="roi-axis-label">{{ t('dashboard.roiYLabel') || '收益' }}</span>
              <div class="roi-chart-bars">
                <div v-for="i in 7" :key="i" class="roi-bar" :style="{ height: (30 + Math.abs((i * 17) % 50)) + '%' }"></div>
              </div>
            </div>
            <div class="roi-chart-x"><span v-for="d in 7" :key="d">{{ d }}</span></div>
          </div>
        </div>
      </section>

      <!-- Live feed sidebar -->
      <aside class="card bento bento--feed">
        <div class="card-content">
          <div class="bento-head">
            <h2 class="section-title">{{ t('dashboard.liveFeed') }}</h2>
            <span class="bento-sub mono">{{ t('dashboard.live') || 'LIVE' }}</span>
          </div>

          <div v-if="activityLoading" class="activity-skeleton">
            <div v-for="i in 6" :key="i" class="activity-skeleton-row">
              <span class="tw-skeleton tw-skeleton-time"></span>
              <span class="tw-skeleton tw-skeleton-text"></span>
            </div>
          </div>

          <TransitionGroup v-else-if="activityEvents.length" name="feed" tag="ul" class="activity-list">
            <li v-for="ev in activityEvents" :key="ev.at + ':' + ev.type + ':' + (ev.task_id || ev.agent_id || '')" class="activity-item">
              <span class="activity-time mono">{{ formatTimeAgo(ev.at) }}</span>
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
          </TransitionGroup>
          <div v-else class="empty-feed">
            <svg class="empty-illustration" viewBox="0 0 240 140" fill="none" aria-hidden="true">
              <path d="M22 106c23-36 52-54 88-54s65 18 88 54" stroke="rgba(34,197,94,0.22)" stroke-width="2" stroke-linecap="round"/>
              <path d="M38 98c18-27 41-40 72-40s54 13 72 40" stroke="rgba(226,232,240,0.10)" stroke-width="2" stroke-linecap="round"/>
              <circle cx="120" cy="44" r="6" fill="rgba(34,197,94,0.40)"/>
              <circle cx="92" cy="54" r="3" fill="rgba(226,232,240,0.20)"/>
              <circle cx="152" cy="54" r="3" fill="rgba(226,232,240,0.20)"/>
            </svg>
            <p class="hint">{{ t('dashboard.noActivity') }}</p>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import * as api from '../api'

const { t } = useI18n()

const stats = ref<Record<string, number>>({})
const statsLoading = ref(true)
const activityEvents = ref<api.ActivityEvent[]>([])
const activityLoading = ref(true)
let pollTimer: ReturnType<typeof setInterval> | null = null

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
  await reloadAll()
  pollTimer = setInterval(async () => {
    try {
      const res = await api.fetchActivity(30)
      const incoming = res.data.events || []
      const existingKeys = new Set(activityEvents.value.map((e) => `${e.at}:${e.type}:${e.task_id || e.agent_id || ''}`))
      const fresh = incoming.filter((e) => !existingKeys.has(`${e.at}:${e.type}:${e.task_id || e.agent_id || ''}`))
      if (fresh.length) {
        activityEvents.value = [...fresh, ...activityEvents.value].slice(0, 40)
      }
    } catch {
      // ignore polling errors
    }
  }, 15000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
})

async function reloadAll() {
  statsLoading.value = true
  activityLoading.value = true
  try {
    let res = await api.fetchStats().catch(() => null)
    if (!res) {
      await new Promise((r) => setTimeout(r, 1000))
      res = await api.fetchStats().catch(() => null)
    }
    stats.value = res?.data ?? {}
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
}
</script>

<style scoped>
.dashboard-view { padding: 0; max-width: 1120px; margin: 0 auto; }
.dash-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
.dash-head-actions { display: flex; gap: 0.5rem; }
.page-desc { color: var(--text-secondary); margin-top: 0.4rem; margin-bottom: 0; font-size: 0.9rem; line-height: 1.7; }

.dash-bento { display: grid; grid-template-columns: 1fr; gap: 1rem; }
@media (min-width: 1024px) {
  .dash-bento { grid-template-columns: 1fr 320px; grid-auto-rows: minmax(120px, auto); gap: 1.25rem; }
  .bento--kpi { grid-column: 1 / 2; }
  .bento--roi { grid-column: 1 / 2; }
  .bento--feed { grid-column: 2 / 3; grid-row: 1 / span 2; position: sticky; top: 92px; align-self: start; }
}

.bento-head { display: flex; align-items: baseline; justify-content: space-between; gap: 0.75rem; margin-bottom: 0.75rem; }
.bento-sub { color: var(--text-secondary); font-size: 0.8rem; }

.kpi-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem; min-width: 0; }
@media (min-width: 640px) { .kpi-grid { grid-template-columns: repeat(5, 1fr); } }
.kpi { padding: 0.9rem 0.75rem; border-radius: var(--radius-md); border: 1px solid var(--border-muted); background: rgba(226, 232, 240, 0.04); box-shadow: var(--shadow-layer-1); text-align: left; min-width: 0; }
.kpi-value { display: block; font-size: 1.5rem; font-weight: 700; letter-spacing: -0.03em; color: var(--primary-color); }
.kpi-label { display: block; margin-top: 0.15rem; font-size: 0.78rem; color: var(--text-secondary); }
.kpi-grid--skeleton { pointer-events: none; }
.kpi-grid--skeleton .kpi { background: var(--card-background); }
.kpi-grid--skeleton .tw-skeleton-value { display: block; width: 3.2rem; height: 1.5rem; border-radius: 6px; }
.kpi-grid--skeleton .tw-skeleton-label { display: block; width: 4.4rem; height: 0.85rem; margin-top: 0.5rem; border-radius: 6px; }
.activity-list { list-style: none; padding: 0; margin: 0; }
.activity-item { display: grid; grid-template-columns: 4.25rem 1fr auto; gap: 0.75rem; padding: 0.65rem 0; border-bottom: 1px solid rgba(226, 232, 240, 0.06); font-size: 0.88rem; }
.activity-item:last-child { border-bottom: none; }
.activity-time { color: var(--text-secondary); font-size: 0.78rem; }
.activity-text { flex: 1; color: var(--text-primary); }
.activity-link { color: var(--primary-color); text-decoration: none; font-weight: 500; }
.activity-link:hover { text-decoration: underline; }
.activity-skeleton { padding: 0.25rem 0; }
.activity-skeleton-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.625rem 0; }
.activity-skeleton-row .tw-skeleton-time { width: 3.5rem; height: 0.8rem; border-radius: 4px; flex-shrink: 0; }
.activity-skeleton-row .tw-skeleton-text { flex: 1; max-width: 80%; height: 0.9rem; border-radius: 4px; }
.roi-chart-placeholder { min-height: 140px; padding: 0.5rem 0; margin-bottom: 0.75rem; }
.roi-chart-axis { display: flex; align-items: stretch; gap: 0.5rem; }
.roi-axis-label { font-size: 0.75rem; color: var(--text-secondary); writing-mode: vertical-rl; transform: rotate(-180deg); align-self: center; }
.roi-chart-bars { display: flex; align-items: flex-end; gap: 0.35rem; flex: 1; min-height: 100px; }
.roi-bar { width: 100%; min-height: 8px; border-radius: 4px; background: linear-gradient(180deg, rgba(var(--primary-rgb), 0.5), rgba(var(--primary-rgb), 0.15)); transition: height 0.3s ease; }
.roi-chart-x { display: flex; justify-content: space-around; padding-top: 0.35rem; font-size: 0.75rem; color: var(--text-secondary); }
.empty-feed { padding: 0.5rem 0 0.25rem; text-align: center; }
.empty-illustration { width: 100%; max-width: 240px; margin: 0.25rem auto 0.5rem; display: block; }
.hint { color: var(--text-secondary); font-size: 0.9rem; }
.loading { padding: 1.5rem; text-align: center; }

/* New event push-in animation */
.feed-enter-active, .feed-leave-active { transition: all 0.22s ease; }
.feed-enter-from { opacity: 0; transform: translateY(-10px); }
.feed-enter-to { opacity: 1; transform: translateY(0); }
.feed-leave-from { opacity: 1; }
.feed-leave-to { opacity: 0; transform: translateY(8px); }
</style>
