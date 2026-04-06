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
            <button type="button" class="task-tab" :class="{ active: tab === 'published' }" @click="tab = 'published'">{{ t('taskManage.tabPublished') || '我发布的' }}</button>
            <button
              v-if="showDisputesTab"
              type="button"
              class="task-tab task-tab--disputes"
              :class="{ active: tab === 'disputes' }"
              @click="goDisputesTab"
            >{{ t('taskManage.tabDisputes') }}<span v-if="disputesTabBadgeCount" class="task-tab__count mono">({{ disputesTabBadgeCount }})</span></button>
          </div>
          <div v-if="pulseFilterBannerText" class="pulse-filter-banner">
            <span>{{ pulseFilterBannerText }}</span>
            <Button size="sm" type="button" variant="secondary" @click="clearPulseQuery">{{ t('taskManage.pulseFilterClear') || '清除筛选' }}</Button>
          </div>
          <div v-if="tab === 'available' && relatedSkillFilter" class="related-skill-banner">
            <p class="related-skill-banner__text">
              {{ t('taskManage.relatedSkillFilterHint', { token: relatedSkillFilter.token || '—' }) }}
            </p>
            <Button size="sm" type="button" variant="secondary" @click="clearRelatedSkillFilter">
              {{ t('taskManage.clearRelatedSkillFilter') || '显示全部任务' }}
            </Button>
          </div>
          <!-- NOTE: translated comment in English. -->
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
                    <p v-if="item.data!.related_skill?.skill_token" class="task-row__meta task-row__meta--skill">
                      Skill: {{ item.data!.related_skill?.skill_name || item.data!.related_skill?.skill_token }}
                    </p>
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

          <!-- NOTE: translated comment in English. -->
          <template v-else-if="tab === 'mine'">
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
                  <div v-if="item.data!.location || item.data!.duration_estimate || (getTaskSkills(item.data!).length) || item.data!.related_skill?.skill_token" class="task-row__tags">
                    <span v-if="item.data!.location" class="task-tag task-tag--location">{{ item.data!.location }}</span>
                    <span v-if="item.data!.duration_estimate" class="task-tag task-tag--duration">{{ item.data!.duration_estimate }}</span>
                    <span v-for="s in getTaskSkills(item.data!)" :key="s" class="task-tag task-tag--skill">{{ s }}</span>
                    <span v-if="item.data!.related_skill?.skill_token" class="task-tag task-tag--skill-related">
                      Skill: {{ item.data!.related_skill?.skill_name || item.data!.related_skill?.skill_token }}
                    </span>
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
              v-if="!myTasksLoading && !mineFilteredTasks.length"
              :title="mineEmptyTitle"
              :description="mineEmptyDescription"
              illustration-src="/assets/illustrations/market-empty.svg"
            >
              <template #actions>
                <Button :as="RouterLink" to="/">{{ t('taskManage.goAccept') || '去接取' }}</Button>
              </template>
            </EmptyState>
            </template>
          </template>

          <template v-else-if="tab === 'published'">
            <EmptyState
              v-if="!auth.isLoggedIn"
              :title="t('taskManage.loginToSeePublished') || '请先登录查看我发布的任务'"
              :description="t('taskManage.emptyTaskHint') || '登录后可管理发布与验收'"
              illustration-src="/assets/illustrations/market-empty.svg"
              size="lg"
            >
              <template #actions>
                <Button type="button" @click="showAuthModal = true">{{ t('common.loginOrRegister') }}</Button>
              </template>
            </EmptyState>
            <template v-else>
              <div v-if="publishedTasksLoading" class="task-list task-list--skeleton">
                <div v-for="i in 4" :key="'p' + i" class="task-row task-row--skeleton">
                  <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--short"></div>
                  <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--full"></div>
                  <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--mid"></div>
                </div>
              </div>
              <div v-else class="task-list task-list--virtual" v-bind="virtualPublished.containerProps">
                <div v-bind="virtualPublished.wrapperProps">
                  <article
                    v-for="item in virtualPublishedItems"
                    :key="item.index"
                    :class="cn('task-row', 'task-row--published', `task-row--${item.data!.status}`, { 'task-row--selected': selectedTaskDetail?.id === item.data!.id })"
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
                    <p class="task-row__meta">
                      <span v-if="item.data!.agent_name">{{ t('task.acceptor') || '接取者' }}：{{ item.data!.agent_name }}</span>
                      <span v-else class="hint-inline">{{ t('taskManage.publishedNoAgent') || '尚未接取' }}</span>
                      <span v-if="item.data!.subscription_count != null"> · {{ item.data!.subscription_count }}{{ t('task.subscribers') }}</span>
                    </p>
                    <div class="task-row__actions" @click.stop>
                      <Button size="sm" variant="ghost" type="button" class="task-row__btn" @click="openTaskDetail(item.data!)">{{ t('task.viewDetail') }}</Button>
                      <div class="task-actions" @click.stop>
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
                v-if="!publishedTasksLoading && !publishedFilteredTasks.length"
                :title="publishedEmptyTitle"
                :description="publishedEmptyDescription"
                illustration-src="/assets/illustrations/market-empty.svg"
              >
                <template #actions>
                  <Button :as="RouterLink" to="/" variant="secondary">{{ t('common.home') }}</Button>
                </template>
              </EmptyState>
            </template>
          </template>

          <template v-else-if="tab === 'disputes'">
            <EmptyState
              v-if="!auth.isLoggedIn"
              :title="t('taskManage.loginToSeeDisputes') || '请先登录查看争议任务'"
              :description="t('taskManage.emptyTaskHint') || ''"
              illustration-src="/assets/illustrations/market-empty.svg"
              size="lg"
            >
              <template #actions>
                <Button type="button" @click="showAuthModal = true">{{ t('common.loginOrRegister') }}</Button>
              </template>
            </EmptyState>
            <template v-else>
              <p v-if="disputedMergedCount" class="disputes-merge-hint">{{ t('taskManage.disputesMergeHint') }}</p>
              <div v-if="disputesTabLoading" class="task-list task-list--skeleton">
                <div v-for="i in 4" :key="'d' + i" class="task-row task-row--skeleton">
                  <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--short"></div>
                  <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--full"></div>
                  <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--mid"></div>
                </div>
              </div>
              <div v-else class="task-list task-list--virtual" v-bind="virtualDisputes.containerProps">
                <div v-bind="virtualDisputes.wrapperProps">
                  <article
                    v-for="item in virtualDisputesItems"
                    :key="item.index"
                    :class="cn('task-row', 'task-row--dispute', `task-row--${item.data!.status}`, { 'task-row--selected': selectedTaskDetail?.id === item.data!.id })"
                    role="button"
                    tabindex="0"
                    @click="openTaskDetail(item.data!)"
                    @keydown.enter.prevent="openTaskDetail(item.data!)"
                    @keydown.space.prevent="openTaskDetail(item.data!)"
                  >
                    <div class="task-row__head">
                      <span class="task-row__dispute-role">{{ disputeRoleLabel(item.data!.id) }}</span>
                      <span v-if="item.data!.category" class="task-row__category">{{ taskCategoryLabel(item.data!.category) }}</span>
                      <span :class="taskStatusPillClass(item.data!.status)">{{ t('status.' + item.data!.status) || item.data!.status }}</span>
                      <span v-if="item.data!.reward_points" class="task-row__reward mono">{{ t('task.reward', { n: item.data!.reward_points }) }}</span>
                    </div>
                    <h3 class="task-row__title">{{ item.data!.title }}</h3>
                    <p class="task-row__desc">{{ (item.data!.description || t('common.noDescription')).slice(0, 120) }}{{ (item.data!.description || '').length > 120 ? '…' : '' }}</p>
                    <p class="task-row__meta">
                      {{ t('task.publisher') }}：{{ item.data!.publisher_name }}
                      <span v-if="item.data!.agent_name"> · {{ t('task.acceptor') || '接取者' }}：{{ item.data!.agent_name }}</span>
                    </p>
                    <div class="task-row__actions" @click.stop>
                      <Button size="sm" variant="ghost" type="button" class="task-row__btn" @click="openTaskDetail(item.data!)">{{ t('task.viewDetail') }}</Button>
                    </div>
                  </article>
                </div>
              </div>
              <EmptyState
                v-if="!disputesTabLoading && !disputedMergedTasks.length"
                :title="t('taskManage.disputesEmptyTitle') || '暂无争议任务'"
                :description="t('taskManage.disputesEmptyDesc') || '当前没有处于争议状态的任务'"
                illustration-src="/assets/illustrations/market-empty.svg"
              />
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
              <dl class="detail-meta" v-if="selectedTaskDetail.category || selectedTaskDetail.requirements || selectedTaskDetail.duration_estimate || (getTaskSkills(selectedTaskDetail).length) || selectedTaskDetail.location || selectedTaskDetail.verification_method || selectedTaskDetail.related_skill?.skill_token">
                <template v-if="selectedTaskDetail.category"><dt>{{ t('task.detailCategory') }}</dt><dd>{{ taskCategoryLabel(selectedTaskDetail.category) }}</dd></template>
                <template v-if="selectedTaskDetail.requirements"><dt>{{ t('task.detailRequirements') }}</dt><dd class="detail-requirements">{{ selectedTaskDetail.requirements }}</dd></template>
                <template v-if="selectedTaskDetail.duration_estimate"><dt>{{ t('task.detailDuration') }}</dt><dd>{{ selectedTaskDetail.duration_estimate }}</dd></template>
                <template v-if="getTaskSkills(selectedTaskDetail).length"><dt>{{ t('task.detailSkills') }}</dt><dd><span v-for="s in getTaskSkills(selectedTaskDetail)" :key="s" class="task-tag task-tag--skill">{{ s }}</span></dd></template>
                <template v-if="selectedTaskDetail.related_skill?.skill_token">
                  <dt>关联 Skill</dt>
                  <dd>
                    <a
                      v-if="selectedTaskDetail.related_skill?.download_skill_url"
                      :href="selectedTaskDetail.related_skill.download_skill_url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="detail-related-skill-link"
                    >
                      {{ selectedTaskDetail.related_skill?.skill_name || selectedTaskDetail.related_skill?.skill_token }}
                    </a>
                    <span v-else class="mono">{{ selectedTaskDetail.related_skill?.skill_name || selectedTaskDetail.related_skill?.skill_token }}</span>
                  </dd>
                </template>
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
                <p v-if="selectedTaskDetail.escrow.disputed" class="detail-escrow__sla hint">{{ t('task.escrowDisputeSla') }}</p>
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
              <div v-if="selectedTaskDetail.reward_points && selectedTaskDetail.payment_breakdown" class="task-payment-panel">
                <h4 class="task-comments-title">{{ t('task.paymentBreakdownTitle') }}</h4>
                <ul class="task-payment-list">
                  <li>{{ t('task.paymentReward') }}：<span class="mono">{{ selectedTaskDetail.payment_breakdown.reward_points }}</span></li>
                  <li>{{ t('task.paymentCommission') }}（{{ (selectedTaskDetail.payment_breakdown.commission_rate * 100).toFixed(0) }}%）：<span class="mono">{{ selectedTaskDetail.payment_breakdown.commission_points }}</span></li>
                  <li>{{ t('task.paymentNet') }}：<span class="mono">{{ selectedTaskDetail.payment_breakdown.executor_net_points }}</span></li>
                </ul>
                <ul v-if="selectedTaskDetail.payment_breakdown.transactions?.length" class="task-payment-tx">
                  <li v-for="(tx, ti) in selectedTaskDetail.payment_breakdown.transactions" :key="ti" class="mono text-xs">{{ tx.amount }} · {{ tx.remark }}</li>
                </ul>
              </div>
              <div v-if="selectedTaskDetail.timeline?.length" class="task-timeline-panel">
                <h4 class="task-comments-title">{{ t('task.flowTimelineTitle') }}</h4>
                <ul class="task-timeline-list">
                  <li v-for="(ev, ei) in selectedTaskDetail.timeline" :key="ei" class="task-timeline-item">
                    <span class="task-timeline-time mono">{{ formatCommentTime(ev.at) }}</span>
                    <span class="task-timeline-summary">{{ ev.summary }}</span>
                  </li>
                </ul>
              </div>
              <div v-if="selectedTaskDetail.rejection_history?.length" class="task-rejection-history">
                <h4 class="task-comments-title">{{ t('task.rejectionHistoryTitle') }}</h4>
                <details v-for="(rh, ri) in selectedTaskDetail.rejection_history" :key="ri" class="task-rejection-details">
                  <summary>{{ t('task.rejectionRound') }} {{ ri + 1 }} · {{ formatCommentTime(rh.at) }}</summary>
                  <p class="task-rejection-reason">{{ rh.reason }}</p>
                </details>
              </div>
              <p v-if="selectedTaskDetail.status === 'pending_verification' && selectedTaskDetail.verification_deadline_at" class="hint task-verify-hint">
                {{ t('task.verificationWindowHint', { h: selectedTaskDetail.verification_hours ?? 6 }) }}
                · {{ t('task.verificationDeadlineLabel') }}：{{ formatCommentTime(selectedTaskDetail.verification_deadline_at) }}
              </p>
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
                  <Button
                    v-if="!selectedTaskDetail.verification_extend_used"
                    size="sm"
                    variant="ghost"
                    :disabled="extendVerificationLoading === selectedTaskDetail.id"
                    @click="runExtendVerification(selectedTaskDetail)"
                  >{{ t('task.extendVerification') }}</Button>
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
              <div v-if="selectedTaskDetail && canA2aTask(selectedTaskDetail)" class="detail-a2a-sync">
                <h4 class="task-comments-title">{{ t('task.a2aSyncTitle') || 'A2A 任务同步' }}</h4>
                <p class="hint detail-a2a-sync__hint">{{ t('task.a2aSyncHint') || '与 GET /a2a/tasks/{id} 一致，便于 Agent 与发布方/接取方对齐状态。' }}</p>
                <div v-if="a2aSyncLoading" class="loading"><div class="spinner"></div></div>
                <template v-else-if="a2aSync">
                  <dl class="detail-a2a-sync__dl">
                    <template v-if="a2aSync.executor_agent_name != null && String(a2aSync.executor_agent_name)">
                      <dt>{{ t('task.a2aFieldExecutor') || '执行 Agent' }}</dt>
                      <dd>{{ a2aSync.executor_agent_name }}</dd>
                    </template>
                    <dt>{{ t('task.a2aFieldStatus') || '状态' }}</dt>
                    <dd><span :class="taskStatusPillClass(String(a2aSync.status || ''))">{{ t('status.' + String(a2aSync.status || '')) || String(a2aSync.status || '') }}</span></dd>
                    <dt>{{ t('task.a2aFieldReward') || '奖励（点）' }}</dt>
                    <dd class="mono">{{ Number(a2aSync.reward_points) || 0 }}</dd>
                    <dt>{{ t('task.a2aFieldSubmitted') || '提交完成时间' }}</dt>
                    <dd class="mono">{{ formatA2aTime(a2aSync.submitted_at) }}</dd>
                    <dt>{{ t('task.a2aFieldDeadline') || '验收截止时间' }}</dt>
                    <dd class="mono">{{ formatA2aTime(a2aSync.verification_deadline_at) }}</dd>
                  </dl>
                  <Button size="sm" type="button" variant="secondary" @click="copyA2aSyncJson">{{ t('task.a2aCopyPayload') || '复制 JSON（供 Agent）' }}</Button>
                </template>
              </div>
              <div class="detail-verification-chain">
                <h4 class="task-comments-title">{{ t('task.verificationRecord') || '验收记录' }} / Chain</h4>
                <Button
                  size="sm"
                  type="button"
                  variant="secondary"
                  :disabled="verificationChainLoading"
                  @click="loadVerificationChain"
                >{{ verificationChainLoading ? 'Loading...' : 'Load verification chain' }}</Button>
                <div v-if="verificationChainData" class="verification-chain-cards">
                  <div class="verification-chain-card">
                    <p class="mono">Declaration</p>
                    <p class="hint">Method: {{ verificationChainData.declaration?.verification_method || '-' }}</p>
                    <p class="hint">Requirements: {{ (verificationChainData.declaration?.verification_requirements || []).length }}</p>
                  </div>
                  <div class="verification-chain-card">
                    <p class="mono">Sandbox</p>
                    <p class="hint">Preflight ok: {{ verificationChainData.sandbox?.ok ? 'yes' : 'no' }}</p>
                    <p class="hint">Warnings: {{ verificationChainData.sandbox?.warnings ?? 0 }}</p>
                  </div>
                  <div class="verification-chain-card">
                    <p class="mono">Cross</p>
                    <p class="hint">Status: {{ verificationChainData.cross?.status || '-' }}</p>
                    <p class="hint">Rejected: {{ verificationChainData.cross?.rejection_reason ? 'yes' : 'no' }}</p>
                  </div>
                </div>
                <pre v-if="verificationChainJson" class="account-json-pre">{{ verificationChainJson }}</pre>
              </div>
              <div v-if="auth.isLoggedIn && selectedTaskDetail.owner_id === auth.userId" class="detail-workflow-dag">
                <h4 class="task-comments-title">Workflow DAG</h4>
                <p class="hint">可视化编辑节点与依赖关系（from -> to）。</p>
                <div class="workflow-editor">
                  <div class="workflow-editor__col">
                    <div class="workflow-editor__head">
                      <strong>节点</strong>
                      <Button size="sm" type="button" variant="secondary" @click="addWorkflowNode">+ 节点</Button>
                    </div>
                    <div v-for="(nid, idx) in workflowNodes" :key="'n-' + idx" class="workflow-row">
                      <input v-model.number="workflowNodes[idx]" type="number" min="1" class="input" />
                      <Button size="sm" type="button" variant="ghost" @click="removeWorkflowNode(idx)">移除</Button>
                    </div>
                  </div>
                  <div class="workflow-editor__col">
                    <div class="workflow-editor__head">
                      <strong>依赖边</strong>
                      <Button size="sm" type="button" variant="secondary" @click="addWorkflowEdge">+ 依赖</Button>
                    </div>
                    <div v-for="(e, idx) in workflowEdges" :key="'e-' + idx" class="workflow-row workflow-row--edge">
                      <select v-model.number="e.from" class="input select-input">
                        <option :value="null">from</option>
                        <option v-for="n in workflowNodeOptions" :key="'f-' + n" :value="n">{{ n }}</option>
                      </select>
                      <span class="mono">→</span>
                      <select v-model.number="e.to" class="input select-input">
                        <option :value="null">to</option>
                        <option v-for="n in workflowNodeOptions" :key="'t-' + n" :value="n">{{ n }}</option>
                      </select>
                      <Button size="sm" type="button" variant="ghost" @click="removeWorkflowEdge(idx)">移除</Button>
                    </div>
                  </div>
                </div>
                <p v-if="workflowValidationError" class="error-msg">{{ workflowValidationError }}</p>
                <div class="memory-search-row">
                  <Button size="sm" type="button" variant="secondary" :disabled="workflowLoading || !!workflowValidationError" @click="planWorkflowNow">规划校验</Button>
                  <Button size="sm" type="button" :disabled="workflowLoading || !selectedTaskDetail || !!workflowValidationError" @click="attachWorkflowNow">绑定到任务</Button>
                  <Button size="sm" type="button" variant="ghost" :disabled="workflowLoading || !selectedTaskDetail" @click="loadWorkflowNow">刷新</Button>
                </div>
                <pre v-if="workflowJson" class="account-json-pre">{{ workflowJson }}</pre>
              </div>
              <div class="task-comments">
                <h4 class="task-comments-title">{{ canA2aTask(selectedTaskDetail) ? (t('task.a2aCommentsTitle') || '协作留言 (A2A)') : (t('task.comments') || '评论') }}</h4>
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
                      <MarkdownHtml class="task-comment-content" :content="c.content" />
                    </div>
                  </li>
                </ul>
                <p v-if="!taskComments.length && !taskCommentsLoading" class="task-comments-empty">{{ t('task.noComments') }}</p>
                <div v-if="auth.isLoggedIn" class="task-comment-form">
                  <div v-if="selectedTaskDetail && canA2aTask(selectedTaskDetail)" class="task-comment-a2a-opts">
                    <div class="task-comment-a2a-row">
                      <label class="task-comment-a2a-label">{{ t('task.commentIdentity') || '发言身份' }}</label>
                      <select v-model="commentAgentId" class="input select-input task-comment-a2a-select">
                        <option value="">{{ t('task.commentAsSelf') || '本人' }}</option>
                        <option v-for="a in myAgents" :key="a.id" :value="String(a.id)">{{ a.name }}</option>
                      </select>
                    </div>
                    <div class="task-comment-a2a-row">
                      <label class="task-comment-a2a-label">{{ t('task.commentKind') || '类型' }}</label>
                      <select v-model="commentKind" class="input select-input task-comment-a2a-select">
                        <option value="message">{{ t('task.commentKindMessage') || '普通消息' }}</option>
                        <option value="status_update">{{ t('task.commentKindStatus') || '状态同步' }}</option>
                      </select>
                    </div>
                  </div>
                  <Textarea v-model="newCommentContent" rows="2" :placeholder="t('task.writeComment')" />
                  <Button size="sm" type="button" :disabled="postCommentLoading || !newCommentContent.trim()" @click="postComment">{{ t('task.postComment') }}</Button>
                </div>
                <p v-else class="hint">{{ t('task.loginToComment') }}</p>
              </div>
            </template>
          </div>
        </div>
      </section>

      <!-- NOTE: translated comment in English. -->
      <aside class="task-right">
        <div class="task-right-card task-right-create">
          <Button type="button" class="w-full" @click="openCreateModal">
            {{ t('task.publish') || '发布任务' }}
          </Button>
        </div>
              <div
                v-if="selectedTaskDetail && selectedTaskDetail.status === 'pending_verification' && selectedTaskDetail.owner_id === auth.userId"
                class="task-verification-ops-hint"
              >
                <p class="hint">
                  {{ t('task.verifyReleaseHint') || 'Approving now will release reward to the executor.' }}
                  <span class="mono">{{ verificationReleaseText(selectedTaskDetail) }}</span>
                </p>
                <p class="hint">
                  {{ t('task.verifyDeadlineHint') || 'Auto-approval countdown:' }}
                  <span class="mono">{{ verificationDeadlineCountdown(selectedTaskDetail.verification_deadline_at) }}</span>
                </p>
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

    <!-- NOTE: translated comment in English. -->
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
          <div class="form-group" v-if="auth.isLoggedIn && myPublishedSkills.length">
            <label class="form-label" for="publish-related-skill">关联已上传 Skill（可选）</label>
            <select id="publish-related-skill" v-model="publishForm.related_skill_token" class="input select-input">
              <option value="">自动（按发布 Agent 绑定 skill token）</option>
              <option v-for="s in myPublishedSkills" :key="s.id" :value="s.skill_token">
                {{ s.name }} · {{ s.skill_token }}
              </option>
            </select>
            <p class="form-hint">关联后，该任务会在 Skill 市场详情中可见。</p>
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

    <!-- NOTE: translated comment in English. -->
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

    <!-- NOTE: translated comment in English. -->
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

    <!-- NOTE: translated comment in English. -->
    <div v-if="rejectTaskId" class="modal-mask" @click.self="rejectTaskId = null; rejectReason = ''">
      <div class="modal">
        <h3>{{ t('task.rejectTitle') || '拒绝验收' }}</h3>
        <p class="hint">{{ t('task.rejectHint') || '请填写拒绝理由，以便接取者改进（将作为强化学习反馈）。' }}</p>
        <div class="form">
          <div class="reject-quick-templates">
            <button
              v-for="tpl in rejectReasonTemplates"
              :key="tpl"
              type="button"
              class="reject-quick-templates__btn"
              @click="rejectReason = tpl"
            >{{ tpl }}</button>
          </div>
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

    <!-- NOTE: translated comment in English. -->
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
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useVirtualList } from '@vueuse/core'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import EmptyState from '../components/EmptyState.vue'
import MarkdownHtml from '../components/MarkdownHtml.vue'
import { cn } from '../lib/utils'
import { safeT } from '../i18n'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'
import type { TaskListItem, TaskCommentItem } from '../api'
import { canA2aTaskParams } from '../utils/taskA2a'

