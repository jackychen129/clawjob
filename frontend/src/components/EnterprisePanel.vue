<template>
  <div class="enterprise-panel">
    <!-- ============ 订阅与席位（D-18） ============ -->
    <section class="card card-content ent-section">
      <header class="ent-head">
        <h3>{{ t('enterprise.subTitle') || '订阅与席位' }}</h3>
        <p class="hint">{{ t('enterprise.subHint') || '订阅可获得月度赠点、佣金折扣与企业级能力（RFQ、优先撮合、Sandbox 配额）。' }}</p>
      </header>

      <div v-if="subLoading" class="ent-skel">{{ t('common.loading') }}</div>
      <template v-else>
        <div class="ent-current">
          <span class="ent-current__label">{{ t('enterprise.currentTier') || '当前档位' }}</span>
          <Badge variant="p2p" class="ent-current__badge">{{ currentTierName }}</Badge>
          <span v-if="subscription?.renews_at" class="hint mono">{{ t('enterprise.renewsAt') || '续费日' }}: {{ formatDate(subscription.renews_at) }}</span>
          <Button
            v-if="subscription && subscription.tier !== 'free'"
            size="sm"
            variant="ghost"
            type="button"
            :disabled="subBusy"
            @click="doCancel"
          >{{ t('enterprise.cancelSub') || '取消订阅' }}</Button>
        </div>

        <div class="ent-plan-grid">
          <article
            v-for="p in plans"
            :key="p.code"
            class="ent-plan-card"
            :class="{ 'ent-plan-card--current': p.code === subscription?.tier }"
          >
            <div class="ent-plan-card__top">
              <h4 class="ent-plan-card__name">{{ p.name }}</h4>
              <Badge v-if="p.code === subscription?.tier" variant="outline">{{ t('enterprise.planCurrent') || '当前' }}</Badge>
            </div>
            <p class="ent-plan-card__price">
              <strong class="mono">{{ p.monthly_price_credits }}</strong>
              <span class="ent-plan-card__unit">{{ t('enterprise.creditsPerMonth') || '点 / 月' }}</span>
            </p>
            <ul class="ent-plan-card__meta">
              <li>{{ t('enterprise.monthlyCredits') || '月度赠点' }}: <strong class="mono">{{ p.monthly_credits }}</strong></li>
              <li>{{ t('enterprise.seats') || '席位' }}: <strong class="mono">{{ p.seat_quota }}</strong></li>
              <li>{{ t('enterprise.commissionDiscount') || '佣金折扣' }}: <strong class="mono">{{ (p.commission_discount_bp / 100).toFixed(0) }}%</strong></li>
            </ul>
            <ul v-if="p.features?.length" class="ent-plan-card__features">
              <li v-for="f in p.features" :key="f">{{ featureLabel(f) }}</li>
            </ul>
            <Button
              size="sm"
              class="ent-plan-card__cta"
              :disabled="subBusy || p.code === subscription?.tier"
              @click="doSubscribe(p.code)"
            >{{ p.code === subscription?.tier ? (t('enterprise.planCurrent') || '当前') : (t('enterprise.subscribe') || '订阅') }}</Button>
          </article>
        </div>
        <p v-if="subError" class="error-msg" role="alert">{{ subError }}</p>
      </template>
    </section>

    <!-- ============ 工作区 / 团队（D-17） ============ -->
    <section class="card card-content ent-section">
      <header class="ent-head">
        <h3>{{ t('enterprise.wsTitle') || '工作区 / 团队' }}</h3>
        <p class="hint">{{ t('enterprise.wsHint') || '企业账户可创建工作区，多成员协作、共享余额与账单，team / enterprise 档需先完成 KYB 企业认证。' }}</p>
      </header>

      <div v-if="wsLoading" class="ent-skel">{{ t('common.loading') }}</div>
      <template v-else>
        <ul v-if="workspaces.length" class="ent-ws-list">
          <li
            v-for="ws in workspaces"
            :key="ws.id"
            class="ent-ws-row"
            :class="{ active: ws.id === activeWorkspaceId, selected: ws.id === selectedWsId }"
          >
            <button type="button" class="ent-ws-row__main" @click="selectWorkspace(ws.id)">
              <span class="ent-ws-name">{{ ws.name }}</span>
              <Badge variant="outline" class="ent-ws-plan">{{ ws.plan }}</Badge>
              <span class="ent-ws-meta mono">{{ t('enterprise.seats') || '席位' }} {{ ws.seats }} · 💰 {{ ws.credits }} · {{ roleLabel(ws.my_role) }}</span>
              <Badge v-if="ws.id === activeWorkspaceId" variant="p2p" class="ent-ws-active-badge">{{ t('enterprise.activeWs') || '当前' }}</Badge>
            </button>
            <Button
              v-if="ws.id !== activeWorkspaceId"
              size="sm"
              variant="ghost"
              type="button"
              :disabled="wsBusy"
              @click="setActive(ws.id)"
            >{{ t('enterprise.setActive') || '设为当前' }}</Button>
          </li>
        </ul>
        <p v-else class="hint">{{ t('enterprise.noWorkspaces') || '尚无工作区，创建一个以开启团队协作。' }}</p>

        <!-- 创建工作区 -->
        <details class="ent-create" :open="!workspaces.length">
          <summary>{{ t('enterprise.createWs') || '创建工作区' }}</summary>
          <div class="ent-form-grid">
            <input v-model="createForm.name" class="input" :placeholder="t('enterprise.wsName') || '工作区名称'" />
            <select v-model="createForm.plan" class="input">
              <option value="free">free</option>
              <option value="team">team</option>
              <option value="enterprise">enterprise</option>
            </select>
            <input v-model="createForm.billing_email" class="input" type="email" :placeholder="t('enterprise.billingEmail') || '账单邮箱（可选）'" />
            <Button size="sm" type="button" :disabled="wsBusy || !createForm.name.trim()" @click="doCreateWorkspace">{{ t('enterprise.create') || '创建' }}</Button>
          </div>
          <p class="hint">{{ t('enterprise.kybHint') || 'team / enterprise 档需先在「钱包 → 法币/KYC」完成企业 KYB 认证。' }}</p>
        </details>

        <!-- 接受邀请 -->
        <details class="ent-create">
          <summary>{{ t('enterprise.acceptInvite') || '接受邀请' }}</summary>
          <div class="ent-form-inline">
            <input v-model="inviteToken" class="input" :placeholder="t('enterprise.inviteToken') || '邀请 token'" />
            <Button size="sm" type="button" :disabled="wsBusy || !inviteToken.trim()" @click="doAcceptInvite">{{ t('enterprise.join') || '加入' }}</Button>
          </div>
        </details>

        <!-- 选中工作区详情 -->
        <div v-if="selectedWs" class="ent-ws-detail">
          <h4 class="ent-ws-detail__title">{{ selectedWs.name }} · {{ t('enterprise.wsDetail') || '工作区详情' }}</h4>

          <div class="ent-ws-actions">
            <div class="ent-form-inline">
              <input v-model.number="rechargeAmount" type="number" min="1" class="input input-num" :placeholder="t('enterprise.rechargeAmount') || '充值点数'" />
              <Button size="sm" variant="secondary" type="button" :disabled="wsBusy || canBill === false" @click="doRecharge">{{ t('enterprise.recharge') || '充值' }}</Button>
            </div>
            <div class="ent-form-inline">
              <select v-model="wsPlanCode" class="input">
                <option value="team">team</option>
                <option value="enterprise">enterprise</option>
              </select>
              <Button size="sm" variant="secondary" type="button" :disabled="wsBusy || canBill === false" @click="doSubscribeWs">{{ t('enterprise.subscribeWs') || '订阅工作区' }}</Button>
            </div>
          </div>

          <h5 class="ent-members-title">{{ t('enterprise.members') || '成员' }}</h5>
          <ul class="ent-members">
            <li v-for="m in selectedWs.members" :key="m.id" class="ent-member-row">
              <span class="ent-member-name">{{ m.username || m.email || ('#' + m.user_id) }}</span>
              <select
                v-if="canManage"
                :value="m.role"
                class="input input-sm"
                :disabled="wsBusy || m.role === 'owner'"
                @change="onRoleChange(m.user_id, ($event.target as HTMLSelectElement).value)"
              >
                <option v-for="r in roleOptions" :key="r" :value="r">{{ roleLabel(r) }}</option>
              </select>
              <Badge v-else variant="outline">{{ roleLabel(m.role) }}</Badge>
              <Button
                v-if="canManage && m.role !== 'owner'"
                size="sm"
                variant="ghost"
                type="button"
                :disabled="wsBusy"
                @click="doRemoveMember(m.user_id)"
              >{{ t('enterprise.remove') || '移除' }}</Button>
            </li>
          </ul>

          <details v-if="canManage" class="ent-create">
            <summary>{{ t('enterprise.inviteMember') || '邀请成员' }}</summary>
            <div class="ent-form-inline">
              <input v-model="memberInvite.email" class="input" type="email" :placeholder="t('auth.email') || '邮箱'" />
              <select v-model="memberInvite.role" class="input">
                <option v-for="r in roleOptions.filter((x) => x !== 'owner')" :key="r" :value="r">{{ roleLabel(r) }}</option>
              </select>
              <Button size="sm" type="button" :disabled="wsBusy || !memberInvite.email.trim()" @click="doInvite">{{ t('enterprise.sendInvite') || '发送邀请' }}</Button>
            </div>
            <p v-if="lastInviteToken" class="hint mono ent-invite-token">{{ t('enterprise.inviteCreated') || '邀请已创建，token' }}: {{ lastInviteToken }}</p>
          </details>

          <p class="hint ent-rfq-link">{{ t('enterprise.rfqHint') || '批量发布（RFQ）可在「任务大厅 → 批量发布」页使用。' }}</p>
        </div>
        <p v-if="wsError" class="error-msg" role="alert">{{ wsError }}</p>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import * as api from '../api'
