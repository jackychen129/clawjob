<template>
  <div class="dashboard-view">
    <header class="dash-head">
      <div>
        <h1 class="page-title">{{ t('dashboard.title') }}</h1>
        <p class="page-desc">{{ t('dashboard.desc') }}</p>
      </div>
      <div class="dash-head-actions">
        <Button size="sm" variant="secondary" type="button" @click="reloadAll">{{ t('common.retry') || '刷新' }}</Button>
      </div>
    </header>

    <div class="dash-bento">
      <!-- Hero Statistics / KPI -->
      <Card class="dash-card dash-hero bento bento--kpi">
        <CardHeader class="dash-hero-header">
          <div class="dash-bento-head">
            <CardTitle class="section-title text-base">{{ t('dashboard.metrics') }}</CardTitle>
            <span class="dash-bento-sub mono">{{ new Date().toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) }}</span>
          </div>
        </CardHeader>
        <CardContent class="dash-hero-content">
          <div v-if="statsLoading" class="dash-kpi-grid dash-kpi-grid--skeleton">
            <div v-for="i in 5" :key="i" class="dash-kpi">
              <span class="tw-skeleton tw-skeleton-value"></span>
              <span class="tw-skeleton tw-skeleton-label"></span>
            </div>
          </div>
          <div v-else class="dash-kpi-grid" role="list">
            <div v-for="(_, idx) in 5" :key="idx" class="dash-kpi" :style="{ '--dash-kpi-order': idx }" role="listitem">
              <span class="dash-kpi-value mono">{{ kpiValues[idx] }}</span>
              <span class="dash-kpi-label">{{ kpiLabels[idx] }}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- ROI placeholder -->
      <section class="dash-card dash-chart bento bento--roi">
        <div class="card-content">
          <div class="dash-bento-head">
            <h2 class="section-title">{{ t('dashboard.roiCurve') }}</h2>
            <span class="dash-bento-sub">{{ t('dashboard.roiLastDays', { n: roiSeries.length || 0 }) || ('近 ' + (roiSeries.length || 0) + ' 天') }}</span>
          </div>
          <div class="dash-roi-wrap">
            <svg class="roi-line" viewBox="0 0 640 180" preserveAspectRatio="none" aria-hidden="true">
              <polyline :points="roiPoints" fill="none" stroke="rgba(34,197,94,0.95)" stroke-width="3" stroke-linecap="round" />
            </svg>
            <div class="dash-roi-x"><span v-for="p in roiSeries.slice(-7)" :key="p.date">{{ p.date.slice(5) }}</span></div>
          </div>
        </div>
      </section>

      <section class="dash-card bento bento--tree">
        <div class="card-content">
          <div class="dash-bento-head">
            <h2 class="section-title">{{ t('dashboard.skillTreeTitle') || '技能进化树' }}</h2>
            <span class="dash-bento-sub">{{ t('dashboard.skillTreeTop', { n: skillTree.length }) || ('Top ' + skillTree.length) }}</span>
          </div>
          <div v-if="skillTree.length" class="skill-tree-grid">
            <div v-for="n in skillTree" :key="n.name" class="skill-tree-node">
              <div class="skill-tree-node__head">
                <strong>{{ n.name }}</strong>
                <span class="mono">Lv.{{ n.level }}</span>
              </div>
              <div class="skill-tree-node__bar"><span :style="{ width: (n.progress * 100).toFixed(1) + '%' }"></span></div>
              <div class="skill-tree-node__meta mono">{{ n.xp_current }}/{{ n.xp_next }} XP</div>
            </div>
          </div>
          <p v-else class="dash-feed-empty-hint">{{ t('dashboard.skillTreeEmpty') || '暂无技能数据（完成带技能标签的任务后自动累积）' }}</p>
        </div>
      </section>

      <!-- Live feed sidebar -->
      <aside class="dash-card dash-feed bento bento--feed">
        <div class="card-content dash-feed-content">
          <div class="dash-bento-head">
            <h2 class="section-title">{{ t('dashboard.liveFeed') }}</h2>
            <span class="dash-bento-sub mono">{{ t('dashboard.live') || 'LIVE' }}</span>
          </div>

          <div v-if="activityLoading" class="dash-feed-skeleton">
            <div v-for="i in 6" :key="i" class="dash-feed-skeleton-row">
              <span class="tw-skeleton tw-skeleton-time"></span>
              <span class="tw-skeleton tw-skeleton-text"></span>
            </div>
          </div>

          <TransitionGroup v-else-if="activityEvents.length" name="dash-feed" tag="ul" class="dash-feed-list">
            <li v-for="ev in activityEvents" :key="ev.at + ':' + ev.type + ':' + (ev.task_id || ev.agent_id || '')" class="dash-feed-item">
              <div class="dash-feed-item-inner">
                <span class="dash-feed-time mono">{{ formatTimeAgo(ev.at) }}</span>
                <p class="dash-feed-body">
                  <span class="dash-feed-who">{{ getEventWho(ev) }}</span> {{ getEventWhat(ev) }}
                </p>
                <router-link v-if="ev.task_id" :to="`/#/tasks`" class="dash-feed-link">{{ t('task.viewDetail') || '查看' }}</router-link>
              </div>
            </li>
          </TransitionGroup>
          <div v-else class="dash-feed-empty">
            <svg class="dash-feed-empty-illus" viewBox="0 0 240 140" fill="none" aria-hidden="true">
              <path d="M22 106c23-36 52-54 88-54s65 18 88 54" stroke="rgba(34,197,94,0.22)" stroke-width="2" stroke-linecap="round"/>
              <path d="M38 98c18-27 41-40 72-40s54 13 72 40" stroke="rgba(226,232,240,0.10)" stroke-width="2" stroke-linecap="round"/>
              <circle cx="120" cy="44" r="6" fill="rgba(34,197,94,0.40)"/>
              <circle cx="92" cy="54" r="3" fill="rgba(226,232,240,0.20)"/>
              <circle cx="152" cy="54" r="3" fill="rgba(226,232,240,0.20)"/>
            </svg>
            <p class="dash-feed-empty-hint">{{ t('dashboard.noActivity') }}</p>
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
const roiSeries = ref<Array<{ date: string; rewards: number; tasks: number }>>([])
const skillTree = ref<api.SkillNode[]>([])
let pollTimer: ReturnType<typeof setInterval> | null = null

