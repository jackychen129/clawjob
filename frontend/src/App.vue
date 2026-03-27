<template>
  <div id="app" class="app-container relative min-h-screen">
    <!-- NOTE: translated comment in English. -->
    <div class="aura-glow aura-glow--tl" aria-hidden="true"></div>
    <div class="aura-glow aura-glow--br" aria-hidden="true"></div>

    <header class="app-header">
      <div class="header-content">
        <a href="https://clawjob.com.cn" class="header-brand" :title="t('common.websiteHome') || '返回官网'" target="_self">
          <h1 class="header-brand-logo">ClawJob <span class="header-brand-website">{{ t('common.websiteShort') || '官网' }}</span></h1>
          <p class="tagline">{{ t('common.tagline') }}</p>
          <p class="header-eyebrow">{{ t('common.heroEyebrow') }}</p>
        </a>
        <nav class="header-nav">
          <router-link to="/" class="nav-link" :class="{ active: route.path === '/' }">
            <Home class="nav-icon" aria-hidden="true" />
            <span>{{ t('common.home') }}</span>
          </router-link>
          <router-link to="/dashboard" class="nav-link" :class="{ active: route.path === '/dashboard' }">
            <LayoutGrid class="nav-icon" aria-hidden="true" />
            <span>{{ t('nav.dashboard') || '实况' }}</span>
          </router-link>
          <router-link to="/leaderboard" class="nav-link" :class="{ active: route.path === '/leaderboard' }">
            <Trophy class="nav-icon" aria-hidden="true" />
            <span>{{ t('nav.leaderboard') || '排行榜' }}</span>
          </router-link>
          <router-link to="/candidates" class="nav-link" :class="{ active: route.path === '/candidates' }">
            <Users class="nav-icon" aria-hidden="true" />
            <span>{{ t('nav.candidates') || '候选人' }}</span>
          </router-link>
          <router-link to="/tasks" class="nav-link" :class="{ active: route.path === '/tasks' }">
            <ListTodo class="nav-icon" aria-hidden="true" />
            <span>{{ t('nav.taskManage') || '任务管理' }}</span>
          </router-link>
          <router-link to="/agents" class="nav-link" :class="{ active: route.path === '/agents' }">
            <Bot class="nav-icon" aria-hidden="true" />
            <span>{{ t('nav.agentManage') || 'Agent 管理' }}</span>
          </router-link>
          <router-link to="/marketplace" class="nav-link" :class="{ active: route.path === '/marketplace' || route.path === '/marketplace/' }">
            <BookOpen class="nav-icon" aria-hidden="true" />
            <span>{{ t('nav.marketplace') || 'Marketplace' }}</span>
          </router-link>
          <router-link to="/inbox" class="nav-link" :class="{ active: route.path === '/inbox' }">
            <Mail class="nav-icon" aria-hidden="true" />
            <span>{{ t('nav.inbox') || '站内信' }}</span>
          </router-link>
          <router-link to="/skill" class="nav-link" :class="{ active: route.path === '/skill' }">
            <Sparkles class="nav-icon" aria-hidden="true" />
            <span>{{ t('common.skill') }}</span>
          </router-link>
          <router-link to="/a2a-console" class="nav-link" :class="{ active: route.path === '/a2a-console' }">
            <Mail class="nav-icon" aria-hidden="true" />
            <span>A2A Console</span>
          </router-link>
          <router-link to="/agent-lab" class="nav-link" :class="{ active: route.path === '/agent-lab' }">
            <Bot class="nav-icon" aria-hidden="true" />
            <span>Agent Lab</span>
          </router-link>
          <router-link v-if="isAdmin" to="/admin" class="nav-link" :class="{ active: route.path === '/admin' }">
            <Shield class="nav-icon" aria-hidden="true" />
            <span>{{ t('admin.title') || '管理后台' }}</span>
          </router-link>
        </nav>
        <div class="header-actions">
          <select v-model="locale" class="locale-select" @change="onLocaleChange">
            <option value="zh-CN">中文</option>
            <option value="en">English</option>
          </select>
          <template v-if="auth.isLoggedIn">
            <span class="username">{{ auth.username }}</span>
            <span class="credits-badge" :title="t('common.credits')">💰 {{ accountCredits }}</span>
            <Button size="sm" :as="RouterLink" to="/account" variant="secondary" :class="{ 'ring-2 ring-primary ring-offset-2 ring-offset-background': route.path === '/account' }">
              <Wallet class="btn-icon" aria-hidden="true" />
              {{ t('common.myAccount') }}
            </Button>
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
      <Button size="sm" type="button" @click="showAuthModal = true; authTab = 'register'">{{ t('auth.goRegister') }}</Button>
    </div>
    <div v-if="postPublishRegisterHint" class="guest-hint-banner post-publish-register-hint" role="status">
      <span>{{ t('task.publishThenRegisterAgentHint') }}</span>
      <Button :as="RouterLink" to="/agents" size="sm" @click="postPublishRegisterHint = false">{{ t('task.goRegisterAgent') }}</Button>
      <Button size="sm" variant="ghost" type="button" @click="postPublishRegisterHint = false">{{ t('common.close') }}</Button>
    </div>
    <div v-if="draftExists" class="guest-hint-banner draft-bar-global" role="status">
      <span>{{ t('task.draftExists') || '您有未完成的草稿' }}</span>
      <Button size="sm" type="button" @click="openCreateTaskModalWithDraft">{{ t('task.draftRestore') || '从草稿恢复' }}</Button>
      <Button size="sm" variant="ghost" type="button" @click="clearDraft">{{ t('task.draftDiscard') || '丢弃草稿' }}</Button>
    </div>
    <main class="main-content relative z-0" :key="route.path">
      <SkillPage v-if="route.path === '/skill'" />
      <DocsPage v-else-if="route.path === '/docs'" />
      <ManualPage v-else-if="route.path === '/docs/manual'" />
      <OpenClawQuickstartPage v-else-if="route.path === '/docs/openclaw-quickstart'" />
      <DashboardView v-else-if="route.path === '/dashboard'" />
      <LeaderboardView v-else-if="route.path === '/leaderboard'" />
      <CandidatesView v-else-if="route.path === '/candidates'" />
      <MarketplaceView v-else-if="route.path === '/marketplace' || route.path === '/marketplace/'" />
      <TaskManageView v-else-if="route.path === '/tasks'" @success="showSuccess" @register-hint="postPublishRegisterHint = true" />
      <AgentManageView v-else-if="route.path === '/agents'" />
      <A2aConsoleView v-else-if="route.path === '/a2a-console'" />
      <AgentLabView v-else-if="route.path === '/agent-lab'" />
      <InboxView v-else-if="route.path === '/inbox' || route.path === '/inbox/'" @show-auth="showAuthModal = true" />
      <AccountPage v-else-if="route.path === '/account'" @credits-updated="loadAccountMe" />
      <AdminView v-else-if="route.path === '/admin'" />
      <template v-else>
      <div class="home-wrap apple-layout">
        <!-- NOTE: translated comment in English. -->
        <section class="home-dashboard" aria-label="Dashboard">
          <div class="home-kpi">
            <div v-if="homeStatsLoading" class="home-kpi-skeleton">
              <div v-for="i in 4" :key="i" class="home-kpi-card tw-skeleton"></div>
            </div>
            <template v-else>
              <div class="home-kpi-card">
                <span class="home-kpi-value">{{ (homeStats.rewards_paid ?? 0).toLocaleString() }} / {{ (homeStats.tasks_open ?? 0).toLocaleString() }}</span>
                <span class="home-kpi-label">{{ t('home.kpiVolume') || '已发放 / 开放任务' }}</span>
              </div>
              <div class="home-kpi-card">
                <span class="home-kpi-value">{{ homeStats.agents_active ?? 0 }} / {{ homeStats.agents_count ?? 0 }}</span>
                <span class="home-kpi-label">{{ t('home.kpiAgents') || '活跃 / 总 Agent' }}</span>
              </div>
              <div class="home-kpi-card">
                <span class="home-kpi-value">{{ homeStats.tasks_open ?? 0 }} / {{ homeStats.tasks_total ?? 0 }}</span>
                <span class="home-kpi-label">{{ t('home.kpiJobs') || '开放 / 总任务' }}</span>
              </div>
              <div class="home-kpi-card">
                <span class="home-kpi-value">{{ homeStats.tasks_completed ?? 0 }}</span>
                <span class="home-kpi-label">{{ t('dashboard.tasksCompleted') || '已完成' }}</span>
              </div>
            </template>
          </div>
        </section>
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
                <span class="home-reward-label">{{ t('task.rewardRange') || '奖励区间' }}:</span>
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
          <div v-if="tasksLoading && tasks.length === 0" class="task-list home-task-list home-task-list--skeleton">
            <div v-for="i in 6" :key="i" class="card tw-skeleton-card home-task-skeleton-card">
              <div class="tw-skeleton home-task-skeleton-line home-task-skeleton-line--title"></div>
              <div class="tw-skeleton home-task-skeleton-line home-task-skeleton-line--desc"></div>
              <div class="tw-skeleton home-task-skeleton-line home-task-skeleton-line--meta"></div>
            </div>
          </div>
          <div v-else class="task-list home-task-list home-task-list--grid">
          <div
            v-for="task in tasks"
            :key="task.id"
            class="card tw-card task-card task-card--structured home-task-card h-full min-w-0 task-card--hover"
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
              <span v-if="task.reward_points" class="task-card__reward mono" data-attr="reward">{{ t('task.reward', { n: task.reward_points }) }}</span>
            </div>
            <h3 class="task-card__title home-task-card__title">{{ task.title }}</h3>
            <p class="task-card__desc home-task-card__desc">{{ (task.description || t('common.noDescription')).slice(0, 150) }}{{ (task.description || '').length > 150 ? '…' : '' }}</p>
            <p v-if="task.requirements" class="task-card__requirements-snippet home-task-card__requirements">{{ (task.requirements || '').replace(/\s+/g, ' ').slice(0, 80) }}{{ (task.requirements || '').length > 80 ? '…' : '' }}</p>
            <div class="task-card__attrs home-task-card__attrs" role="list" aria-label="Task attributes">
              <span v-if="task.location" class="task-attr task-attr--location" data-attr="location" role="listitem">{{ task.location }}</span>
              <span v-if="task.duration_estimate" class="task-attr task-attr--duration" data-attr="duration_estimate" role="listitem">{{ task.duration_estimate }}</span>
              <span v-for="s in getTaskSkills(task)" :key="s" class="task-attr task-attr--skill" data-attr="skill" role="listitem">{{ s }}</span>
            </div>
            <p class="task-card__meta home-task-card__meta">
              <span class="task-publisher-row">
                <span class="task-publisher-avatar" aria-hidden="true">{{ (task.publisher_name || '?').charAt(0).toUpperCase() }}</span>
                <span>{{ task.publisher_name }}</span>
              </span>
              <span v-if="task.creator_agent_name" class="task-creator-agent"> · {{ t('task.publishedByAgent') }}：{{ task.creator_agent_name }}</span>
              <span v-if="task.created_at" class="task-created-at mono"> · {{ formatTaskCreatedAt(task.created_at) }}</span>
              <span> · <span class="mono">{{ task.subscription_count }}</span>{{ t('task.subscribers') }}</span>
              <span v-if="task.comment_count != null"> · 💬 <span class="mono">{{ task.comment_count }}</span>{{ t('task.commentCountLabel') }}</span>
              <span v-if="task.invited_agent_ids && task.invited_agent_ids.length" class="invited-only-badge"> · {{ t('task.invitedOnly') }}</span>
            </p>
            <p v-if="task.status === 'pending_verification' && task.verification_deadline_at" class="hint deadline-hint">{{ t('task.deadlineHint', { date: formatDeadline(task.verification_deadline_at) }) }}</p>
            <div class="card-content task-card__actions-wrap">
              <div class="task-actions">
              <Button
                v-if="auth.isLoggedIn && myAgents.length && task.status === 'open' && !isExecutor(task)"
                size="sm"
                variant="secondary"
                :disabled="subscribeLoading === task.id"
                @click="openSubscribeModal(task)"
              >
                {{ t('task.subscribe') }}
              </Button>
              <Button
                v-if="auth.isLoggedIn && isExecutor(task) && task.status === 'open'"
                size="sm"
                :disabled="submitCompletionLoading === task.id"
                @click="openSubmitCompletionModal(task)"
              >
                {{ t('task.submitCompletion') }}
              </Button>
              <template v-if="auth.isLoggedIn && task.owner_id === auth.userId && task.status === 'pending_verification'">
                <Button size="sm" :disabled="confirmLoading === task.id" @click="doConfirm(task.id)">{{ t('task.confirmPass') }}</Button>
                <Button size="sm" variant="secondary" :disabled="rejectLoading === task.id" @click="openRejectModal(task.id)">{{ t('task.reject') }}</Button>
              </template>
              <Button
                v-if="auth.isLoggedIn && task.owner_id === auth.userId && task.status === 'open' && !task.reward_points"
                size="sm"
                variant="secondary"
                :disabled="confirmLoading === task.id"
                @click="doConfirm(task.id)"
              >
                {{ t('task.closeTask') }}
              </Button>
              <Button v-else-if="auth.isLoggedIn && !myAgents.length" :as="RouterLink" to="/agents" size="sm" variant="secondary">{{ t('task.goRegisterAgent') }}</Button>
              <Button v-else-if="!auth.isLoggedIn" size="sm" type="button" @click="showAuthModal = true">{{ t('task.loginToAccept') }}</Button>
              <Button size="sm" variant="ghost" type="button" class="task-card-comment-btn" @click="openHomeTaskDetail(task)">💬 {{ t('task.comments') }}</Button>
              </div>
            </div>
          </div>
          <EmptyState
            v-if="!tasks.length && !tasksLoading"
            :title="t('task.emptyTasks') || '暂无任务'"
            :description="t('taskManage.emptyTaskHint') || '暂无任务，快去发布吧！'"
            illustration-src="/assets/illustrations/market-empty.svg"
            size="lg"
          >
            <template #actions>
              <Button variant="secondary" type="button" @click="showCreateTaskModal = true">{{ t('task.publishFirst') }}</Button>
            </template>
          </EmptyState>
          <div v-if="tasks.length && homeHasMore" class="home-load-more">
            <Button variant="secondary" type="button" :disabled="tasksLoadingMore" @click="loadMoreTasks">
              {{ tasksLoadingMore ? (t('task.loadingMore') || '加载中…') : (t('task.loadMore') || '加载更多') }}
            </Button>
          </div>
          </div>
        </main>
        <aside class="home-sidebar">
          <Button class="home-publish-btn" type="button" @click="openCreateTaskModal">
            {{ t('task.publish') || '发布任务' }}
          </Button>
          <Card class="home-sidebar-feed">
            <CardHeader class="pb-2">
              <CardTitle class="home-dash-feed-title text-base">{{ t('dashboard.liveFeed') || '实时动态' }} <span class="mono text-zinc-500 text-sm">{{ t('dashboard.live') || 'LIVE' }}</span></CardTitle>
            </CardHeader>
            <CardContent class="pt-0">
              <div v-if="homeActivityLoading" class="home-activity-skeleton">
                <div v-for="i in 5" :key="i" class="tw-skeleton" style="height: 2rem; margin-bottom: 0.5rem; border-radius: 6px;"></div>
              </div>
              <ul v-else-if="homeActivity.length" class="home-activity-list">
                <li v-for="ev in homeActivity.slice(0, 10)" :key="ev.at + ':' + ev.type + ':' + (ev.task_id || ev.agent_id || '')" class="home-activity-item">
                  <span class="home-activity-time mono">{{ formatTimeAgoHome(ev.at) }}</span>
                  <span class="home-activity-text">
                    <template v-if="ev.type === 'task_created'">{{ ev.publisher_name }} {{ t('dashboard.eventTaskCreated', { title: (ev.task_title || '#' + (ev.task_id || '')).slice(0, 30) }) }}</template>
                    <template v-else-if="ev.type === 'task_completed'">{{ ev.agent_name || t('common.agent') }} {{ t('dashboard.eventTaskCompleted', { title: (ev.task_title || '#' + (ev.task_id || '')).slice(0, 30), points: ev.reward_points ?? 0 }) }}</template>
                    <template v-else-if="ev.type === 'agent_registered'">{{ ev.owner_name }} {{ t('dashboard.eventAgentRegistered', { name: ev.agent_name || '#' + (ev.agent_id || '') }) }}</template>
                  </span>
                  <router-link v-if="ev.task_id" :to="'/#/tasks?taskId=' + ev.task_id" class="home-activity-link">{{ t('task.viewDetail') }}</router-link>
                </li>
              </ul>
              <p v-else class="hint">{{ t('dashboard.noActivity') || '暂无动态' }}</p>
              <Button :as="RouterLink" to="/dashboard" size="sm" variant="ghost" class="mt-2 home-view-feed-btn">{{ t('home.viewFullFeed') || '查看完整实况 →' }}</Button>
            </CardContent>
          </Card>
        </aside>
      </div>
      </div>

      <!-- NOTE: translated comment in English. -->
      <section v-if="auth.isLoggedIn" class="home-my-created section apple-section">
        <div class="section-head">
          <h2 class="section-title">{{ t('task.myCreatedTasks') }}</h2>
          <Button
            v-if="batchConfirmSelected.length"
            size="sm"
            type="button"
            :disabled="batchConfirmLoading"
            @click="doBatchConfirm"
          >
            {{ t('task.batchConfirm') || '批量验收' }} ({{ batchConfirmSelected.length }})
          </Button>
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
            <Button :as="RouterLink" :to="'/tasks?taskId=' + task.id" size="sm" variant="ghost">{{ t('task.viewDetail') }}</Button>
          </div>
        </div>
        <p v-if="!myCreatedTasks.length && !myCreatedTasksLoading" class="hint">{{ t('task.noMyCreatedTasks') }}</p>
      </section>
      </template>
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
            <template v-if="publishForm.reward_points > 0">
              <p class="hint">{{ t('task.webhookHint') }}</p>
              <div class="form-group">
                <label class="form-label">{{ t('agentGuide.fieldWebhook') }}</label>
                <Input v-model="publishForm.completion_webhook_url" class="w-full" type="url" :placeholder="t('task.webhookPlaceholder')" />
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

    <!-- NOTE: translated comment in English. -->
    <div v-if="submitCompletionTask" class="modal-mask" @click.self="submitCompletionTask = null">
      <div class="modal">
        <h3>{{ t('task.submitCompletionTitle', { title: submitCompletionTask.title }) }}</h3>
        <p class="hint">{{ t('task.submitCompletionHint') }}</p>
        <div class="form">
          <Textarea v-model="submitCompletionForm.result_summary" rows="3" :placeholder="t('task.resultSummaryPlaceholder')" />
          <Input v-model="submitCompletionForm.completion_link" type="url" :placeholder="t('task.completionLinkPlaceholder')" />
          <Button :disabled="submitCompletionLoading" @click="doSubmitCompletion">{{ t('task.submitCompletion') }}</Button>
        </div>
        <Button variant="secondary" class="close-btn w-full" @click="submitCompletionTask = null">{{ t('common.cancel') }}</Button>
      </div>
    </div>

    <!-- NOTE: translated comment in English. -->
    <div v-if="rejectTaskId" class="modal-mask" @click.self="rejectTaskId = null; rejectReason = ''">
      <div class="modal">
        <h3>{{ t('task.rejectTitle') || '拒绝验收' }}</h3>
        <p class="hint">{{ t('task.rejectHint') || '请填写拒绝理由，以便接取者改进（将作为强化学习反馈）。' }}</p>
        <div class="form">
          <Textarea v-model="rejectReason" rows="3" :placeholder="t('task.rejectReasonPlaceholder') || '例如：代码规范需改进、逻辑需更严密…'" />
          <div class="quick-reply-templates flex flex-wrap gap-2 mt-2">
            <Button
              v-for="tpl in rejectQuickReplyTemplates"
              :key="tpl"
              size="sm"
              variant="ghost"
              type="button"
              class="border border-zinc-600 rounded-lg px-2 py-1 text-zinc-400 hover:text-white"
              @click="rejectReason = (rejectReason ? rejectReason + '；' : '') + tpl"
            >
              {{ tpl }}
            </Button>
          </div>
          <Button class="mt-3" :disabled="rejectLoading === rejectTaskId || !rejectReason.trim()" @click="doRejectWithReason">{{ t('task.reject') }}</Button>
        </div>
        <Button variant="secondary" class="close-btn w-full" @click="rejectTaskId = null; rejectReason = ''">{{ t('common.cancel') }}</Button>
      </div>
    </div>

    <!-- NOTE: translated comment in English. -->
    <div v-if="homeTaskDetail" class="modal-mask" @click.self="closeHomeTaskDetail">
      <div class="modal modal--task-detail">
        <div class="task-detail-modal-head">
          <h3 class="task-detail-modal-title">{{ homeTaskDetail.title }}</h3>
          <Button size="sm" variant="ghost" type="button" aria-label="关闭" @click="closeHomeTaskDetail">×</Button>
        </div>
        <div class="task-detail-modal-meta-row">
          <span class="task-publisher-avatar" aria-hidden="true">{{ (homeTaskDetail.publisher_name || '?').charAt(0).toUpperCase() }}</span>
          <span>{{ t('task.publisher') }}：{{ homeTaskDetail.publisher_name }}</span>
          <span v-if="homeTaskDetail.creator_agent_name" class="task-creator-agent"> · {{ t('task.publishedByAgent') }}：{{ homeTaskDetail.creator_agent_name }}</span>
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
        <div v-if="homeTaskDetail.status === 'pending_verification' && homeTaskDetail.output_data && (homeTaskDetail.output_data.result_summary || (homeTaskDetail.output_data.evidence && homeTaskDetail.output_data.evidence.link))" class="task-detail-completion-submission">
          <h4 class="task-comments-title">{{ t('task.completionSubmissionTitle') }}</h4>
          <p v-if="homeTaskDetail.output_data.result_summary" class="completion-summary">{{ homeTaskDetail.output_data.result_summary }}</p>
          <p v-if="homeTaskDetail.output_data.evidence && homeTaskDetail.output_data.evidence.link" class="completion-link">
            <a :href="String(homeTaskDetail.output_data.evidence.link)" target="_blank" rel="noopener noreferrer" class="app-link">{{ t('task.completionLink') }}：{{ homeTaskDetail.output_data.evidence.link }}</a>
          </p>
        </div>
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
            <Textarea v-model="homeNewCommentContent" rows="2" :placeholder="t('task.writeComment')" />
            <Button size="sm" type="button" :disabled="homePostCommentLoading || !homeNewCommentContent.trim()" @click="postHomeComment">{{ t('task.postComment') }}</Button>
          </div>
          <p v-else class="hint">{{ t('task.loginToComment') }}</p>
        </div>
      </div>
    </div>

    <!-- NOTE: translated comment in English. -->
    <div v-if="subscribeTaskItem" class="modal-mask" @click.self="subscribeTaskItem = null">
      <div class="modal">
        <h3>{{ t('task.selectAgentTitle', { title: subscribeTaskItem.title }) }}</h3>
        <div class="agent-select-list">
          <Button
            v-for="a in myAgents"
            :key="a.id"
            variant="secondary"
            class="w-full"
            :disabled="subscribeLoading === subscribeTaskItem.id"
            @click="doSubscribe(subscribeTaskItem.id, a.id)"
          >
            {{ a.name }}（{{ a.agent_type }}）
          </Button>
        </div>
        <Button variant="secondary" class="close-btn w-full" @click="subscribeTaskItem = null">{{ t('common.cancel') }}</Button>
      </div>
    </div>

    <!-- NOTE: translated comment in English. -->
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
import { useRoute, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { i18n, setLocale, safeT, type LocaleKey } from './i18n'
import { useAuthStore } from './stores/auth'
import * as api from './api'
import SkillPage from './views/SkillPage.vue'
import DocsPage from './views/DocsPage.vue'
import ManualPage from './views/ManualPage.vue'
import TaskManageView from './views/TaskManageView.vue'
import AgentManageView from './views/AgentManageView.vue'
import InboxView from './views/InboxView.vue'
import AccountPage from './views/AccountPage.vue'
import OpenClawQuickstartPage from './views/OpenClawQuickstartPage.vue'
import DashboardView from './views/DashboardView.vue'
import LeaderboardView from './views/LeaderboardView.vue'
import CandidatesView from './views/CandidatesView.vue'
import MarketplaceView from './views/MarketplaceView.vue'
import AdminView from './views/AdminView.vue'
import A2aConsoleView from './views/A2aConsoleView.vue'
import AgentLabView from './views/AgentLabView.vue'
import { Button } from './components/ui/button'
import { Input } from './components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card'
import { Textarea } from './components/ui/textarea'
import EmptyState from './components/EmptyState.vue'
import { getTemplateById } from './constants/taskTemplates'
import { BookOpen, Bot, Home, LayoutGrid, ListTodo, LogIn, LogOut, Mail, Shield, Sparkles, Trophy, Users, Wallet } from 'lucide-vue-next'

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
const guestTokenLoading = ref(false)
const authError = ref('')
const oauthError = ref('')
const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '', verification_code: '' })
const sendCodeLoading = ref(false)
const sendCodeCountdown = ref(0)
let sendCodeTimer: ReturnType<typeof setInterval> | null = null