const route = useRoute()
const router = useRouter()
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

const tab = ref<'available' | 'mine' | 'published' | 'disputes'>('available')
const tasks = ref<TaskListItem[]>([])
const tasksLoading = ref(false)
const myTasks = ref<TaskListItem[]>([])
const myTasksLoading = ref(false)
const publishedTasks = ref<TaskListItem[]>([])
const publishedTasksLoading = ref(false)

function normalizePulse(q: unknown): string {
  const raw = Array.isArray(q) ? q[0] : q
  return typeof raw === 'string' ? raw : ''
}
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
  related_skill_token: string
  verification_method: 'manual_review' | 'proof_link' | 'checklist' | 'hybrid'
  verification_requirements_text: string
  escrow_enabled: boolean
  escrow_rows: EscrowRow[]
  verification_hours: number
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
  related_skill_token: '',
  verification_method: 'manual_review',
  verification_requirements_text: '',
  escrow_enabled: false,
  escrow_rows: defaultEscrowRows(),
  verification_hours: 6,
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
const myPublishedSkills = ref<Array<{ id: number; name: string; skill_token: string }>>([])
const accountCredits = ref(0)
/** 与 /account/me task_pulse.disputes 同步，用于在无 pulse 参数时仍显示「争议」入口 */
const taskPulseDisputes = ref(0)
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
const extendVerificationLoading = ref<number | null>(null)
const rejectLoading = ref<number | null>(null)
const rejectTaskId = ref<number | null>(null)
const rejectReason = ref('')
const rejectReasonTemplates = [
  'Acceptance checklist not fully satisfied.',
  'Evidence link is missing or inaccessible.',
  'Result summary is incomplete and needs clarification.',
]
const confirmTaskId = ref<number | null>(null)
const confirmForm = reactive({ verification_mode: 'manual_review', verification_note: '' })
const categoryFilter = ref('')
const relatedSkillFilter = ref<{ id: number; token: string } | null>(null)
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

