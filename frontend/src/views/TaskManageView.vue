<template>
  <div class="task-manage-view apple-layout">
    <h1 class="page-title">{{ t('nav.taskManage') }}</h1>
    <div class="task-layout task-layout--mine-only">
      <section class="task-center">
        <div class="task-center-inner" :class="{ 'task-center-inner--with-detail': !!selectedTaskDetail }">
          <div class="task-list-wrap">
          <div class="task-tabs">
            <button type="button" class="task-tab" :class="{ active: tab === 'available' }" @click="tab = 'available'">{{ t('taskManage.available') || '可接取任务' }}</button>
            <button type="button" class="task-tab" :class="{ active: tab === 'mine' }" @click="tab = 'mine'">{{ t('taskManage.myAccepted') || '我接取的任务' }}</button>
          </div>
          <!-- 可接取任务：未登录也允许浏览 -->
          <template v-if="tab === 'available'">
              <div class="task-filter-row">
                <select v-model="categoryFilter" class="input select-input task-filter-select">
                  <option value="">{{ t('taskManage.categoryAll') || '全部' }}</option>
                  <option v-for="opt in categoryFilterOptions" :key="opt.value" :value="opt.value">{{ t(opt.labelKey) }}</option>
                </select>
              </div>
              <div v-if="tasksLoading" class="task-list task-list--skeleton">
                <div v-for="i in 5" :key="i" class="task-row task-row--skeleton">
                  <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--short"></div>
                  <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--full"></div>
                  <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--mid"></div>
                </div>
              </div>
              <div v-else class="task-list task-list--virtual" v-bind="virtualAvailable.containerProps">
                <div v-bind="virtualAvailable.wrapperProps">
                  <article
                    v-for="item in virtualAvailableItems"
                    :key="item.index"
                    :class="cn('task-row', 'task-row--available', `task-row--${item.data!.status}`, { 'task-row--selected': selectedTaskDetail?.id === item.data!.id })"
                    role="button"
                    tabindex="0"
                    @click="openTaskDetail(item.data!)"
                    @keydown.enter.prevent="openTaskDetail(item.data!)"
                    @keydown.space.prevent="openTaskDetail(item.data!)"
                  >
                    <div class="task-row__head">
                      <span v-if="item.data!.category" class="task-row__category">{{ taskCategoryLabel(item.data!.category) }}</span>
                      <span :class="taskStatusPillClass(item.data!.status)">{{ t('status.' + item.data!.status) || item.data!.status }}</span>
                      <span v-if="item.data!.reward_points" class="task-row__reward mono">{{ t('task.reward', { n: item.data!.reward_points }) }}</span>
                    </div>
                    <h3 class="task-row__title">{{ item.data!.title }}</h3>
                    <p class="task-row__desc">{{ (item.data!.description || t('common.noDescription')).slice(0, 120) }}{{ (item.data!.description || '').length > 120 ? '…' : '' }}</p>
                    <p class="task-row__meta">{{ t('task.publisher') }}：{{ item.data!.publisher_name }}<span v-if="item.data!.creator_agent_name"> · {{ t('task.publishedByAgent') }}：{{ item.data!.creator_agent_name }}</span><span v-if="item.data!.subscription_count != null"> · {{ item.data!.subscription_count }}{{ t('task.subscribers') }}</span></p>
                    <div class="task-row__actions" @click.stop>
                      <Button size="sm" variant="ghost" type="button" class="task-row__btn" @click="openTaskDetail(item.data!)">{{ t('task.viewDetail') }}</Button>
                      <Button v-if="item.data!.status === 'open' && auth.isLoggedIn && myAgents.length" size="sm" :disabled="subscribeLoading === item.data!.id" class="task-row__btn task-row__btn--primary" @click="openSubscribeModal(item.data!)">{{ t('task.subscribe') }}</Button>
                      <Button v-else-if="item.data!.status === 'open' && !auth.isLoggedIn" size="sm" variant="secondary" type="button" class="task-row__btn" @click="showAuthModal = true">{{ t('task.loginToAccept') }}</Button>
                    </div>
                  </article>
                </div>
              </div>
              <EmptyState
                v-if="!filteredTasks.length && !tasksLoading"
                :title="categoryFilter ? (t('taskManage.noTasksInCategory') || '该分类下暂无任务') : (t('task.emptyTasks') || '暂无任务')"
                :description="t('taskManage.emptyTaskHint') || '切换分类或前往首页浏览更多任务'"
                illustration-src="/assets/illustrations/market-empty.svg"
              >
                <template #actions>
                  <Button :as="RouterLink" to="/" variant="secondary">{{ t('common.home') }}</Button>
                </template>
              </EmptyState>
          </template>

          <!-- 我接取的任务：未登录提示登录 -->
          <template v-else>
            <EmptyState
              v-if="!auth.isLoggedIn"
              :title="t('taskManage.loginToSeeMine') || '请先登录查看我接取的任务'"
              :description="t('taskManage.emptyTaskHint') || '登录后可接取任务并参与评论讨论'"
              illustration-src="/assets/illustrations/market-empty.svg"
              size="lg"
            >
              <template #actions>
                <Button type="button" @click="showAuthModal = true">{{ t('common.loginOrRegister') }}</Button>
              </template>
            </EmptyState>
            <template v-else>
            <div v-if="myTasksLoading" class="task-list task-list--skeleton">
              <div v-for="i in 4" :key="i" class="task-row task-row--skeleton">
                <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--short"></div>
                <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--full"></div>
                <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--mid"></div>
              </div>
            </div>
            <div v-else class="task-list task-list--virtual" v-bind="virtualMine.containerProps">
              <div v-bind="virtualMine.wrapperProps">
                <article
                  v-for="item in virtualMineItems"
                  :key="item.index"
                  :class="cn('task-row', 'task-row--mine', `task-row--${item.data!.status}`, { 'task-row--selected': selectedTaskDetail?.id === item.data!.id })"
                  role="button"
                  tabindex="0"
                  @click="openTaskDetail(item.data!)"
                  @keydown.enter.prevent="openTaskDetail(item.data!)"
                  @keydown.space.prevent="openTaskDetail(item.data!)"
                >
                  <div class="task-row__head">
                    <span v-if="item.data!.category" class="task-row__category">{{ taskCategoryLabel(item.data!.category) }}</span>
                    <span v-if="item.data!.task_type" class="task-row__type">{{ item.data!.task_type }}</span>
                    <span :class="taskStatusPillClass(item.data!.status)">{{ t('status.' + item.data!.status) || item.data!.status }}</span>
                    <span v-if="item.data!.reward_points" class="task-row__reward mono">{{ t('task.reward', { n: item.data!.reward_points }) }}</span>
                  </div>
                  <h3 class="task-row__title">{{ item.data!.title }}</h3>
                  <p class="task-row__desc">{{ (item.data!.description || t('common.noDescription')).slice(0, 120) }}{{ (item.data!.description || '').length > 120 ? '…' : '' }}</p>
                  <div v-if="item.data!.location || item.data!.duration_estimate || (getTaskSkills(item.data!).length)" class="task-row__tags">
                    <span v-if="item.data!.location" class="task-tag task-tag--location">{{ item.data!.location }}</span>
                    <span v-if="item.data!.duration_estimate" class="task-tag task-tag--duration">{{ item.data!.duration_estimate }}</span>
                    <span v-for="s in getTaskSkills(item.data!)" :key="s" class="task-tag task-tag--skill">{{ s }}</span>
                  </div>
                  <p class="task-row__meta">{{ t('task.publisher') }}：{{ item.data!.publisher_name }}<span v-if="item.data!.creator_agent_name"> · {{ t('task.publishedByAgent') }}：{{ item.data!.creator_agent_name }}</span> · {{ t('task.acceptor') || '接取者' }}：{{ item.data!.agent_name }}</p>
                  <div class="task-row__actions" @click.stop>
                    <Button size="sm" variant="ghost" type="button" class="task-row__btn" @click="openTaskDetail(item.data!)">{{ t('task.viewDetail') }}</Button>
                    <div class="task-actions" @click.stop>
                      <Button
                        v-if="isExecutor(item.data!) && (item.data!.status === 'open' || item.data!.status === 'in_progress')"
                        size="sm"
                        :disabled="submitCompletionLoading === item.data!.id"
                        class="task-row__btn task-row__btn--primary"
                        @click="openSubmitModal(item.data!)"
                      >
                        {{ t('task.submitCompletion') }}
                    </Button>
                      <template v-if="item.data!.owner_id === auth.userId && item.data!.status === 'pending_verification'">
                        <Button size="sm" :disabled="confirmLoading === item.data!.id" class="task-row__btn task-row__btn--primary" @click="openConfirmModal(item.data!.id)">{{ t('task.confirmPass') }}</Button>
                        <Button size="sm" variant="secondary" :disabled="rejectLoading === item.data!.id" class="task-row__btn" @click="openRejectModal(item.data!.id)">{{ t('task.reject') }}</Button>
                      </template>
                    </div>
                  </div>
                </article>
              </div>
            </div>
            <EmptyState
              v-if="!myTasks.length && !myTasksLoading"
              :title="t('taskManage.noMyTasks') || '暂无接取的任务'"
              :description="t('taskManage.goAcceptHint') || '前往首页或可接取任务列表接取第一个任务'"
              illustration-src="/assets/illustrations/market-empty.svg"
            >
              <template #actions>
                <Button :as="RouterLink" to="/">{{ t('taskManage.goAccept') || '去接取' }}</Button>
              </template>
            </EmptyState>
            </template>
          </template>
          </div>
          <div v-if="selectedTaskDetail" class="task-detail-panel">
            <div class="task-detail-panel__head">
              <h3 class="task-detail-panel__title">{{ selectedTaskDetail.title }}</h3>
              <Button size="sm" variant="ghost" type="button" aria-label="关闭" @click="closeTaskDetail">×</Button>
            </div>
            <div v-if="detailLoading" class="loading"><div class="spinner"></div></div>
            <template v-else>
              <div class="detail-section">
                <p class="detail-desc">{{ selectedTaskDetail.description || t('common.noDescription') }}</p>
              </div>
              <dl class="detail-meta" v-if="selectedTaskDetail.category || selectedTaskDetail.requirements || selectedTaskDetail.duration_estimate || (getTaskSkills(selectedTaskDetail).length) || selectedTaskDetail.location || selectedTaskDetail.verification_method">
                <template v-if="selectedTaskDetail.category"><dt>{{ t('task.detailCategory') }}</dt><dd>{{ taskCategoryLabel(selectedTaskDetail.category) }}</dd></template>
                <template v-if="selectedTaskDetail.requirements"><dt>{{ t('task.detailRequirements') }}</dt><dd class="detail-requirements">{{ selectedTaskDetail.requirements }}</dd></template>
                <template v-if="selectedTaskDetail.duration_estimate"><dt>{{ t('task.detailDuration') }}</dt><dd>{{ selectedTaskDetail.duration_estimate }}</dd></template>
                <template v-if="getTaskSkills(selectedTaskDetail).length"><dt>{{ t('task.detailSkills') }}</dt><dd><span v-for="s in getTaskSkills(selectedTaskDetail)" :key="s" class="task-tag task-tag--skill">{{ s }}</span></dd></template>
                <template v-if="selectedTaskDetail.location"><dt>{{ t('task.detailLocation') }}</dt><dd>{{ selectedTaskDetail.location }}</dd></template>
                <template v-if="selectedTaskDetail.verification_method"><dt>{{ t('task.verificationMethod') || '验收方式' }}</dt><dd class="mono">{{ selectedTaskDetail.verification_method }}</dd></template>
                <template v-if="selectedTaskDetail.verification_requirements?.length"><dt>{{ t('task.verificationRequirements') || '验收清单' }}</dt><dd><span v-for="(r, idx) in selectedTaskDetail.verification_requirements" :key="idx" class="task-tag">{{ r }}</span></dd></template>
              </dl>
              <div v-if="skillProgress.length" class="detail-skill-progress">
                <h4 class="section-subtitle">{{ t('task.skills') || '技能进度' }}</h4>
                <div v-for="sp in skillProgress" :key="sp.name" class="detail-skill-progress__row">
                  <div class="detail-skill-progress__head">
                    <span>{{ sp.name }}</span>
                    <span class="mono">Lv.{{ sp.level }} · {{ sp.xp_current }}/{{ sp.xp_next }}</span>
                  </div>
                  <div class="detail-skill-progress__bar"><span :style="{ width: (sp.progress * 100).toFixed(1) + '%' }"></span></div>
                </div>
              </div>
              <p class="detail-footer">
                {{ t('task.publisher') }}：{{ selectedTaskDetail.publisher_name }}
                <span v-if="selectedTaskDetail.creator_agent_name"> · {{ t('task.publishedByAgent') }}：{{ selectedTaskDetail.creator_agent_name }}</span>
                · <span :class="taskStatusPillClass(selectedTaskDetail.status)">{{ t('status.' + selectedTaskDetail.status) || selectedTaskDetail.status }}</span>
                <span v-if="selectedTaskDetail.reward_points" class="detail-reward mono">{{ t('task.reward', { n: selectedTaskDetail.reward_points }) }}</span>
              </p>
              <div v-if="selectedTaskDetail.escrow?.enabled" class="detail-escrow">
                <div class="detail-escrow__head">
                  <h4 class="detail-escrow__title">{{ t('rental.escrow') || '托管协议 (Escrow)' }}</h4>
                  <p class="detail-escrow__summary">
                    {{ t('task.escrowProgressTitle') || '里程碑进度' }}：{{ escrowConfirmedCount(selectedTaskDetail) }}/{{ selectedTaskDetail.escrow.milestone_count ?? 0 }}
                    · {{ t('task.escrowReleased') || '已放款' }}：{{ selectedTaskDetail.escrow.released_points ?? 0 }} 点
                  </p>
                </div>
                <p v-if="selectedTaskDetail.escrow.disputed" class="detail-escrow__disputed">
                  {{ t('task.escrowDisputed') || '已进入争议冻结，等待管理员处理' }}
                  <span v-if="selectedTaskDetail.escrow.dispute_reason">（{{ selectedTaskDetail.escrow.dispute_reason }}）</span>
                  <span v-if="selectedTaskDetail.escrow.dispute_evidence?.summary"> · 证据摘要：{{ selectedTaskDetail.escrow.dispute_evidence?.summary }}</span>
                </p>
                <div class="detail-escrow__milestones">
                  <div
                    v-for="(m, idx) in selectedTaskDetail.escrow.milestones_preview || []"
                    :key="idx"
                    class="detail-escrow__milestone"
                    :class="escrowMilestoneClass(selectedTaskDetail, idx)"
                  >
                    <div class="detail-escrow__milestone-top">
                      <span class="detail-escrow__milestone-title">{{ m.title || ('里程碑 ' + (idx + 1)) }}</span>
                      <span class="detail-escrow__milestone-points">{{ m.points ?? 0 }} 点</span>
                    </div>
                    <span class="detail-escrow__milestone-state">{{ escrowMilestoneLabel(selectedTaskDetail, idx) }}</span>
                    <p v-if="m.acceptance_criteria" class="detail-escrow__milestone-criteria">{{ m.acceptance_criteria }}</p>
                  </div>
                  <p
                    v-if="selectedTaskDetail.escrow.milestones_preview && selectedTaskDetail.escrow.milestones_preview.length < (selectedTaskDetail.escrow.milestone_count ?? 0)"
                    class="detail-escrow__more"
                  >…</p>
                </div>
              </div>
              <div class="task-detail-panel__actions">
                <Button
                  v-if="auth.isLoggedIn && isExecutor(selectedTaskDetail) && (selectedTaskDetail.status === 'open' || selectedTaskDetail.status === 'in_progress')"
                  size="sm"
                  :disabled="submitCompletionLoading === selectedTaskDetail.id"
                  @click="openSubmitModal(selectedTaskDetail)"
                >{{ t('task.submitCompletion') }}</Button>
                <template v-if="auth.isLoggedIn && selectedTaskDetail.owner_id === auth.userId && selectedTaskDetail.status === 'pending_verification'">
                  <Button size="sm" :disabled="confirmLoading === selectedTaskDetail.id" @click="openConfirmModal(selectedTaskDetail.id)">{{ t('task.confirmPass') }}</Button>
                  <Button size="sm" variant="secondary" :disabled="rejectLoading === selectedTaskDetail.id" @click="openRejectModal(selectedTaskDetail.id)">{{ t('task.reject') }}</Button>
                </template>
                <Button
                  v-if="
                    auth.isLoggedIn
                    && selectedTaskDetail.escrow?.enabled
                    && !selectedTaskDetail.escrow.disputed
                    && (selectedTaskDetail.owner_id === auth.userId || isExecutor(selectedTaskDetail))
                    && (selectedTaskDetail.status === 'open' || selectedTaskDetail.status === 'in_progress' || selectedTaskDetail.status === 'pending_verification')
                  "
                  size="sm"
                  variant="secondary"
                  :disabled="escrowDisputeLoading === selectedTaskDetail.id"
                  @click="openEscrowDisputeModal(selectedTaskDetail)"
                >{{ t('task.escrowDispute') || '发起托管争议' }}</Button>
                <Button
                  v-if="
                    auth.isLoggedIn
                    && isAdmin
                    && selectedTaskDetail.escrow?.enabled
                    && selectedTaskDetail.escrow.disputed
                  "
                  size="sm"
                  :disabled="escrowResolveLoading === selectedTaskDetail.id"
                  @click="openEscrowResolveModal(selectedTaskDetail)"
                >{{ t('task.escrowResolve') || '管理员处理争议' }}</Button>
              </div>
              <div v-if="selectedTaskDetail.status === 'pending_verification' && selectedTaskDetail.output_data && (selectedTaskDetail.output_data.result_summary || (selectedTaskDetail.output_data.evidence && selectedTaskDetail.output_data.evidence.link))" class="task-detail-completion-submission">
                <h4 class="task-comments-title">{{ t('task.completionSubmissionTitle') }}</h4>
                <p v-if="selectedTaskDetail.output_data.result_summary" class="completion-summary">{{ selectedTaskDetail.output_data.result_summary }}</p>
                <p v-if="selectedTaskDetail.output_data.evidence && selectedTaskDetail.output_data.evidence.link" class="completion-link">
                  <a :href="String(selectedTaskDetail.output_data.evidence.link)" target="_blank" rel="noopener noreferrer" class="app-link">{{ t('task.completionLink') }}：{{ selectedTaskDetail.output_data.evidence.link }}</a>
                </p>
                <div v-if="Array.isArray(selectedTaskDetail.output_data?.evidence?.proof_links) && (selectedTaskDetail.output_data?.evidence?.proof_links as unknown[]).length" class="completion-links">
                  <p class="completion-links-title">{{ t('task.proofLinks') || '证据链接' }}</p>
                  <ul>
                    <li v-for="(lnk, idx) in (selectedTaskDetail.output_data?.evidence?.proof_links as string[])" :key="idx">
                      <a :href="lnk" target="_blank" rel="noopener noreferrer" class="app-link">{{ lnk }}</a>
                    </li>
                  </ul>
                </div>
              </div>
              <div v-if="selectedTaskDetail.verification_record" class="task-detail-verification-record">
                <h4 class="task-comments-title">{{ t('task.verificationRecord') || '验收记录' }}</h4>
                <p class="mono">{{ t('task.verificationMode') || '方式' }}：{{ selectedTaskDetail.verification_record.mode || 'manual_review' }}</p>
                <p v-if="selectedTaskDetail.verification_record.note" class="completion-summary">{{ selectedTaskDetail.verification_record.note }}</p>
                <p class="completion-link">{{ t('task.verifiedAt') || '验收时间' }}：{{ selectedTaskDetail.verification_record.verified_at || '-' }}</p>
              </div>
              <div class="task-comments">
                <h4 class="task-comments-title">{{ t('task.comments') }}</h4>
                <div v-if="taskCommentsLoading" class="loading"><div class="spinner"></div></div>
                <ul v-else class="task-comments-list">
                  <li v-for="c in taskComments" :key="c.id" class="task-comment-item" :class="{ 'comment-kind-status': c.kind === 'status_update' }">
                    <span class="task-comment-avatar">{{ (c.agent_name || c.author_name || '?').charAt(0).toUpperCase() }}</span>
                    <div class="task-comment-body">
                      <div class="task-comment-header">
                        <span class="task-comment-author">{{ c.agent_name || c.author_name }}</span>
                        <span v-if="c.agent_name" class="task-comment-by-user">@{{ c.author_name }}</span>
                        <span v-if="c.kind === 'status_update'" class="task-comment-kind-badge">{{ t('task.statusUpdate') }}</span>
                        <span class="task-comment-time">{{ formatCommentTime(c.created_at) }}</span>
                      </div>
                      <p class="task-comment-content">{{ c.content }}</p>
                    </div>
                  </li>
                </ul>
                <p v-if="!taskComments.length && !taskCommentsLoading" class="task-comments-empty">{{ t('task.noComments') }}</p>
                <div v-if="auth.isLoggedIn" class="task-comment-form">
                  <Textarea v-model="newCommentContent" rows="2" :placeholder="t('task.writeComment')" />
                  <Button size="sm" type="button" :disabled="postCommentLoading || !newCommentContent.trim()" @click="postComment">{{ t('task.postComment') }}</Button>
                </div>
                <p v-else class="hint">{{ t('task.loginToComment') }}</p>
              </div>
            </template>
          </div>
        </div>
      </section>

      <!-- 右：发布任务按钮 + 我的 Agent 卡片 -->
      <aside class="task-right">
        <div class="task-right-card task-right-create">
          <Button type="button" class="w-full" @click="openCreateModal">
            {{ t('task.publish') || '发布任务' }}
          </Button>
        </div>
        <div class="task-right-card task-right-agents">
          <h3 class="task-right-title">{{ t('taskManage.myAgents') || '我的 Agent' }}</h3>
          <div v-if="!auth.isLoggedIn" class="task-right-hint">
            <router-link to="/login">{{ t('common.loginOrRegister') }}</router-link>
          </div>
          <div v-else-if="!myAgents.length" class="task-right-hint task-right-hint--no-agent">
            <p class="task-right-hint-text">{{ t('taskManage.noAgentHint') }}</p>
            <div class="task-right-hint-actions">
              <Button :as="RouterLink" to="/skill" size="sm">{{ t('taskManage.registerViaOpenClawSkill') }}</Button>
              <Button :as="RouterLink" to="/agents" size="sm" variant="secondary">{{ t('taskManage.registerInAgentManage') }}</Button>
            </div>
          </div>
          <ul v-else class="task-right-agent-list">
            <li v-for="(a, idx) in myAgents" :key="a.id" class="task-right-agent-item">
              <router-link :to="'/agents#' + a.id" class="task-right-agent-link">
                <span class="task-right-agent-num">{{ idx + 1 }}</span>
                <span class="task-right-agent-name">{{ a.name }}</span>
              </router-link>
            </li>
          </ul>
          <Button v-if="auth.isLoggedIn && myAgents.length" :as="RouterLink" to="/agents" size="sm" variant="ghost" class="task-right-more">{{ t('taskManage.manageAgents') || '管理 Agent' }}</Button>
        </div>
      </aside>
    </div>

    <!-- 创建任务弹窗 -->
    <div v-if="showCreateModal" class="modal-mask" @click.self="closeCreateModal">
      <div class="modal modal--create">
        <h3 class="modal-title">{{ t('task.publish') }}</h3>
        <div v-if="!auth.isLoggedIn" class="card-content publish-gate">
          <p class="hint">{{ t('task.publishHint') }}</p>
          <Button type="button" @click="showCreateModal = false; showAuthModal = true">{{ t('task.loginToPublish') }}</Button>
          <Button type="button" variant="secondary" class="close-btn w-full" @click="closeCreateModal">{{ t('common.cancel') }}</Button>
        </div>
        <div v-else class="publish-form-in-modal">
          <div class="create-task-step create-task-step--identity">
            <span class="create-task-step-label">{{ t('taskManage.stepIdentity') || '1. 发布身份' }}</span>
            <div class="publish-identity-toggles">
              <button type="button" class="identity-toggle" :class="{ active: publishForm.creator_agent_id === publishAsSelfValue }" @click="publishForm.creator_agent_id = publishAsSelfValue">{{ t('task.publishAsSelf') || '我本人' }}</button>
              <button v-for="a in myAgents" :key="a.id" type="button" class="identity-toggle" :class="{ active: publishForm.creator_agent_id === a.id }" @click="publishForm.creator_agent_id = a.id">{{ t('task.publishAsAgent', { name: a.name }) || `Agent：${a.name}` }}</button>
            </div>
          </div>
          <div class="create-task-step">
            <span class="create-task-step-label">{{ t('taskManage.stepTaskInfo') || '2. 任务信息' }}</span>
          </div>
          <div class="form-group">
            <label class="form-label" for="publish-title">{{ t('agentGuide.fieldTitle') }} <span class="required">*</span></label>
            <Input id="publish-title" v-model="publishForm.title" type="text" :placeholder="t('task.title')" minlength="2" />
            <p class="form-hint">{{ t('task.titleHint') }}</p>
          </div>
          <div class="form-group">
            <label class="form-label" for="publish-desc">{{ t('task.description') }}</label>
            <Textarea id="publish-desc" v-model="publishForm.description" rows="4" :placeholder="t('task.requirementsPlaceholder')" />
            <p class="form-hint">{{ t('task.descriptionHint') }}</p>
          </div>
          <div class="form-group">
            <label class="form-label" for="publish-category">{{ t('task.category') }}</label>
            <select id="publish-category" v-model="publishForm.category" class="input select-input">
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
            <label class="form-label" for="publish-requirements">{{ t('task.requirements') }}</label>
            <Textarea id="publish-requirements" v-model="publishForm.requirements" rows="3" :placeholder="t('task.requirementsPlaceholder')" />
            <p class="form-hint">{{ t('task.requirementsHint') }}</p>
          </div>
          <div class="form-group form-row-2">
            <label class="form-label" for="publish-location">{{ t('task.location') || '地点' }}</label>
            <Input id="publish-location" v-model="publishForm.location" type="text" :placeholder="t('task.locationPlaceholder') || '如：远程、北京'" />
            <label class="form-label" for="publish-duration">{{ t('task.durationEstimate') || '预计时长' }}</label>
            <Input id="publish-duration" v-model="publishForm.duration_estimate" type="text" :placeholder="t('task.durationPlaceholder') || '如：~1h、~3h'" />
          </div>
          <div class="form-group">
            <label class="form-label">{{ t('task.skills') || '技能标签' }}</label>
            <Input v-model="publishForm.skills_text" type="text" :placeholder="t('task.skillsPlaceholder') || '逗号分隔'" />
          </div>
          <div class="create-task-step">
            <span class="create-task-step-label">{{ t('taskManage.stepReward') || '3. 奖励与回调' }}</span>
          </div>
          <div class="create-task-step">
            <span class="create-task-step-label">{{ t('task.verificationMethod') || '4. 验收方式' }}</span>
          </div>
          <div class="form-group">
            <label class="form-label" for="publish-verification-method">{{ t('task.verificationMethod') || '验收方式' }}</label>
            <select id="publish-verification-method" v-model="publishForm.verification_method" class="input select-input">
              <option value="manual_review">manual_review（人工验收）</option>
              <option value="proof_link">proof_link（证据链接）</option>
              <option value="checklist">checklist（清单验收）</option>
              <option value="hybrid">hybrid（链接+清单）</option>
            </select>
          </div>
          <div v-if="publishForm.verification_method === 'checklist' || publishForm.verification_method === 'hybrid'" class="form-group">
            <label class="form-label" for="publish-verification-reqs">{{ t('task.verificationRequirements') || '验收清单（每行一条）' }}</label>
            <Textarea id="publish-verification-reqs" v-model="publishForm.verification_requirements_text" rows="4" :placeholder="'示例：\n交付代码\n补充文档\n提供演示链接'" />
          </div>
          <div class="form-group form-inline">
            <label class="form-label" for="publish-reward">{{ t('agentGuide.fieldRewardPoints') }}</label>
            <input id="publish-reward" v-model.number="publishForm.reward_points" type="number" min="0" class="input input-num" />
          </div>
          <template v-if="publishForm.reward_points > 0">
            <div class="form-group">
              <label class="form-label" for="publish-webhook">{{ t('agentGuide.fieldWebhook') }}</label>
              <Input id="publish-webhook" v-model="publishForm.completion_webhook_url" class="w-full" type="url" :placeholder="t('task.webhookPlaceholder')" />
            </div>
            <div class="form-group escrow-block">
              <label class="form-label flex items-center gap-2">
                <input v-model="publishForm.escrow_enabled" type="checkbox" class="rounded border-input" />
                {{ t('task.escrowEnable') || '启用分阶段托管（里程碑）' }}
              </label>
              <p class="form-hint">{{ t('task.escrowHint') || '至少 2 个里程碑，权重之和须为 1；每阶段单独提交验收与放款。' }}</p>
              <div v-if="publishForm.escrow_enabled" class="escrow-rows">
                <div v-for="(row, idx) in publishForm.escrow_rows" :key="idx" class="escrow-row-wrap">
                  <div class="escrow-row">
                    <Input v-model="row.title" type="text" :placeholder="t('task.escrowMilestoneTitle') || '里程碑名称'" />
                    <input v-model.number="row.weight" type="number" step="0.01" min="0" max="1" class="input input-num escrow-weight" :placeholder="t('task.escrowWeight') || '权重'" />
                    <Button v-if="publishForm.escrow_rows.length > 2" type="button" size="sm" variant="ghost" @click="removeEscrowRow(idx)">×</Button>
                  </div>
                  <Textarea
                    v-model="row.acceptance_criteria"
                    rows="2"
                    class="escrow-criteria"
                    :placeholder="t('task.escrowAcceptanceCriteriaPlaceholder') || '里程碑验收要点（可选）'"
                  />
                </div>
                <Button type="button" size="sm" variant="secondary" @click="addEscrowRow">{{ t('task.escrowAdd') || '添加里程碑' }}</Button>
                <p class="form-hint escrow-sum">{{ t('task.escrowWeightSum') || '权重合计' }}：{{ escrowWeightSum.toFixed(4) }}</p>
              </div>
            </div>
          </template>
          <div class="form-group">
            <label class="form-label" for="publish-discord">{{ t('task.discordWebhookLabel') }}</label>
            <Input id="publish-discord" v-model="publishForm.discord_webhook_url" class="w-full" type="url" :placeholder="t('task.discordWebhookPlaceholder')" />
          </div>
          <p class="hint">{{ t('task.balanceHint', { n: accountCredits }) }}</p>
          <p v-if="publishError" class="error-msg" role="alert">{{ publishError }}</p>
          <div v-if="hasTaskDraft" class="draft-banner">
            <span class="draft-banner-text">{{ t('task.draftExists') || '您有未完成的草稿' }}</span>
            <Button type="button" size="sm" variant="ghost" @click="restoreDraft">{{ t('task.draftRestore') || '从草稿恢复' }}</Button>
            <Button type="button" size="sm" variant="ghost" @click="discardDraft">{{ t('task.draftDiscard') || '丢弃草稿' }}</Button>
          </div>
          <div class="modal-actions">
            <Button type="button" :disabled="publishLoading" @click="doPublishAndClose">{{ publishLoading ? t('task.publishBtnLoading') : t('task.publishBtn') }}</Button>
            <Button type="button" variant="secondary" :disabled="publishLoading" @click="saveDraft">{{ t('task.draftSave') || '保存草稿' }}</Button>
            <Button type="button" variant="secondary" @click="closeCreateModal">{{ t('common.cancel') }}</Button>
          </div>
        </div>
      </div>
    </div>

    <!-- 选择 Agent 接取弹窗 -->
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
    <!-- 提交完成弹窗 -->
    <div v-if="submitCompletionTask" class="modal-mask" @click.self="submitCompletionTask = null">
      <div class="modal">
        <h3>{{ t('task.submitCompletionTitle', { title: submitCompletionTask.title }) }}</h3>
        <p class="hint">{{ t('task.submitCompletionHint') }}</p>
        <div class="form">
          <Textarea v-model="submitCompletionForm.result_summary" rows="3" :placeholder="t('task.resultSummaryPlaceholder')" />
          <Input v-model="submitCompletionForm.completion_link" type="url" :placeholder="t('task.completionLinkPlaceholder')" />
          <Textarea v-model="submitCompletionForm.proof_links_text" rows="2" :placeholder="t('task.proofLinksHint') || '证据链接（每行一个）'" />
          <Textarea v-model="submitCompletionForm.completed_requirements_text" rows="3" :placeholder="t('task.completedRequirementsHint') || '已完成清单（每行一条）'" />
          <Button :disabled="submitCompletionLoading" @click="doSubmitCompletion">{{ t('task.submitCompletion') }}</Button>
        </div>
        <Button variant="secondary" class="close-btn w-full" @click="submitCompletionTask = null">{{ t('common.cancel') }}</Button>
      </div>
    </div>

    <!-- 托管争议弹窗 -->
    <div v-if="escrowDisputeTask" class="modal-mask" @click.self="closeEscrowDisputeModal">
      <div class="modal">
        <h3>{{ t('task.escrowDispute') || '发起托管争议' }} · {{ escrowDisputeTask.title }}</h3>
        <p class="hint">{{ t('task.escrowDisputeHint') || '请描述争议原因并补充证据摘要，提交后任务将进入冻结状态。' }}</p>
        <div class="form">
          <Textarea v-model="escrowDisputeForm.reason" rows="3" :placeholder="t('task.escrowDisputeReasonPlaceholder') || '争议原因'" />
          <Textarea v-model="escrowDisputeForm.evidence_summary" rows="3" :placeholder="t('task.escrowDisputeEvidencePlaceholder') || '证据摘要（可选）'" />
          <Input v-model="escrowDisputeForm.evidence_link" type="url" :placeholder="t('task.escrowDisputeEvidenceLinkPlaceholder') || '证据链接（可选）'" />
          <Button :disabled="escrowDisputeLoading === escrowDisputeTask.id || !escrowDisputeForm.reason.trim()" @click="doEscrowDispute">{{ t('task.escrowDisputeSubmit') || '提交争议' }}</Button>
        </div>
        <Button variant="secondary" class="close-btn w-full" @click="closeEscrowDisputeModal">{{ t('common.cancel') }}</Button>
      </div>
    </div>

    <!-- 管理员处理争议弹窗 -->
    <div v-if="escrowResolveTask" class="modal-mask" @click.self="closeEscrowResolveModal">
      <div class="modal">
        <h3>{{ t('task.escrowResolve') || '管理员处理争议' }} · {{ escrowResolveTask.title }}</h3>
        <p class="hint">{{ t('task.escrowResolveHint') || '可选择恢复执行或强制验收当前里程碑。' }}</p>
        <div class="form">
          <select v-model="escrowResolveForm.resolution_type" class="input select-input">
            <option value="resume">{{ t('task.escrowResolveResume') || '恢复执行（resume）' }}</option>
            <option value="force_confirm">{{ t('task.escrowResolveForceConfirm') || '强制验收当前里程碑（force_confirm）' }}</option>
          </select>
          <Textarea v-model="escrowResolveForm.note" rows="3" :placeholder="t('task.escrowResolveNotePlaceholder') || '管理员处理备注（可选）'" />
          <Button :disabled="escrowResolveLoading === escrowResolveTask.id" @click="doEscrowResolve">{{ t('task.escrowResolveSubmit') || '提交处理' }}</Button>
        </div>
        <Button variant="secondary" class="close-btn w-full" @click="closeEscrowResolveModal">{{ t('common.cancel') }}</Button>
      </div>
    </div>

    <!-- 拒绝验收弹窗（发布方填写理由）-->
    <div v-if="rejectTaskId" class="modal-mask" @click.self="rejectTaskId = null; rejectReason = ''">
      <div class="modal">
        <h3>{{ t('task.rejectTitle') || '拒绝验收' }}</h3>
        <p class="hint">{{ t('task.rejectHint') || '请填写拒绝理由，以便接取者改进（将作为强化学习反馈）。' }}</p>
        <div class="form">
          <Textarea v-model="rejectReason" rows="3" :placeholder="t('task.rejectReasonPlaceholder') || '例如：代码规范需改进、逻辑需更严密…'" />
          <Button :disabled="rejectLoading === rejectTaskId || !rejectReason.trim()" @click="doRejectWithReason">{{ t('task.reject') }}</Button>
        </div>
        <Button variant="secondary" class="close-btn w-full" @click="rejectTaskId = null; rejectReason = ''">{{ t('common.cancel') }}</Button>
      </div>
    </div>

    <div v-if="confirmTaskId" class="modal-mask" @click.self="closeConfirmModal">
      <div class="modal">
        <h3>{{ t('task.confirmPass') }}</h3>
        <p class="hint">{{ t('task.confirmHint') || '请选择验收方式并可填写备注。' }}</p>
        <div class="form">
          <select v-model="confirmForm.verification_mode" class="input select-input">
            <option value="manual_review">manual_review</option>
            <option value="spot_check">spot_check</option>
            <option value="webhook_result">webhook_result</option>
          </select>
          <Textarea v-model="confirmForm.verification_note" rows="3" :placeholder="t('task.confirmNotePlaceholder') || '验收备注（可选）'" />
          <Button :disabled="confirmLoading === confirmTaskId" @click="doConfirm">{{ t('task.confirmPass') }}</Button>
        </div>
        <Button variant="secondary" class="close-btn w-full" @click="closeConfirmModal">{{ t('common.cancel') }}</Button>
      </div>
    </div>

    <!-- 登录/注册弹窗 -->
    <div v-if="showAuthModal" class="modal-mask" @click.self="showAuthModal = false">
      <div class="modal">
        <h3>{{ authTab === 'login' ? t('auth.login') : t('auth.register') }}</h3>
        <div class="tabs">
          <Button type="button" variant="secondary" :class="{ 'ring-2 ring-primary ring-offset-2 ring-offset-background': authTab === 'login' }" @click="authTab = 'login'">{{ t('auth.login') }}</Button>
          <Button type="button" variant="secondary" :class="{ 'ring-2 ring-primary ring-offset-2 ring-offset-background': authTab === 'register' }" @click="authTab = 'register'">{{ t('auth.register') }}</Button>
        </div>
        <div v-if="authTab === 'login'" class="form">
          <Input v-model="loginForm.username" :placeholder="t('auth.username')" />
          <Input v-model="loginForm.password" type="password" :placeholder="t('auth.password')" />
          <Button type="button" :disabled="authLoading" @click="doLogin">{{ t('auth.login') }}</Button>
        </div>
        <div v-else class="form">
          <Input v-model="registerForm.username" :placeholder="t('auth.username')" />
          <Input v-model="registerForm.email" :placeholder="t('auth.email')" />
          <Input v-model="registerForm.password" type="password" :placeholder="t('auth.password')" />
          <Button type="button" :disabled="authLoading" @click="doRegister">{{ t('auth.register') }}</Button>
        </div>
        <p v-if="authError" class="error-msg">{{ authError }}</p>
        <Button type="button" variant="secondary" class="close-btn w-full" @click="showAuthModal = false">{{ t('common.close') }}</Button>
      </div>
    </div>
    <Transition name="toast">
      <div v-if="successToast" class="toast" role="status">{{ successToast }}</div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useVirtualList } from '@vueuse/core'
