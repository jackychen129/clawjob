<template>
  <div class="account-page apple-layout">
    <PageHeader
      :title="t('account.title')"
      :description="t('account.descNew') || t('account.desc')"
    >
      <template #actions>
        <Button :as="RouterLink" to="/agent-studio" size="sm" variant="secondary">{{ t('account.navStudio') }}</Button>
        <Button :as="RouterLink" to="/tasks" size="sm" variant="secondary">{{ t('account.navTasks') }}</Button>
        <Button :as="RouterLink" to="/agents" size="sm" variant="secondary">{{ t('account.navAgents') }}</Button>
        <Button :as="RouterLink" to="/inbox" size="sm" variant="ghost">{{ t('account.navInbox') }}</Button>
      </template>
    </PageHeader>
    <div v-if="!auth.token" class="card card-content">
      <p>{{ t('auth.pleaseLogin') || '请先登录' }}</p>
    </div>
    <template v-else>
      <Tabs v-model="accountTab" default-value="wallet" class="account-primary-tabs">
        <TabList>
          <Tab value="wallet">{{ t('account.tabWallet') }}</Tab>
          <Tab value="growth">{{ t('account.tabGrowth') }}</Tab>
          <Tab value="recharge">{{ t('account.tabRecharge') }}</Tab>
          <Tab value="developer">{{ t('account.tabDeveloper') }}</Tab>
          <Tab v-if="enterpriseEnabled" value="enterprise">{{ t('account.tabEnterprise') || '企业 / 团队' }}</Tab>
        </TabList>

        <TabPanel value="wallet" class="account-tab-panel">
      <section class="card card-content settlement-hero" aria-label="Agent-to-agent settlement wallet">
        <div class="settlement-hero__banner">
          <Badge variant="p2p">{{ t('account.agentDirectBadge') }}</Badge>
          <h2 class="settlement-hero__title">{{ t('account.settlementPrimaryTitle') }}</h2>
          <p class="hint">{{ t('account.settlementPrimaryHint') }}</p>
        </div>
        <div v-if="payoutLoading" class="account-skel">{{ t('common.loading') }}</div>
        <div v-else class="wallet-summary">
          <div class="wallet-stat">
            <span class="wallet-stat__label">{{ t('account.walletCredits') }}</span>
            <strong class="wallet-stat__num mono">{{ credits }}</strong>
          </div>
          <div class="wallet-stat wallet-stat--escrow">
            <span class="wallet-stat__label">{{ t('account.walletEscrowPending') }}</span>
            <strong class="wallet-stat__num mono">{{ escrowPending }}</strong>
            <Badge v-if="escrowPending > 0" variant="escrow" class="wallet-stat__badge">{{ t('account.walletEscrowBadge') }}</Badge>
          </div>
          <div class="wallet-stat">
            <span class="wallet-stat__label">{{ t('account.payoutWithdrawable') }}</span>
            <strong class="wallet-stat__num mono">{{ payout?.withdrawable_balance ?? credits }}</strong>
          </div>
        </div>
        <div v-if="walletTotal > 0" class="escrow-visual" :aria-label="t('account.walletEscrowVisual')">
          <div class="escrow-bar">
            <span class="escrow-bar__credits" :style="{ width: creditsBarPct + '%' }" />
            <span class="escrow-bar__pending" :style="{ width: escrowBarPct + '%' }" />
          </div>
          <div class="escrow-legend">
            <span><i class="escrow-legend__dot escrow-legend__dot--credits" />{{ t('account.walletCredits') }}</span>
            <span><i class="escrow-legend__dot escrow-legend__dot--pending" />{{ t('account.walletEscrowPending') }}</span>
          </div>
        </div>
        <ol class="settlement-steps">
          <li>{{ t('account.settlementStep1') }}</li>
          <li>{{ t('account.settlementStep2') }}</li>
          <li>{{ t('account.settlementStep3') }}</li>
        </ol>
        <div class="payout-actions-row">
          <Button :as="RouterLink" to="/agents" size="sm">{{ t('account.settlementGoAgents') }}</Button>
          <Button :as="RouterLink" to="/tasks" size="sm" variant="secondary">{{ t('account.payoutGoTasks') }}</Button>
        </div>
      </section>

      <section class="card card-content payout-hub" aria-label="Earnings summary">
        <h3>{{ t('account.payoutHubTitle') }}</h3>
        <p class="hint">{{ t('account.payoutHubHint') }}</p>
        <div v-if="payoutLoading" class="account-skel">{{ t('common.loading') }}</div>
        <template v-else-if="payout">
          <div class="payout-stats">
            <div class="payout-stat">
              <span class="payout-stat__label">{{ t('account.payoutTaskEarnings') }}</span>
              <strong class="payout-stat__num">{{ payout.task_reward_earned }}</strong>
            </div>
            <div class="payout-stat">
              <span class="payout-stat__label">{{ t('account.payoutMin') }}</span>
              <strong class="payout-stat__num">{{ payout.min_withdraw_amount }}+</strong>
            </div>
          </div>

          <details class="legacy-fiat-details">
            <summary>
              <Badge variant="outline">{{ t('account.legacyFiatLabel') }}</Badge>
              {{ t('account.legacyFiatTitle') }}
            </summary>
            <p class="hint">{{ t('account.legacyFiatHint') }}</p>
            <p v-if="payout.manual_review" class="hint payout-manual-hint">{{ t('account.payoutManualHint', { hint: payout.processing_time_hint_zh }) }}</p>
            <ul v-if="payoutBlockers.length" class="payout-blockers">
              <li v-for="b in payoutBlockers" :key="b">{{ t('account.payoutBlocker.' + b) }}</li>
            </ul>

            <details class="legacy-fiat-accordion">
              <summary>{{ t('account.receivingAccountTitle') }}</summary>
              <p class="hint">{{ t('account.receivingAccountHint') }}</p>
              <div class="payout-form-grid">
                <select v-model="receivingForm.account_type" class="input">
                  <option value="alipay">{{ t('account.receivingAlipay') }}</option>
                  <option value="bank_card">{{ t('account.receivingBank') }}</option>
                </select>
                <input v-model="receivingForm.account_name" class="input" :placeholder="t('account.receivingAccountName')" />
                <input v-model="receivingForm.account_number" class="input" :placeholder="t('account.receivingAccountNumber')" />
                <Button type="button" size="sm" :disabled="receivingSaving" @click="saveReceivingAccount">{{ t('account.saveReceivingAccount') }}</Button>
              </div>
              <p v-if="receivingError" class="error-msg">{{ receivingError }}</p>
            </details>

            <details class="legacy-fiat-accordion">
              <summary>{{ t('account.kycTitle') }}</summary>
              <p class="hint">{{ t('account.kycHint') }}</p>
              <p class="mono hint">{{ t('account.kycStatus') }}: {{ payout.kyc_status }}</p>
              <div v-if="payout.kyc_status !== 'approved'" class="kyc-kind-tabs" role="tablist">
                <button type="button" class="kyc-kind-tab" :class="{ active: kycKindTab === 'personal' }" @click="kycKindTab = 'personal'">{{ t('account.kycTabPersonal') }}</button>
                <button type="button" class="kyc-kind-tab" :class="{ active: kycKindTab === 'business' }" @click="kycKindTab = 'business'">{{ t('account.kycTabBusiness') }}</button>
              </div>
              <div v-if="payout.kyc_status !== 'approved' && kycKindTab === 'personal'" class="payout-form-grid">
                <input v-model="kycForm.legal_name" class="input" :placeholder="t('account.kycLegalName')" />
                <select v-model="kycForm.id_type" class="input">
                  <option value="id_card">{{ t('account.kycIdCard') }}</option>
                  <option value="passport">{{ t('account.kycPassport') }}</option>
                </select>
                <input v-model="kycForm.id_number" class="input" :placeholder="t('account.kycIdNumber')" />
                <Button type="button" size="sm" :disabled="kycSubmitting" @click="submitKyc">{{ t('account.kycSubmit') }}</Button>
                <Button type="button" size="sm" variant="secondary" :disabled="kycSubmitting" @click="sandboxSkipKycNow">{{ t('account.kycSandboxSkip') }}</Button>
              </div>
              <div v-if="payout.kyc_status !== 'approved' && kycKindTab === 'business'" class="payout-form-grid">
                <input v-model="kybForm.business_name" class="input" :placeholder="t('account.kybBusinessName')" />
                <input v-model="kybForm.business_id" class="input" :placeholder="t('account.kybBusinessId')" />
                <input v-model="kybForm.legal_name" class="input" :placeholder="t('account.kycLegalName')" />
                <Button type="button" size="sm" :disabled="kycSubmitting" @click="submitKyb">{{ t('account.kybSubmit') }}</Button>
              </div>
              <p v-if="kycError" class="error-msg">{{ kycError }}</p>
            </details>

            <details class="legacy-fiat-accordion">
              <summary>{{ t('account.withdrawTitle') }}</summary>
              <p class="hint">{{ t('account.withdrawHint') }}</p>
              <div class="payout-form-grid payout-form-grid--withdraw">
                <input v-model.number="withdrawAmount" class="input" type="number" :min="payout.min_withdraw_amount" :placeholder="t('account.withdrawAmount')" />
                <Button type="button" :disabled="withdrawBusy || !payout.eligible" @click="submitWithdraw">{{ withdrawBusy ? '…' : t('account.submitWithdraw') }}</Button>
              </div>
              <p v-if="withdrawError" class="error-msg">{{ withdrawError }}</p>
              <p v-if="withdrawSuccess" class="hint payout-success">{{ withdrawSuccess }}</p>
              <div v-if="withdrawals.length" class="payout-subsection payout-subsection--nested">
                <h4>{{ t('account.withdrawHistoryTitle') }}</h4>
                <ul class="withdraw-history">
                  <li v-for="w in withdrawals" :key="w.id" class="withdraw-history__row">
                    <span class="mono">#{{ w.id }}</span>
                    <strong>{{ w.amount }}</strong>
                    <span :class="['withdraw-status', 'is-' + w.status]">{{ w.status }}</span>
                    <span class="hint mono">{{ formatDateTimeLocal(w.submitted_at || '') }}</span>
                  </li>
                </ul>
              </div>
            </details>
          </details>
        </template>
      </section>

      <section v-if="!enterpriseEnabled" class="card card-content enterprise-off-hint">
        <h3>{{ t('account.enterpriseOffTitle') }}</h3>
        <p class="hint">{{ t('account.enterpriseOffHint') }}</p>
      </section>
        </TabPanel>

        <TabPanel value="growth" class="account-tab-panel">
      <section class="card card-content referral-panel referral-panel--prominent">
        <h3>{{ t('account.referralTitle') }}</h3>
        <p class="hint">{{ t('account.referralHint') }}</p>
        <div v-if="referralLoading" class="account-skel">{{ t('common.loading') }}</div>
        <template v-else-if="referral">
          <div class="referral-code-row">
            <span class="referral-code mono">{{ referral.referral_code }}</span>
            <Button type="button" size="sm" variant="secondary" @click="copyReferralCode">
              {{ referralCopyDone === 'code' ? t('account.tokenCopied') : t('account.referralCopyCode') }}
            </Button>
            <Button type="button" size="sm" variant="secondary" @click="copyReferralLink">
              {{ referralCopyDone === 'link' ? t('account.tokenCopied') : t('account.referralCopyLink') }}
            </Button>
          </div>
          <div class="referral-stats">
            <div><span class="hint">{{ t('account.referralInvited') }}</span><strong>{{ referral.invited_count }}</strong></div>
            <div><span class="hint">{{ t('account.referralRewarded') }}</span><strong>{{ referral.rewarded_count }}</strong></div>
            <div><span class="hint">{{ t('account.referralBonusEarned') }}</span><strong>{{ referral.total_bonus_earned }}</strong></div>
          </div>
        </template>
      </section>

      <section class="card card-content referral-panel referral-panel--detail">
        <h3>{{ t('account.referralRecordsTitle') || '邀请明细' }}</h3>
        <p class="hint">{{ t('account.referralBonusSpec', { r: referral?.referrer_bonus_points ?? 100, i: referral?.invitee_bonus_points ?? 50 }) }}</p>
        <div v-if="referralLoading" class="account-skel">{{ t('common.loading') }}</div>
        <template v-else-if="referral">
          <div v-if="referralRecords.length" class="referral-records">
            <div v-for="rec in referralRecords" :key="rec.invitee_user_id" class="referral-record-row">
              <div class="referral-record-main">
                <strong>@{{ rec.invitee_username || ('#' + rec.invitee_user_id) }}</strong>
                <span v-if="rec.signup_at" class="hint mono">· {{ formatDateTimeLocal(rec.signup_at) }}</span>
              </div>
              <span :class="['referral-record-state', rec.rewarded ? 'is-ok' : 'is-pending']">
                {{ rec.rewarded ? t('account.referralStateRewarded') : t('account.referralStatePending') }}
              </span>
            </div>
          </div>
          <p v-else class="hint">{{ t('account.referralRecordsEmpty') }}</p>
        </template>
        <p v-else class="hint">{{ t('common.loadFailed') || t('common.retry') }}</p>
      </section>
        </TabPanel>

        <TabPanel value="recharge" class="account-tab-panel">
      <section class="card card-content recharge-panel">
        <h3>{{ t('account.rechargeTitle') }}</h3>
        <p class="hint">{{ t('account.rechargeHint') }}</p>
        <div class="recharge-form">
          <label class="form-label" for="recharge-amount">{{ t('account.rechargeAmount') }}</label>
          <input id="recharge-amount" v-model.number="rechargeAmount" class="input" type="number" min="1" />
        </div>
        <div class="recharge-methods" role="radiogroup">
          <button
            v-for="m in rechargeMethods"
            :key="m.key"
            type="button"
            class="recharge-method"
            :class="{ 'recharge-method--active': selectedMethod === m.key, 'recharge-method--disabled': rechargeAmount > 0 && (rechargeAmount < m.min_amount || rechargeAmount > m.max_amount) }"
            :aria-pressed="selectedMethod === m.key"
            @click="selectedMethod = m.key"
          >
            <span class="recharge-method__name">{{ m.display_name }}</span>
            <span class="recharge-method__meta mono">
              {{ t('account.rechargeMethodFee', { p: (m.fee_rate * 100).toFixed(2) }) }}
              · {{ m.min_amount }}–{{ m.max_amount }}
            </span>
            <span v-if="m.description" class="recharge-method__desc">{{ m.description }}</span>
            <span v-if="m.tags?.length" class="recharge-method__tags">
              <span v-for="tag in m.tags" :key="tag" class="recharge-method__tag">{{ tag }}</span>
            </span>
          </button>
        </div>
        <div class="account-actions">
          <Button type="button" :disabled="rechargeBusy || !rechargeAmount || !selectedMethod" @click="createRechargeOrderNow">
            {{ rechargeBusy ? '…' : t('account.rechargeCreateOrder') }}
          </Button>
          <Button v-if="latestOrder" type="button" variant="secondary" :disabled="rechargeBusy" @click="confirmRechargeOrderNow">
            {{ t('account.rechargeConfirm') }}
          </Button>
        </div>
        <p v-if="rechargeError" class="error-msg">{{ rechargeError }}</p>
        <div v-if="latestOrder" class="recharge-result">
          <p class="hint">
            {{ t('account.rechargeOrderId') }}：<span class="mono">#{{ latestOrder.order_id }}</span>
            · {{ latestOrder.status }}
            · {{ t('account.rechargeOrderAmount') }}: <strong>{{ latestOrder.amount }}</strong>
          </p>
          <div v-if="latestOrder.instructions" class="recharge-instructions">
            <template v-if="latestOrder.instructions.kind === 'url' && latestOrder.instructions.url">
              <a :href="latestOrder.instructions.url" target="_blank" rel="noopener" class="recharge-link">
                {{ t('account.rechargeOpenPayPage') }} ↗
              </a>
            </template>
            <template v-else-if="latestOrder.instructions.kind === 'qr' && latestOrder.instructions.qr_payload">
              <p class="hint">{{ latestOrder.instructions.note || t('account.rechargeScanQr') }}</p>
              <pre class="mono recharge-code">{{ latestOrder.instructions.qr_payload }}</pre>
            </template>
            <template v-else-if="latestOrder.instructions.kind === 'bank' && latestOrder.instructions.bank">
              <p class="hint">{{ latestOrder.instructions.note }}</p>
              <div class="recharge-bank mono">
                <div>{{ latestOrder.instructions.bank.bank_name }}</div>
                <div>{{ latestOrder.instructions.bank.account_name }}</div>
                <div>{{ latestOrder.instructions.bank.account_number }}</div>
                <div v-if="latestOrder.instructions.bank.swift_code">SWIFT: {{ latestOrder.instructions.bank.swift_code }}</div>
                <div>{{ t('account.rechargeBankMemo') }}: <strong>{{ latestOrder.instructions.bank.memo }}</strong></div>
              </div>
            </template>
            <template v-else-if="latestOrder.instructions.kind === 'crypto' && latestOrder.instructions.crypto">
              <p class="hint">{{ latestOrder.instructions.note }}</p>
              <div class="recharge-crypto mono">
                <div v-if="latestOrder.instructions.crypto.network">{{ t('account.rechargeCryptoNetwork') }}: {{ latestOrder.instructions.crypto.network }}</div>
                <div>{{ t('account.rechargeCryptoAddress') }}: {{ latestOrder.instructions.crypto.address }}</div>
                <div v-if="latestOrder.instructions.crypto.memo">{{ t('account.rechargeBankMemo') }}: {{ latestOrder.instructions.crypto.memo }}</div>
              </div>
            </template>
          </div>
        </div>
      </section>
        </TabPanel>

        <TabPanel value="developer" class="account-tab-panel">
      <section class="card card-content">
        <h3>{{ t('account.apiTokenTitle') }}</h3>
        <p class="hint">{{ t('account.apiTokenHint') }}</p>
        <div class="account-actions">
          <Button type="button" @click="copyToken">{{ copyTokenDone ? t('account.tokenCopied') : t('account.copyToken') }}</Button>
          <Button type="button" variant="secondary" @click="copyEnvSnippet">{{ copyEnvDone ? t('account.tokenCopied') : t('account.copyEnvSnippet') }}</Button>
        </div>
      </section>
      <section class="card card-content">
        <h3>{{ t('account.apiKeysTitle') || 'API 密钥托管' }}</h3>
        <p class="hint">{{ t('account.apiKeysHint') || '用于托管第三方模型/服务 API Key，仅展示脱敏值。' }}</p>
        <div class="api-key-form">
          <input v-model="apiKeyForm.provider" class="input" :placeholder="t('account.apiKeyProviderPlaceholder') || 'provider（如 openai/anthropic）'" />
          <input v-model="apiKeyForm.label" class="input" :placeholder="t('account.apiKeyLabelPlaceholder') || '别名（如 生产主 Key）'" />
          <input v-model="apiKeyForm.secret" class="input" type="password" :placeholder="t('account.apiKeySecretPlaceholder') || '输入 API Key'" />
          <Button type="button" :disabled="apiKeySaving" @click="createApiKey">{{ t('account.apiKeySave') || '保存密钥' }}</Button>
        </div>
        <p v-if="apiKeyError" class="error-msg">{{ apiKeyError }}</p>
        <div class="api-key-list">
          <div v-for="it in apiKeys" :key="it.id" class="api-key-item">
            <div>
              <strong>{{ it.label }}</strong>
              <div class="hint mono">{{ it.provider }} · {{ it.secret_masked }}</div>
            </div>
            <Button size="sm" variant="ghost" type="button" @click="removeApiKey(it.id)">{{ t('account.apiKeyDelete') || '删除' }}</Button>
          </div>
          <p v-if="!apiKeys.length" class="hint">{{ t('account.apiKeyEmpty') || '暂无托管密钥' }}</p>
        </div>
      </section>

      <section class="card card-content">
        <h3>{{ t('account.skillTreeTitle') || '技能树（汇总）' }}</h3>
        <p class="hint">{{ t('account.skillTreeHint') || '根据你名下所有 Agent 完成任务所关联的技能经验汇总。' }}</p>
        <Button type="button" size="sm" variant="secondary" :disabled="skillTreeLoading" @click="loadSkillTree">{{ t('common.retry') || '刷新' }}</Button>
        <div v-if="skillTreeLoading && !skillNodes.length" class="account-skel">{{ t('common.loading') || '加载中…' }}</div>
        <div v-else-if="skillNodes.length" class="skill-tree-viz">
          <div v-for="n in skillNodes" :key="n.name" class="skill-tree-viz-row">
            <div class="skill-tree-viz-head">
              <span class="skill-tree-name">{{ n.name }}</span>
              <span class="skill-tree-meta">L{{ n.level }} · {{ n.xp }} XP</span>
            </div>
            <div class="skill-tree-viz-bar" role="presentation">
              <div class="skill-tree-viz-fill" :style="{ width: skillXpPercent(n) + '%' }" />
            </div>
          </div>
        </div>
        <p v-else class="hint">{{ t('account.skillTreeEmpty') || '暂无技能数据；多接取并完成带技能标签的任务后会在此累计。' }}</p>
        <p v-if="skillTreeTotal > 0" class="hint">{{ t('account.skillTreeTotal', { n: skillTreeTotal }) || `共 ${skillTreeTotal} 项技能` }}</p>
        <p v-if="skillTreeDecayMaxRatio > 0" class="hint">
          {{ t('account.skillTreeDecayHint', { p: Math.round(skillTreeDecayMaxRatio * 100) }) || `检测到技能折旧约 ${Math.round(skillTreeDecayMaxRatio * 100)}%` }}
          <span v-if="skillTreeLastActiveAt" class="mono"> · {{ formatDateTimeLocal(skillTreeLastActiveAt) }}</span>
        </p>
        <p v-if="skillTreeDecayIdleDays > 0" class="hint">
          {{ t('account.skillTreeDecayPolicy', { d: skillTreeDecayIdleDays, w: Math.round(skillTreeDecayWeeklyRatio * 100), m: Math.round(skillTreeDecayPolicyMaxRatio * 100) }) || `折旧策略：空闲 ${skillTreeDecayIdleDays} 天后每周 -${Math.round(skillTreeDecayWeeklyRatio * 100)}%，上限 ${Math.round(skillTreeDecayPolicyMaxRatio * 100)}%` }}
        </p>
      </section>

      <section class="card card-content">
        <div class="skill-rev-head">
          <h3>{{ t('account.skillRevenueTitle') || 'Skill 付费收入（作者）' }}</h3>
          <Button type="button" size="sm" variant="ghost" :disabled="skillRevenueLoading" @click="loadSkillEarnings">{{ t('common.retry') || '刷新' }}</Button>
        </div>
        <p class="hint">{{ t('account.skillRevenueHint') || '你发布的付费 Skill 被购买/调用时的分成明细；作者收入计入可提现佣金余额。' }}</p>
        <div class="skill-rev-summary">
          <div class="skill-rev-metric">
            <span class="skill-rev-metric-val">{{ skillRevenuePayoutSum.toLocaleString() }}</span>
            <span class="skill-rev-metric-label">{{ t('account.skillRevenuePayout') || '累计作者分成（点）' }}</span>
          </div>
          <div class="skill-rev-metric">
            <span class="skill-rev-metric-val">{{ skillRevenue.length }}</span>
            <span class="skill-rev-metric-label">{{ t('account.skillRevenueCount') || '结算笔数' }}</span>
          </div>
        </div>
        <div v-if="skillRevenueLoading && !skillRevenue.length" class="account-skel">{{ t('common.loading') || '加载中…' }}</div>
        <div v-else-if="skillRevenue.length" class="skill-rev-list">
          <div v-for="r in skillRevenue" :key="r.id" class="skill-rev-row">
            <div class="skill-rev-row-main">
              <span class="skill-rev-token mono">{{ r.skill_token }}</span>
              <Badge :variant="r.event_kind === 'refund' ? 'destructive' : 'verified'" class="skill-rev-kind">{{ r.event_kind }}</Badge>
            </div>
            <div class="skill-rev-row-amt">
              <span class="skill-rev-payout" :class="{ neg: (r.author_payout || 0) < 0 }">{{ (r.author_payout || 0) >= 0 ? '+' : '' }}{{ r.author_payout }} {{ t('marketplace.creditsUnit') || '点' }}</span>
              <span class="hint mono">{{ t('account.skillRevenueGross') || '总额' }} {{ r.gross_amount }} · {{ t('account.skillRevenueFee') || '平台' }} {{ r.platform_fee }}</span>
            </div>
          </div>
        </div>
        <p v-else class="hint">{{ t('account.skillRevenueEmpty') || '暂无 Skill 收入。在 Marketplace 给已发布 Skill 设置定价，被购买/调用后会在此显示。' }}</p>
        <div class="skill-rev-cta">
          <Button :as="RouterLink" to="/marketplace#section-skill-market" size="sm" variant="secondary">{{ t('account.skillRevenueManageCta') || '去 Marketplace 定价' }}</Button>
        </div>
      </section>

      <section class="card card-content">
        <div class="skill-rev-head">
          <h3>{{ t('account.skillPurchasesTitle') || '我购买的 Skill' }}</h3>
          <Button type="button" size="sm" variant="ghost" :disabled="skillPurchasesLoading" @click="loadSkillPurchases">{{ t('common.retry') || '刷新' }}</Button>
        </div>
        <p class="hint">{{ t('account.skillPurchasesHint', { d: skillRefundWindowDays }) || `付费购买/订阅的 Skill；购买后 ${skillRefundWindowDays} 天内可申请退款。` }}</p>
        <div v-if="skillPurchasesLoading && !skillPurchases.length" class="account-skel">{{ t('common.loading') || '加载中…' }}</div>
        <div v-else-if="skillPurchases.length" class="skill-rev-list">
          <div v-for="p in skillPurchases" :key="p.id" class="skill-rev-row">
            <div class="skill-rev-row-main">
              <span class="skill-rev-token mono">{{ p.skill_token }}</span>
              <Badge :variant="p.status === 'active' ? 'status-open' : (p.status === 'refunded' ? 'destructive' : 'status-completed')" class="skill-rev-kind">
                {{ p.status === 'active' ? (t('account.purchaseActive') || '有效') : (p.status === 'refunded' ? (t('account.purchaseRefunded') || '已退款') : (t('account.purchaseExpired') || '已过期')) }}
              </Badge>
            </div>
            <div class="skill-rev-row-amt">
              <span class="hint mono">-{{ p.gross_amount }} {{ t('marketplace.creditsUnit') || '点' }} · {{ p.pricing_model }}</span>
              <Button
                v-if="p.refundable"
                type="button"
                size="sm"
                variant="outline"
                :disabled="refundingId === p.id"
                @click="refundPurchase(p)"
              >
                {{ refundingId === p.id ? (t('common.loading') || '处理中…') : (t('account.refund') || '申请退款') }}
              </Button>
            </div>
          </div>
        </div>
        <p v-else class="hint">{{ t('account.skillPurchasesEmpty') || '还没有购买过付费 Skill。' }}</p>
      </section>

      <section class="card card-content account-dev">
        <h3>{{ t('account.devToolsTitle') || '开发者工具（调试）' }}</h3>
        <p class="hint">{{ t('account.devToolsHint') || '调用平台已暴露的工具列表与记忆检索 API，便于本地 Agent 联调。' }}</p>
        <p class="hint dev-api-hint">{{ t('account.devExecuteHint') }}</p>

        <div class="dev-subsection">
          <h4 class="dev-subtitle">{{ t('account.devSectionTools') }}</h4>
          <div class="dev-actions">
            <Button type="button" size="sm" variant="secondary" :disabled="toolsLoading" @click="loadTools">
              {{ t('account.devLoadTools') || '加载工具列表 GET /tools' }}
            </Button>
          </div>
          <details v-if="toolsJson" class="dev-json-details" open>
            <summary>{{ t('account.devToolsResponse') }}</summary>
            <pre class="account-json-pre">{{ toolsJson }}</pre>
          </details>
          <p class="hint dev-tools-create-hint">{{ t('account.devToolsCreateHint') }}</p>
          <textarea v-model="toolsCreateBody" class="input memory-store-textarea" rows="4" :placeholder="t('account.devToolsCreatePlaceholder')" />
          <div class="memory-search-row">
            <Button type="button" size="sm" :disabled="toolsCreateLoading" @click="createToolNow">{{ t('account.devToolsCreate') }}</Button>
          </div>
          <details v-if="toolsCreateJson" class="dev-json-details" open>
            <summary>{{ t('account.devToolsCreateResponse') }}</summary>
            <pre class="account-json-pre">{{ toolsCreateJson }}</pre>
          </details>
        </div>

        <div class="dev-subsection">
          <h4 class="dev-subtitle">{{ t('account.devSectionAgentTool') }}</h4>
          <p class="hint">{{ t('account.devAgentToolHint') }}</p>
          <p v-if="!myAgents.length" class="hint">{{ t('account.devAgentToolEmpty') }}</p>
          <template v-else>
            <div class="memory-search-row dev-agent-tool-row">
              <label class="dev-agent-tool-label">
                <span class="dev-agent-tool-label-text">{{ t('account.devAgentSelect') }}</span>
                <select v-model.number="useToolAgentId" class="input dev-agent-select">
                  <option v-for="a in myAgents" :key="a.id" :value="a.id">{{ a.name }} (#{{ a.id }})</option>
                </select>
              </label>
            </div>
            <div class="memory-search-row">
              <label class="dev-agent-tool-label">
                <span class="dev-agent-tool-label-text">{{ t('account.devAgentToolPick') }}</span>
                <select v-model="useToolPresetName" class="input dev-agent-select" @change="applyToolPreset">
                  <option value="">{{ t('account.devAgentToolPickPlaceholder') }}</option>
                  <option v-for="n in availableToolNames" :key="n" :value="n">{{ n }}</option>
                </select>
              </label>
            </div>
            <div class="memory-search-row">
              <input v-model="useToolName" class="input" type="text" :placeholder="t('account.devAgentToolName')" />
            </div>
            <textarea v-model="useToolParamsRaw" class="input memory-store-textarea" rows="4" :placeholder="t('account.devAgentToolParams')" />
            <div class="memory-search-row">
              <Button type="button" size="sm" :disabled="useToolLoading" @click="callAgentUseToolNow">{{ t('account.devAgentToolSubmit') }}</Button>
            </div>
            <div v-if="useToolHistory.length" class="dev-tool-history">
              <p class="hint dev-tool-history__title">{{ t('account.devAgentToolHistory') }}</p>
              <div class="dev-tool-history__list">
                <button
                  v-for="(h, hi) in useToolHistory"
                  :key="`${h.agent_id}-${h.tool_name}-${hi}`"
                  type="button"
                  class="dev-tool-history__item mono"
                  @click="restoreUseToolHistory(h)"
                >
                  #{{ h.agent_id }} · {{ h.tool_name }}
                </button>
              </div>
            </div>
            <details v-if="useToolJson" class="dev-json-details" open>
              <summary>{{ t('account.devAgentToolResponse') }}</summary>
              <pre class="account-json-pre">{{ useToolJson }}</pre>
            </details>
          </template>
        </div>

        <div class="dev-subsection">
          <h4 class="dev-subtitle">{{ t('account.devSectionMemory') }}</h4>
          <div class="memory-search-row">
            <input v-model="memoryQuery" class="input" type="text" :placeholder="t('account.devMemoryPlaceholder') || '记忆检索关键词'" @keyup.enter="searchMemoryNow" />
            <Button type="button" size="sm" :disabled="memoryLoading" @click="searchMemoryNow">{{ t('account.devMemorySearch') || '检索 GET /memory/search' }}</Button>
          </div>
          <details v-if="memoryJson" class="dev-json-details" open>
            <summary>{{ t('account.devMemorySearchResponse') }}</summary>
            <pre class="account-json-pre">{{ memoryJson }}</pre>
          </details>

          <div class="memory-search-row memory-by-id-row">
            <input v-model="memoryIdInput" class="input" type="text" :placeholder="t('account.devMemoryGetPlaceholder')" @keyup.enter="loadMemoryByIdNow" />
            <Button type="button" size="sm" variant="secondary" :disabled="memoryByIdLoading" @click="loadMemoryByIdNow">{{ t('account.devMemoryGet') }}</Button>
          </div>
          <p class="hint dev-memory-get-hint">{{ t('account.devMemoryGetHint') }}</p>
          <details v-if="memoryByIdJson" class="dev-json-details" open>
            <summary>{{ t('account.devMemoryGetResponse') }}</summary>
            <pre class="account-json-pre">{{ memoryByIdJson }}</pre>
          </details>

          <p class="hint memory-store-hint">{{ t('account.devMemoryStoreHint') || '写入为 JSON Body，对应 POST /memory（联调占位）。' }}</p>
          <textarea v-model="memoryStoreBody" class="input memory-store-textarea" rows="5" :placeholder="t('account.devMemoryStorePlaceholder')" />
          <div class="memory-search-row">
            <Button type="button" size="sm" :disabled="memoryStoreLoading" @click="storeMemoryNow">{{ t('account.devMemoryStore') || '写入 POST /memory' }}</Button>
          </div>
          <details v-if="memoryStoreJson" class="dev-json-details" open>
            <summary>{{ t('account.devMemoryStoreResponse') }}</summary>
            <pre class="account-json-pre">{{ memoryStoreJson }}</pre>
          </details>
        </div>
      </section>
        </TabPanel>

        <TabPanel v-if="enterpriseEnabled" value="enterprise" class="account-tab-panel">
          <EnterprisePanel @credits-updated="loadMe" />
        </TabPanel>
      </Tabs>
    </template>
    <div class="account-footer-actions">
      <Button :as="RouterLink" to="/" variant="secondary">{{ t('common.home') }}</Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import PageHeader from '../components/PageHeader.vue'
import { Tabs, TabList, Tab, TabPanel } from '../components/ui/tabs'
import EnterprisePanel from '../components/EnterprisePanel.vue'
import * as api from '../api'
import type { SkillNode } from '../api'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'

const { t } = useI18n()
const auth = useAuthStore()
const toast = useToast()
const accountTab = ref('wallet')
const enterpriseEnabled = ref(false)
const credits = ref(0)
const payout = ref<api.PayoutEligibility | null>(null)
const payoutLoading = ref(false)
const withdrawals = ref<api.WithdrawalRequest[]>([])
const receivingForm = ref({ account_type: 'alipay', account_name: '', account_number: '' })
const receivingSaving = ref(false)
const receivingError = ref('')
const kycKindTab = ref<'personal' | 'business'>('personal')
const kycForm = ref({ legal_name: '', id_type: 'id_card', id_number: '' })
const kybForm = ref({ business_name: '', business_id: '', legal_name: '' })
const kycSubmitting = ref(false)
const kycError = ref('')
const withdrawAmount = ref<number>(50)
const withdrawBusy = ref(false)
const withdrawError = ref('')
const withdrawSuccess = ref('')
const payoutBlockers = computed(() => payout.value?.blockers || [])
const escrowPending = computed(() => {
  const p = payout.value
  if (!p) return 0
  const locked = Math.max(0, (p.task_reward_earned || 0) - (p.withdrawable_balance || 0))
  return locked + (p.pending_withdrawals || 0)
})
const walletTotal = computed(() => Math.max(credits.value + escrowPending.value, 1))
const creditsBarPct = computed(() => Math.round((credits.value / walletTotal.value) * 100))
const escrowBarPct = computed(() => Math.round((escrowPending.value / walletTotal.value) * 100))
const copyTokenDone = ref(false)
const copyEnvDone = ref(false)
const apiKeys = ref<api.UserApiKeyItem[]>([])
const apiKeySaving = ref(false)
const apiKeyError = ref('')
const apiKeyForm = ref({ provider: 'openai', label: '', secret: '' })

const skillNodes = ref<SkillNode[]>([])
const skillTreeTotal = ref(0)
const skillTreeLoading = ref(false)
const skillTreeDecayMaxRatio = ref(0)
const skillTreeLastActiveAt = ref('')
const skillTreeDecayIdleDays = ref(0)
const skillTreeDecayWeeklyRatio = ref(0)
const skillTreeDecayPolicyMaxRatio = ref(0)

// Skill 付费分成（作者视角）+ 购买记录（买家视角）
const skillRevenue = ref<api.SkillRevenueShare[]>([])
const skillRevenuePayoutSum = ref(0)
const skillRevenueLoading = ref(false)
const skillPurchases = ref<api.SkillPurchase[]>([])
const skillPurchasesSpent = ref(0)
const skillRefundWindowDays = ref(7)
const skillPurchasesLoading = ref(false)
const refundingId = ref<number | null>(null)

function loadSkillEarnings() {
  if (!auth.token) return
  skillRevenueLoading.value = true
  api.fetchMySkillRevenue({ limit: 50 })
    .then((res) => {
      skillRevenue.value = res.data?.items ?? []
      skillRevenuePayoutSum.value = res.data?.visible_payout_sum ?? 0
    })
    .catch(() => { skillRevenue.value = []; skillRevenuePayoutSum.value = 0 })
    .finally(() => { skillRevenueLoading.value = false })
}

function loadSkillPurchases() {
  if (!auth.token) return
  skillPurchasesLoading.value = true
  api.fetchMySkillPurchases({ limit: 50 })
    .then((res) => {
      skillPurchases.value = res.data?.items ?? []
      skillPurchasesSpent.value = res.data?.active_spent_sum ?? 0
      skillRefundWindowDays.value = res.data?.refund_window_days ?? 7
    })
    .catch(() => { skillPurchases.value = [] })
    .finally(() => { skillPurchasesLoading.value = false })
}

async function refundPurchase(p: api.SkillPurchase) {
  if (refundingId.value != null) return
  const msg = (t('account.skillRefundConfirm') as string) || '确定申请退款？将冲正本次扣点。'
  if (!window.confirm(msg)) return
  refundingId.value = p.id
  try {
    const res = await api.refundSkillPurchase(p.id)
    p.status = res.data.purchase.status
    p.refundable = false
    if (res.data.credits_remaining != null) credits.value = res.data.credits_remaining
    toast.success(t('account.skillRefundDone') || '退款成功')
    loadSkillPurchases()
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    toast.error((typeof detail === 'string' && detail) || (t('common.operationFailed') as string) || '退款失败')
  } finally {
    refundingId.value = null
  }
}

const toolsLoading = ref(false)
const toolsJson = ref('')
const toolsCreateBody = ref('{\n  "name": "example_tool",\n  "description": "optional"\n}')
const toolsCreateLoading = ref(false)
const toolsCreateJson = ref('')
const memoryQuery = ref('')
const memoryLoading = ref(false)
const memoryJson = ref('')
const memoryStoreBody = ref('{\n  "content": "hello from clawjob",\n  "type": "text"\n}')
const memoryStoreLoading = ref(false)
const memoryStoreJson = ref('')
const memoryIdInput = ref('')
const memoryByIdLoading = ref(false)
const memoryByIdJson = ref('')

const referral = ref<api.ReferralSummary | null>(null)
const referralRecords = ref<api.ReferralRecord[]>([])
const referralLoading = ref(false)
const referralCopyDone = ref<'none' | 'code' | 'link'>('none')

function loadReferral() {
  if (!auth.token) return
  referralLoading.value = true
  api.fetchMyReferral().then((res) => {
    referral.value = res.data
  }).catch(() => {
    referral.value = null
  }).finally(() => {
    referralLoading.value = false
  })
  api.fetchMyReferralRecords({ limit: 20 }).then((res) => {
    referralRecords.value = res.data.items || []
  }).catch(() => {
    referralRecords.value = []
  })
}

function copyReferralCode() {
  if (!referral.value) return
  navigator.clipboard.writeText(referral.value.referral_code).then(() => {
    referralCopyDone.value = 'code'
    setTimeout(() => { referralCopyDone.value = 'none' }, 1500)
  }).catch(() => {})
}

function copyReferralLink() {
  if (!referral.value) return
  const appBase = (import.meta as any).env?.VITE_APP_URL || 'https://app.clawjob.com.cn'
  const link = referral.value.referral_link || `${appBase}/#/r/${encodeURIComponent(referral.value.referral_code)}`
  const text = t('account.referralLinkCopyText', {
    link,
    referrerBonus: referral.value.referrer_bonus_points ?? 100,
    inviteeBonus: referral.value.invitee_bonus_points ?? 50,
  })
  navigator.clipboard.writeText(text).then(() => {
    referralCopyDone.value = 'link'
    setTimeout(() => { referralCopyDone.value = 'none' }, 1500)
  }).catch(() => {})
}

const rechargeAmount = ref<number>(100)
const rechargeMethods = ref<api.PaymentMethodSpec[]>([])
const selectedMethod = ref<string>('')
const rechargeBusy = ref(false)
const rechargeError = ref('')
const latestOrder = ref<api.RechargeOrderResponse | null>(null)

function loadRechargeMethods() {
  api
    .getRechargeMethods()
    .then((res) => {
      rechargeMethods.value = res.data.methods || []
      if (!selectedMethod.value && rechargeMethods.value.length) {
        selectedMethod.value = rechargeMethods.value[0].key
      }
    })
    .catch(() => {
      rechargeMethods.value = []
    })
}

function createRechargeOrderNow() {
  rechargeError.value = ''
  const amt = Math.max(1, Math.floor(Number(rechargeAmount.value) || 0))
  if (!amt || !selectedMethod.value) return
  const spec = rechargeMethods.value.find((m) => m.key === selectedMethod.value)
  if (spec && (amt < spec.min_amount || amt > spec.max_amount)) {
    rechargeError.value = t('account.rechargeOutOfRange', { min: spec.min_amount, max: spec.max_amount })
    return
  }
  rechargeBusy.value = true
  api
    .createRechargeOrder({ amount: amt, payment_method_type: selectedMethod.value })
    .then((res) => {
      latestOrder.value = res.data
    })
    .catch((e: any) => {
      rechargeError.value = e?.response?.data?.detail || t('account.rechargeCreateFailed')
    })
    .finally(() => {
      rechargeBusy.value = false
    })
}

function confirmRechargeOrderNow() {
  if (!latestOrder.value) return
  rechargeBusy.value = true
  rechargeError.value = ''
  api
    .confirmRecharge({ order_id: latestOrder.value.order_id })
    .then((res: any) => {
      credits.value = res.data?.credits ?? credits.value
      if (latestOrder.value) latestOrder.value.status = 'paid'
      emit('credits-updated')
    })
    .catch((e: any) => {
      rechargeError.value = e?.response?.data?.detail || t('account.rechargeConfirmFailed')
    })
    .finally(() => {
      rechargeBusy.value = false
    })
}

const myAgents = ref<Array<{ id: number; name: string }>>([])
const useToolAgentId = ref<number | null>(null)
const useToolName = ref('search_knowledge_base')
const useToolPresetName = ref('')
const useToolParamsRaw = ref('{\n  "query": "test",\n  "top_k": 3\n}')
const useToolLoading = ref(false)
const useToolJson = ref('')
const availableToolNames = ref<string[]>([])
type UseToolHistoryItem = { agent_id: number; tool_name: string; params: Record<string, unknown> }
const USE_TOOL_HISTORY_KEY = 'clawjob_use_tool_history'
const useToolHistory = ref<UseToolHistoryItem[]>([])

const emit = defineEmits<{ (e: 'credits-updated'): void }>()

function formatDateTimeLocal(isoLike: string): string {
  if (!isoLike) return ''
  const d = new Date(isoLike)
  if (Number.isNaN(d.getTime())) return isoLike
  return d.toLocaleString()
}

function loadPayoutHub() {
  if (!auth.token) return
  payoutLoading.value = true
  Promise.all([
    api.fetchPayoutEligibility(),
    api.getReceivingAccount(),
    api.fetchMyWithdrawals().catch(() => ({ data: { withdrawals: [] } })),
    api.fetchMyKyc().catch(() => null),
  ])
    .then(([elig, recv, wd, kycRes]) => {
      payout.value = elig.data
      const r = recv.data as { account_type?: string; account_name?: string; account_number?: string }
      receivingForm.value = {
        account_type: r.account_type || 'alipay',
        account_name: r.account_name || '',
        account_number: r.account_number || '',
      }
      withdrawals.value = wd.data?.withdrawals || []
      if (kycRes?.data?.latest?.legal_name) {
        kycForm.value.legal_name = kycRes.data.latest.legal_name
      }
      credits.value = elig.data.credits_balance ?? credits.value
    })
    .catch(() => { payout.value = null })
    .finally(() => { payoutLoading.value = false })
}

function saveReceivingAccount() {
  receivingError.value = ''
  receivingSaving.value = true
  api.updateReceivingAccount({ ...receivingForm.value })
    .then(() => loadPayoutHub())
    .catch((e: any) => {
      receivingError.value = e?.response?.data?.detail || t('common.loadFailed')
    })
    .finally(() => { receivingSaving.value = false })
}

function submitKyc() {
  kycError.value = ''
  if (!kycForm.value.legal_name.trim() || !kycForm.value.id_number.trim()) {
    kycError.value = t('account.kycValidation')
    return
  }
  kycSubmitting.value = true
  api.submitPersonalKyc({ ...kycForm.value, country: 'CN' })
    .then(() => loadPayoutHub())
    .catch((e: any) => {
      kycError.value = e?.response?.data?.detail || t('common.loadFailed')
    })
    .finally(() => { kycSubmitting.value = false })
}

function submitKyb() {
  kycError.value = ''
  if (!kybForm.value.business_name.trim() || !kybForm.value.business_id.trim() || !kybForm.value.legal_name.trim()) {
    kycError.value = t('account.kybValidation')
    return
  }
  kycSubmitting.value = true
  api.submitBusinessKyc({ ...kybForm.value, country: 'CN' })
    .then(() => loadPayoutHub())
    .catch((e: any) => {
      kycError.value = e?.response?.data?.detail || t('common.loadFailed')
    })
    .finally(() => { kycSubmitting.value = false })
}

function sandboxSkipKycNow() {
  kycError.value = ''
  kycSubmitting.value = true
  api.sandboxSkipKyc()
    .then(() => loadPayoutHub())
    .catch((e: any) => {
      kycError.value = e?.response?.data?.detail || t('account.kycSandboxDisabled')
    })
    .finally(() => { kycSubmitting.value = false })
}

function skillXpPercent(n: SkillNode): number {
  const max = Math.max(...skillNodes.value.map((x) => Number(x.xp) || 0), 1)
  return Math.min(100, Math.round(((Number(n.xp) || 0) / max) * 100))
}

function submitWithdraw() {
  withdrawError.value = ''
  withdrawSuccess.value = ''
  const amt = Math.floor(Number(withdrawAmount.value) || 0)
  if (!amt) return
  withdrawBusy.value = true
  api.submitWithdrawal(amt)
    .then((res) => {
      withdrawSuccess.value = res.data.message || t('account.withdrawSubmitted')
      credits.value = res.data.credits_balance ?? credits.value
      loadPayoutHub()
    })
    .catch((e: any) => {
      withdrawError.value = e?.response?.data?.detail || t('account.withdrawFailed')
    })
    .finally(() => { withdrawBusy.value = false })
}

function loadMe() {
  if (!auth.token) return
  api.getAccountMe().then((res) => {
    credits.value = res.data?.credits ?? 0
    emit('credits-updated')
  }).catch(() => {})
}

function loadApiKeys() {
  if (!auth.token) return
  api.listAccountApiKeys().then((res) => {
    apiKeys.value = res.data.items || []
  }).catch(() => {
    apiKeys.value = []
  })
}

function createApiKey() {
  apiKeyError.value = ''
  const provider = apiKeyForm.value.provider.trim()
  const label = apiKeyForm.value.label.trim()
  const secret = apiKeyForm.value.secret.trim()
  if (!provider || !label || secret.length < 8) {
    apiKeyError.value = t('account.apiKeyValidationError') || '请填写 provider、别名，且密钥至少 8 位'
    return
  }
  apiKeySaving.value = true
  api.createAccountApiKey({ provider, label, secret }).then(() => {
    apiKeyForm.value.label = ''
    apiKeyForm.value.secret = ''
    loadApiKeys()
  }).catch((e: any) => {
    apiKeyError.value = e?.response?.data?.detail || t('account.apiKeySaveFailed') || '保存失败'
  }).finally(() => { apiKeySaving.value = false })
}

function removeApiKey(id: number) {
  api.deleteAccountApiKey(id).then(() => loadApiKeys()).catch(() => {})
}

function loadMyAgentsForTools() {
  if (!auth.token) return
  api.fetchMyAgents()
    .then((res) => {
      const list = (res.data?.agents || []) as Array<{ id: number; name: string }>
      myAgents.value = list
      if (list.length && (useToolAgentId.value == null || !list.some((a) => a.id === useToolAgentId.value))) {
        useToolAgentId.value = list[0].id
      }
    })
    .catch(() => {
      myAgents.value = []
    })
}

function loadUseToolHistory() {
  try {
    const raw = localStorage.getItem(USE_TOOL_HISTORY_KEY)
    if (!raw) {
      useToolHistory.value = []
      return
    }
    const arr = JSON.parse(raw) as UseToolHistoryItem[]
    useToolHistory.value = Array.isArray(arr) ? arr.slice(0, 6) : []
  } catch {
    useToolHistory.value = []
  }
}

function saveUseToolHistory(item: UseToolHistoryItem) {
  const next = [item, ...useToolHistory.value.filter((h) => !(h.agent_id === item.agent_id && h.tool_name === item.tool_name))]
  useToolHistory.value = next.slice(0, 6)
  try {
    localStorage.setItem(USE_TOOL_HISTORY_KEY, JSON.stringify(useToolHistory.value))
  } catch {}
}

function applyToolPreset() {
  const picked = useToolPresetName.value.trim()
  if (!picked) return
  useToolName.value = picked
}

function restoreUseToolHistory(h: UseToolHistoryItem) {
  useToolAgentId.value = h.agent_id
  useToolName.value = h.tool_name
  useToolPresetName.value = ''
  useToolParamsRaw.value = JSON.stringify(h.params || {}, null, 2)
}

function callAgentUseToolNow() {
  const agentId = useToolAgentId.value
  const name = useToolName.value.trim()
  if (agentId == null || !name) {
    useToolJson.value = JSON.stringify({ error: 'agent and tool_name required' }, null, 2)
    return
  }
  let params: Record<string, unknown> = {}
  const raw = useToolParamsRaw.value.trim()
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as unknown
      if (parsed != null && typeof parsed === 'object' && !Array.isArray(parsed)) {
        params = parsed as Record<string, unknown>
      } else {
        useToolJson.value = JSON.stringify({ error: 'params must be a JSON object' }, null, 2)
        return
      }
    } catch {
      useToolJson.value = JSON.stringify({ error: 'Invalid JSON in params' }, null, 2)
      return
    }
  }
  useToolLoading.value = true
  useToolJson.value = ''
  api.postAgentUseTool(agentId, { tool_name: name, params })
    .then((res) => {
      useToolJson.value = JSON.stringify(res.data, null, 2)
      saveUseToolHistory({ agent_id: agentId, tool_name: name, params })
    })
    .catch((e: unknown) => {
      useToolJson.value = JSON.stringify({ error: String(e) }, null, 2)
    })
    .finally(() => {
      useToolLoading.value = false
    })
}

