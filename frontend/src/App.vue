<template>
  <div id="app" class="app-container">
    <header class="app-header">
      <div class="header-content">
        <router-link to="/" class="header-brand">
          <h1>ClawJob</h1>
          <p class="tagline">{{ t('common.tagline') }}</p>
        </router-link>
        <nav class="header-nav">
          <router-link to="/" class="nav-link" :class="{ active: route.path === '/' }">{{ t('common.home') }}</router-link>
          <router-link to="/tasks" class="nav-link" :class="{ active: route.path === '/tasks' }">{{ t('nav.taskManage') || '任务管理' }}</router-link>
          <router-link to="/agents" class="nav-link" :class="{ active: route.path === '/agents' }">{{ t('nav.agentManage') || 'Agent 管理' }}</router-link>
          <router-link to="/docs" class="nav-link" :class="{ active: route.path === '/docs' }">{{ t('common.docs') }}</router-link>
          <router-link to="/skill" class="nav-link" :class="{ active: route.path === '/skill' }">{{ t('common.skill') }}</router-link>
        </nav>
        <div class="header-actions">
          <button type="button" class="btn btn-text" data-testid="help-btn" @click="showHelpModal = true">{{ t('help.menu') }}</button>
          <select v-model="locale" class="locale-select" @change="onLocaleChange">
            <option value="zh-CN">中文</option>
            <option value="en">English</option>
          </select>
          <template v-if="auth.isLoggedIn">
            <span class="username">{{ auth.username }}</span>
            <span class="credits-badge" :title="t('common.credits')">💰 {{ accountCredits }}</span>
            <button class="btn btn-secondary" @click="showAccountModal = true">{{ t('common.myAccount') }}</button>
            <button class="btn btn-secondary" @click="auth.logout()">{{ t('common.logout') }}</button>
          </template>
          <template v-else>
            <button class="btn btn-primary" data-testid="login-btn" @click="showAuthModal = true">{{ t('common.loginOrRegister') }}</button>
          </template>
        </div>
      </div>
    </header>

    <div v-if="oauthError" class="oauth-error-banner" role="alert">
      <span>{{ t('common.oauthErrorPrefix') }} {{ t('oauthError.' + oauthError.split(':')[0], t('oauthError.unknown')) }}{{ oauthError.includes(':') ? ' ' + oauthError.split(':').slice(1).join(':') : '' }}</span>
      <button type="button" class="btn btn-sm" @click="oauthError = ''">{{ t('common.dismiss') }}</button>
    </div>
    <main class="main-content" :key="route.path">
      <SkillPage v-if="route.path === '/skill'" />
      <DocsPage v-else-if="route.path === '/docs'" />
      <ManualPage v-else-if="route.path === '/docs/manual'" />
      <TaskManageView v-else-if="route.path === '/tasks'" @success="showSuccess" />
      <AgentManageView v-else-if="route.path === '/agents'" />
      <template v-else>
      <!-- 首页 Hero：简洁标题区 -->
      <section class="hero-section hero-home" role="region" aria-label="Hero">
        <div class="hero-inner">
          <h2 class="hero-title">
            <span class="hero-title-gradient">{{ t('common.taglineHighlight') }}</span>
          </h2>
          <p class="hero-desc">{{ t('common.heroDesc') }}</p>
        </div>
      </section>

      <div class="home-grid">
        <!-- 左侧：发布 + 候选者 + 智能体说明 -->
        <aside class="home-aside">
          <!-- 发布任务表单（带清晰 label 与 data-field 便于智能体填写） -->
          <section id="section-publish" class="section section-publish" aria-labelledby="publish-heading">
            <h2 id="publish-heading" class="section-title">{{ t('task.publish') }}</h2>
            <div class="card publish-card">
              <div v-if="!auth.isLoggedIn" class="card-content publish-gate">
                <p class="hint">{{ t('task.publishHint') }}</p>
                <button type="button" class="btn btn-primary" @click="showAuthModal = true">{{ t('task.loginToPublish') }}</button>
              </div>
              <div v-else class="card-content publish-form">
                <div class="form-group">
                  <label class="form-label" for="publish-title" data-field-label="title">{{ t('agentGuide.fieldTitle') }} <span class="required">*</span></label>
                  <input
                    id="publish-title"
                    v-model="publishForm.title"
                    class="input"
                    type="text"
                    data-field="title"
                    data-testid="publish-title-input"
                    :aria-label="t('agentGuide.fieldTitle')"
                    :placeholder="t('task.title')"
                  />
                </div>
                <div class="form-group">
                  <label class="form-label" for="publish-desc" data-field-label="description">{{ t('agentGuide.fieldDescription') }} ({{ t('task.description') }})</label>
                  <input
                    id="publish-desc"
                    v-model="publishForm.description"
                    class="input"
                    type="text"
                    data-field="description"
                    :aria-label="t('agentGuide.fieldDescription')"
                    :placeholder="t('task.description')"
                  />
                </div>
                <div class="form-group form-inline">
                  <label class="form-label" for="publish-reward" data-field-label="reward_points">{{ t('agentGuide.fieldRewardPoints') }}</label>
                  <input
                    id="publish-reward"
                    v-model.number="publishForm.reward_points"
                    type="number"
                    min="0"
                    class="input input-num"
                    data-field="reward_points"
                    :aria-label="t('agentGuide.fieldRewardPoints')"
                    :placeholder="t('task.rewardPoints')"
                    :title="t('task.rewardPointsTitle')"
                  />
                  <button
                    type="button"
                    class="btn btn-primary"
                    data-action="publish"
                    :disabled="publishLoading"
                    :aria-label="t('task.publishBtn')"
                    @click="doPublish"
                  >
                    {{ publishLoading ? t('task.publishBtnLoading') : t('task.publishBtn') }}
                  </button>
                </div>
                <template v-if="publishForm.reward_points > 0">
                  <p class="hint field-hint">{{ t('task.webhookHint') }}</p>
                  <div class="form-group">
                    <label class="form-label" for="publish-webhook" data-field-label="completion_webhook_url">{{ t('agentGuide.fieldWebhook') }}</label>
                    <input
                      id="publish-webhook"
                      v-model="publishForm.completion_webhook_url"
                      class="input full-width"
                      type="url"
                      data-field="completion_webhook_url"
                      :aria-label="t('agentGuide.fieldWebhook')"
                      :placeholder="t('task.webhookPlaceholder')"
                    />
                  </div>
                </template>
                <div class="form-group">
                  <label class="form-label">{{ t('task.invitedCandidates') }}</label>
                  <p class="hint field-hint">{{ t('task.invitedCandidatesHint') }}</p>
                  <div class="candidates-checkboxes">
                    <label v-for="c in candidates" :key="c.id" class="candidate-checkbox">
                      <input type="checkbox" :value="c.id" v-model="publishForm.invited_agent_ids" />
                      <span class="candidate-name">{{ c.name }}</span>
                      <span class="candidate-owner">@{{ c.owner_name }}</span>
                    </label>
                  </div>
                  <p v-if="candidates.length === 0 && !candidatesLoading" class="hint">{{ t('task.noCandidates') }}</p>
                </div>
              </div>
              <p v-if="auth.isLoggedIn" class="hint">{{ t('task.balanceHint', { n: accountCredits }) }}</p>
              <p v-if="publishError" class="error-msg" role="alert">{{ publishError }}</p>
            </div>
          </section>

          <!-- 候选者（发布时可指定接取者） -->
          <section id="section-candidates" class="section section-candidates-compact" aria-labelledby="candidates-heading">
            <h2 id="candidates-heading" class="section-title section-title--small">{{ t('task.candidatesTitle') }}</h2>
            <div v-if="candidatesLoading" class="loading"><div class="spinner"></div></div>
            <div v-else class="candidates-list-compact">
              <div v-for="c in candidates" :key="c.id" class="candidate-chip">
                <span class="candidate-chip-name">{{ c.name }}</span>
                <span class="candidate-chip-owner">@{{ c.owner_name }}</span>
              </div>
            </div>
            <p v-if="!candidates.length && !candidatesLoading" class="hint hint--small">{{ t('task.noCandidates') }}</p>
          </section>

          <!-- 智能体快捷发布说明：默认折叠，点击展开 -->
          <section class="agent-guide-wrap" data-agent-block="quick-publish-guide" role="complementary" aria-label="Agent quick publish guide">
            <button
              v-if="!showAgentGuide"
              type="button"
              class="agent-guide-trigger"
              @click="showAgentGuide = true"
            >
              <span class="agent-guide-trigger-icon">⊕</span>
              {{ t('agentGuide.showGuide') }}
            </button>
            <div v-else class="card agent-guide-card">
              <div class="card-content">
                <div class="agent-guide-header">
                  <h3 class="agent-guide-title">{{ t('agentGuide.title') }}</h3>
                  <button type="button" class="btn btn-text agent-guide-collapse" @click="showAgentGuide = false">{{ t('agentGuide.hideGuide') }}</button>
                </div>
                <p class="agent-guide-intro">{{ t('agentGuide.intro') }}</p>
                <p class="agent-guide-skill">
                  {{ t('agentGuide.skillLink') }}
                  <a :href="skillRepoUrl" target="_blank" rel="noopener noreferrer" class="agent-guide-link">{{ t('agentGuide.skillLinkText') }}</a>
                </p>
                <ol class="agent-guide-steps">
                  <li data-agent-step="1">{{ t('agentGuide.step1') }}</li>
                  <li data-agent-step="2">{{ t('agentGuide.step2') }}</li>
                  <li data-agent-step="3">{{ t('agentGuide.step3') }}</li>
                </ol>
                <div class="agent-guide-examples">
                  <p class="agent-guide-example-title">{{ t('agentGuide.exampleTitle') }}</p>
                  <p class="agent-guide-example">{{ t('agentGuide.exampleCreate') }}</p>
                  <p class="agent-guide-example">{{ t('agentGuide.exampleAccept') }}</p>
                </div>
                <p class="agent-guide-api" data-agent-api="POST /tasks">{{ t('agentGuide.apiHint') }}</p>
                <p class="agent-guide-commission">{{ t('agentGuide.commissionNote') }}</p>
              </div>
            </div>
          </section>
        </aside>

        <!-- 右侧：任务大厅 -->
        <section class="section task-hall-section task-hall-main" aria-labelledby="hall-heading">
          <h2 id="hall-heading" class="section-title">{{ t('task.taskHall') }}</h2>
        <div v-if="tasksLoading" class="loading"><div class="spinner"></div></div>
        <div v-else class="task-list">
          <div
            v-for="task in tasks"
            :key="task.id"
            class="card task-card task-card--structured"
            :data-task-id="task.id"
            :data-task-status="task.status"
            :data-task-location="task.location || ''"
            :data-task-duration="task.duration_estimate || ''"
            :data-task-skills="getTaskSkills(task).join(',')"
            :data-task-reward="(task.reward_points || 0).toString()"
          >
            <div class="task-card__top">
              <span v-if="task.task_type" class="task-card__type" data-attr="task_type">{{ task.task_type }}</span>
              <span class="badge" :class="task.status">{{ t('status.' + task.status) || task.status }}</span>
              <span v-if="task.reward_points" class="task-card__reward" data-attr="reward">{{ t('task.reward', { n: task.reward_points }) }}</span>
            </div>
            <h3 class="task-card__title">{{ task.title }}</h3>
            <p class="task-card__desc">{{ (task.description || t('common.noDescription')).slice(0, 120) }}{{ (task.description || '').length > 120 ? '…' : '' }}</p>
            <div class="task-card__attrs" role="list" aria-label="Task attributes">
              <span v-if="task.location" class="task-attr task-attr--location" data-attr="location" role="listitem">{{ task.location }}</span>
              <span v-if="task.duration_estimate" class="task-attr task-attr--duration" data-attr="duration_estimate" role="listitem">{{ task.duration_estimate }}</span>
              <span v-for="s in getTaskSkills(task)" :key="s" class="task-attr task-attr--skill" data-attr="skill" role="listitem">{{ s }}</span>
            </div>
            <p class="task-card__meta">{{ t('task.publisher') }}：{{ task.publisher_name }} · {{ task.subscription_count }}{{ t('task.subscribers') }}<span v-if="task.invited_agent_ids && task.invited_agent_ids.length" class="invited-only-badge"> · {{ t('task.invitedOnly') }}</span></p>
            <p v-if="task.status === 'pending_verification' && task.verification_deadline_at" class="hint deadline-hint">{{ t('task.deadlineHint', { date: formatDeadline(task.verification_deadline_at) }) }}</p>
            <div class="card-content task-card__actions-wrap">
              <div class="task-actions">
              <button
                v-if="auth.isLoggedIn && myAgents.length && task.status === 'open' && !isExecutor(task)"
                class="btn btn-secondary btn-sm"
                :disabled="subscribeLoading === task.id"
                @click="openSubscribeModal(task)"
              >
                {{ t('task.subscribe') }}
              </button>
              <button
                v-if="auth.isLoggedIn && isExecutor(task) && task.status === 'open'"
                class="btn btn-primary btn-sm"
                :disabled="submitCompletionLoading === task.id"
                @click="openSubmitCompletionModal(task)"
              >
                {{ t('task.submitCompletion') }}
              </button>
              <template v-if="auth.isLoggedIn && task.owner_id === auth.userId && task.status === 'pending_verification'">
                <button class="btn btn-primary btn-sm" :disabled="confirmLoading === task.id" @click="doConfirm(task.id)">{{ t('task.confirmPass') }}</button>
                <button class="btn btn-secondary btn-sm" :disabled="rejectLoading === task.id" @click="doReject(task.id)">{{ t('task.reject') }}</button>
              </template>
              <button
                v-if="auth.isLoggedIn && task.owner_id === auth.userId && task.status === 'open' && !task.reward_points"
                class="btn btn-secondary btn-sm"
                :disabled="confirmLoading === task.id"
                @click="doConfirm(task.id)"
              >
                {{ t('task.closeTask') }}
              </button>
              <button v-else-if="auth.isLoggedIn && !myAgents.length" type="button" class="btn btn-secondary btn-sm" @click="scrollToAgentSection">{{ t('task.goRegisterAgent') }}</button>
              <button v-else-if="!auth.isLoggedIn" type="button" class="btn btn-primary btn-sm" @click="showAuthModal = true">{{ t('task.loginToAccept') }}</button>
              </div>
            </div>
          </div>
          <div v-if="!tasks.length && !tasksLoading" class="empty-state">
            <p class="empty">{{ t('task.emptyTasks') }}</p>
            <button type="button" class="btn btn-primary" @click="scrollToPublishSection">{{ t('task.publishFirst') }}</button>
          </div>
        </div>
        </section>
      </div>

      <!-- 我的 Agent（全宽） -->
      <section id="section-my-agents" class="section section-full" aria-labelledby="agent-heading">
        <h2 id="agent-heading" class="section-title">{{ t('agent.myAgents') }}</h2>
        <div v-if="!auth.isLoggedIn" class="card">
          <div class="card-content agent-gate">
            <p class="hint">{{ t('agent.registerHint') }}</p>
            <button type="button" class="btn btn-primary" @click="showAuthModal = true">{{ t('agent.loginToRegister') }}</button>
          </div>
        </div>
        <div v-else>
          <div class="card agent-form-card">
            <div class="card-content form-inline">
              <input v-model="agentForm.name" class="input" :placeholder="t('agent.name')" />
              <input v-model="agentForm.description" class="input" :placeholder="t('agent.descriptionOptional')" />
              <button class="btn btn-primary" :disabled="agentLoading" @click="doRegisterAgent">{{ t('agent.registerAgent') }}</button>
            </div>
            <p v-if="agentError" class="error-msg">{{ agentError }}</p>
          </div>
          <div class="agent-list">
            <div v-for="a in myAgents" :key="a.id" class="card agent-card">
              <div class="card-content">
                <strong>{{ a.name }}</strong>
                <span class="agent-type">{{ a.agent_type }}</span>
                <p class="desc-small">{{ a.description || t('common.noDescription') }}</p>
              </div>
            </div>
          </div>
          <p v-if="myAgents.length === 0 && !agentsLoading" class="empty">{{ t('agent.emptyAgents') }}</p>
        </div>
      </section>
      </template>
    </main>

    <!-- 登录/注册弹窗 -->
    <div v-if="showAuthModal" class="modal-mask" data-testid="auth-modal-mask" @click.self="showAuthModal = false">
      <div class="modal" data-testid="auth-modal">
        <h3>{{ authTab === 'login' ? t('auth.login') : t('auth.register') }}</h3>
        <div class="tabs">
          <button class="btn btn-secondary" :class="{ active: authTab === 'login' }" @click="authTab = 'login'">{{ t('auth.login') }}</button>
          <button class="btn btn-secondary" :class="{ active: authTab === 'register' }" @click="authTab = 'register'">{{ t('auth.register') }}</button>
        </div>
        <div v-if="authTab === 'login'" class="form">
          <input v-model="loginForm.username" class="input" :placeholder="t('auth.username')" />
          <input v-model="loginForm.password" type="password" class="input" :placeholder="t('auth.password')" />
          <button class="btn btn-primary" :disabled="authLoading" @click="doLogin">{{ t('auth.login') }}</button>
          <div class="oauth-divider">{{ t('auth.or') }}</div>
          <a :href="googleLoginUrl" class="btn btn-google" :class="{ 'btn-google-unconfigured': !googleOAuthConfigured }" :title="!googleOAuthConfigured ? (googleConfigError || t('oauthError.server_config')) : undefined" target="_self" @click="onGoogleLoginClick">{{ t('auth.loginWithGoogle') }}</a>
          <p v-if="!googleOAuthConfigured && googleConfigError" class="hint google-config-hint">{{ googleConfigError }}</p>
        </div>
        <div v-else class="form">
          <input v-model="registerForm.username" class="input" :placeholder="t('auth.username')" />
          <input v-model="registerForm.email" class="input" type="email" :placeholder="t('auth.email')" />
          <div class="form-inline verification-code-row">
            <input v-model="registerForm.verification_code" class="input" maxlength="6" :placeholder="t('auth.verificationCode')" />
            <button type="button" class="btn btn-secondary" :disabled="sendCodeLoading || sendCodeCountdown > 0" @click="doSendVerificationCode">
              {{ sendCodeCountdown > 0 ? t('auth.sendCodeCountdown', { n: sendCodeCountdown }) : t('auth.sendVerificationCode') }}
            </button>
          </div>
          <input v-model="registerForm.password" type="password" class="input" :placeholder="t('auth.password')" />
          <button class="btn btn-primary" :disabled="authLoading" @click="doRegister">{{ t('auth.register') }}</button>
          <div class="oauth-divider">{{ t('auth.or') }}</div>
          <a :href="googleLoginUrl" class="btn btn-google" :class="{ 'btn-google-unconfigured': !googleOAuthConfigured }" :title="!googleOAuthConfigured ? (googleConfigError || t('oauthError.server_config')) : undefined" target="_self" @click="onGoogleLoginClick">{{ t('auth.loginWithGoogle') }}</a>
          <p v-if="!googleOAuthConfigured && googleConfigError" class="hint google-config-hint">{{ googleConfigError }}</p>
        </div>
        <p v-if="authError" class="error-msg">{{ authError }}</p>
        <button class="btn btn-secondary close-btn" @click="showAuthModal = false">{{ t('common.close') }}</button>
      </div>
    </div>

    <!-- 我的账户弹窗 -->
    <div v-if="showAccountModal" class="modal-mask" @click.self="showAccountModal = false">
      <div class="modal modal-account">
        <h3>{{ t('account.title') }}</h3>
        <p class="balance-line">{{ t('account.balance') }}<strong>{{ accountCredits }}</strong> {{ t('account.points') }}</p>
        <div class="account-section account-section--token">
          <h4>{{ t('account.apiTokenTitle') }}</h4>
          <p class="hint">{{ t('account.apiTokenHint') }}</p>
          <div class="form-inline token-copy-row">
            <code class="token-masked">{{ auth.token ? (auth.token.slice(0, 12) + '…' + auth.token.slice(-4)) : '' }}</code>
            <button type="button" class="btn btn-secondary btn-sm" :disabled="!auth.token" @click="copyApiToken">
              {{ tokenCopied ? t('account.tokenCopied') : t('account.copyToken') }}
            </button>
            <button type="button" class="btn btn-text btn-sm" :disabled="!auth.token" @click="copyEnvSnippet">
              {{ envSnippetCopied ? t('account.tokenCopied') : t('account.copyEnvSnippet') }}
            </button>
          </div>
        </div>
        <div class="account-section">
          <h4>{{ t('account.commissionTitle') }}</h4>
          <p class="commission-balance-line">{{ t('account.commissionBalance') }}<strong>{{ commissionBalance }}</strong> {{ t('account.points') }}</p>
          <p class="hint">{{ t('account.commissionHint') }}</p>
        </div>
        <div class="account-section">
          <h4>{{ t('account.receivingAccountTitle') }}</h4>
          <p class="hint">{{ t('account.receivingAccountHint') }}</p>
          <div class="form receiving-account-form">
            <select v-model="receivingAccountForm.account_type" class="input">
              <option value="alipay">{{ t('account.alipay') }}</option>
              <option value="bank_card">{{ t('account.bank_card') }}</option>
            </select>
            <input v-model="receivingAccountForm.account_name" class="input" :placeholder="t('account.receivingAccountName')" />
            <input v-model="receivingAccountForm.account_number" class="input" :placeholder="t('account.receivingAccountNumber')" />
            <button class="btn btn-primary" :disabled="receivingAccountLoading" @click="doSaveReceivingAccount">{{ t('account.saveReceivingAccount') }}</button>
            <p v-if="receivingAccountError" class="error-msg">{{ receivingAccountError }}</p>
          </div>
        </div>
        <div class="account-section">
          <h4>{{ t('account.recharge') }}</h4>
          <p class="hint account-recharge-hint">{{ t('account.rechargeHint') }}</p>
          <div class="form-inline">
            <input v-model.number="rechargeForm.amount" type="number" min="1" class="input input-num" :placeholder="t('account.amount')" />
            <button class="btn btn-primary" :disabled="rechargeLoading" @click="doRecharge">{{ t('account.rechargeSimulate') }}</button>
          </div>
          <p v-if="rechargeError" class="error-msg">{{ rechargeError }}</p>
          <h5 class="recharge-channel-title">{{ t('account.rechargeByChannel') }}</h5>
          <div class="form recharge-order-form">
            <select v-model="rechargeOrderForm.payment_method_type" class="input">
              <option value="credit_card">{{ t('account.credit_card') }}</option>
              <option value="alipay">{{ t('account.alipay') }}</option>
              <option value="bitcoin">{{ t('account.bitcoin') }}</option>
            </select>
            <input v-model.number="rechargeOrderForm.amount" type="number" min="1" class="input input-num" :placeholder="t('account.amount')" />
            <button class="btn btn-primary" :disabled="createOrderLoading" @click="doCreateRechargeOrder">{{ t('account.createOrder') }}</button>
          </div>
          <div v-if="lastRechargeOrder" class="recharge-order-result">
            <p v-if="lastRechargeOrder.payment_url">
              {{ t('account.paymentUrl') }}：<a :href="lastRechargeOrder.payment_url" target="_blank" rel="noopener noreferrer">{{ lastRechargeOrder.payment_url }}</a>
            </p>
            <p v-if="lastRechargeOrder.payment_qr">{{ t('account.paymentQr') }}：<code>{{ lastRechargeOrder.payment_qr }}</code></p>
            <p v-if="lastRechargeOrder.btc_address">{{ t('account.btcAddress') }}：<code>{{ lastRechargeOrder.btc_address }}</code></p>
            <button class="btn btn-secondary" :disabled="confirmOrderLoading" @click="doConfirmRecharge">{{ t('account.confirmPaySimulate') }}</button>
          </div>
        </div>
        <div class="account-section">
          <h4>{{ t('account.paymentMethods') }}</h4>
          <div class="form bind-form">
            <select v-model="bindPaymentForm.type" class="input">
              <option value="alipay">{{ t('account.alipay') }}</option>
              <option value="credit_card">{{ t('account.credit_card') }}</option>
              <option value="bitcoin">{{ t('account.bitcoin') }}</option>
            </select>
            <input v-model="bindPaymentForm.masked_info" class="input" :placeholder="t('account.maskedInfoPlaceholder')" />
            <button class="btn btn-secondary" :disabled="bindLoading" @click="doBindPayment">{{ t('common.add') }}</button>
          </div>
          <ul class="payment-list">
            <li v-for="pm in paymentMethods" :key="pm.id">
              <span class="pm-type">{{ t('account.' + pm.type) }}</span> {{ pm.masked_info }}
              <button class="btn btn-sm link-btn" @click="doUnbind(pm.id)">{{ t('common.unbind') }}</button>
            </li>
            <p v-if="paymentMethods.length === 0 && !paymentMethodsLoading" class="hint">{{ t('account.noPaymentMethods') }}</p>
          </ul>
        </div>
        <div class="account-section">
          <h4>{{ t('account.recentTransactions') }}</h4>
          <ul class="tx-list">
            <li v-for="tx in transactions" :key="tx.id">
              <span :class="tx.amount > 0 ? 'tx-in' : 'tx-out'">{{ tx.amount > 0 ? '+' : '' }}{{ tx.amount }}</span>
              {{ t('txType.' + tx.type) }} · {{ tx.remark || '-' }}
              <span class="tx-time">{{ tx.created_at ? tx.created_at.slice(0, 19) : '' }}</span>
            </li>
            <p v-if="transactions.length === 0 && !transactionsLoading" class="hint">{{ t('account.noTransactions') }}</p>
          </ul>
        </div>
        <button class="btn btn-secondary close-btn" @click="showAccountModal = false">{{ t('common.close') }}</button>
      </div>
    </div>

    <!-- 提交完成弹窗（接取者填写结果摘要）-->
    <div v-if="submitCompletionTask" class="modal-mask" @click.self="submitCompletionTask = null">
      <div class="modal">
        <h3>{{ t('task.submitCompletionTitle', { title: submitCompletionTask.title }) }}</h3>
        <p class="hint">{{ t('task.submitCompletionHint') }}</p>
        <div class="form">
          <textarea v-model="submitCompletionForm.result_summary" class="input textarea" :placeholder="t('task.resultSummaryPlaceholder')" rows="3" />
          <button class="btn btn-primary" :disabled="submitCompletionLoading" @click="doSubmitCompletion">{{ t('task.submitCompletion') }}</button>
        </div>
        <button class="btn btn-secondary close-btn" @click="submitCompletionTask = null">{{ t('common.cancel') }}</button>
      </div>
    </div>

    <!-- 选择 Agent 接取任务弹窗 -->
    <div v-if="subscribeTaskItem" class="modal-mask" @click.self="subscribeTaskItem = null">
      <div class="modal">
        <h3>{{ t('task.selectAgentTitle', { title: subscribeTaskItem.title }) }}</h3>
        <div class="agent-select-list">
          <button
            v-for="a in myAgents"
            :key="a.id"
            class="btn btn-secondary block"
            :disabled="subscribeLoading === subscribeTaskItem.id"
            @click="doSubscribe(subscribeTaskItem.id, a.id)"
          >
            {{ a.name }}（{{ a.agent_type }}）
          </button>
        </div>
        <button class="btn btn-secondary close-btn" @click="subscribeTaskItem = null">{{ t('common.cancel') }}</button>
      </div>
    </div>

    <!-- 帮助文档弹窗：OpenClaw Skill 下载与配置 -->
    <div v-if="showHelpModal" class="modal-mask" data-testid="help-modal-mask" @click.self="showHelpModal = false">
      <div class="modal modal-help" data-testid="help-modal">
        <h3>{{ t('help.title') }}</h3>
        <section class="help-section">
          <h4>{{ t('help.downloadTitle') }}</h4>
          <ol class="help-list">
            <li v-for="(stepKey, i) in helpDownloadStepKeys" :key="i">{{ t(stepKey) }}</li>
          </ol>
          <p class="help-note">{{ t('help.downloadNote') }}</p>
        </section>
        <section class="help-section">
          <h4>{{ t('help.configTitle') }}</h4>
          <ul class="help-list help-vars">
            <li><code>CLAWJOB_API_URL</code> — {{ t('help.configApiUrl') }}</li>
            <li><code>CLAWJOB_ACCESS_TOKEN</code> — {{ t('help.configToken') }}</li>
          </ul>
          <p class="help-note">{{ t('help.configNote') }}</p>
        </section>
        <section class="help-section">
          <h4>{{ t('help.quickRegisterTitle') }}</h4>
          <pre class="help-code">export CLAWJOB_API_URL=http://localhost:8000
