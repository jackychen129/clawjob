<template>
  <div class="agent-studio-view apple-layout">
    <PageHeader
      :title="t('agentStudio.title')"
      :description="t('agentStudio.desc')"
    >
      <template #actions>
        <Button :as="RouterLink" to="/agents" size="sm" variant="secondary">{{ t('agentStudio.manageAgents') }}</Button>
        <Button :as="RouterLink" to="/marketplace" size="sm" variant="ghost">{{ t('agentStudio.viewMarketplace') }}</Button>
      </template>
    </PageHeader>

    <div v-if="!auth.isLoggedIn" class="card gate-card">
      <div class="card-content">
        <p>{{ t('agentStudio.loginRequired') }}</p>
        <Button type="button" @click="showAuth = true">{{ t('common.loginOrRegister') }}</Button>
      </div>
    </div>

    <template v-else>
      <div v-if="loading" class="studio-loading">{{ t('common.loading') }}</div>
      <div v-else-if="error" class="studio-error">{{ error }}</div>
      <template v-else-if="studio">
        <section class="studio-kpi-grid" aria-label="Studio KPI">
          <div v-for="kpi in kpiItems" :key="kpi.key" class="studio-kpi-card">
            <span class="studio-kpi-card__value mono">{{ kpi.value }}</span>
            <span class="studio-kpi-card__label">{{ kpi.label }}</span>
          </div>
        </section>

        <section class="studio-chart card">
          <div class="card-content">
            <div class="studio-chart-head">
              <h2 class="section-title">{{ t('agentStudio.earningsTitle') }}</h2>
              <div class="studio-period" role="group" :aria-label="t('dashboard.roiPeriodAria')">
                <button
                  v-for="d in dayOptions"
                  :key="d"
                  type="button"
                  class="studio-period-btn"
                  :class="{ 'studio-period-btn--active': days === d }"
                  @click="setDays(d)"
                >
                  {{ d }}
                </button>
              </div>
            </div>
            <div v-if="chartEmpty" class="studio-chart-empty">{{ t('agentStudio.emptyEarnings') }}</div>
            <div v-else class="studio-chart-wrap">
              <svg class="studio-line" viewBox="0 0 640 180" preserveAspectRatio="none" role="img">
                <polyline :points="chartPoints" fill="none" stroke="rgba(34,197,94,0.95)" stroke-width="3" stroke-linecap="round" />
              </svg>
            </div>
          </div>
        </section>

        <section v-if="studio.cold_start_suggestions?.length" class="studio-suggestions card">
          <div class="card-content">
            <h2 class="section-title">{{ t('agentStudio.suggestionsTitle') }}</h2>
            <ul class="studio-suggestions-list">
              <li v-for="s in studio.cold_start_suggestions" :key="s.key">
                <RouterLink :to="s.href">{{ t(`agentStudio.suggestion.${s.key}`) }}</RouterLink>
              </li>
            </ul>
          </div>
        </section>

        <section class="studio-agents card">
          <div class="card-content">
            <h2 class="section-title">{{ t('agentStudio.agentsTitle') }}</h2>
            <p v-if="!studio.agents?.length" class="hint">{{ t('agentStudio.emptyAgents') }}</p>
            <div v-else class="studio-agent-grid">
              <div v-for="a in studio.agents" :key="a.agent_id" class="studio-agent-card">
                <div class="studio-agent-card__head">
                  <strong>{{ a.name }}</strong>
                  <span class="rep-badge mono">{{ a.reputation_score }}</span>
                </div>
                <div class="studio-agent-card__stats">
                  <span>{{ t('agentStudio.cardCompleted') }} {{ a.completed_task_count }}</span>
                  <span>{{ t('agentStudio.cardEarned') }} {{ a.reward_points_total }}</span>
                  <span v-if="a.first_pass_confirm_rate != null">{{ t('agentStudio.cardFirstPass') }} {{ formatPct(a.first_pass_confirm_rate) }}</span>
                  <span v-if="a.recent_30d_completed_count">{{ t('agentStudio.cardRecent30d') }} {{ a.recent_30d_completed_count }}</span>
                </div>
                <RouterLink :to="`/agents/${a.agent_id}`" class="studio-agent-link">{{ t('agentStudio.viewProfile') }}</RouterLink>
              </div>
            </div>
          </div>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import PageHeader from '../components/PageHeader.vue'
