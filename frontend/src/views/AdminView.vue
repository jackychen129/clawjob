<template>
  <section class="admin-wrap apple-layout">
    <PageHeader :title="t('admin.title') || '管理后台'">
      <template #actions>
        <Button type="button" variant="secondary" :disabled="loading" @click="reloadAll">
          {{ t('common.retry') || '刷新' }}
        </Button>
      </template>
    </PageHeader>

    <div v-if="denied" class="card admin-card">
      <p class="error-msg">{{ t('admin.denied') || '无权限访问（需要管理员账号）' }}</p>
    </div>

    <template v-else>
      <div v-if="loading && !metrics" class="admin-metrics admin-metrics--skeleton">
        <div v-for="i in 4" :key="i" class="card tw-skeleton-card admin-metric-card">
          <div class="tw-skeleton admin-skel-line admin-skel-line--title"></div>
          <div class="tw-skeleton admin-skel-line admin-skel-line--value"></div>
          <div class="tw-skeleton admin-skel-line admin-skel-line--hint"></div>
        </div>
      </div>

      <div v-else class="admin-metrics">
        <div class="card admin-metric-card admin-metric-card--ops">
          <div class="admin-metric-title">{{ t('admin.metricPublicAgents') || '公开 Agent' }}</div>
          <div class="admin-metric-value">{{ metrics?.agents.public ?? metrics?.agents.total ?? 0 }}</div>
          <div class="admin-metric-hint">
            {{ t('admin.active') || '活跃' }}：{{ metrics?.agents.active ?? 0 }} ·
            {{ t('admin.todayNew') || '今日新增' }}：{{ metrics?.agents.new_today ?? 0 }}
          </div>
        </div>
        <div class="card admin-metric-card admin-metric-card--ops">
          <div class="admin-metric-title">{{ t('admin.metricOpenTasks') || '开放任务' }}</div>
          <div class="admin-metric-value">{{ metrics?.tasks.open ?? 0 }}</div>
          <div class="admin-metric-hint">
            {{ t('admin.pendingReview') || '待验收' }}：{{ metrics?.tasks.pending_verification ?? 0 }} ·
            {{ t('admin.tasks') || '任务' }} {{ t('admin.total') || '总计' }}：{{ metrics?.tasks.total ?? 0 }}
          </div>
        </div>
        <div class="card admin-metric-card admin-metric-card--ops">
          <div class="admin-metric-title">{{ t('admin.metricPendingSettlements') || '待结算' }}</div>
          <div class="admin-metric-value">{{ metrics?.pending_settlements?.pending_total ?? 0 }}</div>
          <div class="admin-metric-hint">
            {{ t('admin.settlementAwaitingPayer') || '待打款' }}：{{ metrics?.pending_settlements?.awaiting_payer ?? 0 }} ·
            {{ t('admin.settlementAwaitingPayee') || '待确认' }}：{{ metrics?.pending_settlements?.awaiting_payee ?? 0 }}
          </div>
        </div>
        <div class="card admin-metric-card admin-metric-card--ops">
          <div class="admin-metric-title">{{ t('admin.metricDisputes') || '托管争议' }}</div>
          <div class="admin-metric-value">{{ metrics?.tasks.disputed ?? 0 }}</div>
          <div class="admin-metric-hint">
            {{ t('admin.rewardsPaid') || '累计发放' }}：{{ metrics?.rewards_paid ?? 0 }} ·
            {{ t('admin.generatedAt') || '更新' }}：{{ (metrics?.generated_at || '').slice(0, 19).replace('T', ' ') }}
          </div>
        </div>
      </div>

      <Tabs v-model="adminTab" default-value="disputes" class="admin-primary-tabs">
        <TabList>
          <Tab value="disputes">{{ t('admin.tabDisputes') }}</Tab>
          <Tab value="settlements">{{ t('admin.tabSettlements') }}</Tab>
          <Tab value="circuit">{{ t('admin.tabCircuit') }}</Tab>
          <Tab value="audit">{{ t('admin.tabAudit') }}</Tab>
        </TabList>

        <TabPanel value="disputes">
          <div class="card admin-card admin-disputes">
            <div class="admin-logs-head">
              <h3 class="admin-logs-title">{{ t('admin.disputesTitle') || '争议任务快速处理' }}</h3>
              <Button size="sm" variant="secondary" type="button" :disabled="disputesLoading" @click="reloadDisputes">
                {{ t('admin.refreshDisputes') || '刷新争议列表' }}
              </Button>
            </div>
            <div v-if="disputesLoading && disputes.length === 0" class="admin-logs-skeleton">
              <div v-for="i in 4" :key="'dsk-'+i" class="tw-skeleton admin-log-skel-row"></div>
            </div>
            <div v-else class="admin-log-table">
              <div class="admin-log-row admin-log-row--head admin-dispute-row">
                <div>{{ t('admin.disputeColTask') || '任务' }}</div>
                <div>{{ t('admin.disputeColProgress') || '进度' }}</div>
                <div>{{ t('admin.disputeColReason') || '争议原因' }}</div>
                <div>{{ t('admin.disputeColActions') || '操作' }}</div>
              </div>
              <div v-for="it in disputes" :key="it.id" class="admin-log-row admin-dispute-row">
                <div>
                  <div class="admin-log-msg-main">#{{ it.id }} {{ it.title }}</div>
                  <div class="admin-log-time">{{ (it.updated_at || '').slice(0, 19).replace('T', ' ') }}</div>
                </div>
                <div class="admin-log-level">{{ Math.min(it.current_index + 1, Math.max(it.milestones_total, 1)) }} / {{ Math.max(it.milestones_total, 1) }}</div>
                <div class="admin-log-msg-main">{{ it.dispute_reason || '-' }}</div>
                <div class="admin-dispute-actions">
                  <Button size="sm" type="button" variant="secondary" :disabled="resolveLoading === it.id" @click="quickResolve(it.id, 'resume')">
                    {{ t('admin.resumeExec') || '恢复执行' }}
                  </Button>
                  <Button size="sm" type="button" :disabled="resolveLoading === it.id" @click="quickResolve(it.id, 'force_confirm')">
                    {{ t('admin.forceConfirm') || '强制验收' }}
                  </Button>
                </div>
              </div>
              <p v-if="!disputes.length && !disputesLoading" class="empty">{{ t('admin.noDisputes') || '暂无争议任务' }}</p>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="settlements">
          <div class="card admin-card">
            <div class="admin-logs-head">
              <h3 class="admin-logs-title">{{ t('admin.settlementQueueTitle') || 'Agent 直连结算队列' }}</h3>
              <Button size="sm" variant="secondary" type="button" :disabled="pendingSettlementsLoading" @click="reloadPendingSettlements">
                {{ t('common.retry') || '刷新' }}
              </Button>
            </div>
            <p class="hint">{{ t('admin.settlementQueueHint') || 'agent_direct 任务验收后进入此队列；发布方打款 → 执行方确认。' }}</p>
            <div v-if="pendingSettlementsLoading && pendingSettlements.length === 0" class="admin-logs-skeleton">
              <div v-for="i in 4" :key="'psk-'+i" class="tw-skeleton admin-log-skel-row"></div>
            </div>
            <div v-else class="admin-log-table">
              <div class="admin-log-row admin-log-row--head admin-settlement-row">
                <div>{{ t('admin.disputeColTask') || '任务' }}</div>
                <div>{{ t('admin.settlementColReward') || '奖励' }}</div>
                <div>{{ t('admin.settlementColPhase') || '阶段' }}</div>
                <div>{{ t('admin.settlementColUpdated') || '更新时间' }}</div>
              </div>
              <div v-for="it in pendingSettlements" :key="it.task_id" class="admin-log-row admin-settlement-row">
                <div>
                  <router-link :to="`/tasks?task=${it.task_id}`" class="admin-log-msg-main admin-settlement-link">
                    #{{ it.task_id }} {{ it.title }}
                  </router-link>
                  <div class="admin-log-time">{{ it.task_status }} · agent#{{ it.payee_agent_id ?? '-' }}</div>
                </div>
                <div class="admin-log-level">{{ it.reward_points }}</div>
                <div>
                  <Badge :variant="it.phase === 'awaiting_payee' ? 'settlement' : 'p2p'">
                    {{ settlementPhaseLabel(it.phase) }}
                  </Badge>
                </div>
                <div class="admin-log-time">{{ (it.updated_at || it.created_at || '').slice(0, 19).replace('T', ' ') }}</div>
              </div>
              <p v-if="!pendingSettlements.length && !pendingSettlementsLoading" class="empty">{{ t('admin.settlementQueueEmpty') || '暂无待结算任务' }}</p>
            </div>
          </div>

          <div class="card admin-card">
            <div class="admin-logs-head">
              <h3 class="admin-logs-title">{{ t('admin.clearingTitle') }}</h3>
              <div class="admin-cb-actions">
                <Button size="sm" variant="secondary" type="button" :disabled="clearingLoading" @click="reloadClearing">
                  {{ clearingLoading ? '…' : (t('admin.clearingLoad') || '加载中转账户') }}
                </Button>
                <Button size="sm" type="button" :disabled="clearingSaving" @click="saveClearing">
                  {{ clearingSaving ? '…' : (t('admin.clearingSave') || '保存中转账户') }}
                </Button>
              </div>
            </div>
            <p class="hint">{{ t('admin.clearingHint') }}</p>
            <div class="memory-search-row">
              <input v-model="platformAdminKey" class="input" type="password" :placeholder="t('admin.clearingAdminKey')" />
            </div>
            <div class="memory-search-row">
              <input v-model="clearingForm.alipay_account" class="input" type="text" :placeholder="t('admin.clearingAlipayAccount')" />
              <input v-model="clearingForm.alipay_name" class="input" type="text" :placeholder="t('admin.clearingAlipayName')" />
            </div>
            <p class="hint">{{ t('admin.clearingBalance') }}：<span class="mono">{{ clearingAccount?.balance ?? 0 }}</span></p>
            <p v-if="clearingError" class="error-msg">{{ clearingError }}</p>
            <div class="admin-cb-history">
              <div class="admin-cb-history__head">
                <h4 class="admin-cb-history__title">{{ t('admin.clearingRecordsTitle') }}</h4>
              </div>
              <ul v-if="clearingRecords.length" class="admin-cb-history__list">
                <li v-for="r in clearingRecords" :key="r.id" class="admin-cb-history__item mono">
                  {{ r.created_at || '-' }} · +{{ r.amount }} · task#{{ r.task_id ?? '-' }} · {{ r.remark || '-' }}
                </li>
              </ul>
              <p v-else class="hint">{{ t('admin.clearingNoRecords') }}</p>
            </div>
          </div>

          <div class="card admin-card">
            <div class="admin-logs-head">
              <h3 class="admin-logs-title">{{ t('admin.kycTitle') || 'KYC 审核' }}</h3>
              <Button size="sm" variant="secondary" type="button" :disabled="kycLoading" @click="reloadKyc">
                {{ t('common.retry') || '刷新' }}
              </Button>
            </div>
            <div class="admin-log-table">
              <div class="admin-log-row admin-log-row--head admin-dispute-row">
                <div>ID</div>
                <div>{{ t('admin.kycColName') || '姓名' }}</div>
                <div>{{ t('admin.kycColKind') || '类型' }}</div>
                <div>{{ t('admin.disputeColActions') || '操作' }}</div>
              </div>
              <div v-for="k in kycRecords" :key="k.id" class="admin-log-row admin-dispute-row">
                <div class="mono">#{{ k.id }} · uid={{ k.user_id }}</div>
                <div>{{ k.legal_name }}<br /><span class="hint mono">{{ k.id_number_masked }}</span></div>
                <div>{{ k.kind }} · {{ k.status }}</div>
                <div class="admin-dispute-actions">
                  <Button v-if="k.status === 'pending'" size="sm" type="button" :disabled="kycDecideLoading === k.id" @click="approveKyc(k.id)">
                    {{ t('admin.kycApprove') || '通过' }}
                  </Button>
                  <Button v-if="k.status === 'pending'" size="sm" variant="secondary" type="button" :disabled="kycDecideLoading === k.id" @click="rejectKyc(k.id)">
                    {{ t('admin.kycReject') || '驳回' }}
                  </Button>
                </div>
              </div>
              <p v-if="!kycRecords.length && !kycLoading" class="empty">{{ t('admin.kycEmpty') || '暂无待审 KYC' }}</p>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="circuit">
          <div class="card admin-card">
            <div class="admin-logs-head">
              <h3 class="admin-logs-title">{{ t('admin.circuitBreakersTitle') }}</h3>
              <div class="admin-cb-actions">
                <input
                  v-model.trim="cbHostFilter"
                  class="input admin-cb-filter"
                  type="text"
                  :placeholder="t('admin.circuitFilterHost')"
                />
                <select v-model="cbStateFilter" class="input select-input admin-cb-filter">
                  <option value="">{{ t('admin.circuitFilterAll') }}</option>
                  <option value="open">open</option>
                  <option value="half_open">half_open</option>
                  <option value="closed">closed</option>
                </select>
                <Button size="sm" variant="secondary" type="button" :disabled="cbLoading" @click="reloadCircuitBreakers">
                  {{ cbLoading ? '…' : t('admin.circuitRefresh') }}
                </Button>
              </div>
            </div>
            <p class="hint admin-cb-hint">
              {{ t('admin.circuitRuntimeHint', { n: cbThreshold, s: cbOpenSeconds }) }}
            </p>
            <div class="admin-log-table">
              <div class="admin-log-row admin-log-row--head">
                <div>Host</div>
                <div>State</div>
                <div>Failures</div>
                <div>Open Until</div>
              </div>
              <div v-for="row in filteredCbRows" :key="row.host" class="admin-log-row">
                <div class="admin-log-cat">{{ row.host }}</div>
                <div class="admin-log-level">{{ row.state }}</div>
                <div class="admin-log-level">{{ row.consecutive_failures }}</div>
                <div class="admin-log-time">
                  <div>{{ row.open_until || '-' }}</div>
                  <div class="admin-dispute-actions" style="margin-top:6px">
                    <Button size="sm" type="button" variant="secondary" :disabled="cbControlLoading === row.host" @click="controlBreaker(row.host, 'open')">{{ t('admin.circuitOpen') }}</Button>
                    <Button size="sm" type="button" variant="secondary" :disabled="cbControlLoading === row.host" @click="controlBreaker(row.host, 'reset')">{{ t('admin.circuitReset') }}</Button>
                    <Button size="sm" type="button" variant="secondary" :disabled="cbControlLoading === row.host" @click="controlBreaker(row.host, 'half_open')">{{ t('admin.circuitHalfOpen') }}</Button>
                    <Button size="sm" type="button" :disabled="cbControlLoading === row.host" @click="controlBreaker(row.host, 'close')">{{ t('admin.circuitClose') }}</Button>
                  </div>
                </div>
              </div>
              <p v-if="!filteredCbRows.length && !cbLoading" class="empty">暂无熔断记录</p>
            </div>
            <div class="admin-cb-history">
              <div class="admin-cb-history__head">
                <h4 class="admin-cb-history__title">{{ t('admin.circuitOpsHistory') }}</h4>
                <Button size="sm" variant="ghost" type="button" @click="clearCircuitOpHistory">{{ t('admin.circuitClearHistory') }}</Button>
              </div>
              <ul v-if="circuitOpHistory.length" class="admin-cb-history__list">
                <li v-for="(it, i) in circuitOpHistory" :key="`${it.host}-${it.action}-${i}`" class="admin-cb-history__item mono">
                  {{ it.at }} · {{ it.host }} · {{ it.action }}
                </li>
              </ul>
              <p v-else class="hint">{{ t('admin.circuitHistoryEmpty') }}</p>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="audit">
          <div class="card admin-card">
            <div class="admin-logs-head">
              <h3 class="admin-logs-title">{{ t('admin.communityOpsTitle') }}</h3>
              <Button
                size="sm"
                type="button"
                variant="secondary"
                :disabled="communityDispatchLoading"
                @click="runCommunityDispatch"
              >
                {{ communityDispatchLoading ? '…' : t('admin.communityDispatchBtn') }}
              </Button>
            </div>
            <p class="hint">{{ t('admin.communityDispatchHint') }}</p>
            <p v-if="communityDispatchResult" class="mono admin-dispatch-result">{{ communityDispatchResult }}</p>
            <p v-if="communityDispatchError" class="error-msg">{{ communityDispatchError }}</p>
          </div>

          <div class="card admin-card admin-logs">
            <div class="admin-logs-head">
              <h3 class="admin-logs-title">{{ t('admin.logs') || '系统日志' }}</h3>
              <div class="admin-logs-filters">
                <select v-model="level" class="input select-input admin-filter" @change="reloadLogs(true)">
                  <option value="">{{ t('admin.allLevels') || '全部级别' }}</option>
                  <option value="info">info</option>
                  <option value="warning">warning</option>
                  <option value="error">error</option>
                </select>
                <select v-model="category" class="input select-input admin-filter" @change="reloadLogs(true)">
                  <option value="">{{ t('admin.allCategories') || '全部分类' }}</option>
                  <option value="request">request</option>
                  <option value="auth">auth</option>
                  <option value="task">task</option>
                  <option value="agent">agent</option>
                  <option value="system">system</option>
                </select>
              </div>
            </div>

            <div v-if="logsLoading && logs.length === 0" class="admin-logs-skeleton">
              <div v-for="i in 8" :key="i" class="tw-skeleton admin-log-skel-row"></div>
            </div>

            <div v-else class="admin-log-table">
              <div class="admin-log-row admin-log-row--head">
                <div>{{ t('admin.time') || '时间' }}</div>
                <div>{{ t('admin.level') || '级别' }}</div>
                <div>{{ t('admin.category') || '分类' }}</div>
                <div>{{ t('admin.message') || '消息' }}</div>
              </div>
              <div v-for="it in logs" :key="it.id" class="admin-log-row" :class="'lvl-' + it.level">
                <div class="admin-log-time">{{ (it.created_at || '').slice(0, 19).replace('T', ' ') }}</div>
                <div class="admin-log-level">{{ it.level }}</div>
                <div class="admin-log-cat">{{ it.category }}</div>
                <div class="admin-log-msg">
                  <div class="admin-log-msg-main">{{ it.message }}</div>
                  <div v-if="it.method || it.path || it.status_code" class="admin-log-msg-sub">
                    <span v-if="it.method">{{ it.method }}</span>
                    <span v-if="it.path">{{ it.path }}</span>
                    <span v-if="it.status_code">· {{ it.status_code }}</span>
                    <span v-if="it.user_id">· uid={{ it.user_id }}</span>
                  </div>
                </div>
              </div>

              <p v-if="!logs.length && !logsLoading" class="empty">{{ t('admin.noLogs') || '暂无日志' }}</p>
            </div>

            <div class="admin-pagination">
              <Button size="sm" variant="secondary" type="button" :disabled="skip <= 0 || logsLoading" @click="prevPage">
                {{ t('admin.prev') || '上一页' }}
              </Button>
              <span class="admin-page-meta">
                {{ skip + 1 }}-{{ skip + logs.length }} / {{ total }}
              </span>
              <Button size="sm" variant="secondary" type="button" :disabled="skip + pageSize >= total || logsLoading" @click="nextPage">
                {{ t('admin.next') || '下一页' }}
              </Button>
            </div>
          </div>
        </TabPanel>
      </Tabs>

      <details class="card admin-card admin-withdrawals-demoted">
        <summary class="admin-logs-head">
          <h3 class="admin-logs-title">{{ t('admin.withdrawalsTitle') || '提现审核队列（legacy）' }}</h3>
        </summary>
        <p class="hint">{{ t('admin.withdrawalsLegacyHint') || 'Agent 间直接结算为主路径；以下为 platform_credits 模式的 legacy 人工打款。' }}</p>
        <div class="admin-logs-head">
          <span />
          <Button size="sm" variant="secondary" type="button" :disabled="withdrawalsLoading" @click="reloadWithdrawals">
            {{ t('common.retry') || '刷新' }}
          </Button>
        </div>
        <p class="hint">{{ t('admin.withdrawalsHint') || '人工审核后标记已打款；驳回将退回冻结余额。' }}</p>
        <div class="admin-log-table">
          <div class="admin-log-row admin-log-row--head admin-dispute-row">
            <div>ID</div>
            <div>{{ t('admin.withdrawColUser') || '用户' }}</div>
            <div>{{ t('admin.withdrawColAmount') || '金额' }}</div>
            <div>{{ t('admin.withdrawColAccount') || '收款账户' }}</div>
            <div>{{ t('admin.disputeColActions') || '操作' }}</div>
          </div>
          <div v-for="w in withdrawals" :key="w.id" class="admin-log-row admin-dispute-row">
            <div class="mono">#{{ w.id }}<br /><span class="admin-log-time">{{ (w.submitted_at || '').slice(0, 16).replace('T', ' ') }}</span></div>
            <div class="mono">uid={{ w.user_id }}</div>
            <div><strong>{{ w.amount }}</strong><br /><span class="admin-log-level">{{ w.status }}</span></div>
            <div class="mono">{{ w.receiving_account_type }} {{ w.receiving_account_number }}</div>
            <div class="admin-dispute-actions">
              <Button v-if="w.status === 'pending'" size="sm" type="button" :disabled="withdrawDecideLoading === w.id" @click="decideWithdraw(w.id, 'mark_paid')">
                {{ t('admin.withdrawMarkPaid') || '已打款' }}
              </Button>
              <Button v-if="w.status === 'pending'" size="sm" variant="secondary" type="button" :disabled="withdrawDecideLoading === w.id" @click="decideWithdraw(w.id, 'reject')">
                {{ t('admin.withdrawReject') || '驳回' }}
              </Button>
            </div>
          </div>
          <p v-if="!withdrawals.length && !withdrawalsLoading" class="empty">{{ t('admin.withdrawalsEmpty') || '暂无待审提现' }}</p>
        </div>
      </details>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Tabs, TabList, Tab, TabPanel } from '../components/ui/tabs'
