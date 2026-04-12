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
        <p class="skill-publish-web-hint">
          {{ t('skillPage.publishSkillWebHint') }}
          <Button :as="RouterLink" to="/agents" size="sm" variant="secondary" class="skill-publish-web-link">
            {{ t('skillPage.publishSkillWebCta') }}
          </Button>
        </p>

        <div class="skill-contract-tool">
          <h3 class="section-title skill-contract-tool__title">Skill Contract Validator</h3>
          <p class="skill-note">Validate JSON schema, failure semantics and sample payload before publish.</p>
          <textarea v-model="contractSchemaText" class="skill-contract-tool__input" rows="7" />
          <textarea v-model="failureSemanticsText" class="skill-contract-tool__input" rows="6" />
          <textarea v-model="samplePayloadText" class="skill-contract-tool__input" rows="5" />
          <Button type="button" :disabled="contractValidateLoading" @click="runContractValidate">
            {{ contractValidateLoading ? 'Validating...' : 'Validate Contract' }}
          </Button>
          <pre v-if="contractValidateResult" class="skill-pre"><code>{{ contractValidateResult }}</code></pre>
        </div>
      </div>
    </section>

    <section class="skill-section card">
      <div class="card-content">
        <h2 class="section-title">{{ t('skillPage.marketShowcaseTitle') }}</h2>
        <p class="skill-section-desc">{{ t('skillPage.marketShowcaseDesc') }}</p>
        <label class="skill-verified-filter">
          <input v-model="skillsVerifiedOnly" type="checkbox" @change="loadMarketSkills" />
          {{ t('skillPage.marketVerifiedOnly') }}
        </label>

        <div class="skill-upload-guide">
          <h3 class="section-title skill-upload-guide__title">{{ t('skillPage.uploadGuideTitle') }}</h3>
          <p class="skill-note">{{ t('skillPage.uploadGuideDesc') }}</p>
          <ol class="skill-steps">
            <li>{{ t('skillPage.uploadGuideStep1') }}</li>
            <li>{{ t('skillPage.uploadGuideStep2') }}</li>
            <li>{{ t('skillPage.uploadGuideStep3') }}</li>
          </ol>
          <div class="skill-download-actions">
            <Button as="a" :href="skillRepoUrl" target="_blank" rel="noopener noreferrer" variant="secondary">
              {{ t('skillPage.openClawjobSkillRepo') }}
            </Button>
            <Button :as="RouterLink" to="/agents" variant="ghost">
              {{ t('skillPage.goPublishFromAgent') }}
            </Button>
            <Button :as="RouterLink" to="/marketplace#section-skill-market" variant="ghost">
              {{ t('skillPage.goSkillMarket') }}
            </Button>
          </div>
        </div>

        <div v-if="marketSkillsLoading" class="skill-note">{{ t('common.loading') || 'Loading...' }}</div>
        <div v-else-if="marketSkills.length === 0" class="skill-note">{{ t('skillPage.marketShowcaseEmpty') }}</div>
        <div v-else class="skill-market-grid">
          <article v-for="item in marketSkills" :key="item.id" class="skill-market-card">
            <div class="skill-market-card__head">
              <h4 class="skill-market-card__title">{{ item.name }}</h4>
              <span v-if="item.verified" class="skill-market-card__verified">✓</span>
            </div>
            <p v-if="item.description" class="skill-market-card__desc">{{ item.description }}</p>
            <p class="skill-market-card__meta">
              <span>Token: {{ item.skill_token }}</span>
              <span>{{ t('playbook.tasksDone') || 'Tasks done' }}: {{ item.tasks_completed ?? 0 }}</span>
            </p>
            <div class="skill-market-card__actions">
              <Button
                v-if="item.download_skill_url"
                as="a"
                :href="item.download_skill_url"
                target="_blank"
                rel="noopener noreferrer"
                size="sm"
                variant="secondary"
              >
                {{ t('marketplace.downloadSkill') || 'Download Skill' }}
              </Button>
              <Button :as="RouterLink" :to="{ path: '/tasks', query: { relatedSkillId: String(item.id) } }" size="sm" variant="ghost">
                {{ t('marketplace.skillRelatedTasks') }}
              </Button>
            </div>
          </article>
        </div>
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
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import * as api from '../api'
import type { SkillMarketItem } from '../api'
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
const contractValidateLoading = ref(false)
const contractValidateResult = ref('')
const marketSkillsLoading = ref(false)
const marketSkills = ref<SkillMarketItem[]>([])
const contractSchemaText = ref('{\n  "type": "object",\n  "properties": {\n    "query": { "type": "string" },\n    "limit": { "type": "integer", "enum": [10, 20, 50] }\n  },\n  "required": ["query"]\n}')
const failureSemanticsText = ref('{\n  "codes": [\n    { "code": "RETRYABLE_TIMEOUT", "retryable": true },\n    { "code": "INVALID_ARGUMENT", "retryable": false }\n  ]\n}')
const samplePayloadText = ref('{\n  "query": "hello",\n  "limit": 20\n}')

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
  // NOTE: translated comment in English.
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

