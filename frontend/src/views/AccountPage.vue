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

const emit = defineEmits<{ (e: 'credits-updated'): void }>()

function loadMe() {
  if (!auth.token) return
  api.getAccountMe().then((res) => {
    credits.value = res.data?.credits ?? 0
    emit('credits-updated')
  }).catch(() => {})
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

onMounted(() => loadMe())
</script>

<style scoped>
.account-page { padding: 0; max-width: 720px; margin: 0 auto; min-width: 0; }
.page-desc { margin: 0 0 var(--space-6); font-size: var(--font-body); color: var(--text-secondary); line-height: var(--line-normal); }
.card { margin-bottom: var(--space-5); }
.account-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-3); }
.hint { color: var(--text-secondary); font-size: var(--font-body); margin: 0; }
.account-footer-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-2); }
</style>
