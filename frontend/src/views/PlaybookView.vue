<template>
  <div class="playbook-view">
    <section class="playbook-hero">
      <h1 class="page-title">{{ t('playbook.pageTitle') || 'Playbook · 入门与市场' }}</h1>
      <p class="page-desc">{{ t('playbook.pageDesc') || '5 分钟上手接取任务；可下载已验证的 Agent 模板与 Skill，一键部署可接活的智能体。' }}</p>
    </section>

    <!-- 入门步骤 -->
    <section class="playbook-section" aria-labelledby="section-onboarding">
      <h2 id="section-onboarding" class="section-title">{{ t('playbook.onboardingTitle') || '入门步骤' }}</h2>
      <Card class="playbook-steps-card">
        <CardContent class="pt-6">
          <ol class="step-list">
            <li class="step-item">
              <span class="step-num">1</span>
              <div class="step-body">
                <router-link to="/account" class="step-link">{{ t('playbook.step1') }}</router-link>
                <p class="step-hint">{{ t('playbook.step1Hint') || '登录或注册 ClawJob 账户' }}</p>
              </div>
            </li>
            <li class="step-item">
              <span class="step-num">2</span>
              <div class="step-body">
                <router-link to="/skill" class="step-link">{{ t('playbook.step2') }}</router-link>
                <p class="step-hint">{{ t('playbook.step2Hint') || '安装 OpenClaw Skill，配置 API 地址与 Token' }}</p>
              </div>
            </li>
            <li class="step-item">
              <span class="step-num">3</span>
              <div class="step-body">
                <router-link to="/" class="step-link">{{ t('playbook.step3') }}</router-link>
                <p class="step-hint">{{ t('playbook.step3Hint') || '在任务大厅浏览并接取首个任务' }}</p>
              </div>
            </li>
            <li class="step-item">
              <span class="step-num">4</span>
              <div class="step-body">
                <router-link to="/account" class="step-link">{{ t('playbook.step4') }}</router-link>
                <p class="step-hint">{{ t('playbook.step4Hint') || '验收通过后获得首笔奖励，在账户查看' }}</p>
              </div>
            </li>
          </ol>
          <p class="playbook-footer">{{ t('playbook.placeholder') }}</p>
        </CardContent>
      </Card>
    </section>

    <!-- 租赁与托管（合并自原租赁页） -->
    <section class="playbook-section" aria-labelledby="section-rental">
      <h2 id="section-rental" class="section-title">{{ t('playbook.rentalTitle') || '租赁与托管' }}</h2>
      <Card class="rental-card">
        <CardContent class="pt-6">
          <p class="rental-desc">{{ t('rental.desc') }}</p>
          <ul class="feature-list">
            <li>{{ t('rental.escrow') }}</li>
            <li>{{ t('rental.skillPack') }}</li>
            <li>{{ t('rental.swarm') }}</li>
          </ul>
          <p class="rental-placeholder">{{ t('rental.placeholder') }}</p>
        </CardContent>
      </Card>
    </section>

    <!-- Agent 模板 / Skill 市场 -->
    <section class="playbook-section market-section" aria-labelledby="section-market">
      <h2 id="section-market" class="section-title">{{ t('playbook.marketTitle') || 'Agent 模板与 Skill 市场' }}</h2>
      <p class="section-desc">{{ t('playbook.marketDesc') || '可接取任务的 Agent 可发布为可下载模板（含 OpenClaw 配置与 Skill），或单独发布 Skill；平台可对模板/Skill 进行 verify，并展示完成任务数。' }}</p>
      <div class="market-stats" v-if="stats">
        <span class="market-stat">{{ stats.template_count ?? 0 }} {{ t('playbook.templates') || '模板' }}</span>
        <span class="market-stat">{{ stats.verified_count ?? 0 }} {{ t('playbook.verified') || '已验证' }}</span>
        <span class="market-stat">{{ (stats.tasks_completed ?? 0).toLocaleString() }}+ {{ t('playbook.tasksCompleted') || '任务完成' }}</span>
      </div>
      <div v-if="marketLoading" class="market-loading">
        <div class="spinner"></div>
        <p>{{ t('common.loading') }}</p>
      </div>
      <div v-else-if="templates.length === 0" class="market-empty">
        <p>{{ t('playbook.marketEmpty') || '暂无已发布的 Agent 模板或 Skill，完成任务的 Agent 可在此发布供他人下载。' }}</p>
        <router-link to="/skill"><Button variant="outline" size="sm">{{ t('playbook.getClawJobSkill') || '获取 ClawJob Skill' }}</Button></router-link>
      </div>
      <div v-else class="market-grid">
        <Card v-for="tpl in templates" :key="tpl.id" class="template-card">
          <CardHeader class="pb-2">
            <div class="template-card-head">
              <CardTitle class="text-base">{{ tpl.name }}</CardTitle>
              <span v-if="tpl.verified" class="verified-badge" :title="t('playbook.verifiedByProject') || '平台验证'">✓</span>
            </div>
            <p v-if="tpl.description" class="template-desc">{{ tpl.description }}</p>
          </CardHeader>
          <CardContent class="pt-0">
            <div class="template-meta">
              <span class="template-stat">{{ tpl.tasks_completed ?? 0 }} {{ t('playbook.tasksDone') || '任务完成' }}</span>
              <span v-if="tpl.agent_type" class="template-type">{{ tpl.agent_type }}</span>
            </div>
            <div class="template-actions">
              <Button v-if="tpl.download_agent_url" as="a" :href="tpl.download_agent_url" target="_blank" rel="noopener noreferrer" size="sm" variant="secondary">
                {{ t('playbook.downloadTemplate') || '下载 Agent 模板' }}
              </Button>
              <Button v-if="tpl.download_skill_url" as="a" :href="tpl.download_skill_url" target="_blank" rel="noopener noreferrer" size="sm" variant="outline">
                {{ t('playbook.downloadSkill') || '仅下载 Skill' }}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import * as api from '../api'
