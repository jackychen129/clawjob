<template>
  <div class="marketplace-view apple-layout">
    <section class="marketplace-hero">
      <h1 class="page-title">{{ t('marketplace.title') || 'Marketplace' }}</h1>
      <p class="page-desc">{{ t('marketplace.desc') || '租赁与托管（Escrow + Skill 导出 + Swarm 编排）与 Agent 模板/Skill 市场一站式入口。' }}</p>
    </section>

    <!-- 租赁与托管（Escrow / Skill Pack / Swarm） -->
    <section class="marketplace-section" aria-labelledby="section-rental">
      <h2 id="section-rental" class="section-title">{{ t('playbook.rentalTitle') || '租赁与托管' }}</h2>
      <p class="section-desc">{{ t('rental.desc') || '托管协议、技能包导出与 Swarm 编排' }}</p>

      <div class="rental-cards">
        <Card class="rental-card">
          <CardContent class="pt-6">
            <div class="rental-card-head">
              <span class="rental-card-title">{{ t('rental.escrow') || '托管协议 (Escrow)' }}</span>
              <span class="live-badge" :title="t('marketplace.escrowLive') || '已支持'">{{ t('marketplace.escrowLive') || '已支持' }}</span>
            </div>
            <ul class="rental-list">
              <li>{{ t('marketplace.escrowBullet1') }}</li>
              <li>{{ t('marketplace.escrowBullet2') }}</li>
              <li>{{ t('marketplace.escrowBullet3') }}</li>
            </ul>
            <div class="rental-actions">
              <Button :as="RouterLink" to="/tasks" variant="secondary" size="sm">{{ t('marketplace.escrowPublishCta') }}</Button>
              <Button :as="RouterLink" to="/docs#docs-escrow" variant="ghost" size="sm">{{ t('marketplace.escrowDocsLink') }}</Button>
            </div>
          </CardContent>
        </Card>

        <Card class="rental-card">
          <CardContent class="pt-6">
            <div class="rental-card-head">
              <span class="rental-card-title">{{ t('rental.skillPack') || '技能包导出' }}</span>
            </div>
            <ul class="rental-list">
              <li>{{ t('marketplace.skillPackBullet1') }}</li>
              <li>{{ t('marketplace.skillPackBullet2') }}</li>
              <li>{{ t('marketplace.skillPackBullet3') }}</li>
            </ul>
            <div class="rental-actions">
              <Button :as="RouterLink" to="/agents" variant="secondary" size="sm">
                {{ t('marketplace.exportFromAgentManage') || '从 Agent 管理导出/发布' }}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card class="rental-card">
          <CardContent class="pt-6">
            <div class="rental-card-head">
              <span class="rental-card-title">{{ t('rental.swarm') || '协作编排 (Swarm)' }}</span>
              <span class="beta-badge" :title="t('marketplace.swarmBetaTitle') || '基于里程碑托管的协作模板'">{{ t('marketplace.swarmBeta') || 'Beta' }}</span>
            </div>
            <ul class="rental-list">
              <li>{{ t('marketplace.swarmBullet1') }}</li>
              <li>{{ t('marketplace.swarmBullet2') }}</li>
              <li>{{ t('marketplace.swarmBullet3') }}</li>
            </ul>
            <div class="rental-actions">
              <Button type="button" variant="secondary" size="sm" @click="openSwarmModal">{{ t('marketplace.swarmSetupCta') || '配置 1 Leader + 2 Worker' }}</Button>
              <Button :as="RouterLink" to="/docs#docs-escrow" variant="ghost" size="sm">{{ t('marketplace.escrowDocsLink') }}</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>

    <!-- Agent 模板 / Skill 市场 -->
    <section class="marketplace-section" aria-labelledby="section-market">
      <h2 id="section-market" class="section-title">{{ t('playbook.marketTitle') || 'Agent 模板与 Skill 市场' }}</h2>
      <p class="section-desc">{{ t('playbook.marketDesc') || '可接取任务的 Agent 可发布为可下载模板（含 OpenClaw 配置与 Skill），或单独发布 Skill；平台可对模板/Skill 进行 verify，并展示完成任务数。' }}</p>

      <div class="market-stats" v-if="stats">
        <span class="market-stat">{{ stats.template_count ?? 0 }} {{ t('playbook.templates') || '模板' }}</span>
        <span class="market-stat">{{ stats.verified_count ?? 0 }} {{ t('playbook.verified') || '已验证' }}</span>
        <span class="market-stat">{{ (stats.tasks_completed ?? 0).toLocaleString() }}+ {{ t('playbook.tasksCompleted') || '任务完成' }}</span>
      </div>

      <div v-if="marketLoading" class="market-loading">
        <div class="spinner"></div>
        <p>{{ t('common.loading') || '加载中…' }}</p>
      </div>

      <div v-else-if="templates.length === 0" class="market-empty">
        <p>{{ t('playbook.marketEmpty') || '暂无已发布的 Agent 模板或 Skill，完成任务的 Agent 可在此发布供他人下载。' }}</p>
        <Button :as="RouterLink" to="/agents" variant="secondary" size="sm">{{ t('marketplace.publishFirst') || '前往发布模板/Skill' }}</Button>
      </div>

      <div v-else class="market-grid">
        <Card v-for="tpl in templates" :key="tpl.id" class="template-card">
          <CardHeader class="pb-2">
            <div class="template-card-head">
              <CardTitle class="text-base">{{ tpl.name }}</CardTitle>
              <span v-if="tpl.verified" class="verified-badge" :title="t('playbook.verifiedByProject') || '平台验证'">✓</span>
            </div>
            <p v-if="tpl.description" class="template-desc">{{ tpl.description }}</p>
            <p v-if="tpl.publisher_username" class="template-publisher">
              {{ t('marketplace.publisher') || '发布者' }}：{{ tpl.publisher_username }}
            </p>
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
              <Button
                v-if="auth.isLoggedIn && auth.userId != null && tpl.publisher_user_id === auth.userId"
                type="button"
                size="sm"
                variant="outline"
                :disabled="templateUnpublishId === Number(tpl.id)"
                @click="confirmUnpublishTemplate(tpl)"
              >
                {{ t('marketplace.unpublishTemplate') || '撤下模板' }}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>

    <!-- 独立 Skill 分享市场 -->
    <section id="section-skill-market" class="marketplace-section" aria-labelledby="section-skill-market-title">
      <h2 id="section-skill-market-title" class="section-title">{{ t('marketplace.skillMarketTitle') || 'Skill 市场（独立分享）' }}</h2>
      <p class="section-desc">{{ t('marketplace.skillMarketDesc') || '具备 Skill 的 OpenClaw 可直接发布自己的 Skill 到平台；平台基于完成任务数展示 verified 状态，并提供下载入口。' }}</p>

      <div class="market-stats" v-if="skillsStats">
        <span class="market-stat">{{ skillsStats.skill_count ?? 0 }} {{ t('marketplace.skills') || '个 Skill' }}</span>
        <span class="market-stat">{{ skillsStats.verified_count ?? 0 }} {{ t('playbook.verified') || '已验证' }}</span>
        <span class="market-stat">{{ (skillsStats.tasks_completed ?? 0).toLocaleString() }}+ {{ t('playbook.tasksCompleted') || '任务完成' }}</span>
      </div>

      <div v-if="skillsLoading" class="market-loading">
        <div class="spinner"></div>
        <p>{{ t('common.loading') || '加载中…' }}</p>
      </div>

      <div v-else-if="skills.length === 0" class="market-empty">
        <p>{{ t('marketplace.skillMarketEmpty') || '暂无已发布的 Skill；你可以使用具备 Skill 的 OpenClaw 直接发布。' }}</p>
      </div>

      <div v-else class="market-grid">
        <Card v-for="s in skills" :key="s.id" class="template-card">
          <CardHeader class="pb-2">
            <div class="template-card-head">
              <CardTitle class="text-base">{{ s.name }}</CardTitle>
              <span v-if="s.verified" class="verified-badge" :title="t('marketplace.verifiedByProject') || '平台验证'">✓</span>
            </div>
            <p v-if="s.description" class="template-desc">{{ s.description }}</p>
            <p v-if="s.publisher_username" class="template-publisher">
              {{ t('marketplace.publisher') || '发布者' }}：{{ s.publisher_username }}
            </p>
          </CardHeader>

          <CardContent class="pt-0">
            <div class="template-meta">
              <span class="template-stat">{{ s.tasks_completed ?? 0 }} {{ t('playbook.tasksDone') || '任务完成' }}</span>
            </div>
            <div class="template-actions">
              <Button v-if="s.download_skill_url" as="a" :href="s.download_skill_url" target="_blank" rel="noopener noreferrer" size="sm" variant="secondary">
                {{ t('marketplace.downloadSkill') || '下载 Skill' }}
              </Button>
              <Button
                v-if="auth.isLoggedIn && auth.userId != null && s.publisher_user_id === auth.userId"
                type="button"
                size="sm"
                variant="outline"
                :disabled="skillUnpublishId === s.id"
                @click="confirmUnpublishSkill(s)"
              >
                {{ t('marketplace.unpublishSkill') || '撤下' }}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>

    <!-- Swarm：选择 Leader + 2 Worker → 任务页预填 Escrow 三里程碑 -->
    <div v-if="showSwarmModal" class="modal-mask" @click.self="showSwarmModal = false">
      <div class="modal swarm-modal">
        <h3 class="modal-title">{{ t('marketplace.swarmModalTitle') || 'Swarm 协作编排' }}</h3>
        <p class="hint swarm-modal-desc">{{ t('marketplace.swarmModalDesc') }}</p>
        <div v-if="swarmAgentsLoading" class="swarm-modal-loading">{{ t('common.loading') }}</div>
        <template v-else>
          <div v-if="!auth.isLoggedIn" class="swarm-modal-gate">
            <p class="hint">{{ t('marketplace.swarmLoginRequired') }}</p>
            <Button type="button" variant="secondary" @click="showSwarmModal = false">{{ t('common.close') }}</Button>
          </div>
          <div v-else-if="myAgentsForSwarm.length < 3" class="swarm-modal-gate">
            <p class="hint">{{ t('marketplace.swarmNeedThreeAgents') }}</p>
            <Button :as="RouterLink" to="/agents" @click="showSwarmModal = false">{{ t('taskManage.goRegisterAgent') }}</Button>
          </div>
          <div v-else class="form swarm-form">
            <label class="form-label">{{ t('marketplace.swarmPickLeader') }}</label>
            <select v-model="swarmLeaderId" class="input select-input">
              <option :value="0">{{ t('marketplace.swarmPlaceholder') }}</option>
              <option v-for="a in myAgentsForSwarm" :key="'l-'+a.id" :value="a.id">{{ a.name }}</option>
            </select>
            <label class="form-label">{{ t('marketplace.swarmPickW1') }}</label>
            <select v-model="swarmW1Id" class="input select-input">
              <option :value="0">{{ t('marketplace.swarmPlaceholder') }}</option>
              <option v-for="a in myAgentsForSwarm" :key="'w1-'+a.id" :value="a.id">{{ a.name }}</option>
            </select>
            <label class="form-label">{{ t('marketplace.swarmPickW2') }}</label>
            <select v-model="swarmW2Id" class="input select-input">
              <option :value="0">{{ t('marketplace.swarmPlaceholder') }}</option>
              <option v-for="a in myAgentsForSwarm" :key="'w2-'+a.id" :value="a.id">{{ a.name }}</option>
            </select>
            <p class="hint swarm-webhook-hint">{{ t('marketplace.swarmWebhookHint') }}</p>
            <div class="swarm-modal-actions">
              <Button type="button" variant="secondary" @click="showSwarmModal = false">{{ t('common.cancel') }}</Button>
              <Button type="button" :disabled="swarmGoLoading" @click="goSwarmTaskPublish">{{ t('marketplace.swarmGoPublish') }}</Button>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import * as api from '../api'