function loadSkillTree() {
  if (!auth.token) return
  skillTreeLoading.value = true
  api.fetchMySkillTree()
    .then((res) => {
      skillNodes.value = res.data?.nodes ?? []
      skillTreeTotal.value = res.data?.total_skills ?? 0
      skillTreeDecayMaxRatio.value = Number(res.data?.decay?.max_ratio || 0)
      skillTreeLastActiveAt.value = String(res.data?.decay?.last_active_at || '')
      skillTreeDecayIdleDays.value = Number(res.data?.decay?.policy?.idle_days || 0)
      skillTreeDecayWeeklyRatio.value = Number(res.data?.decay?.policy?.weekly_ratio || 0)
      skillTreeDecayPolicyMaxRatio.value = Number(res.data?.decay?.policy?.max_ratio || 0)
    })
    .catch(() => {
      skillNodes.value = []
      skillTreeTotal.value = 0
      skillTreeDecayMaxRatio.value = 0
      skillTreeLastActiveAt.value = ''
      skillTreeDecayIdleDays.value = 0
      skillTreeDecayWeeklyRatio.value = 0
      skillTreeDecayPolicyMaxRatio.value = 0
    })
    .finally(() => {
      skillTreeLoading.value = false
    })
}

function createToolNow() {
  const raw = toolsCreateBody.value.trim()
  if (!raw) return
  toolsCreateLoading.value = true
  toolsCreateJson.value = ''
  let body: Record<string, unknown>
  try {
    body = JSON.parse(raw) as Record<string, unknown>
  } catch {
    toolsCreateJson.value = JSON.stringify({ error: 'Invalid JSON' }, null, 2)
    toolsCreateLoading.value = false
    return
  }
  api.createAgentTool(body)
    .then((res) => {
      toolsCreateJson.value = JSON.stringify(res.data, null, 2)
    })
    .catch((e: unknown) => {
      toolsCreateJson.value = JSON.stringify({ error: String(e) }, null, 2)
    })
    .finally(() => {
      toolsCreateLoading.value = false
    })
}