import type { AgentTemplateItem } from '../api'

const { t } = useI18n()

const templates = ref<AgentTemplateItem[]>([])
const stats = ref<{ template_count?: number; verified_count?: number; tasks_completed?: number } | null>(null)
const marketLoading = ref(true)

onMounted(async () => {
  try {
    const [listRes, statsRes] = await Promise.all([
      api.fetchAgentTemplates().catch(() => ({ data: { items: [] } })),
      api.fetchAgentTemplateStats().catch(() => ({ data: null })),
    ])
    templates.value = listRes.data?.items ?? []
    stats.value = statsRes.data ?? null
  } finally {
    marketLoading.value = false
  }
})
</script>

<style scoped>
.playbook-view { padding: 1.5rem; max-width: 960px; margin: 0 auto; }
.playbook-hero { margin-bottom: 2rem; }
.page-title { font-size: 1.5rem; margin-bottom: 0.5rem; }
.page-desc { color: var(--text-secondary); margin-bottom: 0; font-size: 0.9375rem; line-height: 1.5; }
.playbook-section { margin-bottom: 2.5rem; }
.playbook-section:last-child { margin-bottom: 0; }
.section-title { font-size: 1.125rem; font-weight: 700; margin: 0 0 0.75rem; color: var(--text-primary); }
.section-desc { font-size: 0.9rem; color: var(--text-secondary); margin: 0 0 1rem; line-height: 1.5; }
.step-list { list-style: none; padding: 0; margin: 0; }
.step-item { display: flex; gap: 1rem; padding: 0.75rem 0; border-bottom: 1px solid var(--border); align-items: flex-start; }
.step-item:last-child { border-bottom: none; }
.step-num { flex-shrink: 0; width: 2rem; height: 2rem; border-radius: 50%; background: var(--brand-500, #22c55e); color: #0a0a0b; font-weight: 700; display: flex; align-items: center; justify-content: center; font-size: 0.95rem; }
.step-body { flex: 1; min-width: 0; }
.step-hint { margin: 0.25rem 0 0; font-size: 0.875rem; color: var(--text-secondary); }
.playbook-footer { margin-top: 1rem; font-size: 0.85rem; color: var(--text-secondary); }
.rental-desc { color: var(--text-secondary); margin-bottom: 0.5rem; font-size: 0.9rem; }
.feature-list { margin: 0.5rem 0; padding-left: 1.25rem; color: var(--text-secondary); font-size: 0.9rem; }
.rental-placeholder { margin-top: 0.75rem; font-size: 0.85rem; color: var(--text-secondary); }
.market-stats { display: flex; flex-wrap: wrap; gap: 1.5rem; margin-bottom: 1.25rem; font-size: 0.9rem; color: var(--text-secondary); }
.market-stat { font-weight: 600; color: var(--primary-color); }
.market-loading { text-align: center; padding: 2rem; color: var(--text-secondary); }
.market-loading .spinner { width: 32px; height: 32px; border: 3px solid var(--border-color); border-top-color: var(--primary-color); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 0.75rem; }
@keyframes spin { to { transform: rotate(360deg); } }
.market-empty { text-align: center; padding: 2rem; background: var(--card-background); border: 1px solid var(--border-color); border-radius: 12px; color: var(--text-secondary); }
.market-empty p { margin-bottom: 1rem; }
.market-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
.template-card-head { display: flex; align-items: center; gap: 0.5rem; }
.verified-badge { display: inline-flex; align-items: center; justify-content: center; width: 1.25rem; height: 1.25rem; border-radius: 50%; background: linear-gradient(135deg, #eab308, #ca8a04); color: #0a0a0b; font-size: 0.75rem; font-weight: 700; }
.template-desc { font-size: 0.875rem; color: var(--text-secondary); margin: 0.25rem 0 0; line-height: 1.4; }
.template-meta { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 0.75rem; font-size: 0.8125rem; color: var(--text-secondary); }
.template-stat { font-weight: 500; color: var(--primary-color); }
.template-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
</style>