const mineFilteredTasks = computed(() => {
  const list = myTasks.value
  const p = normalizePulse(route.query.pulse)
  if (tab.value !== 'mine') return list
  if (p === 'submit') return list.filter((x) => x.status === 'open' || x.status === 'in_progress')
  if (p === 'wait') return list.filter((x) => x.status === 'pending_verification')
  if (p === 'dispute') return list.filter((x) => x.status === 'disputed')
  return list
})

const publishedFilteredTasks = computed(() => {
  const list = publishedTasks.value
  const p = normalizePulse(route.query.pulse)
  if (tab.value !== 'published') return list
  if (p === 'verify') return list.filter((x) => x.status === 'pending_verification')
  if (p === 'dispute') return list.filter((x) => x.status === 'disputed')
  return list
})

const pulseFilterBannerText = computed(() => {
  const p = normalizePulse(route.query.pulse)
  if (!p || route.query.relatedSkillId) return ''
  const keys: Record<string, string> = {
    verify: 'taskManage.pulseFilterBannerVerify',
    submit: 'taskManage.pulseFilterBannerSubmit',
    wait: 'taskManage.pulseFilterBannerWait',
    dispute: 'taskManage.pulseFilterBannerDispute',
  }
  const k = keys[p]
  return k ? String(t(k)) : ''
})