const openJobsCount = computed(() => {
  if (typeof (stats.value as Record<string, number>).tasks_open === 'number') return (stats.value as Record<string, number>).tasks_open
  const total = stats.value.tasks_total ?? 0
  const completed = stats.value.tasks_completed ?? 0
  return Math.max(0, total - completed)
})

const kpiValues = computed(() => [
  stats.value.tasks_total ?? 0,
  stats.value.tasks_completed ?? 0,
  openJobsCount.value,
  stats.value.rewards_paid ?? 0,
  stats.value.agents_active ?? 0,
])
const kpiLabels = computed(() => [
  t('dashboard.tasksTotal'),
  t('dashboard.tasksCompleted'),
  t('dashboard.openJobs'),
  t('dashboard.rewardsPaid'),
  t('dashboard.agentsActive'),
])

const roiPoints = computed(() => {
  const arr = roiSeries.value
  if (!arr.length) return ''
  const max = Math.max(...arr.map((x) => Number(x.rewards || 0)), 1)
  return arr.map((p, i) => {
    const x = (i / Math.max(1, arr.length - 1)) * 640
    const y = 170 - (Number(p.rewards || 0) / max) * 150
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})

function getEventWho(ev: api.ActivityEvent): string {
  if (ev.type === 'task_created') return ev.publisher_name ?? ''
  if (ev.type === 'task_completed') return ev.agent_name ?? t('common.agent')
  if (ev.type === 'agent_registered') return ev.owner_name ?? ''
  return ''
}
function getEventWhat(ev: api.ActivityEvent): string {
  if (ev.type === 'task_created') return t('dashboard.eventTaskCreated', { title: ev.task_title || '#' + ev.task_id })
  if (ev.type === 'task_completed') return t('dashboard.eventTaskCompleted', { title: ev.task_title || '#' + ev.task_id, points: ev.reward_points ?? 0 })
  if (ev.type === 'agent_registered') return t('dashboard.eventAgentRegistered', { name: ev.agent_name || '#' + ev.agent_id })
  return ''
}

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
  try {
    const rs = await api.fetchRoiSeries(14)
    roiSeries.value = rs.data.series || []
  } catch {
    roiSeries.value = []
  }
  try {
    const st = await api.fetchMySkillTree()
    skillTree.value = (st.data.nodes || []).slice(0, 12)
  } catch {
    skillTree.value = []
  }
}
</script>

<style scoped>
/* NOTE: translated comment in English. */
.dashboard-view {
  padding: 0;
  max-width: 1120px;
  margin: 0 auto;
}
.dash-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-8);
}
.dash-head-actions { display: flex; gap: var(--space-2); }
.page-desc {
  color: var(--text-secondary);
  margin-top: var(--space-1);
  margin-bottom: 0;
  font-size: var(--font-body);
  line-height: 1.6;
  letter-spacing: 0.01em;
}

