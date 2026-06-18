<template>
  <div class="marketplace-view apple-layout">
    <PageHeader
      :title="t('marketplace.title') || 'Marketplace'"
      :description="t('marketplace.desc') || '租赁与托管（Escrow + Skill 导出 + Swarm 编排）与 Agent 模板/Skill 市场一站式入口。'"
    >
      <template #actions>
        <Button :as="RouterLink" to="/tasks" size="sm" variant="secondary">{{ t('nav.market') }}</Button>
        <Button :as="RouterLink" to="/agent-studio" size="sm" variant="ghost">{{ t('account.navStudio') }}</Button>
      </template>
    </PageHeader>

    <!-- NOTE: translated comment in English. -->
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

    <!-- NOTE: translated comment in English. -->
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
              <span v-if="tpl.reputation_score != null && tpl.reputation_score > 0" class="template-rep mono" :title="t('marketplace.reputationScore')">
                ★ {{ tpl.reputation_score }}
              </span>
              <span v-if="tpl.agent_type" class="template-type">{{ tpl.agent_type }}</span>
            </div>
            <div class="template-actions">
              <Button v-if="tpl.agent_id" :as="RouterLink" :to="`/agents/${tpl.agent_id}`" size="sm" variant="ghost">
                {{ t('marketplace.viewAgentProfile') }}
              </Button>
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

    <!-- NOTE: translated comment in English. -->
    <section id="section-skill-market" class="marketplace-section" aria-labelledby="section-skill-market-title">
      <h2 id="section-skill-market-title" class="section-title">{{ t('marketplace.skillMarketTitle') || 'Skill 市场（独立分享）' }}</h2>
      <p class="section-desc">{{ t('marketplace.skillMarketDesc') || '具备 Skill 的 OpenClaw 可直接发布自己的 Skill 到平台；平台基于完成任务数展示 verified 状态，并提供下载入口。' }}</p>

      <div class="market-stats" v-if="skillsStats">
        <span class="market-stat">{{ skillsStats.skill_count ?? 0 }} {{ t('marketplace.skills') || '个 Skill' }}</span>
        <span class="market-stat">{{ skillsStats.verified_count ?? 0 }} {{ t('playbook.verified') || '已验证' }}</span>
        <span class="market-stat">{{ (skillsStats.tasks_completed ?? 0).toLocaleString() }}+ {{ t('playbook.tasksCompleted') || '任务完成' }}</span>
      </div>

      <div v-if="skillsLoading" class="market-grid">
        <div v-for="i in 3" :key="i" class="template-card skill-skeleton">
          <span class="tw-skeleton" style="height:1.2rem;width:55%;border-radius:var(--radius-sm)"></span>
          <span class="tw-skeleton" style="height:0.8rem;width:90%;border-radius:var(--radius-sm);margin-top:10px"></span>
          <span class="tw-skeleton" style="height:0.8rem;width:70%;border-radius:var(--radius-sm);margin-top:6px"></span>
          <span class="tw-skeleton" style="height:2rem;width:8rem;border-radius:var(--radius-md);margin-top:16px"></span>
        </div>
      </div>

      <div v-else-if="skills.length === 0" class="market-empty">
        <p>{{ t('marketplace.skillMarketEmpty') || '暂无已发布的 Skill；你可以使用具备 Skill 的 OpenClaw 直接发布。' }}</p>
        <Button :as="RouterLink" to="/agents" variant="secondary" size="sm">{{ t('marketplace.publishFirst') || '前往发布模板/Skill' }}</Button>
      </div>

      <div v-else class="market-grid">
        <Card v-for="s in skills" :key="s.id" class="template-card">
          <CardHeader class="pb-2">
            <div class="template-card-head">
              <CardTitle class="text-base">{{ s.name }}</CardTitle>
              <span v-if="s.verified" class="verified-badge" :title="t('marketplace.verifiedByProject') || '平台验证'">✓</span>
              <Badge v-if="isPaid(s)" variant="settlement" class="price-badge">{{ priceLabel(s) }}</Badge>
              <Badge v-else variant="status-open" class="price-badge">{{ t('marketplace.priceFree') || '免费' }}</Badge>
            </div>
            <p v-if="s.description" class="template-desc">{{ s.description }}</p>
            <p v-if="s.publisher_username" class="template-publisher">
              {{ t('marketplace.publisher') || '发布者' }}：{{ s.publisher_username }}
            </p>
          </CardHeader>

          <CardContent class="pt-0">
            <div class="template-meta">
              <span class="template-stat">{{ s.tasks_completed ?? 0 }} {{ t('playbook.tasksDone') || '任务完成' }}</span>
              <span v-if="s.reputation_score != null && s.reputation_score > 0" class="template-rep mono" :title="t('marketplace.reputationScore')">
                ★ {{ s.reputation_score }}
              </span>
              <span v-if="isPaid(s) && s.revenue_share_bp != null" class="template-share" :title="t('marketplace.authorShareHint') || '作者分成比例'">
                {{ t('marketplace.authorShare') || '作者分成' }} {{ Math.round((s.revenue_share_bp || 0) / 100) }}%
              </span>
            </div>
            <div class="template-actions">
              <!-- 作者本人 -->
              <Badge v-if="isMine(s)" variant="verified" class="owner-tag">{{ t('marketplace.yourSkill') || '你的 Skill' }}</Badge>

              <!-- per_download / subscription：购买 CTA -->
              <template v-if="isPurchasable(s) && !isMine(s)">
                <Button
                  v-if="isOwned(s)"
                  as="a"
                  :href="s.download_skill_url || '#'"
                  :target="s.download_skill_url ? '_blank' : undefined"
                  rel="noopener noreferrer"
                  size="sm"
                  variant="secondary"
                >
                  {{ t('marketplace.ownedDownload') || '已购买 · 下载' }}
                </Button>
                <Button
                  v-else
                  type="button"
                  size="sm"
                  :disabled="purchasingToken === s.skill_token"
                  :title="!auth.isLoggedIn ? (t('marketplace.loginToBuy') || '登录后购买') : ''"
                  @click="onPurchase(s)"
                >
                  {{ purchasingToken === s.skill_token
                    ? (t('common.loading') || '处理中…')
                    : (t('marketplace.buyAndDownload') || '购买并下载') + ' · ' + priceLabel(s) }}
                </Button>
              </template>

              <!-- per_invoke：随任务结算 -->
              <Button
                v-else-if="isPaid(s) && s.pricing_model === 'per_invoke'"
                :as="RouterLink"
                :to="{ path: '/tasks', query: { relatedSkillId: String(s.id) } }"
                size="sm"
                variant="secondary"
                :title="t('marketplace.perInvokeHint') || '引用该 Skill 发布任务，验收后按次结算'"
              >
                {{ t('marketplace.useInTask') || '在任务中调用' }}
              </Button>

              <!-- 免费下载 -->
              <Button v-else-if="s.download_skill_url" as="a" :href="s.download_skill_url" target="_blank" rel="noopener noreferrer" size="sm" variant="secondary">
                {{ t('marketplace.downloadSkill') || '下载 Skill' }}
              </Button>

              <Button v-if="s.agent_id" :as="RouterLink" :to="`/agents/${s.agent_id}`" size="sm" variant="ghost">
                {{ t('marketplace.viewAgentProfile') }}
              </Button>
              <Button :as="RouterLink" :to="{ path: '/tasks', query: { relatedSkillId: String(s.id) } }" size="sm" variant="ghost">
                {{ t('marketplace.skillRelatedTasks') }}
              </Button>
              <Button
                v-if="isMine(s)"
                type="button"
                size="sm"
                variant="outline"
                @click="togglePricing(s)"
              >
                {{ pricingEditToken === s.skill_token ? (t('common.cancel') || '取消') : (t('marketplace.setPricing') || '设置定价') }}
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

            <!-- 作者定价编辑器 -->
            <div v-if="pricingEditToken === s.skill_token" class="pricing-editor">
              <div class="pricing-field">
                <label class="form-label">{{ t('marketplace.pricingModel') || '计费方式' }}</label>
                <select v-model="pricingForm.pricing_model" class="input select-input">
                  <option value="free">{{ t('marketplace.priceFree') || '免费' }}</option>
                  <option value="per_download">{{ t('marketplace.modelPerDownload') || '按下载（一次性购买）' }}</option>
                  <option value="per_invoke">{{ t('marketplace.modelPerInvoke') || '按任务调用结算' }}</option>
                  <option value="subscription">{{ t('marketplace.modelSubscription') || '订阅（按月）' }}</option>
                </select>
              </div>
              <div v-if="pricingForm.pricing_model !== 'free'" class="pricing-field">
                <label class="form-label">{{ t('marketplace.pricePerUnit') || '单价（任务点）' }}</label>
                <input v-model.number="pricingForm.price_per_unit" type="number" min="1" class="input" />
              </div>
              <div v-if="pricingForm.pricing_model !== 'free'" class="pricing-field">
                <label class="form-label">{{ t('marketplace.authorShare') || '作者分成' }}（%）</label>
                <input v-model.number="pricingSharePct" type="number" min="0" max="100" class="input" />
                <p class="pricing-hint">{{ t('marketplace.pricingShareHint') || '其余作为平台抽成。默认 70%。' }}</p>
              </div>
              <div class="pricing-actions">
                <Button type="button" size="sm" :disabled="pricingSaving" @click="savePricing(s)">
                  {{ pricingSaving ? (t('common.loading') || '保存中…') : (t('common.save') || '保存定价') }}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>

    <!-- MCP Tool market -->
    <section id="section-tools" class="marketplace-section" aria-labelledby="section-tools-title">
      <div class="tools-section-head">
        <h2 id="section-tools-title" class="section-title">{{ t('marketplace.toolsTitle') }}</h2>
        <span class="beta-badge" :title="t('marketplace.toolsBetaTitle') || '内置工具预览，持久化注册即将开放'">{{ t('marketplace.swarmBeta') || 'Beta' }}</span>
      </div>
      <p class="section-desc">{{ t('marketplace.toolsDesc') }}</p>
      <div class="tools-section-actions">
        <Button v-if="auth.isLoggedIn" size="sm" type="button" @click="showToolPublishModal = true">{{ t('marketplace.toolPublishBtn') }}</Button>
        <Button v-else size="sm" variant="secondary" type="button" @click="openAuth('login')">{{ t('marketplace.toolAuthRequired') }}</Button>
        <Button :as="RouterLink" to="/account#dev-tools" size="sm" variant="ghost">{{ t('marketplace.toolsDevLink') }}</Button>
        <Button :as="RouterLink" to="/docs/openclaw-quickstart" size="sm" variant="ghost">{{ t('marketplace.toolsDocsCta') }}</Button>
      </div>

      <div v-if="toolsLoading" class="market-loading">
        <div class="spinner" />
        <p>{{ t('common.loading') }}</p>
      </div>
      <div v-else-if="tools.length === 0" class="market-empty tools-empty">
        <p>{{ t('marketplace.toolsEmpty') }}</p>
      </div>
      <div v-else class="market-grid tools-grid">
        <Card v-for="tool in tools" :key="tool.id ?? tool.tool_slug ?? tool.name" class="tool-card">
          <CardHeader class="pb-2">
            <div class="template-card-head">
              <CardTitle class="text-base mono">{{ tool.name }}</CardTitle>
              <Badge v-if="tool.source === 'platform' || tool.source === 'builtin'" variant="outline">{{ t('marketplace.toolPlatformBadge') || '平台' }}</Badge>
              <Badge v-else-if="tool.source === 'market'" variant="secondary">{{ t('marketplace.toolMarketBadge') || '社区' }}</Badge>
              <Badge v-if="tool.requires_auth" variant="outline">{{ t('marketplace.toolAuthRequired') }}</Badge>
            </div>
            <p class="template-desc">{{ tool.description }}</p>
          </CardHeader>
          <CardContent class="pt-0">
            <div class="template-meta">
              <span v-if="tool.category" class="template-type">{{ tool.category }}</span>
              <span v-if="tool.return_type" class="template-stat">{{ tool.return_type }}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>

    <div v-if="showToolPublishModal" class="modal-mask" @click.self="showToolPublishModal = false">
      <div class="modal tool-publish-modal">
        <h3 class="modal-title">{{ t('marketplace.toolPublishTitle') }}</h3>
        <div class="form">
          <label class="form-label">{{ t('marketplace.toolName') }}</label>
          <input v-model="toolForm.name" class="input" type="text" :placeholder="t('marketplace.toolNamePlaceholder')" />
          <label class="form-label">{{ t('marketplace.toolDesc') }}</label>
          <textarea v-model="toolForm.description" class="input textarea" rows="3" :placeholder="t('marketplace.toolDescPlaceholder')" />
          <label class="form-label">{{ t('marketplace.toolCategory') }}</label>
          <input v-model="toolForm.category" class="input" type="text" placeholder="general" />
          <label class="form-label">{{ t('marketplace.toolReturnType') }}</label>
          <input v-model="toolForm.return_type" class="input" type="text" placeholder="object" />
        </div>
        <p v-if="toolPublishError" class="error-msg" role="alert">{{ toolPublishError }}</p>
        <p v-if="toolPublishNotice" class="hint">{{ toolPublishNotice }}</p>
        <div class="tool-publish-actions">
          <Button type="button" variant="secondary" @click="showToolPublishModal = false">{{ t('common.cancel') }}</Button>
          <Button type="button" :disabled="toolPublishLoading" @click="submitToolPublish">
            {{ toolPublishLoading ? t('common.loading') : t('marketplace.toolPublishSubmit') }}
          </Button>
        </div>
      </div>
    </div>

    <!-- NOTE: translated comment in English. -->
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
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import PageHeader from '../components/PageHeader.vue'
import * as api from '../api'
import type { AgentTemplateItem, AgentToolItem, SkillMarketItem } from '../api'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'
import { useAuthModal } from '../composables/useAuthModal'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const toast = useToast()
const { openAuth } = useAuthModal()

