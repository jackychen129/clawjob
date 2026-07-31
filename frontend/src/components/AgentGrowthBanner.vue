<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = withDefaults(defineProps<{
  count: number
  goal?: number
}>(), {
  goal: 10000,
})

const { t } = useI18n()

const pct = computed(() => {
  if (!props.goal) return 0
  return Math.min(100, Math.round((props.count / props.goal) * 1000) / 10)
})
</script>

<template>
  <div class="agent-growth-banner card" role="status" aria-live="polite">
    <div class="agent-growth-banner__head">
      <span class="agent-growth-banner__label">{{ t('growth.agentGoalLabel') || '平台 Agent 规模' }}</span>
      <span class="agent-growth-banner__nums mono">{{ count.toLocaleString() }} / {{ goal.toLocaleString() }}</span>
    </div>
    <div class="agent-growth-banner__track" aria-hidden="true">
      <div class="agent-growth-banner__fill" :style="{ width: pct + '%' }" />
    </div>
    <p class="agent-growth-banner__hint">
      {{ t('growth.agentGoalHint', { pct, goal: goal.toLocaleString() }) || `目标 ${goal.toLocaleString()} Agent 生态 · 已完成 ${pct}%` }}
    </p>
  </div>
</template>

<style scoped>
.agent-growth-banner {
  padding: var(--space-4) var(--space-5);
  margin-bottom: var(--space-6);
  border: var(--border-hairline);
  border-radius: var(--radius-xl);
  background: linear-gradient(135deg, rgba(99,102,241,0.08) 0%, var(--card-background) 55%);
}
.agent-growth-banner__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--space-3);
  flex-wrap: wrap;
  margin-bottom: var(--space-3);
}
.agent-growth-banner__label { font-size: var(--font-caption); font-weight: 600; color: var(--text-secondary); }
.agent-growth-banner__nums { font-size: var(--font-body-strong); font-weight: 700; color: var(--text-primary); }
.agent-growth-banner__track {
  height: 8px;
  border-radius: 999px;
  background: rgba(255,255,255,0.06);
  overflow: hidden;
}
.agent-growth-banner__fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #6366f1, #22c55e);
  transition: width 0.4s var(--ease-apple);
}
.agent-growth-banner__hint {
  margin: var(--space-2) 0 0;
  font-size: var(--font-caption);
  color: var(--text-secondary);
}
</style>
