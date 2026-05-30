<template>
  <div class="user-public-view">
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
          <h1 class="user-public-name">@{{ profile.username }}</h1>
          <p v-if="profile.display_name" class="user-public-display">{{ profile.display_name }}</p>
          <p v-if="profile.bio" class="user-public-bio">{{ profile.bio }}</p>
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
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
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
.user-public-view { max-width: 960px; margin: 0 auto; padding: 24px 16px; }
.user-public-skeleton { padding: 24px; }
.user-public-error { padding: 40px; text-align: center; color: #666; }
.user-public-head { display: flex; gap: 20px; align-items: flex-start; flex-wrap: wrap; }
.user-public-head__avatar { width: 84px; height: 84px; border-radius: 50%; overflow: hidden; background: linear-gradient(135deg, #60a5fa, #2563eb); display: flex; align-items: center; justify-content: center; color: #fff; font-size: 32px; font-weight: 700; flex-shrink: 0; }
.user-public-head__avatar img { width: 100%; height: 100%; object-fit: cover; }
.user-public-head__main { flex: 1 1 280px; min-width: 240px; }
.user-public-name { font-size: 24px; font-weight: 600; margin: 0; }
.user-public-display { color: #444; margin: 4px 0 0; font-size: 14px; }
.user-public-bio { margin-top: 10px; color: #333; font-size: 14px; line-height: 1.6; white-space: pre-wrap; }
.user-public-meta { color: #666; font-size: 13px; margin-top: 8px; }
.user-public-agents { margin-top: 28px; }
.user-public-agents h2 { font-size: 16px; margin-bottom: 10px; }
.user-public-agent-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
.user-public-agent-row { border: 1px solid #eee; border-radius: 12px; padding: 14px 16px; background: #fff; }
.user-public-agent-link { color: inherit; text-decoration: none; display: block; }
.user-public-agent-row__head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.user-public-agent-score { font-size: 12px; color: #92400e; background: #fef3c7; padding: 2px 8px; border-radius: 999px; }
.user-public-agent-desc { margin: 6px 0 0; color: #555; font-size: 13px; line-height: 1.5; }
.user-public-agent-meta { margin-top: 6px; color: #666; font-size: 12px; }
.hint { color: #666; font-size: 13px; }
</style>
