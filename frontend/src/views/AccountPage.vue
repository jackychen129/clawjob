<template>
  <div class="account-page">
    <h2 class="page-title">{{ t('account.title') }}</h2>
    <div v-if="!auth.token" class="card card-content">
      <p>{{ t('auth.pleaseLogin') || '请先登录' }}</p>
    </div>
    <template v-else>
      <section class="card card-content">
        <h3>{{ t('account.apiTokenTitle') }}</h3>
        <p class="hint">{{ t('account.apiTokenHint') }}</p>
        <div class="account-actions">
          <button type="button" class="btn btn-primary" @click="copyToken">{{ copyTokenDone ? t('account.tokenCopied') : t('account.copyToken') }}</button>
          <button type="button" class="btn btn-secondary" @click="copyEnvSnippet">{{ copyEnvDone ? t('account.tokenCopied') : t('account.copyEnvSnippet') }}</button>
        </div>
      </section>
      <section class="card card-content">
        <h3>{{ t('account.balance') }}</h3>
        <p><strong>{{ credits }}</strong> {{ t('account.points') }}</p>
      </section>
    </template>
    <router-link to="/" class="btn btn-secondary">{{ t('common.home') }}</router-link>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
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
.account-page { padding: 1rem; max-width: 600px; margin: 0 auto; }
.page-title { margin-bottom: 1rem; }
.account-actions { display: flex; gap: 0.5rem; margin-top: 0.5rem; }
.hint { color: var(--color-muted, #888); font-size: 0.9rem; }
</style>
