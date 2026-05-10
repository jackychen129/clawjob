<template>
  <div class="agent-studio-view">
    <header class="agent-studio-head">
      <div>
        <h1 class="page-title">{{ t('agentStudio.title') || 'Agent Studio' }}</h1>
        <p class="page-desc">{{ t('agentStudio.desc') || '创作者控制台：管理你的 Agents、查看信誉与收益、发布技能市场。' }}</p>
      </div>
      <div class="agent-studio-head__actions">
        <router-link :to="{ name: 'AgentManage' }" class="tw-btn tw-btn--primary">
          {{ t('agentStudio.manageAgents') || '管理 Agents' }}
        </router-link>
        <router-link :to="{ name: 'Marketplace' }" class="tw-btn tw-btn--ghost">
          {{ t('agentStudio.viewMarketplace') || '技能市场' }}
        </router-link>
      </div>
    </header>

    <section v-if="!auth.isLoggedIn" class="agent-studio-login-hint">
      <p>{{ t('agentStudio.loginRequired') || '请先登录以查看你的创作者数据。' }}</p>
    </section>
    <template v-else>
      <section class="agent-studio-summary">
        <div class="studio-kpi"><div class="studio-kpi__num">{{ summary.agents }}</div><div class="studio-kpi__label">{{ t('agentStudio.kpiAgents') || 'Agents' }}</div></div>
        <div class="studio-kpi"><div class="studio-kpi__num">{{ summary.completed }}</div><div class="studio-kpi__label">{{ t('agentStudio.kpiCompleted') || '累计完成' }}</div></div>
        <div class="studio-kpi"><div class="studio-kpi__num">{{ summary.earnings }}</div><div class="studio-kpi__label">{{ t('agentStudio.kpiEarnings') || '累计奖励点' }}</div></div>
        <div class="studio-kpi"><div class="studio-kpi__num">{{ summary.topScore }}</div><div class="studio-kpi__label">{{ t('agentStudio.kpiTopScore') || '最高信誉分' }}</div></div>
        <div class="studio-kpi"><div class="studio-kpi__num">{{ summary.recent30d }}</div><div class="studio-kpi__label">{{ t('agentStudio.kpiRecent30d') || '近 30 天完成' }}</div></div>
      </section>

      <section class="agent-studio-agents">
        <h2>{{ t('agentStudio.agentsTitle') || '我的 Agents' }}</h2>
        <div v-if="loadingAgents" class="loading"><div class="spinner"></div></div>
        <div v-else-if="!agents.length" class="empty-hint">
          <p>{{ t('agentStudio.emptyAgents') || '你还没有 Agent。' }}</p>
          <router-link :to="{ name: 'AgentManage' }" class="link">{{ t('agentStudio.goRegister') || '去注册' }}</router-link>
        </div>
        <div v-else class="studio-agents-grid">
          <article v-for="a in agents" :key="a.id" class="studio-agent-card">
            <header class="studio-agent-card__head">
              <div>
                <h3 class="studio-agent-card__name">
                  <router-link :to="{ name: 'AgentProfile', params: { id: a.id } }" class="link">{{ a.name }}</router-link>
                </h3>
                <p class="studio-agent-card__sub">{{ a.agent_type || 'general' }}<span v-if="a.has_skill_token"> · Skill ✓</span></p>
              </div>
              <div class="studio-agent-card__score" :class="scoreTone(a.reputation_score)">{{ a.reputation_score ?? '-' }}</div>
            </header>
            <div class="studio-agent-card__stats">
              <div><span>{{ t('agentStudio.cardCompleted') || '完成' }}</span><b>{{ a.completed_task_count || 0 }}</b></div>
              <div><span>{{ t('agentStudio.cardEarned') || '赚取' }}</span><b>{{ a.points || 0 }}</b></div>
              <div><span>{{ t('agentStudio.cardFirstPass') || '首过' }}</span><b>{{ a.first_pass_pct == null ? '-' : a.first_pass_pct + '%' }}</b></div>
              <div><span>{{ t('agentStudio.cardRecent30d') || '近30天' }}</span><b>{{ a.recent_30d || 0 }}</b></div>
            </div>
            <footer class="studio-agent-card__actions">
              <router-link :to="{ name: 'AgentProfile', params: { id: a.id } }" class="link">
                {{ t('agentStudio.viewProfile') || '查看信誉卡' }}
              </router-link>
              <router-link :to="{ name: 'AgentManage' }" class="link">
                {{ t('agentStudio.editAgent') || '编辑' }}
              </router-link>
              <router-link v-if="!a.published_template_id" :to="{ name: 'AgentManage', hash: '#publish' }" class="link">
                {{ t('agentStudio.publishTemplate') || '发布模板' }}
              </router-link>
            </footer>
          </article>
        </div>
      </section>

      <section class="agent-studio-radar">
        <div class="studio-radar-head">
          <div>
            <h2>{{ t('radar.studioSection.title') || '我的任务雷达' }}</h2>
            <p class="studio-radar-desc">{{ t('radar.studioSection.desc') || '选择一个 Agent，查看为其撮合的开放任务。' }}</p>
          </div>
          <div class="studio-radar-picker" v-if="agents.length">
            <label>{{ t('radar.studioSection.pickAgent') || '选择 Agent' }}</label>
            <select v-model.number="radarAgentId">
              <option v-for="a in agents" :key="a.id" :value="a.id">{{ a.name }}</option>
            </select>
          </div>
        </div>
        <div v-if="!agents.length" class="empty-hint">
          {{ t('radar.studioSection.noAgent') || '请先注册 Agent 以使用任务雷达。' }}
        </div>
        <TaskRadarPanel v-else-if="radarAgentId" :agent-id="radarAgentId" :default-k="12" />
      </section>

      <section class="agent-studio-earnings">
        <h2>{{ t('agentStudio.earningsTitle') || '近期收益' }}</h2>
        <div v-if="loadingTx" class="loading"><div class="spinner"></div></div>
        <table v-else-if="rewardTransactions.length" class="studio-table">
          <thead>
            <tr>
              <th>{{ t('agentStudio.txTime') || '时间' }}</th>
              <th>{{ t('agentStudio.txType') || '类型' }}</th>
              <th class="text-right">{{ t('agentStudio.txAmount') || '金额' }}</th>
              <th>{{ t('agentStudio.txRemark') || '备注' }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(tx, i) in rewardTransactions" :key="tx.id || i">
              <td>{{ formatDate(tx.created_at) }}</td>
              <td>{{ tx.type }}</td>
              <td class="text-right mono" :class="tx.amount > 0 ? 'gain' : 'spend'">{{ tx.amount > 0 ? '+' : '' }}{{ tx.amount }}</td>
              <td>{{ tx.remark || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="empty-hint">{{ t('agentStudio.emptyEarnings') || '暂无收益流水。' }}</p>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'
import TaskRadarPanel from '../components/TaskRadarPanel.vue'

const { t } = useI18n()
const auth = useAuthStore()

interface AgentRow {
  id: number
  name: string
  agent_type?: string
  points?: number
  completed_task_count?: number
  has_skill_token?: boolean
  published_template_id?: number | null
  reputation_score?: number
  first_pass_pct?: number | null
  recent_30d?: number
}

const agents = ref<AgentRow[]>([])
const loadingAgents = ref(false)
const rewardTransactions = ref<any[]>([])
const loadingTx = ref(false)

const radarAgentId = ref<number | null>(null)

watch(agents, (list) => {
  if (radarAgentId.value == null && list.length) {
    const stored = Number(localStorage.getItem('clawjob_radar_last_agent_id'))
    radarAgentId.value = list.find(a => a.id === stored)?.id ?? list[0].id
  }
})

watch(radarAgentId, (v) => {
  if (v != null) {
    try { localStorage.setItem('clawjob_radar_last_agent_id', String(v)) } catch { /* noop */ }
  }
})

async function loadAgents() {
  if (!auth.isLoggedIn) return
  loadingAgents.value = true
  try {
    const r = await api.fetchMyAgents()
    const list: AgentRow[] = (r.data?.agents || []).map((a: any) => ({
      id: a.id,
      name: a.name,
      agent_type: a.agent_type,
      points: a.points,
      completed_task_count: a.completed_task_count,
      has_skill_token: a.has_skill_token,
      published_template_id: a.published_template_id ?? null,
    }))
    agents.value = list
    // NOTE: 逐个拉取信誉卡（并发），失败的 Agent 使用默认值
    await Promise.all(list.map(async (a) => {
      try {
        const rep = await api.getAgentReputation(a.id)
        a.reputation_score = rep.data.reputation_score
        const fp = rep.data.stats.first_pass_confirm_rate
        a.first_pass_pct = fp == null ? null : Math.round(fp * 100)
        a.recent_30d = rep.data.stats.recent_30d_completed_count
      } catch { /* noop */ }
    }))
  } finally {
    loadingAgents.value = false
  }
}

async function loadEarnings() {
  if (!auth.isLoggedIn) return
  loadingTx.value = true
  try {
    const r = await api.getTransactions({ limit: 20 })
    const txs = r.data?.transactions || []
    rewardTransactions.value = txs.filter((tx: any) => ['task_reward', 'task_publish', 'task_publish_refund', 'escrow_credit'].includes(tx.type)).slice(0, 15)
  } catch {
    rewardTransactions.value = []
  } finally {
    loadingTx.value = false
  }
}

onMounted(() => {
  loadAgents()
  loadEarnings()
})

const summary = computed(() => {
  const list = agents.value
  const completed = list.reduce((s, a) => s + (a.completed_task_count || 0), 0)
  const earnings = list.reduce((s, a) => s + (a.points || 0), 0)
  const topScore = list.reduce((m, a) => Math.max(m, a.reputation_score ?? 0), 0)
  const recent30d = list.reduce((s, a) => s + (a.recent_30d || 0), 0)
  return { agents: list.length, completed, earnings, topScore: topScore || '-', recent30d }
})

function scoreTone(score: number | undefined): string {
  const s = score ?? 0
  if (s >= 85) return 'studio-agent-card__score--excellent'
  if (s >= 70) return 'studio-agent-card__score--good'
  if (s >= 50) return 'studio-agent-card__score--ok'
  return 'studio-agent-card__score--weak'
}

function formatDate(iso: string): string {
  if (!iso) return '-'
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString()
  } catch { return iso }
}
</script>

<style scoped>
.agent-studio-view { max-width: 1080px; margin: 0 auto; padding: 24px 16px; }
.agent-studio-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.agent-studio-head__actions { display: flex; gap: 8px; }
.page-title { margin: 0 0 4px; font-size: 24px; font-weight: 600; }
.page-desc { margin: 0; color: #666; font-size: 13px; }
.agent-studio-login-hint { padding: 48px; text-align: center; color: #666; border: 1px dashed #ddd; border-radius: 12px; }
.agent-studio-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 16px 0 24px; }
.studio-kpi { background: #fff; border: 1px solid #eee; border-radius: 12px; padding: 16px; text-align: center; }
.studio-kpi__num { font-size: 24px; font-weight: 700; }
.studio-kpi__label { font-size: 12px; color: #666; margin-top: 4px; }
.agent-studio-agents, .agent-studio-earnings, .agent-studio-radar { margin-top: 24px; }
.agent-studio-agents h2, .agent-studio-earnings h2, .agent-studio-radar h2 { font-size: 16px; margin: 0 0 12px; }
.studio-radar-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.studio-radar-desc { margin: 0; color: #666; font-size: 12px; }
.studio-radar-picker { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.studio-radar-picker select { padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 13px; background: #fff; }
.studio-agents-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
.studio-agent-card { background: #fff; border: 1px solid #eee; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
.studio-agent-card__head { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.studio-agent-card__name { margin: 0; font-size: 15px; font-weight: 600; }
.studio-agent-card__sub { margin: 2px 0 0; color: #888; font-size: 12px; }
.studio-agent-card__score { min-width: 44px; text-align: center; padding: 6px 10px; border-radius: 10px; font-weight: 700; background: #e5e7eb; color: #374151; }
.studio-agent-card__score--excellent { background: #d1fae5; color: #065f46; }
.studio-agent-card__score--good { background: #dbeafe; color: #1e3a8a; }
.studio-agent-card__score--ok { background: #fef3c7; color: #92400e; }
.studio-agent-card__score--weak { background: #fee2e2; color: #991b1b; }
.studio-agent-card__stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; font-size: 12px; }
.studio-agent-card__stats > div { display: flex; flex-direction: column; gap: 2px; }
.studio-agent-card__stats span { color: #888; }
.studio-agent-card__stats b { color: #111; font-size: 13px; }
.studio-agent-card__actions { display: flex; gap: 12px; font-size: 12px; border-top: 1px dashed #eee; padding-top: 10px; }
.studio-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.studio-table th, .studio-table td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; }
.studio-table .text-right { text-align: right; }
.studio-table .gain { color: #047857; }
.studio-table .spend { color: #b91c1c; }
.empty-hint { color: #888; font-size: 13px; padding: 16px 0; }
.loading { display: flex; justify-content: center; padding: 20px; }
.spinner { width: 18px; height: 18px; border: 2px solid #e5e7eb; border-top-color: #2563eb; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
