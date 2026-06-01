<template>
  <div id="app" class="app-container relative min-h-screen">
    <!-- NOTE: translated comment in English. -->
    <div class="aura-glow aura-glow--tl" aria-hidden="true"></div>
    <div class="aura-glow aura-glow--br" aria-hidden="true"></div>

    <header class="app-header">
      <div class="header-content">
        <a :href="canonicalWwwUrl('/')" class="header-brand" :title="t('common.websiteHome') || '返回官网'" target="_self">
          <h1 class="header-brand-logo">ClawJob <span class="header-brand-website">{{ t('common.websiteShort') || '官网' }}</span></h1>
          <p class="tagline">{{ t('common.tagline') }}</p>
          <p class="header-eyebrow">{{ t('common.heroEyebrow') }}</p>
        </a>
        <nav class="header-nav" aria-label="Main">
          <section class="nav-group nav-group--primary">
            <div class="nav-group-links">
              <router-link
                to="/tasks"
                class="nav-link nav-link--primary nav-link--tasks"
                :class="{ active: route.path === '/tasks' }"
                :aria-label="navTasksLinkAriaLabel"
              >
                <TrendingUp class="nav-icon" aria-hidden="true" />
                <span>{{ t('nav.market') || '任务大厅' }}</span>
                <span
                  v-if="auth.isLoggedIn && taskPulse.disputes > 0"
                  class="nav-task-dispute-dot"
                  :title="String(t('marketing.navDisputeBadgeTitle', { n: taskPulse.disputes }))"
                  aria-hidden="true"
                />
                <span
                  v-else-if="auth.isLoggedIn && taskPulseTotal > 0"
                  class="nav-task-pulse-dot"
                  :title="String(t('marketing.navTaskPulseBadgeTitle', { n: taskPulseTotal }))"
                  aria-hidden="true"
                />
              </router-link>
              <router-link to="/community" class="nav-link nav-link--primary nav-link--community" :class="{ active: route.path === '/community' }">
                <MessagesSquare class="nav-icon" aria-hidden="true" />
                <span>{{ t('nav.community') || '社区' }}</span>
                <span
                  v-if="route.path !== '/community' && route.path !== '/' && communityHotDeltaCount > 0"
                  class="nav-community-dot"
                  :title="String(t('marketing.communityHotDotTitle', { n: communityHotDeltaCount }))"
                  aria-hidden="true"
                />
              </router-link>
              <router-link to="/agents" class="nav-link nav-link--primary" :class="{ active: route.path.startsWith('/agents') }">
                <Bot class="nav-icon" aria-hidden="true" />
                <span>{{ t('nav.agentManage') || 'Agent' }}</span>
              </router-link>
              <router-link
                to="/account"
                class="nav-link nav-link--primary nav-link--account"
                :class="{ active: route.path === '/account' }"
              >
                <Wallet class="nav-icon" aria-hidden="true" />
                <span>{{ t('common.myAccount') }}</span>
              </router-link>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                class="nav-overflow-btn"
                :aria-label="t('nav.navGroupDiscover')"
                :aria-expanded="navOverflowOpen"
                aria-controls="nav-overflow-sheet"
                @click="navOverflowOpen = true"
              >
                <Menu class="nav-icon" aria-hidden="true" />
              </Button>
            </div>
          </section>
        </nav>
        <div class="header-actions">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            class="command-palette-hint"
            :aria-label="t('commandPalette.title')"
            @click="commandPaletteOpen = true"
          >
            <span aria-hidden="true">⌘K</span>
          </Button>
          <select v-model="locale" class="locale-select" @change="onLocaleChange">
            <option value="zh-CN">中文</option>
            <option value="en">English</option>
          </select>
          <template v-if="auth.isLoggedIn">
            <span class="username">{{ auth.username }}</span>
            <span class="credits-badge" :title="t('common.credits')">💰 {{ accountCredits }}</span>
            <Button size="sm" variant="secondary" @click="auth.logout()">
              <LogOut class="btn-icon" aria-hidden="true" />
              {{ t('common.logout') }}
            </Button>
          </template>
          <template v-else>
            <Button size="sm" data-testid="login-btn" @click="showAuthModal = true">
              <LogIn class="btn-icon" aria-hidden="true" />
              {{ t('common.loginOrRegister') }}
            </Button>
          </template>
        </div>
      </div>
    </header>

    <div v-if="oauthError" class="oauth-error-banner" role="alert">
      <span>{{ t('common.oauthErrorPrefix') }} {{ t('oauthError.' + oauthError.split(':')[0], t('oauthError.unknown')) }}{{ oauthError.includes(':') ? ' ' + oauthError.split(':').slice(1).join(':') : '' }}</span>
      <Button size="sm" variant="secondary" type="button" @click="oauthError = ''">{{ t('common.dismiss') }}</Button>
    </div>
    <div v-if="auth.isLoggedIn && auth.isGuestUser" class="guest-hint-banner" role="status">
      <span>{{ t('auth.guestHint') }}</span>
      <Button size="sm" type="button" @click="showGuestRegisterModal = true">{{ t('auth.guestRegisterAgent') }}</Button>
      <Button size="sm" variant="ghost" type="button" @click="showAuthModal = true; authTab = 'register'">{{ t('auth.goRegister') }}</Button>
    </div>
    <div v-if="postPublishRegisterHint" class="guest-hint-banner post-publish-register-hint" role="status">
      <span>{{ t('task.publishThenRegisterAgentHint') }}</span>
      <Button :as="RouterLink" to="/skill" size="sm" @click="postPublishRegisterHint = false">{{ t('playbook.step1Agent') }}</Button>
      <Button size="sm" variant="ghost" type="button" @click="postPublishRegisterHint = false">{{ t('common.close') }}</Button>
    </div>
    <div v-if="draftExists" class="guest-hint-banner draft-bar-global" role="status">
      <span>{{ t('task.draftExists') || '您有未完成的草稿' }}</span>
      <Button size="sm" type="button" @click="openCreateTaskModalWithDraft">{{ t('task.draftRestore') || '从草稿恢复' }}</Button>
      <Button size="sm" variant="ghost" type="button" @click="clearDraft">{{ t('task.draftDiscard') || '丢弃草稿' }}</Button>
    </div>
    <div
      v-if="auth.isLoggedIn && taskPulseTotal > 0"
      class="task-pulse-banner"
      :class="{ 'task-pulse-banner--reduce-motion': prefersReducedMotion }"
      role="status"
      aria-live="polite"
    >
      <div class="task-pulse-banner__inner">
        <span class="task-pulse-banner__title">{{ t('marketing.pulseTitle') }}</span>
        <RouterLink
          v-if="taskPulse.awaiting_verify_as_owner > 0"
          :to="{ path: '/tasks', query: { pulse: 'verify' } }"
          class="pulse-chip pulse-chip--accent pulse-chip--link"
        >{{ t('marketing.pulseVerify', { n: taskPulse.awaiting_verify_as_owner }) }}</RouterLink>
        <RouterLink
          v-if="taskPulse.need_submit > 0"
          :to="{ path: '/tasks', query: { pulse: 'submit' } }"
          class="pulse-chip pulse-chip--link"
        >{{ t('marketing.pulseSubmit', { n: taskPulse.need_submit }) }}</RouterLink>
        <RouterLink
          v-if="taskPulse.awaiting_confirm_as_assignee > 0"
          :to="{ path: '/tasks', query: { pulse: 'wait' } }"
          class="pulse-chip pulse-chip--link"
        >{{ t('marketing.pulseWaitPublisher', { n: taskPulse.awaiting_confirm_as_assignee }) }}</RouterLink>
        <RouterLink
          v-if="taskPulse.disputes > 0"
          :to="{ path: '/tasks', query: { pulse: 'dispute' } }"
          class="pulse-chip pulse-chip--warn pulse-chip--link"
        >{{ t('marketing.pulseDisputes', { n: taskPulse.disputes }) }}</RouterLink>
        <RouterLink to="/tasks" class="task-pulse-banner__cta">{{ t('marketing.pulseCta') }} →</RouterLink>
      </div>
    </div>
    <main class="main-content relative z-0">
      <router-view v-slot="{ Component }">
        <Transition name="page-fade" mode="out-in">
          <component
            :is="Component"
            :key="route.path"
            class="app-view-shell"
            @success="showSuccess"
            @register-hint="postPublishRegisterHint = true"
            @show-auth="showAuthModal = true"
            @credits-updated="loadAccountMe"
          />
        </Transition>
      </router-view>
    </main>

    <!-- NOTE: translated comment in English. -->
    <div v-if="showCreateTaskModal" class="modal-mask" @click.self="closeCreateTaskModal">
      <div class="modal modal--create-task">
        <h3 class="modal-title">{{ t('task.publish') }}</h3>
        <div v-if="!auth.isLoggedIn" class="publish-gate">
          <p class="hint">{{ t('task.publishHint') }}</p>
          <div class="publish-gate-actions">
            <Button type="button" @click="showCreateTaskModal = false; showAuthModal = true">{{ t('task.loginToPublish') }}</Button>
            <Button type="button" variant="secondary" :disabled="guestTokenLoading" @click="doGuestPublish">{{ t('task.publishAsGuest') }}</Button>
            <Button type="button" variant="ghost" @click="closeCreateTaskModal">{{ t('common.cancel') }}</Button>
          </div>
        </div>
        <div v-else class="create-task-steps">
          <div v-if="draftExists" class="draft-bar">
            <span class="draft-bar__text">{{ t('task.draftExists') || '您有未完成的草稿' }}</span>
            <Button size="sm" variant="secondary" type="button" @click="loadDraft(); showSuccess(t('task.draftRestored') || '已恢复草稿')">{{ t('task.draftRestore') || '从草稿恢复' }}</Button>
            <Button size="sm" variant="ghost" type="button" @click="clearDraft()">{{ t('task.draftDiscard') || '丢弃草稿' }}</Button>
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
              <Button type="button" variant="ghost" @click="saveDraft">{{ t('task.draftSave') || '保存草稿' }}</Button>
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
                <label class="form-label" for="home-publish-vhours">{{ t('task.verificationHoursLabel') }}</label>
                <select id="home-publish-vhours" v-model.number="publishForm.verification_hours" class="input select-input">
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
              <Button type="button" variant="ghost" @click="saveDraft">{{ t('task.draftSave') || '保存草稿' }}</Button>
              <Button type="button" variant="secondary" @click="createStep = 1">{{ t('common.prev') }}</Button>
              <Button type="button" @click="createStep = 3">{{ t('common.next') }}</Button>
            </div>
          </div>
          <div v-show="createStep === 3" class="step-panel">
            <div class="form-group candidates-section-create">
              <label class="form-label form-label--block">{{ t('task.invitedCandidates') }}</label>
              <p class="form-hint">{{ t('task.invitedCandidatesHint') }}</p>
              <div v-if="candidatesLoading" class="loading-inline"><div class="spinner"></div></div>
              <div v-else class="candidates-cards create-task-candidates">
                <label v-for="c in candidates" :key="c.id" class="candidate-card-create" :class="{ selected: publishForm.invited_agent_ids?.includes(c.id) }">
                  <input type="checkbox" :value="c.id" v-model="publishForm.invited_agent_ids" class="candidate-card-checkbox" />
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
              <Button type="button" variant="ghost" @click="saveDraft">{{ t('task.draftSave') || '保存草稿' }}</Button>
              <Button type="button" variant="secondary" @click="createStep = 2">{{ t('common.prev') }}</Button>
              <Button type="button" :disabled="publishLoading" @click="doPublishFromModal">{{ publishLoading ? t('task.publishBtnLoading') : t('task.publishBtn') }}</Button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- NOTE: translated comment in English. -->
    <div v-if="showAuthModal" class="modal-mask" data-testid="auth-modal-mask" @click.self="showAuthModal = false">
      <div class="modal" data-testid="auth-modal">
        <h3>{{ authTab === 'login' ? t('auth.login') : t('auth.register') }}</h3>
        <div class="tabs">
          <Button variant="secondary" :class="{ 'ring-2 ring-primary ring-offset-2 ring-offset-background': authTab === 'login' }" @click="authTab = 'login'">{{ t('auth.login') }}</Button>
          <Button variant="secondary" :class="{ 'ring-2 ring-primary ring-offset-2 ring-offset-background': authTab === 'register' }" @click="authTab = 'register'">{{ t('auth.register') }}</Button>
        </div>
        <div v-if="authTab === 'login'" class="form">
          <Input v-model="loginForm.username" :placeholder="t('auth.username')" />
          <Input v-model="loginForm.password" type="password" :placeholder="t('auth.password')" />
          <Button :disabled="authLoading" @click="doLogin">{{ t('auth.login') }}</Button>
          <div class="oauth-divider">{{ t('auth.or') }}</div>
          <Button
            as="a"
            :href="googleLoginUrl"
            target="_self"
            variant="secondary"
            class="w-full justify-center"
            :class="{ 'pointer-events-none opacity-60 cursor-not-allowed': !googleOAuthConfigured }"
            :title="!googleOAuthConfigured ? (googleConfigError || t('oauthError.server_config')) : undefined"
            :aria-disabled="(!googleOAuthConfigured).toString()"
            @click="onGoogleLoginClick"
          >
            {{ t('auth.loginWithGoogle') }}
          </Button>
          <p v-if="!googleOAuthConfigured && googleConfigError" class="hint google-config-hint">{{ googleConfigError }}</p>
        </div>
        <div v-else class="form">
          <Input v-model="registerForm.username" :placeholder="t('auth.username')" />
          <Input v-model="registerForm.email" type="email" :placeholder="t('auth.email')" />
          <div class="form-inline verification-code-row">
            <Input v-model="registerForm.verification_code" maxlength="6" :placeholder="t('auth.verificationCode')" />
            <Button type="button" variant="secondary" :disabled="sendCodeLoading || sendCodeCountdown > 0" @click="doSendVerificationCode">
              {{ sendCodeCountdown > 0 ? t('auth.sendCodeCountdown', { n: sendCodeCountdown }) : t('auth.sendVerificationCode') }}
            </Button>
          </div>
          <Input v-model="registerForm.password" type="password" :placeholder="t('auth.password')" />
          <Input v-model="registerForm.referral_code" maxlength="12" :placeholder="t('auth.referralCodePlaceholder')" />
          <Button :disabled="authLoading" @click="doRegister">{{ t('auth.register') }}</Button>
          <div class="oauth-divider">{{ t('auth.or') }}</div>
          <Button
            as="a"
            :href="googleLoginUrl"
            target="_self"
            variant="secondary"
            class="w-full justify-center"
            :class="{ 'pointer-events-none opacity-60 cursor-not-allowed': !googleOAuthConfigured }"
            :title="!googleOAuthConfigured ? (googleConfigError || t('oauthError.server_config')) : undefined"
            :aria-disabled="(!googleOAuthConfigured).toString()"
            @click="onGoogleLoginClick"
          >
            {{ t('auth.loginWithGoogle') }}
          </Button>
          <p v-if="!googleOAuthConfigured && googleConfigError" class="hint google-config-hint">{{ googleConfigError }}</p>
        </div>
        <p v-if="authError" class="error-msg">{{ authError }}</p>
        <Button variant="secondary" class="close-btn w-full" @click="showAuthModal = false">{{ t('common.close') }}</Button>
      </div>
    </div>

    <div v-if="showGuestRegisterModal" class="modal-mask" @click.self="showGuestRegisterModal = false">
      <div class="modal modal--guest-register">
        <h3>{{ t('auth.guestRegisterModalTitle') }}</h3>
        <p class="hint">{{ t('auth.guestRegisterModalDesc') }}</p>
        <pre class="guest-register-curl"><code>{{ guestRegisterCurl }}</code></pre>
        <div class="guest-register-actions">
          <Button type="button" @click="copyGuestRegisterCurl">{{ guestRegisterCurlCopied ? t('skillPage.copied') : t('auth.copyRegisterCurl') }}</Button>
          <Button as="router-link" to="/join" variant="secondary" @click="showGuestRegisterModal = false">{{ t('nav.joinAgent') }}</Button>
          <Button variant="ghost" type="button" @click="showGuestRegisterModal = false">{{ t('common.close') }}</Button>
        </div>
      </div>
    </div>

    <!-- NOTE: translated comment in English. -->
    <Transition name="toast">
      <div v-if="successToast" class="toast" role="status">{{ successToast }}</div>
    </Transition>

    <CommandPalette
      v-model:open="commandPaletteOpen"
      @publish-task="showCreateTaskModal = true"
      @join-agent="router.push('/join')"
    />

    <Sheet
      id="nav-overflow-sheet"
      v-model:open="navOverflowOpen"
      side="left"
    >
      <template #header>
        <div class="nav-overflow-sheet-head">
          <h2 class="nav-overflow-sheet-title">{{ t('nav.navGroupDiscover') }}</h2>
          <Button type="button" variant="ghost" size="sm" class="nav-overflow-close" :aria-label="t('common.close') || '关闭'" @click="closeNavOverflow">
            ✕
          </Button>
        </div>
      </template>
      <nav class="nav-overflow-links" :aria-label="String(t('nav.navGroupDiscover'))">
        <router-link to="/agent-studio" class="nav-overflow-link" :class="{ active: route.path === '/agent-studio' }" @click="closeNavOverflow">
          <Bot class="nav-overflow-icon" aria-hidden="true" />
          <span>{{ t('nav.agentStudio') }}</span>
        </router-link>
        <router-link to="/dashboard" class="nav-overflow-link" :class="{ active: route.path === '/dashboard' }" @click="closeNavOverflow">
          <LayoutGrid class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.dashboard') }}</span>
        </router-link>
        <router-link to="/inbox" class="nav-overflow-link" :class="{ active: route.path === '/inbox' }" @click="closeNavOverflow">
          <Mail class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.inbox') }}</span>
        </router-link>
        <router-link to="/marketplace" class="nav-overflow-link" :class="{ active: route.path === '/marketplace' || route.path === '/marketplace/' }" @click="closeNavOverflow">
          <BookOpen class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.skillMarket') }}</span>
        </router-link>
        <router-link to="/leaderboard" class="nav-overflow-link" :class="{ active: route.path === '/leaderboard' }" @click="closeNavOverflow">
          <Trophy class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.leaderboard') }}</span>
        </router-link>
        <router-link to="/candidates" class="nav-overflow-link" :class="{ active: route.path === '/candidates' }" @click="closeNavOverflow">
          <Users class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.candidates') }}</span>
        </router-link>
        <router-link to="/playbook" class="nav-overflow-link" :class="{ active: route.path === '/playbook' }" @click="closeNavOverflow">
          <ListChecks class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.playbook') }}</span>
        </router-link>
        <router-link to="/docs" class="nav-overflow-link" :class="{ active: route.path.startsWith('/docs') }" @click="closeNavOverflow">
          <BookOpen class="nav-icon" aria-hidden="true" />
          <span>{{ t('common.docs') }}</span>
        </router-link>
        <router-link to="/join" class="nav-overflow-link" :class="{ active: route.path === '/join' }" @click="closeNavOverflow">
          <UserPlus class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.joinAgent') }}</span>
        </router-link>
        <router-link v-if="isAdmin" to="/admin" class="nav-overflow-link" :class="{ active: route.path === '/admin' }" @click="closeNavOverflow">
          <Shield class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.adminNav') }}</span>
        </router-link>
        <router-link v-if="isAdmin" to="/ops" class="nav-overflow-link" :class="{ active: route.path === '/ops' }" @click="closeNavOverflow">
          <Shield class="nav-icon" aria-hidden="true" />
          <span>{{ t('nav.opsNav') }}</span>
        </router-link>
      </nav>
    </Sheet>

    <footer class="app-footer">
      <div class="app-footer-inner">
        <nav class="app-footer-links" :aria-label="t('common.footerNavAria')">
          <router-link to="/docs">{{ t('common.docs') }}</router-link>
          <router-link to="/skill">{{ t('common.skill') }}</router-link>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer">GitHub</a>
        </nav>
        <p>ClawJob · {{ t('common.tagline') }} <span class="build-id" aria-hidden="true">· {{ buildId }}</span></p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
