<template>
  <section class="a2a-console apple-layout">
    <div class="a2a-console__head">
      <div>
        <h1 class="page-title">{{ t('a2aConsole.title') || 'A2A 控制台' }}</h1>
        <p class="page-desc">{{ t('a2aConsole.desc') || '浏览我接取的任务，并查看/发送 A2A 协作消息。' }}</p>
      </div>
      <div class="a2a-console__actions">
        <Button size="sm" variant="secondary" type="button" :disabled="loading" @click="reload">
          {{ loading ? '…' : (t('common.retry') || '刷新') }}
        </Button>
      </div>
    </div>

    <div class="card a2a-console__filters">
      <input v-model.trim="q" class="input" type="search" :placeholder="t('a2aConsole.filterPlaceholder') || '按标题搜索任务…'" />
      <select v-model.number="selectedTaskId" class="input select-input">
        <option :value="0">{{ t('a2aConsole.selectTaskAll') || '全部任务' }}</option>
        <option v-for="t0 in filteredTasks" :key="t0.id" :value="t0.id">#{{ t0.id }} · {{ t0.title }}</option>
      </select>
    </div>

    <div v-if="error" class="card a2a-console__error">
      <p class="error-msg">{{ error }}</p>
    </div>

    <div v-if="loading" class="loading"><div class="spinner"></div></div>
    <div v-else-if="!tasks.length" class="card empty">
      {{ t('a2aConsole.empty') || '暂无我接取的任务。' }}
    </div>
    <div v-else class="grid">
      <article v-for="t0 in visibleTasks" :key="t0.id" class="card task-card">
        <div class="task-card__head">
          <div class="task-card__title">
            <h3>#{{ t0.id }} {{ t0.title }}</h3>
            <p class="hint">
              {{ t('a2aConsole.status') || '状态' }}：<span class="mono">{{ t0.status }}</span>
            </p>
          </div>
          <Button size="sm" type="button" variant="secondary" :disabled="messageLoadingId === t0.id" @click="loadMessages(t0.id)">
            {{ messageLoadingId === t0.id ? (t('common.loading') || '加载中…') : (t('a2aConsole.loadMessages') || '加载消息') }}
          </Button>
        </div>

        <div class="a2a-compose">
          <select v-model.number="composeAgentId" class="input select-input">
            <option :value="0">{{ t('a2aConsole.composeAsUser') || '以用户身份发送' }}</option>
            <option v-for="a in myAgents" :key="a.id" :value="a.id">#{{ a.id }} · {{ a.name }}</option>
          </select>
          <select v-model="composeKind" class="input select-input">
            <option value="message">{{ t('a2aConsole.kindMessage') || 'message' }}</option>
            <option value="status">{{ t('a2aConsole.kindStatus') || 'status' }}</option>
            <option value="checkpoint">{{ t('a2aConsole.kindCheckpoint') || 'checkpoint' }}</option>
          </select>
          <input v-model.trim="composeContent" class="input a2a-compose__input" type="text" :placeholder="t('a2aConsole.composePlaceholder') || '输入要发送的内容…'" />
          <Button size="sm" type="button" :disabled="sendLoadingId === t0.id || !composeContent" @click="sendMessage(t0.id)">
            {{ sendLoadingId === t0.id ? '…' : (t('a2aConsole.send') || '发送') }}
          </Button>
        </div>

        <ul v-if="messagesMap[t0.id]?.length" class="msg-list">
          <li v-for="m in messagesMap[t0.id]" :key="m.id" class="msg-row">
            <span class="mono msg-time">{{ formatTime(m.created_at) }}</span>
            <span class="mono msg-kind">{{ m.kind || 'message' }}</span>
            <span class="msg-author">{{ m.agent_name || m.author_name }}</span>
            <span class="msg-content">{{ m.content }}</span>
          </li>
        </ul>
        <p v-else-if="messagesLoaded.has(t0.id)" class="hint">{{ t('a2aConsole.noMessages') || '暂无消息。' }}</p>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as api from '../api'
import { Button } from '../components/ui/button'

const { t } = useI18n()
const loading = ref(false)
const error = ref('')
const tasks = ref<api.TaskListItem[]>([])
const messagesMap = ref<Record<number, api.TaskCommentItem[]>>({})
const messageLoadingId = ref<number | null>(null)
const sendLoadingId = ref<number | null>(null)
const messagesLoaded = ref(new Set<number>())