const mineEmptyTitle = computed(() => {
  if (myTasks.value.length && !mineFilteredTasks.value.length) {
    return String(t('taskManage.mineEmptyFilteredTitle') || '当前筛选下暂无任务')
  }
  return String(t('taskManage.noMyTasks') || '暂无接取的任务')
})
const mineEmptyDescription = computed(() => {
  if (myTasks.value.length && !mineFilteredTasks.value.length) {
    return String(t('taskManage.mineEmptyFilteredDesc') || '可点击「清除筛选」或切换标签')
  }
  return String(t('taskManage.goAcceptHint') || '前往首页或可接取任务列表接取第一个任务')
})

const publishedEmptyTitle = computed(() => {
  if (publishedTasks.value.length && !publishedFilteredTasks.value.length) {
    return String(t('taskManage.publishedEmptyFilteredTitle') || '当前筛选下暂无任务')
  }
  return String(t('taskManage.noPublishedTasks') || '暂无发布的任务')
})
const publishedEmptyDescription = computed(() => {
  if (publishedTasks.value.length && !publishedFilteredTasks.value.length) {
    return String(t('taskManage.publishedEmptyFilteredDesc') || '可清除筛选或前往首页发布')
  }
  return String(t('taskManage.publishedEmptyHint') || '在首页或本页发布任务后，将在此管理验收与结算')
})

const showDisputesTab = computed(
  () => normalizePulse(route.query.pulse) === 'dispute' || taskPulseDisputes.value > 0,
)

const disputedMergedEntries = computed(() => {
  const seen = new Set<number>()
  const out: Array<{ task: TaskListItem; role: 'assignee' | 'publisher' }> = []
  for (const task of myTasks.value) {
    if (task.status !== 'disputed') continue
    if (seen.has(task.id)) continue
    seen.add(task.id)
    out.push({ task, role: 'assignee' })
  }
  for (const task of publishedTasks.value) {
    if (task.status !== 'disputed') continue
    if (seen.has(task.id)) continue
    seen.add(task.id)
    out.push({ task, role: 'publisher' })
  }
  return out
})

const disputedMergedTasks = computed(() => disputedMergedEntries.value.map((e) => e.task))
const disputedMergedCount = computed(() => disputedMergedEntries.value.length)

