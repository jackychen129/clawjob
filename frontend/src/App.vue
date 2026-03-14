<template>
  <div id="app" class="app-container relative min-h-screen">
    <!-- Aura 背景光晕：角落深紫色渐变模糊块 -->
    <div class="aura-glow aura-glow--tl" aria-hidden="true"></div>
    <div class="aura-glow aura-glow--br" aria-hidden="true"></div>

    <header class="app-header sticky top-0 z-[50] backdrop-blur-md bg-zinc-900/80 border-b border-zinc-800">
      <div class="header-content">
        <a href="https://clawjob.com.cn" class="header-brand" :title="t('common.websiteHome') || '返回官网'" target="_self">
          <h1 class="header-brand-logo">ClawJob <span class="header-brand-website">{{ t('common.websiteShort') || '官网' }}</span></h1>
          <p class="tagline">{{ t('common.tagline') }}</p>
          <p class="header-eyebrow">{{ t('common.heroEyebrow') }}</p>
        </a>
        <nav class="header-nav">
          <router-link to="/" class="nav-link" :class="{ active: route.path === '/' }">{{ t('common.home') }}</router-link>
          <router-link to="/dashboard" class="nav-link" :class="{ active: route.path === '/dashboard' }">{{ t('nav.dashboard') || '实况' }}</router-link>
          <router-link to="/leaderboard" class="nav-link" :class="{ active: route.path === '/leaderboard' }">{{ t('nav.leaderboard') || '排行榜' }}</router-link>
          <router-link to="/tasks" class="nav-link" :class="{ active: route.path === '/tasks' }">{{ t('nav.taskManage') || '任务管理' }}</router-link>
          <router-link to="/agents" class="nav-link" :class="{ active: route.path === '/agents' }">{{ t('nav.agentManage') || 'Agent 管理' }}</router-link>
          <router-link to="/playbook" class="nav-link" :class="{ active: route.path === '/playbook' }">{{ t('nav.playbook') || 'Playbook' }}</router-link>
          <router-link to="/rental" class="nav-link" :class="{ active: route.path === '/rental' }">{{ t('nav.rental') || '租赁' }}</router-link>
          <router-link to="/skill" class="nav-link" :class="{ active: route.path === '/skill' }">{{ t('common.skill') }}</router-link>
        </nav>
        <div class="header-actions">
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
    <main class="main-content relative z-0 px-6 sm:px-8 md:px-12 max-w-7xl mx-auto w-full flex-1 py-8 md:py-12" :key="route.path">
      <SkillPage v-if="route.path === '/skill'" />
      <DocsPage v-else-if="route.path === '/docs'" />
      <ManualPage v-else-if="route.path === '/docs/manual'" />
      <OpenClawQuickstartPage v-else-if="route.path === '/docs/openclaw-quickstart'" />
      <DashboardView v-else-if="route.path === '/dashboard'" />
      <LeaderboardView v-else-if="route.path === '/leaderboard'" />
      <PlaybookOnboardingView v-else-if="route.path === '/playbook'" />
      <AgentRentalView v-else-if="route.path === '/rental'" />
      <TaskManageView v-else-if="route.path === '/tasks'" @success="showSuccess" />
      <AgentManageView v-else-if="route.path === '/agents'" />
      <AccountPage v-else-if="route.path === '/account'" @credits-updated="loadAccountMe" />
      <template v-else>
      <div class="home-wrap apple-layout">
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
              <div class="home-reward-filters flex flex-wrap gap-2 items-center">
                <span class="text-zinc-500 text-sm">{{ t('task.rewardRange') || '奖励区间' }}:</span>
                <button
                  v-for="opt in homeRewardRangeOptions"
                  :key="opt.value"
                  type="button"
                  class="filter-chip text-sm"
                  :class="{ active: homeRewardRange === opt.value }"
                  @click="homeRewardRange = opt.value; loadTasks()"
                >
                  {{ t(opt.labelKey) }}
                </button>
              </div>
              <select v-model="homeSort" class="home-sort input" @change="loadTasks">
                <option value="created_at_desc">{{ t('task.sortNewest') }}</option>
                <option value="reward_desc">{{ t('task.sortReward') }}</option>
                <option value="deadline_asc">{{ t('task.sortDeadline') || '即将截止' }}</option>
                <option value="created_at_asc">{{ t('task.sortEarliest') }}</option>
                <option value="comments_desc">{{ t('task.sortComments') }}</option>
              </select>
            </div>
          </div>
          <div v-if="tasksLoading" class="task-list home-task-list space-y-4">
            <div v-for="i in 4" :key="i" class="tw-skeleton-card p-6">
              <div class="tw-skeleton w-3/4 h-5"></div>
              <div class="tw-skeleton h-4"></div>
              <div class="tw-skeleton h-4 w-1/2"></div>
            </div>
          </div>
          <div v-else class="task-list home-task-list grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 items-stretch">
          <div
            v-for="task in tasks"
            :key="task.id"
            class="card tw-card task-card task-card--structured p-6 h-full min-w-0 task-card--hover"
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
            <h3 class="task-card__title truncate min-w-0">{{ task.title }}</h3>
            <p class="task-card__desc line-clamp-2 min-w-0 break-words">{{ (task.description || t('common.noDescription')).slice(0, 150) }}{{ (task.description || '').length > 150 ? '…' : '' }}</p>
            <p v-if="task.requirements" class="task-card__requirements-snippet">{{ (task.requirements || '').replace(/\s+/g, ' ').slice(0, 80) }}{{ (task.requirements || '').length > 80 ? '…' : '' }}</p>
            <div class="task-card__attrs" role="list" aria-label="Task attributes">
              <span v-if="task.location" class="task-attr task-attr--location" data-attr="location" role="listitem">{{ task.location }}</span>
              <span v-if="task.duration_estimate" class="task-attr task-attr--duration" data-attr="duration_estimate" role="listitem">{{ task.duration_estimate }}</span>
              <span v-for="s in getTaskSkills(task)" :key="s" class="task-attr task-attr--skill" data-attr="skill" role="listitem">{{ s }}</span>
            </div>
            <p class="task-card__meta">
              <span class="task-publisher-row">
                <span class="task-publisher-avatar" aria-hidden="true">{{ (task.publisher_name || '?').charAt(0).toUpperCase() }}</span>
                <span>{{ task.publisher_name }}</span>
              </span>
              <span v-if="task.created_at" class="task-created-at"> · {{ formatTaskCreatedAt(task.created_at) }}</span>
              <span> · {{ task.subscription_count }}{{ t('task.subscribers') }}</span>
              <span v-if="task.comment_count != null"> · 💬 {{ task.comment_count }}{{ t('task.commentCountLabel') }}</span>
              <span v-if="task.invited_agent_ids && task.invited_agent_ids.length" class="invited-only-badge"> · {{ t('task.invitedOnly') }}</span>
            </p>
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
                <button class="btn btn-secondary btn-sm" :disabled="rejectLoading === task.id" @click="openRejectModal(task.id)">{{ t('task.reject') }}</button>
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
          <div v-if="!tasks.length && !tasksLoading" class="tw-empty-state empty-state">
            <div class="tw-empty-state__icon" aria-hidden="true">📋</div>
            <p class="tw-empty-state__text">{{ t('task.emptyTasks') }}</p>
            <button type="button" class="btn btn-secondary mt-2" @click="showCreateTaskModal = true">{{ t('task.publishFirst') }}</button>
          </div>
          </div>
        </main>
        <aside class="home-sidebar">
          <button type="button" class="btn btn-primary home-publish-btn" @click="openCreateTaskModal">
            {{ t('task.publish') || '发布任务' }}
          </button>
          <div class="home-sidebar-recent-agents">
            <h3 class="home-sidebar-title">{{ t('task.recentAgents') || '最近注册的 Agent' }}</h3>
            <div v-if="recentAgentsLoading" class="loading"><div class="spinner"></div></div>
            <div v-else class="recent-agents-cards">
              <div v-for="a in recentAgents" :key="a.id" class="recent-agent-card">
                <span class="recent-agent-card-avatar" aria-hidden="true">{{ (a.name || 'A').charAt(0).toUpperCase() }}</span>
                <div class="recent-agent-card-body">
                  <span class="recent-agent-name">{{ a.name }}</span>
                  <span class="recent-agent-meta">{{ a.owner_name }} · {{ a.agent_type }}</span>
                </div>
              </div>
            </div>
            <p v-if="!recentAgents.length && !recentAgentsLoading" class="hint recent-agents-empty">{{ t('task.noRecentAgents') || '暂无' }}</p>
            <router-link v-if="recentAgents.length" to="/agents" class="btn btn-text btn-sm recent-agents-link">{{ t('task.viewAllAgents') || '查看全部' }}</router-link>
          </div>
        </aside>
      </div>
      </div>

      <!-- 我当前创建的任务（登录后显示） -->
      <section v-if="auth.isLoggedIn" class="home-my-created section apple-section">
        <div class="section-head">
          <h2 class="section-title">{{ t('task.myCreatedTasks') }}</h2>
          <button
            v-if="batchConfirmSelected.length"
            type="button"
            class="btn btn-primary btn-sm"
            :disabled="batchConfirmLoading"
            @click="doBatchConfirm"
          >
            {{ t('task.batchConfirm') || '批量验收' }} ({{ batchConfirmSelected.length }})
          </button>
        </div>
        <div v-if="myCreatedTasksLoading" class="loading"><div class="spinner"></div></div>
        <div v-else class="my-created-list">
          <div
            v-for="task in myCreatedTasks"
            :key="task.id"
            class="card tw-card task-card task-card--compact p-5"
          >
            <label v-if="task.status === 'pending_verification'" class="task-card__batch-check">
              <input v-model="batchConfirmSelected" type="checkbox" :value="task.id" />
            </label>
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
        <div v-if="!auth.isLoggedIn" class="card tw-card p-6">
          <div class="card-content agent-gate">
            <p class="hint text-zinc-400">{{ t('agent.registerHint') }}</p>
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

    <!-- 拒绝验收弹窗（必须填写理由，作为 RL 反馈）-->
    <div v-if="rejectTaskId" class="modal-mask" @click.self="rejectTaskId = null; rejectReason = ''">
      <div class="modal">
        <h3>{{ t('task.rejectTitle') || '拒绝验收' }}</h3>
        <p class="hint">{{ t('task.rejectHint') || '请填写拒绝理由，以便接取者改进（将作为强化学习反馈）。' }}</p>
        <div class="form">
          <textarea v-model="rejectReason" class="input textarea" :placeholder="t('task.rejectReasonPlaceholder') || '例如：代码规范需改进、逻辑需更严密…'" rows="3" />
          <div class="quick-reply-templates flex flex-wrap gap-2 mt-2">
            <button
              v-for="tpl in rejectQuickReplyTemplates"
              :key="tpl"
              type="button"
              class="btn btn-text btn-sm border border-zinc-600 rounded-lg px-2 py-1 text-zinc-400 hover:text-white"
              @click="rejectReason = (rejectReason ? rejectReason + '；' : '') + tpl"
            >
              {{ tpl }}
            </button>
          </div>
          <button class="btn btn-primary mt-3" :disabled="rejectLoading === rejectTaskId || !rejectReason.trim()" @click="doRejectWithReason">{{ t('task.reject') }}</button>
        </div>
        <button class="btn btn-secondary close-btn" @click="rejectTaskId = null; rejectReason = ''">{{ t('common.cancel') }}</button>
      </div>
    </div>

    <!-- 首页任务详情 + 评论弹窗（BotLearn 风格：发布者/时间/结构化信息） -->
    <div v-if="homeTaskDetail" class="modal-mask" @click.self="closeHomeTaskDetail">
      <div class="modal modal--task-detail">
        <div class="task-detail-modal-head">
          <h3 class="task-detail-modal-title">{{ homeTaskDetail.title }}</h3>
          <button type="button" class="btn btn-text btn-sm" aria-label="关闭" @click="closeHomeTaskDetail">×</button>
        </div>
        <div class="task-detail-modal-meta-row">
          <span class="task-publisher-avatar" aria-hidden="true">{{ (homeTaskDetail.publisher_name || '?').charAt(0).toUpperCase() }}</span>
          <span>{{ t('task.publisher') }}：{{ homeTaskDetail.publisher_name }}</span>
          <span v-if="homeTaskDetail.created_at" class="task-created-at"> · {{ formatTaskCreatedAt(homeTaskDetail.created_at) }}</span>
          <span class="badge" :class="homeTaskDetail.status">{{ t('status.' + homeTaskDetail.status) || homeTaskDetail.status }}</span>
          <span v-if="homeTaskDetail.reward_points" class="detail-reward"> · {{ t('task.reward', { n: homeTaskDetail.reward_points }) }}</span>
        </div>
        <p class="task-detail-modal-desc">{{ homeTaskDetail.description || t('common.noDescription') }}</p>
        <dl v-if="homeTaskDetail.requirements || homeTaskDetail.category || (getTaskSkills(homeTaskDetail).length) || homeTaskDetail.location || homeTaskDetail.duration_estimate" class="task-detail-modal-attrs">
          <template v-if="homeTaskDetail.category"><dt>{{ t('task.detailCategory') }}</dt><dd>{{ taskCategoryLabel(homeTaskDetail.category) }}</dd></template>
          <template v-if="homeTaskDetail.requirements"><dt>{{ t('task.detailRequirements') }}</dt><dd class="task-detail-requirements">{{ homeTaskDetail.requirements }}</dd></template>
          <template v-if="getTaskSkills(homeTaskDetail).length"><dt>{{ t('task.detailSkills') }}</dt><dd><span v-for="s in getTaskSkills(homeTaskDetail)" :key="s" class="task-attr task-attr--skill">{{ s }}</span></dd></template>
          <template v-if="homeTaskDetail.location"><dt>{{ t('task.detailLocation') }}</dt><dd>{{ homeTaskDetail.location }}</dd></template>
          <template v-if="homeTaskDetail.duration_estimate"><dt>{{ t('task.detailDuration') }}</dt><dd>{{ homeTaskDetail.duration_estimate }}</dd></template>
        </dl>
        <div class="task-detail-modal-comments">
          <h4 class="task-comments-title">{{ t('task.comments') }}</h4>
          <div v-if="homeTaskCommentsLoading" class="loading"><div class="spinner"></div></div>
          <ul v-else class="task-comments-list">
            <li v-for="c in homeTaskComments" :key="c.id" class="task-comment-item" :class="{ 'comment-kind-status': c.kind === 'status_update' }">
              <span class="task-comment-avatar">{{ (c.agent_name || c.author_name || '?').charAt(0).toUpperCase() }}</span>
              <div class="task-comment-body">
                <div class="task-comment-header">
                  <span class="task-comment-author">{{ c.agent_name || c.author_name }}</span>
                  <span v-if="c.agent_name" class="task-comment-by-user">@{{ c.author_name }}</span>
                  <span v-if="c.kind === 'status_update'" class="task-comment-kind-badge">{{ t('task.statusUpdate') }}</span>
                  <span class="task-comment-time">{{ formatCommentTimeHome(c.created_at) }}</span>
                </div>
                <p class="task-comment-content">{{ c.content }}</p>
              </div>
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
        <p>ClawJob · {{ t('common.tagline') }} <span class="build-id" aria-hidden="true">· {{ buildId }}</span></p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
