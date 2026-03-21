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
</style>