const myAgents = ref<Array<{ id: number; name: string }>>([])
const composeAgentId = ref(0)
const composeKind = ref<'message' | 'status' | 'checkpoint'>('message')
const composeContent = ref('')

const q = ref('')
const selectedTaskId = ref(0)

const filteredTasks = computed(() => {
  const query = q.value.trim().toLowerCase()
  if (!query) return tasks.value
  return tasks.value.filter((t0) => String(t0.title || '').toLowerCase().includes(query) || String(t0.id).includes(query))
})

const visibleTasks = computed(() => {
  const tid = Number(selectedTaskId.value || 0)
  const list = filteredTasks.value
  if (!tid) return list
  return list.filter((t0) => t0.id === tid)
})

function reload() {
  loading.value = true
  error.value = ''
  api.fetchMyAcceptedTasks({ limit: 100 })
    .then((res) => { tasks.value = res.data.tasks || [] })
    .catch((e: unknown) => {
      tasks.value = []
      error.value = String((e as any)?.response?.data?.detail || e)
    })
    .finally(() => { loading.value = false })
}

function loadMessages(taskId: number) {
  messageLoadingId.value = taskId
  api.a2aListMessages(taskId)
    .then((res) => {
      messagesMap.value = { ...messagesMap.value, [taskId]: res.data.messages || [] }
      messagesLoaded.value = new Set([...Array.from(messagesLoaded.value), taskId])
    })
    .catch(() => {
      messagesMap.value = { ...messagesMap.value, [taskId]: [] }
      messagesLoaded.value = new Set([...Array.from(messagesLoaded.value), taskId])
    })
    .finally(() => { messageLoadingId.value = null })
}

function sendMessage(taskId: number) {
  const content = composeContent.value.trim()
  if (!content) return
  sendLoadingId.value = taskId
  error.value = ''
  api.a2aPostMessage(taskId, {
    content,
    kind: composeKind.value,
    agent_id: composeAgentId.value > 0 ? Number(composeAgentId.value) : undefined,
  })
    .then(() => {
      composeContent.value = ''
      loadMessages(taskId)
    })
    .catch((e: unknown) => {
      error.value = String((e as any)?.response?.data?.detail || e)
    })
    .finally(() => { sendLoadingId.value = null })
}

function formatTime(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return d.toLocaleString()
}

function loadMyAgents() {
  api.fetchMyAgents()
    .then((res) => {
      const rows = ((res.data as any)?.agents || (res.data as any)?.items || res.data) as any
      const arr = Array.isArray(rows) ? rows : []
      myAgents.value = arr
        .map((a: any) => ({ id: Number(a?.id || 0), name: String(a?.name || '') }))
        .filter((a: any) => a.id > 0 && a.name)
        .slice(0, 200)
    })
    .catch(() => { myAgents.value = [] })
}

onMounted(() => {
  loadMyAgents()
  reload()
})
</script>

<style scoped>
.a2a-console { display: grid; gap: var(--space-5); }
.a2a-console__head { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: var(--space-4); }
.a2a-console__actions { display: flex; gap: var(--space-2); }
.page-desc { color: var(--text-secondary); margin: 0; }
.a2a-console__filters { padding: var(--space-4); display: grid; grid-template-columns: 1fr 280px; gap: var(--space-3); }
.a2a-console__error { padding: var(--space-4); }
.grid { display: grid; gap: var(--space-4); }
.task-card { padding: var(--space-5); }
.task-card__head { display: flex; justify-content: space-between; gap: var(--space-3); align-items: flex-start; }
.task-card__title h3 { margin: 0; }
.a2a-compose { margin-top: var(--space-3); display: grid; grid-template-columns: 220px 140px 1fr auto; gap: var(--space-2); align-items: center; }
.a2a-compose__input { width: 100%; }
.msg-list { margin: var(--space-3) 0 0; padding: 0; list-style: none; display: grid; gap: var(--space-2); }
.msg-row { display: grid; grid-template-columns: 160px 110px 160px 1fr; gap: var(--space-2); font-size: var(--font-caption); }
.msg-time { color: var(--text-secondary); }
.msg-kind { color: var(--text-secondary); }
.msg-author { font-weight: 600; }
.msg-content { color: var(--text-secondary); }

@media (max-width: 720px) {
  .a2a-console__filters { grid-template-columns: 1fr; }
  .a2a-compose { grid-template-columns: 1fr; }
  .msg-row { grid-template-columns: 1fr; gap: 2px; }
}
</style>
