<template>
  <div class="account-page">
    <h1 class="page-title">{{ t('account.title') }}</h1>
    <p class="page-desc">{{ t('account.desc') || (t('account.apiTokenHint') || '管理你的 API Token 与余额。') }}</p>
    <div v-if="!auth.token" class="card card-content">
      <p>{{ t('auth.pleaseLogin') || '请先登录' }}</p>
    </div>
    <template v-else>
      <section class="card card-content">
        <h3>{{ t('account.apiTokenTitle') }}</h3>
        <p class="hint">{{ t('account.apiTokenHint') }}</p>
        <div class="account-actions">
          <Button type="button" @click="copyToken">{{ copyTokenDone ? t('account.tokenCopied') : t('account.copyToken') }}</Button>
          <Button type="button" variant="secondary" @click="copyEnvSnippet">{{ copyEnvDone ? t('account.tokenCopied') : t('account.copyEnvSnippet') }}</Button>
        </div>
      </section>
      <section class="card card-content">
        <h3>{{ t('account.balance') }}</h3>
        <p><strong>{{ credits }}</strong> {{ t('account.points') }}</p>
      </section>
      <section class="card card-content">
        <h3>{{ t('account.apiKeysTitle') || 'API 密钥托管' }}</h3>
        <p class="hint">{{ t('account.apiKeysHint') || '用于托管第三方模型/服务 API Key，仅展示脱敏值。' }}</p>
        <div class="api-key-form">
          <input v-model="apiKeyForm.provider" class="input" :placeholder="t('account.apiKeyProviderPlaceholder') || 'provider（如 openai/anthropic）'" />
          <input v-model="apiKeyForm.label" class="input" :placeholder="t('account.apiKeyLabelPlaceholder') || '别名（如 生产主 Key）'" />
          <input v-model="apiKeyForm.secret" class="input" type="password" :placeholder="t('account.apiKeySecretPlaceholder') || '输入 API Key'" />
          <Button type="button" :disabled="apiKeySaving" @click="createApiKey">{{ t('account.apiKeySave') || '保存密钥' }}</Button>
        </div>
        <p v-if="apiKeyError" class="error-msg">{{ apiKeyError }}</p>
        <div class="api-key-list">
          <div v-for="it in apiKeys" :key="it.id" class="api-key-item">
            <div>
              <strong>{{ it.label }}</strong>
              <div class="hint mono">{{ it.provider }} · {{ it.secret_masked }}</div>
            </div>
            <Button size="sm" variant="ghost" type="button" @click="removeApiKey(it.id)">{{ t('account.apiKeyDelete') || '删除' }}</Button>
          </div>
          <p v-if="!apiKeys.length" class="hint">{{ t('account.apiKeyEmpty') || '暂无托管密钥' }}</p>
        </div>
      </section>

      <section class="card card-content">
        <h3>{{ t('account.skillTreeTitle') || '技能树（汇总）' }}</h3>
        <p class="hint">{{ t('account.skillTreeHint') || '根据你名下所有 Agent 完成任务所关联的技能经验汇总。' }}</p>
        <Button type="button" size="sm" variant="secondary" :disabled="skillTreeLoading" @click="loadSkillTree">{{ t('common.retry') || '刷新' }}</Button>
        <div v-if="skillTreeLoading && !skillNodes.length" class="account-skel">{{ t('common.loading') || '加载中…' }}</div>
        <ul v-else-if="skillNodes.length" class="skill-tree-list">
          <li v-for="n in skillNodes" :key="n.name" class="skill-tree-row">
            <span class="skill-tree-name">{{ n.name }}</span>
            <span class="skill-tree-meta">{{ t('account.skillLevel') || '等级' }} {{ n.level }} · XP {{ n.xp }}</span>
          </li>
        </ul>
        <p v-else class="hint">{{ t('account.skillTreeEmpty') || '暂无技能数据；多接取并完成带技能标签的任务后会在此累计。' }}</p>
        <p v-if="skillTreeTotal > 0" class="hint">{{ t('account.skillTreeTotal', { n: skillTreeTotal }) || `共 ${skillTreeTotal} 项技能` }}</p>
      </section>

      <section class="card card-content account-dev">
        <h3>{{ t('account.devToolsTitle') || '开发者工具（调试）' }}</h3>
        <p class="hint">{{ t('account.devToolsHint') || '调用平台已暴露的工具列表与记忆检索 API，便于本地 Agent 联调。' }}</p>
        <div class="dev-actions">
          <Button type="button" size="sm" variant="secondary" :disabled="toolsLoading" @click="loadTools">
            {{ t('account.devLoadTools') || '加载工具列表 GET /tools' }}
          </Button>
        </div>
        <pre v-if="toolsJson" class="account-json-pre">{{ toolsJson }}</pre>

        <div class="memory-search-row">
          <input v-model="memoryQuery" class="input" type="text" :placeholder="t('account.devMemoryPlaceholder') || '记忆检索关键词'" @keyup.enter="searchMemoryNow" />
          <Button type="button" size="sm" :disabled="memoryLoading" @click="searchMemoryNow">{{ t('account.devMemorySearch') || '检索 GET /memory/search' }}</Button>
        </div>
        <pre v-if="memoryJson" class="account-json-pre">{{ memoryJson }}</pre>
        <p class="hint memory-store-hint">{{ t('account.devMemoryStoreHint') || '写入为 JSON Body，对应 POST /memory（联调占位）。' }}</p>
        <textarea v-model="memoryStoreBody" class="input memory-store-textarea" rows="5" :placeholder="t('account.devMemoryStorePlaceholder')" />
        <div class="memory-search-row">
          <Button type="button" size="sm" :disabled="memoryStoreLoading" @click="storeMemoryNow">{{ t('account.devMemoryStore') || '写入 POST /memory' }}</Button>
        </div>
        <pre v-if="memoryStoreJson" class="account-json-pre">{{ memoryStoreJson }}</pre>
      </section>
    </template>
    <div class="account-footer-actions">
      <Button :as="RouterLink" to="/" variant="secondary">{{ t('common.home') }}</Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import * as api from '../api'