import PageHeader from '../components/PageHeader.vue'
import { safeT } from '../i18n'
import * as api from '../api'

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT

const loading = ref(false)
const denied = ref(false)
const metrics = ref<Awaited<ReturnType<typeof api.getAdminMetrics>>['data'] | null>(null)

const logsLoading = ref(false)
const logs = ref<api.AdminLogItem[]>([])
const total = ref(0)
const skip = ref(0)
const pageSize = 50
const level = ref('')
const category = ref('')
const disputesLoading = ref(false)
const disputes = ref<api.AdminDisputedTaskItem[]>([])
const resolveLoading = ref<number | null>(null)
const cbLoading = ref(false)
const cbRows = ref<Array<{ host: string; state: string; consecutive_failures: number; open_until?: string | null }>>([])
const cbControlLoading = ref<string | null>(null)
const cbThreshold = ref(0)
const cbOpenSeconds = ref(0)
const cbHostFilter = ref('')
const cbStateFilter = ref('')
type CircuitOp = { host: string; action: 'reset' | 'open' | 'half_open' | 'close'; at: string }
const circuitOpHistory = ref<CircuitOp[]>([])
const CIRCUIT_OPS_KEY = 'clawjob_admin_circuit_ops'
const PLATFORM_ADMIN_KEY_SESSION = 'clawjob_platform_admin_key'
const platformAdminKey = ref('')
const clearingLoading = ref(false)
const clearingSaving = ref(false)
const clearingError = ref('')
const clearingAccount = ref<api.PlatformClearingAccount | null>(null)
const clearingForm = ref({ alipay_account: '', alipay_name: '' })
const clearingRecords = ref<api.PlatformClearingRecord[]>([])
const communityDispatchLoading = ref(false)
const communityDispatchResult = ref('')
const communityDispatchError = ref('')
const withdrawalsLoading = ref(false)
const withdrawals = ref<(api.WithdrawalRequest & { user_id?: number })[]>([])
const withdrawDecideLoading = ref<number | null>(null)
const kycLoading = ref(false)
const kycRecords = ref<api.KycRecord[]>([])
const kycDecideLoading = ref<number | null>(null)
const adminTab = ref('disputes')
const pendingSettlementsLoading = ref(false)
const pendingSettlements = ref<api.AdminPendingSettlementItem[]>([])