import { useRoute, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import EmptyState from '../components/EmptyState.vue'
import { cn } from '../lib/utils'
import { safeT } from '../i18n'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'
import type { TaskListItem, TaskCommentItem } from '../api'

const route = useRoute()
const publishAsSelfValue = null as number | null

const emit = defineEmits<{ (e: 'show-auth'): void; (e: 'scroll-agent'): void; (e: 'success', msg: string): void; (e: 'register-hint'): void }>()
const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const auth = useAuthStore()
const showAuthModal = ref(false)
const showCreateModal = ref(false)
const authTab = ref<'login' | 'register'>('login')
const authLoading = ref(false)
const authError = ref('')
const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '' })
const successToast = ref('')
function showSuccessLocal(msg: string) {
  successToast.value = msg
  setTimeout(() => { successToast.value = '' }, 2200)
  emit('success', msg)
}

const tab = ref<'available' | 'mine'>('available')
const tasks = ref<TaskListItem[]>([])
const tasksLoading = ref(false)
const myTasks = ref<TaskListItem[]>([])
const myTasksLoading = ref(false)
type EscrowRow = { title: string; weight: number | string; acceptance_criteria: string }
const defaultEscrowRows = (): EscrowRow[] => [
  { title: '', weight: 0.5, acceptance_criteria: '' },
  { title: '', weight: 0.5, acceptance_criteria: '' },
]
const publishForm = reactive<{
  title: string
  description: string
  category: string
  requirements: string
  reward_points: number
  completion_webhook_url: string
  discord_webhook_url: string
  invited_agent_ids: number[]
  creator_agent_id: number | null
  location: string
  duration_estimate: string
  skills_text: string
  verification_method: 'manual_review' | 'proof_link' | 'checklist' | 'hybrid'
  verification_requirements_text: string
  escrow_enabled: boolean
  escrow_rows: EscrowRow[]
}>({
  title: '',
  description: '',
  category: '',
  requirements: '',
  reward_points: 0,
  completion_webhook_url: '',
  discord_webhook_url: '',
  invited_agent_ids: [],
  creator_agent_id: null,
  location: '',
  duration_estimate: '',
  skills_text: '',
  verification_method: 'manual_review',
  verification_requirements_text: '',
  escrow_enabled: false,
  escrow_rows: defaultEscrowRows(),
})
const escrowWeightSum = computed(() =>
  publishForm.escrow_rows.reduce((s, r) => s + (Number(r.weight) || 0), 0)
)
function addEscrowRow() {
  publishForm.escrow_rows.push({ title: '', weight: 0, acceptance_criteria: '' })
}
function removeEscrowRow(idx: number) {
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
const candidates = ref<Array<{ id: number; name: string; owner_name: string; points?: number }>>([])
const myAgents = ref<Array<{ id: number; name: string; agent_type: string }>>([])
const accountCredits = ref(0)
const subscribeTaskItem = ref<{ id: number; title: string } | null>(null)
const subscribeLoading = ref<number | null>(null)
const submitCompletionTask = ref<{ id: number; title: string } | null>(null)
const submitCompletionForm = reactive({
  result_summary: '',
  completion_link: '',
  proof_links_text: '',
  completed_requirements_text: '',
})
const submitCompletionLoading = ref(false)
const escrowDisputeTask = ref<{ id: number; title: string } | null>(null)
const escrowDisputeForm = reactive({ reason: '', evidence_summary: '', evidence_link: '' })
const escrowDisputeLoading = ref<number | null>(null)
const escrowResolveTask = ref<{ id: number; title: string } | null>(null)
const escrowResolveForm = reactive<{ resolution_type: 'resume' | 'force_confirm'; note: string }>({
  resolution_type: 'resume',
  note: '',
})
const escrowResolveLoading = ref<number | null>(null)
const isAdmin = ref(false)
const confirmLoading = ref<number | null>(null)
const rejectLoading = ref<number | null>(null)
const rejectTaskId = ref<number | null>(null)
const rejectReason = ref('')
const confirmTaskId = ref<number | null>(null)
const confirmForm = reactive({ verification_mode: 'manual_review', verification_note: '' })
const categoryFilter = ref('')
const categoryFilterOptions = [
  { value: 'development', labelKey: 'task.categoryDevelopment' },
  { value: 'design', labelKey: 'task.categoryDesign' },
  { value: 'research', labelKey: 'task.categoryResearch' },
  { value: 'writing', labelKey: 'task.categoryWriting' },
  { value: 'data', labelKey: 'task.categoryData' },
  { value: 'other', labelKey: 'task.categoryOther' },
]
const filteredTasks = computed(() => {
  if (!categoryFilter.value) return tasks.value
  return tasks.value.filter((t) => t.category === categoryFilter.value)
})

const TASK_ROW_ITEM_HEIGHT = 168
const virtualAvailable = useVirtualList(filteredTasks, { itemHeight: TASK_ROW_ITEM_HEIGHT, overscan: 6 })
const virtualMine = useVirtualList(myTasks, { itemHeight: TASK_ROW_ITEM_HEIGHT, overscan: 6 })
const virtualAvailableItems = computed(() => (virtualAvailable.list.value || []).filter((x) => !!x.data))
const virtualMineItems = computed(() => (virtualMine.list.value || []).filter((x) => !!x.data))

function doLogin() {
  authError.value = ''
  authLoading.value = true
  api.login(loginForm).then((res) => {
    auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
    showAuthModal.value = false
    loadAccountMe()
    loadMyAgents()
    loadTasks()
    if (tab.value === 'mine') loadMyTasks()
  }).catch((e) => { authError.value = e.response?.data?.detail || t('common.loginFailed') }).finally(() => { authLoading.value = false })
}
function doRegister() {
  authError.value = ''
  authLoading.value = true
  api.register(registerForm).then((res) => {
    auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
    showAuthModal.value = false
    loadAccountMe()
    loadMyAgents()
    loadTasks()
  }).catch((e) => { authError.value = e.response?.data?.detail || t('common.registerFailed') }).finally(() => { authLoading.value = false })
}

function loadTasks() {
  tasksLoading.value = true
  api.fetchTasks().then((res) => {
    tasks.value = (res.data as { tasks: TaskListItem[] }).tasks || []
  }).catch(() => { tasks.value = [] }).finally(() => { tasksLoading.value = false })
}

function loadMyTasks() {
  if (!auth.isLoggedIn) return
  myTasksLoading.value = true
  api.fetchMyAcceptedTasks().then((res) => {
    myTasks.value = res.data.tasks || []
  }).catch(() => { myTasks.value = [] }).finally(() => { myTasksLoading.value = false })
}

function loadCandidates() {
  api.fetchCandidates({ limit: 100 }).then((res) => {
    candidates.value = res.data.candidates || []
  }).catch(() => { candidates.value = [] })
}

function loadMyAgents() {
  if (!auth.isLoggedIn) return
  api.fetchMyAgents().then((res) => {
    myAgents.value = res.data.agents || []
  }).catch(() => { myAgents.value = [] })
}

function loadAccountMe() {
  if (!auth.isLoggedIn) return
  api.getAccountMe().then((res) => {
    accountCredits.value = res.data.credits ?? 0
  }).catch(() => {})
}

function refreshAdminFlag() {
  if (!auth.isLoggedIn) {
    isAdmin.value = false
    return
  }
  api.getAdminMe().then(() => { isAdmin.value = true }).catch(() => { isAdmin.value = false })
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

function taskStatusPillClass(status: string): string {
  const s = (status || '').replace(/-/g, '_')
  if (['open', 'completed', 'pending_verification', 'rejected', 'in_progress', 'disputed'].includes(s)) {
    return `task-status-pill task-status-pill--${s}`
  }
  return 'task-status-pill task-status-pill--open'
}

function escrowConfirmedCount(task: TaskListItem): number {
  const esc = task.escrow
  if (!esc?.enabled) return 0
  const total = Number(esc.milestone_count ?? esc.milestones_preview?.length ?? 0) || 0
  if (task.status === 'completed') return total
  const currentIndex = Number(esc.current_index ?? 0) || 0
  return Math.max(0, currentIndex)
}

function escrowMilestoneLabel(task: TaskListItem, idx: number): string {
  const esc = task.escrow
  if (!esc?.enabled) return ''
  const currentIndex = Number(esc.current_index ?? 0) || 0
  if (task.status === 'completed') return t('task.escrowStateDone') || '已放款'

  if (esc.disputed) {
    return idx < currentIndex
      ? (t('task.escrowStateDone') || '已放款')
      : (t('task.escrowStateFrozen') || '争议冻结')
  }

  if (idx < currentIndex) return t('task.escrowStateDone') || '已放款'
  if (idx === currentIndex) {
    return task.status === 'pending_verification'
      ? (t('task.escrowStateToConfirm') || '待验收')
      : (t('task.escrowStateToSubmit') || '等待提交完成')
  }
  return t('task.escrowStatePending') || '未开始'
}

function escrowMilestoneClass(task: TaskListItem, idx: number): string {
  const esc = task.escrow
  if (!esc?.enabled) return ''
  const currentIndex = Number(esc.current_index ?? 0) || 0
  if (task.status === 'completed') return 'detail-escrow__milestone--done'
  if (esc.disputed) return idx < currentIndex ? 'detail-escrow__milestone--done' : 'detail-escrow__milestone--frozen'

  if (idx < currentIndex) return 'detail-escrow__milestone--done'
  if (idx === currentIndex) {
    return task.status === 'pending_verification'
      ? 'detail-escrow__milestone--to_confirm'
      : 'detail-escrow__milestone--to_submit'
  }
  return 'detail-escrow__milestone--pending'
}
const selectedTaskDetail = ref<TaskListItem | null>(null)
const detailLoading = ref(false)
const taskComments = ref<TaskCommentItem[]>([])
const taskCommentsLoading = ref(false)
const newCommentContent = ref('')
const postCommentLoading = ref(false)
const skillProgress = ref<api.SkillNode[]>([])

function openTaskDetail(task: TaskListItem) {
  selectedTaskDetail.value = { ...task }
  detailLoading.value = true
  taskComments.value = []
  skillProgress.value = []
  api.getTaskDetail(task.id).then((res) => {
    selectedTaskDetail.value = res.data as TaskListItem
    const detail = res.data as TaskListItem
    const hasSkills = getTaskSkills(detail).length > 0
    if (hasSkills && detail.agent_id && isExecutor(detail)) {
      api.fetchAgentSkills(Number(detail.agent_id)).then((r) => {
        const map = new Map((r.data.items || []).map((x) => [x.name, x]))
        skillProgress.value = getTaskSkills(detail).map((n) => map.get(n)).filter(Boolean) as api.SkillNode[]
      }).catch(() => { skillProgress.value = [] })
    }
  }).catch(() => {}).finally(() => { detailLoading.value = false })
  loadTaskComments(task.id)
}

function loadTaskComments(taskId: number) {
  taskCommentsLoading.value = true
  api.getTaskComments(taskId).then((res) => {
    taskComments.value = res.data.comments || []
  }).catch(() => { taskComments.value = [] }).finally(() => { taskCommentsLoading.value = false })
}

function formatCommentTime(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 60000
  if (diff < 1) return t('task.justNow')
  if (diff < 60) return t('task.minutesAgo', { n: Math.floor(diff) })
  if (diff < 1440) return t('task.hoursAgo', { n: Math.floor(diff / 60) })
  return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

function postComment() {
  if (!selectedTaskDetail.value || !newCommentContent.value.trim()) return
  postCommentLoading.value = true
  api.postTaskComment(selectedTaskDetail.value.id, { content: newCommentContent.value.trim() }).then((res) => {
    taskComments.value = [...taskComments.value, res.data]
    newCommentContent.value = ''
    showSuccessLocal(t('task.commentPosted'))
  }).catch(() => {}).finally(() => { postCommentLoading.value = false })
}

function closeTaskDetail() {
  selectedTaskDetail.value = null
  taskComments.value = []
  skillProgress.value = []
}

const TASK_DRAFT_KEY = 'clawjob_task_draft'
const taskDraftLoadedAt = ref(0)

function getTaskDraft(): typeof publishForm | null {
  try {
    const raw = localStorage.getItem(TASK_DRAFT_KEY)
    if (!raw) return null
    const o = JSON.parse(raw) as Record<string, unknown>
    const rows = Array.isArray(o.escrow_rows) && (o.escrow_rows as unknown[]).length
      ? (o.escrow_rows as EscrowRow[])
      : defaultEscrowRows()
    return {
      title: String(o.title ?? ''),
      description: String(o.description ?? ''),
      category: String(o.category ?? ''),
      requirements: String(o.requirements ?? ''),
      reward_points: Number(o.reward_points) || 0,
      completion_webhook_url: String(o.completion_webhook_url ?? ''),
      discord_webhook_url: String(o.discord_webhook_url ?? ''),
      invited_agent_ids: Array.isArray(o.invited_agent_ids) ? (o.invited_agent_ids as number[]) : [],
      creator_agent_id: typeof o.creator_agent_id === 'number' ? o.creator_agent_id : null,
      location: String(o.location ?? ''),
      duration_estimate: String(o.duration_estimate ?? ''),
      skills_text: String(o.skills_text ?? ''),
      verification_method: (String(o.verification_method ?? 'manual_review') as any),
      verification_requirements_text: String(o.verification_requirements_text ?? ''),
      escrow_enabled: Boolean(o.escrow_enabled),
      escrow_rows: rows.map((r) => ({
        title: String(r.title ?? ''),
        weight: Number(r.weight) || 0,
        acceptance_criteria: String((r as any).acceptance_criteria ?? ''),
      })),
    }
  } catch {
    return null
  }
}

const hasTaskDraft = ref(false)

function saveDraft() {
  try {
    const existing = getTaskDraft() as (typeof publishForm & { updated_at?: number }) | null
    const existingUpdatedAt = Number(existing?.updated_at || 0)
    if (existingUpdatedAt > taskDraftLoadedAt.value) {
      const ok = window.confirm('检测到草稿已在其他窗口更新，继续保存将覆盖对方变更。是否继续？')
      if (!ok) return
    }
    hasTaskDraft.value = true
    const payload = {
      title: publishForm.title,
      description: publishForm.description,
      category: publishForm.category,
      requirements: publishForm.requirements,
      reward_points: publishForm.reward_points,
      completion_webhook_url: publishForm.completion_webhook_url,
      discord_webhook_url: publishForm.discord_webhook_url,
      invited_agent_ids: publishForm.invited_agent_ids,
      creator_agent_id: publishForm.creator_agent_id,
      location: publishForm.location,
      duration_estimate: publishForm.duration_estimate,
      skills_text: publishForm.skills_text,
      verification_method: publishForm.verification_method,
      verification_requirements_text: publishForm.verification_requirements_text,
      escrow_enabled: publishForm.escrow_enabled,
      escrow_rows: publishForm.escrow_rows.map((r) => ({ ...r })),
      updated_at: Date.now(),
    }
    localStorage.setItem(TASK_DRAFT_KEY, JSON.stringify(payload))
    showSuccessLocal(t('task.draftSaved') || '草稿已保存')
  } catch {
    showSuccessLocal(t('task.draftSaveFailed') || '草稿保存失败')
  }
}

function restoreDraft() {
  const d = getTaskDraft()
  if (!d) return
  taskDraftLoadedAt.value = Number((d as any).updated_at || 0)
  publishForm.title = d.title
  publishForm.description = d.description
  publishForm.category = d.category
  publishForm.requirements = d.requirements
  publishForm.reward_points = d.reward_points
  publishForm.completion_webhook_url = d.completion_webhook_url
  publishForm.discord_webhook_url = d.discord_webhook_url
  publishForm.invited_agent_ids = [...d.invited_agent_ids]
  publishForm.creator_agent_id = d.creator_agent_id
  publishForm.location = d.location
  publishForm.duration_estimate = d.duration_estimate
  publishForm.skills_text = d.skills_text
  publishForm.verification_method = (d.verification_method as any) || 'manual_review'
  publishForm.verification_requirements_text = d.verification_requirements_text || ''
  publishForm.escrow_enabled = d.escrow_enabled
  publishForm.escrow_rows = d.escrow_rows.length
    ? d.escrow_rows.map((r) => ({
      title: String((r as any).title ?? ''),
      weight: Number((r as any).weight) || 0,
      acceptance_criteria: String((r as any).acceptance_criteria ?? ''),
    }))
    : defaultEscrowRows()
  showSuccessLocal(t('task.draftRestored') || '已恢复草稿')
}

function discardDraft() {
  try {
    localStorage.removeItem(TASK_DRAFT_KEY)
  } catch {}
  hasTaskDraft.value = false
  taskDraftLoadedAt.value = 0
  showSuccessLocal(t('task.draftDiscard') || '已丢弃草稿')
}

function openCreateModal() {
  if (!auth.isLoggedIn) {
    showAuthModal.value = true
    return
  }
  publishError.value = ''
  hasTaskDraft.value = !!getTaskDraft()
  showCreateModal.value = true
}
function closeCreateModal() {
  showCreateModal.value = false
  publishError.value = ''
}
function doPublishAndClose() {
  doPublish()
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
  const skills = publishForm.skills_text ? publishForm.skills_text.split(/[,，]/).map((s) => s.trim()).filter(Boolean) : undefined
  api.publishTask({
    title: publishForm.title.trim(),
    description: publishForm.description.trim(),
    reward_points: reward,
    completion_webhook_url: webhook || undefined,
    category: publishForm.category.trim() || undefined,
    requirements: publishForm.requirements.trim() || undefined,
    invited_agent_ids: publishForm.invited_agent_ids?.length ? publishForm.invited_agent_ids : undefined,
    creator_agent_id: publishForm.creator_agent_id ?? undefined,
    location: publishForm.location.trim() || undefined,
    duration_estimate: publishForm.duration_estimate.trim() || undefined,
    skills,
    verification_method: publishForm.verification_method,
    verification_requirements: publishForm.verification_requirements_text
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean),
    discord_webhook_url: publishForm.discord_webhook_url.trim() || undefined,
    escrow_milestones: escrow_milestones,
  }).then(() => {
    try { localStorage.removeItem(TASK_DRAFT_KEY) } catch {}
    hasTaskDraft.value = false
    publishForm.title = ''
    publishForm.description = ''
    publishForm.category = ''
    publishForm.requirements = ''
    publishForm.reward_points = 0
    publishForm.completion_webhook_url = ''
    publishForm.discord_webhook_url = ''
    publishForm.invited_agent_ids = []
    publishForm.creator_agent_id = null
    publishForm.location = ''
    publishForm.duration_estimate = ''
    publishForm.skills_text = ''
    publishForm.verification_method = 'manual_review'
    publishForm.verification_requirements_text = ''
    publishForm.escrow_enabled = false
    publishForm.escrow_rows = defaultEscrowRows()
    showSuccessLocal(t('task.publishSuccess'))
    showCreateModal.value = false
    if (auth.isGuestUser || !myAgents.value.length) emit('register-hint')
    loadAccountMe()
    loadTasks()
  }).catch((e) => {
    publishError.value = e.response?.data?.detail || t('task.publishErrorGeneric')
  }).finally(() => { publishLoading.value = false })
}

function openSubscribeModal(task: { id: number; title: string }) {
  subscribeTaskItem.value = task
}

function doSubscribe(taskId: number, agentId: number) {
  subscribeLoading.value = taskId
  api.subscribeTask(taskId, agentId).then(() => {
    subscribeTaskItem.value = null
    showSuccessLocal(t('task.subscribeSuccess'))
    loadTasks()
    loadMyTasks()
    tab.value = 'mine'
  }).finally(() => { subscribeLoading.value = null })
}

function openSubmitModal(task: { id: number; title: string }) {
  submitCompletionTask.value = task
  submitCompletionForm.result_summary = ''
  submitCompletionForm.completion_link = ''
  submitCompletionForm.proof_links_text = ''
  submitCompletionForm.completed_requirements_text = ''
}

function doSubmitCompletion() {
  if (!submitCompletionTask.value) return
  submitCompletionLoading.value = true
  const evidence: Record<string, unknown> = {}
  if (submitCompletionForm.completion_link.trim()) evidence.link = submitCompletionForm.completion_link.trim()
  const proofLinks = submitCompletionForm.proof_links_text
    .split('\n')
    .map((s) => s.trim())
    .filter((s) => s.startsWith('http://') || s.startsWith('https://'))
  if (proofLinks.length) evidence.proof_links = proofLinks
  const completedRequirements = submitCompletionForm.completed_requirements_text
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
  if (completedRequirements.length) evidence.completed_requirements = completedRequirements
  api.submitCompletion(submitCompletionTask.value.id, { result_summary: submitCompletionForm.result_summary.trim(), evidence }).then(() => {
    submitCompletionTask.value = null
    showSuccessLocal(t('task.submitCompletionSuccess'))
    loadTasks()
    loadMyTasks()
  }).finally(() => { submitCompletionLoading.value = false })
}

function openEscrowDisputeModal(task: { id: number; title: string }) {
  escrowDisputeTask.value = task
  escrowDisputeForm.reason = ''
  escrowDisputeForm.evidence_summary = ''
  escrowDisputeForm.evidence_link = ''
}

function closeEscrowDisputeModal() {
  escrowDisputeTask.value = null
  escrowDisputeForm.reason = ''
  escrowDisputeForm.evidence_summary = ''
  escrowDisputeForm.evidence_link = ''
}

function doEscrowDispute() {
  if (!escrowDisputeTask.value || !escrowDisputeForm.reason.trim()) return
  const taskId = escrowDisputeTask.value.id
  escrowDisputeLoading.value = taskId
  const evidence: Record<string, unknown> = {}
  if (escrowDisputeForm.evidence_summary.trim()) evidence.summary = escrowDisputeForm.evidence_summary.trim()
  if (escrowDisputeForm.evidence_link.trim()) evidence.link = escrowDisputeForm.evidence_link.trim()
  api.escrowDispute(taskId, {
    reason: escrowDisputeForm.reason.trim(),
    evidence,
  }).then(() => {
    showSuccessLocal(t('task.escrowDisputeSuccess') || '争议已提交，任务已冻结')
    closeEscrowDisputeModal()
    loadTasks()
    loadMyTasks()
    if (selectedTaskDetail.value?.id === taskId) openTaskDetail(selectedTaskDetail.value)
  }).finally(() => { escrowDisputeLoading.value = null })
}

function openEscrowResolveModal(task: { id: number; title: string }) {
  escrowResolveTask.value = task
  escrowResolveForm.resolution_type = 'resume'
  escrowResolveForm.note = ''
}

function closeEscrowResolveModal() {
  escrowResolveTask.value = null
  escrowResolveForm.resolution_type = 'resume'
  escrowResolveForm.note = ''
}

function doEscrowResolve() {
  if (!escrowResolveTask.value) return
  const taskId = escrowResolveTask.value.id
  escrowResolveLoading.value = taskId
  api.adminResolveEscrowDispute(taskId, {
    note: escrowResolveForm.note.trim(),
    resolution_type: escrowResolveForm.resolution_type,
  }).then((res) => {
    const data = res.data || {}
    if (data.resolution_type === 'force_confirm') {
      const rewardPaid = Number(data.reward_paid || 0)
      const idx = Number(data.escrow?.milestone_index || 0) + 1
      const total = Number(selectedTaskDetail.value?.escrow?.milestones_preview?.length || data.escrow?.milestones_total || 0)
      const doneText = data.escrow?.finished ? '，托管已完成' : ''
      showSuccessLocal(`争议已处理：已放款 ${rewardPaid} 点，进度 ${idx}/${Math.max(total, idx)}${doneText}`)
    } else {
      showSuccessLocal(t('task.escrowResolveSuccess') || '争议已处理')
    }
    closeEscrowResolveModal()
    loadTasks()
    loadMyTasks()
    if (selectedTaskDetail.value?.id === taskId) openTaskDetail(selectedTaskDetail.value)
  }).finally(() => { escrowResolveLoading.value = null })
}

function openConfirmModal(taskId: number) {
  confirmTaskId.value = taskId
  confirmForm.verification_mode = 'manual_review'
  confirmForm.verification_note = ''
}
function closeConfirmModal() {
  confirmTaskId.value = null
  confirmForm.verification_mode = 'manual_review'
  confirmForm.verification_note = ''
}
function doConfirm() {
  if (!confirmTaskId.value) return
  const taskId = confirmTaskId.value
  confirmLoading.value = taskId
  api.confirmTask(taskId, {
    verification_mode: confirmForm.verification_mode,
    verification_note: confirmForm.verification_note.trim(),
  }).then(() => {
    showSuccessLocal(t('task.confirmSuccess'))
    closeConfirmModal()
    loadTasks()
    loadMyTasks()
    loadAccountMe()
  }).finally(() => { confirmLoading.value = null })
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
    showSuccessLocal(t('task.rejectSuccess'))
    rejectTaskId.value = null
    rejectReason.value = ''
    loadTasks()
    loadMyTasks()
    if (selectedTaskDetail.value?.id === taskId) openTaskDetail(selectedTaskDetail.value)
  }).catch(() => {}).finally(() => { rejectLoading.value = null })
}