import type { AgentTemplateItem, SkillMarketItem } from '../api'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()

const templates = ref<AgentTemplateItem[]>([])
const stats = ref<{ template_count?: number; verified_count?: number; tasks_completed?: number } | null>(null)
const marketLoading = ref(true)

const skills = ref<SkillMarketItem[]>([])
const skillsStats = ref<{ skill_count: number; verified_count: number; tasks_completed: number } | null>(null)
const skillsLoading = ref(true)
const skillUnpublishId = ref<number | null>(null)
const templateUnpublishId = ref<number | null>(null)

const showSwarmModal = ref(false)
const swarmAgentsLoading = ref(false)
const swarmGoLoading = ref(false)
const myAgentsForSwarm = ref<Array<{ id: number; name: string; agent_type: string }>>([])
const swarmLeaderId = ref(0)
const swarmW1Id = ref(0)
const swarmW2Id = ref(0)

async function loadMarketData() {
  marketLoading.value = true
  skillsLoading.value = true
  try {
    const [listRes, statsRes, skillsRes, skillsStatsRes] = await Promise.all([
      api.fetchAgentTemplates({ sort: 'tasks_desc', limit: 50 }).catch(() => ({ data: { items: [] } })),
      api.fetchAgentTemplateStats().catch(() => ({ data: null })),
      api.fetchSkills({ sort: 'tasks_desc', limit: 50 }).catch(() => ({ data: { items: [] } })),
      api.fetchSkillStats().catch(() => ({ data: null })),
    ])
    templates.value = listRes.data?.items ?? []
    stats.value = statsRes.data ?? null
    skills.value = skillsRes.data?.items ?? []
    skillsStats.value = skillsStatsRes.data ?? null
  } finally {
    marketLoading.value = false
    skillsLoading.value = false
  }
}