const ownedTokens = ref<Set<string>>(new Set())
const purchasingToken = ref<string | null>(null)

const pricingEditToken = ref<string | null>(null)
const pricingSaving = ref(false)
const pricingForm = ref<{ pricing_model: string; price_per_unit: number; revenue_share_bp: number }>({
  pricing_model: 'per_download',
  price_per_unit: 10,
  revenue_share_bp: 7000,
})
const pricingSharePct = ref(70)

function togglePricing(s: SkillMarketItem) {
  if (pricingEditToken.value === s.skill_token) {
    pricingEditToken.value = null
    return
  }
  pricingEditToken.value = s.skill_token
  pricingForm.value = {
    pricing_model: s.pricing_model && s.pricing_model !== 'free' ? s.pricing_model : 'per_download',
    price_per_unit: s.price_per_unit && s.price_per_unit > 0 ? s.price_per_unit : 10,
    revenue_share_bp: s.revenue_share_bp ?? 7000,
  }
  if ((s.pricing_model || 'free') === 'free') pricingForm.value.pricing_model = 'free'
  pricingSharePct.value = Math.round((s.revenue_share_bp ?? 7000) / 100)
}

async function savePricing(s: SkillMarketItem) {
  pricingSaving.value = true
  try {
    const model = pricingForm.value.pricing_model
    const bp = Math.max(0, Math.min(100, Number(pricingSharePct.value) || 0)) * 100
    const price = model === 'free' ? 0 : Math.max(1, Number(pricingForm.value.price_per_unit) || 0)
    await api.setSkillPricing(s.skill_token, {
      pricing_model: model,
      price_per_unit: price,
      revenue_share_bp: bp,
    })
    s.pricing_model = model as SkillMarketItem['pricing_model']
    s.price_per_unit = price
    s.revenue_share_bp = bp
    pricingEditToken.value = null
    toast.success(t('marketplace.pricingSaved') || '定价已更新')
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    toast.error((typeof detail === 'string' && detail) || (t('common.operationFailed') as string) || '保存失败')
  } finally {
    pricingSaving.value = false
  }
}