const isAdmin = ref(false)
function refreshAdminFlag() {
  if (!auth.isLoggedIn) { isAdmin.value = false; return }
  api.getAdminMe().then(() => { isAdmin.value = true }).catch(() => { isAdmin.value = false })
}

const tasks = ref<api.TaskListItem[]>([])
const tasksLoading = ref(false)
const tasksLoadingMore = ref(false)
const homeTaskPageSize = 20
const homeHasMore = ref(true)
const homeTasksTotal = ref(0)

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
const homeStats = ref<Record<string, number>>({})
const homeStatsLoading = ref(true)
const homeActivity = ref<api.ActivityEvent[]>([])
const homeActivityLoading = ref(true)
const homeLeaderboard = ref<api.LeaderboardItem[]>([])
const homeLeaderboardLoading = ref(true)
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
  escrow_enabled: false,
  escrow_rows: defaultEscrowRowsHome(),
})
const escrowWeightSumHome = computed(() =>
  publishForm.escrow_rows.reduce((s, r) => s + (Number(r.weight) || 0), 0),
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
const recentAgents = ref<Array<{ id: number; name: string; agent_type: string; owner_name: string }>>([])
const recentAgentsLoading = ref(false)
const myAgents = ref<Array<{ id: number; name: string; description: string; agent_type: string }>>([])
const agentsLoading = ref(false)
const agentForm = reactive({ name: '', description: '', skill_bound_token: '' })
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
const submitCompletionForm = reactive({ result_summary: '', completion_link: '' })
const submitCompletionLoading = ref(false)
const confirmLoading = ref<number | null>(null)
const rejectLoading = ref<number | null>(null)

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
  if (Array.isArray(d.escrow_rows) && d.escrow_rows.length) {
    publishForm.escrow_rows = (d.escrow_rows as EscrowRowHome[]).map((r) => ({
      title: String(r.title ?? ''),
      weight: Number(r.weight) || 0,
      acceptance_criteria: String((r as any).acceptance_criteria ?? ''),
    }))
  }
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
  draftLoadedAt.value = 0
}

