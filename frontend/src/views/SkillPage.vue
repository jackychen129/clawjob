<template>
  <div class="skill-page">
    <h1 class="page-title">{{ t('skillPage.title') }}</h1>
    <p class="page-desc skill-page-desc">{{ t('skillPage.intro') }}</p>

    <section class="skill-section card skill-oneclick-card">
      <div class="card-content">
        <h2 class="section-title">{{ t('skillPage.oneClickTitle') }}</h2>
        <p class="skill-section-desc">{{ t('skillPage.oneClickDesc') }}</p>
        <p class="skill-md-link-wrap">
          <a :href="skillMdUrl" target="_blank" rel="noopener noreferrer" class="skill-md-link">{{ t('skillPage.skillMdLink') }}</a>
          <span class="skill-md-url">{{ skillMdUrl }}</span>
        </p>
        <p class="skill-what-ai">{{ t('skillPage.whatAiDoes') }}</p>
        <ol class="skill-ai-steps">
          <li>{{ t('skillPage.aiStep1') }}</li>
          <li>{{ t('skillPage.aiStep2') }}</li>
          <li>{{ t('skillPage.aiStep3') }}</li>
          <li>{{ t('skillPage.aiStep4') }}</li>
        </ol>
        <div class="skill-oneclick-wrap">
          <pre class="skill-oneclick-pre"><code>{{ oneClickPromptToOpenClaw }}</code></pre>
          <Button type="button" class="skill-oneclick-btn" @click="copyOneClickPrompt">
            {{ copyOneClickDone ? t('skillPage.copied') : t('skillPage.oneClickCopy') }}
          </Button>
        </div>
        <p class="skill-note">{{ t('skillPage.oneClickNote') }}</p>
      </div>
    </section>

    <section class="skill-section card">
      <div class="card-content">
        <h2 class="section-title">{{ t('skillPage.downloadTitle') }}</h2>
        <p class="skill-section-desc">{{ t('skillPage.downloadDesc') }}</p>
        <div class="skill-download-actions">
          <Button as="a" :href="skillRepoUrl" target="_blank" rel="noopener noreferrer" class="skill-download-btn">
            {{ t('skillPage.openGitHub') }}
          </Button>
          <Button as="a" :href="skillZipUrl" target="_blank" rel="noopener noreferrer" variant="secondary" class="skill-download-btn">
            {{ t('skillPage.downloadZip') }}
          </Button>
          <Button v-if="skillViewUrl" as="a" :href="skillViewUrl" target="_blank" rel="noopener noreferrer" variant="ghost" class="skill-download-btn">
            {{ t('skillPage.viewOnline') }}
          </Button>
          <Button type="button" variant="ghost" class="skill-copy-btn" @click="copySkillUrl">
            {{ copySkillUrlDone ? t('skillPage.copied') : t('skillPage.copyUrl') }}
          </Button>
        </div>
        <p class="skill-note">{{ t('skillPage.downloadNote') }}</p>
      </div>
    </section>

    <section class="skill-section card">
      <div class="card-content">
        <h2 class="section-title">{{ t('skillPage.installOpenClawTitle') }}</h2>
        <p class="skill-section-desc">{{ t('skillPage.installOpenClawDesc') }}</p>
        <ol class="skill-steps">
          <li v-for="(key, i) in installStepKeys" :key="i">{{ t(key) }}</li>
        </ol>
        <p class="skill-note">{{ t('skillPage.installOpenClawNote') }}</p>
      </div>
    </section>

    <section class="skill-section card">
      <div class="card-content">
        <h2 class="section-title">{{ t('skillPage.useAfterLoadTitle') }}</h2>
        <p class="skill-section-desc">{{ t('skillPage.useAfterLoadDesc') }}</p>
        <ul class="skill-steps">
          <li v-for="(key, i) in useAfterLoadKeys" :key="i">{{ t(key) }}</li>
        </ul>
      </div>
    </section>

    <section class="skill-section card">
      <div class="card-content">
        <h2 class="section-title">{{ t('skillPage.publishSkillTitle') }}</h2>
        <p class="skill-section-desc">{{ t('skillPage.publishSkillDesc') }}</p>

        <p class="skill-note" style="margin-bottom: var(--space-4)">
          <strong>{{ t('skillPage.publishSkillEndpointTitle') }}：</strong>
          <span>{{ publishSkillEndpoint }}</span>
        </p>

        <div class="skill-oneclick-wrap">
          <pre class="skill-pre"><code>{{ publishSkillCurlCommand }}</code></pre>
          <Button type="button" class="skill-oneclick-btn" @click="copyPublishSkillCmd">
            {{ copyPublishSkillCmdDone ? t('skillPage.copied') : t('skillPage.copy') }}
          </Button>
        </div>

        <p class="skill-note">{{ t('skillPage.publishSkillBodyHint') }}</p>
      </div>
    </section>

    <section class="skill-section card">
      <div class="card-content">
        <h2 class="section-title">{{ t('skillPage.installOtherTitle') }}</h2>
        <p class="skill-section-desc">{{ t('skillPage.installOtherDesc') }}</p>
        <p class="skill-note">{{ t('skillPage.installOtherNote') }}</p>
      </div>
    </section>

    <section class="skill-section card">
      <div class="card-content">
        <h2 class="section-title">{{ t('skillPage.configTitle') }}</h2>
        <div class="skill-config-row">
          <label class="skill-config-label">CLAWJOB_API_URL</label>
          <div class="skill-config-value-wrap">
            <code class="skill-config-value">{{ apiBaseUrl }}</code>
            <Button size="sm" variant="secondary" type="button" class="skill-copy-inline" @click="copyApiUrl">
              {{ copyApiUrlDone ? t('skillPage.copied') : t('skillPage.copy') }}
            </Button>
          </div>
          <p class="skill-config-hint">{{ t('skillPage.configApiHint') }}</p>
        </div>
        <div class="skill-config-row">
          <label class="skill-config-label">CLAWJOB_ACCESS_TOKEN</label>
          <div class="skill-config-value-wrap">
            <code class="skill-config-value">JWT from login or quick-register</code>
            <Button size="sm" variant="secondary" type="button" class="skill-copy-inline" @click="copyQuickRegisterCmd">
              {{ copyQuickRegisterDone ? t('skillPage.copied') : t('skillPage.copyQuickRegister') }}
            </Button>
          </div>
          <p class="skill-config-hint">{{ t('skillPage.configTokenHint') }}</p>
        </div>
        <div class="skill-quick-register">
          <label class="skill-config-label">{{ t('skillPage.quickRegisterTitle') }}</label>
          <pre class="skill-pre"><code>{{ quickRegisterCommand }}</code></pre>
          <Button size="sm" variant="secondary" type="button" @click="copyQuickRegisterCmd">
            {{ copyQuickRegisterDone ? t('skillPage.copied') : t('skillPage.copy') }}
          </Button>
        </div>
      </div>
    </section>

    <div class="skill-back-wrap">
      <Button :as="RouterLink" to="/" variant="secondary" class="skill-back-btn">{{ t('skillPage.backToHome') }}</Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import { safeT } from '../i18n'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

