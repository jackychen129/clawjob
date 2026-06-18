<script setup lang="ts">
import { toRef } from 'vue'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Textarea } from './ui/textarea'
import { usePublishTaskForm } from '../composables/usePublishTaskForm'

const open = defineModel<boolean>('open', { default: false })

const props = defineProps<{
  accountCredits: number
  myAgentsCount: number
}>()

const emit = defineEmits<{
  published: []
  'credits-updated': []
  'register-hint': []
  'request-auth': []
  'guest-publish': []
  'draft-restored': []
  'draft-saved': []
}>()

const {
  t,
  auth,
  createStep,
  selectedTaskTemplateId,
  publishForm,
  escrowWeightSumHome,
  publishFeeEstimate,
  publishLoading,
  publishError,
  candidates,
  candidatesLoading,
  draftExists,
  applyTaskTemplateHome,
  addEscrowRowHome,
  removeEscrowRowHome,
  saveDraft,
  loadDraft,
  clearDraft,
  closeModal,
  doPublish,
} = usePublishTaskForm({
  open,
  accountCredits: toRef(props, 'accountCredits'),
  myAgentsCount: toRef(props, 'myAgentsCount'),
  onPublished: () => emit('published'),
  onCreditsUpdated: () => emit('credits-updated'),
  onRegisterHint: () => emit('register-hint'),
})

function restoreDraft() {
  loadDraft()
  emit('draft-restored')
}

function handleSaveDraft() {
  saveDraft()
  emit('draft-saved')
}

defineExpose({ draftExists, openWithDraft: () => { loadDraft(); open.value = true }, clearDraft })
</script>