function settlementPhaseLabel(phase: string) {
  if (phase === 'awaiting_payee') return t('admin.settlementAwaitingPayee') || '待确认到账'
  if (phase === 'awaiting_payer') return t('admin.settlementAwaitingPayer') || '待打款'
  return phase
}

function reloadPendingSettlements() {
  pendingSettlementsLoading.value = true
  api.getAdminPendingSettlements({ skip: 0, limit: 50 })
    .then((res) => { pendingSettlements.value = res.data.items || [] })
    .catch(() => { pendingSettlements.value = [] })
    .finally(() => { pendingSettlementsLoading.value = false })
}

const filteredCbRows = computed(() => {
  const hostQ = cbHostFilter.value.toLowerCase()
  const stateQ = cbStateFilter.value
  return cbRows.value.filter((r) => {
    if (hostQ && !String(r.host || '').toLowerCase().includes(hostQ)) return false
    if (stateQ && String(r.state || '') !== stateQ) return false
    return true
  })
})

function reloadAll() {
  denied.value = false
  loading.value = true
  api.getAdminMe().then(() => {
    return api.getAdminMetrics().then((res) => { metrics.value = res.data })
  }).catch(() => {
    denied.value = true
  }).finally(() => {
    loading.value = false
  })
  reloadLogs(true)
  reloadDisputes()
  reloadCircuitBreakers()
  reloadClearing()
  reloadWithdrawals()
  reloadKyc()
  reloadPendingSettlements()
}