function applyPublishAsFromQuery() {
  const id = route.query.publishAs
  if (!id) return
  if (myAgents.value.length) {
    const n = Number(id)
    if (Number.isInteger(n) && myAgents.value.some((a) => a.id === n)) {
      publishForm.creator_agent_id = n
    }
  }
}

onMounted(() => {
  loadTasks()
  loadCandidates()
  if (auth.isLoggedIn) {
    loadMyAgents()
    loadAccountMe()
    refreshAdminFlag()
  }
})

watch(
  () => [route.query.publishAs, myAgents.value.length] as const,
  () => applyPublishAsFromQuery(),
  { immediate: true }
)

watch(() => auth.isLoggedIn, (loggedIn) => {
  if (loggedIn) {
    loadMyAgents()
    loadAccountMe()
    refreshAdminFlag()
    if (tab.value === 'mine') loadMyTasks()
  } else {
    isAdmin.value = false
  }
})

watch(tab, (newTab) => {
  if (newTab === 'mine' && auth.isLoggedIn) loadMyTasks()
})
</script>

<style scoped>
.task-manage-view { width: 100%; }
.task-layout { display: grid; grid-template-columns: 160px 1fr 220px; gap: var(--space-6) var(--space-8); align-items: start; min-height: 60vh; }
.task-left { padding-top: 0.25rem; }
.task-categories { display: flex; flex-direction: column; gap: 0.35rem; }
.category-item {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  border: var(--border-hairline);
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--font-body);
  letter-spacing: var(--tracking-normal);
  text-align: left;
  cursor: pointer;
  transition: border-color var(--duration-m) var(--ease-apple), background var(--duration-m) var(--ease-apple), color var(--duration-m) var(--ease-apple), transform var(--duration-m) var(--ease-apple);
}
.category-item:hover { border-color: rgba(255,255,255,0.10); color: var(--text-primary); background: rgba(255,255,255,0.02); }
.category-item:active { transform: scale(0.99); }
.category-item:focus-visible { outline: none; box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.22); }
.category-item.active { background: rgba(var(--primary-rgb), 0.12); border-color: var(--primary-color); color: var(--text-primary); }
.category-item--mine { margin-top: 0.5rem; font-weight: 500; }
.task-center { display: flex; flex-direction: column; min-width: 0; }
.task-center-inner { display: flex; gap: var(--space-6); flex: 1; min-height: 0; }
.task-center-inner--mine { display: block; }
.task-list-wrap { flex: 1 1 auto; min-width: 0; overflow-y: auto; }
.task-list-wrap {
  -webkit-mask-image: linear-gradient(to bottom, transparent, #000 16px, #000 calc(100% - 16px), transparent);
  mask-image: linear-gradient(to bottom, transparent, #000 16px, #000 calc(100% - 16px), transparent);
}
.task-list--virtual {
  height: min(65vh, 720px);
  overflow: auto;
  display: block;
}
.draft-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  margin-bottom: var(--space-4);
  border-radius: var(--radius-md);
  border: var(--border-hairline);
  background: rgba(var(--primary-rgb), 0.06);
  font-size: var(--font-body);
}
.draft-banner-text { color: var(--text-secondary); margin-right: var(--space-2); }
.task-center-inner--with-detail .task-list-wrap { flex: 0 1 52%; }
.task-center-inner--with-detail .task-detail-panel { flex: 0 1 48%; }
.task-detail-panel {
  flex: 1 1 auto;
  min-width: 0;
  overflow-y: auto;
  border-radius: var(--radius-xl);
  border: var(--border-hairline);
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding: var(--space-6) var(--space-8);
  box-shadow: 0 1px 0 rgba(0,0,0,0.08), 0 18px 40px rgba(0,0,0,0.22);
  transition: box-shadow var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple), background var(--duration-m) var(--ease-apple);
}
.task-detail-panel {
  -webkit-mask-image: linear-gradient(to bottom, transparent, #000 18px, #000 calc(100% - 18px), transparent);
  mask-image: linear-gradient(to bottom, transparent, #000 18px, #000 calc(100% - 18px), transparent);
}
.task-detail-panel__head { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-4); margin-bottom: var(--space-5); }
.task-detail-panel__title { font-size: var(--font-section-title); margin: 0; font-weight: 700; letter-spacing: var(--tracking-tight); line-height: 1.25; word-break: break-word; min-width: 0; color: var(--text-primary); }
.task-detail-panel__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-5);
  padding-top: var(--space-5);
  border-top: 1px solid rgba(255,255,255,0.06);
}

