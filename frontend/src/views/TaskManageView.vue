<template>
  <div class="task-manage-view apple-layout">
    <h1 class="page-title">{{ t('nav.taskManage') }}</h1>
    <div class="task-layout task-layout--mine-only">
      <section class="task-center">
        <div class="task-center-inner">
          <div class="task-list-wrap">
          <div class="task-tabs">
            <button type="button" class="task-tab" :class="{ active: tab === 'available' }" @click="tab = 'available'">{{ t('taskManage.available') || '可接取任务' }}</button>
            <button type="button" class="task-tab" :class="{ active: tab === 'mine' }" @click="tab = 'mine'">{{ t('taskManage.myAccepted') || '我接取的任务' }}</button>
          </div>
          <div v-if="!auth.isLoggedIn" class="empty-state">
            <p class="empty">{{ t('taskManage.loginToSeeMine') || '请先登录查看我接取的任务' }}</p>
            <Button type="button" @click="showAuthModal = true">{{ t('common.loginOrRegister') }}</Button>
          </div>
          <template v-else>
            <!-- 可接取任务 -->
            <template v-if="tab === 'available'">
              <div class="task-filter-row">
                <select v-model="categoryFilter" class="input select-input task-filter-select">
                  <option value="">{{ t('taskManage.categoryAll') || '全部' }}</option>
                  <option v-for="opt in categoryFilterOptions" :key="opt.value" :value="opt.value">{{ t(opt.labelKey) }}</option>
                </select>
              </div>
              <div v-if="tasksLoading" class="task-list task-list--skeleton">
                <div v-for="i in 5" :key="i" class="card task-card tw-skeleton-card task-manage-skeleton-card">
                  <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--short"></div>
                  <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--full"></div>
                  <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--mid"></div>
                </div>
              </div>
              <div v-else class="task-list">
                <div v-for="task in filteredTasks" :key="task.id" class="card task-card task-card--structured task-manage-card">
                  <div class="task-card__top">
                    <span v-if="task.category" class="task-card__category">{{ taskCategoryLabel(task.category) }}</span>
                    <span class="badge" :class="task.status">{{ t('status.' + task.status) || task.status }}</span>
                    <span v-if="task.reward_points" class="task-card__reward mono">{{ t('task.reward', { n: task.reward_points }) }}</span>
                  </div>
                  <h3 class="task-card__title">{{ task.title }}</h3>
                  <p class="task-card__desc">{{ (task.description || t('common.noDescription')).slice(0, 120) }}{{ (task.description || '').length > 120 ? '…' : '' }}</p>
                  <p class="task-card__meta">{{ t('task.publisher') }}：{{ task.publisher_name }}<span v-if="task.creator_agent_name"> · {{ t('task.publishedByAgent') }}：{{ task.creator_agent_name }}</span><span v-if="task.subscription_count != null"> · {{ task.subscription_count }}{{ t('task.subscribers') }}</span></p>
                  <div class="card-content task-card__actions-wrap">
                    <Button size="sm" variant="ghost" type="button" class="detail-btn" @click="openTaskDetail(task)">{{ t('task.viewDetail') }}</Button>
                    <Button v-if="task.status === 'open' && auth.isLoggedIn && myAgents.length" size="sm" :disabled="subscribeLoading === task.id" @click="openSubscribeModal(task)">{{ t('task.subscribe') }}</Button>
                    <Button v-else-if="task.status === 'open' && !auth.isLoggedIn" size="sm" variant="secondary" type="button" @click="showAuthModal = true">{{ t('task.loginToAccept') }}</Button>
                  </div>
                </div>
              </div>
              <div v-if="!filteredTasks.length && !tasksLoading" class="empty-state">
                <p class="empty">{{ categoryFilter ? (t('taskManage.noTasksInCategory') || '该分类下暂无任务') : (t('task.emptyTasks') || '暂无任务') }}</p>
                <Button :as="RouterLink" to="/" variant="secondary">{{ t('common.home') }}</Button>
              </div>
            </template>
            <!-- 我接取的任务 -->
            <template v-else>
            <div v-if="myTasksLoading" class="task-list task-list--skeleton">
              <div v-for="i in 4" :key="i" class="card task-card tw-skeleton-card task-manage-skeleton-card">
                <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--short"></div>
                <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--full"></div>
                <div class="tw-skeleton task-manage-skeleton-line task-manage-skeleton-line--mid"></div>
              </div>
            </div>
            <div v-else class="task-list">
              <div v-for="task in myTasks" :key="task.id" class="card task-card task-card--structured task-manage-card">
                <div class="task-card__top">
                  <span v-if="task.category" class="task-card__category">{{ taskCategoryLabel(task.category) }}</span>
                  <span v-if="task.task_type" class="task-card__type">{{ task.task_type }}</span>
                  <span class="badge" :class="task.status">{{ t('status.' + task.status) || task.status }}</span>
                  <span v-if="task.reward_points" class="task-card__reward mono">{{ t('task.reward', { n: task.reward_points }) }}</span>
                </div>
                <h3 class="task-card__title">{{ task.title }}</h3>
                <p class="task-card__desc">{{ (task.description || t('common.noDescription')).slice(0, 120) }}{{ (task.description || '').length > 120 ? '…' : '' }}</p>
                <div v-if="task.location || task.duration_estimate || (getTaskSkills(task).length)" class="task-card__attrs">
                  <span v-if="task.location" class="task-tag task-tag--location">{{ task.location }}</span>
                  <span v-if="task.duration_estimate" class="task-tag task-tag--duration">{{ task.duration_estimate }}</span>
                  <span v-for="s in getTaskSkills(task)" :key="s" class="task-tag task-tag--skill">{{ s }}</span>
                </div>
                <p class="task-card__meta">{{ t('task.publisher') }}：{{ task.publisher_name }}<span v-if="task.creator_agent_name"> · {{ t('task.publishedByAgent') }}：{{ task.creator_agent_name }}</span> · {{ t('task.acceptor') || '接取者' }}：{{ task.agent_name }}</p>
                <div class="card-content task-card__actions-wrap">
                  <Button size="sm" variant="ghost" type="button" class="detail-btn" @click="openTaskDetail(task)">{{ t('task.viewDetail') }}</Button>
                  <div class="task-actions">
                    <Button
                      v-if="isExecutor(task) && task.status === 'open'"
                      size="sm"
                      :disabled="submitCompletionLoading === task.id"
                      @click="openSubmitModal(task)"
                    >
                      {{ t('task.submitCompletion') }}
                    </Button>
                    <template v-if="task.owner_id === auth.userId && task.status === 'pending_verification'">
                      <Button size="sm" :disabled="confirmLoading === task.id" @click="doConfirm(task.id)">{{ t('task.confirmPass') }}</Button>
                      <Button size="sm" variant="secondary" :disabled="rejectLoading === task.id" @click="openRejectModal(task.id)">{{ t('task.reject') }}</Button>
                    </template>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="!myTasks.length && !myTasksLoading" class="empty-state">
              <p class="empty">{{ t('taskManage.noMyTasks') || '暂无接取的任务' }}</p>
              <Button :as="RouterLink" to="/">{{ t('taskManage.goAccept') || '去接取' }}</Button>
            </div>
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
              <dl class="detail-meta" v-if="selectedTaskDetail.category || selectedTaskDetail.requirements || selectedTaskDetail.duration_estimate || (getTaskSkills(selectedTaskDetail).length) || selectedTaskDetail.location">
                <template v-if="selectedTaskDetail.category"><dt>{{ t('task.detailCategory') }}</dt><dd>{{ taskCategoryLabel(selectedTaskDetail.category) }}</dd></template>
                <template v-if="selectedTaskDetail.requirements"><dt>{{ t('task.detailRequirements') }}</dt><dd class="detail-requirements">{{ selectedTaskDetail.requirements }}</dd></template>
                <template v-if="selectedTaskDetail.duration_estimate"><dt>{{ t('task.detailDuration') }}</dt><dd>{{ selectedTaskDetail.duration_estimate }}</dd></template>
                <template v-if="getTaskSkills(selectedTaskDetail).length"><dt>{{ t('task.detailSkills') }}</dt><dd><span v-for="s in getTaskSkills(selectedTaskDetail)" :key="s" class="task-tag task-tag--skill">{{ s }}</span></dd></template>
                <template v-if="selectedTaskDetail.location"><dt>{{ t('task.detailLocation') }}</dt><dd>{{ selectedTaskDetail.location }}</dd></template>
              </dl>
              <p class="detail-footer">
                {{ t('task.publisher') }}：{{ selectedTaskDetail.publisher_name }}
                <span v-if="selectedTaskDetail.creator_agent_name"> · {{ t('task.publishedByAgent') }}：{{ selectedTaskDetail.creator_agent_name }}</span>
                · <span class="badge" :class="selectedTaskDetail.status">{{ t('status.' + selectedTaskDetail.status) || selectedTaskDetail.status }}</span>
                <span v-if="selectedTaskDetail.reward_points" class="detail-reward">{{ t('task.reward', { n: selectedTaskDetail.reward_points }) }}</span>
              </p>
              <div class="task-detail-panel__actions">
                <Button v-if="auth.isLoggedIn && isExecutor(selectedTaskDetail) && selectedTaskDetail.status === 'open'" size="sm" :disabled="submitCompletionLoading === selectedTaskDetail.id" @click="openSubmitModal(selectedTaskDetail)">{{ t('task.submitCompletion') }}</Button>
                <template v-if="auth.isLoggedIn && selectedTaskDetail.owner_id === auth.userId && selectedTaskDetail.status === 'pending_verification'">
                  <Button size="sm" :disabled="confirmLoading === selectedTaskDetail.id" @click="doConfirm(selectedTaskDetail.id)">{{ t('task.confirmPass') }}</Button>
                  <Button size="sm" variant="secondary" :disabled="rejectLoading === selectedTaskDetail.id" @click="openRejectModal(selectedTaskDetail.id)">{{ t('task.reject') }}</Button>
                </template>
              </div>
              <div v-if="selectedTaskDetail.status === 'pending_verification' && selectedTaskDetail.output_data && (selectedTaskDetail.output_data.result_summary || (selectedTaskDetail.output_data.evidence && selectedTaskDetail.output_data.evidence.link))" class="task-detail-completion-submission">
                <h4 class="task-comments-title">{{ t('task.completionSubmissionTitle') }}</h4>
                <p v-if="selectedTaskDetail.output_data.result_summary" class="completion-summary">{{ selectedTaskDetail.output_data.result_summary }}</p>
                <p v-if="selectedTaskDetail.output_data.evidence && selectedTaskDetail.output_data.evidence.link" class="completion-link">
                  <a :href="String(selectedTaskDetail.output_data.evidence.link)" target="_blank" rel="noopener noreferrer" class="app-link">{{ t('task.completionLink') }}：{{ selectedTaskDetail.output_data.evidence.link }}</a>
                </p>
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
          <div class="form-group form-inline">
            <label class="form-label" for="publish-reward">{{ t('agentGuide.fieldRewardPoints') }}</label>
            <input id="publish-reward" v-model.number="publishForm.reward_points" type="number" min="0" class="input input-num" />
          </div>
          <template v-if="publishForm.reward_points > 0">
            <div class="form-group">
              <label class="form-label" for="publish-webhook">{{ t('agentGuide.fieldWebhook') }}</label>
              <Input id="publish-webhook" v-model="publishForm.completion_webhook_url" class="w-full" type="url" :placeholder="t('task.webhookPlaceholder')" />
            </div>
          </template>
          <div class="form-group">
            <label class="form-label" for="publish-discord">{{ t('task.discordWebhookLabel') }}</label>
            <Input id="publish-discord" v-model="publishForm.discord_webhook_url" class="w-full" type="url" :placeholder="t('task.discordWebhookPlaceholder')" />
          </div>
          <p class="hint">{{ t('task.balanceHint', { n: accountCredits }) }}</p>
          <p v-if="publishError" class="error-msg" role="alert">{{ publishError }}</p>
          <div class="modal-actions">
            <Button type="button" :disabled="publishLoading" @click="doPublishAndClose">{{ publishLoading ? t('task.publishBtnLoading') : t('task.publishBtn') }}</Button>
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
          <Button :disabled="submitCompletionLoading" @click="doSubmitCompletion">{{ t('task.submitCompletion') }}</Button>
        </div>
        <Button variant="secondary" class="close-btn w-full" @click="submitCompletionTask = null">{{ t('common.cancel') }}</Button>
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
import { useRoute, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
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
const publishForm = reactive<{ title: string; description: string; category: string; requirements: string; reward_points: number; completion_webhook_url: string; discord_webhook_url: string; invited_agent_ids: number[]; creator_agent_id: number | null; location: string; duration_estimate: string; skills_text: string }>({ title: '', description: '', category: '', requirements: '', reward_points: 0, completion_webhook_url: '', discord_webhook_url: '', invited_agent_ids: [], creator_agent_id: null, location: '', duration_estimate: '', skills_text: '' })
const publishLoading = ref(false)
const publishError = ref('')
const candidates = ref<Array<{ id: number; name: string; owner_name: string; points?: number }>>([])
const myAgents = ref<Array<{ id: number; name: string; agent_type: string }>>([])
const accountCredits = ref(0)
const subscribeTaskItem = ref<{ id: number; title: string } | null>(null)
const subscribeLoading = ref<number | null>(null)
const submitCompletionTask = ref<{ id: number; title: string } | null>(null)
const submitCompletionForm = reactive({ result_summary: '', completion_link: '' })
const submitCompletionLoading = ref(false)
const confirmLoading = ref<number | null>(null)
const rejectLoading = ref<number | null>(null)
const rejectTaskId = ref<number | null>(null)
const rejectReason = ref('')
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
const selectedTaskDetail = ref<TaskListItem | null>(null)
const detailLoading = ref(false)
const taskComments = ref<TaskCommentItem[]>([])
const taskCommentsLoading = ref(false)
const newCommentContent = ref('')
const postCommentLoading = ref(false)

function openTaskDetail(task: TaskListItem) {
  selectedTaskDetail.value = { ...task }
  detailLoading.value = true
  taskComments.value = []
  api.getTaskDetail(task.id).then((res) => {
    selectedTaskDetail.value = res.data as TaskListItem
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
}

function openCreateModal() {
  if (!auth.isLoggedIn) {
    showAuthModal.value = true
    return
  }
  publishError.value = ''
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
    discord_webhook_url: publishForm.discord_webhook_url.trim() || undefined,
  }).then(() => {
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
}

function doSubmitCompletion() {
  if (!submitCompletionTask.value) return
  submitCompletionLoading.value = true
  const evidence = submitCompletionForm.completion_link.trim() ? { link: submitCompletionForm.completion_link.trim() } : {}
  api.submitCompletion(submitCompletionTask.value.id, { result_summary: submitCompletionForm.result_summary.trim(), evidence }).then(() => {
    submitCompletionTask.value = null
    showSuccessLocal(t('task.submitCompletionSuccess'))
    loadTasks()
    loadMyTasks()
  }).finally(() => { submitCompletionLoading.value = false })
}

function doConfirm(taskId: number) {
  confirmLoading.value = taskId
  api.confirmTask(taskId).then(() => {
    showSuccessLocal(t('task.confirmSuccess'))
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
    if (tab.value === 'mine') loadMyTasks()
  }
})

watch(tab, (newTab) => {
  if (newTab === 'mine' && auth.isLoggedIn) loadMyTasks()
})
</script>

<style scoped>
.task-manage-view { width: 100%; }
.task-layout { display: grid; grid-template-columns: 160px 1fr 200px; gap: var(--space-4) var(--space-6); align-items: start; min-height: 60vh; }
.task-left { padding-top: 0.25rem; }
.task-categories { display: flex; flex-direction: column; gap: 0.25rem; }
.category-item {
  padding: 0.5rem 0.75rem; border-radius: 8px; border: 1px solid var(--border, #333); background: transparent; color: var(--text-secondary);
  font-size: 0.9rem; text-align: left; cursor: pointer; transition: border-color 0.2s, background 0.2s, color 0.2s;
}
.category-item:hover { border-color: var(--primary-color); color: var(--text-primary); }
.category-item.active { background: rgba(var(--primary-rgb, 34, 197, 94), 0.12); border-color: var(--primary-color); color: var(--primary-color); }
.category-item--mine { margin-top: 0.5rem; font-weight: 500; }
.task-center { display: flex; flex-direction: column; min-width: 0; }
.task-center-inner { display: flex; gap: var(--space-5); flex: 1; min-height: 0; }
.task-center-inner--mine { display: block; }
.task-list-wrap { flex: 0 1 50%; min-width: 0; overflow-y: auto; }
.task-detail-panel {
  flex: 0 1 50%; min-width: 0; overflow-y: auto; border-radius: var(--radius-md); border: 1px solid var(--border-color);
  background: var(--card-bg); padding: var(--space-5) var(--space-6);
  box-shadow: var(--shadow-card); transition: box-shadow var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple);
}
.task-detail-panel__head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: var(--space-4); }
.task-detail-panel__title { font-size: 1.05rem; margin: 0; font-weight: 600; letter-spacing: -0.02em; line-height: 1.3; word-break: break-word; min-width: 0; color: var(--text-primary); }
.task-detail-panel__actions { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-4); }
.task-card__title { word-break: break-word; min-width: 0; }
.task-card__desc { word-break: break-word; min-width: 0; }
.task-card__meta { word-break: break-word; min-width: 0; }
.task-card__actions-wrap { flex-wrap: wrap; gap: 0.5rem; }
.task-card__top { flex-wrap: wrap; gap: 0.35rem; }
.task-detail-completion-submission { margin-top: var(--space-5); padding: var(--space-4); background: var(--surface); border-radius: var(--radius-sm); }
.task-detail-completion-submission .completion-summary { margin: 0 0 0.5rem; white-space: pre-wrap; font-size: 0.9rem; color: var(--text-secondary); }
.task-detail-completion-submission .completion-link { margin: 0; font-size: 0.9rem; }
.task-tabs { display: flex; gap: var(--space-2); margin-bottom: var(--space-5); }
.task-tab { padding: 0.5rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: transparent; color: var(--text-secondary); font-size: 0.9rem; font-weight: 500; cursor: pointer; transition: border-color var(--duration-m) var(--ease-apple), background var(--duration-m) var(--ease-apple), color var(--duration-m) var(--ease-apple); }
.task-tab:hover { border-color: var(--primary-color); color: var(--primary-color); }
.task-tab.active { background: rgba(var(--primary-rgb, 34, 197, 94), 0.12); border-color: var(--primary-color); color: var(--primary-color); }
.task-filter-row { margin-bottom: var(--space-4); }
.task-filter-select { max-width: 180px; }
.task-layout--mine-only { grid-template-columns: minmax(0, 1fr) 220px; }
.task-layout--mine-only .task-center { min-width: 0; }
.task-right { display: flex; flex-direction: column; gap: var(--space-5); }
.task-right-card {
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--card-background, var(--card-bg));
  padding: var(--space-5) var(--space-6);
  box-shadow: var(--shadow-card);
  transition: box-shadow var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple);
}
.task-right-create .btn { width: 100%; }
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
.task-right-agent-link:hover { background: rgba(var(--primary-rgb, 34, 197, 94), 0.1); color: var(--primary-color); text-decoration: none; border-color: var(--border-color); }
.task-right-agent-num {
  flex-shrink: 0; width: 1.35rem; height: 1.35rem; border-radius: 6px;
  background: var(--surface); color: var(--text-secondary);
  font-size: 0.75rem; font-weight: 600; display: inline-flex; align-items: center; justify-content: center;
}
.task-right-agent-link:hover .task-right-agent-num { background: rgba(var(--primary-rgb, 34, 197, 94), 0.2); color: var(--primary-color); }
.task-right-agent-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-right-more { padding: 0.25rem 0; margin-top: 0.25rem; }
@media (max-width: 1024px) {
  .task-layout { grid-template-columns: 1fr 200px; }
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
}
.modal--create { max-width: 520px; width: 95%; max-height: 90vh; overflow-y: auto; }
.publish-form-in-modal .form-group { margin-bottom: 1rem; }
.publish-form-in-modal .create-task-step { margin-bottom: 0.75rem; }
.publish-form-in-modal .create-task-step-label { display: block; font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.5rem; }
.publish-form-in-modal .modal-actions { display: flex; gap: 0.5rem; margin-top: 1rem; }
.publish-form-in-modal .form-group.form-inline { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.publish-form-in-modal .form-group.form-inline .form-label { margin-bottom: 0; margin-right: 0.25rem; }
.publish-form-in-modal .form-group.form-inline .input-num { width: 6rem; }
.publish-form-in-modal .form-hint { font-size: 0.8rem; color: var(--text-secondary); margin: 0.35rem 0 0; line-height: 1.4; }
.create-task-step { margin-bottom: 1rem; }
.create-task-step-label { display: block; font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.03em; }
.create-task-step--identity { margin-bottom: 1.25rem; }
.publish-identity-toggles { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.35rem; }
.identity-toggle { padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid var(--border-color); background: var(--background-dark); color: var(--text-secondary); font-size: 0.9rem; cursor: pointer; transition: border-color var(--duration-m) var(--ease-apple), background var(--duration-m) var(--ease-apple), color var(--duration-m) var(--ease-apple); }
.identity-toggle:hover { border-color: var(--primary-color); color: var(--primary-color); }
.identity-toggle.active { background: rgba(var(--primary-rgb, 34, 197, 94), 0.15); border-color: var(--primary-color); color: var(--primary-color); }
.form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem 1rem; }
.form-row-2 .form-group { margin-bottom: 0; }
@media (max-width: 480px) { .form-row-2 { grid-template-columns: 1fr; } }
.task-list { display: flex; flex-direction: column; gap: 1rem; }
.task-list--skeleton .task-manage-skeleton-card { padding: 1.25rem; }
.task-manage-skeleton-line { display: block; border-radius: 4px; height: 0.875rem; margin-bottom: 0.5rem; }
.task-manage-skeleton-line:last-child { margin-bottom: 0; }
.task-manage-skeleton-line--short { width: 30%; }
.task-manage-skeleton-line--full { width: 100%; }
.task-manage-skeleton-line--mid { width: 75%; }
.task-card .card-header { display: flex; justify-content: space-between; align-items: center; }
.task-card .meta { font-size: 0.875rem; color: var(--muted); margin: 0.25rem 0; }

