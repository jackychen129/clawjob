<template>
  <section class="agent-lab apple-layout" :class="{ 'agent-lab--dark': darkUi }">
    <div class="agent-lab__head">
      <div>
        <h1 class="page-title">{{ t('agentLab.title') }}</h1>
        <p class="page-desc">{{ t('agentLab.desc') }}</p>
      </div>
      <label class="agent-lab__dark">
        <input v-model="darkUi" type="checkbox" class="rounded border-input" @change="persistDark" />
        {{ t('agentLab.darkMode') }}
      </label>
    </div>

    <div class="card lab-card">
      <div class="field">
        <label class="form-label">{{ t('agentLab.executionMode') }}</label>
        <select v-model="form.executionMode" class="input select-input">
          <option value="safe">{{ t('agentLab.modeSafe') }}</option>
          <option value="balanced">{{ t('agentLab.modeBalanced') }}</option>
          <option value="aggressive">{{ t('agentLab.modeAggressive') }}</option>
        </select>
      </div>
      <div class="field">
        <label class="form-label">{{ t('agentLab.retryAttempts') }}</label>
        <input v-model.number="form.retryAttempts" type="number" min="0" max="10" class="input" />
      </div>
      <div class="field">
        <label class="form-label flex items-center gap-2">
          <input v-model="form.requirePreflight" type="checkbox" class="rounded border-input" />
          {{ t('agentLab.requirePreflight') }}
        </label>
      </div>
      <div class="actions">
        <Button type="button" @click="save">{{ t('agentLab.savePreset') }}</Button>
        <Button type="button" variant="secondary" :disabled="!savedJson" @click="copyPreset">{{ t('agentLab.copyPreset') }}</Button>
        <Button type="button" variant="secondary" :disabled="!savedJson" @click="exportPreset">{{ t('agentLab.exportPreset') }}</Button>
        <Button type="button" variant="ghost" @click="reset">{{ t('agentLab.reset') }}</Button>
      </div>
      <div class="field">
        <label class="form-label">{{ t('agentLab.importPreset') }}</label>
        <textarea v-model="importText" class="input import-textarea" rows="4" :placeholder="t('agentLab.importPlaceholder')" />
        <div class="actions">
          <Button type="button" variant="secondary" :disabled="!importText.trim()" @click="importPreset">{{ t('agentLab.importApply') }}</Button>
        </div>
      </div>
      <p v-if="notice" class="saved-hint">{{ notice }}</p>
      <p v-if="savedJson" class="saved-hint">{{ t('agentLab.savedHint') }}</p>
      <pre v-if="savedJson" class="saved mono">{{ savedJson }}</pre>
    </div>

    <div class="card lab-card">
      <div class="history-head">
        <h3 class="history-title">{{ t('agentLab.historyTitle') }}</h3>
        <Button size="sm" type="button" variant="ghost" :disabled="!history.length" @click="clearHistory">{{ t('agentLab.historyClear') }}</Button>
      </div>
      <p v-if="!history.length" class="saved-hint">{{ t('agentLab.historyEmpty') }}</p>
      <div v-else class="history-list">
        <button v-for="h in history" :key="h.id" type="button" class="history-item mono" @click="restoreFromHistory(h.id)">
          {{ formatHistoryTitle(h) }}
        </button>
      </div>
    </div>

    <div class="card lab-card">
      <div class="history-head">
        <h3 class="history-title">{{ t('agentLab.diffTitle') }}</h3>
      </div>
      <div class="diff-pick">
        <select v-model="diffA" class="input select-input">
          <option value="">{{ t('agentLab.diffPickA') }}</option>
          <option v-for="h in history" :key="`a-${h.id}`" :value="h.id">{{ formatHistoryTitle(h) }}</option>
        </select>
        <select v-model="diffB" class="input select-input">
          <option value="">{{ t('agentLab.diffPickB') }}</option>
          <option v-for="h in history" :key="`b-${h.id}`" :value="h.id">{{ formatHistoryTitle(h) }}</option>
        </select>
      </div>
      <p v-if="!diffRows.length" class="saved-hint">{{ t('agentLab.diffEmpty') }}</p>
      <ul v-else class="diff-list mono">
        <li v-for="r in diffRows" :key="r.key" class="diff-row">
          <span class="diff-key">{{ r.key }}</span>
          <span class="diff-from">{{ r.from }}</span>
          <span class="diff-arrow">→</span>
          <span class="diff-to">{{ r.to }}</span>
        </li>
      </ul>
    </div>

    <div class="card lab-card">
      <div class="history-head">
        <h3 class="history-title">{{ t('agentLab.runTitle') }}</h3>
      </div>
      <div class="run-grid">
        <select v-model="runType" class="input select-input">
          <option value="use_tool">{{ t('agentLab.runTypeUseTool') }}</option>
          <option value="execute_task">{{ t('agentLab.runTypeExecuteTask') }}</option>
        </select>
        <select v-if="runType === 'use_tool'" v-model.number="runAgentId" class="input select-input">
          <option :value="0">{{ t('agentLab.pickAgent') }}</option>
          <option v-for="a in myAgents" :key="a.id" :value="a.id">#{{ a.id }} · {{ a.name }}</option>
        </select>
        <select v-else v-model.number="runTaskId" class="input select-input">
          <option :value="0">{{ t('agentLab.pickTask') }}</option>
          <option v-for="task in myTasks" :key="task.id" :value="task.id">#{{ task.id }} · {{ task.title }}</option>
        </select>
        <input v-if="runType === 'use_tool'" v-model.trim="runToolName" class="input" type="text" :placeholder="t('agentLab.toolName')" />
        <input v-else v-model.number="runRetryCount" class="input" type="number" min="0" max="3" :placeholder="t('agentLab.runRetry')" />
      </div>
      <textarea
        v-if="runType === 'use_tool'"
        v-model="runToolParams"
        class="input import-textarea"
        rows="4"
        :placeholder="t('agentLab.toolParams')"
      />
      <div class="actions">
        <Button type="button" :disabled="running" @click="runNow">{{ running ? '…' : (t('agentLab.runNow') || '运行') }}</Button>
      </div>
      <pre v-if="runResult" class="saved mono">{{ runResult }}</pre>
    </div>

    <div class="card lab-card">
      <div class="history-head">
        <h3 class="history-title">{{ t('agentLab.runHistoryTitle') }}</h3>
        <div class="actions">
          <Button size="sm" type="button" variant="secondary" :disabled="!runHistory.length" @click="exportReport">{{ t('agentLab.exportReport') }}</Button>
          <Button size="sm" type="button" variant="ghost" :disabled="!runHistory.length" @click="clearRunHistory">{{ t('agentLab.historyClear') }}</Button>
        </div>
      </div>
      <div class="run-filters">
        <input v-model.trim="runFilterQuery" class="input" type="search" :placeholder="t('agentLab.runFilterPlaceholder')" />
        <select v-model="runFilterKind" class="input select-input">
          <option value="">{{ t('agentLab.runFilterKindAll') }}</option>
          <option value="use_tool">{{ t('agentLab.runTypeUseTool') }}</option>
          <option value="execute_task">{{ t('agentLab.runTypeExecuteTask') }}</option>
        </select>
        <select v-model="runFilterStatus" class="input select-input">
          <option value="">{{ t('agentLab.runFilterStatusAll') }}</option>
          <option value="ok">{{ t('agentLab.runFilterStatusOk') }}</option>
          <option value="failed">{{ t('agentLab.runFilterStatusFailed') }}</option>
        </select>
      </div>
      <p v-if="!filteredRunHistory.length" class="saved-hint">{{ t('agentLab.runHistoryEmpty') }}</p>
      <div v-else class="history-list">
        <div v-for="r in filteredRunHistory" :key="r.id" class="run-item">
          <button type="button" class="history-item mono run-item__title" @click="openRun(r.id)">
            {{ formatRunTitle(r) }}
          </button>
          <div class="actions">
            <Button size="sm" type="button" variant="secondary" :disabled="running" @click="replayRun(r.id)">{{ t('agentLab.replay') }}</Button>
          </div>
        </div>
      </div>
    </div>

    <div class="card lab-card">
      <div class="history-head">
        <h3 class="history-title">{{ t('agentLab.resultDiffTitle') }}</h3>
      </div>
      <div class="diff-pick">
        <select v-model="runDiffA" class="input select-input">
          <option value="">{{ t('agentLab.resultDiffPickA') }}</option>
          <option v-for="r in runHistory" :key="`ra-${r.id}`" :value="r.id">{{ formatRunTitle(r) }}</option>
        </select>
        <select v-model="runDiffB" class="input select-input">
          <option value="">{{ t('agentLab.resultDiffPickB') }}</option>
          <option v-for="r in runHistory" :key="`rb-${r.id}`" :value="r.id">{{ formatRunTitle(r) }}</option>
        </select>
      </div>
      <p v-if="!runDiffRows.length" class="saved-hint">{{ t('agentLab.resultDiffEmpty') }}</p>
      <ul v-else class="diff-list mono">
        <li v-for="r in runDiffRows" :key="r.key" class="diff-row">
          <span class="diff-key">{{ r.key }}</span>
          <span class="diff-from">{{ r.from }}</span>
          <span class="diff-arrow">→</span>
          <span class="diff-to">{{ r.to }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import * as api from '../api'

const { t } = useI18n()
const STORAGE_KEY = 'clawjob_agent_lab_preset'
const STORAGE_DARK = 'clawjob_agent_lab_dark'
const STORAGE_HISTORY = 'clawjob_agent_lab_history'
const STORAGE_RUN_HISTORY = 'clawjob_agent_lab_run_history'
const savedJson = ref('')
const darkUi = ref(false)
const notice = ref('')
const importText = ref('')
type Preset = {
  id: string
  executionMode: string
  retryAttempts: number
  requirePreflight: boolean
  updatedAt: string
}
const history = ref<Preset[]>([])
type RunItem = {
  id: string
  at: string
  kind: 'use_tool' | 'execute_task'
  ok: boolean
  summary: string
  snapshot: Preset
  payload: Record<string, unknown>
  result: unknown
}
const runHistory = ref<RunItem[]>([])
const form = reactive({
  executionMode: 'balanced',
  retryAttempts: 3,
  requirePreflight: true,
})
const diffA = ref('')
const diffB = ref('')
const runDiffA = ref('')
const runDiffB = ref('')
const runFilterQuery = ref('')
const runFilterKind = ref<'' | 'use_tool' | 'execute_task'>('')
const runFilterStatus = ref<'' | 'ok' | 'failed'>('')
const runType = ref<'use_tool' | 'execute_task'>('use_tool')
const runAgentId = ref(0)
const runTaskId = ref(0)
const runToolName = ref('search_knowledge_base')
const runToolParams = ref('{\n  "query": "test",\n  "top_k": 3\n}')
const runRetryCount = ref(1)
const running = ref(false)
const runResult = ref('')
const myAgents = ref<Array<{ id: number; name: string }>>([])
const myTasks = ref<Array<{ id: number; title: string }>>([])

const diffRows = computed(() => {
  const a = history.value.find((x) => x.id === diffA.value)
  const b = history.value.find((x) => x.id === diffB.value)
  if (!a || !b) return []
  const keys: Array<keyof Preset> = ['executionMode', 'retryAttempts', 'requirePreflight', 'updatedAt']
  return keys
    .filter((k) => String(a[k]) !== String(b[k]))
    .map((k) => ({ key: String(k), from: String(a[k]), to: String(b[k]) }))
})

const filteredRunHistory = computed(() => {
  const q = runFilterQuery.value.toLowerCase()
  const kind = runFilterKind.value
  const status = runFilterStatus.value
  return runHistory.value.filter((r) => {
    if (kind && r.kind !== kind) return false
    if (status === 'ok' && !r.ok) return false
    if (status === 'failed' && r.ok) return false
    if (!q) return true
    const hay = `${r.id} ${r.kind} ${r.summary} ${JSON.stringify(r.payload)}`.toLowerCase()
    return hay.includes(q)
  })
})

function flattenObject(obj: unknown, prefix = '', out: Record<string, string> = {}): Record<string, string> {
  if (obj === null || obj === undefined) {
    out[prefix || '(root)'] = String(obj)
    return out
  }
  if (typeof obj !== 'object') {
    out[prefix || '(root)'] = typeof obj === 'string' ? obj : JSON.stringify(obj)
    return out
  }
  if (Array.isArray(obj)) {
    if (obj.length === 0) {
      out[prefix || '(root)'] = '[]'
      return out
    }
    obj.forEach((v, i) => flattenObject(v, prefix ? `${prefix}[${i}]` : `[${i}]`, out))
    return out
  }
  const entries = Object.entries(obj as Record<string, unknown>)
  if (entries.length === 0) {
    out[prefix || '(root)'] = '{}'
    return out
  }
  for (const [k, v] of entries) {
    flattenObject(v, prefix ? `${prefix}.${k}` : k, out)
  }
  return out
}

const runDiffRows = computed(() => {
  const a = runHistory.value.find((x) => x.id === runDiffA.value)
  const b = runHistory.value.find((x) => x.id === runDiffB.value)
  if (!a || !b) return []
  const fa = flattenObject(a.result)
  const fb = flattenObject(b.result)
  const keys = Array.from(new Set([...Object.keys(fa), ...Object.keys(fb)])).sort()
  const rows: Array<{ key: string; from: string; to: string }> = []
  for (const k of keys) {
    const va = fa[k] ?? '(missing)'
    const vb = fb[k] ?? '(missing)'
    if (va !== vb) rows.push({ key: k, from: String(va), to: String(vb) })
  }
  return rows.slice(0, 200)
})

function persistDark() {
  try {
    localStorage.setItem(STORAGE_DARK, darkUi.value ? '1' : '0')
  } catch {}
}

function save() {
  const payload = buildPayload()
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch {}
  savedJson.value = JSON.stringify(payload, null, 2)
  pushHistory(payload)
  notice.value = String(t('agentLab.savedHint'))
}

function buildPayload(): Preset {
  return {
    id: `${Date.now()}_${Math.random().toString(16).slice(2, 8)}`,
    executionMode: form.executionMode,
    retryAttempts: Number(form.retryAttempts) || 0,
    requirePreflight: !!form.requirePreflight,
    updatedAt: new Date().toISOString(),
  }
}

function reset() {
  form.executionMode = 'balanced'
  form.retryAttempts = 3
  form.requirePreflight = true
  localStorage.removeItem(STORAGE_KEY)
  savedJson.value = ''
  notice.value = ''
  importText.value = ''
}

function copyPreset() {
  if (!savedJson.value) return
  try {
    void navigator.clipboard.writeText(savedJson.value)
    notice.value = String(t('agentLab.copied'))
  } catch {}
}

function exportPreset() {
  if (!savedJson.value) return
  try {
    const blob = new Blob([savedJson.value], { type: 'application/json;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `agent-lab-preset-${new Date().toISOString().replace(/[:.]/g, '-')}.json`
    a.click()
    URL.revokeObjectURL(a.href)
    notice.value = String(t('agentLab.exported'))
  } catch {}
}

function importPreset() {
  try {
    const parsed = JSON.parse(importText.value) as Record<string, unknown>
    applyPreset(parsed)
    save()
    notice.value = String(t('agentLab.imported'))
  } catch {
    notice.value = String(t('agentLab.importError'))
  }
}

function applyPreset(parsed: Record<string, unknown>) {
  const mode = typeof parsed.executionMode === 'string' ? parsed.executionMode : 'balanced'
  const retry = Number(parsed.retryAttempts || 0)
  const preflight = Boolean(parsed.requirePreflight)
  form.executionMode = ['safe', 'balanced', 'aggressive'].includes(mode) ? mode : 'balanced'
  form.retryAttempts = Number.isFinite(retry) ? Math.max(0, Math.min(10, Math.round(retry))) : 0
  form.requirePreflight = preflight
}

function loadHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_HISTORY)
    if (!raw) {
      history.value = []
      return
    }
    const arr = JSON.parse(raw) as Preset[]
    history.value = Array.isArray(arr) ? arr.slice(0, 12) : []
  } catch {
    history.value = []
  }
}