python3 tools/quick_register.py &lt;用户名&gt; &lt;邮箱&gt; &lt;密码&gt;</pre>
          <p class="help-note">{{ t('help.quickRegisterNote') }}</p>
        </section>
        <p class="help-skill-link">
          <router-link to="/docs" class="btn btn-text" @click="showHelpModal = false">{{ t('help.fullDocsLink') }}</router-link>
          <router-link to="/skill" class="btn btn-primary" @click="showHelpModal = false">{{ t('help.fullSetupLink') }}</router-link>
        </p>
        <button type="button" class="btn btn-secondary close-btn" @click="showHelpModal = false">{{ t('common.close') }}</button>
      </div>
    </div>

    <!-- 成功提示 Toast -->
    <Transition name="toast">
      <div v-if="successToast" class="toast" role="status">{{ successToast }}</div>
    </Transition>

    <footer class="app-footer">
      <p>ClawJob · {{ t('common.tagline') }}</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { i18n, setLocale, safeT, type LocaleKey } from './i18n'
import { useAuthStore } from './stores/auth'
import * as api from './api'
import SkillPage from './views/SkillPage.vue'
import DocsPage from './views/DocsPage.vue'
import ManualPage from './views/ManualPage.vue'
import TaskManageView from './views/TaskManageView.vue'
import AgentManageView from './views/AgentManageView.vue'

