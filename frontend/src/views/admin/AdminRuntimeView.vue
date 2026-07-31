<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '../../components/ui/button'
import CircuitOpenDialog from '../../components/admin/CircuitOpenDialog.vue'
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import * as api from '../../api'
import { safeT } from '../../i18n'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

const cbLoading = ref(false)
const cbRows = ref<Array<{ host: string; state: string; consecutive_failures: number; open_until?: string | null }>>([])
const cbControlLoading = ref<string | null>(null)
const cbThreshold = ref(0)
const cbOpenSeconds = ref(0)
const cbHostFilter = ref('')
const cbStateFilter = ref('')
const cbConfigThreshold = ref(3)
const cbConfigOpenSeconds = ref(60)
const cbConfigSaving = ref(false)
const cbConfigError = ref('')

type CircuitOp = { host: string; action: 'reset' | 'open' | 'half_open' | 'close'; at: string }
const circuitOpHistory = ref<CircuitOp[]>([])
const CIRCUIT_OPS_KEY = 'clawjob_admin_circuit_ops'

const confirmOpen = ref(false)
const confirmHost = ref('')

const filteredCbRows = computed(() => {
  const hostQ = cbHostFilter.value.toLowerCase()
  const stateQ = cbStateFilter.value
  return cbRows.value.filter((r) => {
    if (hostQ && !String(r.host || '').toLowerCase().includes(hostQ)) return false
    if (stateQ && String(r.state || '') !== stateQ) return false
    return true
  })
})

function loadCircuitOpHistory() {
  try {
    const raw = localStorage.getItem(CIRCUIT_OPS_KEY)
    circuitOpHistory.value = raw ? (JSON.parse(raw) as CircuitOp[]).slice(0, 20) : []
  } catch {
    circuitOpHistory.value = []
  }
}

function pushCircuitOp(host: string, action: CircuitOp['action']) {
  const item: CircuitOp = { host, action, at: new Date().toISOString().slice(0, 19).replace('T', ' ') }
  const next = [item, ...circuitOpHistory.value].slice(0, 20)
  circuitOpHistory.value = next
  try { localStorage.setItem(CIRCUIT_OPS_KEY, JSON.stringify(next)) } catch { /* ignore */ }
}

function clearCircuitOpHistory() {
  circuitOpHistory.value = []
  try { localStorage.removeItem(CIRCUIT_OPS_KEY) } catch { /* ignore */ }
}

function reload() {
  cbLoading.value = true
  api.getRuntimeCircuitBreakers()
    .then((res) => {
      cbRows.value = res.data.items || []
      cbThreshold.value = Number(res.data.threshold || 0)
      cbOpenSeconds.value = Number(res.data.open_seconds || 0)
      cbConfigThreshold.value = cbThreshold.value
      cbConfigOpenSeconds.value = cbOpenSeconds.value
    })
    .catch(() => { cbRows.value = [] })
    .finally(() => { cbLoading.value = false })
}

function saveCircuitConfig() {
  cbConfigError.value = ''
  cbConfigSaving.value = true
  api.patchRuntimeCircuitBreakerConfig({
    threshold: Math.max(1, Math.floor(cbConfigThreshold.value || 3)),
    open_seconds: Math.max(5, Math.floor(cbConfigOpenSeconds.value || 60)),
  })
    .then((res) => {
      cbThreshold.value = res.data.threshold
      cbOpenSeconds.value = res.data.open_seconds
      reload()
    })
    .catch((e: unknown) => {
      const ax = e as { response?: { data?: { detail?: string } } }
      cbConfigError.value = ax.response?.data?.detail || String(e)
    })
    .finally(() => { cbConfigSaving.value = false })
}

function controlBreaker(host: string, action: 'reset' | 'open' | 'half_open' | 'close') {
  if (action === 'open') {
    confirmHost.value = host
    confirmOpen.value = true
    return
  }
  runControl(host, action)
}

function runControl(host: string, action: 'reset' | 'open' | 'half_open' | 'close') {
  cbControlLoading.value = host
  api.controlRuntimeCircuitBreaker({ host, action })
    .then(() => { pushCircuitOp(host, action); reload() })
    .finally(() => { cbControlLoading.value = null; confirmOpen.value = false })
}

onMounted(() => {
  loadCircuitOpHistory()
  reload()
})
</script>