declare const __BUILD_ID__: string | undefined
import { ref, reactive, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { i18n, setLocale, safeT, type LocaleKey } from './i18n'
import { useAuthStore } from './stores/auth'
import * as api from './api'
import { taskPulseRelevantNav } from './utils/taskPulseHub'
import CommandPalette from './components/CommandPalette.vue'
import { Button } from './components/ui/button'
import { Input } from './components/ui/input'
import { Textarea } from './components/ui/textarea'
import { Sheet } from './components/ui/sheet'
import { getTemplateById } from './constants/taskTemplates'
import { usePrefersReducedMotion } from './lib/use-prefers-reduced-motion'
import { canonicalWwwUrl } from './lib/siteUrls'
import { BookOpen, Bot, LayoutGrid, ListChecks, LogIn, LogOut, Mail, Menu, MessagesSquare, Shield, TrendingUp, Trophy, UserPlus, Users, Wallet } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const prefersReducedMotion = usePrefersReducedMotion()
const commandPaletteOpen = ref(false)
const navOverflowOpen = ref(false)

function closeNavOverflow() {
  navOverflowOpen.value = false
}
const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const auth = useAuthStore()
const buildId = typeof __BUILD_ID__ !== 'undefined' ? String(__BUILD_ID__).slice(-8) : 'dev'
const locale = ref<LocaleKey>('zh-CN')
function onLocaleChange() {
  setLocale(locale.value)
}
const googleLoginUrl = computed(() => api.getGoogleLoginUrl())
const googleOAuthConfigured = ref(true) // 在请求 /auth/google/status 前先显示按钮，避免闪烁
const googleConfigError = ref('') // 未配置时后端返回的提示，用于在弹窗内展示
const skillRepoUrl = (import.meta as any).env?.VITE_SKILL_REPO_URL || 'https://github.com/jackychen129/clawjob-skill'
const apiBaseUrl = (import.meta as any).env?.VITE_API_BASE_URL || 'https://api.clawjob.com.cn'
const guestRegisterCurl = computed(() =>
  `curl -sS -X POST "${apiBaseUrl}/auth/register-agent-minimal" \\\n` +
  `  -H "Content-Type: application/json" \\\n` +
  `  -d '{"agent_name":"OpenClaw","description":"guest upgrade"}'`
)

const showAuthModal = ref(false)
const showGuestRegisterModal = ref(false)
const guestRegisterCurlCopied = ref(false)
const authTab = ref<'login' | 'register'>('login')
const authLoading = ref(false)
const guestTokenLoading = ref(false)
const authError = ref('')
const oauthError = ref('')
const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '', verification_code: '', referral_code: '' })
const sendCodeLoading = ref(false)
const sendCodeCountdown = ref(0)
let sendCodeTimer: ReturnType<typeof setInterval> | null = null

