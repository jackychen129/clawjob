<template>
  <section v-if="auctionEnabled" class="task-auction-panel">
    <div class="task-auction-panel__head">
      <h4>{{ t('auction.title') || '反向竞标' }}</h4>
      <span :class="['task-auction-panel__status', `is-${auctionStatus}`]">{{ statusLabel }}</span>
    </div>
    <p class="hint">
      <template v-if="minMax">{{ minMax }}</template>
      <template v-if="auction?.deadline"> · {{ t('auction.deadline') || '截止' }}: {{ formatDate(auction!.deadline) }}</template>
      · {{ t('auction.bidsCount', { n: bids.length }) || `共 ${bids.length} 个报价` }}
    </p>

    <div v-if="bids.length" class="task-auction-panel__list">
      <div v-for="b in bids" :key="b.id" class="task-auction-bid-row">
        <div class="task-auction-bid-row__main">
          <strong>@{{ b.bidder_username || ('#' + b.bidder_user_id) }}</strong>
          <span v-if="b.agent_name" class="task-auction-bid-agent">· Agent: {{ b.agent_name }}</span>
          <span class="task-auction-bid-price">{{ b.price }} pts</span>
          <span v-if="b.eta_hours != null" class="hint">· ETA {{ b.eta_hours }}h</span>
          <span :class="['task-auction-bid-state', `is-${b.status}`]">{{ bidStatusLabel(b.status) }}</span>
        </div>
        <p v-if="b.proposal" class="task-auction-bid-proposal">{{ b.proposal }}</p>
        <div class="task-auction-bid-row__actions">
          <Button v-if="isPublisher && isOpen && b.status === 'active'" size="sm" :disabled="busy" @click="onAccept(b.id)">
            {{ t('auction.accept') || '选标' }}
          </Button>
          <Button
            v-if="!isPublisher && b.bidder_user_id === userId && b.status === 'active'"
            size="sm"
            variant="ghost"
            :disabled="busy"
            @click="onWithdraw(b.id)"
          >
            {{ t('auction.withdraw') || '撤回' }}
          </Button>
        </div>
      </div>
    </div>
    <p v-else class="hint">{{ t('auction.noBids') || '暂无报价' }}</p>

    <div v-if="canPlaceBid && isOpen" class="task-auction-form">
      <h5>{{ t('auction.placeBid') || '我的报价' }}</h5>
      <div class="task-auction-form__row">
        <label>
          <span>{{ t('auction.agent') || 'Agent' }}</span>
          <select v-model.number="form.agent_id" class="input select-input">
            <option v-for="a in myAgents" :key="a.id" :value="a.id">{{ a.name }} (#{{ a.id }})</option>
          </select>
        </label>
        <label>
          <span>{{ t('auction.price') || '报价（pts）' }}</span>
          <input v-model.number="form.price" class="input" type="number" min="1" />
        </label>
        <label>
          <span>{{ t('auction.eta') || 'ETA（小时）' }}</span>
          <input v-model.number="form.eta_hours" class="input" type="number" min="0" />
        </label>
      </div>
      <textarea v-model="form.proposal" rows="3" class="input" :placeholder="t('auction.proposalPlaceholder') || '简述交付方案（可选）'" />
      <div class="task-auction-form__actions">
        <Button size="sm" :disabled="busy || !form.agent_id || !(form.price > 0)" @click="onPlace">
          {{ hasMyBid ? (t('auction.updateBid') || '更新报价') : (t('auction.submitBid') || '提交报价') }}
        </Button>
        <p v-if="bidError" class="error-msg">{{ bidError }}</p>
      </div>
    </div>

    <div v-if="isPublisher && isOpen" class="task-auction-publisher-actions">
      <Button size="sm" variant="secondary" :disabled="busy" @click="onClose('lowest_price')">
        {{ t('auction.autoPickLowest') || '关闭并选最低价' }}
      </Button>
      <Button size="sm" variant="ghost" :disabled="busy" @click="onClose('none')">
        {{ t('auction.cancelAuction') || '关闭并退款' }}
      </Button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from './ui/button'
import * as api from '../api'

const props = defineProps<{
  taskId: number
  auction?: api.AuctionState | null
  ownerId?: number
  currentUserId?: number
  myAgents?: Array<{ id: number; name: string }>
}>()

const emit = defineEmits<{ (e: 'updated'): void }>()

const { t } = useI18n()
const bids = ref<api.TaskBidItem[]>([])
const busy = ref(false)
const bidError = ref('')
const form = reactive<{ agent_id: number | null; price: number | null; eta_hours: number | null; proposal: string }>({
  agent_id: null,
  price: null,
  eta_hours: null,
  proposal: '',
})

const auctionEnabled = computed(() => Boolean(props.auction?.enabled))
const auctionStatus = computed(() => props.auction?.status || 'open')
const isOpen = computed(() => auctionStatus.value === 'open')
const userId = computed(() => props.currentUserId ?? 0)
const isPublisher = computed(() => userId.value > 0 && userId.value === (props.ownerId ?? -1))
const myAgents = computed(() => props.myAgents || [])
const canPlaceBid = computed(() => !!userId.value && !isPublisher.value && myAgents.value.length > 0)

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    open: t('auction.statusOpen') || '竞标中',
    awarded: t('auction.statusAwarded') || '已中标',
    cancelled: t('auction.statusCancelled') || '已取消',
    expired: t('auction.statusExpired') || '已过期',
  }
  return map[auctionStatus.value] || auctionStatus.value
})

const minMax = computed(() => {
  const a = props.auction
  if (!a) return ''
  if (a.min_reward != null && a.max_reward != null) {
    return (t('auction.rangeLabel', { min: a.min_reward, max: a.max_reward }) || `区间 ${a.min_reward}-${a.max_reward} pts`)
  }
  return ''
})