/* 结构化任务卡片（与首页/website 一致：8px 栅格、typography、.mono） */
.task-card--structured.task-manage-card {
  padding: 24px;
  border-radius: 12px;
  border: 1px solid var(--border-color, rgba(255,255,255,0.08));
  background: var(--card-background, var(--card-bg));
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  transition: box-shadow 0.2s, border-color 0.2s;
}
.task-card--structured.task-manage-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  border-color: var(--border-color, rgba(255,255,255,0.12));
}
.task-card--structured.task-manage-card .task-card__top { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.task-card--structured.task-manage-card .task-card__type { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.02em; }
.task-card--structured.task-manage-card .task-card__reward { margin-left: auto; font-size: 0.9rem; font-weight: 600; color: var(--primary, #6366f1); }
.task-card--structured.task-manage-card .task-card__title { font-size: 1rem; margin: 0 0 8px; font-weight: 600; line-height: 1.35; }
.task-card--structured.task-manage-card .task-card__desc { font-size: 0.875rem; color: var(--text-secondary, var(--muted)); margin: 0 0 8px; line-height: 1.55; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.task-card--structured.task-manage-card .task-card__tags,
.task-card--structured.task-manage-card .task-card__attrs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; font-size: 0.8125rem; }
.task-tag { display: inline-block; font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 999px; background: var(--surface, rgba(255,255,255,0.06)); color: var(--text-secondary, #94a3b8); border: 1px solid var(--border, rgba(255,255,255,0.1)); }
.task-tag--location { border-color: rgba(34, 197, 94, 0.4); color: #86efac; }
.task-tag--duration { border-color: rgba(59, 130, 246, 0.4); color: #93c5fd; }
.task-card__category { font-size: 0.75rem; padding: 0.25rem 0.5rem; background: var(--surface-700, #333); border-radius: 6px; margin-right: 0.35rem; font-weight: 500; }
.select-input { max-width: 100%; }
.textarea-input { min-height: 4rem; resize: vertical; }
.modal--detail { max-width: 28rem; }
.detail-section { margin-bottom: 1rem; }
.detail-desc { white-space: pre-wrap; word-break: break-word; color: var(--text-secondary); }
.detail-meta { margin: 0 0 1rem; font-size: 0.9rem; }
.detail-meta dt { font-weight: 600; color: var(--text-secondary); margin-top: 0.5rem; margin-bottom: 0.2rem; }
.detail-meta dd { margin: 0; }
.detail-requirements { white-space: pre-wrap; word-break: break-word; }
.detail-footer { font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.75rem; }
.detail-reward { margin-left: 0.5rem; }
.detail-btn { margin-right: auto; }
.task-card__requirements-snippet { font-size: 0.8rem; color: var(--text-secondary); margin: 0 0 0.4rem; padding-left: 0.5rem; border-left: 2px solid var(--surface-700); line-height: 1.35; }
.task-card__priority { font-size: 0.7rem; padding: 0.15rem 0.4rem; border-radius: 4px; text-transform: uppercase; }
.task-card__priority.priority--high { background: rgba(234, 179, 8, 0.2); color: #eab308; }
.task-card__priority.priority--critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.task-card__priority.priority--low { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
.task-tag--skill { border-color: rgba(168, 85, 247, 0.4); color: #e9d5ff; }
.task-card--structured.task-manage-card .task-card__meta { font-size: 0.8125rem; line-height: 1.5; color: var(--text-secondary, var(--muted)); margin: 0 0 12px; }
.task-card--structured.task-manage-card .task-card__actions-wrap { padding: 0; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-muted, var(--border-color)); }

.task-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
.empty-state { text-align: center; padding: 2rem; color: var(--muted); }
.agent-select-list { display: flex; flex-direction: column; gap: 0.5rem; margin: 1rem 0; }
.modal--create { max-width: 520px; padding: var(--space-6, 1.5rem); }
.modal--create .form-group { margin-bottom: var(--space-4, 1rem); }
.modal--create .modal-actions { margin-top: var(--space-5, 1.25rem); }
</style>
