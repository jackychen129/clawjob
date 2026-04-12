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
        <Button type="button" variant="ghost" @click="reset">{{ t('agentLab.reset') }}</Button>
      </div>
      <p v-if="savedJson" class="saved-hint">{{ t('agentLab.savedHint') }}</p>
      <pre v-if="savedJson" class="saved mono">{{ savedJson }}</pre>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'

const { t } = useI18n()
const STORAGE_KEY = 'clawjob_agent_lab_preset'
const STORAGE_DARK = 'clawjob_agent_lab_dark'
const savedJson = ref('')
const darkUi = ref(false)
const form = reactive({
  executionMode: 'balanced',
  retryAttempts: 3,
  requirePreflight: true,
})

function persistDark() {
  try {
    localStorage.setItem(STORAGE_DARK, darkUi.value ? '1' : '0')
  } catch {}
}

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

function copyPreset() {
  if (!savedJson.value) return
  try {
    void navigator.clipboard.writeText(savedJson.value)
  } catch {}
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
      if (typeof parsed.executionMode === 'string') form.executionMode = parsed.executionMode
      if (typeof parsed.retryAttempts === 'number') form.retryAttempts = parsed.retryAttempts
      if (typeof parsed.requirePreflight === 'boolean') form.requirePreflight = parsed.requirePreflight
      savedJson.value = JSON.stringify(parsed, null, 2)
    }
  } catch {}
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
.saved-hint { margin: 0; font-size: var(--font-caption); color: var(--text-secondary); }
.saved { margin: 0; font-size: 12px; padding: var(--space-3); border-radius: var(--radius-md); border: var(--border-hairline); background: rgba(255, 255, 255, 0.03); overflow: auto; }
.agent-lab--dark .lab-card {
  background: rgba(0, 0, 0, 0.35);
  border-color: rgba(255, 255, 255, 0.08);
}
.agent-lab--dark .page-desc { color: rgba(255, 255, 255, 0.65); }
</style>
