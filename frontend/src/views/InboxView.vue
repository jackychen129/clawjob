<template>
  <div class="inbox-view apple-layout">
    <h1 class="page-title">{{ t('inbox.title') || '站内信' }}</h1>
    <p class="page-desc">{{ t('inbox.desc') || '给其他用户发送消息，查看收件箱与已发送。' }}</p>

    <div v-if="!auth.isLoggedIn" class="tw-empty-state empty-state">
      <div class="tw-empty-state__icon" aria-hidden="true">✉</div>
      <p class="tw-empty-state__title">{{ t('inbox.loginRequired') || '请先登录' }}</p>
      <p class="tw-empty-state__text">{{ t('inbox.loginRequiredHint') || '登录后可查看与您相关的任务动态与通知。' }}</p>
      <div class="tw-empty-state__actions">
        <Button type="button" @click="showAuth()">{{ t('common.loginOrRegister') }}</Button>
      </div>
    </div>

    <template v-else>
      <div class="compose-card">
        <h3 class="compose-title">{{ t('inbox.compose') || '发送站内信' }}</h3>
        <div class="compose-grid">
          <Input v-model="composeForm.recipient_username" :placeholder="t('inbox.recipientUsername') || '收件人用户名'" />
          <Input v-model="composeForm.title" :placeholder="t('inbox.messageTitle') || '标题'" />
        </div>
        <Textarea v-model="composeForm.content" rows="3" :placeholder="t('inbox.messageContent') || '消息内容'" />
        <div class="compose-actions">
          <Button :disabled="sending || !composeForm.recipient_username.trim() || !composeForm.title.trim() || !composeForm.content.trim()" @click="sendMessage">
            {{ sending ? (t('common.loading') || '发送中...') : (t('inbox.send') || '发送') }}
          </Button>
        </div>
      </div>

      <div class="inbox-tabs">
        <button type="button" class="inbox-tab" :class="{ active: tab === 'inbox' }" @click="tab = 'inbox'">
          {{ t('inbox.inbox') || '收件箱' }}
        </button>
        <button type="button" class="inbox-tab" :class="{ active: tab === 'sent' }" @click="tab = 'sent'">
          {{ t('inbox.sent') || '已发送' }}
        </button>
        <label v-if="tab === 'inbox'" class="unread-only">
          <input v-model="unreadOnly" type="checkbox" />
          {{ t('inbox.unreadOnly') || '仅看未读' }}
        </label>
      </div>

      <div v-if="loading" class="inbox-skeleton">
        <div v-for="i in 8" :key="i" class="inbox-skeleton-row">
          <span class="tw-skeleton tw-skeleton-time"></span>
          <span class="tw-skeleton tw-skeleton-text"></span>
        </div>
      </div>

      <TransitionGroup v-else-if="displayMessages.length" name="inbox-list" tag="ul" class="inbox-list">
        <li v-for="msg in displayMessages" :key="msg.id" class="inbox-item" :class="{ unread: tab === 'inbox' && !msg.is_read }">
          <div class="inbox-item-inner">
            <div class="inbox-item-main">
              <p class="inbox-title-row">
                <strong>{{ msg.title }}</strong>
                <span class="inbox-time mono">{{ formatTimeAgo(msg.created_at || '') }}</span>
              </p>
              <p class="inbox-meta" v-if="tab === 'inbox'">
                {{ t('inbox.from') || '来自' }}：{{ msg.sender_username || ('#' + (msg.sender_user_id ?? '')) }}
              </p>
              <p class="inbox-meta" v-else>
                {{ t('inbox.to') || '发送给' }}：{{ msg.recipient_username || ('#' + (msg.recipient_user_id ?? '')) }}
              </p>
              <p class="inbox-body">{{ msg.content }}</p>
              <router-link v-if="msg.related_task_id" :to="'/tasks?taskId=' + msg.related_task_id" class="inbox-link">{{ t('task.viewDetail') }}</router-link>
            </div>
            <Button
              v-if="tab === 'inbox' && !msg.is_read"
              size="sm"
              variant="secondary"
              :disabled="markingReadId === msg.id"
              @click="markRead(msg.id)"
            >
              {{ t('inbox.markRead') || '标记已读' }}
            </Button>
          </div>
        </li>
      </TransitionGroup>

      <div v-else class="tw-empty-state empty-state empty-state--inbox">
        <div class="tw-empty-state__icon" aria-hidden="true">✉</div>
        <p class="tw-empty-state__title">{{ tab === 'inbox' ? (t('inbox.emptyInbox') || '收件箱暂无消息') : (t('inbox.emptySent') || '暂无已发送消息') }}</p>
        <p class="tw-empty-state__text">{{ tab === 'inbox' ? (t('inbox.emptyInboxHint') || '让其他用户给你发送一条站内信试试。') : (t('inbox.emptySentHint') || '发送后可在这里查看历史。') }}</p>
        <div class="tw-empty-state__actions">
          <Button :as="RouterLink" to="/tasks">{{ t('nav.taskManage') }}</Button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'
import { safeT } from '../i18n'

const emit = defineEmits<{ (e: 'show-auth'): void }>()
function showAuth() {
  emit('show-auth')
}

const _i18n = useI18n()
const t = typeof _i18n.t === 'function' ? _i18n.t : safeT
const auth = useAuthStore()