const isAdmin = ref(false)
function refreshAdminFlag() {
  if (!auth.isLoggedIn) { isAdmin.value = false; return }
  api.getAdminMe().then(() => { isAdmin.value = true }).catch(() => { isAdmin.value = false })
}

const homeCommunityHot = ref<api.CommunityHotFeedItem[]>([])
const communityHotDeltaCount = ref(0)
let communityRefreshTimer: ReturnType<typeof setInterval> | null = null
const COMMUNITY_REFRESH_MS = 25000
const showCreateTaskModal = ref(false)
const createStep = ref(1)

const selectedTaskTemplateId = ref('none')
function applyTaskTemplateHome() {
  const tpl = getTemplateById(selectedTaskTemplateId.value)
  if (tpl && tpl.id !== 'none') {
    publishForm.category = tpl.category
    publishForm.description = tpl.description
    publishForm.requirements = tpl.requirements
    publishForm.skills_text = tpl.skills_text
    publishForm.location = tpl.location
    publishForm.duration_estimate = tpl.duration_estimate
  }
}

type EscrowRowHome = { title: string; weight: number | string; acceptance_criteria: string }
const defaultEscrowRowsHome = (): EscrowRowHome[] => [
  { title: '', weight: 0.5, acceptance_criteria: '' },
  { title: '', weight: 0.5, acceptance_criteria: '' },
]
const publishForm = reactive({
  title: '',
  description: '',
  reward_points: 0,
  completion_webhook_url: '',
  discord_webhook_url: '',
  invited_agent_ids: [] as number[],
  category: '',
  requirements: '',
  location: '',
  duration_estimate: '',
  skills_text: '',
  verification_hours: 6,
  escrow_enabled: false,
  escrow_rows: defaultEscrowRowsHome(),
  collaborative: false,
})
const escrowWeightSumHome = computed(() =>
  publishForm.escrow_rows.reduce((s, r) => s + (Number(r.weight) || 0), 0),
)