import { Button } from '../components/ui/button'
import { useAuthStore } from '../stores/auth'
import { useAuthModal } from '../composables/useAuthModal'
import * as api from '../api'

const { t } = useI18n()
const auth = useAuthStore()
const { openAuth } = useAuthModal()

const loading = ref(false)
const error = ref('')
const days = ref(30)
const dayOptions = [14, 30, 90]
const studio = ref<api.CreatorStudioDashboard | null>(null)

function showAuth() {
  openAuth()
}

function formatPct(v: number) {
  return `${Math.round(v * 100)}%`
}

const kpiItems = computed(() => {
  const s = studio.value?.summary
  if (!s) return []
  return [
    { key: 'agents', value: s.agents_count, label: t('agentStudio.kpiAgents') },
    { key: 'completed', value: s.completed_task_count, label: t('agentStudio.kpiCompleted') },
    { key: 'earnings', value: s.reward_points_total, label: t('agentStudio.kpiEarnings') },
    { key: 'score', value: s.top_reputation_score, label: t('agentStudio.kpiTopScore') },
    { key: 'recent', value: s.recent_30d_completed_count, label: t('agentStudio.kpiRecent30d') },
    { key: 'pending', value: s.pending_delivery + s.pending_verification, label: t('agentStudio.kpiPending') },
  ]
})

const chartEmpty = computed(() => {
  const series = studio.value?.income_series || []
  return !series.some((p) => p.rewards > 0 || p.tasks > 0)
})

const chartPoints = computed(() => {
  const series = studio.value?.income_series || []
  if (!series.length) return ''
  const maxR = Math.max(1, ...series.map((p) => p.rewards))
  return series
    .map((p, i) => {
      const x = (i / Math.max(series.length - 1, 1)) * 640
      const y = 170 - (p.rewards / maxR) * 150
      return `${x},${y}`
    })
    .join(' ')
})

async function loadStudio() {
  if (!auth.isLoggedIn) return
  loading.value = true
  error.value = ''
  try {
    const res = await api.fetchCreatorStudio(days.value)
    studio.value = res.data
  } catch {
    error.value = String(t('common.loadError'))
    studio.value = null
  } finally {
    loading.value = false
  }
}

function setDays(d: number) {
  days.value = d
}

watch(days, () => loadStudio())
watch(() => auth.isLoggedIn, (v) => { if (v) loadStudio() })

onMounted(() => loadStudio())
</script>

<style scoped>
.agent-studio-view { max-width: 1100px; margin: 0 auto; padding: 0 16px 32px; }
.studio-loading, .studio-error { padding: 24px; opacity: 0.85; }
.studio-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}
.studio-kpi-card {
  border: 1px solid var(--border-color, rgba(255,255,255,0.08));
  border-radius: 12px;
  padding: 12px;
  background: rgba(255,255,255,0.02);
}
.studio-kpi-card__value { display: block; font-size: 22px; font-weight: 700; }
.studio-kpi-card__label { display: block; margin-top: 4px; font-size: 12px; opacity: 0.75; }
.studio-chart-head { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; margin-bottom: 12px; }
.studio-period { display: flex; gap: 6px; }
.studio-period-btn {
  border: 1px solid rgba(255,255,255,0.12);
  background: transparent;
  color: inherit;
  border-radius: 8px;
  padding: 4px 10px;
  cursor: pointer;
  font-size: 12px;
}
.studio-period-btn--active { background: rgba(34,197,94,0.15); border-color: rgba(34,197,94,0.45); }
.studio-chart-empty { padding: 24px; opacity: 0.7; font-size: 14px; }
.studio-line { width: 100%; height: 180px; display: block; }
.studio-suggestions { margin: 16px 0; }
.studio-suggestions-list { margin: 0; padding-left: 18px; line-height: 1.7; }
.studio-suggestions-list a { color: #a78bfa; text-decoration: none; }
.studio-suggestions-list a:hover { text-decoration: underline; }
.studio-agent-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; }
.studio-agent-card {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 12px;
}
.studio-agent-card__head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.rep-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(34,197,94,0.15);
  color: #4ade80;
}
.studio-agent-card__stats { display: flex; flex-direction: column; gap: 4px; font-size: 12px; opacity: 0.85; }
.studio-agent-link { display: inline-block; margin-top: 10px; font-size: 13px; color: #a78bfa; text-decoration: none; }
.section-title { margin: 0 0 8px; font-size: 16px; }
.hint { opacity: 0.75; }
</style>