<template>
  <div class="admin-page">
    <AdminPageHeader
      :title="t('admin.nav.runtime') || 'Runtime 熔断'"
      :description="t('admin.circuitRuntimeHint', { n: cbThreshold, s: cbOpenSeconds })"
    />

    <Card>
      <CardHeader>
        <div class="admin-panel__head">
          <CardTitle>{{ t('admin.circuitBreakersTitle') }}</CardTitle>
          <div class="admin-cb-actions">
            <input v-model.trim="cbHostFilter" class="input admin-cb-filter" type="text" :placeholder="t('admin.circuitFilterHost')" />
            <select v-model="cbStateFilter" class="input select-input admin-cb-filter">
              <option value="">{{ t('admin.circuitFilterAll') }}</option>
              <option value="open">open</option>
              <option value="half_open">half_open</option>
              <option value="closed">closed</option>
            </select>
            <Button size="sm" variant="secondary" type="button" :disabled="cbLoading" @click="reload">{{ cbLoading ? '…' : t('admin.circuitRefresh') }}</Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
    <div class="admin-cb-config" style="display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; margin-bottom: var(--space-4)">
      <label class="hint">{{ t('admin.circuitConfigThreshold') }}</label>
      <input v-model.number="cbConfigThreshold" class="input" type="number" min="1" max="50" style="width: 5rem" />
      <label class="hint">{{ t('admin.circuitConfigOpenSeconds') }}</label>
      <input v-model.number="cbConfigOpenSeconds" class="input" type="number" min="5" max="3600" style="width: 5rem" />
      <Button size="sm" type="button" :disabled="cbConfigSaving" @click="saveCircuitConfig">{{ cbConfigSaving ? '…' : t('admin.circuitConfigSave') }}</Button>
      <p v-if="cbConfigError" class="error-msg">{{ cbConfigError }}</p>
    </div>
    <div class="admin-log-table">
      <div class="admin-log-row admin-log-row--head">
        <div>Host</div>
        <div>State</div>
        <div>Failures</div>
        <div>Open Until</div>
      </div>
      <div v-for="row in filteredCbRows" :key="row.host" class="admin-log-row">
        <div class="admin-log-cat">{{ row.host }}</div>
        <div class="admin-log-level">{{ row.state }}</div>
        <div class="admin-log-level">{{ row.consecutive_failures }}</div>
        <div class="admin-log-time">
          <div>{{ row.open_until || '-' }}</div>
          <div class="admin-dispute-actions" style="margin-top:6px">
            <Button size="sm" type="button" variant="secondary" :disabled="cbControlLoading === row.host" @click="controlBreaker(row.host, 'open')">{{ t('admin.circuitOpen') }}</Button>
            <Button size="sm" type="button" variant="secondary" :disabled="cbControlLoading === row.host" @click="controlBreaker(row.host, 'reset')">{{ t('admin.circuitReset') }}</Button>
            <Button size="sm" type="button" variant="secondary" :disabled="cbControlLoading === row.host" @click="controlBreaker(row.host, 'half_open')">{{ t('admin.circuitHalfOpen') }}</Button>
            <Button size="sm" type="button" :disabled="cbControlLoading === row.host" @click="controlBreaker(row.host, 'close')">{{ t('admin.circuitClose') }}</Button>
          </div>
        </div>
      </div>
      <p v-if="!filteredCbRows.length && !cbLoading" class="empty">暂无熔断记录</p>
    </div>
    <div class="admin-cb-history">
      <div class="admin-cb-history__head">
        <h4 class="admin-cb-history__title">{{ t('admin.circuitOpsHistory') }}</h4>
        <Button size="sm" variant="ghost" type="button" @click="clearCircuitOpHistory">{{ t('admin.circuitClearHistory') }}</Button>
      </div>
      <ul v-if="circuitOpHistory.length" class="admin-cb-history__list">
        <li v-for="(it, i) in circuitOpHistory" :key="`${it.host}-${it.action}-${i}`" class="admin-cb-history__item mono">{{ it.at }} · {{ it.host }} · {{ it.action }}</li>
      </ul>
      <p v-else class="hint">{{ t('admin.circuitHistoryEmpty') }}</p>
    </div>
    <CircuitOpenDialog
      v-model:open="confirmOpen"
      :host="confirmHost"
      :loading="cbControlLoading === confirmHost"
      @confirm="runControl(confirmHost, 'open')"
    />
      </CardContent>
    </Card>
  </div>
</template>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: var(--space-6); }
</style>