<template>
  <div v-if="open" class="modal-mask" @click.self="closeModal">
    <div class="modal modal--create-task">
      <h3 class="modal-title">{{ t('task.publish') }}</h3>
      <div v-if="!auth.isLoggedIn" class="publish-gate">
        <p class="hint">{{ t('task.publishHint') }}</p>
        <div class="publish-gate-actions">
          <Button type="button" @click="open = false; emit('request-auth')">{{ t('task.loginToPublish') }}</Button>
          <Button type="button" variant="secondary" @click="emit('guest-publish')">{{ t('task.publishAsGuest') }}</Button>
          <Button type="button" variant="ghost" @click="closeModal">{{ t('common.cancel') }}</Button>
        </div>
      </div>
      <div v-else class="create-task-steps">
        <div v-if="draftExists" class="draft-bar">
          <span class="draft-bar__text">{{ t('task.draftExists') || '您有未完成的草稿' }}</span>
          <Button size="sm" variant="secondary" type="button" @click="restoreDraft">{{ t('task.draftRestore') || '从草稿恢复' }}</Button>
          <Button size="sm" variant="ghost" type="button" @click="clearDraft">{{ t('task.draftDiscard') || '丢弃草稿' }}</Button>
        </div>
        <div class="create-step-tabs">
          <button type="button" class="step-tab" :class="{ active: createStep === 1 }" @click="createStep = 1">1. {{ t('taskManage.stepTaskInfo') || '任务信息' }}</button>
          <button type="button" class="step-tab" :class="{ active: createStep === 2 }" @click="createStep = 2">2. {{ t('taskManage.stepReward') || '奖励与回调' }}</button>
          <button type="button" class="step-tab" :class="{ active: createStep === 3 }" @click="createStep = 3">3. {{ t('task.optional') }}</button>
        </div>
        <div v-show="createStep === 1" class="step-panel">
          <div class="form-group form-group--template">
            <label class="form-label">{{ t('task.useTemplate') || '使用模板' }}</label>
            <select v-model="selectedTaskTemplateId" class="input select-input" @change="applyTaskTemplateHome">
              <option value="none">{{ t('task.templateNone') || '从空白创建' }}</option>
              <option value="general">{{ t('task.templateGeneral') || '通用任务' }}</option>
              <option value="best_practice">{{ t('task.templateBestPractice') || '最佳实践分享' }}</option>
              <option value="development">{{ t('task.templateDevelopment') || '需求/开发' }}</option>
              <option value="research">{{ t('task.templateResearch') || '调研' }}</option>
              <option value="writing">{{ t('task.templateWriting') || '写作' }}</option>
              <option value="data">{{ t('task.templateData') || '数据标注' }}</option>
            </select>
            <p class="form-hint">{{ t('task.templateHint') || '选择模板后可自动填充描述与要求结构，便于接取者理解' }}</p>
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('agentGuide.fieldTitle') }} <span class="required">*</span></label>
            <Input v-model="publishForm.title" type="text" :placeholder="t('task.title')" minlength="2" />
            <p class="form-hint">{{ t('task.titleHint') }}</p>
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('task.description') }}</label>
            <Textarea v-model="publishForm.description" rows="4" :placeholder="t('task.requirementsPlaceholder')" />
            <p class="form-hint">{{ t('task.descriptionHint') }}</p>
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('task.category') }}</label>
            <select v-model="publishForm.category" class="input select-input">
              <option value="">{{ t('task.categoryPlaceholder') }}</option>
              <option value="development">{{ t('task.categoryDevelopment') }}</option>
              <option value="design">{{ t('task.categoryDesign') }}</option>
              <option value="research">{{ t('task.categoryResearch') }}</option>
              <option value="writing">{{ t('task.categoryWriting') }}</option>
              <option value="data">{{ t('task.categoryData') }}</option>
              <option value="other">{{ t('task.categoryOther') }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('task.requirements') }}</label>
            <Textarea v-model="publishForm.requirements" rows="2" :placeholder="t('task.requirementsPlaceholder')" />
            <p class="form-hint">{{ t('task.requirementsHint') }}</p>
          </div>
          <div class="form-group form-row-2">
            <div class="form-group">
              <label class="form-label">{{ t('task.location') }}</label>
              <Input v-model="publishForm.location" type="text" :placeholder="t('task.locationPlaceholder')" />
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('task.durationEstimate') }}</label>
              <Input v-model="publishForm.duration_estimate" type="text" :placeholder="t('task.durationPlaceholder')" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('task.skills') }}</label>
            <Input v-model="publishForm.skills_text" type="text" :placeholder="t('task.skillsPlaceholder')" />
          </div>
          <div class="form-group">
            <label class="form-label flex items-center gap-2">
              <input v-model="publishForm.collaborative" type="checkbox" class="rounded border-input" />
              {{ t('task.collaborativePublish') }}
            </label>
            <p class="form-hint">{{ t('task.collaborativePublishHint') }}</p>
          </div>
          <div class="step-actions">
            <Button type="button" variant="ghost" @click="handleSaveDraft">{{ t('task.draftSave') || '保存草稿' }}</Button>
            <Button type="button" @click="createStep = 2">{{ t('common.next') }}</Button>
          </div>
        </div>
        <div v-show="createStep === 2" class="step-panel">
          <div class="form-group form-inline">
            <label class="form-label">{{ t('agentGuide.fieldRewardPoints') }}</label>
            <input v-model.number="publishForm.reward_points" type="number" min="0" class="input input-num" />
          </div>
          <div
            v-if="publishForm.reward_points > 0 && publishFeeEstimate"
            class="publish-fee-card mono text-sm"
            :class="{ 'publish-fee-card--insufficient': !publishFeeEstimate.sufficient }"
            role="status"
          >
            <div class="publish-fee-row">
              <span>{{ t('task.feeEstimateExecutorNet') }}</span>
              <strong>{{ publishFeeEstimate.executor_net_points }}</strong>
            </div>
            <div class="publish-fee-row">
              <span>{{ t('task.feeEstimateCommission') }}（{{ (publishFeeEstimate.commission_rate * 100).toFixed(2) }}%）</span>
              <strong>{{ publishFeeEstimate.commission_points }}</strong>
            </div>
            <div class="publish-fee-row">
              <span>{{ t('task.feeEstimateBalanceAfter') }}</span>
              <strong>{{ publishFeeEstimate.publisher_credits_after }}</strong>
            </div>
            <div v-if="!publishFeeEstimate.sufficient" class="publish-fee-warn">
              {{ t('task.feeEstimateInsufficient', { n: publishForm.reward_points - publishFeeEstimate.publisher_credits }) }}
            </div>
          </div>
          <template v-if="publishForm.reward_points > 0">
            <p class="hint">{{ t('task.webhookHint') }}</p>
            <div class="form-group">
              <label class="form-label">{{ t('agentGuide.fieldWebhook') }}</label>
              <Input v-model="publishForm.completion_webhook_url" class="w-full" type="url" :placeholder="t('task.webhookPlaceholder')" />
            </div>
            <div class="form-group">
              <label class="form-label" for="publish-vhours">{{ t('task.verificationHoursLabel') }}</label>
              <select id="publish-vhours" v-model.number="publishForm.verification_hours" class="input select-input">
                <option :value="6">6</option>
                <option :value="12">12</option>
                <option :value="24">24</option>
                <option :value="48">48</option>
                <option :value="72">72</option>
                <option :value="168">168</option>
              </select>
              <p class="form-hint">{{ t('task.verificationHoursHint') }}</p>
            </div>
            <div class="form-group escrow-block">
              <label class="form-label flex items-center gap-2">
                <input v-model="publishForm.escrow_enabled" type="checkbox" class="rounded border-input" />
                {{ t('task.escrowEnable') || '启用分阶段托管（里程碑）' }}
              </label>
              <p class="form-hint">{{ t('task.escrowHint') || '至少 2 个里程碑，权重之和须为 1。' }}</p>
              <div v-if="publishForm.escrow_enabled" class="escrow-rows">
                <div v-for="(row, idx) in publishForm.escrow_rows" :key="idx" class="escrow-row-wrap">
                  <div class="escrow-row">
                    <Input v-model="row.title" type="text" :placeholder="t('task.escrowMilestoneTitle') || '里程碑名称'" />
                    <input v-model.number="row.weight" type="number" step="0.01" min="0" max="1" class="input input-num escrow-weight" :placeholder="t('task.escrowWeight') || '权重'" />
                    <Button v-if="publishForm.escrow_rows.length > 2" type="button" size="sm" variant="ghost" @click="removeEscrowRowHome(idx)">×</Button>
                  </div>
                  <Textarea
                    v-model="row.acceptance_criteria"
                    rows="2"
                    class="escrow-criteria"
                    :placeholder="t('task.escrowAcceptanceCriteriaPlaceholder') || '里程碑验收要点（可选）'"
                  />
                </div>
                <Button type="button" size="sm" variant="secondary" @click="addEscrowRowHome">{{ t('task.escrowAdd') || '添加里程碑' }}</Button>
                <p class="form-hint escrow-sum">{{ t('task.escrowWeightSum') || '权重合计' }}：{{ escrowWeightSumHome.toFixed(4) }}</p>
              </div>
            </div>
          </template>
          <div class="step-actions">
            <Button type="button" variant="ghost" @click="handleSaveDraft">{{ t('task.draftSave') || '保存草稿' }}</Button>
            <Button type="button" variant="secondary" @click="createStep = 1">{{ t('common.prev') }}</Button>
            <Button type="button" @click="createStep = 3">{{ t('common.next') }}</Button>
          </div>
        </div>
        <div v-show="createStep === 3" class="step-panel">
          <div class="form-group candidates-section-create">
            <label class="form-label form-label--block">{{ t('task.invitedCandidates') }}</label>
            <p class="form-hint">{{ t('task.invitedCandidatesHint') }}</p>
            <div v-if="candidatesLoading" class="loading-inline"><div class="spinner" /></div>
            <div v-else class="candidates-cards create-task-candidates">
              <label v-for="c in candidates" :key="c.id" class="candidate-card-create" :class="{ selected: publishForm.invited_agent_ids?.includes(c.id) }">
                <input v-model="publishForm.invited_agent_ids" type="checkbox" :value="c.id" class="candidate-card-checkbox" />
                <span class="candidate-card-avatar" aria-hidden="true">{{ (c.name || 'A').charAt(0).toUpperCase() }}</span>
                <div class="candidate-card-body">
                  <span class="candidate-name">{{ c.name }}</span>
                  <span class="candidate-owner">{{ c.owner_name }}</span>
                  <span class="candidate-meta">
                    <span class="candidate-type-badge" :class="(c.type || 'agent')">{{ (c.type === 'human' ? t('task.receiverHuman') : t('task.receiverAgent')) || (c.type === 'human' ? '人类' : 'Agent') }}</span>
                    {{ c.agent_type }}<span v-if="c.points != null" class="candidate-points"> · 💰 {{ c.points }}</span>
                  </span>
                  <p v-if="c.description" class="candidate-desc">{{ (c.description || '').slice(0, 60) }}{{ (c.description || '').length > 60 ? '…' : '' }}</p>
                </div>
              </label>
            </div>
            <p v-if="!candidates.length && !candidatesLoading" class="hint">{{ t('task.noCandidates') }}</p>
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('task.discordWebhookLabel') }}</label>
            <Input v-model="publishForm.discord_webhook_url" class="w-full" type="url" :placeholder="t('task.discordWebhookPlaceholder')" />
          </div>
          <p class="hint">{{ t('task.balanceHint', { n: accountCredits }) }}</p>
          <p v-if="publishError" class="error-msg" role="alert">{{ publishError }}</p>
          <div class="step-actions">
            <Button type="button" variant="ghost" @click="handleSaveDraft">{{ t('task.draftSave') || '保存草稿' }}</Button>
            <Button type="button" variant="secondary" @click="createStep = 2">{{ t('common.prev') }}</Button>
            <Button type="button" :disabled="publishLoading" @click="doPublish">{{ publishLoading ? t('task.publishBtnLoading') : t('task.publishBtn') }}</Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.draft-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding: 0.5rem 0;
  margin-bottom: 0.5rem;
  border-radius: var(--radius-sm);
  background: rgba(var(--primary-rgb), 0.08);
  border: 1px solid rgba(var(--primary-rgb), 0.2);
}
.draft-bar__text {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-right: 0.25rem;
}
.escrow-block {
  margin-top: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md, 8px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.12);
}
.escrow-rows { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.5rem; }
.escrow-row-wrap { display: flex; flex-direction: column; gap: 0.45rem; }
.escrow-row { display: grid; grid-template-columns: 1fr 5.5rem auto; gap: 0.5rem; align-items: center; }
@media (max-width: 520px) { .escrow-row { grid-template-columns: 1fr 4.5rem auto; } }
.escrow-weight { max-width: 100%; }
.escrow-criteria { width: 100%; }
.escrow-sum { margin-top: 0.35rem; font-weight: 500; color: var(--primary-color); }
.publish-fee-card {
  margin: 0.25rem 0 0.75rem;
  padding: 0.6rem 0.8rem;
  border: var(--border-hairline);
  border-radius: var(--radius-md);
  background: rgba(34, 197, 94, 0.06);
  display: grid;
  gap: 0.3rem;
}
.publish-fee-card--insufficient {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.35);
}
.publish-fee-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  color: var(--text-secondary);
}
.publish-fee-row strong { color: var(--text-primary); }
.publish-fee-warn {
  margin-top: 0.2rem;
  color: rgb(220, 38, 38);
  font-weight: 500;
}
</style>
