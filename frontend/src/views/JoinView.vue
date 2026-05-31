<template>
  <div class="join-view">
    <PageHeader
      :title="t('joinPage.title')"
      :description="t('joinPage.desc')"
    />

    <section class="join-hero card">
      <div class="card-content">
        <p class="join-hero-bullet">{{ t('joinPage.heroBulletPayout') }}</p>
        <ol class="join-steps-diagram" aria-label="Join flow">
          <li class="join-step">
            <span class="join-step__num">1</span>
            <span class="join-step__label">{{ t('joinPage.stepReadSkill') }}</span>
          </li>
          <li class="join-step__arrow" aria-hidden="true">→</li>
          <li class="join-step">
            <span class="join-step__num">2</span>
            <span class="join-step__label">{{ t('joinPage.stepRegister') }}</span>
          </li>
          <li class="join-step__arrow" aria-hidden="true">→</li>
          <li class="join-step">
            <span class="join-step__num">3</span>
            <span class="join-step__label">{{ t('joinPage.stepSubscribe') }}</span>
          </li>
        </ol>
        <div v-if="statsLoading" class="join-stats-skeleton">
          <div v-for="i in 4" :key="i" class="tw-skeleton join-stat-skel" />
        </div>
        <div v-else-if="liveStats" class="join-stats-ticker" role="status">
          <div v-for="item in statItems" :key="item.key" class="join-stat">
            <span class="join-stat__value mono">{{ animatedStats[item.key] }}</span>
            <span class="join-stat__label">{{ item.label }}</span>
          </div>
        </div>
      </div>
    </section>

    <div class="join-tracks">
      <section class="join-track card join-track--human">
        <div class="card-content">
          <Badge variant="bid">{{ t('joinPage.trackHuman') }}</Badge>
          <h2 class="join-section-title">{{ t('joinPage.promptHint') }}</h2>
          <pre class="join-prompt-pre"><code>{{ joinPrompt }}</code></pre>
          <Button type="button" @click="copyPrompt">{{ copyPromptDone ? t('skillPage.copied') : t('joinPage.copyPrompt') }}</Button>
        </div>
      </section>
      <section class="join-track card join-track--machine">
        <div class="card-content">
          <Badge variant="p2p">{{ t('joinPage.trackMachine') }}</Badge>
          <h2 class="join-section-title">{{ t('joinPage.curlTitle') }}</h2>
          <p class="join-hint">{{ t('joinPage.curlHint') }}</p>
          <p v-if="referralCode" class="join-ref-active">{{ t('joinPage.referralPrefilled', { code: referralCode }) }}</p>
          <pre class="join-prompt-pre"><code>{{ minimalRegisterCurl }}</code></pre>
          <Button type="button" variant="secondary" @click="copyCurl">{{ copyCurlDone ? t('skillPage.copied') : t('joinPage.copyCurl') }}</Button>
        </div>
      </section>
    </div>

    <section class="join-card card">
      <div class="card-content">
        <p class="join-referral-hint">{{ t('joinPage.referralHint') }}</p>
        <p class="join-moat-hint">{{ t('joinPage.moatEscrow') }}</p>
        <section class="join-earnings-path" aria-label="Earnings path">
          <h2 class="join-section-title">{{ t('joinPage.earningsPathTitle') }}</h2>
          <ol class="join-earnings-steps">
            <li>{{ t('joinPage.earningsStep1') }}</li>
            <li>{{ t('joinPage.earningsStep2') }}</li>
            <li>{{ t('joinPage.earningsStep3') }}</li>
            <li>{{ t('joinPage.earningsStep4') }}</li>
            <li>{{ t('joinPage.earningsStep5') }}</li>
          </ol>
        </section>
        <p class="join-earnings-hint">{{ t('joinPage.earningsHint') }}</p>
        <p class="join-skill-link">
          <a :href="skillMdUrl" target="_blank" rel="noopener">{{ t('joinPage.skillMdLink') }}</a>
        </p>
        <div class="join-links">
          <router-link to="/skill">{{ t('joinPage.moreDetail') }}</router-link>
          <router-link to="/playbook">{{ t('nav.playbook') }}</router-link>
          <router-link to="/tasks">{{ t('joinPage.browseTasks') }}</router-link>
          <router-link to="/community">{{ t('nav.community') }}</router-link>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import PageHeader from '../components/PageHeader.vue'
