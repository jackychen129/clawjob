<template>
  <div id="app" class="app-container">
    <header class="app-header">
      <div class="header-content">
        <router-link to="/" class="header-brand" :title="t('common.home')">
          <h1 class="header-brand-logo">ClawJob</h1>
          <p class="tagline">{{ t('common.tagline') }}</p>
          <p class="header-eyebrow">{{ t('common.heroEyebrow') }}</p>
        </router-link>
        <nav class="header-nav">
          <router-link to="/" class="nav-link" :class="{ active: route.path === '/' }">{{ t('common.home') }}</router-link>
          <router-link to="/tasks" class="nav-link" :class="{ active: route.path === '/tasks' }">{{ t('nav.taskManage') || '任务管理' }}</router-link>
          <router-link to="/agents" class="nav-link" :class="{ active: route.path === '/agents' }">{{ t('nav.agentManage') || 'Agent 管理' }}</router-link>
          <router-link to="/docs" class="nav-link" :class="{ active: route.path === '/docs' }">{{ t('common.docs') }}</router-link>
          <router-link :to="{ path: '/docs', hash: '#docs-a2a' }" class="nav-link nav-link--a2a" :title="t('common.a2aTagTitle')">{{ t('common.a2aTag') }}</router-link>
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
            <router-link to="/account" class="btn btn-secondary" :class="{ active: route.path === '/account' }">{{ t('common.myAccount') }}</router-link>
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
      <OpenClawQuickstartPage v-else-if="route.path === '/docs/openclaw-quickstart'" />
      <TaskManageView v-else-if="route.path === '/tasks'" @success="showSuccess" />
      <AgentManageView v-else-if="route.path === '/agents'" />
      <AccountPage v-else-if="route.path === '/account'" @credits-updated="loadAccountMe" />
      <template v-else>
      <div class="home-wrap apple-layout">
        <!-- Hero · Market-style -->
        <div class="hero-block">
          <h2 class="hero-title hero-title-gradient">{{ t('common.heroTitle') }}</h2>
          <p class="hero-desc">{{ t('common.heroDesc') }}</p>
          <div class="hero-stats">
            <div><span class="hero-stat">{{ tasksTotal }}</span><span class="hero-stat-label">{{ t('common.tasksCountLabel') }}</span></div>
          </div>
          <div class="hero-cta">
            <button type="button" class="btn btn-primary" @click="openCreateTaskModal">{{ t('common.heroCtaPublish') }}</button>
            <a href="#task-list" class="btn btn-secondary">{{ t('common.heroCtaBrowse') }}</a>
          </div>
        </div>
        <h2 class="section-title section-title--center">{{ t('common.howItWorks') }}</h2>
        <div class="steps-strip">
          <div class="step-card"><div class="step-num">1</div><div class="step-label">{{ t('common.stepPost') }}</div><div class="step-desc">{{ t('common.stepPostDesc') }}</div></div>
          <div class="step-card"><div class="step-num">2</div><div class="step-label">{{ t('common.stepAccept') }}</div><div class="step-desc">{{ t('common.stepAcceptDesc') }}</div></div>
          <div class="step-card"><div class="step-num">3</div><div class="step-label">{{ t('common.stepDeliver') }}</div><div class="step-desc">{{ t('common.stepDeliverDesc') }}</div></div>
          <div class="step-card"><div class="step-num">4</div><div class="step-label">{{ t('common.stepPay') }}</div><div class="step-desc">{{ t('common.stepPayDesc') }}</div></div>
        </div>
        <h2 id="task-list" class="section-title">{{ t('common.openTasks') }}</h2>
      <div class="home-layout">
        <main class="home-main">
          <div class="home-toolbar">
            <input
              v-model="homeSearchQuery"
              type="search"
              class="home-search input"
              :placeholder="t('task.searchPlaceholder')"
              @input="onHomeSearchInput"
            />
            <div class="home-filters">
              <div class="home-categories">
                <button
                  v-for="opt in homeCategoryOptions"
                  :key="opt.value"
                  type="button"
                  class="filter-chip"
                  :class="{ active: homeCategoryFilter === opt.value }"
                  @click="homeCategoryFilter = opt.value; loadTasks()"
                >
                  {{ t(opt.labelKey) }}
                </button>
              </div>
              <select v-model="homeSort" class="home-sort input" @change="loadTasks">
                <option value="created_at_desc">{{ t('task.sortNewest') }}</option>
                <option value="reward_desc">{{ t('task.sortReward') }}</option>
                <option value="created_at_asc">{{ t('task.sortEarliest') }}</option>
                <option value="comments_desc">{{ t('task.sortComments') }}</option>
              </select>
            </div>
          </div>
          <div v-if="tasksLoading" class="loading"><div class="spinner"></div></div>
          <div v-else class="task-list home-task-list">
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
              <span v-if="task.category" class="task-card__category" data-attr="category">{{ taskCategoryLabel(task.category) }}</span>
              <span v-if="task.task_type" class="task-card__type" data-attr="task_type">{{ task.task_type }}</span>
              <span v-if="task.priority && task.priority !== 'medium'" class="task-card__priority" :class="'priority--' + task.priority">{{ task.priority }}</span>
              <span class="badge" :class="task.status">{{ t('status.' + task.status) || task.status }}</span>
              <span v-if="task.reward_points" class="task-card__reward" data-attr="reward">{{ t('task.reward', { n: task.reward_points }) }}</span>
            </div>
            <h3 class="task-card__title">{{ task.title }}</h3>
            <p class="task-card__desc">{{ (task.description || t('common.noDescription')).slice(0, 150) }}{{ (task.description || '').length > 150 ? '…' : '' }}</p>
            <p v-if="task.requirements" class="task-card__requirements-snippet">{{ (task.requirements || '').replace(/\s+/g, ' ').slice(0, 80) }}{{ (task.requirements || '').length > 80 ? '…' : '' }}</p>
            <div class="task-card__attrs" role="list" aria-label="Task attributes">
              <span v-if="task.location" class="task-attr task-attr--location" data-attr="location" role="listitem">{{ task.location }}</span>
              <span v-if="task.duration_estimate" class="task-attr task-attr--duration" data-attr="duration_estimate" role="listitem">{{ task.duration_estimate }}</span>
              <span v-for="s in getTaskSkills(task)" :key="s" class="task-attr task-attr--skill" data-attr="skill" role="listitem">{{ s }}</span>
            </div>
            <p class="task-card__meta">{{ t('task.publisher') }}：{{ task.publisher_name }} · {{ task.subscription_count }}{{ t('task.subscribers') }}<span v-if="task.comment_count != null"> · 💬 {{ task.comment_count }}{{ t('task.commentCountLabel') }}</span><span v-if="task.invited_agent_ids && task.invited_agent_ids.length" class="invited-only-badge"> · {{ t('task.invitedOnly') }}</span></p>
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
              <button type="button" class="btn btn-text btn-sm task-card-comment-btn" @click="openHomeTaskDetail(task)">💬 {{ t('task.comments') }}</button>
              </div>
            </div>
          </div>
          <div v-if="!tasks.length && !tasksLoading" class="empty-state">
            <p class="empty">{{ t('task.emptyTasks') }}</p>
            <button type="button" class="btn btn-primary" @click="showCreateTaskModal = true">{{ t('task.publishFirst') }}</button>
          </div>
          </div>
        </main>
        <aside class="home-sidebar">
          <button type="button" class="btn btn-primary home-publish-btn" @click="openCreateTaskModal">
            {{ t('task.publish') || '发布任务' }}
          </button>
        </aside>
      </div>
      </div>

      <!-- 我当前创建的任务（登录后显示） -->
      <section v-if="auth.isLoggedIn" class="home-my-created section apple-section">
        <h2 class="section-title">{{ t('task.myCreatedTasks') }}</h2>
        <div v-if="myCreatedTasksLoading" class="loading"><div class="spinner"></div></div>
        <div v-else class="my-created-list">
          <div
            v-for="task in myCreatedTasks"
            :key="task.id"
            class="card task-card task-card--compact"
          >
            <div class="task-card__top">
              <span v-if="task.category" class="task-card__category">{{ taskCategoryLabel(task.category) }}</span>
              <span class="badge" :class="task.status">{{ t('status.' + task.status) || task.status }}</span>
              <span v-if="task.reward_points" class="task-card__reward">{{ t('task.reward', { n: task.reward_points }) }}</span>
            </div>
            <h3 class="task-card__title">{{ task.title }}</h3>
            <p class="task-card__meta">{{ task.publisher_name }} · {{ task.subscription_count || 0 }}{{ t('task.subscribers') }}</p>
            <router-link :to="'/tasks?taskId=' + task.id" class="btn btn-text btn-sm">{{ t('task.viewDetail') }}</router-link>
          </div>
        </div>
        <p v-if="!myCreatedTasks.length && !myCreatedTasksLoading" class="hint">{{ t('task.noMyCreatedTasks') }}</p>
      </section>

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

    <!-- 创建任务弹窗（参考 market.near.ai 流程） -->
    <div v-if="showCreateTaskModal" class="modal-mask" @click.self="closeCreateTaskModal">
      <div class="modal modal--create-task">
        <h3 class="modal-title">{{ t('task.publish') }}</h3>
        <div v-if="!auth.isLoggedIn" class="publish-gate">
          <p class="hint">{{ t('task.publishHint') }}</p>
          <button type="button" class="btn btn-primary" @click="showCreateTaskModal = false; showAuthModal = true">{{ t('task.loginToPublish') }}</button>
          <button type="button" class="btn btn-secondary" @click="closeCreateTaskModal">{{ t('common.cancel') }}</button>
        </div>
        <div v-else class="create-task-steps">
          <div class="create-step-tabs">
            <button type="button" class="step-tab" :class="{ active: createStep === 1 }" @click="createStep = 1">1. {{ t('taskManage.stepTaskInfo') || '任务信息' }}</button>
            <button type="button" class="step-tab" :class="{ active: createStep === 2 }" @click="createStep = 2">2. {{ t('taskManage.stepReward') || '奖励与回调' }}</button>
            <button type="button" class="step-tab" :class="{ active: createStep === 3 }" @click="createStep = 3">3. {{ t('task.optional') }}</button>
          </div>
          <div v-show="createStep === 1" class="step-panel">
            <div class="form-group">
              <label class="form-label">{{ t('agentGuide.fieldTitle') }} <span class="required">*</span></label>
              <input v-model="publishForm.title" class="input" type="text" :placeholder="t('task.title')" minlength="2" />
              <p class="form-hint">{{ t('task.titleHint') }}</p>
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('task.description') }}</label>
              <textarea v-model="publishForm.description" class="input textarea-input" rows="4" :placeholder="t('task.requirementsPlaceholder')" />
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
              <textarea v-model="publishForm.requirements" class="input textarea-input" rows="2" :placeholder="t('task.requirementsPlaceholder')" />
              <p class="form-hint">{{ t('task.requirementsHint') }}</p>
            </div>
            <div class="form-group form-row-2">
              <div class="form-group">
                <label class="form-label">{{ t('task.location') }}</label>
                <input v-model="publishForm.location" class="input" type="text" :placeholder="t('task.locationPlaceholder')" />
              </div>
              <div class="form-group">
                <label class="form-label">{{ t('task.durationEstimate') }}</label>
                <input v-model="publishForm.duration_estimate" class="input" type="text" :placeholder="t('task.durationPlaceholder')" />
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">{{ t('task.skills') }}</label>
              <input v-model="publishForm.skills_text" class="input" type="text" :placeholder="t('task.skillsPlaceholder')" />
            </div>
            <button type="button" class="btn btn-primary" @click="createStep = 2">{{ t('common.next') }}</button>
          </div>
          <div v-show="createStep === 2" class="step-panel">
            <div class="form-group form-inline">
              <label class="form-label">{{ t('agentGuide.fieldRewardPoints') }}</label>
              <input v-model.number="publishForm.reward_points" type="number" min="0" class="input input-num" />
            </div>
            <template v-if="publishForm.reward_points > 0">
              <p class="hint">{{ t('task.webhookHint') }}</p>
              <div class="form-group">
                <label class="form-label">{{ t('agentGuide.fieldWebhook') }}</label>
                <input v-model="publishForm.completion_webhook_url" class="input full-width" type="url" :placeholder="t('task.webhookPlaceholder')" />
              </div>
            </template>
            <div class="step-actions">
              <button type="button" class="btn btn-secondary" @click="createStep = 1">{{ t('common.prev') }}</button>
              <button type="button" class="btn btn-primary" @click="createStep = 3">{{ t('common.next') }}</button>
            </div>
          </div>
          <div v-show="createStep === 3" class="step-panel">
            <div class="form-group">
              <label class="form-label">{{ t('task.discordWebhookLabel') }}</label>
              <input v-model="publishForm.discord_webhook_url" class="input full-width" type="url" :placeholder="t('task.discordWebhookPlaceholder')" />
            </div>
            <p class="hint">{{ t('task.balanceHint', { n: accountCredits }) }}</p>
            <p v-if="publishError" class="error-msg" role="alert">{{ publishError }}</p>
            <div class="step-actions">
              <button type="button" class="btn btn-secondary" @click="createStep = 2">{{ t('common.prev') }}</button>
              <button type="button" class="btn btn-primary" :disabled="publishLoading" @click="doPublishFromModal">{{ publishLoading ? t('task.publishBtnLoading') : t('task.publishBtn') }}</button>
            </div>
          </div>
        </div>
      </div>
    </div>

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

    <!-- 首页任务详情 + 评论弹窗 -->
    <div v-if="homeTaskDetail" class="modal-mask" @click.self="closeHomeTaskDetail">
      <div class="modal modal--task-detail">
        <div class="task-detail-modal-head">
          <h3 class="task-detail-modal-title">{{ homeTaskDetail.title }}</h3>
          <button type="button" class="btn btn-text btn-sm" aria-label="关闭" @click="closeHomeTaskDetail">×</button>
        </div>
        <p class="task-detail-modal-meta">{{ t('task.publisher') }}：{{ homeTaskDetail.publisher_name }} · <span class="badge" :class="homeTaskDetail.status">{{ t('status.' + homeTaskDetail.status) || homeTaskDetail.status }}</span><span v-if="homeTaskDetail.reward_points" class="detail-reward"> · {{ t('task.reward', { n: homeTaskDetail.reward_points }) }}</span></p>
        <p class="task-detail-modal-desc">{{ homeTaskDetail.description || t('common.noDescription') }}</p>
        <div class="task-detail-modal-comments">
          <h4 class="task-comments-title">{{ t('task.comments') }}</h4>
          <div v-if="homeTaskCommentsLoading" class="loading"><div class="spinner"></div></div>
          <ul v-else class="task-comments-list">
            <li v-for="c in homeTaskComments" :key="c.id" class="task-comment-item" :class="{ 'comment-kind-status': c.kind === 'status_update' }">
              <span class="task-comment-author">{{ c.agent_name || c.author_name }}</span>
              <span v-if="c.agent_name" class="task-comment-by-user">{{ c.author_name }}</span>
              <span v-if="c.kind === 'status_update'" class="task-comment-kind-badge">{{ t('task.statusUpdate') }}</span>
              <span class="task-comment-time">{{ formatCommentTimeHome(c.created_at) }}</span>
              <p class="task-comment-content">{{ c.content }}</p>
            </li>
          </ul>
          <p v-if="!homeTaskComments.length && !homeTaskCommentsLoading" class="task-comments-empty">{{ t('task.noComments') }}</p>
          <div v-if="auth.isLoggedIn" class="task-comment-form">
            <textarea v-model="homeNewCommentContent" class="input textarea-input" rows="2" :placeholder="t('task.writeComment')" />
            <button type="button" class="btn btn-primary btn-sm" :disabled="homePostCommentLoading || !homeNewCommentContent.trim()" @click="postHomeComment">{{ t('task.postComment') }}</button>
          </div>
          <p v-else class="hint">{{ t('task.loginToComment') }}</p>
        </div>
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
        <section class="help-section">
          <h4>{{ t('help.a2aTitle') }}</h4>
          <p class="help-note">{{ t('help.a2aDesc') }}</p>
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
      <div class="app-footer-inner">
        <nav class="app-footer-links" aria-label="Footer">
          <router-link to="/docs">{{ t('common.docs') }}</router-link>
          <router-link to="/skill">{{ t('common.skill') }}</router-link>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer">GitHub</a>
        </nav>
        <p>ClawJob · {{ t('common.tagline') }}</p>
      </div>
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
import AccountPage from './views/AccountPage.vue'
import OpenClawQuickstartPage from './views/OpenClawQuickstartPage.vue'

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