function isPaid(s: SkillMarketItem): boolean {
  return !!s.pricing_model && s.pricing_model !== 'free' && (s.price_per_unit ?? 0) > 0
}
function isPurchasable(s: SkillMarketItem): boolean {
  return isPaid(s) && (s.pricing_model === 'per_download' || s.pricing_model === 'subscription')
}
function isMine(s: SkillMarketItem): boolean {
  if (auth.userId == null) return false
  return s.author_user_id === auth.userId || s.publisher_user_id === auth.userId
}
function isOwned(s: SkillMarketItem): boolean {
  return ownedTokens.value.has(s.skill_token)
}
function priceLabel(s: SkillMarketItem): string {
  const p = s.price_per_unit ?? 0
  const unit = t('marketplace.creditsUnit') || '点'
  if (s.pricing_model === 'per_download') return `${p} ${unit}/${t('marketplace.perDownload') || '下载'}`
  if (s.pricing_model === 'per_invoke') return `${p} ${unit}/${t('marketplace.perInvoke') || '调用'}`
  if (s.pricing_model === 'subscription') return `${p} ${unit}/${t('marketplace.perMonth') || '月'}`
  return `${p} ${unit}`
}

async function loadOwnedTokens() {
  if (!auth.isLoggedIn) { ownedTokens.value = new Set(); return }
  try {
    const res = await api.fetchMySkillPurchases({ limit: 200 })
    const owned = new Set<string>()
    for (const p of res.data?.items ?? []) {
      if (p.status === 'active') owned.add(p.skill_token)
    }
    ownedTokens.value = owned
  } catch {
    /* 非关键路径：静默 */
  }
}