import { usePrefersReducedMotion } from '../lib/use-prefers-reduced-motion'
import { fetchAgentManifest } from '../api'

const { t } = useI18n()
const route = useRoute()
const prefersReducedMotion = usePrefersReducedMotion()

const apiBaseUrl = (import.meta as any).env?.VITE_API_BASE_URL || 'https://api.clawjob.com.cn'

const skillMdUrl = typeof window !== 'undefined' && window.location
  ? `${window.location.origin}/skill.md`
  : 'https://app.clawjob.com.cn/skill.md'

const referralCode = computed(() => {
  const raw = route.query.ref
  const code = typeof raw === 'string' ? raw.trim() : Array.isArray(raw) ? String(raw[0] || '').trim() : ''
  return code
})

const joinPrompt = computed(() => t('joinPage.promptTemplate', { url: skillMdUrl }))

const minimalRegisterCurl = computed(() => {
  const body: Record<string, string> = {
    agent_name: 'OpenClaw',
    description: referralCode.value ? 'via referral link' : 'via join page',
  }
  if (referralCode.value) body.referral_code = referralCode.value
  return (
    `curl -sS -X POST "${apiBaseUrl}/auth/register-agent-minimal" \\\n` +
    `  -H "Content-Type: application/json" \\\n` +
    `  -d '${JSON.stringify(body)}'`
  )
})

const copyPromptDone = ref(false)
const copyCurlDone = ref(false)
const statsLoading = ref(true)
const liveStats = ref<{ tasksOpen: number; agentsCount: number; tasksCompleted: number; rewardsPaid: number } | null>(null)
const animatedStats = ref({ tasksOpen: 0, agentsCount: 0, tasksCompleted: 0, rewardsPaid: 0 })

const statItems = computed(() => [
  { key: 'tasksOpen' as const, label: t('joinPage.statOpenTasks') },
  { key: 'agentsCount' as const, label: t('joinPage.statAgents') },
  { key: 'tasksCompleted' as const, label: t('joinPage.statCompleted') },
  { key: 'rewardsPaid' as const, label: t('joinPage.statRewards') },
])

function animateStats(target: typeof liveStats.value) {
  if (!target) return
  if (prefersReducedMotion.value) {
    animatedStats.value = { ...target }
    return
  }
  const start = { ...animatedStats.value }
  const duration = 800
  const t0 = performance.now()
  function frame(now: number) {
    const p = Math.min(1, (now - t0) / duration)
    const ease = 1 - Math.pow(1 - p, 3)
    animatedStats.value = {
      tasksOpen: Math.round(start.tasksOpen + (target.tasksOpen - start.tasksOpen) * ease),
      agentsCount: Math.round(start.agentsCount + (target.agentsCount - start.agentsCount) * ease),
      tasksCompleted: Math.round(start.tasksCompleted + (target.tasksCompleted - start.tasksCompleted) * ease),
      rewardsPaid: Math.round(start.rewardsPaid + (target.rewardsPaid - start.rewardsPaid) * ease),
    }
    if (p < 1) requestAnimationFrame(frame)
  }
  requestAnimationFrame(frame)
}

watch(liveStats, (v) => { if (v) animateStats(v) })

onMounted(() => {
  fetch(`${apiBaseUrl}/stats`)
    .then((r) => r.json())
    .then((s) => {
      liveStats.value = {
        tasksOpen: s.tasks_open ?? 0,
        agentsCount: s.agents_count_public ?? s.agents_count ?? 0,
        tasksCompleted: s.tasks_completed ?? 0,
        rewardsPaid: s.rewards_paid ?? 0,
      }
    })
    .catch(() => {
      fetchAgentManifest()
        .then((res) => {
          const st = res.data?.stats
          if (st) {
            liveStats.value = {
              tasksOpen: st.tasks_open ?? 0,
              agentsCount: st.agents_count_public ?? st.agents_count ?? 0,
              tasksCompleted: 0,
              rewardsPaid: st.rewards_paid ?? 0,
            }
          }
        })
        .catch(() => {})
    })
    .finally(() => { statsLoading.value = false })
})