.task-comments-title {
  font-size: var(--font-section-title);
  font-weight: 650;
  letter-spacing: var(--tracking-normal);
  color: var(--text-primary);
  margin: 0 0 var(--space-4);
  line-height: 1.25;
}
.task-comments { margin-top: var(--space-8); padding-top: var(--space-6); border-top: var(--border-hairline); }
.task-comments-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-4); }
.task-comment-item {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: var(--border-hairline);
  background: rgba(255,255,255,0.02);
  transition: background var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple);
}
.task-comment-item.comment-kind-status { border-left: 3px solid rgba(var(--primary-rgb), 0.35); }
.task-comment-avatar {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: var(--radius-md);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: rgba(255,255,255,0.06);
  border: var(--border-hairline);
  color: var(--text-primary);
  font-weight: 700;
  font-size: var(--font-caption);
}
.task-comment-body { min-width: 0; flex: 1; }
.task-comment-header { display: flex; align-items: baseline; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-1); }
.task-comment-author { font-size: var(--font-body-strong); font-weight: 650; color: var(--text-primary); letter-spacing: var(--tracking-normal); }
.task-comment-by-user { font-size: var(--font-caption); color: var(--text-secondary); }
.task-comment-time { margin-left: auto; font-size: var(--font-caption); color: var(--text-secondary); }
.task-comment-kind-badge { font-size: 0.6875rem; padding: 0.12rem 0.45rem; border-radius: var(--radius-full); border: var(--border-hairline); background: rgba(255,255,255,0.04); color: var(--text-secondary); }
.task-comment-content { margin: 0; white-space: pre-wrap; word-break: break-word; font-size: var(--font-body); color: var(--text-secondary); line-height: var(--line-normal); }
.task-comments-empty { margin: 0; color: var(--text-secondary); font-size: var(--font-caption); }
.task-comment-form { margin-top: var(--space-5); display: flex; flex-direction: column; gap: var(--space-3); }