import { useToast } from '../composables/useToast'

const emit = defineEmits<{ (e: 'credits-updated'): void }>()
const { t } = useI18n()
const toast = useToast()

const roleOptions: api.WorkspaceRole[] = ['owner', 'admin', 'publisher', 'accounting', 'auditor']

// ---- subscription ----
const plans = ref<api.SubscriptionPlan[]>([])
const subscription = ref<api.SubscriptionSummary | null>(null)
const subLoading = ref(true)
const subBusy = ref(false)
const subError = ref('')

const currentTierName = computed(() => {
  const tier = subscription.value?.tier || 'free'
  const p = plans.value.find((x) => x.code === tier)
  return p?.name || tier
})

function formatDate(s?: string | null) {
  if (!s) return '—'
  try { return new Date(s).toLocaleDateString() } catch { return s }
}

function featureLabel(f: string) {
  return t('enterprise.feature.' + f) || f
}

function roleLabel(r?: api.WorkspaceRole | null) {
  if (!r) return '—'
  return t('enterprise.role.' + r) || r
}

async function loadSubscription() {
  subLoading.value = true
  subError.value = ''
  try {
    const [pRes, sRes] = await Promise.all([api.fetchSubscriptionPlans(), api.fetchMySubscription()])
    plans.value = pRes.data.plans || []
    subscription.value = sRes.data
  } catch (e: any) {
    subError.value = e?.response?.data?.detail || e?.message || String(e)
  } finally {
    subLoading.value = false
  }
}