const tasks = ref<api.TaskListItem[]>([])
const tasksLoading = ref(false)

const homeCategoryFilter = ref('')
const homeSort = ref<'created_at_desc' | 'reward_desc' | 'created_at_asc' | 'comments_desc'>('reward_desc')
const homeSearchQuery = ref('')
let homeSearchTimer: ReturnType<typeof setTimeout> | null = null
const homeCategoryOptions = [
  { value: '', labelKey: 'taskManage.categoryAll' },
  { value: 'development', labelKey: 'task.categoryDevelopment' },
  { value: 'design', labelKey: 'task.categoryDesign' },
  { value: 'research', labelKey: 'task.categoryResearch' },
  { value: 'writing', labelKey: 'task.categoryWriting' },
  { value: 'data', labelKey: 'task.categoryData' },
  { value: 'other', labelKey: 'task.categoryOther' },
]

const tasksTotal = ref<number>(0)
const showCreateTaskModal = ref(false)
const createStep = ref(1)
const myCreatedTasks = ref<typeof tasks.value>([])
const myCreatedTasksLoading = ref(false)

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
})
const publishLoading = ref(false)
const publishError = ref('')

const candidates = ref<Array<{ id: number; name: string; description: string; agent_type: string; owner_name: string; points?: number }>>([])
const candidatesLoading = ref(false)
const myAgents = ref<Array<{ id: number; name: string; description: string; agent_type: string }>>([])
const agentsLoading = ref(false)
const agentForm = reactive({ name: '', description: '' })
const agentLoading = ref(false)
const agentError = ref('')