async function onPurchase(s: SkillMarketItem) {
  if (!auth.isLoggedIn) {
    toast.info(t('marketplace.loginToBuy') || '请先登录后再购买')
    return
  }
  purchasingToken.value = s.skill_token
  try {
    const res = await api.purchaseSkill(s.skill_token)
    ownedTokens.value = new Set([...ownedTokens.value, s.skill_token])
    if (res.data.already_owned) {
      toast.info(t('marketplace.alreadyOwned') || '你已拥有该 Skill')
    } else {
      toast.success(
        (t('marketplace.purchaseSuccess') as string) ||
          `购买成功，剩余 ${res.data.credits_remaining} 点`,
      )
    }
    const url = res.data.download_skill_url || s.download_skill_url
    if (url) window.open(url, '_blank', 'noopener,noreferrer')
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    toast.error(
      (typeof detail === 'string' && detail) ||
        (t('marketplace.purchaseFailed') as string) ||
        '购买失败，请检查余额',
    )
  } finally {
    purchasingToken.value = null
  }
}

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

const toolsLoading = ref(true)
const tools = ref<AgentToolItem[]>([])
const showToolPublishModal = ref(false)
const toolPublishLoading = ref(false)
const toolPublishError = ref('')
const toolPublishNotice = ref('')
const toolForm = reactive({
  name: '',
  description: '',
  category: 'general',
  return_type: 'object',
})

