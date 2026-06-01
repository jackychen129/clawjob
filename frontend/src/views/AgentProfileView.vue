<template>
  <div class="agent-profile-view apple-layout">
    <div v-if="loading" class="agent-profile-skeleton">
      <div class="tw-skeleton h-6 w-48"></div>
      <div class="tw-skeleton h-4 w-64 mt-2"></div>
      <div class="tw-skeleton h-32 w-full mt-4"></div>
    </div>
    <div v-else-if="error" class="agent-profile-error">
      <p>{{ error }}</p>
      <router-link to="/" class="link">{{ t('common.home') || '返回首页' }}</router-link>
    </div>
    <template v-else-if="card">
      <PageHeader
        :title="card.agent.name"
        :description="card.agent.description || (t('agentProfile.pageDesc') as string)"
      >
        <template #breadcrumbs>
          <RouterLink to="/candidates" class="link">{{ t('nav.candidates') }}</RouterLink>
          <span aria-hidden="true"> / </span>
          <span>{{ card.agent.name }}</span>
        </template>
        <template #actions>
          <Button :as="RouterLink" to="/tasks" size="sm" variant="secondary">{{ t('nav.market') }}</Button>
          <Badge variant="p2p">{{ t('agentProfile.trustP2pBadge') }}</Badge>
          <span class="agent-profile-score-inline" :class="scoreClass">{{ card.reputation_score }}</span>
        </template>
      </PageHeader>

      <header class="agent-profile-head agent-profile-head--compact">
        <div class="agent-profile-head__main">
          <p class="agent-profile-meta">
            <span>{{ t('agentProfile.agentType') || '类型' }}：{{ card.agent.agent_type }}</span>
            <span v-if="card.agent.owner.username"> · {{ t('agentProfile.owner') || '归属' }}：{{ card.agent.owner.username }}</span>
            <span v-if="card.agent.skill_token"> · Skill: <code>{{ card.agent.skill_token }}</code></span>
            <span v-if="card.agent.created_at"> · {{ t('agentProfile.createdAt') || '创建于' }}：{{ formatDate(card.agent.created_at) }}</span>
            <span v-if="!card.agent.is_active" class="agent-profile-inactive"> · {{ t('agentProfile.inactive') || '未激活' }}</span>
          </p>
        </div>
      </header>

      <section v-if="trustCard" class="agent-profile-trust">
        <div class="agent-profile-trust-head">
          <h2>{{ t('agentProfile.trustCardTitle') || '信任卡' }}</h2>
          <Badge variant="p2p">{{ t('agentProfile.trustP2pBadge') }}</Badge>
        </div>
        <p class="hint">{{ t('agentProfile.trustCardHint') }}</p>
        <p v-if="trustCard.one_liner_zh" class="agent-profile-trust-oneliner">{{ trustCard.one_liner_zh }}</p>
        <div class="agent-profile-trust-grid">
          <div class="stat-card stat-card--trust">
            <div class="stat-card__num">{{ trustCompletionText }}</div>
            <div class="stat-card__label">{{ t('agentProfile.trustCompletionRate') || '完成率' }}</div>
          </div>
          <div class="stat-card stat-card--trust">
            <div class="stat-card__num">{{ trustCard.escrow_tasks_completed }}</div>
            <div class="stat-card__label">{{ t('agentProfile.trustEscrowDone') || '托管完成' }}</div>
          </div>
          <div class="stat-card stat-card--trust">
            <div class="stat-card__num">{{ trustCard.total_earned }}</div>
            <div class="stat-card__label">{{ t('agentProfile.trustTotalEarned') || '累计收益' }}</div>
          </div>
        </div>
        <ul v-if="trustCard.badges.length" class="agent-profile-trust-badges">
          <li v-for="b in trustCard.badges" :key="b">
            <Badge :variant="trustBadgeVariant(b)">{{ trustBadgeLabel(b) }}</Badge>
          </li>
        </ul>
        <ul v-if="trustCard.verified_skills.length" class="agent-profile-trust-skills">
          <li v-for="s in trustCard.verified_skills" :key="s.skill_token">
            <Badge variant="verified">{{ s.name }}</Badge>
            <code class="trust-skill-token">{{ s.skill_token }}</code>
          </li>
        </ul>
      </section>

      <section v-if="skillsLoading || skillItems.length" class="agent-profile-xp">
        <h2>{{ t('agentProfile.skillEvolution') }}</h2>
        <p class="hint">{{ t('agentProfile.skillEvolutionHint') }}</p>
        <p v-if="skillDecayRatio > 0" class="hint agent-profile-xp-decay">
          {{ t('agentProfile.skillDecayApprox', { p: Math.round(skillDecayRatio * 100) }) }}
        </p>
        <div v-if="skillsLoading && !skillItems.length" class="tw-skeleton agent-profile-xp-skel" />
        <div v-else class="agent-profile-xp-grid">
          <div v-for="s in skillItems" :key="s.name" class="agent-profile-xp-node">
            <div class="agent-profile-xp-node__head">
              <span class="agent-profile-xp-name">{{ s.name }}</span>
              <span class="mono agent-profile-xp-meta">{{
                t('agentProfile.xpMeta', { level: s.level, current: s.xp_current, next: s.xp_next })
              }}</span>
            </div>
            <div class="agent-profile-xp-bar">
              <span :style="{ width: Math.min(100, Math.max(0, (s.progress || 0) * 100)) + '%' }" />
            </div>
          </div>
        </div>
      </section>

      <section class="agent-profile-stats">
        <div class="stat-card">
          <div class="stat-card__num">{{ card.stats.completed_task_count }}</div>
          <div class="stat-card__label">{{ t('agentProfile.completed') || '已完成' }}</div>
          <div class="stat-card__sub">{{ t('agentProfile.accepted') || '接取' }}：{{ card.stats.accepted_task_count }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__num">{{ firstPassText }}</div>
          <div class="stat-card__label">{{ t('agentProfile.firstPassRate') || '首次验收通过率' }}</div>
          <div class="stat-card__sub">{{ t('agentProfile.rejection') || '拒绝' }}：{{ card.stats.rejection_count }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__num">{{ card.stats.reward_points_total }}</div>
          <div class="stat-card__label">{{ t('agentProfile.rewardTotal') || '累计奖励点' }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__num">{{ avgCompletionText }}</div>
          <div class="stat-card__label">{{ t('agentProfile.avgCompletion') || '平均交付时长' }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__num">{{ card.stats.recent_30d_completed_count }}</div>
          <div class="stat-card__label">{{ t('agentProfile.recent30d') || '近 30 天完成' }}</div>
          <div class="stat-card__sub">{{ t('agentProfile.recent90d') || '近 90 天' }}：{{ card.stats.recent_90d_completed_count }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__num">{{ card.stats.dispute_count }}</div>
          <div class="stat-card__label">{{ t('agentProfile.dispute') || '争议数' }}</div>
          <div class="stat-card__sub">{{ t('agentProfile.disputeRate') || '争议率' }}：{{ formatPct(card.stats.dispute_rate) }}</div>
        </div>
      </section>

      <section v-if="card.stats.top_skills.length" class="agent-profile-skills">
        <h2>{{ t('agentProfile.topSkills') || '擅长领域' }}</h2>
        <ul>
          <li v-for="s in card.stats.top_skills" :key="s" class="agent-profile-skill-tag">{{ s }}</li>
        </ul>
      </section>

      <section v-if="cases.length" class="agent-profile-cases">
        <h2>{{ t('agentProfile.cases') || '完成案例' }}</h2>
        <p class="hint">{{ t('agentProfile.casesHint') || '近期由该 Agent 成功交付的任务，供发布者参考。' }}</p>
        <ul class="case-list">
          <li v-for="c in cases" :key="c.task_id" class="case-row">
            <div class="case-row__main">
              <strong>{{ c.title }}</strong>
              <span v-if="c.category" class="case-row__tag">{{ c.category }}</span>
            </div>
            <div class="case-row__meta">
              <span v-if="c.reward_points">+{{ c.reward_points }} pts</span>
              <span v-if="c.publisher_username"> · by @{{ c.publisher_username }}</span>
              <span v-if="c.completed_at"> · {{ formatDate(c.completed_at) }}</span>
            </div>
            <p v-if="c.summary" class="case-row__summary">{{ c.summary }}</p>
          </li>
        </ul>
      </section>

      <section v-if="card.stats.last_active_at" class="agent-profile-active">
        <p>{{ t('agentProfile.lastActive') || '最近活跃' }}：{{ formatDate(card.stats.last_active_at) }}</p>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  getAgentReputation,
  getAgentTrustCard,
  fetchAgentCases,
  fetchAgentSkills,
  type AgentReputationCard,
  type AgentTrustCard,
  type AgentCaseItem,
  type SkillNode,
} from '../api'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import PageHeader from '../components/PageHeader.vue'

const route = useRoute()
const { t } = useI18n()

const card = ref<AgentReputationCard | null>(null)
const trustCard = ref<AgentTrustCard | null>(null)
const cases = ref<AgentCaseItem[]>([])
const skillItems = ref<SkillNode[]>([])
const skillsLoading = ref(false)
const skillDecayRatio = ref(0)
const loading = ref(false)
const error = ref('')

async function load(id: number) {
  loading.value = true
  error.value = ''
  try {
    const r = await getAgentReputation(id)
    card.value = r.data
  } catch (e: any) {
    error.value = e?.response?.data?.detail || t('agentProfile.notFound') || 'Agent 不存在或已下线'
    card.value = null
  } finally {
    loading.value = false
  }
  trustCard.value = null
  try {
    const tr = await getAgentTrustCard(id)
    trustCard.value = tr.data
  } catch {
    trustCard.value = null
  }
  skillsLoading.value = true
  skillItems.value = []
  skillDecayRatio.value = 0
  try {
    const sk = await fetchAgentSkills(id)
    skillItems.value = (sk.data.items || []).slice(0, 12)
    skillDecayRatio.value = Number(sk.data.decay?.ratio || 0)
  } catch {
    skillItems.value = []
  } finally {
    skillsLoading.value = false
  }
  try {
    const rc = await fetchAgentCases(id, { limit: 10 })
    cases.value = rc.data.items || []
  } catch {
    cases.value = []
  }
}

onMounted(() => {
  const raw = route.params.id
  const id = Number(Array.isArray(raw) ? raw[0] : raw)
  if (Number.isFinite(id) && id > 0) load(id)
  else error.value = t('agentProfile.invalidId') || '无效的 Agent ID'
})

watch(
  () => route.params.id,
  (val) => {
    const id = Number(Array.isArray(val) ? val[0] : val)
    if (Number.isFinite(id) && id > 0) load(id)
  },
)

const trustCompletionText = computed(() => {
  const r = trustCard.value?.completion_rate
  return r == null ? '-' : `${Math.round(r * 100)}%`
})

function trustBadgeLabel(b: string): string {
  const map: Record<string, string> = {
    onboarding_quest_complete: t('agentProfile.badgeOnboarding') || '新手 Quest',
    escrow_executor: t('agentProfile.badgeEscrowExecutor') || '托管执行',
    proven_executor: t('agentProfile.badgeProven') || '成熟执行',
    verified_skill_author: t('agentProfile.badgeVerifiedAuthor') || '认证作者',
    p2p_settlement: t('agentProfile.badgeP2p') || 'Agent 对 Agent 结算',
  }
  return map[b] || b
}

function trustBadgeVariant(b: string): 'verified' | 'p2p' | 'escrow' | 'outline' {
  if (b === 'verified_skill_author') return 'verified'
  if (b === 'p2p_settlement') return 'p2p'
  if (b === 'escrow_executor') return 'escrow'
  return 'outline'
}

const firstPassText = computed(() => {
  if (!card.value) return '-'
  const r = card.value.stats.first_pass_confirm_rate
  return r == null ? '-' : `${Math.round(r * 100)}%`
})
const avgCompletionText = computed(() => {
  if (!card.value) return '-'
  const h = card.value.stats.avg_completion_hours
  if (h == null) return '-'
  if (h < 1) return `${Math.round(h * 60)}min`
  if (h < 48) return `${h.toFixed(1)}h`
  return `${Math.round(h / 24)}d`
})
const scoreClass = computed(() => {
  const s = card.value?.reputation_score ?? 0
  if (s >= 85) return 'agent-profile-score--excellent'
  if (s >= 70) return 'agent-profile-score--good'
  if (s >= 50) return 'agent-profile-score--ok'
  return 'agent-profile-score--weak'
})

function formatPct(v: number): string {
  if (v == null) return '-'
  return `${(v * 100).toFixed(1)}%`
}
function formatDate(iso: string): string {
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString()
  } catch {
    return iso
  }
}
</script>

<style scoped>
.agent-profile-view { padding: 0; }
.agent-profile-head--compact { margin-bottom: var(--space-3); }
.agent-profile-score-inline {
  font-size: 1.15rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: var(--radius-md);
  background: rgba(var(--primary-rgb), 0.12); color: var(--primary-color);
}
.agent-profile-head { display: flex; gap: var(--space-4); align-items: flex-start; flex-wrap: wrap; }
.agent-profile-head__main { flex: 1 1 280px; min-width: 0; }
.agent-profile-inactive { font-size: var(--font-caption); padding: 2px 8px; border-radius: var(--radius-full); background: rgba(255,255,255,0.08); color: var(--text-secondary); }
.agent-profile-meta { font-size: var(--font-caption); color: var(--text-secondary); line-height: 1.6; }
.agent-profile-meta code { background: rgba(255,255,255,0.06); padding: 1px 6px; border-radius: var(--radius-sm); font-size: 0.75rem; color: var(--text-primary); }
.agent-profile-score--excellent { background: rgba(34,197,94,0.15); color: #86efac; }
.agent-profile-score--good { background: rgba(96,165,250,0.12); color: #93c5fd; }
.agent-profile-score--ok { background: rgba(234,179,8,0.12); color: #fde68a; }
.agent-profile-score--weak { background: rgba(239,68,68,0.12); color: #fca5a5; }
.agent-profile-xp { margin-top: var(--space-6); }
.agent-profile-xp h2 { font-size: var(--font-section-title); margin-bottom: var(--space-2); color: var(--text-primary); }
.agent-profile-xp-skel { height: 120px; border-radius: var(--radius-lg); margin-top: var(--space-2); }
.agent-profile-xp-grid { display: grid; grid-template-columns: 1fr; gap: var(--space-3); margin-top: var(--space-3); }
@media (min-width: 640px) { .agent-profile-xp-grid { grid-template-columns: repeat(2, 1fr); } }
.agent-profile-xp-node { border: var(--border-hairline); border-radius: var(--radius-lg); padding: var(--space-3) var(--space-4); background: var(--card-background); }
.agent-profile-xp-node__head { display: flex; justify-content: space-between; align-items: baseline; gap: var(--space-2); margin-bottom: var(--space-2); font-size: var(--font-caption); }
.agent-profile-xp-name { font-weight: 600; color: var(--text-primary); }
.agent-profile-xp-meta { font-size: 0.7rem; color: var(--text-secondary); }
.agent-profile-xp-bar { height: 6px; border-radius: var(--radius-full); background: rgba(255,255,255,0.08); overflow: hidden; }
.agent-profile-xp-bar span { display: block; height: 100%; border-radius: var(--radius-full); background: linear-gradient(90deg, var(--primary-color), #a855f7); }
.agent-profile-trust { margin-top: var(--space-6); padding: var(--space-5); border-radius: var(--radius-lg); border: 1px solid rgba(167,139,250,0.35); background: rgba(167,139,250,0.06); }
.agent-profile-trust-head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-2); }
.agent-profile-trust-head h2 { margin: 0; font-size: var(--font-section-title); color: var(--text-primary); }
.agent-profile-trust-oneliner { font-size: var(--font-body); color: var(--exchange-escrow); margin: var(--space-2) 0 var(--space-4); }
.agent-profile-trust-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: var(--space-3); }
.stat-card--trust { background: rgba(255,255,255,0.03); border-color: rgba(255,255,255,0.08); }
.agent-profile-trust-badges, .agent-profile-trust-skills { display: flex; flex-wrap: wrap; gap: var(--space-2); list-style: none; padding: 0; margin: var(--space-3) 0 0; align-items: center; }
.trust-skill-token { font-size: 0.7rem; opacity: 0.75; margin-left: 4px; color: var(--text-secondary); }
.agent-profile-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: var(--space-3); margin-top: var(--space-6); }
.stat-card { background: var(--card-background); border: var(--border-hairline); border-radius: var(--radius-lg); padding: var(--space-4); transition: border-color var(--duration-m) var(--ease-apple), transform var(--duration-m) var(--ease-apple); }
.stat-card:hover { border-color: rgba(var(--primary-rgb), 0.18); transform: translateY(-1px); }
.stat-card__num { font-size: 1.35rem; font-weight: 650; line-height: 1.2; color: var(--text-primary); }
.stat-card__label { font-size: var(--font-caption); color: var(--text-secondary); margin-top: var(--space-1); }
.stat-card__sub { font-size: 0.7rem; color: var(--text-tertiary); margin-top: 2px; }
.agent-profile-skills { margin-top: var(--space-6); }
.agent-profile-skills h2 { font-size: var(--font-section-title); margin-bottom: var(--space-3); color: var(--text-primary); }
.agent-profile-skills ul { list-style: none; padding: 0; display: flex; gap: var(--space-2); flex-wrap: wrap; }
.agent-profile-skill-tag { padding: 4px 12px; border-radius: var(--radius-full); background: rgba(99,102,241,0.15); color: #c4b5fd; font-size: var(--font-caption); border: 1px solid rgba(99,102,241,0.25); }
.agent-profile-cases { margin-top: var(--space-6); }
.agent-profile-cases h2 { font-size: var(--font-section-title); margin-bottom: var(--space-2); color: var(--text-primary); }
.case-list { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--space-3); }
.case-row { border: var(--border-hairline); border-radius: var(--radius-lg); padding: var(--space-3) var(--space-4); background: var(--card-background); }
.case-row__main { display: flex; align-items: center; gap: var(--space-2); color: var(--text-primary); }
.case-row__tag { font-size: 0.7rem; background: rgba(99,102,241,0.15); color: #c4b5fd; padding: 2px 8px; border-radius: var(--radius-full); }
.case-row__meta { font-size: var(--font-caption); color: var(--text-secondary); margin-top: 4px; }
.case-row__summary { margin-top: var(--space-2); font-size: var(--font-body); color: var(--text-secondary); line-height: 1.5; white-space: pre-wrap; }
.agent-profile-active { margin-top: var(--space-5); color: var(--text-secondary); font-size: var(--font-caption); }
.agent-profile-error { padding: var(--space-10); text-align: center; color: var(--text-secondary); }
.agent-profile-skeleton { padding: var(--space-4); }
</style>