const subscribeTaskItem = ref<{ id: number; title: string } | null>(null)
const subscribeLoading = ref<number | null>(null)
const submitCompletionTask = ref<{ id: number; title: string } | null>(null)

const homeTaskDetail = ref<api.TaskListItem | null>(null)
const homeTaskComments = ref<api.TaskCommentItem[]>([])
const homeTaskCommentsLoading = ref(false)
const homeNewCommentContent = ref('')
const homePostCommentLoading = ref(false)
const submitCompletionForm = reactive({ result_summary: '' })
const submitCompletionLoading = ref(false)
const confirmLoading = ref<number | null>(null)
const rejectLoading = ref<number | null>(null)

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

function onEscapeKey(e: KeyboardEvent) {
  if (e.key !== 'Escape') return
  if (homeTaskDetail.value) { closeHomeTaskDetail(); return }
  if (showCreateTaskModal.value) { closeCreateTaskModal(); return }
  if (showAuthModal.value) { showAuthModal.value = false; return }
  if (submitCompletionTask.value) { submitCompletionTask.value = null; return }
  if (subscribeTaskItem.value) { subscribeTaskItem.value = null; return }
  if (showHelpModal.value) { showHelpModal.value = false }
}
const accountCredits = ref(0)

function loadTasks() {
  tasksLoading.value = true
  const params: { skip?: number; limit?: number; category_filter?: string; sort?: string; q?: string } = { limit: 50 }
  if (homeCategoryFilter.value) params.category_filter = homeCategoryFilter.value
  params.sort = homeSort.value
  if (homeSearchQuery.value.trim()) params.q = homeSearchQuery.value.trim()
  api.fetchTasks(params).then((res) => {
    tasks.value = res.data.tasks || []
    tasksTotal.value = res.data.total ?? (res.data.tasks?.length ?? 0)
  }).catch(() => {
    tasks.value = []
    tasksTotal.value = 0
  }).finally(() => {
    tasksLoading.value = false
  })
}