async function doSubscribe(code: string) {
  subBusy.value = true
  subError.value = ''
  try {
    const res = await api.subscribePlan(code)
    subscription.value = res.data.summary
    toast.success(t('enterprise.subscribed') || '订阅成功')
    emit('credits-updated')
  } catch (e: any) {
    subError.value = e?.response?.data?.detail || e?.message || String(e)
  } finally {
    subBusy.value = false
  }
}

async function doCancel() {
  subBusy.value = true
  subError.value = ''
  try {
    const res = await api.cancelSubscription()
    subscription.value = res.data.summary
    toast.success(t('enterprise.cancelled') || '已取消订阅')
  } catch (e: any) {
    subError.value = e?.response?.data?.detail || e?.message || String(e)
  } finally {
    subBusy.value = false
  }
}

// ---- workspaces ----
type WorkspaceDetail = api.Workspace & { members: api.WorkspaceMember[] }
const workspaces = ref<api.Workspace[]>([])
const activeWorkspaceId = ref<number | null>(null)
const selectedWsId = ref<number | null>(null)
const selectedWs = ref<WorkspaceDetail | null>(null)
const wsLoading = ref(true)
const wsBusy = ref(false)
const wsError = ref('')
const createForm = ref({ name: '', plan: 'free', billing_email: '' })
const inviteToken = ref('')
const rechargeAmount = ref<number>(100)
const wsPlanCode = ref<'team' | 'enterprise'>('team')
const memberInvite = ref({ email: '', role: 'publisher' as api.WorkspaceRole })
const lastInviteToken = ref('')

const canManage = computed(() => {
  const r = selectedWs.value?.my_role
  return r === 'owner' || r === 'admin'
})
const canBill = computed(() => {
  const r = selectedWs.value?.my_role
  return r === 'owner' || r === 'admin' || r === 'accounting'
})