function loadTools() {
  toolsLoading.value = true
  toolsJson.value = ''
  api.listAgentTools()
    .then((res) => {
      toolsJson.value = JSON.stringify(res.data, null, 2)
      const data = res.data as any
      const items = Array.isArray(data) ? data : (Array.isArray(data?.items) ? data.items : [])
      availableToolNames.value = items
        .map((x: any) => (x && typeof x.name === 'string' ? x.name : ''))
        .filter((x: string) => !!x)
        .slice(0, 100)
    })
    .catch((e: unknown) => {
      toolsJson.value = JSON.stringify({ error: String(e) }, null, 2)
    })
    .finally(() => {
      toolsLoading.value = false
    })
}

function loadMemoryByIdNow() {
  const id = memoryIdInput.value.trim()
  if (!id) return
  memoryByIdLoading.value = true
  memoryByIdJson.value = ''
  api.getMemoryById(id)
    .then((res) => {
      memoryByIdJson.value = JSON.stringify(res.data, null, 2)
    })
    .catch((e: unknown) => {
      memoryByIdJson.value = JSON.stringify({ error: String(e) }, null, 2)
    })
    .finally(() => {
      memoryByIdLoading.value = false
    })
}

function searchMemoryNow() {
  const q = memoryQuery.value.trim()
  if (!q) return
  memoryLoading.value = true
  memoryJson.value = ''
  api.searchMemory(q)
    .then((res) => {
      memoryJson.value = JSON.stringify(res.data, null, 2)
    })
    .catch((e: unknown) => {
      memoryJson.value = JSON.stringify({ error: String(e) }, null, 2)
    })
    .finally(() => {
      memoryLoading.value = false
    })
}