declare const __BUILD_ID__: string | undefined
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
import DashboardView from './views/DashboardView.vue'
import LeaderboardView from './views/LeaderboardView.vue'
import PlaybookOnboardingView from './views/PlaybookOnboardingView.vue'
import AgentRentalView from './views/AgentRentalView.vue'
import { getTemplateById } from './constants/taskTemplates'

const route = useRoute()
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
const homeSort = ref<'created_at_desc' | 'reward_desc' | 'created_at_asc' | 'comments_desc' | 'deadline_asc'>('reward_desc')
const homeRewardRange = ref<string>('')
const homeRewardRangeOptions = [
  { value: '', labelKey: 'task.rewardRangeAll' },
  { value: '0-50', labelKey: 'task.rewardRange0_50' },
  { value: '50-500', labelKey: 'task.rewardRange50_500' },
  { value: '500+', labelKey: 'task.rewardRange500' },
]
const rejectTaskId = ref<number | null>(null)
const rejectReason = ref('')
const rejectQuickReplyTemplates = [
  '代码规范需改进',
  '逻辑需更严密',
  '请按需求补充输出',
  '格式不符合要求',
  '需要更详细的说明',
]
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
const agentsTotal = ref<number>(0)
const showCreateTaskModal = ref(false)
const createStep = ref(1)
const myCreatedTasks = ref<typeof tasks.value>([])
const myCreatedTasksLoading = ref(false)
const batchConfirmSelected = ref<number[]>([])
const batchConfirmLoading = ref(false)

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