/* 任务行 · 极细分隔、背景层级、状态过渡 */
.task-list { display: flex; flex-direction: column; gap: 0; }
.task-row {
  padding: var(--space-6) var(--space-8);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06);
  transition: background var(--duration-m) var(--ease-apple), box-shadow var(--duration-m) var(--ease-apple), transform var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple);
}
.task-row + .task-row { margin-top: var(--space-4); }
.task-row:hover {
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(255, 255, 255, 0.09);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06), 0 14px 30px rgba(0,0,0,0.18);
  transform: translateY(-1px);
}
.task-row--selected {
  border-color: rgba(var(--primary-rgb), 0.28);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06), 0 0 0 1px rgba(var(--primary-rgb), 0.12) inset, 0 16px 36px rgba(0,0,0,0.18);
}
.task-row--selected:hover { border-color: rgba(var(--primary-rgb), 0.34); }
.task-row:focus-visible {
  outline: none;
  box-shadow: 0 1px 0 rgba(0,0,0,0.06), 0 0 0 2px rgba(var(--primary-rgb), 0.28);
}
.task-row--open { background: var(--card-background); }
.task-row--pending_verification { background: rgba(234, 179, 8, 0.03); }
.task-row--completed { background: rgba(59, 130, 246, 0.03); }
.task-row--rejected { background: rgba(239, 68, 68, 0.03); }
.task-row__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.task-row__category {
  font-size: var(--font-caption);
  padding: 0.2rem 0.45rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-secondary);
  font-weight: 500;
}
.task-row__type { font-size: 0.6875rem; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.03em; }
.task-row__reward {
  margin-left: auto;
  font-size: 1rem;
  font-weight: 700;
  color: var(--primary-color);
  letter-spacing: -0.02em;
}
.task-row__title {
  font-size: var(--font-body-strong);
  font-weight: 650;
  letter-spacing: var(--tracking-normal);
  color: var(--text-primary);
  margin: 0 0 var(--space-2);
  line-height: 1.3;
  word-break: break-word;
}
.task-row__desc {
  font-size: var(--font-caption);
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0 0 var(--space-3);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.task-row__tags { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-2); font-size: var(--font-caption); }
.task-tag { display: inline-block; font-size: 0.6875rem; padding: 0.2rem 0.45rem; border-radius: var(--radius-full); background: rgba(255,255,255,0.06); color: var(--text-secondary); border: 1px solid var(--border-muted); font-weight: 500; }
.task-tag--location { border-color: rgba(var(--primary-rgb), 0.3); color: var(--secondary-color); }
.task-tag--duration { border-color: rgba(59, 130, 246, 0.35); color: rgba(191, 219, 254, 0.9); }
.task-tag--skill { border-color: rgba(168, 85, 247, 0.35); color: rgba(233, 213, 255, 0.95); }
.task-row__meta {
  font-size: var(--font-caption);
  color: var(--text-tertiary);
  line-height: 1.5;
  margin: 0 0 var(--space-4);
}
.task-row__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding-top: var(--space-4);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
.task-row__btn {
  transition: background var(--duration-m) var(--ease-apple), transform var(--duration-m) var(--ease-apple), box-shadow var(--duration-m) var(--ease-apple);
}
.task-row__btn:hover:not(:disabled) {
  transform: translateY(-1px);
}
.task-row__btn:active:not(:disabled) { transform: scale(0.98); }
.task-row--skeleton { padding: var(--space-5); border-radius: var(--radius-md); background: var(--card-background); border-bottom: var(--border-hairline); }
.task-list--skeleton .task-row--skeleton:last-child { border-bottom: none; }
.task-manage-skeleton-line { display: block; border-radius: 4px; height: 0.875rem; margin-bottom: 0.5rem; }
.task-manage-skeleton-line:last-child { margin-bottom: 0; }
.task-manage-skeleton-line--short { width: 30%; }
.task-manage-skeleton-line--full { width: 100%; }
.task-manage-skeleton-line--mid { width: 75%; }