/** 标签角标：列表已加载时优先用合并条数，否则用服务端 task_pulse.disputes */
const disputesTabBadgeCount = computed(() => {
  const merged = disputedMergedEntries.value.length
  if (merged > 0) return merged
  return taskPulseDisputes.value
})

const disputesTabLoading = computed(() => {
  if (tab.value !== 'disputes') return false
  return myTasksLoading.value || publishedTasksLoading.value
})

function disputeRoleLabel(taskId: number): string {
  const e = disputedMergedEntries.value.find((x) => x.task.id === taskId)
  if (!e) return ''
  return e.role === 'assignee'
    ? String(t('taskManage.disputeRoleAssignee') || '接取方')
    : String(t('taskManage.disputeRolePublisher') || '发布方')
}

const TASK_ROW_ITEM_HEIGHT = 168
const virtualAvailable = useVirtualList(filteredTasks, { itemHeight: TASK_ROW_ITEM_HEIGHT, overscan: 6 })
const virtualMine = useVirtualList(mineFilteredTasks, { itemHeight: TASK_ROW_ITEM_HEIGHT, overscan: 6 })
const virtualPublished = useVirtualList(publishedFilteredTasks, { itemHeight: TASK_ROW_ITEM_HEIGHT, overscan: 6 })
const virtualDisputes = useVirtualList(disputedMergedTasks, { itemHeight: TASK_ROW_ITEM_HEIGHT, overscan: 6 })
const virtualAvailableItems = computed(() => (virtualAvailable.list.value || []).filter((x) => !!x.data))
const virtualMineItems = computed(() => (virtualMine.list.value || []).filter((x) => !!x.data))
const virtualPublishedItems = computed(() => (virtualPublished.list.value || []).filter((x) => !!x.data))
const virtualDisputesItems = computed(() => (virtualDisputes.list.value || []).filter((x) => !!x.data))

function clearPulseQuery() {
  const q = { ...route.query } as Record<string, string | string[] | undefined>
  delete q.pulse
  if (tab.value === 'disputes') tab.value = 'mine'
  router.replace({ path: '/tasks', query: q })
}

/** 进入争议合并视图并写入 URL，便于刷新与分享 */
function goDisputesTab() {
  const q = { ...route.query } as Record<string, string | string[] | undefined>
  q.pulse = 'dispute'
  router.replace({ path: '/tasks', query: q })
}

function applyPulseFromQuery() {
  if (route.query.relatedSkillId) return
  const p = normalizePulse(route.query.pulse)
  if (!p && tab.value === 'disputes') tab.value = 'mine'
  if (!p || !auth.isLoggedIn) return
  if (p === 'verify') {
    tab.value = 'published'
    loadPublishedTasks()
    return
  }
  if (p === 'submit' || p === 'wait') {
    tab.value = 'mine'
    loadMyTasks()
    return
  }
  if (p === 'dispute') {
    tab.value = 'disputes'
    /* 列表由 watch(tab) 在切换到 disputes 时拉取，避免与 applyPulse 重复请求 */
  }
}

function doLogin() {
  authError.value = ''
  authLoading.value = true
  api.login(loginForm).then((res) => {
    auth.setUser(res.data.access_token, res.data.username, res.data.user_id)
    showAuthModal.value = false
    loadAccountMe()
    loadMyAgents()
    loadMyPublishedSkills()
    loadTasks()
    if (tab.value === 'mine') loadMyTasks()
    if (tab.value === 'published') loadPublishedTasks()
    applyPulseFromQuery()
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
    loadMyPublishedSkills()
    loadTasks()
    if (tab.value === 'mine') loadMyTasks()
    if (tab.value === 'published') loadPublishedTasks()
    applyPulseFromQuery()
  }).catch((e) => { authError.value = e.response?.data?.detail || t('common.registerFailed') }).finally(() => { authLoading.value = false })
}

function loadTasks() {
  if (route.query.relatedSkillId) {
    applyRelatedSkillFromQuery()
    return
  }
  tasksLoading.value = true
  api.fetchTasks().then((res) => {
    tasks.value = (res.data as { tasks: TaskListItem[] }).tasks || []
  }).catch(() => { tasks.value = [] }).finally(() => { tasksLoading.value = false })
}

function applyRelatedSkillFromQuery() {
  const raw = route.query.relatedSkillId
  const id = raw != null && raw !== '' ? Number(Array.isArray(raw) ? raw[0] : raw) : NaN
  if (!Number.isInteger(id) || id <= 0) {
    relatedSkillFilter.value = null
    const q = { ...route.query } as Record<string, string | string[] | undefined>
    if (q.relatedSkillId != null && q.relatedSkillId !== '') {
      delete q.relatedSkillId
      router.replace({ path: '/tasks', query: q })
    }
    return
  }
  tab.value = 'available'
  tasksLoading.value = true
  api.fetchSkillRelatedTasks(id, { limit: 200 })
    .then((res) => {
      relatedSkillFilter.value = { id, token: res.data.skill_token || '' }
      tasks.value = res.data.items || []
    })
    .catch(() => {
      relatedSkillFilter.value = null
      tasks.value = []
    })
    .finally(() => { tasksLoading.value = false })
}

function clearRelatedSkillFilter() {
  const q = { ...route.query } as Record<string, string | string[] | undefined>
  delete q.relatedSkillId
  router.replace({ path: '/tasks', query: q })
}

function loadMyTasks() {
  if (!auth.isLoggedIn) return Promise.resolve()
  myTasksLoading.value = true
  return api
    .fetchMyAcceptedTasks({ limit: 500 })
    .then((res) => {
      myTasks.value = res.data.tasks || []
    })
    .catch(() => {
      myTasks.value = []
    })
    .finally(() => {
      myTasksLoading.value = false
    })
}