function pushHistory(preset: Preset) {
  const next = [preset, ...history.value.filter((h) => h.id !== preset.id)].slice(0, 12)
  history.value = next
  try {
    localStorage.setItem(STORAGE_HISTORY, JSON.stringify(next))
  } catch {}
}

function clearHistory() {
  history.value = []
  try { localStorage.removeItem(STORAGE_HISTORY) } catch {}
}

function restoreFromHistory(id: string) {
  const hit = history.value.find((h) => h.id === id)
  if (!hit) return
  applyPreset(hit as unknown as Record<string, unknown>)
  savedJson.value = JSON.stringify(hit, null, 2)
  notice.value = String(t('agentLab.historyRestored'))
}

function loadRunHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_RUN_HISTORY)
    const arr = raw ? (JSON.parse(raw) as RunItem[]) : []
    runHistory.value = Array.isArray(arr) ? arr.slice(0, 20) : []
  } catch {
    runHistory.value = []
  }
}

function pushRunHistory(item: RunItem) {
  const next = [item, ...runHistory.value].slice(0, 20)
  runHistory.value = next
  try {
    localStorage.setItem(STORAGE_RUN_HISTORY, JSON.stringify(next))
  } catch {}
}

function clearRunHistory() {
  runHistory.value = []
  try { localStorage.removeItem(STORAGE_RUN_HISTORY) } catch {}
}

