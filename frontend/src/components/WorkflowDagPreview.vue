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
      <p v-if="svgTitle" class="wf-dag-preview__svg-cap">{{ svgTitle }}</p>
      <div v-if="orderedNodes.length" class="wf-dag-preview__svg-wrap" aria-hidden="true">
        <svg
          class="wf-dag-preview__svg"
          :viewBox="`0 0 ${svgW} ${svgH}`"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <marker :id="arrowMarkerId" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
              <path d="M0,0 L8,4 L0,8 z" fill="rgba(148, 163, 184, 0.85)" />
            </marker>
          </defs>
          <line
            v-for="(ln, li) in svgLines"
            :key="'ln-' + li"
            :x1="ln.x1"
            :y1="ln.y1"
            :x2="ln.x2"
            :y2="ln.y2"
            stroke="rgba(148, 163, 184, 0.55)"
            stroke-width="1.5"
            :marker-end="arrowMarkerRef"
          />
          <g v-for="n in orderedNodes" :key="'g-' + n">
            <circle
              :cx="nodePos.get(n)!.x"
              :cy="nodePos.get(n)!.y"
              r="18"
              :fill="n === taskId ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255,255,255,0.04)'"
              :stroke="n === taskId ? 'rgba(96, 165, 250, 0.75)' : 'rgba(148, 163, 184, 0.45)'"
              stroke-width="1.25"
            />
            <text
              :x="nodePos.get(n)!.x"
              :y="nodePos.get(n)!.y + 4"
              text-anchor="middle"
              fill="currentColor"
              class="wf-dag-preview__svg-label"
            >{{ nodeLabelPrefix }}{{ n }}</text>
          </g>
        </svg>
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
    /** 可选：SVG 示意图标题（i18n） */
    svgTitle?: string
  }>(),
  {
    emptyText: '未绑定工作流 DAG',
    readyLabel: '可执行',
    blockedLabel: '有依赖未就绪',
    blockedDetailLabel: '阻塞来自任务',
    edgesTitle: '依赖边',
    nodeLabelPrefix: '#',
    svgTitle: '',
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

const orderedNodes = computed(() => {
  const seen = new Set<number>()
  const out: number[] = []
  for (const n of topoDisplay.value) {
    if (!seen.has(n)) {
      seen.add(n)
      out.push(n)
    }
  }
  const missing = nodeList.value.filter((n) => !seen.has(n)).sort((a, b) => a - b)
  for (const n of missing) out.push(n)
  return out
})

const nodeSpacing = 96
const nodeY = 44

const nodePos = computed(() => {
  const m = new Map<number, { x: number; y: number }>()
  orderedNodes.value.forEach((n, i) => {
    m.set(n, { x: 52 + i * nodeSpacing, y: nodeY })
  })
  return m
})

const svgW = computed(() => Math.max(orderedNodes.value.length * nodeSpacing + 32, 120))
const svgH = computed(() => 88)

const svgLines = computed(() => {
  const d = props.dag
  if (!d || !Array.isArray(d.edges)) return []
  const pos = nodePos.value
  const lines: { x1: number; y1: number; x2: number; y2: number }[] = []
  for (const e of d.edges) {
    const from = Number(e.from)
    const to = Number(e.to)
    const p1 = pos.get(from)
    const p2 = pos.get(to)
    if (!p1 || !p2) continue
    lines.push({
      x1: p1.x + 16,
      y1: p1.y,
      x2: p2.x - 16,
      y2: p2.y,
    })
  }
  return lines
})

const edgeLines = computed(() => {
  const d = props.dag
  if (!d || !Array.isArray(d.edges)) return []
  return d.edges.map((e) => `${props.nodeLabelPrefix}${e.from} → ${props.nodeLabelPrefix}${e.to}`)
})

const arrowMarkerId = computed(() => `wf-arrow-${props.taskId}`)
const arrowMarkerRef = computed(() => `url(#${arrowMarkerId.value})`)
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
.wf-dag-preview__svg-cap {
  margin: 0;
  font-size: var(--font-caption);
  font-weight: 600;
  color: var(--text-secondary);
}
.wf-dag-preview__svg-wrap {
  width: 100%;
  overflow-x: auto;
  border: var(--border-hairline);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-primary);
}
.wf-dag-preview__svg {
  display: block;
  min-width: 100%;
  height: auto;
  min-height: 5.5rem;
}
.wf-dag-preview__svg-label {
  font-size: 11px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
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