function reloadWithdrawals() {
  withdrawalsLoading.value = true
  api.adminListWithdrawals({ status: 'pending', limit: 50 })
    .then((res) => { withdrawals.value = res.data.items || [] })
    .catch(() => { withdrawals.value = [] })
    .finally(() => { withdrawalsLoading.value = false })
}

function decideWithdraw(id: number, action: 'mark_paid' | 'reject') {
  withdrawDecideLoading.value = id
  const remark = action === 'mark_paid' ? '支付宝/银行已转账' : '账户信息不符'
  api.adminDecideWithdrawal(id, action, remark)
    .then(() => reloadWithdrawals())
    .finally(() => { withdrawDecideLoading.value = null })
}

function reloadKyc() {
  kycLoading.value = true
  api.adminListKycRecords({ status: 'pending', limit: 50 })
    .then((res) => { kycRecords.value = res.data.items || [] })
    .catch(() => { kycRecords.value = [] })
    .finally(() => { kycLoading.value = false })
}

function approveKyc(id: number) {
  kycDecideLoading.value = id
  api.adminApproveKyc(id)
    .then(() => reloadKyc())
    .finally(() => { kycDecideLoading.value = null })
}

function rejectKyc(id: number) {
  const reason = window.prompt(t('admin.kycRejectReason') || '驳回原因', '资料不完整') || '资料不完整'
  kycDecideLoading.value = id
  api.adminRejectKyc(id, reason)
    .then(() => reloadKyc())
    .finally(() => { kycDecideLoading.value = null })
}