function currentPresetSnapshot(): Preset {
  return buildPayload()
}

async function runNow() {
  running.value = true
  notice.value = ''
  let ok = false
  let result: unknown = null
  let summary = ''
  const snapshot = currentPresetSnapshot()
  const payload: Record<string, unknown> = { runType: runType.value }
  try {
    if (runType.value === 'use_tool') {
      if (!runAgentId.value || !runToolName.value.trim()) throw new Error(String(t('agentLab.runMissingUseTool')))
      let params: Record<string, unknown> = {}
      try {
        params = runToolParams.value.trim() ? (JSON.parse(runToolParams.value) as Record<string, unknown>) : {}
      } catch {
        throw new Error(String(t('agentLab.runInvalidParams')))
      }
      payload.agent_id = runAgentId.value
      payload.tool_name = runToolName.value.trim()
      payload.params = params
      const res = await api.postAgentUseTool(runAgentId.value, { tool_name: runToolName.value.trim(), params })
      result = res.data
      ok = true
      summary = `tool:${runToolName.value.trim()}`
    } else {
      if (!runTaskId.value) throw new Error(String(t('agentLab.runMissingTask')))
      const retry = Math.max(0, Math.min(3, Number(runRetryCount.value || 0)))
      payload.task_id = runTaskId.value
      payload.retry_count = retry
      const res = await api.api.post(`/tasks/${runTaskId.value}/execute`, null, { params: { retry_count: retry } })
      result = res.data
      ok = true
      summary = `task:${runTaskId.value}`
    }
    runResult.value = JSON.stringify(result, null, 2)
  } catch (e: unknown) {
    const detail = (e as any)?.response?.data?.detail || String(e)
    result = { error: detail }
    runResult.value = JSON.stringify(result, null, 2)
    summary = String(detail).slice(0, 80)
  } finally {
    const item: RunItem = {
      id: `${Date.now()}_${Math.random().toString(16).slice(2, 8)}`,
      at: new Date().toISOString(),
      kind: runType.value,
      ok,
      summary,
      snapshot,
      payload,
      result,
    }
    pushRunHistory(item)
    running.value = false
  }
}