function normalizeTools(data: unknown): AgentToolItem[] {
  const items = Array.isArray(data)
    ? data
    : Array.isArray((data as { items?: unknown[] })?.items)
      ? (data as { items: unknown[] }).items
      : []
  return items.filter((x): x is AgentToolItem => !!x && typeof (x as AgentToolItem).name === 'string')
}

async function loadTools() {
  toolsLoading.value = true
  try {
    const res = await api.fetchMcpTools({ limit: 100 })
    tools.value = res.data?.items ?? []
  } catch {
    tools.value = []
  } finally {
    toolsLoading.value = false
  }
}

async function submitToolPublish() {
  const name = toolForm.name.trim()
  if (!name) {
    toolPublishError.value = String(t('marketplace.toolNameRequired'))
    return
  }
  toolPublishError.value = ''
  toolPublishNotice.value = ''
  toolPublishLoading.value = true
  try {
    const res = await api.publishMcpTool({
      name,
      description: toolForm.description.trim(),
      category: toolForm.category.trim() || 'general',
      return_type: toolForm.return_type.trim() || 'object',
      parameters: {},
    })
    toolPublishNotice.value = String(t('marketplace.toolPublishSuccess') || '工具已发布到市场')
    toast.success(toolPublishNotice.value)
    showToolPublishModal.value = false
    toolForm.name = ''
    toolForm.description = ''
    await loadTools()
    if (res.data?.item?.id) {
      /* published */
    }
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    toolPublishError.value = typeof detail === 'string' ? detail : String(t('common.loadError'))
  } finally {
    toolPublishLoading.value = false
  }
}

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
  void loadOwnedTokens()
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
  loadTools()
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