async function loadWorkspaces() {
  wsLoading.value = true
  wsError.value = ''
  try {
    const res = await api.fetchMyWorkspaces()
    workspaces.value = res.data.workspaces || []
    activeWorkspaceId.value = res.data.active_workspace_id ?? null
    if (selectedWsId.value && !workspaces.value.find((w) => w.id === selectedWsId.value)) {
      selectedWsId.value = null
      selectedWs.value = null
    }
  } catch (e: any) {
    wsError.value = e?.response?.data?.detail || e?.message || String(e)
  } finally {
    wsLoading.value = false
  }
}

async function selectWorkspace(id: number) {
  if (selectedWsId.value === id) {
    selectedWsId.value = null
    selectedWs.value = null
    return
  }
  selectedWsId.value = id
  selectedWs.value = null
  try {
    const res = await api.fetchWorkspace(id)
    selectedWs.value = res.data as WorkspaceDetail
  } catch (e: any) {
    wsError.value = e?.response?.data?.detail || e?.message || String(e)
  }
}

async function setActive(id: number) {
  wsBusy.value = true
  try {
    await api.setActiveWorkspace(id)
    activeWorkspaceId.value = id
    toast.success(t('enterprise.activeSet') || '已切换当前工作区')
  } catch (e: any) {
    wsError.value = e?.response?.data?.detail || e?.message || String(e)
  } finally {
    wsBusy.value = false
  }
}

async function doCreateWorkspace() {
  wsBusy.value = true
  wsError.value = ''
  try {
    await api.createWorkspace({
      name: createForm.value.name.trim(),
      plan: createForm.value.plan,
      billing_email: createForm.value.billing_email.trim() || undefined,
    })
    createForm.value = { name: '', plan: 'free', billing_email: '' }
    toast.success(t('enterprise.wsCreated') || '工作区已创建')
    await loadWorkspaces()
  } catch (e: any) {
    wsError.value = e?.response?.data?.detail || e?.message || String(e)
  } finally {
    wsBusy.value = false
  }
}

async function doAcceptInvite() {
  wsBusy.value = true
  wsError.value = ''
  try {
    await api.acceptWorkspaceInvite(inviteToken.value.trim())
    inviteToken.value = ''
    toast.success(t('enterprise.joined') || '已加入工作区')
    await loadWorkspaces()
  } catch (e: any) {
    wsError.value = e?.response?.data?.detail || e?.message || String(e)
  } finally {
    wsBusy.value = false
  }
}

async function doRecharge() {
  if (!selectedWsId.value) return
  const amt = Math.max(1, Number(rechargeAmount.value) || 0)
  wsBusy.value = true
  wsError.value = ''
  try {
    await api.rechargeWorkspace(selectedWsId.value, amt)
    toast.success(t('enterprise.recharged') || '充值成功')
    await Promise.all([loadWorkspaces(), selectWorkspaceRefresh()])
  } catch (e: any) {
    wsError.value = e?.response?.data?.detail || e?.message || String(e)
  } finally {
    wsBusy.value = false
  }
}

async function doSubscribeWs() {
  if (!selectedWsId.value) return
  wsBusy.value = true
  wsError.value = ''
  try {
    await api.subscribeWorkspacePlan(selectedWsId.value, wsPlanCode.value)
    toast.success(t('enterprise.subscribed') || '订阅成功')
    await Promise.all([loadWorkspaces(), selectWorkspaceRefresh()])
  } catch (e: any) {
    wsError.value = e?.response?.data?.detail || e?.message || String(e)
  } finally {
    wsBusy.value = false
  }
}

async function doInvite() {
  if (!selectedWsId.value) return
  wsBusy.value = true
  wsError.value = ''
  lastInviteToken.value = ''
  try {
    const res = await api.inviteWorkspaceMember(selectedWsId.value, memberInvite.value.email.trim(), memberInvite.value.role)
    lastInviteToken.value = res.data.token
    memberInvite.value.email = ''
    toast.success(t('enterprise.inviteSent') || '邀请已发送')
  } catch (e: any) {
    wsError.value = e?.response?.data?.detail || e?.message || String(e)
  } finally {
    wsBusy.value = false
  }
}

async function onRoleChange(userId: number, role: string) {
  if (!selectedWsId.value) return
  wsBusy.value = true
  try {
    await api.updateWorkspaceMemberRole(selectedWsId.value, userId, role as api.WorkspaceRole)
    await selectWorkspaceRefresh()
  } catch (e: any) {
    wsError.value = e?.response?.data?.detail || e?.message || String(e)
  } finally {
    wsBusy.value = false
  }
}