function openRun(id: string) {
  const hit = runHistory.value.find((r) => r.id === id)
  if (!hit) return
  runResult.value = JSON.stringify(hit.result, null, 2)
}

async function replayRun(id: string) {
  const hit = runHistory.value.find((r) => r.id === id)
  if (!hit) return
  applyPreset(hit.snapshot as unknown as Record<string, unknown>)
  runType.value = hit.kind
  if (hit.kind === 'use_tool') {
    runAgentId.value = Number(hit.payload.agent_id || 0)
    runToolName.value = String(hit.payload.tool_name || '')
    runToolParams.value = JSON.stringify((hit.payload.params || {}) as Record<string, unknown>, null, 2)
  } else {
    runTaskId.value = Number(hit.payload.task_id || 0)
    runRetryCount.value = Number(hit.payload.retry_count || 0)
  }
  await runNow()
}

function formatHistoryTitle(h: Preset): string {
  const when = new Date(h.updatedAt)
  const ts = Number.isNaN(when.getTime()) ? h.updatedAt : when.toLocaleString()
  return `${ts} · ${h.executionMode} · retry=${h.retryAttempts} · preflight=${h.requirePreflight ? 'on' : 'off'}`
}

function formatRunTitle(r: RunItem): string {
  const ts = new Date(r.at)
  const at = Number.isNaN(ts.getTime()) ? r.at : ts.toLocaleString()
  return `${at} · ${r.kind} · ${r.ok ? 'ok' : 'failed'} · ${r.summary || '-'}`
}