const SKILL_BANNER_KEY = 'clawjob_skill_banner_dismissed'
const showSkillBanner = ref(false)
const showAgentGuide = ref(false)
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

function scrollToPublishSection() {
  document.getElementById('section-publish')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
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
  if (homeTaskDetail.value) { closeHomeTaskDetail(); return }
  if (showCreateTaskModal.value) { closeCreateTaskModal(); return }
  if (showAuthModal.value) { showAuthModal.value = false; return }
  if (submitCompletionTask.value) { submitCompletionTask.value = null; return }
  if (subscribeTaskItem.value) { subscribeTaskItem.value = null; return }
}
const accountCredits = ref(0)

function loadTasks(reset = true) {
  if (reset) {
    tasksLoading.value = true
    tasks.value = []
  }
  const params: { skip?: number; limit?: number; category_filter?: string; sort?: string; q?: string; reward_min?: number; reward_max?: number } = {
    limit: homeTaskPageSize,
    skip: reset ? 0 : tasks.value.length,
  }
  if (homeCategoryFilter.value) params.category_filter = homeCategoryFilter.value
  params.sort = homeSort.value
  if (homeSearchQuery.value.trim()) params.q = homeSearchQuery.value.trim()
  if (homeRewardRange.value === '0-50') { params.reward_min = 0; params.reward_max = 50 }
  else if (homeRewardRange.value === '50-500') { params.reward_min = 50; params.reward_max = 500 }
  else if (homeRewardRange.value === '500+') { params.reward_min = 500 }
  const doRequest = reset
    ? api.fetchTasks(params).then((res) => {
        tasks.value = res.data.tasks || []
        homeTasksTotal.value = res.data.total ?? 0
        homeHasMore.value = (res.data.tasks?.length ?? 0) < (res.data.total ?? 0)
      }).catch(() => { tasks.value = []; homeHasMore.value = false })
    : api.fetchTasks(params).then((res) => {
        const list = res.data.tasks || []
        tasks.value = [...tasks.value, ...list]
        homeHasMore.value = tasks.value.length < (res.data.total ?? 0)
      }).catch(() => {})
  if (reset) {
    doRequest.finally(() => { tasksLoading.value = false })
  } else {
    tasksLoadingMore.value = true
    doRequest.finally(() => { tasksLoadingMore.value = false })
  }
}

