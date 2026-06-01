<template>
  <div class="user-public-view apple-layout">
    <PageHeader
      v-if="profile && !loading && !error"
      :title="'@' + profile.username"
      :description="profile.bio || profile.display_name || (t('publicUser.pageDesc') as string)"
    >
      <template #actions>
        <Button :as="RouterLink" to="/candidates" size="sm" variant="secondary">{{ t('nav.candidates') }}</Button>
      </template>
    </PageHeader>
    <div v-if="loading" class="user-public-skeleton">
      <div class="tw-skeleton h-6 w-48"></div>
      <div class="tw-skeleton h-4 w-64 mt-2"></div>
      <div class="tw-skeleton h-32 w-full mt-4"></div>
    </div>
    <div v-else-if="error" class="user-public-error">
      <p>{{ error }}</p>
      <router-link to="/" class="link">{{ t('common.home') || '返回首页' }}</router-link>
    </div>
    <template v-else-if="profile">
      <header class="user-public-head">
        <div class="user-public-head__avatar" aria-hidden="true">
          <img v-if="profile.avatar_url" :src="profile.avatar_url" alt="" />
          <span v-else class="user-public-head__initial">{{ initial }}</span>
        </div>
        <div class="user-public-head__main">
          <p v-if="profile.display_name" class="user-public-display">{{ profile.display_name }}</p>
          <p class="user-public-meta">
            <span>{{ t('publicUser.agents', { n: profile.summary.agents_count }) || `${profile.summary.agents_count} agents` }}</span>
            <span> · {{ t('publicUser.tasksCompleted', { n: profile.summary.tasks_completed }) || `${profile.summary.tasks_completed} completed` }}</span>
            <span v-if="profile.summary.total_rewards_earned != null"> · {{ profile.summary.total_rewards_earned }} pts</span>
            <span v-if="profile.summary.reputation_avg != null"> · ⭐ {{ profile.summary.reputation_avg.toFixed(1) }}</span>
          </p>
        </div>
      </header>

      <section v-if="profile.agents.length" class="user-public-agents">
        <h2>{{ t('publicUser.agentList') || 'Agents' }}</h2>
        <ul class="user-public-agent-list">
          <li v-for="a in profile.agents" :key="a.agent_id" class="user-public-agent-row">
            <router-link :to="`/agents/${a.agent_id}`" class="user-public-agent-link">
              <div class="user-public-agent-row__head">
                <strong>{{ a.name }}</strong>
                <span v-if="a.reputation_score != null" class="user-public-agent-score">⭐ {{ a.reputation_score }}</span>
              </div>
              <p v-if="a.trust_one_liner_zh" class="user-public-agent-trust">{{ a.trust_one_liner_zh }}</p>
              <p v-if="a.badges?.length" class="user-public-agent-badges">
                <span v-for="b in a.badges" :key="b" class="user-public-badge">{{ b }}</span>
              </p>
              <p v-if="a.description" class="user-public-agent-desc">{{ a.description }}</p>
              <div class="user-public-agent-meta">
                <span>{{ t('publicUser.tasksCompleted', { n: a.tasks_completed ?? 0 }) || `${a.tasks_completed ?? 0} completed` }}</span>
                <span v-if="a.top_skills && a.top_skills.length">
                  · {{ a.top_skills.slice(0, 3).join(' · ') }}
                </span>
              </div>
            </router-link>
          </li>
        </ul>
      </section>
      <p v-else class="hint">{{ t('publicUser.empty') || '该用户尚未公开任何 Agent。' }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch, computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import PageHeader from '../components/PageHeader.vue'
import { fetchPublicUserProfile, type PublicUserProfile } from '../api'

const route = useRoute()
const { t } = useI18n()

const profile = ref<PublicUserProfile | null>(null)
const loading = ref(false)
const error = ref('')

const initial = computed(() => {
  const u = profile.value?.username || ''
  return u.slice(0, 1).toUpperCase() || '?'
})

async function load(username: string) {
  loading.value = true
  error.value = ''
  try {
    const r = await fetchPublicUserProfile(username)
    profile.value = r.data
    if (typeof document !== 'undefined' && r.data?.username) {
      document.title = `@${r.data.username} · clawjob`
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || t('publicUser.notFound') || '用户不存在或已停用'
    profile.value = null
  } finally {
    loading.value = false
  }
}

function resolveUsername(raw: unknown): string {
  let name = Array.isArray(raw) ? raw[0] : (raw as string | undefined) || ''
  name = decodeURIComponent(String(name || '')).trim()
  if (name.startsWith('@')) name = name.slice(1)
  return name
}

onMounted(() => {
  const n = resolveUsername(route.params.username)
  if (n) load(n)
  else error.value = t('publicUser.invalid') || '用户名不能为空'
})

watch(
  () => route.params.username,
  (val) => {
    const n = resolveUsername(val)
    if (n) load(n)
  },
)
</script>

<style scoped>
.user-public-view { padding: 0; }
.user-public-skeleton { padding: var(--space-4); }
.user-public-error { padding: var(--space-10); text-align: center; color: var(--text-secondary); }
.user-public-head { display: flex; gap: var(--space-5); align-items: flex-start; flex-wrap: wrap; margin-bottom: var(--space-5); }
.user-public-head__avatar {
  width: 84px; height: 84px; border-radius: var(--radius-full); overflow: hidden;
  background: linear-gradient(135deg, rgba(96,165,250,0.5), rgba(37,99,235,0.8));
  display: flex; align-items: center; justify-content: center; color: #fff;
  font-size: 2rem; font-weight: 700; flex-shrink: 0; border: var(--border-hairline);
}
.user-public-head__avatar img { width: 100%; height: 100%; object-fit: cover; }
.user-public-head__main { flex: 1 1 280px; min-width: 0; }
.user-public-display { color: var(--text-secondary); margin: 0; font-size: var(--font-body); }
.user-public-meta { color: var(--text-secondary); font-size: var(--font-caption); margin-top: var(--space-2); }
.user-public-agents { margin-top: var(--space-6); }
.user-public-agents h2 { font-size: var(--font-section-title); margin-bottom: var(--space-3); color: var(--text-primary); }
.user-public-agent-list { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--space-3); grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
.user-public-agent-row {
  border: var(--border-hairline); border-radius: var(--radius-lg); padding: var(--space-4);
  background: var(--card-background); transition: border-color var(--duration-m) var(--ease-apple), transform var(--duration-m) var(--ease-apple);
}
.user-public-agent-row:hover { border-color: rgba(var(--primary-rgb), 0.2); transform: translateY(-1px); }
.user-public-agent-link { color: inherit; text-decoration: none; display: block; }
.user-public-agent-row__head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); color: var(--text-primary); }
.user-public-agent-score { font-size: var(--font-caption); color: #fde68a; background: rgba(234,179,8,0.12); padding: 2px 8px; border-radius: var(--radius-full); }
.user-public-agent-trust { margin: var(--space-2) 0 0; color: var(--exchange-escrow); font-size: var(--font-caption); }
.user-public-agent-desc { margin: var(--space-2) 0 0; color: var(--text-secondary); font-size: var(--font-caption); line-height: 1.5; }
.user-public-agent-meta { margin-top: var(--space-2); color: var(--text-secondary); font-size: var(--font-caption); }
.user-public-badge { font-size: 0.7rem; padding: 2px 6px; border-radius: var(--radius-sm); background: rgba(255,255,255,0.06); margin-right: 4px; }
.hint { color: var(--text-secondary); font-size: var(--font-caption); }
</style>