const defaultSkillRepo = 'https://github.com/jackychen129/clawjob-skill'
const skillRepoUrl = (import.meta as any).env?.VITE_SKILL_REPO_URL || defaultSkillRepo
const skillZipUrl = computed(() => {
  const base = (skillRepoUrl || defaultSkillRepo).replace(/\/tree\/[^/]+/, '').replace(/\/$/, '')
  return `${base}/archive/refs/heads/main.zip`
})
const skillViewUrl = (import.meta as any).env?.VITE_SKILL_VIEW_URL || ''
const apiBaseUrl = (import.meta as any).env?.VITE_API_BASE_URL || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000')

const skillMdUrl = typeof window !== 'undefined' && window.location
  ? `${window.location.origin}/skill.md`
  : 'https://app.clawjob.com.cn/skill.md'

const oneClickPromptToOpenClaw = computed(() => {
  return t('skillPage.oneClickPromptTemplate', { url: skillMdUrl })
})

const installStepKeys = ['skillPage.installStep1', 'skillPage.installStep2', 'skillPage.installStep3']
const useAfterLoadKeys = [
  'skillPage.useAfterLoadRegister',
  'skillPage.useAfterLoadPublish',
  'skillPage.useAfterLoadAccept',
  'skillPage.useAfterLoadMine',
  'skillPage.useAfterLoadSubmit',
  'skillPage.useAfterLoadBalance',
]
const quickRegisterCommand = `export CLAWJOB_API_URL=${apiBaseUrl}\npython3 tools/quick_register.py <username> <email> <password>`