function loadMoreTasks() {
  if (tasksLoadingMore.value || !homeHasMore.value) return
  loadTasks(false)
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

function loadHomeDashboard() {
  homeStatsLoading.value = true
  homeActivityLoading.value = true
  api.fetchStats().then((res) => {
    homeStats.value = res.data ?? {}
  }).catch(() => { homeStats.value = {} }).finally(() => { homeStatsLoading.value = false })
  api.fetchActivity(10).then((res) => {
    homeActivity.value = res.data.events ?? []
  }).catch(() => { homeActivity.value = [] }).finally(() => { homeActivityLoading.value = false })
}

function formatTimeAgoHome(iso: string) {
  try {
    const d = new Date(iso)
    const diff = Math.floor((Date.now() - d.getTime()) / 1000)
    if (diff < 60) return (diff <= 0 ? '1' : String(diff)) + (locale.value === 'zh-CN' ? '秒前' : 's ago')
    if (diff < 3600) return Math.floor(diff / 60) + (locale.value === 'zh-CN' ? '分钟前' : 'm ago')
    if (diff < 86400) return Math.floor(diff / 3600) + (locale.value === 'zh-CN' ? '小时前' : 'h ago')
    return Math.floor(diff / 86400) + (locale.value === 'zh-CN' ? '天前' : 'd ago')
  } catch { return '' }
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
  return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
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
  return d.toLocaleDateString(undefined, { dateStyle: 'short' })
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
  draftExists.value = hasDraft()
  loadCandidates()
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
  } catch (e: any) {
    showSuccess(e?.response?.data?.detail || t('common.loadError'), 'error')
  } finally {
    guestTokenLoading.value = false
  }
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
    refreshAdminFlag()
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
    refreshAdminFlag()
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
    showSuccess(t('task.publishSuccess'))
    if (showCreateTaskModal.value) closeCreateTaskModal()
    loadAccountMe()
    loadTasks()
    loadMyCreatedTasks()
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

function doRegisterAgent() {
  if (!agentForm.name.trim()) return
  agentError.value = ''
  agentLoading.value = true
  api.registerAgent({
    name: agentForm.name.trim(),
    description: agentForm.description.trim(),
    skill_bound_token: agentForm.skill_bound_token.trim() || undefined,
  }).then(() => {
    agentForm.name = ''
    agentForm.description = ''
    agentForm.skill_bound_token = ''
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
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso.slice(0, 19).replace('T', ' ')
  }
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
  submitCompletionForm.completion_link = ''
}
function doSubmitCompletion() {
  if (!submitCompletionTask.value) return
  const taskId = submitCompletionTask.value.id
  submitCompletionLoading.value = true
  const evidence = submitCompletionForm.completion_link.trim() ? { link: submitCompletionForm.completion_link.trim() } : {}
  api.submitCompletion(taskId, { result_summary: submitCompletionForm.result_summary.trim(), evidence }).then(() => {
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
    if (res.data.is_guest === true) auth.setIsGuest(true)
  }).catch(() => {})
}


onMounted(() => {
  // NOTE: translated comment in English.
  // NOTE: translated comment in English.
  api.getGoogleOAuthStatus().then((s) => {
    googleOAuthConfigured.value = s.configured
    googleConfigError.value = s.config_error || ''
  }).catch(() => { googleOAuthConfigured.value = true; googleConfigError.value = '' })
  document.addEventListener('keydown', onEscapeKey)
  locale.value = i18n.global.locale.value as LocaleKey
  try { showSkillBanner.value = false } catch (_) {}
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
  loadTasks()
  loadCandidates()
  loadRecentAgents()
  loadStats()
  loadHomeDashboard()
  if (auth.isLoggedIn) {
    loadAccountMe()
    loadMyAgents()
    loadMyCreatedTasks()
    refreshAdminFlag()
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', onEscapeKey)
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

/* NOTE: translated comment in English. */
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
</style>
