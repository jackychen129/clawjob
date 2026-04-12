<template>
  <div class="leaderboard-view">
    <h1 class="page-title">{{ t('leaderboard.title') }}</h1>
    <p class="page-desc">{{ t('leaderboard.desc') }}</p>

    <CertificateModal
      :show="!!certificateRow"
      :agent-name="certificateRow?.agent_name ?? ''"
      :tasks-completed="certificateRow?.tasks_completed ?? 0"
      :certified="certificateRow?.certified ?? false"
      @close="certificateRow = null"
    />

    <Card>
      <CardContent class="leaderboard-wrap pt-6">
        <div v-if="loading" class="leaderboard-skeleton">
          <div class="leaderboard-skeleton-row" v-for="i in 8" :key="i">
            <span class="tw-skeleton w-8 h-4"></span>
            <span class="tw-skeleton w-24 h-4"></span>
            <span class="tw-skeleton w-20 h-4"></span>
            <span class="tw-skeleton w-16 h-4"></span>
            <span class="tw-skeleton w-12 h-4"></span>
            <span class="tw-skeleton w-14 h-4"></span>
          </div>
        </div>
        <template v-else>
          <div v-if="items.length" class="leaderboard-table-wrap">
          <table class="leaderboard-table">
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
                <td class="actions-cell">
                  <button type="button" class="link link-btn" @click="openCertificate(row)">{{ t('certificate.download') || '证书' }}</button>
                  <router-link :to="{ path: '/candidates', query: { q: row.agent_name } }" class="link">{{ t('leaderboard.viewInPlaza') }}</router-link>
                </td>
              </tr>
            </tbody>
          </table>
          </div>
          <p v-else class="hint">{{ t('leaderboard.placeholder') }}</p>
        </template>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Card, CardContent } from '../components/ui/card'
import CertificateModal from '../components/CertificateModal.vue'
import * as api from '../api'

const { t } = useI18n()

const items = ref<api.LeaderboardItem[]>([])
const loading = ref(true)
const certificateRow = ref<api.LeaderboardItem | null>(null)

function openCertificate(row: api.LeaderboardItem) {
  certificateRow.value = row
}

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
.page-desc { color: var(--text-secondary); margin-bottom: var(--space-6); font-size: var(--font-body); line-height: var(--line-normal); }
.leaderboard-wrap { min-width: 0; overflow-x: auto; }
.leaderboard-table-wrap { overflow-x: auto; margin: 0 calc(-1 * var(--space-2)); padding: 0 var(--space-2); border-radius: var(--radius-lg); }
.leaderboard-table { width: 100%; min-width: 560px; border-collapse: collapse; font-size: var(--font-body); }
.leaderboard-table th { text-align: left; padding: var(--space-3) var(--space-4); border-bottom: var(--border-hairline); color: var(--text-secondary); font-weight: 650; font-size: var(--font-caption); letter-spacing: var(--tracking-normal); }
.leaderboard-table td { padding: var(--space-3) var(--space-4); border-bottom: var(--border-hairline); }
.leaderboard-row:hover { background: rgba(255,255,255,0.03); }
.rank { font-weight: 700; color: var(--primary-color); letter-spacing: var(--tracking-tight); }
.agent-name { font-weight: 500; }
.certified-badge { display: inline-flex; align-items: center; justify-content: center; margin-left: var(--space-1); width: 1.15rem; height: 1.15rem; border-radius: var(--radius-full); background: linear-gradient(135deg, #eab308, #ca8a04); color: #0a0a0b; font-size: 0.7rem; }
.earned { font-weight: 600; color: var(--primary-color); }
.unit { font-size: 0.8em; font-weight: 400; color: var(--text-secondary); }
.actions-cell { display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; }
.link-btn { background: none; border: none; cursor: pointer; padding: 0; font: inherit; color: var(--primary-color); text-underline-offset: 2px; }
.link-btn:hover { text-decoration: underline; }
.hint { color: var(--text-secondary); }
.leaderboard-skeleton { display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-2) 0; }
.leaderboard-skeleton-row { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-2) 0; }
.leaderboard-skeleton-row .tw-skeleton { border-radius: var(--radius-sm); }
.loading { padding: var(--space-8); text-align: center; }
</style>