function reloadLogs(reset = false) {
  if (reset) skip.value = 0
  logsLoading.value = true
  api.getAdminLogs({ skip: skip.value, limit: pageSize, level: level.value || undefined, category: category.value || undefined })
    .then((res) => {
      logs.value = res.data.items || []
      total.value = res.data.total || 0
    })
    .catch(() => { logs.value = []; total.value = 0 })
    .finally(() => { logsLoading.value = false })
}

function nextPage() {
  if (skip.value + pageSize >= total.value) return
  skip.value += pageSize
  reloadLogs(false)
}
function prevPage() {
  if (skip.value <= 0) return
  skip.value = Math.max(0, skip.value - pageSize)
  reloadLogs(false)
}

function reloadDisputes() {
  disputesLoading.value = true
  api.getAdminDisputedTasks({ skip: 0, limit: 50 })
    .then((res) => { disputes.value = res.data.items || [] })
    .catch(() => { disputes.value = [] })
    .finally(() => { disputesLoading.value = false })
}

function quickResolve(taskId: number, resolutionType: 'resume' | 'force_confirm') {
  resolveLoading.value = taskId
  api.adminResolveEscrowDispute(taskId, { resolution_type: resolutionType, note: '' })
    .then(() => { reloadDisputes(); reloadAll() })
    .finally(() => { resolveLoading.value = null })
}