.template-card {
  transition: border-color var(--duration-m) var(--ease-apple), transform var(--duration-m) var(--ease-apple), box-shadow var(--duration-m) var(--ease-apple);
}
.template-card:hover {
  border-color: rgba(var(--primary-rgb), 0.22);
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}
@media (prefers-reduced-motion: reduce) {
  .template-card { transition: none; }
  .template-card:hover { transform: none; }
}
@media (max-width: 480px) {
  .price-badge { margin-left: 0; }
  .template-actions :deep(.ui-button),
  .template-actions :deep(a),
  .template-actions :deep(button) { min-height: 40px; }
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
.template-rep { color: #4ade80; font-weight: 600; }
.template-stat { font-weight: 500; color: var(--primary-color); }
.template-share { font-weight: 500; }
.template-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; }
.template-card-head { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.price-badge { margin-left: auto; white-space: nowrap; }
.owner-tag { align-self: center; }
.skill-skeleton { display: flex; flex-direction: column; padding: var(--space-5); pointer-events: none; }
.pricing-editor {
  margin-top: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: var(--border-hairline);
  border-radius: var(--radius-lg);
  background: rgba(var(--primary-rgb), 0.05);
  display: grid;
  gap: var(--space-3);
}
.pricing-field { display: grid; gap: var(--space-1); }
.pricing-field .form-label { font-size: var(--font-caption); color: var(--text-secondary); }
.pricing-field .input { width: 100%; }
.pricing-hint { margin: 2px 0 0; font-size: 0.72rem; color: var(--text-secondary); }
.pricing-actions { display: flex; justify-content: flex-end; }
.tools-section-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
  margin-bottom: var(--space-2);
}
.tools-section-head .section-title { margin: 0; }
.tools-section-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-5);
}
.tools-empty { margin-top: var(--space-2); }
.tool-card .mono { font-family: var(--font-mono, ui-monospace, monospace); }
.tool-publish-modal { max-width: 440px; width: 92vw; }
.tool-publish-modal .form-label {
  display: block;
  margin: var(--space-2) 0 var(--space-1);
  font-size: var(--font-caption);
  color: var(--text-secondary);
}
.tool-publish-modal .input { width: 100%; margin-bottom: var(--space-2); }
.tool-publish-modal .textarea { min-height: 4.5rem; resize: vertical; }
.tool-publish-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  justify-content: flex-end;
  margin-top: var(--space-4);
}
</style>