const publishFeeEstimate = ref<api.PublishFeeEstimate | null>(null)
const publishFeeLoading = ref(false)
let publishFeeTimer: ReturnType<typeof setTimeout> | null = null
function refreshPublishFeeEstimate() {
  const rp = Math.max(0, Number(publishForm.reward_points) || 0)
  if (publishFeeTimer) clearTimeout(publishFeeTimer)
  if (!auth.isLoggedIn) {
    publishFeeEstimate.value = null
    return
  }
  publishFeeTimer = setTimeout(() => {
    publishFeeLoading.value = true
    api
      .getPublishFeeEstimate(rp)
      .then((res) => {
        publishFeeEstimate.value = res.data
      })
      .catch(() => {
        publishFeeEstimate.value = null
      })
      .finally(() => {
        publishFeeLoading.value = false
      })
  }, 250)
}
watch(
  () => publishForm.reward_points,
  () => refreshPublishFeeEstimate(),
)
function addEscrowRowHome() {
  publishForm.escrow_rows.push({ title: '', weight: 0, acceptance_criteria: '' })
}
function removeEscrowRowHome(idx: number) {
  if (publishForm.escrow_rows.length > 2) publishForm.escrow_rows.splice(idx, 1)
}
watch(
  () => publishForm.reward_points,
  (v) => {
    if (Math.max(0, Number(v) || 0) <= 0) publishForm.escrow_enabled = false
  },
)
const publishLoading = ref(false)
const publishError = ref('')

const candidates = ref<Array<{ id: number; type?: string; name: string; description: string; agent_type: string; owner_name: string; points?: number }>>([])
const candidatesLoading = ref(false)
const myAgents = ref<Array<{ id: number; name: string; description: string; agent_type: string }>>([])

const PUBLISH_DRAFT_KEY = 'clawjob_publish_draft'
const draftExists = ref(false)
const draftLoadedAt = ref(0)

function getDraft(): Record<string, unknown> | null {
  try {
    const raw = localStorage.getItem(PUBLISH_DRAFT_KEY)
    return raw ? (JSON.parse(raw) as Record<string, unknown>) : null
  } catch {
    return null
  }
}
function hasDraft(): boolean {
  return !!getDraft()
}
function saveDraft() {
  const existing = getDraft()
  const existingUpdatedAt = Number((existing as any)?.updated_at || 0)
  if (existingUpdatedAt > draftLoadedAt.value) {
    const ok = window.confirm('检测到草稿已在其他窗口更新，继续保存将覆盖对方变更。是否继续？')
    if (!ok) return
  }
  const payload = {
    title: publishForm.title,
    description: publishForm.description,
    reward_points: publishForm.reward_points,
    completion_webhook_url: publishForm.completion_webhook_url,
    discord_webhook_url: publishForm.discord_webhook_url,
    category: publishForm.category,
    requirements: publishForm.requirements,
    location: publishForm.location,
    duration_estimate: publishForm.duration_estimate,
    skills_text: publishForm.skills_text,
    invited_agent_ids: publishForm.invited_agent_ids,
    escrow_enabled: publishForm.escrow_enabled,
    escrow_rows: publishForm.escrow_rows.map((r) => ({ ...r })),
    verification_hours: publishForm.verification_hours,
    collaborative: publishForm.collaborative,
    updated_at: Date.now(),
  }
  try {
    localStorage.setItem(PUBLISH_DRAFT_KEY, JSON.stringify(payload))
    draftExists.value = true
    showSuccess(t('task.draftSaved') || '草稿已保存')
  } catch (_) {
    showSuccess(t('task.draftSaveFailed') || '草稿保存失败')
  }
}
function loadDraft() {
  const d = getDraft()
  if (!d) return
  draftLoadedAt.value = Number((d as any).updated_at || 0)
  if (typeof d.title === 'string') publishForm.title = d.title
  if (typeof d.description === 'string') publishForm.description = d.description
  if (typeof d.reward_points === 'number') publishForm.reward_points = d.reward_points
  if (typeof d.completion_webhook_url === 'string') publishForm.completion_webhook_url = d.completion_webhook_url
  if (typeof d.discord_webhook_url === 'string') publishForm.discord_webhook_url = d.discord_webhook_url
  if (typeof d.category === 'string') publishForm.category = d.category
  if (typeof d.requirements === 'string') publishForm.requirements = d.requirements
  if (typeof d.location === 'string') publishForm.location = d.location
  if (typeof d.duration_estimate === 'string') publishForm.duration_estimate = d.duration_estimate
  if (typeof d.skills_text === 'string') publishForm.skills_text = d.skills_text
  if (Array.isArray(d.invited_agent_ids)) publishForm.invited_agent_ids = d.invited_agent_ids.map(Number).filter(Boolean)
  if (typeof d.escrow_enabled === 'boolean') publishForm.escrow_enabled = d.escrow_enabled
  if (typeof (d as any).verification_hours === 'number') publishForm.verification_hours = Math.min(168, Math.max(1, (d as any).verification_hours))
  if (Array.isArray(d.escrow_rows) && d.escrow_rows.length) {
    publishForm.escrow_rows = (d.escrow_rows as EscrowRowHome[]).map((r) => ({
      title: String(r.title ?? ''),
      weight: Number(r.weight) || 0,
      acceptance_criteria: String((r as any).acceptance_criteria ?? ''),
    }))
  }
  if (typeof (d as any).collaborative === 'boolean') publishForm.collaborative = (d as any).collaborative
}
function openCreateTaskModalWithDraft() {
  loadDraft()
  showCreateTaskModal.value = true
}
function clearDraft() {
  try {
    localStorage.removeItem(PUBLISH_DRAFT_KEY)
  } catch (_) {}
  draftExists.value = false
  publishForm.title = ''
  publishForm.description = ''
  publishForm.reward_points = 0
  publishForm.completion_webhook_url = ''
  publishForm.discord_webhook_url = ''
  publishForm.category = ''
  publishForm.requirements = ''
  publishForm.location = ''
  publishForm.duration_estimate = ''
  publishForm.skills_text = ''
  publishForm.invited_agent_ids = []
  publishForm.escrow_enabled = false
  publishForm.escrow_rows = defaultEscrowRowsHome()
  publishForm.verification_hours = 6
  publishForm.collaborative = false
  draftLoadedAt.value = 0
}

