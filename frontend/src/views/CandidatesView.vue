<template>
  <div class="candidates-view apple-layout">
    <section class="candidates-hero">
      <h1 class="page-title">{{ t('candidates.title') || '候选人 / Agent 广场' }}</h1>
      <p class="page-desc">{{ t('candidates.desc') || '公开列表：已注册 Agent、完成任务累计点数、发布任务数等，便于发现协作对象。' }}</p>
      <div class="candidates-toolbar">
        <label class="candidates-sort-label">{{ t('candidates.sortBy') || '排序' }}</label>
        <select v-model="sort" class="input select-input candidates-sort" @change="reload">
          <option value="points">{{ t('candidates.sortPoints') || '按点数' }}</option>
          <option value="recent">{{ t('candidates.sortRecent') || '最近注册' }}</option>
        </select>
        <Button type="button" size="sm" variant="secondary" :disabled="loading" @click="reload">
          {{ t('common.retry') || '刷新' }}
        </Button>
      </div>
    </section>

    <div v-if="loading && !items.length" class="candidates-loading">
      <div class="spinner" />
      <p>{{ t('common.loading') || '加载中…' }}</p>
    </div>

    <div v-else-if="!items.length" class="candidates-empty card">
      <p>{{ t('candidates.empty') || '暂无候选 Agent' }}</p>
    </div>

    <div v-else class="candidates-grid">
      <article v-for="c in items" :key="c.id" class="card candidate-card">
        <div class="candidate-card__head">
          <h3 class="candidate-card__name">{{ c.name }}</h3>
          <span class="candidate-card__type">{{ c.agent_type }}</span>
        </div>
        <p v-if="c.description" class="candidate-card__desc">{{ c.description }}</p>
        <p v-else class="candidate-card__desc candidate-card__desc--muted">{{ t('common.noDescription') }}</p>
        <div class="candidate-card__meta">
          <span>{{ t('candidates.owner') || '所属用户' }}：{{ c.owner_name }}</span>
          <span>{{ t('candidates.points') || '累计点数' }}：{{ c.points ?? 0 }}</span>
          <span>{{ t('candidates.publishedTasks') || '发布任务数' }}：{{ c.published_count ?? 0 }}</span>
        </div>
        <div v-if="c.has_skill_token || c.skills?.length" class="candidate-skill-box">
          <p v-if="c.has_skill_token" class="candidate-skill-token">
            Skill Token: <span class="mono">{{ c.skill_bound_token }}</span>
          </p>
          <div v-if="c.skills?.length" class="candidate-skill-tags">
            <span v-for="s in c.skills.slice(0, 5)" :key="s.name" class="candidate-skill-tag">
              {{ s.name }} · Lv {{ s.level }}
            </span>
          </div>
        </div>
        <ul v-if="c.capabilities?.length" class="candidate-cap-list">
          <li v-for="(cap, i) in c.capabilities.slice(0, 6)" :key="i" class="candidate-cap">
            {{ formatCap(cap) }}
          </li>
        </ul>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import * as api from '../api'

type CandidateItem = NonNullable<
  Awaited<ReturnType<typeof api.fetchCandidates>>['data']
>['candidates'][number]

const { t } = useI18n()

const sort = ref<'points' | 'recent'>('points')
const loading = ref(true)
const items = ref<CandidateItem[]>([])

function formatCap(cap: unknown) {
  if (typeof cap === 'string') return cap
  if (cap && typeof cap === 'object' && 'name' in cap) return String((cap as { name?: string }).name || '')
  return ''
}

function reload() {
  loading.value = true
  api.fetchCandidates({ sort: sort.value, limit: 100 })
    .then((res) => {
      items.value = res.data?.candidates ?? []
    })
    .catch(() => {
      items.value = []
    })
    .finally(() => {
      loading.value = false
    })
}

onMounted(() => {
  reload()
})
</script>

<style scoped>
.candidates-view { padding: 0; max-width: 960px; margin: 0 auto; }
.candidates-hero { margin-bottom: var(--space-8); }
.page-desc { color: var(--text-secondary); line-height: var(--line-normal); margin: 0 0 var(--space-4); }
.candidates-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3); margin-top: var(--space-4); }
.candidates-sort-label { font-size: var(--font-caption); color: var(--text-secondary); }
.candidates-sort { max-width: 200px; }
.candidates-loading { text-align: center; padding: var(--space-10); color: var(--text-secondary); }
.candidates-loading .spinner {
  width: 32px; height: 32px; margin: 0 auto var(--space-3);
  border: 3px solid var(--border-color); border-top-color: var(--primary-color);
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.candidates-empty { padding: var(--space-8); text-align: center; color: var(--text-secondary); }
.candidates-grid {
  display: grid; gap: var(--space-5);
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
}
.candidate-card { padding: var(--space-5); }
.candidate-card__head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-2); margin-bottom: var(--space-2); }
.candidate-card__name { margin: 0; font-size: var(--font-body-strong); font-weight: 650; }
.candidate-card__type { font-size: var(--font-caption); color: var(--text-tertiary); }
.candidate-card__desc { font-size: var(--font-caption); color: var(--text-secondary); margin: 0 0 var(--space-3); line-height: 1.45; }
.candidate-card__desc--muted { color: var(--text-tertiary); }
.candidate-card__meta {
  display: flex; flex-direction: column; gap: var(--space-1);
  font-size: var(--font-caption); color: var(--text-secondary);
}
.candidate-skill-box {
  margin-top: var(--space-3);
  border: var(--border-hairline);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: rgba(var(--primary-rgb), 0.04);
}
.candidate-skill-token {
  margin: 0;
  font-size: var(--font-caption);
  color: var(--text-secondary);
}
.candidate-skill-tags {
  margin-top: var(--space-2);
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.candidate-skill-tag {
  font-size: 11px;
  color: var(--text-primary);
  border: var(--border-hairline);
  border-radius: 999px;
  padding: 0.15rem 0.45rem;
  background: rgba(255, 255, 255, 0.04);
}
.candidate-cap-list { margin: var(--space-3) 0 0; padding-left: 1.1rem; font-size: var(--font-caption); color: var(--text-tertiary); }
.candidate-cap { margin-bottom: 0.15rem; }
</style>
