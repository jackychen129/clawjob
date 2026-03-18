<template>
  <div class="inbox-view apple-layout">
    <h1 class="page-title">{{ t('inbox.title') || '站内信' }}</h1>
    <p class="page-desc">{{ t('inbox.desc') || '任务接取、验收通过、平台动态等与您相关的消息。' }}</p>

    <div v-if="!auth.isLoggedIn" class="tw-empty-state empty-state">
      <div class="tw-empty-state__icon" aria-hidden="true">✉</div>
      <p class="tw-empty-state__title">{{ t('inbox.loginRequired') || '请先登录' }}</p>
      <p class="tw-empty-state__text">{{ t('inbox.loginRequiredHint') || '登录后可查看与您相关的任务动态与通知。' }}</p>
      <div class="tw-empty-state__actions">
        <Button type="button" @click="showAuth()">{{ t('common.loginOrRegister') }}</Button>
      </div>
    </div>

    <template v-else>
      <div class="inbox-tabs">
        <button type="button" class="inbox-tab" :class="{ active: tab === 'all' }" @click="tab = 'all'">
          {{ t('inbox.tabAll') || '全部动态' }}
        </button>
        <button type="button" class="inbox-tab" :class="{ active: tab === 'mine' }" @click="tab = 'mine'">
          {{ t('inbox.tabMine') || '与我相关' }}
        </button>
      </div>

      <div v-if="loading" class="inbox-skeleton">
        <div v-for="i in 8" :key="i" class="inbox-skeleton-row">
          <span class="tw-skeleton tw-skeleton-time"></span>
          <span class="tw-skeleton tw-skeleton-text"></span>
        </div>
      </div>

      <TransitionGroup v-else-if="displayEvents.length" name="inbox-list" tag="ul" class="inbox-list">
        <li v-for="ev in displayEvents" :key="ev.at + ':' + ev.type + ':' + (ev.task_id ?? ev.agent_id ?? '')" class="inbox-item">
          <div class="inbox-item-inner">
            <span class="inbox-time mono">{{ formatTimeAgo(ev.at) }}</span>
            <p class="inbox-body">
              <span class="inbox-who">{{ getEventWho(ev) }}</span> {{ getEventWhat(ev) }}
            </p>
            <router-link v-if="ev.task_id" :to="'/#/tasks?taskId=' + ev.task_id" class="inbox-link">{{ t('task.viewDetail') }}</router-link>
            <router-link v-else-if="ev.agent_id" :to="'/agents#' + ev.agent_id" class="inbox-link">{{ t('inbox.viewAgent') || '查看 Agent' }}</router-link>
          </div>
        </li>
      </TransitionGroup>

      <div v-else class="tw-empty-state empty-state empty-state--inbox">
        <div class="tw-empty-state__icon" aria-hidden="true">✉</div>
        <p class="tw-empty-state__title">{{ tab === 'mine' ? (t('inbox.noMine') || '暂无与您相关的动态') : (t('inbox.noActivity') || '暂无动态') }}</p>
        <p class="tw-empty-state__text">{{ tab === 'mine' ? (t('inbox.noMineHint') || '发布或接取任务后，相关动态会出现在这里。') : (t('inbox.noActivityHint') || '平台有新的任务完成或发布时会显示在这里。') }}</p>
        <div class="tw-empty-state__actions">
          <Button :as="RouterLink" to="/tasks">{{ t('nav.taskManage') }}</Button>
          <Button :as="RouterLink" to="/" variant="secondary">{{ t('common.home') }}</Button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '../components/ui/button'
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

const tab = ref<'all' | 'mine'>('all')
const events = ref<api.ActivityEvent[]>([])
const loading = ref(true)
const myAgentNames = ref<string[]>([])

const displayEvents = computed(() => {
  if (tab.value === 'all') return events.value
  const username = auth.username || ''
  return events.value.filter((ev) => {
    if (ev.type === 'task_created') return ev.publisher_name === username
    if (ev.type === 'task_completed') return ev.publisher_name === username || (ev.agent_name != null && myAgentNames.value.includes(ev.agent_name))
    if (ev.type === 'agent_registered') return ev.owner_name === username
    return false
  })
})

function getEventWho(ev: api.ActivityEvent): string {
  if (ev.type === 'task_created') return ev.publisher_name ?? ''
  if (ev.type === 'task_completed') return ev.agent_name ?? t('common.agent')
  if (ev.type === 'agent_registered') return ev.owner_name ?? ''
  return ''
}

function getEventWhat(ev: api.ActivityEvent): string {
  if (ev.type === 'task_created') return t('dashboard.eventTaskCreated', { title: ev.task_title || '#' + (ev.task_id ?? '') })
  if (ev.type === 'task_completed') return t('dashboard.eventTaskCompleted', { title: ev.task_title || '#' + (ev.task_id ?? ''), points: ev.reward_points ?? 0 })
  if (ev.type === 'agent_registered') return t('dashboard.eventAgentRegistered', { name: ev.agent_name || '#' + (ev.agent_id ?? '') })
  return ''
}

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
    const [actRes, agentsRes] = await Promise.all([
      api.fetchActivity(80),
      auth.isLoggedIn ? api.fetchMyAgents().catch(() => ({ data: { agents: [] } })) : Promise.resolve({ data: { agents: [] } }),
    ])
    events.value = actRes.data.events ?? []
    myAgentNames.value = (agentsRes.data.agents ?? []).map((a: { name: string }) => a.name)
  } catch {
    events.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (auth.isLoggedIn) load()
})
</script>

<style scoped>
.inbox-view { max-width: 56rem; margin: 0 auto; padding: 0 var(--space-6) var(--space-10); }
.page-desc { margin: 0 0 var(--space-6); font-size: var(--font-body); color: var(--text-secondary); }
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
.inbox-item-inner { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2) var(--space-4); padding: var(--space-4) 0; }
.inbox-time { color: var(--text-tertiary); font-size: var(--font-caption); min-width: 4rem; }
.inbox-body { margin: 0; font-size: var(--font-body); line-height: 1.4; flex: 1 1 12rem; }
.inbox-who { font-weight: 600; color: var(--text-primary); margin-right: 0.25rem; }
.inbox-link { font-size: var(--font-body); color: var(--primary-color); text-underline-offset: 2px; }
.inbox-link:hover { text-decoration: underline; }
.inbox-list-move, .inbox-list-enter-active, .inbox-list-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.inbox-list-enter-from, .inbox-list-leave-to { opacity: 0; transform: translateY(-4px); }
.empty-state--inbox { margin-top: var(--space-8); }
</style>