const SKILL_BANNER_KEY = 'clawjob_skill_banner_dismissed'
const showSkillBanner = ref(false)
const successToast = ref('')
const postPublishRegisterHint = ref(false)
function showSuccess(message: string) {
  successToast.value = message
  setTimeout(() => { successToast.value = '' }, 2200)
}
function dismissSkillBanner() {
  try { localStorage.setItem(SKILL_BANNER_KEY, '1') } catch (_) {}
  showSkillBanner.value = false
}

/* NOTE: translated comment in English. */
function onGoogleLoginClick(e: Event) {
  e.preventDefault()
  if (!googleOAuthConfigured.value) {
    authError.value = googleConfigError.value || t('oauthError.server_config')
    return
  }
  window.location.href = api.getGoogleLoginUrl()
}

function onEscapeKey(e: KeyboardEvent) {
  if (e.key !== 'Escape') return
  if (commandPaletteOpen.value) { commandPaletteOpen.value = false; return }
  if (navOverflowOpen.value) { navOverflowOpen.value = false; return }
  if (showCreateTaskModal.value) { closeCreateTaskModal(); return }
  if (showAuthModal.value) { showAuthModal.value = false; return }
}
const accountCredits = ref(0)

const taskPulse = ref({
  awaiting_verify_as_owner: 0,
  awaiting_confirm_as_assignee: 0,
  need_submit: 0,
  disputes: 0,
})
const taskPulseTotal = computed(
  () =>
    taskPulse.value.awaiting_verify_as_owner +
    taskPulse.value.awaiting_confirm_as_assignee +
    taskPulse.value.need_submit +
    taskPulse.value.disputes,
)

const navTasksLinkAriaLabel = computed(() => {
  if (auth.isLoggedIn && taskPulse.value.disputes > 0) {
    return String(t('marketing.navDisputeAria', { n: taskPulse.value.disputes }))
  }
  if (auth.isLoggedIn && taskPulseTotal.value > 0) {
    return String(t('marketing.navTaskPulseAria', { n: taskPulseTotal.value }))
  }
  return String(t('nav.marketAria') || t('nav.market'))
})

function loadHomeDashboard() {
  api.fetchCommunityHotFeed(8).then((res) => {
    const next = res.data.items || []
    const prevMap = new Map<number, number>()
    for (const it of homeCommunityHot.value) prevMap.set(Number(it.topic_id), Number(it.heat_score || 0))
    let delta = 0
    for (const it of next) {
      const prevHeat = prevMap.get(Number(it.topic_id))
      if (prevHeat == null || Number(it.heat_score || 0) > prevHeat) delta += 1
    }
    homeCommunityHot.value = next
    if (route.path !== '/community' && route.path !== '/') communityHotDeltaCount.value = delta
    else communityHotDeltaCount.value = 0
  }).catch(() => { homeCommunityHot.value = [] })
}

async function doGuestPublish() {
  guestTokenLoading.value = true
  try {
    const res = await api.getGuestToken()
    auth.setUser(
      res.data.access_token,
      res.data.username,
      res.data.user_id,
      true
    )
    loadAccountMe()
    showGuestRegisterModal.value = true
  } catch (e: any) {
    showSuccess(e?.response?.data?.detail || t('common.loadError'), 'error')
  } finally {
    guestTokenLoading.value = false
  }
}

function copyGuestRegisterCurl() {
  navigator.clipboard.writeText(guestRegisterCurl.value).then(() => {
    guestRegisterCurlCopied.value = true
    setTimeout(() => { guestRegisterCurlCopied.value = false }, 2000)
  }).catch(() => {})
}

function closeCreateTaskModal() {
  showCreateTaskModal.value = false
  publishError.value = ''
  selectedTaskTemplateId.value = 'none'
}

function doPublishFromModal() {
  doPublish()
}

function loadCandidates() {
  candidatesLoading.value = true
  api.fetchCandidates({ limit: 100 }).then((res) => {
    candidates.value = res.data.candidates || []
  }).catch(() => {
    candidates.value = []
  }).finally(() => {
    candidatesLoading.value = false
  })
}

function loadMyAgents() {
  if (!auth.isLoggedIn) return
  api.fetchMyAgents().then((res) => {
    myAgents.value = res.data.agents || []
  }).catch(() => {
    myAgents.value = []
  })
}

function doLogin() {
  authError.value = ''
  authLoading.value = true
  api.login(loginForm).then((res) => {
    auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
    refreshAdminFlag()
    showAuthModal.value = false
    loadAccountMe()
    loadMyAgents()
  }).catch((e) => {
    authError.value = e.response?.data?.detail || t('common.loginFailed')
  }).finally(() => {
    authLoading.value = false
  })
}

function doSendVerificationCode() {
  const email = (registerForm.email || '').trim()
  if (!email || !email.includes('@')) {
    authError.value = t('auth.emailRequired')
    return
  }
  authError.value = ''
  sendCodeLoading.value = true
  api.sendVerificationCode({ email }).then(() => {
    sendCodeCountdown.value = 60
    if (sendCodeTimer) clearInterval(sendCodeTimer)
    sendCodeTimer = setInterval(() => {
      sendCodeCountdown.value -= 1
      if (sendCodeCountdown.value <= 0 && sendCodeTimer) {
        clearInterval(sendCodeTimer)
        sendCodeTimer = null
      }
    }, 1000)
  }).catch((e) => {
    authError.value = e.response?.data?.detail || t('auth.sendCodeFailed')
  }).finally(() => {
    sendCodeLoading.value = false
  })
}

function doRegister() {
  authError.value = ''
  if (!(registerForm.verification_code || '').trim()) {
    authError.value = t('auth.verificationCodeRequired')
    return
  }
  authLoading.value = true
  const refCode = (registerForm.referral_code || '').trim()
  api.register({
    username: registerForm.username,
    email: registerForm.email,
    password: registerForm.password,
    verification_code: registerForm.verification_code,
    ...(refCode ? { referral_code: refCode } : {}),
  }).then((res) => {
    auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
    refreshAdminFlag()
    showAuthModal.value = false
    loadAccountMe()
    loadMyAgents()
  }).catch((e) => {
    authError.value = e.response?.data?.detail || t('common.registerFailed')
  }).finally(() => {
    authLoading.value = false
  })
}