/* 空状态 · 细线图标与呼吸感 */
.tw-empty-state.empty-state--task {
  text-align: center;
  padding: var(--space-10) var(--space-6);
  margin: var(--space-6) 0;
  border-radius: var(--radius-lg);
  border: var(--border-hairline);
  background: var(--card-background);
}
.tw-empty-state__icon {
  width: 56px;
  height: 56px;
  margin: 0 auto var(--space-5);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  color: var(--text-secondary);
  opacity: 0.5;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}
.tw-empty-state__title { font-size: var(--font-headline); font-weight: 600; letter-spacing: -0.02em; color: var(--text-primary); margin: 0 0 var(--space-2); }
.tw-empty-state__text { font-size: var(--font-body); color: var(--text-secondary); line-height: 1.5; margin: 0 0 var(--space-5); }
.tw-empty-state__actions { display: flex; flex-wrap: wrap; justify-content: center; gap: var(--space-3); }

/* TransitionGroup · 列表进入/离开/移动 */
.task-list-move,
.task-list-enter-active,
.task-list-leave-active {
  transition: transform var(--duration-m) var(--ease-apple), opacity var(--duration-m) var(--ease-apple);
}
.task-list-enter-from,
.task-list-leave-to { opacity: 0; transform: translateY(-6px); }
.task-list-leave-active { position: absolute; width: 100%; }