function exportReport() {
  if (!runHistory.value.length) return
  const report = {
    exported_at: new Date().toISOString(),
    agent_lab_version: 1,
    current_preset: savedJson.value ? JSON.parse(savedJson.value) : null,
    preset_history: history.value,
    runs: runHistory.value,
    timeline: runHistory.value
      .map((r) => ({ at: r.at, kind: r.kind, ok: r.ok, summary: r.summary }))
      .sort((a, b) => String(a.at).localeCompare(String(b.at))),
  }
  try {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `agent-lab-report-${new Date().toISOString().replace(/[:.]/g, '-')}.json`
    a.click()
    URL.revokeObjectURL(a.href)
    notice.value = String(t('agentLab.reportExported'))
  } catch {
    notice.value = String(t('agentLab.reportExportFailed'))
  }
}

function loadAgentsAndTasks() {
  api.fetchMyAgents()
    .then((res) => {
      const rows = ((res.data as any)?.agents || (res.data as any)?.items || res.data) as any
      const arr = Array.isArray(rows) ? rows : []
      myAgents.value = arr
        .map((a: any) => ({ id: Number(a?.id || 0), name: String(a?.name || '') }))
        .filter((a: any) => a.id > 0 && a.name)
    })
    .catch(() => { myAgents.value = [] })
  api.fetchMyAcceptedTasks({ limit: 100 })
    .then((res) => {
      const arr = (res.data?.tasks || []).map((t: any) => ({ id: Number(t.id || 0), title: String(t.title || '') }))
      myTasks.value = arr.filter((t: any) => t.id > 0)
    })
    .catch(() => { myTasks.value = [] })
}