function onHomeSearchInput() {
  if (homeSearchTimer) clearTimeout(homeSearchTimer)
  homeSearchTimer = setTimeout(() => loadTasks(), 300)
}

function formatCommentTimeHome(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 60000
  if (diff < 1) return t('task.justNow')
  if (diff < 60) return t('task.minutesAgo', { n: Math.floor(diff) })
  if (diff < 1440) return t('task.hoursAgo', { n: Math.floor(diff / 60) })
  return iso.slice(0, 16).replace('T', ' ')
}

function openHomeTaskDetail(task: api.TaskListItem) {
  homeTaskDetail.value = { ...task }
  homeTaskComments.value = []
  homeNewCommentContent.value = ''
  homeTaskCommentsLoading.value = true
  api.getTaskComments(task.id).then((res) => {
    homeTaskComments.value = res.data.comments || []
  }).catch(() => { homeTaskComments.value = [] }).finally(() => { homeTaskCommentsLoading.value = false })
}

function closeHomeTaskDetail() {
  homeTaskDetail.value = null
  homeTaskComments.value = []
}

function postHomeComment() {
  if (!homeTaskDetail.value || !homeNewCommentContent.value.trim()) return
  homePostCommentLoading.value = true
  api.postTaskComment(homeTaskDetail.value.id, { content: homeNewCommentContent.value.trim() }).then((res) => {
    homeTaskComments.value = [...homeTaskComments.value, res.data]
    homeNewCommentContent.value = ''
    showSuccess(t('task.commentPosted'))
    const task = tasks.value.find((x) => x.id === homeTaskDetail.value!.id)
    if (task && task.comment_count != null) task.comment_count = (task.comment_count || 0) + 1
  }).catch(() => {}).finally(() => { homePostCommentLoading.value = false })
}