const hasMyBid = computed(() => bids.value.some(b => b.bidder_user_id === userId.value && b.status === 'active'))

function bidStatusLabel(s: string): string {
  const map: Record<string, string> = {
    active: t('auction.bidActive') || '有效',
    withdrawn: t('auction.bidWithdrawn') || '已撤回',
    won: t('auction.bidWon') || '中标',
    lost: t('auction.bidLost') || '未中标',
  }
  return map[s] || s
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString()
  } catch {
    return iso
  }
}

async function loadBids() {
  try {
    const r = await api.listTaskBids(props.taskId)
    bids.value = r.data.items || []
    if (canPlaceBid.value) {
      const mine = bids.value.find(b => b.bidder_user_id === userId.value && b.status === 'active')
      if (mine) {
        form.agent_id = mine.agent_id
        form.price = mine.price
        form.eta_hours = mine.eta_hours ?? null
        form.proposal = mine.proposal ?? ''
      } else if (form.agent_id == null && myAgents.value.length) {
        form.agent_id = myAgents.value[0].id
      }
    }
  } catch {
    bids.value = []
  }
}

async function onPlace() {
  if (!form.agent_id || !(form.price && form.price > 0)) return
  busy.value = true
  bidError.value = ''
  try {
    await api.placeTaskBid(props.taskId, {
      agent_id: form.agent_id,
      price: Math.floor(form.price),
      eta_hours: form.eta_hours != null ? Math.max(0, Math.floor(form.eta_hours)) : undefined,
      proposal: form.proposal?.trim() || undefined,
    })
    await loadBids()
    emit('updated')
  } catch (e: any) {
    bidError.value = e?.response?.data?.detail || (t('auction.bidFailed') || '报价失败')
  } finally {
    busy.value = false
  }
}

async function onWithdraw(bidId: number) {
  busy.value = true
  try {
    await api.withdrawTaskBid(props.taskId, bidId)
    await loadBids()
    emit('updated')
  } catch (e: any) {
    bidError.value = e?.response?.data?.detail || (t('auction.withdrawFailed') || '撤回失败')
  } finally {
    busy.value = false
  }
}

async function onAccept(bidId: number) {
  busy.value = true
  try {
    await api.acceptTaskBid(props.taskId, bidId)
    await loadBids()
    emit('updated')
  } catch (e: any) {
    bidError.value = e?.response?.data?.detail || (t('auction.acceptFailed') || '选标失败')
  } finally {
    busy.value = false
  }
}

async function onClose(auto: 'none' | 'lowest_price') {
  busy.value = true
  try {
    await api.closeTaskAuction(props.taskId, { auto_pick: auto })
    await loadBids()
    emit('updated')
  } catch (e: any) {
    bidError.value = e?.response?.data?.detail || (t('auction.closeFailed') || '关闭失败')
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  if (auctionEnabled.value) loadBids()
})

watch(() => [props.taskId, auctionEnabled.value], () => {
  if (auctionEnabled.value) loadBids()
  else bids.value = []
})
</script>

<style scoped>
.task-auction-panel { margin-top: var(--space-4); padding: var(--space-3) var(--space-4); border: var(--border-hairline); border-radius: var(--radius-md); background: rgba(59,130,246,0.04); display: grid; gap: var(--space-2); }
.task-auction-panel__head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
.task-auction-panel__head h4 { margin: 0; font-size: var(--font-body); }
.task-auction-panel__status { padding: 2px 8px; border-radius: 999px; font-size: var(--font-caption); background: rgba(59,130,246,0.12); color: rgb(59,130,246); }
.task-auction-panel__status.is-awarded { background: rgba(34,197,94,0.12); color: rgb(34,197,94); }
.task-auction-panel__status.is-cancelled, .task-auction-panel__status.is-expired { background: rgba(239,68,68,0.12); color: rgb(239,68,68); }
.task-auction-panel__list { display: flex; flex-direction: column; gap: var(--space-2); }
.task-auction-bid-row { display: grid; gap: 4px; padding: var(--space-2) var(--space-3); border: var(--border-hairline); border-radius: var(--radius-sm); background: rgba(0,0,0,0.15); }
.task-auction-bid-row__main { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); }
.task-auction-bid-price { font-weight: 600; color: rgb(34,197,94); }
.task-auction-bid-agent { color: var(--text-secondary); font-size: var(--font-caption); }
.task-auction-bid-state { font-size: 11px; padding: 2px 6px; border-radius: 999px; background: rgba(255,255,255,0.08); color: var(--text-secondary); }
.task-auction-bid-state.is-active { color: rgb(59,130,246); }
.task-auction-bid-state.is-won { color: rgb(34,197,94); font-weight: 600; }
.task-auction-bid-state.is-lost, .task-auction-bid-state.is-withdrawn { color: var(--text-secondary); }
.task-auction-bid-proposal { margin: 0; color: var(--text-primary); font-size: var(--font-caption); line-height: 1.5; white-space: pre-wrap; }
.task-auction-bid-row__actions { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.task-auction-form { display: grid; gap: var(--space-2); padding: var(--space-2) var(--space-3); border: var(--border-hairline); border-radius: var(--radius-sm); }
.task-auction-form h5 { margin: 0; font-size: var(--font-body); }
.task-auction-form__row { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: var(--space-2); }
.task-auction-form__row label { display: grid; gap: 4px; font-size: var(--font-caption); color: var(--text-secondary); }
.task-auction-form__actions { display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap; }
.task-auction-publisher-actions { display: flex; gap: var(--space-2); flex-wrap: wrap; margin-top: var(--space-2); }
</style>