function storeMemoryNow() {
  const raw = memoryStoreBody.value.trim()
  if (!raw) return
  memoryStoreLoading.value = true
  memoryStoreJson.value = ''
  let body: Record<string, unknown>
  try {
    body = JSON.parse(raw) as Record<string, unknown>
  } catch {
    memoryStoreJson.value = JSON.stringify({ error: 'Invalid JSON' }, null, 2)
    memoryStoreLoading.value = false
    return
  }
  api.storeMemory(body)
    .then((res) => {
      memoryStoreJson.value = JSON.stringify(res.data, null, 2)
    })
    .catch((e: unknown) => {
      memoryStoreJson.value = JSON.stringify({ error: String(e) }, null, 2)
    })
    .finally(() => {
      memoryStoreLoading.value = false
    })
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

onMounted(async () => {
  const features = await api.loadAppFeatures()
  enterpriseEnabled.value = !!features.enterprise_enabled
  loadMe()
  loadPayoutHub()
  loadApiKeys()
  loadSkillTree()
  loadSkillEarnings()
  loadSkillPurchases()
  loadMyAgentsForTools()
  loadUseToolHistory()
  loadTools()
  loadRechargeMethods()
  loadReferral()
})
</script>

<style scoped>
.account-page { padding: 0; max-width: 720px; margin: 0 auto; min-width: 0; }
.skill-rev-head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
.skill-rev-head h3 { margin: 0; }
.skill-rev-summary { display: flex; gap: var(--space-5); margin: var(--space-3) 0; flex-wrap: wrap; }
.skill-rev-metric { display: flex; flex-direction: column; }
.skill-rev-metric-val { font-size: 1.4rem; font-weight: 700; color: var(--primary-color); line-height: 1.1; }
.skill-rev-metric-label { font-size: var(--font-caption); color: var(--text-secondary); }
.skill-rev-list { display: grid; gap: var(--space-2); margin-top: var(--space-3); }
.skill-rev-row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); padding: var(--space-2) var(--space-3); border: var(--border-hairline); border-radius: var(--radius-md); background: rgba(0,0,0,0.14); }
.skill-rev-row-main { display: flex; align-items: center; gap: var(--space-2); min-width: 0; }
.skill-rev-token { font-size: var(--font-caption); color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 16rem; }
.skill-rev-kind { flex: none; text-transform: capitalize; }
.skill-rev-row-amt { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; flex: none; }
.skill-rev-payout { font-weight: 700; color: #22c55e; }
.skill-rev-payout.neg { color: var(--danger-color); }
.skill-rev-cta { margin-top: var(--space-3); }
.page-desc { margin: 0 0 var(--space-6); font-size: var(--font-body); color: var(--text-secondary); line-height: var(--line-normal); }
.card { margin-bottom: var(--space-5); }
.account-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-3); }
.recharge-panel { display: grid; gap: var(--space-3); }
.referral-panel { display: grid; gap: var(--space-3); }
.referral-panel--prominent { border-color: rgba(var(--primary-rgb), 0.35); background: rgba(var(--primary-rgb), 0.06); }
.referral-panel--detail { margin-top: 0; }
.referral-code-row { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); }
.referral-code { padding: 0.25rem 0.6rem; background: rgba(0,0,0,0.25); border-radius: var(--radius-sm); font-size: var(--font-body); letter-spacing: 0.08em; }
.referral-stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: var(--space-2); }
.referral-stats > div { display: grid; gap: 2px; padding: var(--space-2) var(--space-3); border: var(--border-hairline); border-radius: var(--radius-md); }
.referral-records { display: flex; flex-direction: column; gap: var(--space-2); margin-top: var(--space-2); }
.referral-record-row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); border: var(--border-hairline); border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); font-size: var(--font-caption); }
.referral-record-state.is-ok { color: rgb(34,197,94); font-weight: 600; }
.referral-record-state.is-pending { color: var(--text-secondary); }
.recharge-form { display: grid; gap: var(--space-2); max-width: 18rem; }
.recharge-methods {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-2);
}
.recharge-method {
  text-align: left;
  display: grid;
  gap: 0.25rem;
  padding: 0.6rem 0.8rem;
  border: var(--border-hairline);
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.02);
  color: var(--text-primary);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.recharge-method:hover { border-color: var(--primary-color); }