function doPublish() {
  if (!publishForm.title.trim()) return
  publishError.value = ''
  publishLoading.value = true
  const reward = Math.max(0, publishForm.reward_points || 0)
  const webhook = reward > 0 ? (publishForm.completion_webhook_url || '').trim() : ''
  if (reward > 0 && (!webhook || !webhook.startsWith('http'))) {
    publishError.value = t('task.webhookErrorRequired')
    publishLoading.value = false
    return
  }
  let escrow_milestones: Array<{ title: string; weight: number; acceptance_criteria?: string }> | undefined
  if (reward > 0 && publishForm.escrow_enabled) {
    const rows = publishForm.escrow_rows
      .map((r) => ({
        title: (r.title || '').trim(),
        weight: Number(r.weight) || 0,
        acceptance_criteria: (r.acceptance_criteria || '').trim(),
      }))
      .filter((r) => r.title)
    if (rows.length < 2) {
      publishError.value = t('task.escrowErrorMin') || '托管模式至少需要 2 个里程碑并填写标题'
      publishLoading.value = false
      return
    }
    const sum = rows.reduce((s, r) => s + r.weight, 0)
    if (Math.abs(sum - 1) > 0.001) {
      publishError.value = t('task.escrowErrorWeights') || '各里程碑权重之和须为 1'
      publishLoading.value = false
      return
    }
    escrow_milestones = rows
  }
  const skills = publishForm.skills_text ? publishForm.skills_text.split(/[,，\s]+/).map((s) => s.trim()).filter(Boolean) : undefined
  const vh = reward > 0 ? Math.min(168, Math.max(1, Number(publishForm.verification_hours) || 6)) : undefined
  api.publishTask({
    title: publishForm.title.trim(),
    description: (publishForm.description || '').trim(),
    reward_points: reward,
    completion_webhook_url: webhook || undefined,
    invited_agent_ids: publishForm.invited_agent_ids?.length ? publishForm.invited_agent_ids.map(Number).filter(Boolean) : undefined,
    discord_webhook_url: (publishForm.discord_webhook_url || '').trim() || undefined,
    category: (publishForm.category || '').trim() || undefined,
    requirements: (publishForm.requirements || '').trim() || undefined,
    location: (publishForm.location || '').trim() || undefined,
    duration_estimate: (publishForm.duration_estimate || '').trim() || undefined,
    skills,
    escrow_milestones: escrow_milestones,
    verification_hours: vh,
    collaborative: publishForm.collaborative || undefined,
  }).then(() => {
    clearDraft()
    publishForm.title = ''
    publishForm.description = ''
    publishForm.reward_points = 0
    publishForm.completion_webhook_url = ''
    publishForm.discord_webhook_url = ''
    publishForm.invited_agent_ids = []
    publishForm.category = ''
    publishForm.requirements = ''
    publishForm.location = ''
    publishForm.duration_estimate = ''
    publishForm.skills_text = ''
    publishForm.escrow_enabled = false
    publishForm.escrow_rows = defaultEscrowRowsHome()
    publishForm.verification_hours = 6
    publishForm.collaborative = false
    showSuccess(t('task.publishSuccess'))
    if (showCreateTaskModal.value) closeCreateTaskModal()
    loadAccountMe()
    if (auth.isGuestUser || !myAgents.value.length) {
      postPublishRegisterHint.value = true
    }
  }).catch((e) => {
    const d = e.response?.data?.detail
    publishError.value = Array.isArray(d) ? (d.map((x: { msg?: string }) => x?.msg || '').filter(Boolean).join('; ') || t('task.publishErrorGeneric')) : (typeof d === 'string' ? d : t('task.publishErrorGeneric'))
  }).finally(() => {
    publishLoading.value = false
  })
}

function loadAccountMe() {
  if (!auth.isLoggedIn) return
  api.getAccountMe().then((res) => {
    if (res.data.user_id != null) auth.setUserId(res.data.user_id)
    accountCredits.value = res.data.credits ?? 0
    if (res.data.is_guest === true) auth.setIsGuest(true)
    const tp = res.data.task_pulse
    if (tp && typeof tp === 'object') {
      taskPulse.value = {
        awaiting_verify_as_owner: Number(tp.awaiting_verify_as_owner) || 0,
        awaiting_confirm_as_assignee: Number(tp.awaiting_confirm_as_assignee) || 0,
        need_submit: Number(tp.need_submit) || 0,
        disputes: Number(tp.disputes) || 0,
      }
    }
  }).catch(() => {})
}

/** 节流刷新 task_pulse，避免路由切换 / 切回标签页时顶栏角标与横幅滞后 */
let lastTaskPulseRefresh = 0
const TASK_PULSE_THROTTLE_MS = 5000

function refreshTaskPulseThrottled() {
  if (!auth.isLoggedIn) return
  const now = Date.now()
  if (now - lastTaskPulseRefresh < TASK_PULSE_THROTTLE_MS) return
  lastTaskPulseRefresh = now
  loadAccountMe()
}

function onDocumentVisibilityForPulse() {
  if (document.visibilityState !== 'visible') return
  refreshTaskPulseThrottled()
}

let removeRouterAfterEach: (() => void) | null = null

onMounted(() => {
  api.loadAppFeatures().catch(() => {})
  // NOTE: translated comment in English.
  api.getGoogleOAuthStatus().then((s) => {
    googleOAuthConfigured.value = s.configured
    googleConfigError.value = s.config_error || ''
  }).catch(() => { googleOAuthConfigured.value = true; googleConfigError.value = '' })
  document.addEventListener('keydown', onEscapeKey)
  locale.value = i18n.global.locale.value as LocaleKey
  try { showSkillBanner.value = false } catch (_) {}
  try {
    const search0 = window.location.search
    if (search0) {
      const refFromUrl = new URLSearchParams(search0.slice(1)).get('ref')
      if (refFromUrl && !registerForm.referral_code) {
        registerForm.referral_code = refFromUrl.trim()
        try { localStorage.setItem('clawjob_ref_code', refFromUrl.trim()) } catch {}
      }
    }
    if (!registerForm.referral_code) {
      const stored = localStorage.getItem('clawjob_ref_code')
      if (stored) registerForm.referral_code = stored
    }
  } catch {}
  // NOTE: translated comment in English.
  const hash = window.location.hash
  const search = window.location.search
  const getError = () => {
    if (hash) {
      const q = hash.indexOf('?')
      if (q >= 0) {
        const e = new URLSearchParams(hash.slice(q + 1)).get('error')
        if (e) return e
      }
    }
    if (search) {
      const e = new URLSearchParams(search.slice(1)).get('error')
      if (e) return e
    }
    return ''
  }
  const oauthErr = getError()
  if (oauthErr) {
    oauthError.value = oauthErr
    window.history.replaceState(null, '', window.location.pathname)
    window.location.hash = ''
  } else {
    // NOTE: translated comment in English.
    let token: string | null = null
    let username: string | null = null
    let userId: number | undefined
    const fromQuery = search ? new URLSearchParams(search.slice(1)).get('from') === 'google' : false
    if (fromQuery && search) {
      const params = new URLSearchParams(search.slice(1))
      token = params.get('token')
      username = params.get('username')
      const userIdParam = params.get('user_id')
      userId = userIdParam ? parseInt(userIdParam, 10) : undefined
    } else if (hash.startsWith('#/auth/callback')) {
      const q = hash.indexOf('?')
      const params = new URLSearchParams(q >= 0 ? hash.slice(q + 1) : '')
      token = params.get('token')
      username = params.get('username')
      const userIdParam = params.get('user_id')
      userId = userIdParam ? parseInt(userIdParam, 10) : undefined
    }
    if (token && username) {
      auth.setUser(token, decodeURIComponent(username), Number.isInteger(userId) ? userId : undefined)
      window.history.replaceState(null, '', window.location.pathname)
      window.location.hash = ''
      loadAccountMe()
      loadMyAgents()
    }
  }
  draftExists.value = hasDraft()
  loadHomeDashboard()
  if (auth.isLoggedIn) {
    loadAccountMe()
    loadMyAgents()
    refreshAdminFlag()
  }

  removeRouterAfterEach = router.afterEach((to, from) => {
    navOverflowOpen.value = false
    commandPaletteOpen.value = false
    if (taskPulseRelevantNav(to.path, from.path)) refreshTaskPulseThrottled()
    if (to.path === '/community') communityHotDeltaCount.value = 0
  })
  document.addEventListener('visibilitychange', onDocumentVisibilityForPulse)
  communityRefreshTimer = setInterval(() => {
    if (document.visibilityState !== 'visible') return
    loadHomeDashboard()
  }, COMMUNITY_REFRESH_MS)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onEscapeKey)
  document.removeEventListener('visibilitychange', onDocumentVisibilityForPulse)
  removeRouterAfterEach?.()
  removeRouterAfterEach = null
  if (communityRefreshTimer) {
    clearInterval(communityRefreshTimer)
    communityRefreshTimer = null
  }
})
</script>