const route = useRoute()
const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const auth = useAuthStore()
const locale = ref<LocaleKey>('zh-CN')
function onLocaleChange() {
  setLocale(locale.value)
}
const googleLoginUrl = computed(() => api.getGoogleLoginUrl())
const googleOAuthConfigured = ref(true) // 在请求 /auth/google/status 前先显示按钮，避免闪烁
const googleConfigError = ref('') // 未配置时后端返回的提示，用于在弹窗内展示
const skillRepoUrl = (import.meta as any).env?.VITE_SKILL_REPO_URL || 'https://github.com/clawjob/clawjob/tree/main/skills/clawjob'

const showAuthModal = ref(false)
const authTab = ref<'login' | 'register'>('login')
const authLoading = ref(false)
const authError = ref('')
const oauthError = ref('')
const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '', verification_code: '' })
const sendCodeLoading = ref(false)
const sendCodeCountdown = ref(0)
let sendCodeTimer: ReturnType<typeof setInterval> | null = null

const tasks = ref<Array<{
  id: number
  title: string
  description: string
  status: string
  publisher_name: string
  owner_id: number
  subscription_count: number
  reward_points?: number
  submitted_at?: string
  verification_deadline_at?: string
}>>([])
const tasksLoading = ref(false)

const publishForm = reactive({ title: '', description: '', reward_points: 0, completion_webhook_url: '', invited_agent_ids: [] as number[] })
const publishLoading = ref(false)
const publishError = ref('')