function loadPublishedTasks() {
  if (!auth.isLoggedIn) return Promise.resolve()
  publishedTasksLoading.value = true
  return api
    .fetchMyCreatedTasks({ limit: 500 })
    .then((res) => {
      publishedTasks.value = res.data.tasks || []
    })
    .catch(() => {
      publishedTasks.value = []
    })
    .finally(() => {
      publishedTasksLoading.value = false
    })
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

function loadMyPublishedSkills() {
  if (!auth.isLoggedIn || auth.userId == null) return
  api.fetchSkills({ sort: 'created_desc', limit: 200 })
    .then((res) => {
      const items = (res.data?.items || []) as Array<{ id: number; name: string; skill_token: string; publisher_user_id?: number | null }>
      myPublishedSkills.value = items.filter((x) => Number(x.publisher_user_id) === Number(auth.userId))
    })
    .catch(() => { myPublishedSkills.value = [] })
}

function loadAccountMe() {
  if (!auth.isLoggedIn) return
  api.getAccountMe().then((res) => {
    accountCredits.value = res.data.credits ?? 0
    taskPulseDisputes.value = res.data.task_pulse?.disputes ?? 0
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

/* NOTE: translated comment in English. */
function canA2aTask(t: TaskListItem | null): boolean {
  if (!t) return false
  return canA2aTaskParams({
    isLoggedIn: auth.isLoggedIn,
    userId: auth.userId,
    taskOwnerId: t.owner_id,
    taskAgentId: t.agent_id,
    myAgentIds: myAgents.value.map((a) => a.id),
  })
}

function formatA2aTime(v: unknown): string {
  if (v == null || v === '') return '—'
  try {
    const d = new Date(String(v))
    if (Number.isNaN(d.getTime())) return '—'
    return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return '—'
  }
}

function verificationDeadlineCountdown(iso: string | undefined): string {
  if (!iso) return '—'
  const deadline = new Date(iso).getTime()
  if (Number.isNaN(deadline)) return '—'
  const now = Date.now()
  if (deadline <= now) return t('task.justNow') || 'now'
  const mins = Math.max(1, Math.floor((deadline - now) / 60000))
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  const remMins = mins % 60
  return `${hours}h ${remMins}m`
}

function verificationReleaseText(task: TaskListItem): string {
  const reward = Number(task.reward_points || 0)
  const esc = task.escrow
  if (!esc?.enabled) return `${reward} pts`
  const idx = Number(esc.current_index || 0)
  const points = Number(esc.milestones_preview?.[idx]?.points || 0)
  return points > 0 ? `${points} pts (milestone ${idx + 1})` : `${reward} pts`
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
const a2aSync = ref<Record<string, unknown> | null>(null)
const a2aSyncLoading = ref(false)
const verificationChainLoading = ref(false)
const verificationChainJson = ref('')
const verificationChainData = ref<any>(null)
const workflowLoading = ref(false)
const workflowJson = ref('')
const workflowNodes = ref<number[]>([])
const workflowEdges = ref<Array<{ from: number | null; to: number | null }>>([])
const commentKind = ref<'message' | 'status_update'>('message')
const commentAgentId = ref('')
const skillProgress = ref<api.SkillNode[]>([])

function openTaskDetail(task: TaskListItem) {
  selectedTaskDetail.value = { ...task }
  detailLoading.value = true
  taskComments.value = []
  skillProgress.value = []
  a2aSync.value = null
  verificationChainJson.value = ''
  verificationChainData.value = null
  workflowJson.value = ''
  workflowNodes.value = [task.id]
  workflowEdges.value = []
  commentKind.value = 'message'
  commentAgentId.value = ''
  api.getTaskDetail(task.id).then((res) => {
    selectedTaskDetail.value = res.data as TaskListItem
    const detail = res.data as TaskListItem
    loadA2aSync(task.id)
    if (detail.agent_id) {
      api.fetchAgentSkills(Number(detail.agent_id)).then((r) => {
        const requested = getTaskSkills(detail)
        if (requested.length) {
          const map = new Map((r.data.items || []).map((x) => [x.name, x]))
          skillProgress.value = requested.map((n) => map.get(n)).filter(Boolean) as api.SkillNode[]
        } else {
          skillProgress.value = (r.data.items || []).slice(0, 5)
        }
      }).catch(() => { skillProgress.value = [] })
    }
  }).catch(() => {}).finally(() => { detailLoading.value = false })
  loadTaskComments(task.id, task)
}

function loadA2aSync(taskId: number) {
  const t = selectedTaskDetail.value
  if (!t || !canA2aTask(t)) {
    a2aSync.value = null
    return
  }
  a2aSyncLoading.value = true
  api.a2aGetTask(taskId)
    .then((res) => { a2aSync.value = res.data as Record<string, unknown> })
    .catch(() => { a2aSync.value = null })
    .finally(() => { a2aSyncLoading.value = false })
}

function loadVerificationChain() {
  const t = selectedTaskDetail.value
  if (!t) return
  verificationChainLoading.value = true
  verificationChainJson.value = ''
  verificationChainData.value = null
  api.getTaskVerificationChain(t.id)
    .then((res) => {
      verificationChainData.value = res.data
      verificationChainJson.value = JSON.stringify(res.data, null, 2)
    })
    .catch((e: unknown) => { verificationChainJson.value = JSON.stringify({ error: String(e) }, null, 2) })
    .finally(() => { verificationChainLoading.value = false })
}

const workflowNodeOptions = computed(() => {
  const s = new Set<number>()
  for (const n of workflowNodes.value) {
    const v = Number(n)
    if (Number.isInteger(v) && v > 0) s.add(v)
  }
  return Array.from(s.values()).sort((a, b) => a - b)
})

const workflowValidationError = computed(() => {
  if (!selectedTaskDetail.value) return ''
  const options = workflowNodeOptions.value
  if (!options.length) return '至少需要 1 个有效节点'
  if (!options.includes(selectedTaskDetail.value.id)) return '节点列表必须包含当前任务 ID'
  for (const e of workflowEdges.value) {
    if (e.from == null || e.to == null) return '依赖边必须同时选择 from 和 to'
    if (e.from === e.to) return '依赖边不允许自环'
    if (!options.includes(e.from) || !options.includes(e.to)) return '依赖边引用了不存在的节点'
  }
  return ''
})

function parseWorkflowInput() {
  const nodes = workflowNodeOptions.value
  const edges = workflowEdges.value
    .filter((e): e is { from: number; to: number } => e.from != null && e.to != null)
    .map((e) => ({ from: Number(e.from), to: Number(e.to) }))
  return { nodes, edges }
}

function addWorkflowNode() {
  const base = selectedTaskDetail.value?.id || 1
  let candidate = base
  const exists = new Set(workflowNodeOptions.value)
  while (exists.has(candidate)) candidate += 1
  workflowNodes.value = [...workflowNodes.value, candidate]
}

function removeWorkflowNode(idx: number) {
  const removed = workflowNodes.value[idx]
  workflowNodes.value.splice(idx, 1)
  workflowEdges.value = workflowEdges.value.filter((e) => e.from !== removed && e.to !== removed)
}

function addWorkflowEdge() {
  workflowEdges.value = [...workflowEdges.value, { from: null, to: null }]
}

function removeWorkflowEdge(idx: number) {
  workflowEdges.value.splice(idx, 1)
}

function planWorkflowNow() {
  workflowLoading.value = true
  workflowJson.value = ''
  const body = parseWorkflowInput()
  api.planWorkflow(body)
    .then((res) => { workflowJson.value = JSON.stringify(res.data, null, 2) })
    .catch((e: unknown) => { workflowJson.value = JSON.stringify({ error: String(e) }, null, 2) })
    .finally(() => { workflowLoading.value = false })
}

function attachWorkflowNow() {
  if (!selectedTaskDetail.value) return
  workflowLoading.value = true
  workflowJson.value = ''
  const body = parseWorkflowInput()
  api.attachTaskWorkflow(selectedTaskDetail.value.id, body)
    .then((res) => { workflowJson.value = JSON.stringify(res.data, null, 2) })
    .catch((e: unknown) => { workflowJson.value = JSON.stringify({ error: String(e) }, null, 2) })
    .finally(() => { workflowLoading.value = false })
}

function loadWorkflowNow() {
  if (!selectedTaskDetail.value) return
  workflowLoading.value = true
  workflowJson.value = ''
  api.getTaskWorkflow(selectedTaskDetail.value.id)
    .then((res) => {
      workflowJson.value = JSON.stringify(res.data, null, 2)
      const dag = (res.data as any)?.workflow_dag
      if (dag && Array.isArray(dag.nodes)) {
        workflowNodes.value = dag.nodes.map((n: unknown) => Number(n)).filter((n: number) => Number.isInteger(n) && n > 0)
      }
      if (dag && Array.isArray(dag.edges)) {
        workflowEdges.value = dag.edges.map((e: any) => ({
          from: Number.isInteger(Number(e?.from)) ? Number(e.from) : null,
          to: Number.isInteger(Number(e?.to)) ? Number(e.to) : null,
        }))
      }
    })
    .catch((e: unknown) => { workflowJson.value = JSON.stringify({ error: String(e) }, null, 2) })
    .finally(() => { workflowLoading.value = false })
}

async function loadTaskComments(taskId: number, taskHint?: TaskListItem | null) {
  taskCommentsLoading.value = true
  const t = taskHint ?? selectedTaskDetail.value
  try {
    if (t && canA2aTask(t)) {
      try {
        const res = await api.a2aListMessages(taskId)
        taskComments.value = res.data.messages || []
      } catch {
        const res = await api.getTaskComments(taskId)
        taskComments.value = res.data.comments || []
      }
    } else {
      const res = await api.getTaskComments(taskId)
      taskComments.value = res.data.comments || []
    }
  } catch {
    taskComments.value = []
  } finally {
    taskCommentsLoading.value = false
  }
}

async function copyA2aSyncJson() {
  if (!a2aSync.value) return
  try {
    await navigator.clipboard.writeText(JSON.stringify(a2aSync.value, null, 2))
    showSuccessLocal(t('task.a2aCopied') || '已复制 A2A JSON')
  } catch {
    showSuccessLocal(t('task.a2aCopyFailed') || '复制失败')
  }
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

async function postComment() {
  if (!selectedTaskDetail.value || !newCommentContent.value.trim()) return
  const tid = selectedTaskDetail.value.id
  const content = newCommentContent.value.trim()
  const asA2a = canA2aTask(selectedTaskDetail.value)
  const agentId = commentAgentId.value ? Number(commentAgentId.value) : undefined
  postCommentLoading.value = true
  try {
    if (asA2a) {
      await api.a2aPostMessage(tid, {
        content,
        kind: commentKind.value,
        ...(agentId != null && !Number.isNaN(agentId) ? { agent_id: agentId } : {}),
      })
    } else {
      await api.postTaskComment(tid, { content })
    }
    newCommentContent.value = ''
    commentKind.value = 'message'
    commentAgentId.value = ''
    await loadTaskComments(tid)
    showSuccessLocal(t('task.commentPosted'))
  } catch {
    // NOTE: translated comment in English.
  } finally {
    postCommentLoading.value = false
  }
}

function closeTaskDetail() {
  selectedTaskDetail.value = null
  taskComments.value = []
  skillProgress.value = []
  a2aSync.value = null
  verificationChainJson.value = ''
  verificationChainData.value = null
  workflowJson.value = ''
  workflowNodes.value = []
  workflowEdges.value = []
  commentKind.value = 'message'
  commentAgentId.value = ''
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
      related_skill_token: String(o.related_skill_token ?? ''),
      verification_method: (String(o.verification_method ?? 'manual_review') as any),
      verification_requirements_text: String(o.verification_requirements_text ?? ''),
      escrow_enabled: Boolean(o.escrow_enabled),
      escrow_rows: rows.map((r) => ({
        title: String(r.title ?? ''),
        weight: Number(r.weight) || 0,
        acceptance_criteria: String((r as any).acceptance_criteria ?? ''),
      })),
      verification_hours: Math.min(168, Math.max(1, Number(o.verification_hours) || 6)),
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
      related_skill_token: publishForm.related_skill_token,
      verification_method: publishForm.verification_method,
      verification_requirements_text: publishForm.verification_requirements_text,
      escrow_enabled: publishForm.escrow_enabled,
      escrow_rows: publishForm.escrow_rows.map((r) => ({ ...r })),
      verification_hours: publishForm.verification_hours,
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
  publishForm.related_skill_token = d.related_skill_token || ''
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
  publishForm.verification_hours = typeof (d as any).verification_hours === 'number' ? (d as any).verification_hours : 6
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
    related_skill_token: publishForm.related_skill_token.trim() || undefined,
    verification_method: publishForm.verification_method,
    verification_requirements: publishForm.verification_requirements_text
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean),
    discord_webhook_url: publishForm.discord_webhook_url.trim() || undefined,
    escrow_milestones: escrow_milestones,
    verification_hours: reward > 0 ? Math.min(168, Math.max(1, Number(publishForm.verification_hours) || 6)) : undefined,
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
    publishForm.related_skill_token = ''
    publishForm.verification_method = 'manual_review'
    publishForm.verification_requirements_text = ''
    publishForm.escrow_enabled = false
    publishForm.escrow_rows = defaultEscrowRows()
    publishForm.verification_hours = 6
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
    loadPublishedTasks()
    loadAccountMe()
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
    loadPublishedTasks()
    loadAccountMe()
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
    loadPublishedTasks()
    loadAccountMe()
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
    loadPublishedTasks()
    loadAccountMe()
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
    loadPublishedTasks()
    loadAccountMe()
  }).finally(() => { confirmLoading.value = null })
}

function runExtendVerification(task: TaskListItem) {
  extendVerificationLoading.value = task.id
  api.extendTaskVerification(task.id).then(() => {
    showSuccessLocal(t('task.extendVerificationOk'))
    loadTasks()
    loadMyTasks()
    loadPublishedTasks()
    loadAccountMe()
    if (selectedTaskDetail.value?.id === task.id) openTaskDetail(selectedTaskDetail.value)
  }).catch(() => {}).finally(() => { extendVerificationLoading.value = null })
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
    loadPublishedTasks()
    loadAccountMe()
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

function applySwarmFromQuery() {
  if (String(route.query.swarm) !== '1') return
  const leader = Number(route.query.leader)
  const w1 = Number(route.query.w1)
  const w2 = Number(route.query.w2)
  if (![leader, w1, w2].every((n) => Number.isInteger(n) && n > 0)) return
  if (new Set([leader, w1, w2]).size !== 3) return
  if (!myAgents.value.length) return
  const names = new Map(myAgents.value.map((a) => [a.id, a.name]))
  if (!names.has(leader) || !names.has(w1) || !names.has(w2)) {
    nextTick(() => {
      router.replace({ path: '/tasks', query: {} })
    })
    showSuccessLocal(String(t('marketplace.swarmInvalidAgents') || '未找到所选 Agent，请重试'))
    return
  }
  const ln = names.get(leader)!
  const n1 = names.get(w1)!
  const n2 = names.get(w2)!

  publishForm.title = String(t('marketplace.swarmDefaultTitle', { leader: ln }))
  publishForm.description = String(t('marketplace.swarmDefaultDesc', { leader: ln, w1: n1, w2: n2 }))
  publishForm.requirements = String(t('marketplace.swarmDefaultReq'))
  publishForm.category = 'other'
  publishForm.skills_text = 'swarm, collaboration'
  publishForm.reward_points = Math.max(publishForm.reward_points, 10)
  publishForm.escrow_enabled = true
  publishForm.escrow_rows = [
    {
      title: String(t('marketplace.swarmMilestoneLeader', { name: ln })),
      weight: 0.34,
      acceptance_criteria: String(t('marketplace.swarmMilestoneLeaderAc')),
    },
    {
      title: String(t('marketplace.swarmMilestoneW1', { name: n1 })),
      weight: 0.33,
      acceptance_criteria: String(t('marketplace.swarmMilestoneW1Ac')),
    },
    {
      title: String(t('marketplace.swarmMilestoneW2', { name: n2 })),
      weight: 0.33,
      acceptance_criteria: String(t('marketplace.swarmMilestoneW2Ac')),
    },
  ]
  publishForm.creator_agent_id = leader
  publishError.value = ''
  showCreateModal.value = true
  nextTick(() => {
    router.replace({ path: '/tasks', query: {} })
  })
}

onMounted(() => {
  loadCandidates()
  if (auth.isLoggedIn) {
    loadMyAgents()
    loadMyPublishedSkills()
    loadAccountMe()
    refreshAdminFlag()
  }
})

watch(
  () => String(route.query.relatedSkillId ?? ''),
  (v) => {
    if (v) applyRelatedSkillFromQuery()
    else {
      relatedSkillFilter.value = null
      loadTasks()
    }
  },
  { immediate: true }
)

watch(
  () => [normalizePulse(route.query.pulse), auth.isLoggedIn, String(route.query.relatedSkillId ?? '')] as const,
  () => {
    applyPulseFromQuery()
  },
  { immediate: true }
)

watch(
  () => String(route.query.taskId ?? ''),
  (v) => {
    if (!v) return
    const id = Number(v)
    if (!Number.isInteger(id) || id <= 0) return
    if (selectedTaskDetail.value?.id === id) {
      if (detailLoading.value) return
      return
    }
    openTaskDetail({ id } as TaskListItem)
  },
  { immediate: true }
)

watch(
  () => [route.query.publishAs, myAgents.value.length] as const,
  () => applyPublishAsFromQuery(),
  { immediate: true }
)

watch(
  () => [String(route.query.swarm), route.query.leader, route.query.w1, route.query.w2, myAgents.value.length] as const,
  () => applySwarmFromQuery(),
  { immediate: true }
)

watch(() => auth.isLoggedIn, (loggedIn) => {
  if (loggedIn) {
    loadMyAgents()
    loadMyPublishedSkills()
    loadAccountMe()
    refreshAdminFlag()
    if (tab.value === 'mine') loadMyTasks()
    if (tab.value === 'published') loadPublishedTasks()
    applyPulseFromQuery()
  } else {
    isAdmin.value = false
    myPublishedSkills.value = []
    publishedTasks.value = []
    taskPulseDisputes.value = 0
  }
})

watch(tab, (newTab) => {
  if (!auth.isLoggedIn) return
  if (newTab === 'mine') loadMyTasks()
  if (newTab === 'published') loadPublishedTasks()
  if (newTab === 'disputes') {
    void Promise.all([loadMyTasks(), loadPublishedTasks()]).then(() => loadAccountMe())
  }
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

.detail-a2a-sync {
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: var(--border-hairline);
}
.detail-a2a-sync__hint { margin: 0 0 var(--space-6); font-size: var(--font-caption); }
.detail-a2a-sync__dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-2) var(--space-6);
  margin: 0 0 var(--space-4);
  font-size: var(--font-caption);
}
.detail-a2a-sync__dl dt { color: var(--text-secondary); margin: 0; }
.detail-a2a-sync__dl dd { margin: 0; color: var(--text-primary); }
.detail-verification-chain {
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: var(--border-hairline);
  display: grid;
  gap: var(--space-3);
}
.verification-chain-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}
.verification-chain-card {
  border: var(--border-hairline);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: rgba(255, 255, 255, 0.03);
}
.detail-workflow-dag {
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: var(--border-hairline);
  display: grid;
  gap: var(--space-3);
}
.workflow-editor {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}
.workflow-editor__col {
  border: var(--border-hairline);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  display: grid;
  gap: var(--space-2);
}
.workflow-editor__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.workflow-row {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}
.workflow-row--edge .input {
  min-width: 6.5rem;
}
.task-comment-a2a-opts { display: flex; flex-direction: column; gap: var(--space-3); margin-bottom: var(--space-2); }
.task-comment-a2a-row { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3); }
.task-comment-a2a-label { font-size: var(--font-caption); color: var(--text-secondary); min-width: 4.5rem; }
.task-comment-a2a-select { flex: 1; min-width: 160px; max-width: 100%; }
.task-verification-ops-hint {
  margin-top: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: var(--border-hairline);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.03);
}
.task-verification-ops-hint .hint { margin: 0; }
.task-verification-ops-hint .hint + .hint { margin-top: var(--space-2); }
.reject-quick-templates {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.reject-quick-templates__btn {
  border: var(--border-hairline);
  background: rgba(255,255,255,0.04);
  color: var(--text-secondary);
  padding: 0.3rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
}
.reject-quick-templates__btn:hover { color: var(--text-primary); }

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
.task-comment-content { margin: 0; font-size: var(--font-body); color: var(--text-secondary); line-height: var(--line-normal); }
.task-comment-content :deep(.claw-md) { color: inherit; }
.task-comments-empty { margin: 0; color: var(--text-secondary); font-size: var(--font-caption); }
.task-comment-form { margin-top: var(--space-5); display: flex; flex-direction: column; gap: var(--space-3); }
.task-payment-panel, .task-timeline-panel, .task-rejection-history {
  margin-top: var(--space-4);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: var(--border-hairline);
  background: rgba(255,255,255,0.02);
}
.task-payment-list { margin: 0; padding-left: 1.1rem; font-size: var(--font-small); color: var(--text-secondary); }
.task-payment-tx { margin: 0.5rem 0 0; padding-left: 1rem; list-style: disc; color: var(--text-tertiary); }
.task-timeline-list { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 0.5rem; }
.task-timeline-item { display: flex; flex-direction: column; gap: 0.15rem; font-size: var(--font-small); }
.task-timeline-time { color: var(--text-tertiary); font-size: 0.75rem; }
.task-timeline-summary { color: var(--text-secondary); }
.task-rejection-details { margin-bottom: 0.5rem; }
.task-rejection-reason { margin: 0.35rem 0 0; white-space: pre-wrap; font-size: var(--font-small); color: var(--text-secondary); }
.task-verify-hint { margin-top: var(--space-3); }
.detail-escrow__sla { margin-top: 0.35rem; font-size: var(--font-caption); }

/* NOTE: translated comment in English. */
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
.task-tag--skill-related { border-color: rgba(34, 197, 94, 0.38); color: rgba(187, 247, 208, 0.95); }
.task-row__meta {
  font-size: var(--font-caption);
  color: var(--text-tertiary);
  line-height: 1.5;
  margin: 0 0 var(--space-4);
}
.task-row__meta--skill { color: rgba(187, 247, 208, 0.86); }
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

/* NOTE: translated comment in English. */
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

/* NOTE: translated comment in English. */
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
.pulse-filter-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
  padding: 0.5rem 0.75rem;
  margin-bottom: var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid rgba(var(--primary-rgb), 0.22);
  background: rgba(var(--primary-rgb), 0.06);
  font-size: 0.875rem;
  color: var(--text-secondary);
}
.pulse-filter-banner span:first-child {
  flex: 1;
  min-width: 0;
}
.hint-inline {
  color: var(--text-tertiary, var(--text-secondary));
  font-style: italic;
}
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
.task-tab--disputes.task-tab.active {
  border-color: rgba(251, 146, 60, 0.45);
  background: rgba(251, 146, 60, 0.12);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06), 0 0 0 1px rgba(251, 146, 60, 0.15) inset;
}
.task-tab__count {
  margin-left: 0.2rem;
  font-weight: 600;
  opacity: 0.9;
}
.disputes-merge-hint {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin: 0 0 var(--space-3);
  line-height: 1.45;
}
.task-row__dispute-role {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.15rem 0.45rem;
  border-radius: 6px;
  background: rgba(251, 146, 60, 0.12);
  border: 1px solid rgba(251, 146, 60, 0.35);
  color: #fdba74;
}
.related-skill-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(34, 197, 94, 0.28);
  background: rgba(34, 197, 94, 0.08);
}
.related-skill-banner__text {
  margin: 0;
  font-size: var(--font-caption);
  color: var(--text-secondary);
  line-height: 1.5;
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
.detail-related-skill-link { color: var(--primary-color); text-decoration: none; }
.detail-related-skill-link:hover { text-decoration: underline; }
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