async function doRemoveMember(userId: number) {
  if (!selectedWsId.value) return
  wsBusy.value = true
  try {
    await api.removeWorkspaceMember(selectedWsId.value, userId)
    await selectWorkspaceRefresh()
  } catch (e: any) {
    wsError.value = e?.response?.data?.detail || e?.message || String(e)
  } finally {
    wsBusy.value = false
  }
}

async function selectWorkspaceRefresh() {
  if (!selectedWsId.value) return
  try {
    const res = await api.fetchWorkspace(selectedWsId.value)
    selectedWs.value = res.data as WorkspaceDetail
  } catch { /* ignore */ }
}

onMounted(() => {
  loadSubscription()
  loadWorkspaces()
})
</script>

<style scoped>
.enterprise-panel { display: flex; flex-direction: column; gap: var(--space-5); }
.ent-section { margin-bottom: 0; }
.ent-head h3 { margin: 0 0 var(--space-1); }
.ent-head .hint { margin: 0 0 var(--space-3); }
.ent-skel { color: var(--text-secondary); padding: var(--space-4) 0; }
.ent-current { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-4); }
.ent-current__label { color: var(--text-secondary); font-size: var(--font-caption); }
.ent-plan-grid { display: grid; grid-template-columns: 1fr; gap: var(--space-3); }
@media (min-width: 640px) { .ent-plan-grid { grid-template-columns: repeat(2, 1fr); } }
@media (min-width: 980px) { .ent-plan-grid { grid-template-columns: repeat(4, 1fr); } }
.ent-plan-card { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-4); border: var(--border-hairline); border-radius: var(--radius-lg); background: rgba(255,255,255,0.02); }
.ent-plan-card--current { border-color: rgba(var(--primary-rgb), 0.5); background: rgba(var(--primary-rgb), 0.06); }
.ent-plan-card__top { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
.ent-plan-card__name { margin: 0; font-size: var(--font-body); font-weight: 700; }
.ent-plan-card__price { margin: 0; }
.ent-plan-card__price strong { font-size: 1.5rem; color: var(--primary-color); }
.ent-plan-card__unit { font-size: var(--font-caption); color: var(--text-secondary); margin-left: 4px; }
.ent-plan-card__meta { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; font-size: var(--font-caption); color: var(--text-secondary); }
.ent-plan-card__features { margin: var(--space-1) 0 0; padding-left: 1.1rem; font-size: 0.75rem; color: var(--text-tertiary, var(--text-secondary)); display: grid; gap: 2px; }
.ent-plan-card__cta { margin-top: auto; }
.ent-ws-list { list-style: none; margin: 0 0 var(--space-3); padding: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.ent-ws-row { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); border: var(--border-hairline); border-radius: var(--radius-md); background: rgba(255,255,255,0.02); }
.ent-ws-row.selected { border-color: rgba(var(--primary-rgb), 0.5); }
.ent-ws-row__main { flex: 1; min-width: 0; display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; appearance: none; background: none; border: none; cursor: pointer; text-align: left; font: inherit; color: var(--text-primary); }
.ent-ws-name { font-weight: 600; }
.ent-ws-meta { font-size: var(--font-caption); color: var(--text-secondary); }
.ent-create { margin-bottom: var(--space-3); }
.ent-create summary { cursor: pointer; font-weight: 600; font-size: var(--font-caption); color: var(--text-secondary); }
.ent-form-grid { display: grid; grid-template-columns: 1fr; gap: var(--space-2); margin: var(--space-2) 0; }
@media (min-width: 640px) { .ent-form-grid { grid-template-columns: 1fr 1fr; } }
.ent-form-inline { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); margin: var(--space-2) 0; }
.input-num { max-width: 8rem; }
.input-sm { padding: 0.2rem 0.4rem; font-size: var(--font-caption); }
.ent-ws-detail { margin-top: var(--space-3); padding: var(--space-4); border: var(--border-hairline); border-radius: var(--radius-md); background: rgba(0,0,0,0.12); }
.ent-ws-detail__title { margin: 0 0 var(--space-3); }
.ent-ws-actions { display: flex; flex-wrap: wrap; gap: var(--space-4); margin-bottom: var(--space-3); }
.ent-members-title { margin: var(--space-2) 0; font-size: var(--font-caption); color: var(--text-secondary); }
.ent-members { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.ent-member-row { display: flex; align-items: center; gap: var(--space-2); }
.ent-member-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ent-invite-token { word-break: break-all; }
.ent-rfq-link { margin-top: var(--space-3); }
</style>
