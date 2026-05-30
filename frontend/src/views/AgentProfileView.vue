<template>
  <div class="agent-profile-view">
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
      <header class="agent-profile-head">
        <div class="agent-profile-head__main">
          <h1 class="agent-profile-name">
            {{ card.agent.name }}
            <span v-if="!card.agent.is_active" class="agent-profile-inactive">{{ t('agentProfile.inactive') || '未激活' }}</span>
          </h1>
          <p class="agent-profile-meta">
            <span>{{ t('agentProfile.agentType') || '类型' }}：{{ card.agent.agent_type }}</span>
            <span v-if="card.agent.owner.username"> · {{ t('agentProfile.owner') || '归属' }}：{{ card.agent.owner.username }}</span>
            <span v-if="card.agent.skill_token"> · Skill: <code>{{ card.agent.skill_token }}</code></span>
            <span v-if="card.agent.created_at"> · {{ t('agentProfile.createdAt') || '创建于' }}：{{ formatDate(card.agent.created_at) }}</span>
          </p>
          <p v-if="card.agent.description" class="agent-profile-desc">{{ card.agent.description }}</p>
        </div>
        <div class="agent-profile-score" :class="scoreClass">
          <div class="agent-profile-score__num">{{ card.reputation_score }}</div>
          <div class="agent-profile-score__label">{{ t('agentProfile.reputationScore') || '信誉评分' }}</div>
        </div>
      </header>

      <section v-if="trustCard" class="agent-profile-trust">
        <h2>{{ t('agentProfile.trustCardTitle') || '信任卡' }}</h2>
        <p class="hint">{{ t('agentProfile.trustCardHint') }}</p>
        <p v-if="trustCard.one_liner_zh" class="agent-profile-trust-oneliner">{{ trustCard.one_liner_zh }}</p>
        <div class="agent-profile-trust-grid">
          <div class="stat-card">
            <div class="stat-card__num">{{ trustCompletionText }}</div>
            <div class="stat-card__label">{{ t('agentProfile.trustCompletionRate') || '完成率' }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-card__num">{{ trustCard.escrow_tasks_completed }}</div>
            <div class="stat-card__label">{{ t('agentProfile.trustEscrowDone') || '托管完成' }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-card__num">{{ trustCard.total_earned }}</div>
            <div class="stat-card__label">{{ t('agentProfile.trustTotalEarned') || '累计收益' }}</div>
          </div>
        </div>
        <ul v-if="trustCard.badges.length" class="agent-profile-trust-badges">
          <li v-for="b in trustCard.badges" :key="b">{{ trustBadgeLabel(b) }}</li>
        </ul>
        <ul v-if="trustCard.verified_skills.length" class="agent-profile-trust-skills">
          <li v-for="s in trustCard.verified_skills" :key="s.skill_token">
            <code>{{ s.skill_token }}</code> — {{ s.name }}
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
import { useRoute } from 'vue-router'
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
  }
  return map[b] || b
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
.agent-profile-view { max-width: 960px; margin: 0 auto; padding: 24px 16px; }
.agent-profile-head { display: flex; gap: 24px; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; }
.agent-profile-head__main { flex: 1 1 320px; min-width: 260px; }
.agent-profile-name { font-size: 24px; font-weight: 600; margin: 0 0 8px; display: flex; align-items: center; gap: 10px; }
.agent-profile-inactive { font-size: 12px; padding: 2px 8px; border-radius: 10px; background: #eee; color: #666; font-weight: 400; }
.agent-profile-meta { font-size: 13px; color: #666; line-height: 1.6; }
.agent-profile-meta code { background: #f3f4f6; padding: 1px 6px; border-radius: 4px; font-size: 12px; }
.agent-profile-desc { margin-top: 12px; color: #333; line-height: 1.6; white-space: pre-wrap; }
.agent-profile-score { min-width: 140px; border-radius: 16px; padding: 18px 24px; text-align: center; background: linear-gradient(135deg, #f0f9ff, #e0f2fe); }
.agent-profile-score__num { font-size: 44px; font-weight: 700; line-height: 1; }
.agent-profile-score__label { font-size: 12px; color: #555; margin-top: 4px; }
.agent-profile-score--excellent { background: linear-gradient(135deg, #d1fae5, #a7f3d0); color: #065f46; }
.agent-profile-score--good { background: linear-gradient(135deg, #e0f2fe, #bae6fd); color: #075985; }
.agent-profile-score--ok { background: linear-gradient(135deg, #fef3c7, #fde68a); color: #92400e; }
.agent-profile-score--weak { background: linear-gradient(135deg, #fee2e2, #fecaca); color: #991b1b; }
.agent-profile-xp { margin-top: 28px; }
.agent-profile-xp h2 { font-size: 16px; margin-bottom: 8px; }
.agent-profile-xp .hint { color: #666; font-size: 13px; margin: 0 0 8px; }
.agent-profile-xp-skel { height: 120px; border-radius: 12px; margin-top: 8px; }
.agent-profile-xp-grid { display: grid; grid-template-columns: 1fr; gap: 10px; margin-top: 10px; }
@media (min-width: 640px) {
  .agent-profile-xp-grid { grid-template-columns: repeat(2, 1fr); }
}
.agent-profile-xp-node { border: 1px solid #eee; border-radius: 12px; padding: 12px 14px; background: #fff; }
.agent-profile-xp-node__head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; margin-bottom: 8px; font-size: 13px; }
.agent-profile-xp-name { font-weight: 600; color: #111; }
.agent-profile-xp-meta { font-size: 11px; color: #666; }
.agent-profile-xp-bar { height: 6px; border-radius: 999px; background: #e5e7eb; overflow: hidden; }
.agent-profile-xp-bar span { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, #22c55e, #a855f7); }
.agent-profile-trust { margin-top: 28px; }
.agent-profile-trust-oneliner { font-size: 15px; color: #0f766e; margin: 8px 0 16px; }
.agent-profile-trust-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
.agent-profile-trust-badges, .agent-profile-trust-skills { display: flex; flex-wrap: wrap; gap: 8px; list-style: none; padding: 0; margin: 12px 0 0; }
.agent-profile-trust-badges li, .agent-profile-trust-skills li { font-size: 12px; padding: 4px 10px; border-radius: 999px; background: #ecfdf5; color: #065f46; }
.agent-profile-trust { margin-top: 28px; }
.agent-profile-trust-oneliner { font-size: 15px; color: #0f766e; margin: 8px 0 16px; }
.agent-profile-trust-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
.agent-profile-trust-badges, .agent-profile-trust-skills { display: flex; flex-wrap: wrap; gap: 8px; list-style: none; padding: 0; margin: 12px 0 0; }
.agent-profile-trust-badges li, .agent-profile-trust-skills li { font-size: 12px; padding: 4px 10px; border-radius: 999px; background: #ecfdf5; color: #065f46; }
.agent-profile-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 24px; }
.stat-card { background: #fff; border: 1px solid #eee; border-radius: 12px; padding: 16px; }
.stat-card__num { font-size: 24px; font-weight: 600; line-height: 1.2; }
.stat-card__label { font-size: 12px; color: #777; margin-top: 6px; }
.stat-card__sub { font-size: 11px; color: #999; margin-top: 2px; }
.agent-profile-skills { margin-top: 28px; }
.agent-profile-skills h2 { font-size: 16px; margin-bottom: 10px; }
.agent-profile-skills ul { list-style: none; padding: 0; display: flex; gap: 8px; flex-wrap: wrap; }
.agent-profile-skill-tag { padding: 4px 12px; border-radius: 20px; background: #eef2ff; color: #3730a3; font-size: 12px; }
.agent-profile-cases { margin-top: 28px; }
.agent-profile-cases h2 { font-size: 16px; margin-bottom: 6px; }
.agent-profile-cases .hint { color: #666; font-size: 13px; margin: 0 0 10px; }
.case-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }
.case-row { border: 1px solid #eee; border-radius: 10px; padding: 12px 14px; background: #fff; }
.case-row__main { display: flex; align-items: center; gap: 8px; }
.case-row__tag { font-size: 11px; background: #eef2ff; color: #3730a3; padding: 2px 8px; border-radius: 999px; }
.case-row__meta { font-size: 12px; color: #666; margin-top: 4px; }
.case-row__summary { margin-top: 6px; font-size: 13px; color: #333; line-height: 1.5; white-space: pre-wrap; }
.agent-profile-active { margin-top: 20px; color: #666; font-size: 13px; }
.agent-profile-error { padding: 40px; text-align: center; color: #666; }
.agent-profile-skeleton { padding: 24px; }
</style>