onMounted(() => {
  try {
    const d = localStorage.getItem(STORAGE_DARK)
    darkUi.value = d === '1'
  } catch {}
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as Record<string, unknown>
      applyPreset(parsed)
      savedJson.value = JSON.stringify(parsed, null, 2)
    }
  } catch {}
  loadHistory()
  loadRunHistory()
  loadAgentsAndTasks()
})
</script>

<style scoped>
.agent-lab {
  display: grid;
  gap: var(--space-5);
  max-width: 640px;
  margin: 0 auto;
  padding: 0 0 var(--space-10);
}
.agent-lab__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.page-desc { margin: var(--space-2) 0 0; color: var(--text-secondary); line-height: 1.5; }
.agent-lab__dark {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-caption);
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
}
.agent-lab__dark input { accent-color: var(--primary-color); }
.lab-card { padding: var(--space-5); display: grid; gap: var(--space-4); }
.field { display: grid; gap: var(--space-2); }
.actions { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.import-textarea { width: 100%; min-height: 88px; resize: vertical; }
.saved-hint { margin: 0; font-size: var(--font-caption); color: var(--text-secondary); }
.saved { margin: 0; font-size: 12px; padding: var(--space-3); border-radius: var(--radius-md); border: var(--border-hairline); background: rgba(255, 255, 255, 0.03); overflow: auto; }
.history-head { display: flex; justify-content: space-between; align-items: center; gap: var(--space-2); }
.history-title { margin: 0; font-size: 1rem; }
.history-list { display: grid; gap: var(--space-2); }
.history-item {
  text-align: left;
  border: var(--border-hairline);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-secondary);
  padding: .45rem .6rem;
  font-size: .75rem;
}
.diff-pick { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-2); }
.diff-list { margin: 0; padding-left: 0; list-style: none; display: grid; gap: 6px; }
.diff-row { display: grid; grid-template-columns: 140px 1fr auto 1fr; gap: 6px; font-size: .75rem; }
.diff-key { color: var(--text-primary); }
.diff-from, .diff-to { color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.diff-arrow { color: var(--text-secondary); }
.run-grid { display: grid; grid-template-columns: 180px 1fr 1fr 180px; gap: var(--space-2); }
.run-item { display: grid; gap: var(--space-2); }
.run-item__title { width: 100%; }
.run-filters { display: grid; grid-template-columns: 1fr 160px 160px; gap: var(--space-2); }

@media (max-width: 900px) {
  .run-grid { grid-template-columns: 1fr; }
  .run-filters { grid-template-columns: 1fr; }
  .diff-pick { grid-template-columns: 1fr; }
  .diff-row { grid-template-columns: 1fr; }
}
.agent-lab--dark .lab-card {
  background: rgba(0, 0, 0, 0.35);
  border-color: rgba(255, 255, 255, 0.08);
}
.agent-lab--dark .page-desc { color: rgba(255, 255, 255, 0.65); }
</style>
