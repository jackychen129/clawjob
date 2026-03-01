<template>
  <div class="manual-page">
    <div class="manual-header">
      <h2 class="manual-title">{{ t('docsPage.manualTitle') }}</h2>
      <router-link to="/docs" class="btn btn-secondary">{{ t('docsPage.backToDocs') }}</router-link>
    </div>
    <div v-if="loading" class="loading"><div class="spinner"></div></div>
    <p v-else-if="error" class="error-msg">{{ error }}</p>
    <div v-else class="manual-body docs-body" v-html="html"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : ((key: string) => key)

const content = ref('')
const html = ref('')
const loading = ref(true)
const error = ref('')

function manualPath(locale: string): string {
  return locale === 'zh-CN' ? '/docs/manual_zh.md' : '/docs/manual_en.md'
}

function loadManual(locale: string) {
  loading.value = true
  error.value = ''
  fetch(manualPath(locale))
    .then((r) => {
      if (!r.ok) throw new Error(r.statusText)
      return r.text()
    })
    .then((text) => {
      content.value = text
      html.value = simpleMarkdownToHtml(text)
    })
    .catch((e) => {
      error.value = (typeof t === 'function' ? t('common.loadError') : 'Load failed') || e.message
    })
    .finally(() => {
      loading.value = false
    })
}

function simpleMarkdownToHtml(md: string): string {
  let h = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  h = h.replace(/^### (.+)$/gm, '<h3 class="manual-h3">$1</h3>')
  h = h.replace(/^## (.+)$/gm, '<h2 class="manual-h2">$1</h2>')
  h = h.replace(/^# (.+)$/gm, '<h1 class="manual-h1">$1</h1>')
  h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  h = h.replace(/\n\n/g, '</p><p class="manual-p">')
  h = h.replace(/\n/g, '<br/>')
  return '<p class="manual-p">' + h + '</p>'
}

onMounted(() => {
  loadManual(_i18n.locale.value)
})

watch(() => _i18n.locale.value, (locale) => {
  loadManual(locale)
})
</script>

<style scoped>
.manual-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 1rem 3rem;
}
.manual-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}
.manual-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}
.manual-body {
  font-size: 0.95rem;
  color: var(--text-secondary);
  line-height: 1.7;
}
.manual-body :deep(.manual-h1) {
  font-size: 1.35rem;
  color: var(--text-primary);
  margin: 1.5rem 0 0.75rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--border-color);
}
.manual-body :deep(.manual-h2) {
  font-size: 1.15rem;
  color: var(--text-primary);
  margin: 1.25rem 0 0.5rem;
}
.manual-body :deep(.manual-h3) {
  font-size: 1.05rem;
  color: var(--text-primary);
  margin: 1rem 0 0.4rem;
}
.manual-body :deep(.manual-p) {
  margin: 0 0 0.6rem;
}
.manual-body :deep(strong) {
  color: var(--text-primary);
}
</style>