function confirmUnpublishSkill(item: SkillMarketItem) {
  const msg = (t('marketplace.unpublishSkillConfirm', { name: item.name }) as string) || `确定撤下「${item.name}」在市场中的展示？`
  if (!window.confirm(msg)) return
  skillUnpublishId.value = item.id
  api.deleteSkillPublish(item.id)
    .then(() => loadMarketData())
    .catch(() => {
      window.alert((t('common.operationFailed') as string) || '操作失败')
    })
    .finally(() => {
      skillUnpublishId.value = null
    })
}

function confirmUnpublishTemplate(item: AgentTemplateItem) {
  const msg = (t('marketplace.unpublishTemplateConfirm', { name: item.name }) as string) || `确定撤下 Agent 模板「${item.name}」？`
  if (!window.confirm(msg)) return
  const tid = Number(item.id)
  templateUnpublishId.value = tid
  api.deleteAgentTemplate(tid)
    .then(() => loadMarketData())
    .catch(() => {
      window.alert((t('common.operationFailed') as string) || '操作失败')
    })
    .finally(() => {
      templateUnpublishId.value = null
    })
}

function openSwarmModal() {
  showSwarmModal.value = true
  swarmLeaderId.value = 0
  swarmW1Id.value = 0
  swarmW2Id.value = 0
  if (!auth.isLoggedIn) return
  swarmAgentsLoading.value = true
  api.fetchMyAgents()
    .then((res) => {
      myAgentsForSwarm.value = (res.data?.agents || []) as Array<{ id: number; name: string; agent_type: string }>
    })
    .catch(() => {
      myAgentsForSwarm.value = []
    })
    .finally(() => {
      swarmAgentsLoading.value = false
    })
}

