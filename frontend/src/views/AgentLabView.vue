<template>
  <section class="agent-lab">
    <h1 class="page-title">Agent Lab</h1>
    <p class="page-desc">Experiment presets for execution strategy and safety defaults.</p>

    <div class="card lab-card">
      <div class="field">
        <label>Execution Mode</label>
        <select v-model="form.executionMode" class="input select-input">
          <option value="safe">safe</option>
          <option value="balanced">balanced</option>
          <option value="aggressive">aggressive</option>
        </select>
      </div>
      <div class="field">
        <label>Retry Attempts</label>
        <input v-model.number="form.retryAttempts" type="number" min="0" max="10" class="input" />
      </div>
      <div class="field">
        <label>
          <input v-model="form.requirePreflight" type="checkbox" />
          Require preflight before task execution
        </label>
      </div>
      <div class="actions">
        <button type="button" class="btn" @click="save">Save Preset</button>
        <button type="button" class="btn btn-ghost" @click="reset">Reset</button>
      </div>
      <pre v-if="savedJson" class="saved mono">{{ savedJson }}</pre>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'

const STORAGE_KEY = 'clawjob_agent_lab_preset'
const savedJson = ref('')
const form = reactive({
  executionMode: 'balanced',
  retryAttempts: 3,
  requirePreflight: true,
})

function save() {
  const payload = {
    executionMode: form.executionMode,
    retryAttempts: Number(form.retryAttempts) || 0,
    requirePreflight: !!form.requirePreflight,
    updatedAt: new Date().toISOString(),
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  savedJson.value = JSON.stringify(payload, null, 2)
}

function reset() {
  form.executionMode = 'balanced'
  form.retryAttempts = 3
  form.requirePreflight = true
  localStorage.removeItem(STORAGE_KEY)
  savedJson.value = ''
}

try {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (raw) {
    const parsed = JSON.parse(raw) as Record<string, unknown>
    if (typeof parsed.executionMode === 'string') form.executionMode = parsed.executionMode
    if (typeof parsed.retryAttempts === 'number') form.retryAttempts = parsed.retryAttempts
    if (typeof parsed.requirePreflight === 'boolean') form.requirePreflight = parsed.requirePreflight
    savedJson.value = JSON.stringify(parsed, null, 2)
  }
} catch {}
</script>

<style scoped>
.agent-lab { display: grid; gap: var(--space-5); }
.page-desc { margin: 0; color: var(--text-secondary); }
.lab-card { padding: var(--space-5); display: grid; gap: var(--space-4); }
.field { display: grid; gap: var(--space-2); }
.actions { display: flex; gap: var(--space-2); }
.btn { border: var(--border-hairline); border-radius: var(--radius-md); padding: .4rem .7rem; background: rgba(255,255,255,.08); color: var(--text-primary); }
.btn-ghost { background: rgba(255,255,255,.03); color: var(--text-secondary); }
.saved { margin: 0; font-size: 12px; }
</style>
