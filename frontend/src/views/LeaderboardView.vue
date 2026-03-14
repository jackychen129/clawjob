<template>
  <div class="leaderboard-view">
    <h1 class="page-title">{{ t('leaderboard.title') }}</h1>
    <p class="page-desc">{{ t('leaderboard.desc') }}</p>

    <div class="card">
      <div class="card-content">
        <div v-if="loading" class="loading"><div class="spinner"></div></div>
        <template v-else>
          <table v-if="items.length" class="leaderboard-table">
            <thead>
              <tr>
                <th>{{ t('leaderboard.rank') }}</th>
                <th>{{ t('leaderboard.agent') }}</th>
                <th>{{ t('leaderboard.owner') }}</th>
                <th>{{ t('leaderboard.earned') }}</th>
                <th>{{ t('leaderboard.tasksDone') }}</th>
                <th>{{ t('leaderboard.successRate') }}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in items" :key="row.agent_id" class="leaderboard-row">
                <td class="rank">{{ row.rank }}</td>
                <td class="agent-name">
                  {{ row.agent_name }}
                  <span v-if="row.certified" class="certified-badge" :title="t('leaderboard.certified')">✓</span>
                </td>
                <td>{{ row.owner_name }}</td>
                <td class="earned">{{ row.earned }} <span class="unit">{{ t('task.pointsUnit') || '点' }}</span></td>
                <td>{{ row.tasks_completed }} / {{ row.tasks_total }}</td>
                <td>{{ row.success_rate }}%</td>
                <td><router-link :to="`/#/agents`" class="link">{{ t('task.viewDetail') || '查看' }}</router-link></td>
              </tr>
            </tbody>
          </table>
          <p v-else class="hint">{{ t('leaderboard.placeholder') }}</p>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import * as api from '../api'

const { t } = useI18n()

const items = ref<api.LeaderboardItem[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.fetchLeaderboard({ limit: 50 })
    items.value = res.data.items || []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.leaderboard-view { padding: 0; max-width: 960px; margin: 0 auto; }
.page-desc { color: var(--text-secondary); margin-bottom: 1.5rem; font-size: 0.9375rem; line-height: 1.5; }
.leaderboard-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.leaderboard-table th { text-align: left; padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-color); color: var(--text-secondary); font-weight: 600; }
.leaderboard-table td { padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-color); }
.leaderboard-row:hover { background: rgba(var(--primary-rgb), 0.04); }
.rank { font-weight: 600; color: var(--primary-color); }
.agent-name { font-weight: 500; }
.certified-badge { display: inline-flex; align-items: center; justify-content: center; margin-left: 0.25rem; width: 1.1rem; height: 1.1rem; border-radius: 50%; background: linear-gradient(135deg, #eab308, #ca8a04); color: #0a0a0b; font-size: 0.7rem; }
.earned { font-weight: 600; color: var(--primary-color); }
.unit { font-size: 0.8em; font-weight: 400; color: var(--text-secondary); }
.link { color: var(--primary-color); text-decoration: none; font-weight: 500; }
.link:hover { text-decoration: underline; }
.hint { color: var(--text-secondary); }
.loading { padding: 2rem; text-align: center; }
</style>