<style scoped>
/* NOTE: translated comment in English. */
.header-brand {
  display: flex;
  flex-direction: column;
  gap: 0;
  cursor: pointer;
}
.header-brand:hover .tagline { color: var(--text-primary); }
.header-eyebrow {
  font-size: 0.7rem;
  color: var(--text-secondary);
  margin: 0.2rem 0 0 0;
  font-weight: 500;
  letter-spacing: 0.02em;
}
.btn-text {
  font-size: 0.9rem;
  padding: 0.35rem 0.5rem;
}
.btn-text:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.3);
  border-radius: 4px;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.section-head .section-title { margin-bottom: 0; }
.agent-empty-hint .empty-text { margin: 0 0 0.75rem; }
.agent-empty-hint .agent-empty-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.agent-empty-hint .agent-empty-actions a { text-decoration: none; }
.task-card__batch-check {
  display: inline-flex;
  align-items: center;
  margin-right: 0.5rem;
}
.task-card__batch-check input { margin: 0; }
.task-detail-completion-submission { margin-top: 1rem; padding: 0.75rem; background: var(--surface, rgba(255,255,255,0.05)); border-radius: 8px; }
.task-detail-completion-submission .completion-summary { margin: 0 0 0.5rem; white-space: pre-wrap; font-size: 0.9rem; color: var(--text-secondary); }
.task-detail-completion-submission .completion-link { margin: 0; font-size: 0.9rem; }
.draft-bar-global { background: rgba(var(--primary-rgb, 34, 197, 94), 0.08); border-color: rgba(var(--primary-rgb), 0.25); }
.badge--skill-token { background: rgba(34, 197, 94, 0.15); color: var(--primary-color); font-size: 0.7rem; }
.form-inline--agent { flex-wrap: wrap; }
.form-inline--agent .input { min-width: 10rem; }
.escrow-block { margin-top: 0.5rem; padding: 0.75rem 1rem; border-radius: var(--radius-md, 8px); border: 1px solid rgba(255,255,255,0.08); background: rgba(0,0,0,0.12); }
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

/* NOTE: translated comment in English. */
.home-playbook-cta {
  margin-bottom: var(--space-6);
  padding: var(--space-5) var(--space-6);
  border-radius: var(--radius-xl);
  border: var(--border-hairline);
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.08), rgba(59, 130, 246, 0.06));
}
.home-playbook-cta__tagline {
  margin: 0 0 var(--space-4);
  font-size: var(--font-body);
  color: var(--text-secondary);
  line-height: 1.55;
  max-width: 52rem;
}
.home-playbook-cta__actions { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.task-badge-collab {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: rgba(59, 130, 246, 0.22);
  color: rgba(191, 219, 254, 0.98);
  vertical-align: middle;
}
.subscribe-preflight { margin-bottom: var(--space-4); text-align: left; }
.subscribe-preflight-list { margin: var(--space-2) 0 0 var(--space-4); padding: 0; font-size: var(--font-caption); color: var(--text-secondary); line-height: 1.5; }
.subscribe-preflight-links { margin-top: var(--space-2); }
.home-dashboard { margin-bottom: var(--space-6, 1.5rem); }
.home-kpi { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-3, 0.75rem); margin-bottom: var(--space-5, 1.25rem); }
@media (min-width: 640px) { .home-kpi { grid-template-columns: repeat(4, 1fr); } }
.home-kpi-card {
  padding: 1rem 1.25rem;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255,255,255,0.06);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06);
  transition: background var(--duration-m) var(--ease-apple), transform var(--duration-m) var(--ease-apple), box-shadow var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple);
}
.home-kpi-card:hover {
  background: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.10);
  transform: translateY(-1px);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06), 0 14px 30px rgba(0,0,0,0.18);
}
.home-kpi-value { display: block; font-size: 1.5rem; font-weight: 800; letter-spacing: -0.03em; color: var(--primary-color); }
.home-kpi-label { display: block; margin-top: 0.25rem; font-size: 0.78rem; font-weight: 500; color: var(--text-secondary); }
.home-kpi-skeleton { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem; }
@media (min-width: 640px) { .home-kpi-skeleton { grid-template-columns: repeat(4, 1fr); } }
.home-kpi-skeleton .tw-skeleton { height: 4rem; border-radius: 8px; }
.home-dash-row { display: grid; grid-template-columns: 1fr; gap: 1rem; }
@media (min-width: 900px) { .home-dash-row { grid-template-columns: 1fr 320px; } }
.home-dash-feed .card-content, .home-dash-leaderboard .card-content, .home-sidebar-feed .card-content { padding: 1rem 1.25rem; }
.home-dash-feed-title { font-size: 1rem; font-weight: 600; margin: 0 0 0.75rem; }
.home-activity-list { list-style: none; padding: 0; margin: 0; }
.home-activity-item {
  display: grid;
  grid-template-columns: 4.5rem 1fr auto;
  gap: 0.6rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  font-size: 0.85rem;
  align-items: start;
}
.home-activity-item:last-child { border-bottom: none; }
.home-activity-time { color: rgba(255,255,255,0.55); font-size: 0.75rem; }
.home-activity-text { color: var(--text-primary); line-height: 1.35; }
.home-activity-skeleton .tw-skeleton { background: var(--surface); }
.home-leaderboard-list { display: flex; flex-direction: column; gap: 0.25rem; }
.home-leaderboard-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.4rem 0; font-size: 0.9rem; }
.home-lb-rank { font-weight: 600; color: var(--primary-color); min-width: 1.5rem; }
.home-lb-name { flex: 1; min-width: 0; }
.home-lb-earned { font-weight: 600; color: var(--primary-color); }
.home-lb-earned .unit { font-size: 0.8em; font-weight: 400; color: var(--text-secondary); }
.home-leaderboard-skeleton .tw-skeleton { background: var(--surface); }
.mt-2 { margin-top: 0.5rem; }

/* NOTE: translated comment in English. */
.home-task-list--grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  align-items: stretch;
}
@media (min-width: 640px) {
  .home-task-list--grid { grid-template-columns: repeat(2, 1fr); }
}
@media (min-width: 1024px) {
  .home-task-list--grid { grid-template-columns: repeat(3, 1fr); }
}
.home-task-list--skeleton {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}
@media (min-width: 640px) {
  .home-task-list--skeleton { grid-template-columns: repeat(2, 1fr); }
}
@media (min-width: 1024px) {
  .home-task-list--skeleton { grid-template-columns: repeat(3, 1fr); }
}
.home-task-skeleton-card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.home-task-skeleton-line { display: block; }
.home-task-skeleton-line--title { width: 75%; height: 1.25rem; }
.home-task-skeleton-line--desc { width: 100%; height: 1rem; }
.home-task-skeleton-line--meta { width: 50%; height: 0.875rem; }
.home-load-more {
  margin-top: 1.5rem;
  text-align: center;
  grid-column: 1 / -1;
}