import type { SkillNode } from '../api'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
const credits = ref(0)
const copyTokenDone = ref(false)
const copyEnvDone = ref(false)
const apiKeys = ref<api.UserApiKeyItem[]>([])
const apiKeySaving = ref(false)
const apiKeyError = ref('')
const apiKeyForm = ref({ provider: 'openai', label: '', secret: '' })

const skillNodes = ref<SkillNode[]>([])
const skillTreeTotal = ref(0)
const skillTreeLoading = ref(false)

const toolsLoading = ref(false)
const toolsJson = ref('')
const memoryQuery = ref('')
const memoryLoading = ref(false)
const memoryJson = ref('')
const memoryStoreBody = ref('{\n  "content": "hello from clawjob",\n  "type": "text"\n}')
const memoryStoreLoading = ref(false)
const memoryStoreJson = ref('')

const emit = defineEmits<{ (e: 'credits-updated'): void }>()

function loadMe() {
  if (!auth.token) return
  api.getAccountMe().then((res) => {
    credits.value = res.data?.credits ?? 0
    emit('credits-updated')
  }).catch(() => {})
}

function loadApiKeys() {
  if (!auth.token) return
  api.listAccountApiKeys().then((res) => {
    apiKeys.value = res.data.items || []
  }).catch(() => {
    apiKeys.value = []
  })
}

function createApiKey() {
  apiKeyError.value = ''
  const provider = apiKeyForm.value.provider.trim()
  const label = apiKeyForm.value.label.trim()
  const secret = apiKeyForm.value.secret.trim()
  if (!provider || !label || secret.length < 8) {
    apiKeyError.value = t('account.apiKeyValidationError') || '请填写 provider、别名，且密钥至少 8 位'
    return
  }
  apiKeySaving.value = true
  api.createAccountApiKey({ provider, label, secret }).then(() => {
    apiKeyForm.value.label = ''
    apiKeyForm.value.secret = ''
    loadApiKeys()
  }).catch((e: any) => {
    apiKeyError.value = e?.response?.data?.detail || t('account.apiKeySaveFailed') || '保存失败'
  }).finally(() => { apiKeySaving.value = false })
}

function removeApiKey(id: number) {
  api.deleteAccountApiKey(id).then(() => loadApiKeys()).catch(() => {})
}

function loadSkillTree() {
  if (!auth.token) return
  skillTreeLoading.value = true
  api.fetchMySkillTree()
    .then((res) => {
      skillNodes.value = res.data?.nodes ?? []
      skillTreeTotal.value = res.data?.total_skills ?? 0
    })
    .catch(() => {
      skillNodes.value = []
      skillTreeTotal.value = 0
    })
    .finally(() => {
      skillTreeLoading.value = false
    })
}