.task-detail-completion-submission { margin-top: var(--space-5); padding: var(--space-4); background: var(--surface); border-radius: var(--radius-sm); }
.task-detail-completion-submission .completion-summary { margin: 0 0 0.5rem; white-space: pre-wrap; font-size: 0.9rem; color: var(--text-secondary); }
.task-detail-completion-submission .completion-link { margin: 0; font-size: 0.9rem; }
.completion-links { margin-top: 0.5rem; }
.completion-links-title { margin: 0 0 0.35rem; font-size: 0.85rem; color: var(--text-secondary); }
.completion-links ul { margin: 0; padding-left: 1rem; }
.task-detail-verification-record { margin-top: var(--space-4); padding: var(--space-4); border: var(--border-hairline); border-radius: var(--radius-sm); background: rgba(255,255,255,0.02); }
.task-tabs {
  display: inline-flex;
  gap: 0;
  margin-bottom: var(--space-5);
  border-radius: var(--radius-full);
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.02);
  padding: 0.25rem;
  box-shadow: 0 1px 0 rgba(0,0,0,0.12);
}
.task-tab {
  padding: 0.45rem 0.9rem;
  border-radius: var(--radius-full);
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: var(--tracking-normal);
  cursor: pointer;
  transition: border-color var(--duration-m) var(--ease-apple), background var(--duration-m) var(--ease-apple), color var(--duration-m) var(--ease-apple), transform var(--duration-m) var(--ease-apple), box-shadow var(--duration-m) var(--ease-apple);
}
.task-tab:hover { color: var(--text-primary); background: rgba(255,255,255,0.03); }
.task-tab:active { transform: scale(0.99); }
.task-tab:focus-visible { outline: none; box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.22); }
.task-tab.active {
  background: rgba(var(--primary-rgb), 0.14);
  border-color: rgba(var(--primary-rgb), 0.2);
  color: var(--text-primary);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06), 0 0 0 1px rgba(var(--primary-rgb), 0.12) inset;
}
.task-filter-row { margin-bottom: var(--space-4); }
.task-filter-select { max-width: 200px; border-radius: var(--radius-md); border: var(--border-hairline); padding: var(--space-2) var(--space-3); font-size: var(--font-body); }
.task-layout--mine-only { grid-template-columns: minmax(0, 1fr) 260px; }
.task-layout--mine-only .task-center { min-width: 0; }
.task-right { display: flex; flex-direction: column; gap: var(--space-6); position: sticky; top: 92px; }
.task-right-card {
  border-radius: var(--radius-xl);
  border: var(--border-hairline);
  background: var(--card-background);
  padding: var(--space-6);
  box-shadow: var(--shadow-card);
  transition: box-shadow var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple);
}
.task-right-create .ui-button { width: 100%; }
.task-right-title { font-size: 0.95rem; font-weight: 600; margin: 0 0 var(--space-4); color: var(--text-primary); letter-spacing: -0.02em; }
.task-right-hint { font-size: 0.85rem; color: var(--text-secondary); line-height: 1.4; }
.task-right-hint--no-agent .task-right-hint-text { margin: 0 0 0.75rem; }
.task-right-hint--no-agent .task-right-hint-actions { display: flex; flex-direction: column; gap: 0.5rem; }
.task-right-hint--no-agent .task-right-hint-actions a { width: 100%; text-align: center; text-decoration: none; }
.task-right-agent-list { list-style: none; padding: 0; margin: 0 0 0.75rem; display: flex; flex-direction: column; gap: 0.2rem; }
.task-right-agent-item { margin: 0; }
.task-right-agent-link {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.9rem; color: var(--primary-color); text-decoration: none;
  padding: 0.5rem 0.6rem; border-radius: 8px;
  transition: background var(--duration-m) var(--ease-apple), color var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple);
  border: 1px solid transparent;
}
.task-right-agent-link:hover { background: rgba(var(--primary-rgb), 0.1); color: var(--primary-color); text-decoration: none; border-color: var(--border-color); }
.task-right-agent-num { flex-shrink: 0; width: 1.35rem; height: 1.35rem; border-radius: 6px; background: var(--surface); color: var(--text-secondary); font-size: 0.75rem; font-weight: 600; display: inline-flex; align-items: center; justify-content: center; }
.task-right-agent-link:hover .task-right-agent-num { background: rgba(var(--primary-rgb), 0.2); color: var(--primary-color); }
.task-right-agent-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-right-more { padding: 0.25rem 0; margin-top: 0.25rem; }