const tab = ref<'inbox' | 'sent'>('inbox')
const unreadOnly = ref(false)
const inboxItems = ref<api.InternalMessageItem[]>([])
const sentItems = ref<api.InternalMessageItem[]>([])
const loading = ref(true)
const sending = ref(false)
const markingReadId = ref<number | null>(null)
const composeForm = ref({ recipient_username: '', title: '', content: '' })

const displayMessages = computed(() => {
  if (tab.value === 'inbox') return inboxItems.value
  return sentItems.value
})

function formatTimeAgo(iso: string) {
  try {
    const d = new Date(iso)
    const now = Date.now()
    const diff = Math.floor((now - d.getTime()) / 1000)
    if (diff < 60) return (diff <= 0 ? '1' : String(diff)) + (t('inbox.secondsAgo') || '秒前')
    if (diff < 3600) return Math.floor(diff / 60) + (t('inbox.minutesAgo') || '分钟前')
    if (diff < 86400) return Math.floor(diff / 3600) + (t('inbox.hoursAgo') || '小时前')
    return Math.floor(diff / 86400) + (t('inbox.daysAgo') || '天前')
  } catch {
    return ''
  }
}

async function load() {
  loading.value = true
  try {
    const [inboxRes, sentRes] = await Promise.all([
      api.fetchInboxMessages({ limit: 100, unread_only: unreadOnly.value }),
      api.fetchSentMessages({ limit: 100 }),
    ])
    inboxItems.value = inboxRes.data.items ?? []
    sentItems.value = sentRes.data.items ?? []
  } catch {
    inboxItems.value = []
    sentItems.value = []
  } finally {
    loading.value = false
  }
}

async function markRead(messageId: number) {
  markingReadId.value = messageId
  try {
    await api.markMessageRead(messageId)
    await load()
  } finally {
    markingReadId.value = null
  }
}

async function sendMessage() {
  if (!composeForm.value.recipient_username.trim() || !composeForm.value.title.trim() || !composeForm.value.content.trim()) return
  sending.value = true
  try {
    await api.sendInternalMessage({
      recipient_username: composeForm.value.recipient_username.trim(),
      title: composeForm.value.title.trim(),
      content: composeForm.value.content.trim(),
    })
    composeForm.value = { recipient_username: '', title: '', content: '' }
    tab.value = 'sent'
    await load()
  } finally {
    sending.value = false
  }
}

onMounted(() => {
  if (auth.isLoggedIn) load()
})
watch(unreadOnly, () => {
  if (auth.isLoggedIn && tab.value === 'inbox') load()
})
</script>

<style scoped>
.inbox-view { max-width: 56rem; margin: 0 auto; padding: 0 var(--space-6) var(--space-10); }
.page-desc { margin: 0 0 var(--space-6); font-size: var(--font-body); color: var(--text-secondary); }
.compose-card { border: var(--border-hairline); border-radius: var(--radius-lg); background: var(--card-background); padding: var(--space-4); margin-bottom: var(--space-5); }
.compose-title { margin: 0 0 var(--space-3); font-size: var(--font-body-strong); }
.compose-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-2); margin-bottom: var(--space-2); }
.compose-actions { margin-top: var(--space-2); display: flex; justify-content: flex-end; }
.inbox-tabs { display: flex; gap: var(--space-2); margin-bottom: var(--space-5); }
.inbox-tab {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  border: var(--border-hairline);
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--font-body);
  cursor: pointer;
  transition: border-color var(--duration-m) var(--ease-apple), background var(--duration-m) var(--ease-apple), color var(--duration-m) var(--ease-apple);
}
.inbox-tab:hover { border-color: rgba(255,255,255,0.12); color: var(--text-primary); }
.inbox-tab.active { background: rgba(var(--primary-rgb), 0.12); border-color: var(--primary-color); color: var(--text-primary); }
.inbox-skeleton { display: flex; flex-direction: column; gap: var(--space-3); }
.inbox-skeleton-row { display: flex; align-items: center; gap: var(--space-3); }
.tw-skeleton-time { width: 4rem; height: 1rem; border-radius: var(--radius-sm); }
.tw-skeleton-text { flex: 1; height: 1.25rem; border-radius: var(--radius-sm); }
.inbox-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0; }
.inbox-item { border-bottom: var(--border-hairline); }
.inbox-item-inner { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); padding: var(--space-4) 0; }
.inbox-item.unread { background: rgba(var(--primary-rgb), 0.05); }
.inbox-item-main { flex: 1 1 auto; min-width: 0; }
.inbox-title-row { margin: 0 0 0.2rem; display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
.inbox-time { color: var(--text-tertiary); font-size: var(--font-caption); }
.inbox-meta { margin: 0 0 0.35rem; color: var(--text-secondary); font-size: var(--font-caption); }
.inbox-body { margin: 0 0 0.35rem; font-size: var(--font-body); line-height: 1.5; white-space: pre-wrap; }
.inbox-link { font-size: var(--font-body); color: var(--primary-color); text-underline-offset: 2px; }
.inbox-link:hover { text-decoration: underline; }
.unread-only { display: inline-flex; align-items: center; gap: 0.35rem; margin-left: auto; font-size: var(--font-caption); color: var(--text-secondary); }
.inbox-list-move, .inbox-list-enter-active, .inbox-list-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.inbox-list-enter-from, .inbox-list-leave-to { opacity: 0; transform: translateY(-4px); }
.empty-state--inbox { margin-top: var(--space-8); }
@media (max-width: 768px) {
  .compose-grid { grid-template-columns: 1fr; }
}
</style>