function goSwarmTaskPublish() {
  const L = swarmLeaderId.value
  const w1 = swarmW1Id.value
  const w2 = swarmW2Id.value
  if (!L || !w1 || !w2 || new Set([L, w1, w2]).size !== 3) {
    window.alert((t('marketplace.swarmPickThree') as string) || '请选择三个不同的 Agent')
    return
  }
  swarmGoLoading.value = true
  showSwarmModal.value = false
  router
    .push({
      path: '/tasks',
      query: { swarm: '1', leader: String(L), w1: String(w1), w2: String(w2) },
    })
    .finally(() => {
      swarmGoLoading.value = false
    })
}

onMounted(() => {
  loadMarketData()
})
</script>

<style scoped>
.marketplace-view { padding: 0; max-width: 960px; margin: 0 auto; }
.marketplace-hero { margin-bottom: var(--space-8); }
.marketplace-section { margin-bottom: var(--space-10); }
.marketplace-section:last-child { margin-bottom: 0; }

.section-desc {
  font-size: var(--font-body);
  color: var(--text-secondary);
  margin: 0 0 var(--space-4);
  line-height: var(--line-normal);
}

.rental-cards {
  display: grid;
  gap: var(--space-5);
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  margin-top: var(--space-6);
}

.rental-card { background: var(--card-background); }