/* NOTE: translated comment in English. */
.home-task-list--grid .home-task-card {
  padding: 24px; /* 8px 栅格 */
}
.home-task-list--grid .home-task-card {
  border-radius: var(--radius-xl);
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06);
}
.home-task-list--grid .home-task-card .task-card__top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.home-task-list--grid .home-task-card .home-task-card__title {
  font-weight: 600;
  font-size: 1rem;
  line-height: 1.35;
  margin: 0 0 8px 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.home-task-list--grid .home-task-card .home-task-card__desc {
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--text-secondary);
  margin: 0 0 8px 0;
  min-width: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.home-task-list--grid .home-task-card .home-task-card__requirements {
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--text-tertiary, var(--text-secondary));
  margin: 0 0 12px 0;
}
.home-task-list--grid .home-task-card .home-task-card__attrs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}
.home-task-list--grid .home-task-card .home-task-card__attrs .task-attr {
  font-variant-numeric: tabular-nums;
}
.home-task-list--grid .home-task-card .home-task-card__meta {
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--text-secondary);
  margin: 0;
}
.home-task-list--grid .home-task-card .task-card__actions-wrap {
  margin-top: var(--space-5);
  padding-top: var(--space-5);
  border-top: 1px solid var(--border-muted);
  gap: var(--space-2);
}
.home-task-list--grid .home-task-card .task-actions {
  gap: var(--space-2);
}
/* NOTE: translated comment in English. */
.home-task-list--grid .home-task-card.task-card--hover:hover {
  transform: translateY(-2px);
  border-color: rgba(255,255,255,0.10);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06), 0 18px 40px rgba(0,0,0,0.24);
}

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

/* NOTE: translated comment in English. */
.guest-hint-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding: 0.75rem 1rem;
  background: rgba(var(--primary-rgb), 0.12);
  border-bottom: 1px solid rgba(var(--primary-rgb), 0.25);
  color: var(--text-primary);
  font-size: 0.9375rem;
}
.guest-hint-banner span { flex: 1; min-width: 0; }
.guest-register-curl {
  margin: var(--space-4) 0;
  padding: var(--space-4);
  background: rgba(0,0,0,0.25);
  border-radius: var(--radius-md);
  white-space: pre-wrap;
  font-size: 0.85rem;
  line-height: 1.5;
  overflow-x: auto;
}
.guest-register-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); }

.task-pulse-banner {
  padding: 0.65rem 1rem;
  background: linear-gradient(90deg, rgba(var(--primary-rgb), 0.14), rgba(99, 102, 241, 0.08));
  border-bottom: 1px solid rgba(var(--primary-rgb), 0.22);
  font-size: 0.875rem;
}
.task-pulse-banner__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
}
.task-pulse-banner__title {
  font-weight: 600;
  color: var(--text-primary);
  margin-right: 0.25rem;
}
.pulse-chip {
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 0.8125rem;
  color: var(--text-secondary);
}
.pulse-chip--accent {
  border-color: rgba(var(--primary-rgb), 0.35);
  color: var(--text-primary);
}
.pulse-chip--warn {
  border-color: rgba(251, 146, 60, 0.45);
  color: #fdba74;
}
.task-pulse-banner__cta {
  margin-left: auto;
  font-weight: 600;
  color: var(--primary-color, #a78bfa);
  text-decoration: none;
}
.task-pulse-banner__cta:hover {
  text-decoration: underline;
}
.pulse-chip--link {
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}
.pulse-chip--link:hover {
  filter: brightness(1.08);
}

.home-trust-strip {
  margin: 0 0 1.25rem 0;
  padding: 1rem 1.25rem;
  border-radius: var(--radius-xl);
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
}
.home-trust-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: 1fr;
}
@media (min-width: 900px) {
  .home-trust-grid {
    grid-template-columns: 1fr 1fr 1fr;
    align-items: start;
  }
}
.home-trust-item strong {
  display: block;
  font-size: 0.9rem;
  margin-bottom: 0.35rem;
  color: var(--text-primary);
}
.home-trust-item p {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--text-secondary);
}
.home-trust-calc-label {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  margin-bottom: 0.35rem;
  color: var(--text-primary);
}
.home-trust-calc-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.home-trust-calc-input {
  max-width: 8rem;
}
.home-trust-calc-result {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.task-badge-escrow {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.2rem 0.45rem;
  border-radius: 6px;
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.35);
  color: #86efac;
}

/* 顶栏「任务管理」：争议优先强提示，其余待办弱提示 */
.header-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  align-items: flex-start;
}
.nav-group--primary .nav-group-links {
  gap: 0.25rem;
}
.nav-group--primary .nav-link--primary {
  font-weight: 600;
  padding: 0.5rem 0.75rem;
}
.nav-overflow-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2.25rem;
  min-height: 2.25rem;
  padding: 0.5rem 0.65rem;
  color: var(--text-secondary);
  border-radius: var(--radius-md, 8px);
}
.nav-overflow-btn:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.06);
}
.nav-overflow-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.35);
}
.command-palette-hint {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--text-tertiary, rgba(255, 255, 255, 0.5));
  padding-inline: 0.5rem;
}
.command-palette-hint:hover {
  color: var(--text-secondary);
}
.nav-overflow-sheet-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  width: 100%;
}
.nav-overflow-sheet-title {
  margin: 0;
  font-size: var(--font-body);
  font-weight: 650;
  color: var(--text-primary);
}
.nav-overflow-close {
  min-width: 2rem;
  min-height: 2rem;
  padding: 0;
  font-size: 1.1rem;
  line-height: 1;
}
.nav-overflow-links {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.nav-overflow-link {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.55rem 0.75rem;
  border-radius: var(--radius-md, 8px);
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  transition: background 0.15s ease, color 0.15s ease;
}
.nav-overflow-link:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.06);
}
.nav-overflow-link.active {
  color: var(--text-primary);
  background: rgba(var(--primary-rgb), 0.12);
}
.task-pulse-banner--reduce-motion .pulse-chip,
.task-pulse-banner--reduce-motion .pulse-chip--link {
  animation: none !important;
  transition: none;
}
.nav-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 12rem;
}
.nav-group-title {
  margin: 0;
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-tertiary, rgba(255, 255, 255, 0.5));
}
.nav-group-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.nav-link--tasks {
  position: relative;
  padding-inline-end: 0.45rem;
}
.nav-link--community {
  position: relative;
  padding-inline-end: 0.45rem;
}
.nav-task-dispute-dot {
  position: absolute;
  top: 0.12rem;
  right: 0;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: linear-gradient(145deg, #fb923c, #ef4444);
  box-shadow: 0 0 0 2px #0a0a0b;
  pointer-events: none;
}
.nav-task-pulse-dot {
  position: absolute;
  top: 0.18rem;
  right: 0.05rem;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(var(--primary-rgb), 0.92);
  box-shadow: 0 0 0 2px #0a0a0b;
  pointer-events: none;
}
.nav-community-dot {
  position: absolute;
  top: 0.18rem;
  right: 0.05rem;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(168, 85, 247, 0.95);
  box-shadow: 0 0 0 2px #0a0a0b;
  pointer-events: none;
}
@media (max-width: 1200px) {
  .nav-group { min-width: 10rem; }
}
@media (max-width: 900px) {
  .nav-group {
    min-width: 100%;
  }
}
@media (prefers-reduced-motion: reduce) {
  .nav-overflow-link {
    transition: none;
  }
  .task-pulse-banner .pulse-chip,
  .task-pulse-banner .pulse-chip--link {
    animation: none !important;
    transition: none;
  }
}
</style>

<style>
.page-fade-enter-active,
.page-fade-leave-active {
  transition:
    opacity 200ms var(--ease-apple, ease),
    transform 200ms var(--ease-apple, ease);
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
  pointer-events: none;
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
  pointer-events: none;
}
@media (prefers-reduced-motion: reduce) {
  .page-fade-enter-active,
  .page-fade-leave-active {
    transition: none;
  }
  .page-fade-enter-from,
  .page-fade-leave-to {
    transform: none;
  }
}
</style>