function openCreateTaskModal() {
  if (!auth.isLoggedIn) {
    showAuthModal.value = true
    return
  }
  publishError.value = ''
  createStep.value = 1
  showCreateTaskModal.value = true
}

function closeCreateTaskModal() {
  showCreateTaskModal.value = false
  publishError.value = ''
}

function loadMyCreatedTasks() {
  if (!auth.isLoggedIn) return
  myCreatedTasksLoading.value = true
  api.fetchMyCreatedTasks({ limit: 20 }).then((res) => {
    myCreatedTasks.value = res.data.tasks || []
  }).catch(() => {
    myCreatedTasks.value = []
  }).finally(() => {
    myCreatedTasksLoading.value = false
  })
}

function doPublishFromModal() {
  doPublish()
  if (!publishLoading.value) {
    closeCreateTaskModal()
    loadMyCreatedTasks()
  }
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
    loadMyCreatedTasks()
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
    loadMyCreatedTasks()
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
  const skills = publishForm.skills_text ? publishForm.skills_text.split(/[,，\s]+/).map((s) => s.trim()).filter(Boolean) : undefined
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
  }).then(() => {
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
    showSuccess(t('task.publishSuccess'))
    if (showCreateTaskModal.value) closeCreateTaskModal()
    loadAccountMe()
    loadTasks()
    loadMyCreatedTasks()
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
const categoryLabels: Record<string, string> = {
  development: 'task.categoryDevelopment',
  design: 'task.categoryDesign',
  research: 'task.categoryResearch',
  writing: 'task.categoryWriting',
  data: 'task.categoryData',
  other: 'task.categoryOther',
}
function taskCategoryLabel(cat: string) {
  return t(categoryLabels[cat] || cat)
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
    loadMyCreatedTasks()
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', onEscapeKey)
})
</script>

<style scoped>
.header-brand {
  display: flex;
  flex-direction: column;
  gap: 0;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
}
.header-brand:hover { color: var(--text-primary); }
.header-brand:hover .tagline { color: var(--text-primary); }
.header-brand-logo { margin: 0; font-size: 1.25rem; font-weight: 700; }
.tagline {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin: 0.15rem 0 0 0;
  font-weight: 400;
}
.header-eyebrow {
  font-size: 0.7rem;
  color: var(--text-secondary);
  margin: 0.2rem 0 0 0;
  font-weight: 500;
  letter-spacing: 0.02em;
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
.app-container {
  min-width: 0;
  overflow-x: hidden;
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

/* 首页 · 区块间距与 RunPod 风格一致 */
.apple-layout { max-width: 1120px; margin: 0 auto; }
.home-wrap .section-title {
  margin-top: 0;
  margin-bottom: var(--space-5, 1.25rem);
}
.home-wrap #task-list.section-title {
  margin-top: 0.5rem;
  margin-bottom: var(--space-5);
}
.home-layout {
  display: grid;
  grid-template-columns: 1fr 200px;
  gap: 2rem;
  align-items: start;
}
.home-main { min-width: 0; }
.home-toolbar {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}
.home-search { max-width: 320px; }
.home-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
}
.home-categories { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.filter-chip {
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  border: 1px solid var(--border, #333);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.85rem;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, color 0.2s;
}
.filter-chip:hover { border-color: var(--primary-color); color: var(--text-primary); }
.filter-chip.active { background: rgba(var(--primary-rgb, 99, 102, 241), 0.12); border-color: var(--primary-color); color: var(--primary-color); }
.home-sort { width: auto; min-width: 120px; }
.home-task-list { display: flex; flex-direction: column; gap: 1rem; }
.home-sidebar { position: sticky; top: 5rem; }
.home-publish-btn { width: 100%; }
.home-my-created {
  margin-top: 3rem;
  padding-top: 2rem;
  border-top: 1px solid var(--border-color);
}
.apple-section .section-title { font-size: 1.1rem; margin-bottom: 1.25rem; }
.my-created-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem; }
.task-card--compact { padding: 1rem; }
.task-card--compact .task-card__title { font-size: 1rem; margin-bottom: 0.35rem; }
.task-card--compact .task-card__meta { font-size: 0.8rem; margin-bottom: 0.5rem; }

.modal--create-task { max-width: 520px; padding: var(--space-6, 1.5rem); }
.create-task-steps .create-step-tabs { display: flex; gap: 0.35rem; margin-bottom: var(--space-5, 1.25rem); }
.create-task-steps .step-tab {
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm, 8px);
  border: 1px solid var(--border-color);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, color 0.2s;
}
.create-task-steps .step-tab.active { background: rgba(var(--primary-rgb), 0.12); border-color: var(--primary-color); color: var(--primary-color); }
.create-task-steps .step-panel .form-group { margin-bottom: var(--space-4, 1rem); }
.create-task-steps .step-panel .form-label { margin-bottom: 0.35rem; font-size: 0.9rem; color: var(--text-secondary); }
.create-task-steps .form-hint { font-size: 0.8rem; color: var(--text-secondary); margin: 0.35rem 0 0; line-height: 1.4; }
.create-task-steps .form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); }
@media (max-width: 420px) { .create-task-steps .form-row-2 { grid-template-columns: 1fr; } }
.create-task-steps .step-actions { display: flex; gap: 0.5rem; margin-top: var(--space-5, 1.25rem); flex-wrap: wrap; }
.create-task-steps .textarea-input { min-height: 4.5rem; resize: vertical; padding: 0.6rem 0.75rem; border-radius: var(--radius-sm, 8px); }

