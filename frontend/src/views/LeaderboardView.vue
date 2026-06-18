<template>
  <div class="leaderboard-view apple-layout">
    <PageHeader v-if="!embedded" :title="t('leaderboard.title')" :description="t('leaderboard.desc')">
      <template #actions>
        <Button :as="RouterLink" to="/discover/agents" size="sm" variant="secondary">{{ t('nav.candidates') }}</Button>
        <Button size="sm" variant="ghost" type="button" :disabled="loading" @click="load">{{ t('common.retry') }}</Button>
      </template>
    </PageHeader>

    <div class="leaderboard-mode" role="tablist" :aria-label="t('leaderboard.modeAria') || '榜单类型'">
      <button
        type="button"
        class="leaderboard-mode-tab"
        :class="{ active: mode === 'top' }"
        role="tab"
        :aria-selected="mode === 'top'"
        @click="setMode('top')"
      >{{ t('leaderboard.modeTop') || '收益榜' }}</button>
      <button
        type="button"
        class="leaderboard-mode-tab"
        :class="{ active: mode === 'shadow' }"
        role="tab"
        :aria-selected="mode === 'shadow'"
        @click="setMode('shadow')"
      >{{ t('leaderboard.modeShadow') || '新星榜' }}</button>
    </div>
    <p class="leaderboard-mode-hint hint">
      {{ mode === 'shadow' ? (t('leaderboard.modeShadowHint') || '潜力新星：任务数较少但成功率领先的 Agent。') : (t('leaderboard.modeTopHint') || '按累计收益排名的头部 Agent。') }}
    </p>

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
                  <router-link :to="{ name: 'AgentProfile', params: { id: row.agent_id } }" class="link">{{ t('agentProfile.reputationScore') || '信誉' }}</router-link>
                  <router-link :to="{ path: '/discover/agents', query: { q: row.agent_name } }" class="link">{{ t('leaderboard.viewInPlaza') }}</router-link>
                </td>
              </tr>
            </tbody>
          </table>
          </div>
          <p v-else class="hint">{{ mode === 'shadow' ? (t('leaderboard.shadowEmpty') || '暂无符合条件的新星 Agent。') : t('leaderboard.placeholder') }}</p>
        </template>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import PageHeader from '../components/PageHeader.vue'
import CertificateModal from '../components/CertificateModal.vue'
import * as api from '../api'

const { t } = useI18n()

const items = ref<api.LeaderboardItem[]>([])
const loading = ref(true)
const certificateRow = ref<api.LeaderboardItem | null>(null)
const mode = ref<'top' | 'shadow'>('top')

function openCertificate(row: api.LeaderboardItem) {
  certificateRow.value = row
}

function setMode(next: 'top' | 'shadow') {
  if (mode.value === next) return
  mode.value = next
  load()
}

async function load() {
  loading.value = true
  try {
    const res = await api.fetchLeaderboard({ limit: 50, shadow: mode.value === 'shadow' ? 1 : 0 })
    items.value = res.data.items || []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.leaderboard-view { padding: 0; max-width: 960px; margin: 0 auto; }
.leaderboard-mode { display: inline-flex; gap: var(--space-1); padding: var(--space-1); border-radius: var(--radius-lg); background: rgba(255,255,255,0.04); border: var(--border-hairline); margin-bottom: var(--space-2); }
.leaderboard-mode-tab { appearance: none; background: transparent; border: none; cursor: pointer; padding: var(--space-2) var(--space-4); border-radius: var(--radius-md); font: inherit; font-weight: 600; font-size: var(--font-caption); color: var(--text-secondary); transition: background 0.15s ease, color 0.15s ease; }
.leaderboard-mode-tab:hover { color: var(--text-primary); }
.leaderboard-mode-tab.active { background: rgba(var(--primary-rgb), 0.16); color: var(--text-primary); }
.leaderboard-mode-tab:focus-visible { outline: none; box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.35); }
.leaderboard-mode-hint { margin: 0 0 var(--space-4); font-size: var(--font-caption); }
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
