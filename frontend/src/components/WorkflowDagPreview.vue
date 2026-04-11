<template>
  <div class="wf-dag-preview">
    <div v-if="!dag || !nodeList.length" class="wf-dag-preview__empty">
      {{ emptyText }}
    </div>
    <template v-else>
      <div class="wf-dag-preview__badges">
        <span class="wf-dag-preview__badge" :class="ready ? 'wf-dag-preview__badge--ok' : 'wf-dag-preview__badge--block'">
          {{ ready ? readyLabel : blockedLabel }}
        </span>
        <span v-if="blockedBy.length" class="wf-dag-preview__hint">
          {{ blockedDetailLabel }}: {{ blockedBy.join(', ') }}
        </span>
      </div>
      <div class="wf-dag-preview__flow" aria-label="workflow topo">
        <template v-for="(n, i) in topoDisplay" :key="'n-' + n">
          <span
            class="wf-dag-preview__node"
            :class="{ 'wf-dag-preview__node--current': n === taskId }"
          >{{ nodeLabelPrefix }}{{ n }}</span>
          <span v-if="i < topoDisplay.length - 1" class="wf-dag-preview__arrow" aria-hidden="true">→</span>
        </template>
      </div>
      <div v-if="edgeLines.length" class="wf-dag-preview__edges">
        <div class="wf-dag-preview__edges-title">{{ edgesTitle }}</div>
        <ul class="wf-dag-preview__edge-list">
          <li v-for="(e, idx) in edgeLines" :key="'e-' + idx" class="mono">{{ e }}</li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export type WorkflowDagShape = {
  nodes: number[]
  edges: Array<{ from: number; to: number }>
  topo_order?: number[]
}

const props = withDefaults(
  defineProps<{
    taskId: number
    dag: WorkflowDagShape | null | undefined
    ready: boolean
    blockedBy: number[]
    emptyText?: string
    readyLabel?: string
    blockedLabel?: string
    blockedDetailLabel?: string
    edgesTitle?: string
    nodeLabelPrefix?: string
  }>(),
  {
    emptyText: '未绑定工作流 DAG',
    readyLabel: '可执行',
    blockedLabel: '有依赖未就绪',
    blockedDetailLabel: '阻塞来自任务',
    edgesTitle: '依赖边',
    nodeLabelPrefix: '#',
  },
)

const nodeList = computed(() => {
  const d = props.dag
  if (!d || !Array.isArray(d.nodes)) return []
  return d.nodes.map((x) => Number(x)).filter((n) => Number.isInteger(n) && n > 0)
})

const topoDisplay = computed(() => {
  const d = props.dag
  if (!d) return []
  const topo = d.topo_order
  if (Array.isArray(topo) && topo.length) {
    return topo.map((x) => Number(x)).filter((n) => Number.isInteger(n) && n > 0)
  }
  return [...nodeList.value].sort((a, b) => a - b)
})

const edgeLines = computed(() => {
  const d = props.dag
  if (!d || !Array.isArray(d.edges)) return []
  return d.edges.map((e) => `${props.nodeLabelPrefix}${e.from} → ${props.nodeLabelPrefix}${e.to}`)
})
</script>

<style scoped>
.wf-dag-preview {
  display: grid;
  gap: var(--space-3);
}
.wf-dag-preview__empty {
  font-size: var(--font-caption);
  color: var(--text-secondary);
  padding: var(--space-2) 0;
}
.wf-dag-preview__badges {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
.wf-dag-preview__badge {
  font-size: var(--font-caption);
  font-weight: 600;
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-sm);
  border: var(--border-hairline);
}
.wf-dag-preview__badge--ok {
  color: var(--primary-color, #86efac);
  border-color: rgba(134, 239, 172, 0.35);
  background: rgba(34, 197, 94, 0.12);
}
.wf-dag-preview__badge--block {
  color: var(--warning-color, #fbbf24);
  border-color: rgba(251, 191, 36, 0.35);
  background: rgba(251, 191, 36, 0.1);
}
.wf-dag-preview__hint {
  font-size: var(--font-caption);
  color: var(--text-secondary);
}
.wf-dag-preview__flow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  border: var(--border-hairline);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.03);
}
.wf-dag-preview__node {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: var(--font-caption);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  border: var(--border-hairline);
  color: var(--text-secondary);
}
.wf-dag-preview__node--current {
  color: var(--text-primary);
  border-color: rgba(96, 165, 250, 0.45);
  background: rgba(59, 130, 246, 0.12);
}
.wf-dag-preview__arrow {
  color: var(--text-secondary);
  font-size: 0.85rem;
}
.wf-dag-preview__edges-title {
  font-size: var(--font-caption);
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: var(--space-1);
}
.wf-dag-preview__edge-list {
  margin: 0;
  padding-left: 1.1rem;
  font-size: var(--font-caption);
  color: var(--text-secondary);
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
</style>