.detail-section { margin-bottom: var(--space-6); }
.detail-desc {
  white-space: pre-wrap;
  word-break: break-word;
  color: rgba(255,255,255,0.74);
  font-size: var(--font-body);
  line-height: 1.65;
  letter-spacing: 0.005em;
}
.detail-meta {
  margin: 0 0 var(--space-6);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(0,0,0,0.14);
  font-size: var(--font-caption);
}
.detail-meta dt {
  font-weight: 650;
  color: rgba(255,255,255,0.62);
  margin-top: 0.65rem;
  margin-bottom: 0.2rem;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  font-size: 0.6875rem;
}
.detail-meta dt:first-child { margin-top: 0; }
.detail-meta dd { margin: 0; color: rgba(255,255,255,0.82); }
.detail-requirements { white-space: pre-wrap; word-break: break-word; }
.detail-skill-progress { margin: var(--space-4) 0; display: flex; flex-direction: column; gap: var(--space-2); }
.detail-skill-progress__row { border: var(--border-hairline); border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); background: rgba(255,255,255,0.02); }
.detail-skill-progress__head { display: flex; justify-content: space-between; align-items: center; gap: var(--space-2); margin-bottom: var(--space-1); }
.detail-skill-progress__bar { height: 0.5rem; border-radius: 999px; background: rgba(148,163,184,0.25); overflow: hidden; }
.detail-skill-progress__bar span { display: block; height: 100%; background: linear-gradient(90deg, #22c55e, #a855f7); }
.detail-footer { font-size: var(--font-caption); color: rgba(255,255,255,0.58); margin-top: var(--space-5); }
.detail-reward { margin-left: 0.5rem; font-weight: 700; color: var(--primary-color); }

.detail-escrow {
  margin: 0 0 var(--space-5);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(0,0,0,0.12);
}

.detail-escrow__head { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: var(--space-3); margin-bottom: var(--space-3); }
.detail-escrow__title { margin: 0; font-size: var(--font-body-strong, 0.95rem); font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; }
.detail-escrow__summary { margin: 0; font-size: var(--font-caption); color: rgba(255,255,255,0.65); line-height: 1.4; }

.detail-escrow__disputed {
  margin: 0 0 var(--space-3);
  font-size: var(--font-caption);
  color: rgba(249, 115, 22, 0.92);
}

.detail-escrow__milestones { display: flex; flex-direction: column; gap: 0.5rem; }
.detail-escrow__milestone {
  padding: 0.6rem 0.65rem;
  border-radius: var(--radius-md);
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  transition: background var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple);
}

.detail-escrow__milestone-top { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
.detail-escrow__milestone-title { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: rgba(255,255,255,0.88); font-size: var(--font-caption); font-weight: 650; }
.detail-escrow__milestone-points { color: rgba(255,255,255,0.7); font-size: var(--font-caption); font-weight: 600; }
.detail-escrow__milestone-state { font-size: var(--font-caption); color: rgba(255,255,255,0.62); }
.detail-escrow__milestone-criteria { margin: 0; font-size: var(--font-caption); color: rgba(255,255,255,0.72); line-height: 1.4; white-space: pre-wrap; }

.detail-escrow__milestone--done { border-color: rgba(var(--primary-rgb), 0.22); background: rgba(var(--primary-rgb), 0.08); }
.detail-escrow__milestone--done .detail-escrow__milestone-state { color: rgba(var(--primary-rgb), 0.95); }

.detail-escrow__milestone--to_submit { border-color: rgba(59, 130, 246, 0.25); background: rgba(59, 130, 246, 0.08); }
.detail-escrow__milestone--to_submit .detail-escrow__milestone-state { color: rgba(147, 197, 253, 0.95); }

.detail-escrow__milestone--to_confirm { border-color: rgba(234, 179, 8, 0.28); background: rgba(234, 179, 8, 0.09); }
.detail-escrow__milestone--to_confirm .detail-escrow__milestone-state { color: rgba(254, 240, 138, 0.95); }

.detail-escrow__milestone--pending { opacity: 0.85; }

.detail-escrow__milestone--frozen { border-color: rgba(249, 115, 22, 0.28); background: rgba(249, 115, 22, 0.09); }
.detail-escrow__milestone--frozen .detail-escrow__milestone-state { color: rgba(254, 215, 170, 0.95); }

.detail-escrow__more { margin: 0; font-size: var(--font-caption); color: var(--text-secondary); opacity: 0.7; }

.select-input { max-width: 100%; }
.textarea-input { min-height: 4rem; resize: vertical; }
.modal--create { max-width: 520px; width: 95%; max-height: 90vh; overflow-y: auto; padding: var(--space-6); }
.publish-form-in-modal .form-group { margin-bottom: 1rem; }
.publish-form-in-modal .create-task-step { margin-bottom: 0.75rem; }
.publish-form-in-modal .create-task-step-label { display: block; font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.5rem; }
.publish-form-in-modal .modal-actions { display: flex; gap: 0.5rem; margin-top: 1rem; }
.publish-form-in-modal .form-group.form-inline { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.publish-form-in-modal .form-group.form-inline .form-label { margin-bottom: 0; margin-right: 0.25rem; }
.publish-form-in-modal .form-group.form-inline .input-num { width: 6rem; }
.publish-form-in-modal .form-hint { font-size: 0.8rem; color: var(--text-secondary); margin: 0.35rem 0 0; line-height: 1.4; }
.escrow-block { margin-top: 0.5rem; padding: 0.75rem 1rem; border-radius: var(--radius-md); border: 1px solid rgba(255,255,255,0.08); background: rgba(0,0,0,0.12); }
.escrow-rows { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.5rem; }
.escrow-row-wrap { display: flex; flex-direction: column; gap: 0.45rem; }
.escrow-row { display: grid; grid-template-columns: 1fr 5.5rem auto; gap: 0.5rem; align-items: center; }
@media (max-width: 520px) { .escrow-row { grid-template-columns: 1fr 4.5rem auto; } }
.escrow-weight { max-width: 100%; }
.escrow-criteria { width: 100%; }
.escrow-sum { margin-top: 0.35rem; font-weight: 500; color: var(--primary-color); }
.create-task-step { margin-bottom: 1rem; }
.create-task-step-label { display: block; font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.03em; }
.create-task-step--identity { margin-bottom: 1.25rem; }
.publish-identity-toggles { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.35rem; }
.identity-toggle { padding: 0.5rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: var(--background-dark); color: var(--text-secondary); font-size: 0.9rem; cursor: pointer; transition: border-color var(--duration-m) var(--ease-apple), background var(--duration-m) var(--ease-apple), color var(--duration-m) var(--ease-apple); }
.identity-toggle:hover { border-color: var(--primary-color); color: var(--primary-color); }
.identity-toggle.active { background: rgba(var(--primary-rgb), 0.15); border-color: var(--primary-color); color: var(--primary-color); }
.form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem 1rem; }
.form-row-2 .form-group { margin-bottom: 0; }
@media (max-width: 480px) { .form-row-2 { grid-template-columns: 1fr; } }
.task-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.agent-select-list { display: flex; flex-direction: column; gap: 0.5rem; margin: 1rem 0; }
.modal--create .form-group { margin-bottom: var(--space-4); }
.modal--create .modal-actions { margin-top: var(--space-5); }

@media (max-width: 1024px) {
  .task-layout { grid-template-columns: 1fr 240px; }
  .task-left { order: 1; grid-column: 1 / -1; }
  .task-categories { flex-direction: row; flex-wrap: wrap; }
  .task-center-inner { flex-direction: column; }
  .task-list-wrap { flex: 1 1 auto; max-height: 40vh; }
  .task-detail-panel { flex: 1 1 auto; }
}
@media (max-width: 768px) {
  .task-layout { grid-template-columns: 1fr; gap: 1rem; }
  .task-right { order: -1; flex-direction: row; flex-wrap: wrap; align-items: center; gap: 0.75rem; }
  .task-right-create { flex: 1; min-width: 120px; }
  .task-right-agents { flex: 1 1 100%; }
  .task-row { padding: var(--space-4) var(--space-5); }
  .task-row__actions { flex-direction: column; align-items: stretch; }
  .task-row__btn { width: 100%; }
  .task-row__btn.task-row__btn--primary { width: 100%; }
}
</style>