const candidates = ref<Array<{ id: number; name: string; description: string; agent_type: string; owner_name: string }>>([])
const candidatesLoading = ref(false)
const myAgents = ref<Array<{ id: number; name: string; description: string; agent_type: string }>>([])
const agentsLoading = ref(false)
const agentForm = reactive({ name: '', description: '' })
const agentLoading = ref(false)
const agentError = ref('')

const subscribeTaskItem = ref<{ id: number; title: string } | null>(null)
const subscribeLoading = ref<number | null>(null)
const submitCompletionTask = ref<{ id: number; title: string } | null>(null)
const submitCompletionForm = reactive({ result_summary: '' })
const submitCompletionLoading = ref(false)
const confirmLoading = ref<number | null>(null)
const rejectLoading = ref<number | null>(null)

const showAccountModal = ref(false)
const tokenCopied = ref(false)
const envSnippetCopied = ref(false)
const showHelpModal = ref(false)
const SKILL_BANNER_KEY = 'clawjob_skill_banner_dismissed'
const showSkillBanner = ref(false)
const showAgentGuide = ref(false)
const successToast = ref('')
function showSuccess(message: string) {
  successToast.value = message
  setTimeout(() => { successToast.value = '' }, 2200)
}
function dismissSkillBanner() {
  try { localStorage.setItem(SKILL_BANNER_KEY, '1') } catch (_) {}
  showSkillBanner.value = false
}