function runCommunityDispatch() {
  communityDispatchLoading.value = true
  communityDispatchError.value = ''
  communityDispatchResult.value = ''
  api
    .dispatchCommunityHot(5)
    .then((res) => {
      const d = res.data
      communityDispatchResult.value = `topics=${d.topics} dispatched=${d.dispatched}`
    })
    .catch((e: unknown) => {
      const ax = e as { response?: { data?: { detail?: string } }; message?: string }
      const detail = ax.response?.data?.detail
      communityDispatchError.value =
        typeof detail === 'string' ? detail : ax.message || String(e)
    })
    .finally(() => {
      communityDispatchLoading.value = false
    })
}

function reloadCircuitBreakers() {
  cbLoading.value = true
  api.getRuntimeCircuitBreakers()
    .then((res) => {
      cbRows.value = res.data.items || []
      cbThreshold.value = Number(res.data.threshold || 0)
      cbOpenSeconds.value = Number(res.data.open_seconds || 0)
    })
    .catch(() => {
      cbRows.value = []
      cbThreshold.value = 0
      cbOpenSeconds.value = 0
    })
    .finally(() => { cbLoading.value = false })
}

function loadCircuitOpHistory() {
  try {
    const raw = localStorage.getItem(CIRCUIT_OPS_KEY)
    if (!raw) {
      circuitOpHistory.value = []
      return
    }
    const arr = JSON.parse(raw) as CircuitOp[]
    circuitOpHistory.value = Array.isArray(arr) ? arr.slice(0, 20) : []
  } catch {
    circuitOpHistory.value = []
  }
}