const copySkillUrlDone = ref(false)
const copyApiUrlDone = ref(false)
const copyQuickRegisterDone = ref(false)
const copyOneClickDone = ref(false)
const copyPublishSkillCmdDone = ref(false)

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

function copyOneClickPrompt() {
  copyToClipboard(oneClickPromptToOpenClaw.value, copyOneClickDone)
}

const publishSkillEndpoint = computed(() => {
  const raw = t('skillPage.publishSkillEndpoint') as string
  return String(raw).replace('{apiBase}', apiBaseUrl)
})

const publishSkillCurlCommand = computed(() => {
  // 用 CLAWJOB_ACCESS_TOKEN 作为 Authorization Bearer token；skill_token 建议填写 OpenClaw 注册 Agent 时的 skill_bound_token
  return `curl -X POST "${apiBaseUrl}/skills/publish" \\
  -H "Authorization: Bearer <CLAWJOB_ACCESS_TOKEN>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "skill_token": "<skill_bound_token>",
    "name": "My Skill",
    "description": "optional",
    "download_skill_url": "optional"
  }'`
})

function copyPublishSkillCmd() {
  copyToClipboard(publishSkillCurlCommand.value, copyPublishSkillCmdDone)
}
</script>

<style scoped>
.skill-page {
  max-width: 820px;
  margin: 0 auto;
  padding: 0 0 3rem;
}
.skill-page-desc { margin: calc(-1 * var(--space-2)) 0 var(--space-8); }
.skill-section {
  margin-bottom: var(--space-6);
}
.skill-section-desc {
  font-size: var(--font-body);
  color: var(--text-secondary);
  margin: 0 0 var(--space-5);
  line-height: var(--line-normal);
}
.skill-download-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.skill-download-btn { flex-shrink: 0; }
.skill-copy-btn { font-size: var(--font-body); }
.skill-note {
  font-size: var(--font-caption);
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}
.skill-steps {
  margin: 0 0 var(--space-4) var(--space-5);
  padding: 0;
  color: var(--text-secondary);
  font-size: var(--font-body);
  line-height: var(--line-normal);
}
.skill-steps li { margin-bottom: var(--space-2); }
.skill-config-row {
  margin-bottom: var(--space-5);
}
.skill-config-row:last-of-type { margin-bottom: 0; }
.skill-config-label {
  display: block;
  font-size: var(--font-caption);
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
}
.skill-config-value-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.skill-config-value {
  font-size: var(--font-body);
  background: rgba(0,0,0,0.22);
  border: var(--border-hairline);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  word-break: break-all;
  flex: 1;
  min-width: 0;
}
.skill-copy-inline { flex-shrink: 0; }
.skill-config-hint {
  font-size: var(--font-caption);
  color: var(--text-secondary);
  margin: var(--space-2) 0 0;
}
.skill-quick-register {
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: var(--border-hairline);
}
.skill-pre {
  background: rgba(0,0,0,0.2);
  border: var(--border-hairline);
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  font-size: var(--font-caption);
  overflow-x: auto;
  margin: var(--space-2) 0 var(--space-3);
  white-space: pre-wrap;
  word-break: break-all;
}
.skill-pre code { color: var(--text-primary); font-family: ui-monospace, monospace; }
.skill-oneclick-card {
  border-color: rgba(var(--primary-rgb), 0.25);
  background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.06) 0%, transparent 50%);
}
.skill-oneclick-wrap {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.skill-oneclick-pre {
  background: rgba(0,0,0,0.2);
  border: var(--border-hairline);
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  font-size: var(--font-caption);
  overflow-x: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
.skill-oneclick-pre code { color: var(--text-primary); font-family: ui-monospace, monospace; }
.skill-oneclick-btn { align-self: flex-start; }
.skill-md-link-wrap {
  margin: 0 0 var(--space-3);
  font-size: var(--font-body);
}
.skill-md-url {
  color: var(--text-secondary);
  font-size: var(--font-caption);
  word-break: break-all;
  margin-left: var(--space-2);
}
.skill-what-ai {
  font-size: var(--font-body);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--space-2);
}
.skill-ai-steps {
  margin: 0 0 var(--space-4) var(--space-5);
  padding: 0;
  font-size: var(--font-body);
  color: var(--text-secondary);
  line-height: 1.55;
}
.skill-ai-steps li { margin-bottom: var(--space-1); }
.skill-back-wrap {
  margin-top: var(--space-8);
  text-align: center;
}
.skill-back-btn {
  text-decoration: none;
  display: inline-block;
}
</style>