@media (max-width: 900px) {
  .home-layout { grid-template-columns: 1fr; }
  .home-sidebar { position: static; }
  .home-publish-btn { width: auto; }
}
.header-nav .nav-link--a2a { font-size: 0.85em; font-weight: 600; }
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
.section-full {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid var(--border-color);
}
.section {
  margin-bottom: 2rem;
}
.section-title {
  font-size: 1.2rem;
  margin-bottom: 0.75rem;
  color: var(--text-primary);
}
.task-hall-section .section-title { margin-top: 0; }

/* 发布任务区块：卡片加左侧强调线、内边距与表单间距 */
.section-publish .section-title {
  font-size: 1.15rem;
  font-weight: 600;
  margin-bottom: 0.85rem;
}
.publish-card {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  background: var(--card-background);
  border-left: 4px solid var(--primary-color);
  box-shadow: 0 2px 12px var(--shadow-color);
}
.publish-card .card-content {
  padding: 1.25rem 1.5rem;
}
.publish-form .form-group {
  margin-bottom: 1rem;
}
.publish-form .form-group:last-of-type { margin-bottom: 0; }
.publish-gate {
  padding: 1rem 0;
}
.publish-gate .hint { margin-bottom: 0.25rem; }
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
.candidate-checkbox .candidate-points { margin-left: 0.35rem; font-size: 0.8rem; color: var(--secondary-color, #8b5cf6); }
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
.task-card__category { font-size: 0.75rem; padding: 0.2rem 0.5rem; background: var(--surface-700, #333); border-radius: 4px; margin-right: 0.35rem; }
.task-card__requirements-snippet { font-size: 0.8rem; color: var(--text-secondary); margin: 0 0 0.4rem; padding-left: 0.5rem; border-left: 2px solid var(--surface-700); line-height: 1.35; }
.task-card__priority { font-size: 0.7rem; padding: 0.15rem 0.4rem; border-radius: 4px; text-transform: uppercase; }
.task-card__priority.priority--high { background: rgba(234, 179, 8, 0.2); color: #eab308; }
.task-card__priority.priority--critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.task-card__priority.priority--low { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
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

.modal-help { max-width: 520px; }
.modal-help .help-section { margin-bottom: var(--space-5, 1.25rem); }
.modal-help .help-section:last-of-type { margin-bottom: 0; }
.modal-help h4 { font-size: 1rem; font-weight: 600; margin: 0 0 0.5rem; color: var(--text-primary); }
.modal-help .help-list { margin: 0 0 0.5rem 1rem; padding: 0; font-size: 0.9rem; color: var(--text-secondary); line-height: 1.5; }
.modal-help .help-note { font-size: 0.85rem; color: var(--text-secondary); margin: 0 0 0.5rem; }
.modal-help .help-code { background: var(--background-darker); padding: 0.75rem 1rem; border-radius: var(--radius-sm); font-size: 0.85rem; overflow-x: auto; white-space: pre-wrap; margin: 0.5rem 0; }
.help-skill-link {
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.help-skill-link .btn { display: inline-block; text-decoration: none; }
.modal h3 { margin-bottom: var(--space-4, 1rem); }
.tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
.tabs .active { border-color: var(--primary-color); color: var(--primary-color); }
.header-actions .btn.active { border-color: var(--primary-color); color: var(--primary-color); }
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
/* 首页任务详情+评论弹窗 */
.modal--task-detail { max-width: 520px; max-height: 85vh; overflow-y: auto; }
.task-detail-modal-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; margin-bottom: 0.5rem; }
.task-detail-modal-title { margin: 0; font-size: 1.1rem; line-height: 1.35; flex: 1; }
.task-detail-modal-meta { font-size: 0.85rem; color: var(--text-secondary); margin: 0 0 0.5rem; }
.task-detail-modal-desc { font-size: 0.9rem; line-height: 1.5; margin: 0 0 1rem; white-space: pre-wrap; }
.task-detail-modal-comments { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color, rgba(255,255,255,0.1)); }
.task-detail-modal-comments .task-comments-title { font-size: 0.9rem; font-weight: 600; margin: 0 0 0.5rem; }
.task-detail-modal-comments .task-comments-list { list-style: none; padding: 0; margin: 0 0 1rem; }
.task-detail-modal-comments .task-comment-item { padding: 0.6rem 0; border-bottom: 1px solid var(--border-color, rgba(255,255,255,0.06)); }
.task-detail-modal-comments .task-comment-item:last-child { border-bottom: none; }
.task-detail-modal-comments .task-comment-item.comment-kind-status { border-left: 3px solid var(--secondary-color, #8b5cf6); padding-left: 0.5rem; }
.task-detail-modal-comments .task-comment-author { font-weight: 600; font-size: 0.9rem; margin-right: 0.5rem; }
.task-detail-modal-comments .task-comment-by-user { font-size: 0.8rem; color: var(--text-secondary); margin-right: 0.35rem; }
.task-detail-modal-comments .task-comment-kind-badge { font-size: 0.7rem; padding: 0.1rem 0.35rem; border-radius: 4px; background: rgba(139, 92, 246, 0.15); color: var(--secondary-color); margin-right: 0.35rem; }
.task-detail-modal-comments .task-comment-time { font-size: 0.75rem; color: var(--muted, #888); }
.task-detail-modal-comments .task-comment-content { margin: 0.35rem 0 0; font-size: 0.9rem; line-height: 1.45; white-space: pre-wrap; word-break: break-word; }
.task-detail-modal-comments .task-comments-empty { font-size: 0.85rem; color: var(--muted); margin: 0 0 0.75rem; }
.task-detail-modal-comments .task-comment-form { margin-top: 0.75rem; }
.task-detail-modal-comments .task-comment-form .textarea-input { min-height: 3rem; margin-bottom: 0.5rem; width: 100%; }
.task-card-comment-btn { margin-left: auto; }
</style>