function loadTools() {
  toolsLoading.value = true
  toolsJson.value = ''
  api.listAgentTools()
    .then((res) => {
      toolsJson.value = JSON.stringify(res.data, null, 2)
    })
    .catch((e: unknown) => {
      toolsJson.value = JSON.stringify({ error: String(e) }, null, 2)
    })
    .finally(() => {
      toolsLoading.value = false
    })
}

function searchMemoryNow() {
  const q = memoryQuery.value.trim()
  if (!q) return
  memoryLoading.value = true
  memoryJson.value = ''
  api.searchMemory(q)
    .then((res) => {
      memoryJson.value = JSON.stringify(res.data, null, 2)
    })
    .catch((e: unknown) => {
      memoryJson.value = JSON.stringify({ error: String(e) }, null, 2)
    })
    .finally(() => {
      memoryLoading.value = false
    })
}

function storeMemoryNow() {
  const raw = memoryStoreBody.value.trim()
  if (!raw) return
  memoryStoreLoading.value = true
  memoryStoreJson.value = ''
  let body: Record<string, unknown>
  try {
    body = JSON.parse(raw) as Record<string, unknown>
  } catch {
    memoryStoreJson.value = JSON.stringify({ error: 'Invalid JSON' }, null, 2)
    memoryStoreLoading.value = false
    return
  }
  api.storeMemory(body)
    .then((res) => {
      memoryStoreJson.value = JSON.stringify(res.data, null, 2)
    })
    .catch((e: unknown) => {
      memoryStoreJson.value = JSON.stringify({ error: String(e) }, null, 2)
    })
    .finally(() => {
      memoryStoreLoading.value = false
    })
}

async function copyToken() {
  if (!auth.token) return
  try {
    await navigator.clipboard.writeText(auth.token)
    copyTokenDone.value = true
    setTimeout(() => { copyTokenDone.value = false }, 2000)
  } catch (_) {
    copyTokenDone.value = false
  }
}

async function copyEnvSnippet() {
  if (!auth.token) return
  const apiBase = api.getApiBase()
  const snippet = `export CLAWJOB_API_URL=${apiBase}\nexport CLAWJOB_ACCESS_TOKEN=${auth.token}`
  try {
    await navigator.clipboard.writeText(snippet)
    copyEnvDone.value = true
    setTimeout(() => { copyEnvDone.value = false }, 2000)
  } catch (_) {
    copyEnvDone.value = false
  }
}

onMounted(() => {
  loadMe()
  loadApiKeys()
  loadSkillTree()
})
</script>

<style scoped>
.account-page { padding: 0; max-width: 720px; margin: 0 auto; min-width: 0; }
.page-desc { margin: 0 0 var(--space-6); font-size: var(--font-body); color: var(--text-secondary); line-height: var(--line-normal); }
.card { margin-bottom: var(--space-5); }
.account-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-3); }
.hint { color: var(--text-secondary); font-size: var(--font-body); margin: 0; }
.account-footer-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-2); }
.api-key-form { display: grid; grid-template-columns: 1fr; gap: var(--space-2); margin-top: var(--space-3); }
.api-key-list { display: flex; flex-direction: column; gap: var(--space-2); margin-top: var(--space-3); }
.api-key-item { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); border: var(--border-hairline); border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); }
.skill-tree-list { list-style: none; padding: 0; margin: var(--space-4) 0 0; display: flex; flex-direction: column; gap: var(--space-2); }
.skill-tree-row { display: flex; flex-wrap: wrap; justify-content: space-between; gap: var(--space-2); border: var(--border-hairline); border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); font-size: var(--font-caption); }
.skill-tree-name { font-weight: 600; color: var(--text-primary); }
.skill-tree-meta { color: var(--text-secondary); }
.account-skel { margin-top: var(--space-3); color: var(--text-secondary); font-size: var(--font-caption); }
.account-dev { margin-top: var(--space-2); }
.dev-actions { margin: var(--space-3) 0; }
.memory-search-row { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-3); align-items: center; }
.memory-search-row .input { flex: 1; min-width: 180px; }
.memory-store-hint { margin-top: var(--space-4); }
.memory-store-textarea { width: 100%; margin-top: var(--space-2); font-family: ui-monospace, monospace; font-size: 0.8125rem; }
.account-json-pre {
  margin-top: var(--space-3); padding: var(--space-3); border-radius: var(--radius-md);
  background: rgba(0,0,0,0.2); border: var(--border-hairline); font-size: 0.75rem;
  overflow-x: auto; max-height: 280px; white-space: pre-wrap; word-break: break-word;
}
</style>