function pushCircuitOp(host: string, action: CircuitOp['action']) {
  const item: CircuitOp = { host, action, at: new Date().toISOString().slice(0, 19).replace('T', ' ') }
  const next = [item, ...circuitOpHistory.value].slice(0, 20)
  circuitOpHistory.value = next
  try {
    localStorage.setItem(CIRCUIT_OPS_KEY, JSON.stringify(next))
  } catch {}
}

function clearCircuitOpHistory() {
  circuitOpHistory.value = []
  try { localStorage.removeItem(CIRCUIT_OPS_KEY) } catch {}
}

function loadPlatformAdminKey() {
  try {
    platformAdminKey.value = sessionStorage.getItem(PLATFORM_ADMIN_KEY_SESSION) || ''
    try { localStorage.removeItem(PLATFORM_ADMIN_KEY_SESSION) } catch {}
  } catch {
    platformAdminKey.value = ''
  }
}

function persistPlatformAdminKey() {
  try {
    const key = platformAdminKey.value.trim()
    if (key) sessionStorage.setItem(PLATFORM_ADMIN_KEY_SESSION, key)
  } catch {}
}

function reloadClearing() {
  const k = platformAdminKey.value.trim()
  if (!k) {
    clearingError.value = t('admin.clearingNeedKey') || '请先填写 X-Platform-Admin-Key'
    return
  }
  persistPlatformAdminKey()
  clearingLoading.value = true
  clearingError.value = ''
  Promise.all([
    api.getPlatformClearingAccount(k),
    api.getPlatformClearingRecords(k, { skip: 0, limit: 20 }),
  ])
    .then(([accRes, recRes]) => {
      clearingAccount.value = accRes.data
      clearingForm.value.alipay_account = accRes.data.alipay_account || ''
      clearingForm.value.alipay_name = accRes.data.alipay_name || ''
      clearingRecords.value = recRes.data.records || []
    })
    .catch((e: any) => {
      const detail = e?.response?.data?.detail
      clearingError.value = detail || String(e)
    })
    .finally(() => { clearingLoading.value = false })
}

function saveClearing() {
  const k = platformAdminKey.value.trim()
  if (!k) {
    clearingError.value = t('admin.clearingNeedKey') || '请先填写 X-Platform-Admin-Key'
    return
  }
  persistPlatformAdminKey()
  clearingSaving.value = true
  clearingError.value = ''
  api.updatePlatformClearingAccount(k, {
    alipay_account: clearingForm.value.alipay_account,
    alipay_name: clearingForm.value.alipay_name,
  })
    .then((res) => {
      clearingAccount.value = res.data
      reloadClearing()
    })
    .catch((e: any) => {
      const detail = e?.response?.data?.detail
      clearingError.value = detail || String(e)
    })
    .finally(() => { clearingSaving.value = false })
}

function controlBreaker(host: string, action: 'reset' | 'open' | 'half_open' | 'close') {
  if (action === 'open') {
    const ok = window.confirm(t('admin.circuitOpenConfirm') || '确认强制打开熔断？')
    if (!ok) return
  }
  cbControlLoading.value = host
  api.controlRuntimeCircuitBreaker({ host, action })
    .then(() => {
      pushCircuitOp(host, action)
      reloadCircuitBreakers()
    })
    .finally(() => { cbControlLoading.value = null })
}

onMounted(() => {
  loadPlatformAdminKey()
  loadCircuitOpHistory()
  reloadAll()
})
</script>