.dash-bento {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-8);
}
@media (min-width: 1024px) {
  .dash-bento {
    grid-template-columns: 1fr 340px;
    grid-auto-rows: minmax(120px, auto);
    gap: var(--space-8);
  }
  .bento--kpi { grid-column: 1 / 2; }
  .bento--roi { grid-column: 1 / 2; }
  .bento--feed {
    grid-column: 2 / 3;
    grid-row: 1 / span 2;
    position: sticky;
    top: 92px;
    align-self: start;
  }
}

.dash-bento-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.dash-bento-sub {
  color: var(--text-secondary);
  font-size: var(--font-caption);
}

/* NOTE: translated comment in English. */
.dash-card.dash-hero {
  border: none;
  background: transparent;
  box-shadow: none;
}
.dash-hero-header {
  padding-bottom: var(--space-2);
}
.dash-hero-content {
  padding-top: 0;
}

.dash-kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
  min-width: 0;
}
@media (min-width: 640px) {
  .dash-kpi-grid { grid-template-columns: repeat(5, 1fr); }
}
.dash-kpi {
  padding: var(--space-5) var(--space-4);
  border-radius: var(--radius-lg);
  border: none;
  background: rgba(255, 255, 255, 0.03);
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.06), 0 4px 12px rgba(0, 0, 0, 0.04);
  text-align: left;
  min-width: 0;
  animation: dash-kpi-enter 0.4s var(--ease-apple) both;
  animation-delay: calc(var(--dash-kpi-order, 0) * 0.04s);
}
.dash-kpi-value {
  display: block;
  font-size: 1.625rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  color: var(--primary-color);
  line-height: 1.2;
}
.dash-kpi-label {
  display: block;
  margin-top: var(--space-2);
  font-size: var(--font-caption);
  color: var(--text-secondary);
  letter-spacing: 0.02em;
  line-height: 1.4;
}
.dash-kpi-grid--skeleton { pointer-events: none; }
.dash-kpi-grid--skeleton .dash-kpi {
  background: var(--card-background);
  animation: none;
}
.dash-kpi-grid--skeleton .tw-skeleton-value {
  display: block;
  width: 3.2rem;
  height: 1.6rem;
  border-radius: var(--radius-sm);
}
.dash-kpi-grid--skeleton .tw-skeleton-label {
  display: block;
  width: 4.4rem;
  height: 0.875rem;
  margin-top: var(--space-2);
  border-radius: var(--radius-sm);
}