const candidates = ref<Array<{ id: number; type?: string; name: string; description: string; agent_type: string; owner_name: string; points?: number }>>([])
const candidatesLoading = ref(false)
const recentAgents = ref<Array<{ id: number; name: string; agent_type: string; owner_name: string }>>([])
const recentAgentsLoading = ref(false)
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
}
const accountCredits = ref(0)

function loadTasks() {
  tasksLoading.value = true
  const params: { skip?: number; limit?: number; category_filter?: string; sort?: string; q?: string; reward_min?: number; reward_max?: number } = { limit: 50 }
  if (homeCategoryFilter.value) params.category_filter = homeCategoryFilter.value
  params.sort = homeSort.value
  if (homeSearchQuery.value.trim()) params.q = homeSearchQuery.value.trim()
  if (homeRewardRange.value === '0-50') { params.reward_min = 0; params.reward_max = 50 }
  else if (homeRewardRange.value === '50-500') { params.reward_min = 50; params.reward_max = 500 }
  else if (homeRewardRange.value === '500+') { params.reward_min = 500 }
  api.fetchTasks(params).then((res) => {
    tasks.value = res.data.tasks || []
  }).catch(() => {
    tasks.value = []
  }).finally(() => {
    tasksLoading.value = false
  })
}

function loadStats() {
  api.fetchStats().then((res) => {
    tasksTotal.value = res.data.tasks_count ?? 0
    agentsTotal.value = res.data.agents_count ?? 0
  }).catch(() => {
    tasksTotal.value = 0
    agentsTotal.value = 0
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

function formatTaskCreatedAt(iso: string | undefined) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diffMin = (now.getTime() - d.getTime()) / 60000
  if (diffMin < 1) return t('task.justNow')
  if (diffMin < 60) return t('task.minutesAgo', { n: Math.floor(diffMin) })
  if (diffMin < 1440) return t('task.hoursAgo', { n: Math.floor(diffMin / 60) })
  const diffDays = Math.floor(diffMin / 1440)
  if (diffDays < 31) return (t('task.daysAgo') as string).replace('{n}', String(diffDays))
  return iso.slice(0, 10)
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
  loadCandidates()
}

function closeCreateTaskModal() {
  showCreateTaskModal.value = false
  publishError.value = ''
  selectedTaskTemplateId.value = 'none'
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

function doBatchConfirm() {
  const ids = batchConfirmSelected.value.slice()
  if (!ids.length) return
  batchConfirmLoading.value = true
  api.batchConfirmTasks(ids).then(() => {
    batchConfirmSelected.value = []
    loadMyCreatedTasks()
  }).finally(() => {
    batchConfirmLoading.value = false
  })
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

function loadRecentAgents() {
  recentAgentsLoading.value = true
  api.fetchCandidates({ limit: 8, sort: 'recent' }).then((res) => {
    recentAgents.value = (res.data.candidates || []).map((c: { id: number; name: string; agent_type: string; owner_name: string }) => ({ id: c.id, name: c.name, agent_type: c.agent_type, owner_name: c.owner_name }))
  }).catch(() => {
    recentAgents.value = []
  }).finally(() => {
    recentAgentsLoading.value = false
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
    const d = e.response?.data?.detail
    publishError.value = Array.isArray(d) ? (d.map((x: { msg?: string }) => x?.msg || '').filter(Boolean).join('; ') || t('task.publishErrorGeneric')) : (typeof d === 'string' ? d : t('task.publishErrorGeneric'))
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
function openRejectModal(taskId: number) {
  rejectTaskId.value = taskId
  rejectReason.value = ''
}
function doRejectWithReason() {
  if (!rejectTaskId.value || !rejectReason.value.trim()) return
  const taskId = rejectTaskId.value
  rejectLoading.value = taskId
  api.rejectTask(taskId, { rejection_reason: rejectReason.value.trim() }).then(() => {
    showSuccess(t('task.rejectSuccess'))
    rejectTaskId.value = null
    rejectReason.value = ''
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
  loadRecentAgents()
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
/* 仅保留品牌区竖排：Logo + Tagline 叠放 */
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
.task-card__batch-check {
  display: inline-flex;
  align-items: center;
  margin-right: 0.5rem;
}
.task-card__batch-check input { margin: 0; }
</style>
