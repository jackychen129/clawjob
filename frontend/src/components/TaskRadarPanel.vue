<template>
  <div class="task-radar">
    <div class="radar-header">
      <div>
        <div class="radar-title">{{ t('radar.title') }}</div>
        <div class="radar-subtitle" v-if="agentName">
          {{ t('radar.subtitle', { name: agentName, score: repScore }) }}
        </div>
      </div>
      <div class="radar-actions">
        <button class="radar-btn" :disabled="loading" @click="refresh(true)">
          {{ loading ? t('radar.refreshing') : t('radar.refresh') }}
        </button>
        <button class="radar-btn ghost" @click="showWeights = !showWeights">
          {{ showWeights ? t('radar.hideWeights') : t('radar.tuneWeights') }}
        </button>
      </div>
    </div>

    <div v-if="showWeights" class="weights-panel">
      <div v-for="key in weightKeys" :key="key" class="weight-row">
        <label>{{ t('radar.weights.' + key) }}</label>
        <input
          type="range"
          min="0"
          max="5"
          step="0.5"
          v-model.number="localWeights[key]"
          @change="onWeightChange"
        />
        <span class="weight-value">{{ localWeights[key].toFixed(1) }}</span>
      </div>
      <div class="weight-row preset-row">
        <button class="preset-btn" @click="applyPreset('default')">{{ t('radar.presets.default') }}</button>
        <button class="preset-btn" @click="applyPreset('skill')">{{ t('radar.presets.skill') }}</button>
        <button class="preset-btn" @click="applyPreset('reward')">{{ t('radar.presets.reward') }}</button>
        <button class="preset-btn" @click="applyPreset('fresh')">{{ t('radar.presets.fresh') }}</button>
      </div>
    </div>

    <div v-if="error" class="radar-error">{{ error }}</div>

    <div v-if="!loading && !radar.length && !error" class="radar-empty">
      {{ t('radar.empty') }}
    </div>

    <div class="radar-pool-hint" v-if="radar.length">
      {{ t('radar.poolHint', { total: totalPool, shown: radar.length }) }}
    </div>

    <div class="radar-list">
      <div
        v-for="item in radar"
        :key="item.task.id"
        class="radar-item"
        :class="{ invited: item.task.invited_for_me }"
      >
        <div class="radar-score" :style="{ background: scoreColor(item.score) }">
          <div class="score-num">{{ Math.round(item.score) }}</div>
          <div class="score-label">{{ t('radar.scoreLabel') }}</div>
        </div>
        <div class="radar-body">
          <div class="radar-item-head">
            <span v-if="item.task.invited_for_me" class="invited-tag">{{ t('radar.invitedTag') }}</span>
            <a class="task-title-link" :href="`#/tasks/${item.task.id}`" target="_blank">
              {{ item.task.title || `#${item.task.id}` }}
            </a>
            <span class="reward-chip">{{ item.task.reward_points }} pts</span>
            <span v-if="item.task.category" class="cat-chip">{{ item.task.category }}</span>
          </div>
          <div class="radar-item-desc" v-if="item.task.description">
            {{ item.task.description }}
          </div>
          <div class="radar-item-tags" v-if="item.task.skills && item.task.skills.length">
            <span class="skill-chip" v-for="s in item.task.skills.slice(0, 6)" :key="s">{{ s }}</span>
          </div>
          <div class="radar-breakdown">
            <span v-for="(v, k) in item.breakdown" :key="k" class="bd-chip" :title="t('radar.weights.' + k)">
              {{ t('radar.short.' + k) }} {{ Math.round(v * 100) }}
            </span>
            <span v-for="r in item.reasons" :key="r" class="reason-chip">{{ t('radar.reasons.' + r, r) }}</span>
          </div>
          <div class="radar-item-foot">
            <span class="bid-hint">{{ t('radar.suggestedBid', { n: item.suggested_bid }) }}</span>
            <span class="time-hint" v-if="item.task.created_at">{{ formatTime(item.task.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import * as api from '../api'
import type { TaskRadarItem } from '../api'

const props = defineProps<{
  agentId: number
  autoLoad?: boolean
  defaultK?: number
}>()

const emit = defineEmits<{ (e: 'loaded', payload: { total: number; count: number }): void }>()

const { t } = useI18n()
const loading = ref(false)
const error = ref('')
const radar = ref<TaskRadarItem[]>([])
const totalPool = ref(0)
const agentName = ref('')
const repScore = ref(0)
const showWeights = ref(false)

const weightKeys = ['skill_match', 'reward_fit', 'freshness', 'history_affinity'] as const

const storageKey = computed(() => `clawjob_radar_weights_v1_${props.agentId}`)

const localWeights = reactive<Record<string, number>>({
  skill_match: 2,
  reward_fit: 1,
  freshness: 1,
  history_affinity: 1,
})

function loadStoredWeights() {
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (raw) {
      const obj = JSON.parse(raw)
      for (const k of weightKeys) {
        const v = Number(obj?.[k])
        if (Number.isFinite(v) && v >= 0 && v <= 5) localWeights[k] = v
      }
    }
  } catch {
    // ignore
  }
}

function saveWeights() {
  try {
    localStorage.setItem(storageKey.value, JSON.stringify(localWeights))
  } catch {
    // ignore
  }
}

function onWeightChange() {
  saveWeights()
  refresh(false)
}

function applyPreset(kind: 'default' | 'skill' | 'reward' | 'fresh') {
  if (kind === 'default') {
    Object.assign(localWeights, { skill_match: 2, reward_fit: 1, freshness: 1, history_affinity: 1 })
  } else if (kind === 'skill') {
    Object.assign(localWeights, { skill_match: 3, reward_fit: 1, freshness: 0.5, history_affinity: 2 })
  } else if (kind === 'reward') {
    Object.assign(localWeights, { skill_match: 1, reward_fit: 3, freshness: 0.5, history_affinity: 0.5 })
  } else if (kind === 'fresh') {
    Object.assign(localWeights, { skill_match: 1, reward_fit: 1, freshness: 3, history_affinity: 0.5 })
  }
  saveWeights()
  refresh(false)
}

function scoreColor(score: number): string {
  if (score >= 85) return 'linear-gradient(135deg,#10b981,#059669)'
  if (score >= 70) return 'linear-gradient(135deg,#3b82f6,#2563eb)'
  if (score >= 50) return 'linear-gradient(135deg,#f59e0b,#d97706)'
  return 'linear-gradient(135deg,#6b7280,#4b5563)'
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    const diffMs = Date.now() - d.getTime()
    const m = Math.floor(diffMs / 60000)
    if (m < 1) return t('radar.justNow')
    if (m < 60) return t('radar.minutesAgo', { n: m })
    const h = Math.floor(m / 60)
    if (h < 24) return t('radar.hoursAgo', { n: h })
    const days = Math.floor(h / 24)
    return t('radar.daysAgo', { n: days })
  } catch {
    return iso
  }
}

async function refresh(manual = false) {
  if (!props.agentId) return
  loading.value = true
  error.value = ''
  try {
    const params = {
      k: props.defaultK ?? 10,
      w_skill: localWeights.skill_match,
      w_reward: localWeights.reward_fit,
      w_fresh: localWeights.freshness,
      w_history: localWeights.history_affinity,
    }
    const r = await api.getAgentTaskRadar(props.agentId, params)
    radar.value = r.data.radar || []
    totalPool.value = r.data.total_pool || 0
    agentName.value = r.data.agent_name || ''
    repScore.value = r.data.agent_reputation_score || 0
    emit('loaded', { total: totalPool.value, count: radar.value.length })
  } catch (e: any) {
    if (manual || radar.value.length === 0) {
      error.value = e?.response?.data?.detail || e?.message || t('radar.errorGeneric')
    }
  } finally {
    loading.value = false
  }
}

watch(() => props.agentId, () => {
  loadStoredWeights()
  if (props.autoLoad !== false) refresh(false)
})

onMounted(() => {
  loadStoredWeights()
  if (props.autoLoad !== false) refresh(false)
})
</script>

<style scoped>
.task-radar {
  background: var(--color-card, #fff);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.radar-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.radar-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text, #111827);
}

.radar-subtitle {
  font-size: 12px;
  color: var(--color-text-muted, #6b7280);
  margin-top: 2px;
}

.radar-actions {
  display: flex;
  gap: 8px;
}

.radar-btn {
  border: 1px solid #3b82f6;
  background: #3b82f6;
  color: #fff;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.radar-btn:hover:not(:disabled) { opacity: 0.9; }
.radar-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.radar-btn.ghost {
  background: transparent;
  color: #3b82f6;
}

.weights-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: rgba(59, 130, 246, 0.05);
  border: 1px dashed rgba(59, 130, 246, 0.3);
  border-radius: 8px;
}

.weight-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--color-text, #374151);
}

.weight-row label { flex: 0 0 120px; }
.weight-row input[type='range'] { flex: 1; }
.weight-value { flex: 0 0 36px; text-align: right; font-variant-numeric: tabular-nums; }

.preset-row {
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 6px;
}

.preset-btn {
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 11px;
  cursor: pointer;
}
.preset-btn:hover { background: #f3f4f6; }

.radar-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  padding: 10px;
  border-radius: 8px;
  font-size: 13px;
}

.radar-empty {
  padding: 24px;
  text-align: center;
  color: var(--color-text-muted, #6b7280);
  font-size: 13px;
  background: #f9fafb;
  border-radius: 8px;
}

.radar-pool-hint {
  font-size: 11px;
  color: var(--color-text-muted, #6b7280);
}

.radar-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.radar-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 10px;
  transition: transform 0.15s, box-shadow 0.15s;
  background: var(--color-card, #fff);
}

.radar-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
}

.radar-item.invited {
  border-color: #8b5cf6;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.05), transparent);
}

.radar-score {
  min-width: 64px;
  height: 64px;
  border-radius: 10px;
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}
.score-num { font-size: 20px; font-weight: 800; line-height: 1; }
.score-label { font-size: 10px; opacity: 0.9; }

.radar-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.radar-item-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.task-title-link {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text, #111827);
  text-decoration: none;
}
.task-title-link:hover { text-decoration: underline; }

.reward-chip {
  background: #fef3c7;
  color: #92400e;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.cat-chip {
  background: #e0e7ff;
  color: #3730a3;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
}

.invited-tag {
  background: #8b5cf6;
  color: #fff;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.radar-item-desc {
  font-size: 12px;
  color: var(--color-text-muted, #4b5563);
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.radar-item-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.skill-chip {
  background: #f3f4f6;
  color: #374151;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
}

.radar-breakdown {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  font-size: 10px;
}

.bd-chip {
  background: #f0f9ff;
  color: #0369a1;
  padding: 2px 6px;
  border-radius: 4px;
  font-variant-numeric: tabular-nums;
}

.reason-chip {
  background: #f0fdf4;
  color: #15803d;
  padding: 2px 6px;
  border-radius: 4px;
}

.radar-item-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: var(--color-text-muted, #6b7280);
}

.bid-hint { font-weight: 600; color: #d97706; }

@media (max-width: 640px) {
  .radar-item { flex-direction: column; }
  .radar-score { min-width: 100%; height: 48px; flex-direction: row; gap: 6px; }
  .score-num { font-size: 16px; }
}
</style>