.recharge-method--active { border-color: var(--primary-color); background: rgba(59,130,246,0.08); }
.recharge-method--disabled { opacity: 0.5; cursor: not-allowed; }
.recharge-method__name { font-weight: 600; }
.recharge-method__meta { font-size: var(--font-caption); color: var(--text-secondary); }
.recharge-method__desc { font-size: var(--font-caption); color: var(--text-secondary); }
.recharge-method__tags { display: flex; flex-wrap: wrap; gap: 4px; }
.recharge-method__tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  background: rgba(34,197,94,0.12);
  color: rgb(34,197,94);
}
.recharge-result { display: grid; gap: var(--space-2); padding: var(--space-3); border: var(--border-hairline); border-radius: var(--radius-md); background: rgba(255,255,255,0.02); }
.recharge-code, .recharge-bank, .recharge-crypto {
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  background: rgba(0,0,0,0.25);
  word-break: break-all;
  white-space: pre-wrap;
  font-size: var(--font-caption);
}
.recharge-link { color: var(--primary-color); font-weight: 500; }
.settlement-hero { border-color: rgba(167, 139, 250, 0.45); background: linear-gradient(135deg, rgba(167, 139, 250, 0.1), rgba(79, 70, 229, 0.06)); display: grid; gap: var(--space-4); }
.settlement-hero__banner { display: grid; gap: var(--space-2); }
.settlement-hero__title { margin: 0; font-size: 1.125rem; font-weight: 650; }
.wallet-summary { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: var(--space-2); }
.wallet-stat { padding: var(--space-3); border: var(--border-hairline); border-radius: var(--radius-md); display: grid; gap: 4px; background: rgba(0,0,0,0.15); }
.wallet-stat--escrow { border-color: rgba(var(--exchange-escrow-rgb), 0.35); }
.wallet-stat__label { font-size: var(--font-caption); color: var(--text-secondary); }
.wallet-stat__num { font-size: 1.35rem; font-weight: 700; }
.wallet-stat__badge { justify-self: start; margin-top: 2px; }
.escrow-visual { display: grid; gap: var(--space-2); }
.escrow-bar { display: flex; height: 8px; border-radius: var(--radius-full); overflow: hidden; background: rgba(255,255,255,0.06); }
.escrow-bar__credits { background: var(--primary-color); transition: width 0.6s ease; }
.escrow-bar__pending { background: var(--exchange-escrow, #eab308); transition: width 0.6s ease; }
@media (prefers-reduced-motion: reduce) { .escrow-bar__credits, .escrow-bar__pending { transition: none; } }
.escrow-legend { display: flex; flex-wrap: wrap; gap: var(--space-3); font-size: var(--font-caption); color: var(--text-secondary); }
.escrow-legend__dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
.escrow-legend__dot--credits { background: var(--primary-color); }
.escrow-legend__dot--pending { background: var(--exchange-escrow, #eab308); }
.legacy-fiat-accordion { margin-top: var(--space-2); padding: var(--space-3); border: var(--border-hairline); border-radius: var(--radius-md); background: rgba(255,255,255,0.02); }
.legacy-fiat-accordion > summary { cursor: pointer; font-weight: 600; list-style: none; }
.legacy-fiat-accordion > summary::-webkit-details-marker { display: none; }
.legacy-fiat-accordion[open] > summary { margin-bottom: var(--space-2); }
.payout-subsection--nested { margin-top: var(--space-2); padding-top: var(--space-2); border-top: var(--border-hairline); }
.legacy-fiat-details > summary { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); }
.settlement-steps { margin: 0; padding-left: 1.25rem; color: var(--text-secondary); font-size: var(--font-body); line-height: 1.55; display: grid; gap: var(--space-1); }
.legacy-fiat-details { margin-top: var(--space-2); padding: var(--space-3); border: var(--border-hairline); border-radius: var(--radius-md); background: rgba(255,255,255,0.02); }
.legacy-fiat-details > summary { cursor: pointer; font-weight: 600; color: var(--text-secondary); list-style: none; }
.legacy-fiat-details > summary::-webkit-details-marker { display: none; }
.legacy-fiat-details[open] > summary { margin-bottom: var(--space-2); color: var(--text-primary); }
.payout-hub { display: grid; gap: var(--space-3); }
.payout-stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: var(--space-2); }
.payout-stat { padding: var(--space-2) var(--space-3); border: var(--border-hairline); border-radius: var(--radius-md); display: grid; gap: 2px; }
.payout-stat__label { font-size: var(--font-caption); color: var(--text-secondary); }
.payout-stat__num { font-size: 1.25rem; }
.payout-manual-hint { color: rgb(245, 158, 11); }
.payout-blockers { margin: 0; padding-left: 1.2rem; color: var(--text-secondary); font-size: var(--font-caption); }
.payout-actions-row { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.payout-subsection { margin-top: var(--space-3); padding-top: var(--space-3); border-top: var(--border-hairline); display: grid; gap: var(--space-2); }
.payout-subsection h4 { margin: 0; font-size: var(--font-body); font-weight: 650; }
.payout-form-grid { display: grid; gap: var(--space-2); }
@media (min-width: 560px) {
  .payout-form-grid { grid-template-columns: repeat(2, 1fr); }
  .payout-form-grid--withdraw { grid-template-columns: 1fr auto; align-items: center; }
}
.withdraw-history { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-2); }
.withdraw-history__row { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); font-size: var(--font-caption); border: var(--border-hairline); border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); }
.withdraw-status.is-pending { color: rgb(245, 158, 11); }
.withdraw-status.is-paid { color: rgb(34, 197, 94); font-weight: 600; }
.withdraw-status.is-rejected { color: rgb(239, 68, 68); }
.payout-success { color: rgb(34, 197, 94); }
.hint { color: var(--text-secondary); font-size: var(--font-body); margin: 0; }
.account-primary-tabs { margin-top: var(--space-2); }
.account-tab-panel { display: grid; gap: var(--space-4); margin-top: var(--space-4); }
.account-footer-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-2); }
.api-key-form { display: grid; grid-template-columns: 1fr; gap: var(--space-2); margin-top: var(--space-3); }
.api-key-list { display: flex; flex-direction: column; gap: var(--space-2); margin-top: var(--space-3); }
.api-key-item { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); border: var(--border-hairline); border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); }
.skill-tree-list { list-style: none; padding: 0; margin: var(--space-4) 0 0; display: flex; flex-direction: column; gap: var(--space-2); }
.skill-tree-row { display: flex; flex-wrap: wrap; justify-content: space-between; gap: var(--space-2); border: var(--border-hairline); border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); font-size: var(--font-caption); }
.skill-tree-viz { margin-top: var(--space-4); display: flex; flex-direction: column; gap: var(--space-3); }
.skill-tree-viz-head { display: flex; justify-content: space-between; gap: var(--space-2); font-size: var(--font-caption); }
.skill-tree-viz-bar { height: 6px; border-radius: 999px; background: var(--surface-elevated); overflow: hidden; margin-top: var(--space-1); }
.skill-tree-viz-fill { height: 100%; border-radius: inherit; background: linear-gradient(90deg, rgba(34, 197, 94, 0.55), rgba(34, 197, 94, 0.95)); }
.kyc-kind-tabs { display: flex; gap: var(--space-2); margin: var(--space-3) 0; }
.kyc-kind-tab { padding: var(--space-1) var(--space-3); border-radius: var(--radius-md); border: var(--border-hairline); background: transparent; color: var(--text-secondary); cursor: pointer; font-size: var(--font-caption); }
.kyc-kind-tab.active { border-color: var(--accent); color: var(--text-primary); }
.skill-tree-name { font-weight: 600; color: var(--text-primary); }
.skill-tree-meta { color: var(--text-secondary); }
.account-skel { margin-top: var(--space-3); color: var(--text-secondary); font-size: var(--font-caption); }
.account-dev { margin-top: var(--space-2); }
.dev-actions { margin: var(--space-3) 0; }
.memory-search-row { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-3); align-items: center; }
.memory-search-row .input { flex: 1; min-width: 180px; }
.memory-store-hint { margin-top: var(--space-4); }
.memory-store-textarea { width: 100%; margin-top: var(--space-2); font-family: ui-monospace, monospace; font-size: 0.8125rem; }
.dev-subsection { margin-top: var(--space-5); padding-top: var(--space-4); border-top: var(--border-hairline); }
.dev-subsection:first-of-type { margin-top: var(--space-3); padding-top: 0; border-top: none; }
.dev-subtitle { margin: 0 0 var(--space-2); font-size: var(--font-caption); font-weight: 650; color: var(--text-primary); }
.dev-api-hint { margin-top: var(--space-2); font-size: var(--font-caption); }
.dev-json-details { margin-top: var(--space-2); }
.dev-json-details summary { cursor: pointer; font-size: var(--font-caption); color: var(--text-secondary); user-select: none; margin-bottom: var(--space-2); }
.dev-json-details .account-json-pre { margin-top: 0; }
.memory-by-id-row { margin-top: var(--space-3); }
.dev-agent-tool-row { margin-top: var(--space-2); }
.dev-agent-tool-label { display: flex; flex-direction: column; gap: var(--space-1); flex: 1; min-width: 200px; }
.dev-agent-tool-label-text { font-size: var(--font-caption); color: var(--text-secondary); }
.dev-agent-select { width: 100%; }
.dev-tool-history { margin-top: var(--space-2); }
.dev-tool-history__title { margin: 0 0 var(--space-1); font-size: var(--font-caption); }
.dev-tool-history__list { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.dev-tool-history__item {
  border: var(--border-hairline);
  border-radius: var(--radius-sm);
  padding: 0.15rem 0.45rem;
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-secondary);
  font-size: 0.75rem;
}
.dev-memory-get-hint { margin-top: var(--space-1); font-size: var(--font-caption); }
.account-json-pre {
  margin-top: var(--space-3); padding: var(--space-3); border-radius: var(--radius-md);
  background: rgba(0,0,0,0.2); border: var(--border-hairline); font-size: 0.75rem;
  overflow-x: auto; max-height: 280px; white-space: pre-wrap; word-break: break-word;
}
</style>
