<template>
  <div v-if="events?.length" class="task-timeline-panel">
    <h4 class="task-comments-title">{{ t(titleKey) }}</h4>
    <ul class="task-timeline-list">
      <li v-for="(ev, ei) in events" :key="ei" class="task-timeline-item">
        <div class="task-timeline-row">
          <span class="task-timeline-time mono">{{ formatTime(ev.at) }}</span>
          <span v-if="ev.type" class="task-timeline-type">{{ typeLabel(ev.type) }}</span>
        </div>
        <span class="task-timeline-summary">{{ ev.summary }}</span>
      </li>
    </ul>
    <div v-if="$slots.default" class="task-timeline-panel__footer">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { safeT } from '../i18n'
import { formatTaskRelativeTime, timelineEventTypeLabel } from '../utils/taskTimeline'

export type TaskTimelineEvent = { at: string; type: string; summary: string }

withDefaults(
  defineProps<{
    events: TaskTimelineEvent[] | undefined | null
    titleKey?: string
  }>(),
  { titleKey: 'task.flowTimelineTitle' },
)

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

function formatTime(iso: string | null) {
  return formatTaskRelativeTime(t, iso)
}
function typeLabel(type: string) {
  return timelineEventTypeLabel(t, type)
}
</script>

<style scoped>
.task-comments-title {
  font-size: var(--font-section-title);
  font-weight: 650;
  letter-spacing: var(--tracking-normal);
  color: var(--text-primary);
  margin: 0 0 var(--space-4);
  line-height: 1.25;
}
.task-timeline-panel {
  margin-top: var(--space-4);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: var(--border-hairline);
  background: rgba(255, 255, 255, 0.02);
}
.task-timeline-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.task-timeline-item {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  font-size: var(--font-small);
}
.task-timeline-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.4rem 0.6rem;
}
.task-timeline-time {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}
.task-timeline-type {
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
}
.task-timeline-summary {
  color: var(--text-secondary);
}
.task-timeline-panel__footer {
  margin-top: var(--space-3);
}
</style>