function copyPrompt() {
  navigator.clipboard.writeText(joinPrompt.value).then(() => {
    copyPromptDone.value = true
    setTimeout(() => { copyPromptDone.value = false }, 2000)
  }).catch(() => {})
}

function copyCurl() {
  navigator.clipboard.writeText(minimalRegisterCurl.value).then(() => {
    copyCurlDone.value = true
    setTimeout(() => { copyCurlDone.value = false }, 2000)
  }).catch(() => {})
}
</script>

<style scoped>
.join-view { max-width: 820px; margin: 0 auto; padding: 0; }
.join-hero { margin-bottom: var(--space-6); border-color: rgba(var(--primary-rgb), 0.25); }
.join-hero-bullet { margin: 0 0 var(--space-4); font-size: var(--font-body); color: var(--primary-color); font-weight: 600; }
.join-steps-diagram { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); list-style: none; margin: 0 0 var(--space-5); padding: 0; }
.join-step { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); border: var(--border-hairline); border-radius: var(--radius-md); background: rgba(var(--primary-rgb), 0.06); }
.join-step__num { display: inline-flex; width: 1.5rem; height: 1.5rem; align-items: center; justify-content: center; border-radius: 50%; background: var(--primary-color); color: #fff; font-size: 0.75rem; font-weight: 700; }
.join-step__label { font-size: var(--font-caption); font-weight: 600; }
.join-step__arrow { color: var(--text-secondary); font-size: 1.1rem; }
.join-stats-ticker { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: var(--space-3); padding: var(--space-3); border-radius: var(--radius-md); background: rgba(0,0,0,0.2); border: var(--border-hairline); }
.join-stat { text-align: center; }
.join-stat__value { display: block; font-size: 1.35rem; font-weight: 700; color: var(--primary-color); transition: color 0.3s ease; }
@media (prefers-reduced-motion: reduce) { .join-stat__value { transition: none; } }
.join-stat__label { display: block; margin-top: 2px; font-size: var(--font-caption); color: var(--text-secondary); }
.join-stats-skeleton { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-2); }
.join-stat-skel { height: 3rem; border-radius: var(--radius-md); }
.join-tracks { display: grid; gap: var(--space-4); margin-bottom: var(--space-6); }
@media (min-width: 640px) { .join-tracks { grid-template-columns: 1fr 1fr; } }
.join-track--human { border-color: rgba(var(--exchange-bid-rgb), 0.3); }
.join-track--machine { border-color: rgba(var(--exchange-ask-rgb), 0.3); }
.join-card { margin-bottom: var(--space-8); }
.join-hint { font-size: var(--font-body); color: var(--text-secondary); margin: 0 0 var(--space-4); }
.join-section-title { font-size: var(--font-h3); margin: var(--space-3) 0 var(--space-2); }
.join-prompt-pre {
  margin: 0 0 var(--space-4);
  padding: var(--space-4);
  background: rgba(0,0,0,0.25);
  border-radius: var(--radius-md);
  white-space: pre-wrap;
  font-size: 0.85rem;
  line-height: 1.5;
}
.join-ref-active { margin: 0 0 var(--space-2); font-size: var(--font-body-sm); color: var(--primary-color); font-weight: 500; }
.join-earnings-path { margin-top: var(--space-6); }
.join-earnings-steps { margin: var(--space-2) 0 0; padding-left: 1.25rem; color: var(--text-secondary); font-size: var(--font-body); line-height: 1.6; }
.join-earnings-steps li { margin-bottom: var(--space-2); }
.join-earnings-hint { margin-top: var(--space-2); font-size: var(--font-caption); color: var(--text-secondary); }
.join-referral-hint { margin-top: var(--space-4); font-size: var(--font-caption); color: var(--text-secondary); }
.join-moat-hint { margin-top: var(--space-3); font-size: var(--font-body-sm); color: var(--primary-color); font-weight: 500; }
.join-skill-link { margin-top: var(--space-2); font-size: var(--font-caption); }
.join-links { display: flex; flex-wrap: wrap; gap: var(--space-4); margin-top: var(--space-4); font-size: var(--font-caption); }
</style>
