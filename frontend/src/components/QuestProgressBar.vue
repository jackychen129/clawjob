<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from './ui/button'
import { useQuestProgress } from '../composables/useQuestProgress'
import { cn } from '../lib/utils'

const { t } = useI18n()
const { steps, activeIndex, visible, dismiss } = useQuestProgress()

function stateFor(i: number): 'done' | 'current' | 'upcoming' {
  if (i < activeIndex.value) return 'done'
  if (i === activeIndex.value) return 'current'
  return 'upcoming'
}
</script>

<template>
  <div v-if="visible" class="quest-progress" role="navigation" :aria-label="t('questProgress.aria')">
    <div class="quest-progress__head">
      <span class="quest-progress__title">{{ t('questProgress.title') }}</span>
      <Button type="button" size="sm" variant="ghost" class="quest-progress__dismiss" @click="dismiss">
        {{ t('questProgress.dismiss') }}
      </Button>
    </div>
    <ol class="quest-progress__steps">
      <li
        v-for="(step, i) in steps"
        :key="step.id"
        class="quest-progress__step"
        :class="`quest-progress__step--${stateFor(i)}`"
      >
        <RouterLink
          :to="step.to"
          class="quest-progress__link"
          :aria-current="stateFor(i) === 'current' ? 'step' : undefined"
        >
          <span class="quest-progress__num" aria-hidden="true">{{ i + 1 }}</span>
          <span class="quest-progress__label">{{ t(step.labelKey) }}</span>
        </RouterLink>
        <span
          v-if="i < steps.length - 1"
          :class="cn('quest-progress__rail', stateFor(i) === 'done' && 'quest-progress__rail--done')"
          aria-hidden="true"
        />
      </li>
    </ol>
    <p class="quest-progress__hint">{{ t('questProgress.hint') }}</p>
  </div>
</template>

<style scoped>
.quest-progress {
  margin: 0 0 var(--space-5);
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-lg);
  border: var(--border-hairline);
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.08), rgba(255, 255, 255, 0.02));
}
.quest-progress__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.quest-progress__title {
  font-size: var(--font-caption);
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--text-secondary);
  text-transform: uppercase;
}
.quest-progress__dismiss {
  color: var(--text-tertiary);
}
.quest-progress__steps {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-2);
  list-style: none;
  margin: 0;
  padding: 0;
}
.quest-progress__step {
  position: relative;
  min-width: 0;
}
.quest-progress__link {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.35rem;
  text-decoration: none;
  color: inherit;
  min-width: 0;
}
.quest-progress__num {
  display: inline-flex;
  width: 1.5rem;
  height: 1.5rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-secondary);
}
.quest-progress__label {
  font-size: var(--font-caption);
  font-weight: 600;
  color: var(--text-secondary);
  line-height: 1.3;
  word-break: break-word;
}
.quest-progress__step--done .quest-progress__num {
  background: rgba(34, 197, 94, 0.2);
  border-color: rgba(34, 197, 94, 0.45);
  color: #bbf7d0;
}
.quest-progress__step--current .quest-progress__num {
  background: var(--primary-color);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 0 0 3px rgba(var(--primary-rgb), 0.22);
}
.quest-progress__step--current .quest-progress__label {
  color: var(--text-primary);
}
.quest-progress__rail {
  display: none;
}
.quest-progress__hint {
  margin: var(--space-3) 0 0;
  font-size: var(--font-caption);
  color: var(--text-secondary);
  line-height: 1.45;
}
@media (max-width: 640px) {
  .quest-progress__steps {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