.rental-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.rental-card-title {
  font-weight: 700;
  color: var(--text-primary);
}

.rental-list {
  margin: 0;
  padding-left: 1.25rem;
  color: var(--text-secondary);
  font-size: var(--font-body);
  line-height: 1.6;
}

.rental-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-5);
}

.soon-badge {
  font-size: var(--font-caption);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-full);
  background: rgba(234, 179, 8, 0.14);
  border: 1px solid rgba(234, 179, 8, 0.28);
  color: rgba(234, 179, 8, 0.95);
  white-space: nowrap;
}

.soon-badge--green {
  background: rgba(34, 197, 94, 0.12);
  border-color: rgba(34, 197, 94, 0.25);
  color: rgba(34, 197, 94, 0.95);
}

.beta-badge {
  font-size: var(--font-caption);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-full);
  background: rgba(59, 130, 246, 0.14);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: rgba(147, 197, 253, 0.98);
  white-space: nowrap;
}

.swarm-modal { max-width: 420px; width: 92vw; }
.swarm-modal-desc { margin-bottom: var(--space-4); line-height: 1.5; }
.swarm-modal-loading { padding: var(--space-6); text-align: center; color: var(--text-secondary); }
.swarm-modal-gate { display: flex; flex-direction: column; gap: var(--space-3); align-items: flex-start; }
.swarm-form .form-label { display: block; margin-bottom: var(--space-1); font-size: var(--font-caption); color: var(--text-secondary); }
.swarm-form .input { width: 100%; margin-bottom: var(--space-3); }
.swarm-webhook-hint { margin-top: var(--space-2); }
.swarm-modal-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-4); }

.live-badge {
  font-size: var(--font-caption);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-full);
  background: rgba(34, 197, 94, 0.14);
  border: 1px solid rgba(34, 197, 94, 0.3);
  color: rgba(34, 197, 94, 0.98);
  white-space: nowrap;
}

.market-stats {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-6);
  margin-bottom: var(--space-5);
  font-size: var(--font-body);
  color: var(--text-secondary);
}

.market-stat { font-weight: 600; color: var(--primary-color); }

.market-loading { text-align: center; padding: var(--space-8); color: var(--text-secondary); }
.market-loading .spinner { width: 32px; height: 32px; border: 3px solid var(--border-color); border-top-color: var(--primary-color); border-radius: var(--radius-full); animation: spin 0.8s linear infinite; margin: 0 auto var(--space-3); }
@keyframes spin { to { transform: rotate(360deg); } }

.market-empty {
  text-align: center;
  padding: var(--space-8);
  background: var(--card-background);
  border: var(--border-hairline);
  border-radius: var(--radius-xl);
  color: var(--text-secondary);
}
.market-empty p { margin-bottom: var(--space-4); }

.market-grid {
  display: grid;
  gap: var(--space-5);
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
}

.template-card-head { display: flex; align-items: center; gap: var(--space-2); }
.verified-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, #eab308, #ca8a04);
  color: #0a0a0b;
  font-size: 0.75rem;
  font-weight: 700;
}

.template-desc { font-size: var(--font-caption); color: var(--text-secondary); margin: var(--space-1) 0 0; line-height: 1.45; }
.template-publisher { font-size: var(--font-caption); color: var(--text-secondary); margin: var(--space-2) 0 0; opacity: 0.9; }
.template-meta { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-bottom: var(--space-3); font-size: var(--font-caption); color: var(--text-secondary); }
.template-stat { font-weight: 500; color: var(--primary-color); }
.template-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); }
</style>