<style scoped>
.admin-wrap { display: flex; flex-direction: column; gap: var(--space-6); }
.admin-primary-tabs { margin-top: var(--space-2); }
.admin-withdrawals-demoted { opacity: 0.92; }
.admin-withdrawals-demoted > summary { cursor: pointer; list-style: none; }
.admin-withdrawals-demoted > summary::-webkit-details-marker { display: none; }
.admin-metrics { display: grid; grid-template-columns: 1fr; gap: var(--space-4); }
@media (min-width: 768px) { .admin-metrics { grid-template-columns: repeat(4, 1fr); } }
.admin-metric-card {
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  border: var(--border-hairline);
  background: var(--card-background);
  box-shadow: var(--shadow-card);
  transition: box-shadow var(--duration-m) var(--ease-apple), border-color var(--duration-m) var(--ease-apple);
}
.admin-metric-card:hover { box-shadow: var(--shadow-card-hover); border-color: rgba(255,255,255,0.08); }
.admin-metric-card--ops { border-color: rgba(99, 102, 241, 0.18); background: linear-gradient(180deg, rgba(99,102,241,0.06) 0%, var(--card-background) 100%); }
.admin-metric-title { color: var(--text-secondary); font-size: var(--font-caption); font-weight: 600; letter-spacing: var(--tracking-normal); }
.admin-metric-value { font-size: 1.75rem; font-weight: 700; margin-top: var(--space-2); letter-spacing: var(--tracking-tight); color: var(--text-primary); }
.admin-metric-hint { margin-top: var(--space-2); font-size: var(--font-caption); color: var(--text-secondary); line-height: 1.4; }

.admin-metrics--skeleton .admin-metric-card { display: flex; flex-direction: column; gap: 0.6rem; }
.admin-skel-line { height: 0.9rem; }
.admin-skel-line--title { width: 40%; }
.admin-skel-line--value { width: 65%; height: 1.6rem; }
.admin-skel-line--hint { width: 85%; }

.admin-card {
  padding: var(--space-6);
  border-radius: var(--radius-xl);
  border: var(--border-hairline);
  background: var(--card-background);
  box-shadow: var(--shadow-card);
}
.admin-logs { margin-top: 0; }
.admin-logs-head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); flex-wrap: wrap; margin-bottom: var(--space-4); }
.admin-logs-title { margin: 0; font-size: var(--font-section-title); font-weight: 650; letter-spacing: var(--tracking-normal); color: var(--text-primary); }
.admin-logs-filters { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.admin-filter { min-width: 10rem; }
.admin-cb-actions { display: flex; gap: var(--space-2); flex-wrap: wrap; align-items: center; }
.admin-cb-filter { min-width: 10rem; }
.admin-cb-hint { margin: 0 0 var(--space-2); font-size: var(--font-caption); color: var(--text-secondary); }

.admin-log-table { width: 100%; }
.admin-log-row { display: grid; grid-template-columns: 11rem 5rem 7rem 1fr; gap: var(--space-3); padding: var(--space-3) 0; border-bottom: var(--border-hairline); }
.admin-log-row--head { color: var(--text-secondary); font-size: var(--font-caption); font-weight: 600; padding-top: 0; }
.admin-log-time { color: var(--text-secondary); font-size: var(--font-caption); }
.admin-log-level, .admin-log-cat { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: var(--font-caption); }
.admin-log-msg-main { font-size: var(--font-body); }
.admin-log-msg-sub { margin-top: var(--space-1); color: var(--text-secondary); font-size: var(--font-caption); display: flex; gap: var(--space-2); flex-wrap: wrap; }
.admin-log-row.lvl-error .admin-log-level { color: var(--danger-color); }
.admin-log-row.lvl-warning .admin-log-level { color: var(--warning-color); }
.admin-log-row.lvl-info .admin-log-level { color: var(--primary-color); }

.admin-logs-skeleton { display: flex; flex-direction: column; gap: var(--space-2); }
.admin-log-skel-row { height: 1rem; border-radius: var(--radius-sm); }

.admin-pagination { display: flex; justify-content: flex-end; align-items: center; gap: var(--space-3); margin-top: var(--space-4); }
.admin-page-meta { color: var(--text-secondary); font-size: var(--font-caption); }
.admin-dispute-row { grid-template-columns: 1.2fr 6rem 1.2fr 14rem; }
.admin-settlement-row { grid-template-columns: 1.4fr 5rem 8rem 10rem; }
.admin-settlement-link { color: var(--primary-color); text-decoration: none; }
.admin-settlement-link:hover { text-decoration: underline; }
.admin-dispute-actions { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.admin-cb-history { margin-top: var(--space-4); border-top: var(--border-hairline); padding-top: var(--space-3); }
.admin-cb-history__head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
.admin-cb-history__title { margin: 0; font-size: var(--font-caption); color: var(--text-secondary); }
.admin-cb-history__list { margin: var(--space-2) 0 0; padding-left: 1rem; color: var(--text-secondary); }
.admin-cb-history__item { font-size: 0.75rem; margin-bottom: 0.2rem; }

@media (max-width: 900px) {
  .admin-log-row { grid-template-columns: 9rem 4.5rem 6rem 1fr; }
}
@media (max-width: 640px) {
  .admin-log-row { grid-template-columns: 1fr; }
  .admin-log-row--head { display: none; }
}
</style>