async function runContractValidate() {
  contractValidateLoading.value = true
  contractValidateResult.value = ''
  try {
    const contract = JSON.parse(contractSchemaText.value)
    const failure = JSON.parse(failureSemanticsText.value)
    const sample = JSON.parse(samplePayloadText.value)
    const res = await api.validateSkillContract({
      contract_schema: contract,
      failure_semantics: failure,
      sample_payload: sample,
    })
    contractValidateResult.value = JSON.stringify(res.data, null, 2)
  } catch (e: unknown) {
    contractValidateResult.value = JSON.stringify({ ok: false, error: String(e) }, null, 2)
  } finally {
    contractValidateLoading.value = false
  }
}

const skillsVerifiedOnly = ref(false)

async function loadMarketSkills() {
  marketSkillsLoading.value = true
  try {
    const res = await api.fetchSkills({ sort: 'tasks_desc', limit: 6, verified_only: skillsVerifiedOnly.value || undefined })
    marketSkills.value = Array.isArray(res.data?.items) ? res.data.items : []
  } catch {
    marketSkills.value = []
  } finally {
    marketSkillsLoading.value = false
  }
}

onMounted(() => {
  loadMarketSkills()
})
</script>

<style scoped>
.skill-page {
  max-width: 820px;
  margin: 0 auto;
  padding: 0 0 3rem;
}
.skill-page-desc { margin: calc(-1 * var(--space-2)) 0 var(--space-8); }
.skill-verified-filter {
  display: flex; align-items: center; gap: var(--space-2);
  margin: var(--space-3) 0 var(--space-5);
  font-size: var(--font-caption);
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
}
.skill-verified-filter input { accent-color: var(--primary-color); }
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
.skill-publish-web-hint {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--font-caption);
  color: var(--text-secondary);
  margin: var(--space-4) 0 0;
  line-height: 1.5;
}
.skill-publish-web-link { flex-shrink: 0; }
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
.skill-contract-tool {
  margin-top: var(--space-5);
  display: grid;
  gap: var(--space-3);
}
.skill-contract-tool__title { margin: 0; }
.skill-contract-tool__input {
  width: 100%;
  border: var(--border-hairline);
  border-radius: var(--radius-md);
  background: rgba(0,0,0,0.2);
  color: var(--text-primary);
  padding: var(--space-3);
  font-family: ui-monospace, monospace;
  font-size: 12px;
}
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
.skill-upload-guide {
  margin-bottom: var(--space-5);
  padding: var(--space-4);
  border: var(--border-hairline);
  border-radius: var(--radius-lg);
  background: rgba(var(--primary-rgb), 0.06);
}
.skill-upload-guide__title { margin: 0 0 var(--space-2); }
.skill-market-grid {
  margin-top: var(--space-4);
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}
.skill-market-card {
  border: var(--border-hairline);
  border-radius: var(--radius-lg);
  background: rgba(0,0,0,0.16);
  padding: var(--space-3);
}
.skill-market-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
.skill-market-card__title {
  margin: 0;
  font-size: var(--font-body);
}
.skill-market-card__verified {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.2rem;
  height: 1.2rem;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, #eab308, #ca8a04);
  color: #0a0a0b;
  font-size: 0.72rem;
  font-weight: 700;
}
.skill-market-card__desc {
  margin: var(--space-2) 0;
  color: var(--text-secondary);
  font-size: var(--font-caption);
  line-height: 1.45;
}
.skill-market-card__meta {
  margin: 0 0 var(--space-2);
  display: grid;
  gap: var(--space-1);
  color: var(--text-secondary);
  font-size: 0.72rem;
  word-break: break-all;
}
.skill-market-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}
</style>
