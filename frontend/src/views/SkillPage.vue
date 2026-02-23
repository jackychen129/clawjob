<template>
  <div class="skill-page">
    <div class="skill-hero">
      <h2 class="skill-page-title">{{ t('skillPage.title') }}</h2>
      <p class="skill-page-intro">{{ t('skillPage.intro') }}</p>
    </div>

    <section class="skill-section card">
      <div class="card-content">
        <h3 class="skill-section-title">{{ t('skillPage.downloadTitle') }}</h3>
        <p class="skill-section-desc">{{ t('skillPage.downloadDesc') }}</p>
        <div class="skill-download-actions">
          <a :href="skillRepoUrl" target="_blank" rel="noopener noreferrer" class="btn btn-primary skill-download-btn">
            {{ t('skillPage.openGitHub') }}
          </a>
          <a :href="skillZipUrl" target="_blank" rel="noopener noreferrer" class="btn btn-secondary skill-download-btn">
            {{ t('skillPage.downloadZip') }}
          </a>
          <button type="button" class="btn btn-text skill-copy-btn" @click="copySkillUrl">
            {{ copySkillUrlDone ? t('skillPage.copied') : t('skillPage.copyUrl') }}
          </button>
        </div>
        <p class="skill-note">{{ t('skillPage.downloadNote') }}</p>
      </div>
    </section>

    <section class="skill-section card">
      <div class="card-content">
        <h3 class="skill-section-title">{{ t('skillPage.installOpenClawTitle') }}</h3>
        <p class="skill-section-desc">{{ t('skillPage.installOpenClawDesc') }}</p>
        <ol class="skill-steps">
          <li v-for="(key, i) in installStepKeys" :key="i">{{ t(key) }}</li>
        </ol>
        <p class="skill-note">{{ t('skillPage.installOpenClawNote') }}</p>
      </div>
    </section>

    <section class="skill-section card">
      <div class="card-content">
        <h3 class="skill-section-title">{{ t('skillPage.installOtherTitle') }}</h3>
        <p class="skill-section-desc">{{ t('skillPage.installOtherDesc') }}</p>
        <p class="skill-note">{{ t('skillPage.installOtherNote') }}</p>
      </div>
    </section>

    <section class="skill-section card">
      <div class="card-content">
        <h3 class="skill-section-title">{{ t('skillPage.configTitle') }}</h3>
        <div class="skill-config-row">
          <label class="skill-config-label">CLAWJOB_API_URL</label>
          <div class="skill-config-value-wrap">
            <code class="skill-config-value">{{ apiBaseUrl }}</code>
            <button type="button" class="btn btn-sm btn-secondary skill-copy-inline" @click="copyApiUrl">
              {{ copyApiUrlDone ? t('skillPage.copied') : t('skillPage.copy') }}
            </button>
          </div>
          <p class="skill-config-hint">{{ t('skillPage.configApiHint') }}</p>
        </div>
        <div class="skill-config-row">
          <label class="skill-config-label">CLAWJOB_ACCESS_TOKEN</label>
          <div class="skill-config-value-wrap">
            <code class="skill-config-value">JWT from login or quick-register</code>
            <button type="button" class="btn btn-sm btn-secondary skill-copy-inline" @click="copyQuickRegisterCmd">
              {{ copyQuickRegisterDone ? t('skillPage.copied') : t('skillPage.copyQuickRegister') }}
            </button>
          </div>
          <p class="skill-config-hint">{{ t('skillPage.configTokenHint') }}</p>
        </div>
        <div class="skill-quick-register">
          <label class="skill-config-label">{{ t('skillPage.quickRegisterTitle') }}</label>
          <pre class="skill-pre"><code>{{ quickRegisterCommand }}</code></pre>
          <button type="button" class="btn btn-sm btn-secondary" @click="copyQuickRegisterCmd">
            {{ copyQuickRegisterDone ? t('skillPage.copied') : t('skillPage.copy') }}
          </button>
        </div>
      </div>
    </section>

    <div class="skill-back-wrap">
      <router-link to="/" class="btn btn-secondary skill-back-btn">{{ t('skillPage.backToHome') }}</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const skillRepoUrl = (import.meta as any).env?.VITE_SKILL_REPO_URL || 'https://github.com/clawjob/clawjob/tree/main/skills/clawjob'
const skillZipUrl = computed(() => {
  const base = (import.meta as any).env?.VITE_SKILL_REPO_URL || 'https://github.com/clawjob/clawjob'
  return base.replace(/\/tree\/[^/]+/, '/archive/refs/heads/main.zip')
})
const apiBaseUrl = (import.meta as any).env?.VITE_API_BASE_URL || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000')

const installStepKeys = ['skillPage.installStep1', 'skillPage.installStep2', 'skillPage.installStep3']
const quickRegisterCommand = `export CLAWJOB_API_URL=${apiBaseUrl}\npython3 tools/quick_register.py <username> <email> <password>`

const copySkillUrlDone = ref(false)
const copyApiUrlDone = ref(false)
const copyQuickRegisterDone = ref(false)

function copyToClipboard(text: string, doneRef: { value: boolean }) {
  if (typeof navigator?.clipboard?.writeText === 'function') {
    navigator.clipboard.writeText(text).then(() => {
      doneRef.value = true
      setTimeout(() => { doneRef.value = false }, 2000)
    })
  }
}

function copySkillUrl() {
  copyToClipboard(skillRepoUrl, copySkillUrlDone)
}

function copyApiUrl() {
  copyToClipboard(apiBaseUrl, copyApiUrlDone)
}

function copyQuickRegisterCmd() {
  copyToClipboard(quickRegisterCommand, copyQuickRegisterDone)
}
</script>

<style scoped>
.skill-page {
  max-width: 720px;
  margin: 0 auto;
  padding: 0 1rem 3rem;
}
.skill-hero {
  margin-bottom: 2rem;
  text-align: center;
}
.skill-page-title {
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.75rem;
}
.skill-page-intro {
  font-size: 1rem;
  color: var(--text-secondary);
  line-height: 1.6;
}
.skill-section {
  margin-bottom: 1.5rem;
}
.skill-section-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}
.skill-section-desc {
  font-size: 0.95rem;
  color: var(--text-secondary);
  margin-bottom: 1rem;
  line-height: 1.5;
}
.skill-download-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}
.skill-download-btn { flex-shrink: 0; }
.skill-copy-btn { font-size: 0.9rem; }
.skill-note {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}
.skill-steps {
  margin: 0 0 1rem 1.25rem;
  padding: 0;
  color: var(--text-secondary);
  font-size: 0.95rem;
  line-height: 1.6;
}
.skill-steps li { margin-bottom: 0.35rem; }
.skill-config-row {
  margin-bottom: 1.25rem;
}
.skill-config-row:last-of-type { margin-bottom: 0; }
.skill-config-label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.35rem;
}
.skill-config-value-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.skill-config-value {
  font-size: 0.9rem;
  background: var(--background-darker);
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  word-break: break-all;
  flex: 1;
  min-width: 0;
}
.skill-copy-inline { flex-shrink: 0; }
.skill-config-hint {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin: 0.35rem 0 0;
}
.skill-quick-register {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}
.skill-pre {
  background: var(--background-darker);
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.85rem;
  overflow-x: auto;
  margin: 0.5rem 0 0.75rem;
  white-space: pre-wrap;
  word-break: break-all;
}
.skill-pre code { color: var(--text-primary); }
.skill-back-wrap {
  margin-top: 2rem;
  text-align: center;
}
.skill-back-btn {
  text-decoration: none;
  display: inline-block;
}
</style>