function scrollToPublishSection() {
  document.getElementById('section-publish')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function scrollToAgentSection() {
  document.getElementById('section-my-agents')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/** 使用 Google 登录：未配置时在弹窗内展示错误，已配置时整页跳转后端 OAuth */
function onGoogleLoginClick(e: Event) {
  e.preventDefault()
  if (!googleOAuthConfigured.value) {
    authError.value = googleConfigError.value || t('oauthError.server_config')
    return
  }
  window.location.href = api.getGoogleLoginUrl()
}

async function copyApiToken() {
  if (!auth.token) return
  try {
    await navigator.clipboard.writeText(auth.token)
    tokenCopied.value = true
    setTimeout(() => { tokenCopied.value = false }, 2000)
  } catch (_) {
    tokenCopied.value = false
  }
}

async function copyEnvSnippet() {
  if (!auth.token) return
  const apiBase = api.getApiBase()
  const snippet = `export CLAWJOB_API_URL=${apiBase}\nexport CLAWJOB_ACCESS_TOKEN=${auth.token}`
  try {
    await navigator.clipboard.writeText(snippet)
    envSnippetCopied.value = true
    setTimeout(() => { envSnippetCopied.value = false }, 2000)
  } catch (_) {
    envSnippetCopied.value = false
  }
}

function onEscapeKey(e: KeyboardEvent) {
  if (e.key !== 'Escape') return
  if (showAuthModal.value) { showAuthModal.value = false; return }
  if (showAccountModal.value) { showAccountModal.value = false; return }
  if (submitCompletionTask.value) { submitCompletionTask.value = null; return }
  if (subscribeTaskItem.value) { subscribeTaskItem.value = null; return }
  if (showHelpModal.value) { showHelpModal.value = false }
}
const accountCredits = ref(0)
const commissionBalance = ref(0)
const receivingAccountForm = reactive({ account_type: 'alipay', account_name: '', account_number: '' })
const receivingAccountLoading = ref(false)
const receivingAccountError = ref('')
const rechargeForm = reactive({ amount: 100 })
const rechargeLoading = ref(false)
const rechargeError = ref('')
const rechargeOrderForm = reactive({ payment_method_type: 'credit_card', amount: 100 })
const createOrderLoading = ref(false)
const lastRechargeOrder = ref<{ order_id: number; payment_url?: string; payment_qr?: string; btc_address?: string; status: string } | null>(null)
const confirmOrderLoading = ref(false)
const paymentMethods = ref<Array<{ id: number; type: string; masked_info: string }>>([])
const paymentMethodsLoading = ref(false)
const bindPaymentForm = reactive({ type: 'alipay', masked_info: '' })
const bindLoading = ref(false)
const transactions = ref<Array<{ id: number; amount: number; type: string; remark: string | null; created_at: string | null }>>([])
const transactionsLoading = ref(false)

function loadTasks() {
  tasksLoading.value = true
  api.fetchTasks().then((res) => {
    tasks.value = res.data.tasks || []
  }).catch(() => {
    tasks.value = []
  }).finally(() => {
    tasksLoading.value = false
  })
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
  agentsLoading.value = true
  api.fetchMyAgents().then((res) => {
    myAgents.value = res.data.agents || []
  }).catch(() => {
    myAgents.value = []
  }).finally(() => {
    agentsLoading.value = false
  })
}

function doLogin() {
  authError.value = ''
  authLoading.value = true
  api.login(loginForm).then((res) => {
    auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
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
  api.register({
    username: registerForm.username,
    email: registerForm.email,
    password: registerForm.password,
    verification_code: registerForm.verification_code,
  }).then((res) => {
    auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
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
  api.publishTask({
    title: publishForm.title.trim(),
    description: publishForm.description.trim(),
    reward_points: reward,
    completion_webhook_url: webhook || undefined,
    invited_agent_ids: publishForm.invited_agent_ids?.length ? publishForm.invited_agent_ids.map(Number).filter(Boolean) : undefined,
  }).then(() => {
    publishForm.title = ''
    publishForm.description = ''
    publishForm.reward_points = 0
    publishForm.completion_webhook_url = ''
    publishForm.invited_agent_ids = []
    showSuccess(t('task.publishSuccess'))
    loadAccountMe()
    loadTasks()
  }).catch((e) => {
    publishError.value = e.response?.data?.detail || t('task.publishErrorGeneric')
  }).finally(() => {
    publishLoading.value = false
  })
}

function doRegisterAgent() {
  if (!agentForm.name.trim()) return
  agentError.value = ''
  agentLoading.value = true
  api.registerAgent({
    name: agentForm.name.trim(),
    description: agentForm.description.trim(),
  }).then(() => {
    agentForm.name = ''
    agentForm.description = ''
    loadMyAgents()
  }).catch((e) => {
    agentError.value = e.response?.data?.detail || t('common.registerFailed')
  }).finally(() => {
    agentLoading.value = false
  })
}

function openSubscribeModal(task: { id: number; title: string }) {
  subscribeTaskItem.value = task
}

function doSubscribe(taskId: number, agentId: number) {
  subscribeLoading.value = taskId
  api.subscribeTask(taskId, agentId).then(() => {
    subscribeTaskItem.value = null
    showSuccess(t('task.subscribeSuccess'))
    loadTasks()
  }).catch(() => {}).finally(() => {
    subscribeLoading.value = null
  })
}

function formatDeadline(iso: string) {
  if (!iso) return ''
  return iso.slice(0, 19).replace('T', ' ')
}
function isExecutor(t: { agent_id?: number }) {
  if (!auth.userId || !t.agent_id) return false
  return myAgents.value.some((a) => a.id === t.agent_id)
}
function getTaskSkills(t: { skills?: string[] | string }): string[] {
  if (!t.skills) return []
  if (Array.isArray(t.skills)) return t.skills
  if (typeof t.skills === 'string') return t.skills.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
  return []
}
function openSubmitCompletionModal(task: { id: number; title: string }) {
  submitCompletionTask.value = task
  submitCompletionForm.result_summary = ''
}
function doSubmitCompletion() {
  if (!submitCompletionTask.value) return
  const taskId = submitCompletionTask.value.id
  submitCompletionLoading.value = true
  api.submitCompletion(taskId, { result_summary: submitCompletionForm.result_summary.trim() }).then(() => {
    submitCompletionTask.value = null
    showSuccess(t('task.submitCompletionSuccess'))
    loadTasks()
  }).catch(() => {}).finally(() => { submitCompletionLoading.value = false })
}
function doConfirm(taskId: number) {
  confirmLoading.value = taskId
  api.confirmTask(taskId).then(() => {
    showSuccess(t('task.confirmSuccess'))
    loadTasks()
    loadAccountMe()
  }).catch(() => {}).finally(() => { confirmLoading.value = null })
}
function doReject(taskId: number) {
  rejectLoading.value = taskId
  api.rejectTask(taskId).then(() => {
    showSuccess(t('task.rejectSuccess'))
    loadTasks()
  }).catch(() => {}).finally(() => { rejectLoading.value = null })
}

function loadAccountMe() {
  if (!auth.isLoggedIn) return
  api.getAccountMe().then((res) => {
    if (res.data.user_id != null) auth.setUserId(res.data.user_id)
    accountCredits.value = res.data.credits ?? 0
  }).catch(() => {})
}

function loadAccountData() {
  if (!auth.isLoggedIn) return
  loadAccountMe()
  api.getCommission().then((res) => {
    commissionBalance.value = res.data.commission_balance ?? 0
  }).catch(() => {})
  api.getReceivingAccount().then((res) => {
    receivingAccountForm.account_type = res.data.account_type || 'alipay'
    receivingAccountForm.account_name = res.data.account_name || ''
    receivingAccountForm.account_number = res.data.account_number || ''
  }).catch(() => {})
  paymentMethodsLoading.value = true
  api.getPaymentMethods().then((res) => {
    paymentMethods.value = res.data.payment_methods || []
  }).catch(() => {}).finally(() => { paymentMethodsLoading.value = false })
  transactionsLoading.value = true
  api.getTransactions({ limit: 20 }).then((res) => {
    transactions.value = res.data.transactions || []
  }).catch(() => {}).finally(() => { transactionsLoading.value = false })
}

function doSaveReceivingAccount() {
  receivingAccountLoading.value = true
  api.updateReceivingAccount({
    account_type: receivingAccountForm.account_type,
    account_name: receivingAccountForm.account_name,
    account_number: receivingAccountForm.account_number,
  }).then(() => {
    receivingAccountError.value = ''
    showSuccess(t('account.receivingAccountSaved'))
  }).catch((e) => {
    receivingAccountError.value = e.response?.data?.detail || t('account.receivingAccountSaveFailed')
  }).finally(() => { receivingAccountLoading.value = false })
}

function doRecharge() {
  const amount = Number(rechargeForm.amount) || 0
  if (amount <= 0) return
  rechargeError.value = ''
  rechargeLoading.value = true
  api.recharge({ amount }).then((res) => {
    accountCredits.value = res.data.credits ?? 0
    if (showAccountModal.value) {
      api.getTransactions({ limit: 20 }).then((r) => { transactions.value = r.data.transactions || [] })
    }
  }).catch((e) => {
    rechargeError.value = e.response?.data?.detail || '充值失败'
  }).finally(() => { rechargeLoading.value = false })
}

function doCreateRechargeOrder() {
  const amount = Number(rechargeOrderForm.amount) || 0
  if (amount <= 0) return
  rechargeError.value = ''
  createOrderLoading.value = true
  lastRechargeOrder.value = null
  api.createRechargeOrder({ amount, payment_method_type: rechargeOrderForm.payment_method_type }).then((res) => {
    lastRechargeOrder.value = {
      order_id: res.data.order_id,
      payment_url: res.data.payment_url,
      payment_qr: res.data.payment_qr,
      btc_address: res.data.btc_address,
      status: res.data.status,
    }
  }).catch((e) => {
    rechargeError.value = e.response?.data?.detail || '创建订单失败'
  }).finally(() => { createOrderLoading.value = false })
}

function doConfirmRecharge() {
  if (!lastRechargeOrder.value) return
  confirmOrderLoading.value = true
  api.confirmRecharge({ order_id: lastRechargeOrder.value.order_id }).then((res) => {
    accountCredits.value = res.data.credits ?? 0
    lastRechargeOrder.value = null
    if (showAccountModal.value) {
      api.getTransactions({ limit: 20 }).then((r) => { transactions.value = r.data.transactions || [] })
    }
  }).catch((e) => {
    rechargeError.value = e.response?.data?.detail || '确认失败'
  }).finally(() => { confirmOrderLoading.value = false })
}

function doBindPayment() {
  const type = bindPaymentForm.type
  const masked_info = bindPaymentForm.masked_info.trim() || `${type} ***`
  bindLoading.value = true
  api.bindPaymentMethod({ type, masked_info }).then(() => {
    bindPaymentForm.masked_info = ''
    api.getPaymentMethods().then((res) => { paymentMethods.value = res.data.payment_methods || [] })
  }).catch(() => {}).finally(() => { bindLoading.value = false })
}

function doUnbind(pmId: number) {
  api.unbindPaymentMethod(pmId).then(() => {
    paymentMethods.value = paymentMethods.value.filter((p) => p.id !== pmId)
  })
}

const helpDownloadStepKeys = ['help.step1', 'help.step2', 'help.step3']

onMounted(() => {
  // 延后到 onMounted 再拉取，避免首屏被阻塞或未挂载时请求导致异常
  // 仅当接口明确返回 configured: false 时禁用按钮；请求失败（跨域/网络）时保持可点，让用户尝试点击
  api.getGoogleOAuthStatus().then((s) => {
    googleOAuthConfigured.value = s.configured
    googleConfigError.value = s.config_error || ''
  }).catch(() => { googleOAuthConfigured.value = true; googleConfigError.value = '' })
  document.addEventListener('keydown', onEscapeKey)
  locale.value = i18n.global.locale.value as LocaleKey
  try { showSkillBanner.value = false } catch (_) {}
  // Google OAuth 错误：后端重定向到 FRONTEND_URL#/?error=xxx 或 FRONTEND_URL?error=xxx
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
    // 成功回调：优先读 query（后端 302 用 query 传参，避免 fragment 被丢弃）；兼容 hash #/auth/callback?...
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
  loadTasks()
  loadCandidates()
  if (auth.isLoggedIn) {
    loadAccountMe()
    loadMyAgents()
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', onEscapeKey)
})

watch(showAccountModal, (open) => {
  if (open) {
    receivingAccountError.value = ''
    loadAccountData()
  }
})
</script>

<style scoped>
.header-brand {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.header-brand:hover .tagline { color: var(--text-primary); }
.tagline {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin: 0.15rem 0 0 0;
  font-weight: 400;
}
.btn-text {
  background: transparent;
  border: none;
  color: var(--primary-color);
  font-size: 0.9rem;
  padding: 0.35rem 0.5rem;
  cursor: pointer;
}
.btn-text:hover { text-decoration: underline; }
.btn-text:focus-visible { outline: none; box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.3); border-radius: 4px; }
.modal-help {
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
}
.modal-help h3 { margin-bottom: 1rem; }
.help-section { margin-bottom: 1.25rem; }
.help-section h4 { font-size: 0.95rem; margin-bottom: 0.5rem; color: var(--text-secondary); }
.help-list { margin: 0 0 0 1.25rem; padding: 0; font-size: 0.9rem; line-height: 1.5; color: var(--text-primary); }
.help-list li { margin-bottom: 0.35rem; }
.help-vars { list-style: none; margin-left: 0; }
.help-vars code { background: var(--background-darker); padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.85rem; }
.help-note { font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.5rem; }
.help-code {
  background: var(--background-darker);
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  overflow-x: auto;
  white-space: pre;
  margin: 0.5rem 0 0 0;
}
.credits-badge {
  margin-right: 0.75rem;
  font-size: 0.9rem;
  color: var(--text-secondary);
}
.reward-points {
  color: var(--primary-color);
}
.task-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin-top: 0.5rem;
}
.input-num {
  min-width: 90px;
  width: 90px;
}
.form-group.form-inline .input-num { flex-shrink: 0; }
.publish-form .form-inline { margin-bottom: 0.5rem; }
.publish-form .full-width { width: 100%; margin-top: 0.5rem; }
.field-hint, .deadline-hint { margin-top: 0.35rem; font-size: 0.85rem; }
.textarea { resize: vertical; min-height: 60px; }
.modal-account {
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 1.5rem 1.75rem;
}
.balance-line,
.commission-balance-line {
  font-size: 1.1rem;
  margin-bottom: 1rem;
}
.receiving-account-form .input,
.receiving-account-form select {
  display: block;
  width: 100%;
  margin-bottom: 0.5rem;
}
.receiving-account-form .btn { margin-top: 0.25rem; }
.recharge-channel-title {
  font-size: 0.9rem;
  margin: 1rem 0 0.5rem;
  color: var(--text-secondary);
}
.recharge-order-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.5rem;
}
.recharge-order-form .input-num { min-width: 80px; width: 80px; }
.recharge-order-result {
  margin-top: 0.75rem;
  padding: 0.6rem;
  background: var(--background-darker);
  border-radius: 6px;
  font-size: 0.9rem;
}
.recharge-order-result p { margin: 0.35rem 0; }
.recharge-order-result code { word-break: break-all; font-size: 0.85rem; }
.recharge-order-result a { color: var(--primary-color); }
.account-section {
  margin-bottom: 1.25rem;
}
.account-section h4 {
  font-size: 0.95rem;
  margin-bottom: 0.5rem;
  color: var(--text-secondary);
}
.token-copy-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.token-copy-row code.token-masked {
  font-size: 0.85rem;
  word-break: break-all;
  max-width: 100%;
}
.bind-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
.bind-form .input { flex: 1; min-width: 120px; }
.payment-list, .tx-list {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0 0;
  font-size: 0.9rem;
}
.payment-list li, .tx-list li {
  padding: 0.35rem 0;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.pm-type { font-weight: 600; color: var(--primary-color); }
.link-btn { margin-left: auto; }
.tx-in { color: var(--success-color); }
.tx-out { color: var(--danger-color); }
.tx-time { font-size: 0.8rem; color: var(--text-secondary); margin-left: auto; }
.app-container {
  min-width: 0;
  overflow-x: hidden;
}
.app-header {
  position: relative;
  z-index: 100;
}
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1.5rem 2rem;
  width: 100%;
  min-width: 0;
}
.oauth-error-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 1rem;
  background: var(--danger-color);
  color: #fff;
  font-size: 0.9rem;
}
.oauth-error-banner .btn { background: rgba(255,255,255,0.3); color: #fff; }
.hero-section {
  position: relative;
  padding: 1.25rem 0 1.5rem;
  margin-bottom: 1rem;
}
.hero-section.hero-home { padding: 1rem 0 1.25rem; }
.hero-inner {
  position: relative;
  max-width: 48rem;
  margin: 0 auto;
  text-align: center;
}
.hero-home .hero-inner { max-width: 40rem; }
.hero-title {
  font-size: clamp(1.5rem, 3.5vw, 2rem);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.4rem;
  line-height: 1.25;
}
.hero-home .hero-title { margin-bottom: 0.35rem; }
.hero-title-gradient {
  background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-desc {
  font-size: 0.95rem;
  color: var(--text-secondary);
  max-width: 36rem;
  margin: 0 auto;
  line-height: 1.55;
}
.hero-home .hero-desc { font-size: 0.9rem; max-width: 32rem; }
.home-grid {
  display: grid;
  grid-template-columns: minmax(280px, 380px) 1fr;
  gap: 2rem 2.5rem;
  align-items: start;
}
@media (max-width: 900px) {
  .home-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
}
@media (max-width: 600px) {
  .main-content { padding: 0 1rem 1.5rem; }
  .app-header { padding: 0.75rem 1rem; }
  .header-content { flex-wrap: wrap; gap: 0.5rem; }
  .header-nav { margin-left: 0; }
}
.home-aside {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.agent-guide-card {
  border-left: 4px solid var(--primary-color);
}
.agent-guide-card:hover {
  transform: none;
}
.agent-guide-title {
  font-size: 1rem;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}
.agent-guide-intro {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 0.75rem;
}
.agent-guide-skill {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}
.agent-guide-link {
  color: var(--primary-color);
  text-decoration: none;
}
.agent-guide-link:hover {
  text-decoration: underline;
}
.agent-guide-examples {
  margin: 0.75rem 0;
  padding: 0.6rem 0.75rem;
  background: var(--background-darker);
  border-radius: 6px;
  font-size: 0.85rem;
  color: var(--text-secondary);
}
.agent-guide-example-title {
  font-weight: 600;
  margin-bottom: 0.4rem;
  color: var(--text-primary);
}
.agent-guide-example {
  margin: 0.25rem 0;
  line-height: 1.45;
}
.agent-guide-steps {
  margin: 0 0 0.75rem 1.2rem;
  padding: 0;
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.5;
}
.agent-guide-steps li { margin-bottom: 0.35rem; }
.agent-guide-api {
  font-size: 0.8rem;
  color: var(--text-secondary);
  background: var(--background-darker);
  padding: 0.6rem 0.75rem;
  border-radius: 6px;
  word-break: break-all;
}
.agent-guide-commission {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-top: 0.5rem;
}
.form-group {
  margin-bottom: 0.75rem;
}
.form-group.form-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
.form-label {
  display: block;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 0.35rem;
}
.form-group.form-inline .form-label { margin-bottom: 0; margin-right: 0.25rem; }
.required { color: var(--danger-color); }
.section-full { margin-top: 1.5rem; }
.section {
  margin-bottom: 1.5rem;
}
.section-title {
  font-size: 1.2rem;
  margin-bottom: 0.75rem;
  color: var(--text-primary);
}
.task-hall-section .section-title { margin-top: 0; }
.section-desc { margin-top: -0.5rem; margin-bottom: 0.75rem; font-size: 0.9rem; }
.candidates-section { margin-bottom: 1rem; }
.candidates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}
.candidate-card {
  padding: 0.75rem;
}
.candidate-card .card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.35rem;
}
.candidate-card .card-header strong { font-size: 0.95rem; }
.candidate-owner-badge { font-size: 0.8rem; color: var(--text-secondary); }
.candidate-desc { font-size: 0.85rem; color: var(--text-secondary); margin: 0; line-height: 1.4; }
.candidates-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  max-height: 120px;
  overflow-y: auto;
  padding: 0.5rem 0;
}
.candidate-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.9rem;
  cursor: pointer;
  white-space: nowrap;
}
.candidate-checkbox input { margin: 0; }
.candidate-checkbox .candidate-name { color: var(--text-primary); }
.candidate-checkbox .candidate-owner { color: var(--text-secondary); font-size: 0.85rem; }
.invited-only-badge {
  margin-left: 0.5rem;
  font-size: 0.75rem;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  background: var(--border-color);
  color: var(--text-secondary);
}

/* 智能体快捷发布说明：默认折叠 */
.agent-guide-wrap {
  margin-top: 1rem;
}
.agent-guide-trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.9rem;
  color: var(--primary-color);
  background: transparent;
  border: 1px dashed var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.agent-guide-trigger:hover {
  border-color: var(--primary-color);
  background: rgba(var(--primary-rgb, 59, 130, 246), 0.06);
}
.agent-guide-trigger-icon {
  font-size: 1.1rem;
  line-height: 1;
}
.agent-guide-card {
  margin-top: 0;
}
.agent-guide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}
.agent-guide-title {
  font-size: 1rem;
  margin: 0;
  color: var(--text-primary);
}
.agent-guide-collapse {
  flex-shrink: 0;
  font-size: 0.85rem;
  color: var(--text-secondary);
}
.agent-guide-intro,
.agent-guide-skill,
.agent-guide-api,
.agent-guide-commission {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin: 0 0 0.5rem;
}
.agent-guide-link {
  color: var(--primary-color);
  text-decoration: none;
}
.agent-guide-link:hover { text-decoration: underline; }
.agent-guide-steps {
  margin: 0.5rem 0 0.75rem;
  padding-left: 1.25rem;
  font-size: 0.9rem;
  color: var(--text-secondary);
}
.agent-guide-steps li { margin-bottom: 0.25rem; }
.agent-guide-examples {
  margin: 0.5rem 0 0.75rem;
}
.agent-guide-example-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.35rem;
}
.agent-guide-example {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 0 0 0.2rem;
  font-family: var(--font-mono, monospace);
}

.publish-card .form-inline,
.agent-form-card .form-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}
.publish-form .form-group:last-of-type { margin-bottom: 0; }
.input {
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--background-dark);
  color: var(--text-primary);
  min-width: 160px;
  width: 100%;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.2);
}
.form-group .input { min-width: 0; }
.task-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.task-card .badge {
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  background: var(--border-color);
}
.task-card .badge.open { background: var(--success-color); }
.task-card .badge.pending_verification { background: #e6a800; color: #1a1a1a; }
.task-card .meta, .desc-small {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-top: 0.5rem;
}
.task-card--structured { padding: 1rem 1.25rem; }
.task-card--structured .task-card__top { display: flex; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.35rem; }
.task-card--structured .task-card__type { font-size: 0.75rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.02em; }
.task-card--structured .task-card__reward { margin-left: auto; font-size: 0.95rem; font-weight: 600; color: var(--primary-color); }
.task-card--structured .task-card__title { font-size: 1.05rem; margin: 0 0 0.4rem; font-weight: 600; line-height: 1.3; }
.task-card--structured .task-card__desc { font-size: 0.9rem; color: var(--text-secondary); margin: 0 0 0.5rem; line-height: 1.45; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.task-card--structured .task-card__tags,
.task-card--structured .task-card__attrs { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.5rem; }
.task-tag, .task-attr { display: inline-block; font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 999px; background: var(--card-background); color: var(--text-secondary); border: 1px solid var(--border-color); }
.task-tag--location, .task-attr--location { border-color: rgba(34, 197, 94, 0.5); color: #16a34a; }
.task-tag--duration, .task-attr--duration { border-color: rgba(59, 130, 246, 0.5); color: #2563eb; }
.task-tag--skill, .task-attr--skill { border-color: rgba(168, 85, 247, 0.5); color: #7c3aed; }
.task-card--structured .task-card__meta { font-size: 0.8rem; color: var(--text-secondary); margin: 0 0 0.5rem; }
.task-card--structured .task-card__actions-wrap { padding: 0; margin-top: 0.25rem; border: none; }
.section-candidates-compact { margin-top: 0.5rem; }
.section-title--small { font-size: 1rem; margin-bottom: 0.5rem; }
.candidates-list-compact { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.candidate-chip { display: inline-flex; align-items: center; gap: 0.25rem; font-size: 0.8rem; padding: 0.25rem 0.5rem; border-radius: 6px; background: var(--card-background); border: 1px solid var(--border-color); color: var(--text-primary); }
.candidate-chip-name { font-weight: 500; }
.candidate-chip-owner { font-size: 0.75rem; color: var(--text-secondary); }
.hint--small { font-size: 0.8rem; margin-top: 0.25rem; }
.task-hall-main .section-title { margin-bottom: 0.75rem; }
.agent-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}
.agent-type {
  font-size: 0.8rem;
  color: var(--primary-color);
  margin-left: 0.5rem;
}
.hint, .empty {
  color: var(--text-secondary);
  font-size: 0.9rem;
}
.publish-gate, .agent-gate {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: flex-start;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem 1rem;
  text-align: center;
}
.empty-state .empty { margin: 0; }
.error-msg {
  color: var(--danger-color);
  font-size: 0.9rem;
  margin-top: 0.5rem;
}
.btn-sm { padding: 0.35rem 0.75rem; font-size: 0.85rem; }
/* Toast */
.toast {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.6rem 1.25rem;
  background: var(--card-background);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  font-size: 0.95rem;
  color: var(--text-primary);
  box-shadow: 0 4px 20px var(--shadow-color);
  z-index: 200;
}
.toast-enter-active, .toast-leave-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(10px); }

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: modal-fade-in 0.2s ease;
}
.modal {
  background: var(--card-background);
  border-radius: 12px;
  padding: 1.5rem;
  max-width: 400px;
  width: 90%;
  border: 1px solid var(--border-color);
  animation: modal-scale-in 0.22s ease;
}
@keyframes modal-fade-in { from { opacity: 0; } to { opacity: 1; } }
@keyframes modal-scale-in { from { opacity: 0; transform: scale(0.96); } to { opacity: 1; transform: scale(1); } }
.help-skill-link {
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.help-skill-link .btn { display: inline-block; text-decoration: none; }
.modal h3 { margin-bottom: 1rem; }
.tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
.tabs .active { border-color: var(--primary-color); color: var(--primary-color); }
.form { display: flex; flex-direction: column; gap: 0.75rem; }
.form .input { width: 100%; min-width: 0; }
.agent-select-list { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; }
.btn.block { width: 100%; text-align: left; }
.close-btn { margin-top: 1rem; }
.verification-code-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.verification-code-row .input { flex: 1; min-width: 0; }
.oauth-divider {
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin: 0.75rem 0;
}
.btn-google {
  display: block;
  text-align: center;
  padding: 0.5rem 1rem;
  background: #fff;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.95rem;
}
.btn-google:hover {
  background: #f5f5f5;
  border-color: #ccc;
}
/* 服务端可能未配置时仍可点击，由后端返回错误提示 */
.btn-google-unconfigured {
  opacity: 0.85;
}
.google-config-hint {
  margin-top: 0.5rem;
  font-size: 0.85rem;
}
</style>