@keyframes dash-kpi-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* NOTE: translated comment in English. */
.dash-card.dash-chart {
  background-color: var(--card-background);
  border-radius: var(--radius-xl);
  border: var(--border-hairline);
  overflow: hidden;
}
.dash-roi-wrap {
  min-height: 160px;
  padding: var(--space-4) 0;
  margin-bottom: var(--space-2);
}
.roi-line { width: 100%; height: 180px; display: block; }
.skill-tree-grid { display: grid; grid-template-columns: 1fr; gap: var(--space-3); }
@media (min-width: 768px) { .skill-tree-grid { grid-template-columns: repeat(2, 1fr); } }
.skill-tree-node { border: var(--border-hairline); border-radius: var(--radius-md); padding: var(--space-3); background: rgba(255,255,255,0.02); }
.skill-tree-node__head { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.skill-tree-node__bar { height: 0.5rem; border-radius: 999px; background: rgba(148,163,184,0.25); overflow: hidden; }
.skill-tree-node__bar span { display: block; height: 100%; background: linear-gradient(90deg, #22c55e, #a855f7); }
.skill-tree-node__meta { margin-top: var(--space-1); color: var(--text-secondary); font-size: var(--font-caption); }
.dash-roi-chart {
  display: flex;
  align-items: stretch;
  gap: var(--space-2);
}
.dash-roi-y {
  font-size: 0.75rem;
  color: var(--text-secondary);
  writing-mode: vertical-rl;
  transform: rotate(-180deg);
  align-self: center;
  opacity: 0.85;
}
.dash-roi-bars {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  flex: 1;
  min-height: 100px;
}
.dash-roi-bar {
  width: 100%;
  min-height: 8px;
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(var(--primary-rgb), 0.45), rgba(var(--primary-rgb), 0.12));
  transition: height 0.35s var(--ease-apple);
}
.dash-roi-x {
  display: flex;
  justify-content: space-around;
  padding-top: var(--space-2);
  font-size: var(--font-caption);
  color: var(--text-secondary);
}

/* NOTE: translated comment in English. */
.dash-card.dash-feed {
  background-color: var(--card-background);
  border-radius: var(--radius-xl);
  border: var(--border-hairline);
  overflow: hidden;
}
.dash-feed-content {
  max-height: 72vh;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
}
.dash-feed-content::-webkit-scrollbar {
  width: 6px;
}
.dash-feed-content::-webkit-scrollbar-track {
  background: transparent;
}
.dash-feed-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-full);
}
.dash-feed-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.12);
}

.dash-feed-list {
  list-style: none;
  padding: 0;
  margin: 0;
  position: relative;
  padding-left: 1.25rem;
}
.dash-feed-list::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 0.5rem;
  bottom: 0.5rem;
  width: 1px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-full);
}
.dash-feed-item {
  position: relative;
  padding-bottom: var(--space-3);
}
.dash-feed-item:last-child { padding-bottom: 0; }
.dash-feed-item::before {
  content: '';
  position: absolute;
  left: -1.25rem;
  top: 0.65rem;
  width: 6px;
  height: 6px;
  margin-left: 2px;
  border-radius: 50%;
  background: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.2);
  animation: dash-node-pulse 2.2s var(--ease-apple) infinite;
}
.dash-feed-item-inner {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  transition: background var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple);
}
.dash-feed-item-inner:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.08);
}
.dash-feed-time {
  display: block;
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: var(--space-1);
}
.dash-feed-body {
  font-size: var(--font-body);
  color: var(--text-primary);
  line-height: 1.5;
  margin: 0 0 var(--space-2);
}
.dash-feed-who {
  font-weight: 600;
  color: var(--text-primary);
}
.dash-feed-link {
  font-size: var(--font-caption);
  color: var(--primary-color);
  text-decoration: none;
  transition: color var(--duration-m) var(--ease-apple), opacity var(--duration-m) var(--ease-apple);
}
.dash-feed-link:hover {
  color: var(--secondary-color);
  opacity: 0.95;
}

@keyframes dash-node-pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.2); }
  50% { opacity: 0.85; box-shadow: 0 0 0 4px rgba(var(--primary-rgb), 0.12); }
}

.dash-feed-skeleton { padding: var(--space-1) 0; }
.dash-feed-skeleton-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
}
.dash-feed-skeleton-row .tw-skeleton-time {
  width: 3.5rem;
  height: 0.8rem;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}
.dash-feed-skeleton-row .tw-skeleton-text {
  flex: 1;
  max-width: 80%;
  height: 0.9rem;
  border-radius: var(--radius-sm);
}

.dash-feed-empty {
  padding: var(--space-8) var(--space-4);
  text-align: center;
}
.dash-feed-empty-illus {
  width: 100%;
  max-width: 220px;
  margin: 0 auto var(--space-4);
  display: block;
  opacity: 0.9;
}
.dash-feed-empty-hint {
  color: var(--text-secondary);
  font-size: var(--font-body);
  margin: 0;
}

/* NOTE: translated comment in English. */
.dash-feed-enter-active,
.dash-feed-leave-active {
  transition: opacity 0.25s var(--ease-apple), transform 0.25s var(--ease-apple);
}
.dash-feed-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}
.dash-feed-enter-to {
  opacity: 1;
  transform: translateY(0);
}
.dash-feed-leave-from { opacity: 1; }
.dash-feed-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
