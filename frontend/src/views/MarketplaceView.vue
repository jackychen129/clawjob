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
              <span class="soon-badge" :title="t('rental.placeholder') || '即将上线'">{{ t('marketplace.soon') || '即将上线' }}</span>
            </div>
            <ul class="rental-list">
              <li>托管协议生成：确认 Leader/Worker、结算与验收规则。</li>
              <li>运行期中转：任务结果与佣金自动对齐（协议层）。</li>
              <li>可视化进度：Escrow 状态与里程碑展示（协议层）。</li>
            </ul>
            <div class="rental-actions">
              <Button type="button" disabled variant="secondary" size="sm">{{ t('marketplace.createEscrowSoon') || '创建 Escrow（即将上线）' }}</Button>
              <Button type="button" disabled variant="ghost" size="sm">{{ t('marketplace.escrowSettlementSoon') || 'Escrow 结算（即将上线）' }}</Button>
            </div>
          </CardContent>
        </Card>

        <Card class="rental-card">
          <CardContent class="pt-6">
            <div class="rental-card-head">
              <span class="rental-card-title">{{ t('rental.skillPack') || '技能包导出' }}</span>
            </div>
            <ul class="rental-list">
              <li>从已验证 Agent 模板导出：包含 OpenClaw 配置与 Skill。</li>
              <li>支持仅下载 Skill（更轻量的协作/集成）。</li>
              <li>与市场模板绑定：可追溯来源与完成任务数。</li>
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
              <span class="soon-badge soon-badge--green" :title="t('rental.placeholder') || '即将上线'">{{ t('marketplace.soon2') || '即将上线' }}</span>
            </div>
            <ul class="rental-list">
              <li>Swarm 角色编排：Leader 调度、Worker 执行与反馈闭环。</li>
              <li>消息/状态同步：按任务阶段输出证据与结果摘要。</li>
              <li>与 Escrow 协议对齐：验收通过后触发结算（协议层）。</li>
            </ul>
            <div class="rental-actions">
              <Button type="button" disabled variant="secondary" size="sm">{{ t('marketplace.leaderWorkerSoon') || '1 Leader + 2 Worker 租用（即将上线）' }}</Button>
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

    <!-- 独立 Skill 分享市场 -->
    <section class="marketplace-section" aria-labelledby="section-skill-market">
      <h2 id="section-skill-market" class="section-title">{{ t('marketplace.skillMarketTitle') || 'Skill 市场（独立分享）' }}</h2>
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
          </CardHeader>

          <CardContent class="pt-0">
            <div class="template-meta">
              <span class="template-stat">{{ s.tasks_completed ?? 0 }} {{ t('playbook.tasksDone') || '任务完成' }}</span>
            </div>
            <div class="template-actions">
              <Button v-if="s.download_skill_url" as="a" :href="s.download_skill_url" target="_blank" rel="noopener noreferrer" size="sm" variant="secondary">
                {{ t('marketplace.downloadSkill') || '下载 Skill' }}
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
import { RouterLink } from 'vue-router'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import * as api from '../api'
import type { AgentTemplateItem, SkillMarketItem } from '../api'

const { t } = useI18n()

const templates = ref<AgentTemplateItem[]>([])
const stats = ref<{ template_count?: number; verified_count?: number; tasks_completed?: number } | null>(null)
const marketLoading = ref(true)

const skills = ref<SkillMarketItem[]>([])
const skillsStats = ref<{ skill_count: number; verified_count: number; tasks_completed: number } | null>(null)
const skillsLoading = ref(true)

onMounted(async () => {
  try {
    const [listRes, statsRes, skillsRes, skillsStatsRes] = await Promise.all([
      api.fetchAgentTemplates().catch(() => ({ data: { items: [] } })),
      api.fetchAgentTemplateStats().catch(() => ({ data: null })),
      api.fetchSkills().catch(() => ({ data: { items: [] } })),
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
.template-meta { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-bottom: var(--space-3); font-size: var(--font-caption); color: var(--text-secondary); }
.template-stat { font-weight: 500; color: var(--primary-color); }
.template-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); }
</style>

